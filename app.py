from flask import Flask, redirect, render_template, request, url_for

from database import (
    ORDER_STATUSES,
    PAYMENT_STATUSES,
    create_order,
    create_product,
    delete_product,
    get_active_products,
    get_all_orders,
    get_all_products,
    get_dashboard_stats,
    get_order_by_id,
    get_product_by_id,
    init_db,
    update_order_status,
    update_payment_status,
    update_product,
)

app = Flask(__name__)

init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    products = get_active_products()

    if request.method == "POST":
        order_id = create_order(
            request.form["customer_name"],
            request.form["phone_number"],
            request.form["address"],
            int(request.form["product_id"]),
            int(request.form["quantity"]),
        )
        order = get_order_by_id(order_id)
        return render_template("index.html", order=order, products=products)

    return render_template("index.html", products=products)


@app.route("/track", methods=["GET", "POST"])
def track():
    order = None
    error = None

    if request.method == "POST":
        order_id = request.form.get("order_id", "").strip()

        if not order_id.isdigit():
            error = "Please enter a valid order ID number."
        else:
            order = get_order_by_id(int(order_id))
            if order is None:
                error = f"No order found with ID #{order_id}."

    return render_template("track.html", order=order, error=error)


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        search = request.form.get("search", "")
        action = request.form.get("action")

        if action == "update_order":
            update_order_status(
                int(request.form["order_id"]),
                request.form["status"],
            )
        elif action == "update_payment":
            update_payment_status(
                int(request.form["order_id"]),
                request.form["payment_status"],
            )

        return redirect(url_for("admin", search=search))

    search = request.args.get("search", "")
    stats = get_dashboard_stats()
    orders = get_all_orders(search)

    return render_template(
        "admin.html",
        orders=orders,
        stats=stats,
        search=search,
        order_statuses=ORDER_STATUSES,
        payment_statuses=PAYMENT_STATUSES,
    )


@app.route("/admin/products", methods=["GET", "POST"])
def admin_products():
    if request.method == "POST":
        create_product(
            request.form["name"],
            float(request.form["price"]),
            request.form.get("description", ""),
        )
        return redirect(url_for("admin_products"))

    products = get_all_products()
    return render_template("admin_products.html", products=products)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    product = get_product_by_id(product_id)
    if product is None:
        return redirect(url_for("admin_products"))

    if request.method == "POST":
        update_product(
            product_id,
            request.form["name"],
            float(request.form["price"]),
            request.form.get("description", ""),
            1 if request.form.get("is_active") else 0,
        )
        return redirect(url_for("admin_products"))

    return render_template("edit_product.html", product=product)


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
def delete_product_route(product_id):
    delete_product(product_id)
    return redirect(url_for("admin_products"))


if __name__ == "__main__":
    app.run(debug=True)
