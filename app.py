from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
import json
import sqlite3
import hashlib
import datetime
import os
import random
from functools import wraps

app = Flask(__name__)
app.secret_key = 'aimbotfx_reseller_secret_2026'

def init_db():
    db_exists = os.path.exists('reseller.db')
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    
    if db_exists:
        try:
            c.execute("SELECT price FROM products LIMIT 1")
        except sqlite3.OperationalError:
            try:
                c.execute("ALTER TABLE products ADD COLUMN price REAL DEFAULT 0")
            except:
                pass
        
        try:
            c.execute("SELECT duration FROM products LIMIT 1")
        except sqlite3.OperationalError:
            try:
                c.execute("ALTER TABLE products ADD COLUMN duration TEXT DEFAULT '7 days'")
            except:
                pass
    
    if db_exists:
        try:
            c.execute("SELECT price FROM key_history LIMIT 1")
        except sqlite3.OperationalError:
            try:
                c.execute("ALTER TABLE key_history ADD COLUMN price REAL DEFAULT 0")
            except:
                pass
        
        try:
            c.execute("SELECT product_name FROM key_history LIMIT 1")
        except sqlite3.OperationalError:
            try:
                c.execute("ALTER TABLE key_history ADD COLUMN product_name TEXT")
            except:
                pass
    
    c.execute('''CREATE TABLE IF NOT EXISTS admin
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS resellers
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, balance REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS key_history
                 (id INTEGER PRIMARY KEY, reseller_id INTEGER, product_id INTEGER, 
                  product_name TEXT, duration TEXT, key_value TEXT, generated_at TEXT, price REAL,
                  FOREIGN KEY(reseller_id) REFERENCES resellers(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id INTEGER PRIMARY KEY, name TEXT, api_id INTEGER, duration TEXT, price REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS product_durations
                 (id INTEGER PRIMARY KEY, product_id INTEGER, duration TEXT, price REAL,
                  FOREIGN KEY(product_id) REFERENCES products(id))''')
    
    conn.commit()
    
    admin = c.execute("SELECT * FROM admin WHERE username='admin'").fetchone()
    if not admin:
        hashed = hashlib.sha256('khanbro786'.encode()).hexdigest()
        c.execute("INSERT INTO admin (username, password) VALUES (?, ?)", 
                  ('admin', hashed))
        conn.commit()
    else:
        hashed = hashlib.sha256('khanbro786'.encode()).hexdigest()
        c.execute("UPDATE admin SET password = ? WHERE username = 'admin'", (hashed,))
        conn.commit()
    
    default_products = [
        (124, "DRIPCLIENT FF PC AIMKILL", 44, "7 days", 7.99),
        (49, "BR MOD FF PC VERSION", 49, "7 days", 6.99),
        (67, "BR MOD FF ROOT ANDROID", 67, "7 days", 5.49),
        (59, "DRIPCLIENT 8BP NONROOT ANDROID", 59, "7 days", 6.23),
        (62, "DRIPCLIENT FF NONROOT APKMOD", 62, "7 days", 6.23),
        (63, "DRIPCLIENT FF ROOT ANDROID", 63, "7 days", 6.23),
        (91, "DRIPCLIENT PROXY FF NONROOT ANDROID", 91, "7 days", 8.49),
        (58, "FLUORITE IOS FF", 58, "7 days", 9.99),
        (84, "FLUORITE IOS MLBB", 84, "7 days", 9.99),
        (64, "HAXX-CKER PRO FF ROOT ANDROID", 64, "7 days", 7.49),
        (65, "HG CHEATS FF APKMOD NONROOT+ROOT", 65, "7 days", 6.99),
        (72, "HIKARI MOD FF ROOT ANDROID", 72, "7 days", 5.99),
        (54, "PATO TEAM FF ALL ANDROID", 54, "7 days", 4.99),
        (48, "PRIME HOOK FF NONROOT ANDROID", 48, "7 days", 5.99),
        (130, "RAPID CORE FF ROOT ANDROID", 130, "7 days", 12.99),
        (81, "REAPER X PRO FF ROOT ANDROID", 81, "7 days", 8.99),
        (127, "SILENT CHEAT FF NONROOT APKMOD", 127, "7 days", 7.49),
        (128, "SILENT CHEAT FF ROOT ANDROID", 128, "7 days", 7.49),
        (66, "XYZ CHEATS FF ROOT ANDROID", 66, "7 days", 6.99),
        (129, "XYZ CHEATS UNLIMITED CREDIT FOR 1 SEASON", 129, "30 days", 29.99)
    ]
    
    count = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        for pid, name, api_id, dur, price in default_products:
            try:
                c.execute("INSERT INTO products (id, name, api_id, duration, price) VALUES (?,?,?,?,?)", 
                          (pid, name, api_id, dur, price))
            except:
                pass
        conn.commit()
    
    for pid, _, _, _, _ in default_products:
        durations = c.execute("SELECT COUNT(*) FROM product_durations WHERE product_id=?", (pid,)).fetchone()[0]
        if durations == 0:
            default_durs = [
                (pid, "1 day", 1.00),
                (pid, "7 days", 5.00),
                (pid, "15 days", 10.00),
                (pid, "30 days", 20.00)
            ]
            for prod_id, dur, price in default_durs:
                try:
                    c.execute("INSERT INTO product_durations (product_id, duration, price) VALUES (?,?,?)", 
                              (prod_id, dur, price))
                except:
                    pass
        conn.commit()
    
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'reseller_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Admin access required', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def get_balance(reseller_id):
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM resellers WHERE id=?", (reseller_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def get_product_name(product_id):
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    c.execute("SELECT name FROM products WHERE id=?", (product_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else f"Product {product_id}"

def get_products():
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    products = c.execute("SELECT id, name, api_id, duration, price FROM products ORDER BY name").fetchall()
    conn.close()
    return products

def get_product_durations(product_id):
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    durations = c.execute("SELECT id, duration, price FROM product_durations WHERE product_id=? ORDER BY id", (product_id,)).fetchall()
    conn.close()
    return durations

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('reseller.db')
        c = conn.cursor()
        c.execute("SELECT id, username, password, balance FROM resellers WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()
        if user and user[2] == hashlib.sha256(password.encode()).hexdigest():
            session['reseller_id'] = user[0]
            session['reseller_username'] = user[1]
            session['balance'] = user[3]
            flash(f'✅ Welcome back {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('reseller.db')
        c = conn.cursor()
        c.execute("SELECT id, password FROM admin WHERE username=?", (username,))
        admin = c.fetchone()
        conn.close()
        if admin:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if admin[1] == hashed_password:
                session['admin_id'] = admin[0]
                flash('✅ Admin access granted!', 'success')
                return redirect(url_for('admin_panel'))
            else:
                flash('❌ Invalid admin credentials', 'danger')
        else:
            flash('❌ Invalid admin credentials', 'danger')
    return render_template('admin_login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    reseller_id = session['reseller_id']
    balance = get_balance(reseller_id)
    session['balance'] = balance
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT product_name, duration, key_value, generated_at, price FROM key_history WHERE reseller_id=? ORDER BY id DESC LIMIT 20", (reseller_id,))
        history = c.fetchall()
    except sqlite3.OperationalError:
        c.execute("SELECT product_name, duration, key_value, generated_at, 0 FROM key_history WHERE reseller_id=? ORDER BY id DESC LIMIT 20", (reseller_id,))
        history = c.fetchall()
    
    products = get_products()
    conn.close()
    return render_template('dashboard.html', products=products, 
                           balance=balance, history=history, username=session['reseller_username'])

@app.route('/get_price', methods=['POST'])
@login_required
def get_price():
    product_id = request.form.get('product_id')
    duration = request.form.get('duration')
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    
    c.execute("SELECT price FROM product_durations WHERE product_id=? AND duration=?", (product_id, duration))
    price_row = c.fetchone()
    
    if not price_row:
        c.execute("SELECT price FROM products WHERE id=?", (product_id,))
        default_price = c.fetchone()
        price = default_price[0] if default_price else 1.00
    else:
        price = price_row[0]
    
    conn.close()
    return jsonify({'price': price})

@app.route('/generate_key', methods=['POST'])
@login_required
def generate_key():
    product_id = request.form.get('product_id')
    duration = request.form.get('duration')
    quantity = int(request.form.get('quantity', 1))
    
    if not product_id or not duration:
        flash('❌ Product and duration required', 'danger')
        return redirect(url_for('dashboard'))
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    
    c.execute("SELECT price FROM product_durations WHERE product_id=? AND duration=?", (product_id, duration))
    price_row = c.fetchone()
    
    if not price_row:
        c.execute("SELECT price FROM products WHERE id=?", (product_id,))
        default_price = c.fetchone()
        price = default_price[0] if default_price else 1.00
    else:
        price = price_row[0]
    
    total_cost = price * quantity
    
    reseller_id = session['reseller_id']
    balance = get_balance(reseller_id)
    if balance < total_cost:
        flash(f'❌ Insufficient balance. Need ${total_cost:.2f}, you have ${balance:.2f}', 'danger')
        conn.close()
        return redirect(url_for('dashboard'))
    
    keys_generated = []
    for _ in range(quantity):
        api_url = f"https://xyzcheats.com/api/reseller_v1.php?api_key=4f296722ccffa6f829ed9cef05273531&action=buy&product_id={product_id}&duration={duration.replace(' ', '%20')}"
        try:
            response = requests.get(api_url, timeout=15)
            data = response.json()
        except Exception as e:
            flash(f'❌ API Error: {str(e)}', 'danger')
            conn.close()
            return redirect(url_for('dashboard'))
        
        if response.status_code != 200 or 'key' not in data:
            flash('❌ Failed to generate key. Please try again.', 'danger')
            conn.close()
            return redirect(url_for('dashboard'))
        
        key_value = data.get('key', '')
        keys_generated.append(key_value)
        
        product_name = get_product_name(int(product_id))
        c.execute("INSERT INTO key_history (reseller_id, product_id, product_name, duration, key_value, generated_at, price) VALUES (?,?,?,?,?,?,?)",
                  (reseller_id, product_id, product_name, duration, key_value, datetime.datetime.now().isoformat(), price))
    
    new_balance = balance - total_cost
    c.execute("UPDATE resellers SET balance=? WHERE id=?", (new_balance, reseller_id))
    conn.commit()
    conn.close()
    
    session['balance'] = new_balance
    flash(f'✅ {quantity} key(s) generated successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/admin_panel')
@admin_required
def admin_panel():
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    resellers = c.execute("SELECT id, username, balance FROM resellers").fetchall()
    products = c.execute("SELECT id, name, api_id, duration, price FROM products ORDER BY id").fetchall()
    
    product_durations = {}
    for p in products:
        durations = c.execute("SELECT id, duration, price FROM product_durations WHERE product_id=? ORDER BY id", (p[0],)).fetchall()
        product_durations[p[0]] = durations
    
    conn.close()
    return render_template('admin_panel.html', resellers=resellers, products=products, 
                          product_durations=product_durations)

@app.route('/add_reseller', methods=['POST'])
@admin_required
def add_reseller():
    username = request.form.get('username')
    password = request.form.get('password')
    balance = float(request.form.get('balance', 0))
    
    if not username or not password:
        flash('❌ Username and password required', 'danger')
        return redirect(url_for('admin_panel'))
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO resellers (username, password, balance) VALUES (?,?,?)",
                  (username, hashlib.sha256(password.encode()).hexdigest(), balance))
        conn.commit()
        flash('✅ Reseller added successfully', 'success')
    except sqlite3.IntegrityError:
        flash('❌ Username already exists', 'danger')
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/update_balance', methods=['POST'])
@admin_required
def update_balance():
    reseller_id = request.form.get('reseller_id')
    amount = float(request.form.get('amount', 0))
    action = request.form.get('action')
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    if action == 'add':
        c.execute("UPDATE resellers SET balance = balance + ? WHERE id=?", (amount, reseller_id))
    elif action == 'set':
        c.execute("UPDATE resellers SET balance = ? WHERE id=?", (amount, reseller_id))
    conn.commit()
    conn.close()
    flash('✅ Balance updated', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/add_product', methods=['POST'])
@admin_required
def add_product():
    name = request.form.get('name')
    api_id = request.form.get('api_id')
    
    if not name or not api_id:
        flash('❌ Product name and API ID required', 'danger')
        return redirect(url_for('admin_panel'))
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO products (name, api_id, duration, price) VALUES (?,?,?,?)", 
                  (name, api_id, '7 days', 0))
        product_id = c.lastrowid
        default_durs = [
            (product_id, "1 day", 1.00),
            (product_id, "7 days", 5.00),
            (product_id, "15 days", 10.00),
            (product_id, "30 days", 20.00)
        ]
        for prod_id, dur, price in default_durs:
            c.execute("INSERT INTO product_durations (product_id, duration, price) VALUES (?,?,?)", 
                      (prod_id, dur, price))
        conn.commit()
        flash('✅ Product added successfully with default durations', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/add_product_duration', methods=['POST'])
@admin_required
def add_product_duration():
    product_id = request.form.get('product_id')
    duration = request.form.get('duration')
    price = float(request.form.get('price', 0))
    
    if not product_id or not duration:
        flash('❌ Product and duration required', 'danger')
        return redirect(url_for('admin_panel'))
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO product_durations (product_id, duration, price) VALUES (?,?,?)", 
                  (product_id, duration, price))
        conn.commit()
        flash('✅ Duration added successfully', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/update_product_duration', methods=['POST'])
@admin_required
def update_product_duration():
    duration_id = request.form.get('duration_id')
    price = float(request.form.get('price', 0))
    duration = request.form.get('duration')
    
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE product_durations SET price=?, duration=? WHERE id=?", 
                  (price, duration, duration_id))
        conn.commit()
        flash('✅ Duration updated successfully', 'success')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/delete_product_duration/<int:duration_id>', methods=['POST'])
@admin_required
def delete_product_duration(duration_id):
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    c.execute("DELETE FROM product_durations WHERE id=?", (duration_id,))
    conn.commit()
    conn.close()
    flash('✅ Duration deleted', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id=?", (product_id,))
    c.execute("DELETE FROM product_durations WHERE product_id=?", (product_id,))
    conn.commit()
    conn.close()
    flash('✅ Product deleted', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/delete_reseller/<int:reseller_id>', methods=['POST'])
@admin_required
def delete_reseller(reseller_id):
    conn = sqlite3.connect('reseller.db')
    c = conn.cursor()
    c.execute("DELETE FROM resellers WHERE id=?", (reseller_id,))
    c.execute("DELETE FROM key_history WHERE reseller_id=?", (reseller_id,))
    conn.commit()
    conn.close()
    flash('✅ Reseller deleted', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    flash('✅ Logged out successfully', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)