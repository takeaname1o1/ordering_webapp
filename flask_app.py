import sqlite3
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

DB_NAME = "momo_orders.db"

def init_db():
    """Initialize the SQLite database and migrate schema if needed."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_number TEXT,
            items TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            customer_name TEXT DEFAULT 'Guest',
            order_type TEXT DEFAULT 'Dine-in',
            is_paid BOOLEAN DEFAULT 0,
            packing_charge REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- ROUTES ---

@app.route('/adminmomo')
def kitchen_view():
    """Serve the Kitchen Display System (admin.html)."""
    try:
        return send_file('admin.html')
    except Exception as e:
        return f"Error serving admin.html: {e}", 500

@app.route('/')
def customer_view():
    """Serve the Customer Ordering App (index.html)."""
    try:
        return send_file('index.html')
    except Exception as e:
        return f"Error serving index.html: {e}", 500


@app.route('/menu.json')
def serve_menu():
    try:
        return send_file('static/menu.json')
    except Exception as e:
        return jsonify({"error": "menu.json not found"}), 404



@app.route('/app')
def app_alias():
    """Alias for customer view to match logs."""
    return customer_view()

@app.route('/api/order', methods=['POST'])
def place_order():
    try:
        data = request.json

        # Extract data matching frontend payload
        table_number = data.get('tableNumber')
        cart = data.get('cart')
        customer_name = data.get('customerName', 'Guest')
        total_amount = data.get('totalAmount')
        packing_charge = data.get('packingCharge', 0)

        # Determine order type based on packing charge
        order_type = 'Takeaway' if packing_charge > 0 else 'Dine-in'

        if not cart or total_amount is None:
            return jsonify({"error": "Missing cart or total amount"}), 400

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Convert list of item objects to JSON string for storage
        items_json = json.dumps(cart)

        cursor.execute('''
            INSERT INTO orders (table_number, items, total_amount, customer_name, order_type, is_paid, packing_charge)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (table_number, items_json, total_amount, customer_name, order_type, 0, packing_charge))

        new_order_id = cursor.lastrowid
        conn.commit()

        # Get count of pending orders for "Orders Ahead" calculation
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending' AND id < ?", (new_order_id,))
        orders_ahead = cursor.fetchone()[0]

        conn.close()

        return jsonify({
            "success": True,
            "orderId": new_order_id,
            "ordersAhead": orders_ahead,
            "customerName": customer_name
        }), 201
    except Exception as e:
        print(f"Order Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/kitchen', methods=['GET'])
def get_kitchen_orders():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('SELECT id, table_number, items, total_amount, status, timestamp, customer_name, order_type, is_paid, packing_charge FROM orders ORDER BY timestamp ASC')
        rows = cursor.fetchall()

        orders = []
        for row in rows:
            orders.append({
                'id': row[0],
                'tableNumber': row[1],
                'cart': json.loads(row[2]),
                'total_amount': row[3],
                'status': row[4],
                'timestamp': row[5],
                'customerName': row[6],
                'orderType': row[7],
                'is_paid': bool(row[8]),
                'packingCharge': row[9]
            })

        # Calculate Total Sales (completed and paid orders)
        cursor.execute("SELECT SUM(total_amount) FROM orders WHERE status = 'completed' AND is_paid = 1")
        total_sales_result = cursor.fetchone()[0]
        total_sales = total_sales_result if total_sales_result else 0.0

        conn.close()

        return jsonify({
            'orders': orders,
            'total_sales': total_sales
        })

    except Exception as e:
        print(f"Error fetching kitchen: {e}")
        return jsonify({'orders': [], 'total_sales': 0.0})

@app.route('/api/order/status', methods=['POST'])
def update_order_status():
    try:
        data = request.json
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE orders SET status = ? WHERE id = ?', (data.get('status'), data.get('orderId')))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/order/payment', methods=['POST'])
def update_payment_status():
    try:
        data = request.json
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('UPDATE orders SET is_paid = ? WHERE id = ?', (1 if data.get('is_paid') else 0, data.get('orderId')))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("--------------------------------------------------")
    print(" NEPALI MOMO SERVER RUNNING")
    print("--------------------------------------------------")
    print(" Kitchen View  : http://127.0.0.1:5006/admin") # Updated to point to /admin correctly
    print(" Customer App  : http://127.0.0.1:5006/")
    print("--------------------------------------------------")
    print(" PRE-SET TABLE LINKS (Copy or Click to Test)")
    print("--------------------------------------------------")
    for i in range(1, 11):
        print(f" Table {i:<2} : http://127.0.0.1:5006/?table={i}")
    print("--------------------------------------------------")

    app.run(host='0.0.0.0', port=5006, debug=True)
    print("--------------------------------------------------")
    print(" NEPALI MOMO SERVER RUNNING")
    print("--------------------------------------------------")
    print(" Kitchen View  : http://127.0.0.1:5006/")
    print(" Customer App  : http://127.0.0.1:5006/app")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', port=5006, debug=True)