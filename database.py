import sqlite3
from pathlib import Path

DATABASE = Path(__file__).parent / "orders.db"

STATUSES = ["Pending", "Accepted", "Delivered", "Rejected"]


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                address TEXT NOT NULL,
                water_can_quantity INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def create_order(customer_name, phone_number, address, water_can_quantity):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO orders (customer_name, phone_number, address, water_can_quantity, status)
            VALUES (?, ?, ?, ?, 'Pending')
            """,
            (customer_name, phone_number, address, water_can_quantity),
        )
        conn.commit()
        return cursor.lastrowid


def get_order_by_id(order_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)


def get_all_orders():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def update_order_status(order_id, status):
    if status not in STATUSES:
        raise ValueError("Invalid status")

    with get_connection() as conn:
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
        conn.commit()
