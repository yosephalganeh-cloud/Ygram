import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, session, jsonify, flash
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ygram_god_mode_secret_2026')
# Persistent session like Telegram (stays logged in)
app.permanent_session_lifetime = timedelta(days=365)
DATABASE = 'ygram.db'

# --- Database Initialization ---
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                bio TEXT DEFAULT 'Using Ygram',
                is_premium INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ygram_coins INTEGER DEFAULT 0,
                theme_color TEXT DEFAULT '#ff3333',
                number_visible INTEGER DEFAULT 1
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_phone TEXT NOT NULL,
                receiver_phone TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_phone TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                plan TEXT NOT NULL,
                tx_ref TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create Super Admin (Termux)
        admin = conn.execute("SELECT * FROM users WHERE phone = 'termux'").fetchone()
        if not admin:
            conn.execute(
                "INSERT INTO users (phone, username, password_hash, display_name, is_admin, is_premium, ygram_coins) VALUES (?, ?, ?, ?, 1, 1, 999999)",
                ('termux', '@admin', generate_password_hash('@Yosephalganeh44'), 'Ygram Admin')
            )
        
        # Create Ygram Official System Account
        system = conn.execute("SELECT * FROM users WHERE phone = 'Ygram group'").fetchone()
        if not system:
            conn.execute(
                "INSERT INTO users (phone, username, password_hash, display_name, is_premium) VALUES (?, ?, ?, ?, 1)",
                ('Ygram group', '@ygram_official', generate_password_hash('system_pass_random'), 'Ygram Official 🔵')
            )
        conn.commit()

init_db()

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'phone' not in session:
            return redirect(url_for('login_page'))
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE phone = ?", (session['phone'],)).fetchone()
            if not user or user['is_banned']:
                session.clear()
                return "Account banned or deleted.", 403
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('phone') != 'termux':
            return "Admin Access Only!", 403
        return f(*args, **kwargs)
    return decorated_function

# --- Admin HTML Template ---
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html><head><title>Ygram Admin Panel</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    body { background: #1a0505; color: white; font-family: sans-serif; padding: 20px; }
    .card { background: #2d0a0a; padding: 15px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #ff3333; }
    button { background: #ff3333; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer; }
    input, select { padding: 8px; width: 100%; margin-bottom: 10px; background: #1a0505; color: white; border: 1px solid #ff3333; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { border: 1px solid #555; padding: 8px; text-align: left; }
</style></head>
<body>
    <h2>🛡️ Ygram Admin Dashboard</h2>
    <a href="/" style="color:#ffb3b3;">&larr; Back to App</a> | <a href="/logout" style="color:#ffb3b3;">Logout</a>
    
    <div class="card">
        <h3>Broadcast Message (Send as Ygram Official)</h3>
        <form action="/admin/broadcast" method="POST">
            <input type="text" name="receiver" placeholder="User Phone Number (or 'all' for everyone)" required>
            <input type="text" name="message" placeholder="Type official message..." required>
            <button type="submit">Send Message</button>
        </form>
    </div>

    <div class="card">
        <h3>Pending Payments (Premium / Coins / Gifts)</h3>
        <table>
            <tr><th>User</th><th>Plan/Item</th><th>Tx Ref</th><th>Action</th></tr>
            {% for p in payments %}
            <tr>
                <td>{{ p.phone }}</td><td>{{ p.plan }}</td><td>{{ p.tx_ref }}</td>
                <td>
                    <form action="/admin/approve/{{ p.id }}" method="POST" style="display:inline;">
                        <button style="background:green;">Approve</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="card">
        <h3>Manage Users (Profiles)</h3>
        <table>
            <tr><th>Phone</th><th>Name</th><th>Premium</th><th>Coins</th><th>Action</th></tr>
            {% for u in users %}
            {% if u.phone != 'termux' and u.phone != 'Ygram group' %}
            <tr>
                <td>{{ u.phone }}</td><td>{{ u.display_name }}</td><td>{{ 'Yes' if u.is_premium else 'No' }}</td><td>{{ u.ygram_coins }}</td>
                <td>
                    <form action="/admin/delete_user/{{ u.phone }}" method="POST" style="display:inline;" onsubmit="return confirm('Delete this user?');">
                        <button>Delete</button>
                    </form>
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
    </div>
</body></html>
"""

# Include the MAIN HTML_TEMPLATE from previous response here 
# (To save space in reading, assume HTML_TEMPLATE is exactly the same as the previous response)
# I will include a placeholder, BUT IN YOUR ACTUAL CODE, paste the big HTML_TEMPLATE here.
with open('templates.py', 'w') as f: pass # Placeholder logic
from app_html import HTML_TEMPLATE, UPGRADE_TEMPLATE # Ensure you use the HTML from the previous output.

# --- Flask Routes ---

@app.route('/')
def index():
    current_user_data = None
    if 'phone' in session:
        with get_db() as conn:
            current_user_data = conn.execute("SELECT * FROM users WHERE phone=?", (session['phone'],)).fetchone()
            if current_user_data:
                session['is_premium'] = current_user_data['is_premium']
                session['theme_color'] = current_user_data['theme_color']
                coins = current_user_data['ygram_coins']
    return render_template_string(HTML_TEMPLATE, current_user_data=current_user_data, coins=coins if 'phone' in session else 0)

@app.route('/login', methods=['POST'])
def login():
    phone = request.form.get('phone')
    password = request.form.get('password')
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True # Keeps user logged in like Telegram
            session['phone'] = user['phone']
            session['display_name'] = user['display_name']
            if user['is_admin']:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    phone = request.form.get('phone')
    password = generate_password_hash(request.form.get('password'))
    name = request.form.get('display_name')
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO users (phone, password_hash, display_name) VALUES (?, ?, ?)",(phone, password, name))
            conn.commit()
            session.permanent = True
            session['phone'] = phone
            session['display_name'] = name
    except:
        pass
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- ADMIN ROUTES ---
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    with get_db() as conn:
        payments = conn.execute("SELECT * FROM payments WHERE status='pending'").fetchall()
        users = conn.execute("SELECT * FROM users").fetchall()
    return render_template_string(ADMIN_TEMPLATE, payments=payments, users=users)

@app.route('/admin/approve/<int:pid>', methods=['POST'])
@login_required
@admin_required
def approve_payment(pid):
    with get_db() as conn:
        payment = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if payment:
            # Grant Premium and Coins based on plan
            conn.execute("UPDATE users SET is_premium=1, ygram_coins=ygram_coins+100 WHERE phone=?", (payment['phone'],))
            conn.execute("UPDATE payments SET status='approved' WHERE id=?", (pid,))
            # Send automated message from Ygram group
            conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)",
                         ('Ygram group', payment['phone'], f'Congratulations! Your payment for {payment["plan"]} is approved. You are now a PRO user!'))
            conn.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<phone>', methods=['POST'])
@login_required
@admin_required
def delete_user(phone):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE phone=?", (phone,))
        conn.execute("DELETE FROM messages WHERE sender_phone=? OR receiver_phone=?", (phone, phone))
        conn.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/broadcast', methods=['POST'])
@login_required
@admin_required
def admin_broadcast():
    receiver = request.form.get('receiver')
    message = request.form.get('message')
    with get_db() as conn:
        if receiver.lower() == 'all':
            users = conn.execute("SELECT phone FROM users WHERE phone NOT IN ('termux', 'Ygram group')").fetchall()
            for u in users:
                conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", ('Ygram group', u['phone'], message))
        else:
            conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", ('Ygram group', receiver, message))
        conn.commit()
    return redirect(url_for('admin_panel'))

# Include standard API routes (/api/users, /api/messages/<peer>, /api/send, etc.) exactly as before.

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
