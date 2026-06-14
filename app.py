from flask import Flask, redirect, render_template, request, url_for

from database import (
    STATUSES,
    create_order,
    get_all_orders,
    get_order_by_id,
    init_db,
    update_order_status,
)

app = Flask(__name__)

init_db()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        order_id = create_order(
            request.form["customer_name"],
            request.form["phone_number"],
            request.form["address"],
            int(request.form["water_can_quantity"]),
        )
        order = {
            "id": order_id,
            "customer_name": request.form["customer_name"],
            "phone_number": request.form["phone_number"],
            "address": request.form["address"],
            "water_can_quantity": request.form["water_can_quantity"],
            "status": "Pending",
        }
        return render_template("index.html", order=order)

    return render_template("index.html")


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
        update_order_status(
            int(request.form["order_id"]),
            request.form["status"],
        )
        return redirect(url_for("admin"))

    orders = get_all_orders()
    return render_template("admin.html", orders=orders, statuses=STATUSES)


if __name__ == "__main__":
    app.run(debug=True)
