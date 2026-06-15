import sqlite3
from pathlib import Path

DATABASE = Path(__file__).parent / "orders.db"

ORDER_STATUSES = [
    "Pending",
    "Accepted",
    "Out for Delivery",
    "Delivered",
    "Cancelled",
]
PAYMENT_STATUSES = ["Paid", "Unpaid"]

DEFAULT_PRODUCTS = [
    ("20L Water Can", 50.0, "Large refillable water can"),
    ("5L Water Bottle", 15.0, "Small bottled water pack"),
]


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def _create_products_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        )
        """
    )


def _create_orders_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            address TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            payment_status TEXT NOT NULL DEFAULT 'Unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
        """
    )


def _migrate_v1_orders(conn):
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()
    }
    if not columns or "product_id" in columns:
        return

    conn.execute("ALTER TABLE orders RENAME TO orders_old")
    _create_orders_table(conn)

    default_product_id = conn.execute(
        "SELECT id FROM products ORDER BY id LIMIT 1"
    ).fetchone()[0]

    old_orders = conn.execute("SELECT * FROM orders_old").fetchall()
    for old in old_orders:
        quantity = old["water_can_quantity"]
        total_amount = quantity * 50.0
        status = old["status"]
        if status == "Rejected":
            status = "Cancelled"

        conn.execute(
            """
            INSERT INTO orders (
                id, customer_name, phone_number, address,
                product_id, quantity, total_amount, status,
                payment_status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Unpaid', ?)
            """,
            (
                old["id"],
                old["customer_name"],
                old["phone_number"],
                old["address"],
                default_product_id,
                quantity,
                total_amount,
                status,
                old["created_at"],
            ),
        )

    conn.execute("DROP TABLE orders_old")


def _seed_products(conn):
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO products (name, price, description) VALUES (?, ?, ?)",
            DEFAULT_PRODUCTS,
        )


def init_db():
    with get_connection() as conn:
        _create_products_table(conn)
        _seed_products(conn)

        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()
        }
        if not columns:
            _create_orders_table(conn)
        else:
            _migrate_v1_orders(conn)

        conn.commit()


def _order_query():
    return """
        SELECT
            orders.*,
            products.name AS product_name,
            products.price AS product_price
        FROM orders
        JOIN products ON orders.product_id = products.id
    """


def get_active_products():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM products
            WHERE is_active = 1
            ORDER BY name
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_products():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM products ORDER BY name").fetchall()
        return [dict(row) for row in rows]


def get_product_by_id(product_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)


def create_product(name, price, description):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO products (name, price, description)
            VALUES (?, ?, ?)
            """,
            (name, price, description),
        )
        conn.commit()
        return cursor.lastrowid


def update_product(product_id, name, price, description, is_active):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE products
            SET name = ?, price = ?, description = ?, is_active = ?
            WHERE id = ?
            """,
            (name, price, description, is_active, product_id),
        )
        conn.commit()


def delete_product(product_id):
    with get_connection() as conn:
        order_count = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE product_id = ?",
            (product_id,),
        ).fetchone()[0]
        if order_count > 0:
            conn.execute(
                "UPDATE products SET is_active = 0 WHERE id = ?",
                (product_id,),
            )
        else:
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()


def create_order(customer_name, phone_number, address, product_id, quantity):
    product = get_product_by_id(product_id)
    if product is None or not product["is_active"]:
        raise ValueError("Invalid product")

    total_amount = product["price"] * quantity

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO orders (
                customer_name, phone_number, address,
                product_id, quantity, total_amount,
                status, payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'Pending', 'Unpaid')
            """,
            (
                customer_name,
                phone_number,
                address,
                product_id,
                quantity,
                total_amount,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def get_order_by_id(order_id):
    with get_connection() as conn:
        row = conn.execute(
            _order_query() + " WHERE orders.id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)


def get_all_orders(search=""):
    query = _order_query()
    params = []

    search = search.strip()
    if search:
        if search.isdigit():
            query += """
                WHERE orders.id = ?
                   OR orders.customer_name LIKE ?
                   OR orders.phone_number LIKE ?
            """
            like_search = f"%{search}%"
            params = [int(search), like_search, like_search]
        else:
            query += """
                WHERE orders.customer_name LIKE ?
                   OR orders.phone_number LIKE ?
            """
            like_search = f"%{search}%"
            params = [like_search, like_search]

    query += " ORDER BY orders.created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def update_order_status(order_id, status):
    if status not in ORDER_STATUSES:
        raise ValueError("Invalid order status")

    with get_connection() as conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
        conn.commit()


def update_payment_status(order_id, payment_status):
    if payment_status not in PAYMENT_STATUSES:
        raise ValueError("Invalid payment status")

    with get_connection() as conn:
        conn.execute(
            "UPDATE orders SET payment_status = ? WHERE id = ?",
            (payment_status, order_id),
        )
        conn.commit()


def get_dashboard_stats():
    with get_connection() as conn:
        total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        pending_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'Pending'"
        ).fetchone()[0]
        delivered_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = 'Delivered'"
        ).fetchone()[0]
        total_revenue = conn.execute(
            """
            SELECT COALESCE(SUM(total_amount), 0)
            FROM orders
            WHERE payment_status = 'Paid' AND status != 'Cancelled'
            """
        ).fetchone()[0]

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "delivered_orders": delivered_orders,
        "total_revenue": round(total_revenue, 2),
    }
