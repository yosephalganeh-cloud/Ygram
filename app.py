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
app.secret_key = os.environ.get('SECRET_KEY', 'ygram_super_secret_key_2026')
# አንድ ጊዜ ሎጊን ካደረገ በኋላ ለ1 አመት አይወጣም (Like Telegram)
app.permanent_session_lifetime = timedelta(days=365)
DATABASE = 'ygram.db'

# --- Database Initialization ---
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        # Users Table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                bio TEXT DEFAULT 'I am using Ygram',
                is_premium INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ygram_coins INTEGER DEFAULT 0,
                theme_color TEXT DEFAULT '#ff3333',
                number_visible INTEGER DEFAULT 1
            )
        ''')
        # Messages Table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_phone TEXT NOT NULL,
                receiver_phone TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Stories Table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_phone TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Payments Table
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
        
        # 1. Create Super Admin (የጠየቅከው login)
        admin = conn.execute("SELECT * FROM users WHERE phone = 'termux'").fetchone()
        if not admin:
            conn.execute(
                "INSERT INTO users (phone, username, password_hash, display_name, is_admin, is_premium, ygram_coins) VALUES (?, ?, ?, ?, 1, 1, 999999)",
                ('termux', '@Yosephalganeh44', generate_password_hash('@Yosephalganeh44'), 'Ygram Admin')
            )
        
        # 2. Create Official Ygram System Account
        system = conn.execute("SELECT * FROM users WHERE phone = 'Ygram group'").fetchone()
        if not system:
            conn.execute(
                "INSERT INTO users (phone, username, password_hash, display_name, is_premium) VALUES (?, ?, ?, ?, 1)",
                ('Ygram group', '@ygram_official', generate_password_hash('system_pass'), 'Ygram Official 🔵')
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
            user = conn.execute("SELECT is_banned FROM users WHERE phone = ?", (session['phone'],)).fetchone()
            if not user or user['is_banned']:
                session.clear()
                return "Your account has been deleted or banned.", 403
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('phone') != 'termux':
            return "Admin Access Only!", 403
        return f(*args, **kwargs)
    return decorated_function

# --- HTML TEMPLATES ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ygram Messenger</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        /* YGRAM DEFAULT RED THEME */
        :root {
            --bg-main: #1a0505;
            --bg-header: #2d0a0a;
            --accent: {{ session.get('theme_color', '#ff3333') }};
            --text-main: #ffffff;
            --text-muted: #ffb3b3;
            --divider: #3d1414;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: sans-serif; }
        body { background: var(--bg-main); color: var(--text-main); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

        /* Auth */
        .auth-box { margin: auto; padding: 30px; background: var(--bg-header); border: 1px solid var(--accent); border-radius: 12px; max-width: 400px; text-align: center; margin-top: 20%; }
        .auth-box input { width: 100%; padding: 12px; margin-bottom: 10px; background: var(--bg-main); color: white; border: 1px solid var(--divider); border-radius: 5px; }
        .auth-box button { width: 100%; padding: 12px; background: var(--accent); color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; }

        /* App Layout */
        .header { background: var(--bg-header); padding: 15px; display: flex; flex-direction: column; gap: 10px; border-bottom: 1px solid var(--divider); }
        .search-bar input { width: 100%; padding: 8px 15px; background: var(--bg-main); border: 1px solid var(--divider); border-radius: 20px; color: white; }
        
        .content { flex: 1; overflow-y: auto; position: relative; }
        .view { display: none; padding: 15px; padding-bottom: 80px; }
        .view.active { display: block; }
        
        /* Lists */
        .list-item { display: flex; align-items: center; gap: 15px; padding: 15px 0; border-bottom: 1px solid var(--divider); cursor: pointer; }
        .avatar { width: 45px; height: 45px; background: var(--accent); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; }
        
        /* FAB */
        .fab { position: absolute; bottom: 80px; right: 20px; width: 60px; height: 60px; background: var(--accent); border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 24px; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.5); cursor: pointer; }
        .fab-story { bottom: 150px; width: 50px; height: 50px; font-size: 20px; background: var(--bg-header); border: 2px solid var(--accent); }

        /* Bottom Nav */
        .bottom-nav { background: var(--bg-header); display: flex; justify-content: space-around; padding: 10px 0; border-top: 1px solid var(--divider); z-index: 100; position: fixed; bottom: 0; width: 100%; }
        .nav-btn { display: flex; flex-direction: column; align-items: center; color: var(--text-muted); font-size: 12px; cursor: pointer; }
        .nav-btn.active { color: var(--accent); }
        .nav-btn i { font-size: 20px; margin-bottom: 4px; }

        /* Forms / Settings */
        .setting-box { background: var(--bg-header); padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .btn { background: var(--accent); color: white; padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; }
        
        /* Chat Room */
        #chat-ui { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: var(--bg-main); display: none; flex-direction: column; z-index: 200; }
        #messages { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; }
        .msg { padding: 10px; border-radius: 10px; max-width: 80%; }
        .msg.in { background: #3d1414; align-self: flex-start; }
        .msg.out { background: var(--accent); align-self: flex-end; }
        .chat-input { padding: 10px; background: var(--bg-header); display: flex; gap: 10px; }
        .chat-input input { flex: 1; padding: 10px; border-radius: 20px; border: none; background: var(--bg-main); color: white; }
    </style>
</head>
<body>

{% if not session.get('phone') %}
<!-- LOGIN / REGISTER (Admin use phone: termux, pass: @Yosephalganeh44) -->
<div class="auth-box">
    <h2 style="color: var(--accent); margin-bottom: 20px;"><i class="fa-brands fa-telegram"></i> Ygram Red</h2>
    <form action="/login" method="POST">
        <input type="text" name="phone" placeholder="Phone Number or Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Log In</button>
    </form>
    <hr style="border-color: var(--divider); margin: 20px 0;">
    <form action="/register" method="POST">
        <input type="text" name="phone" placeholder="Phone Number" required>
        <input type="text" name="display_name" placeholder="Full Name" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit" style="background: #10b981;">Create Account</button>
    </form>
</div>
{% else %}

<!-- HEADER -->
<div class="header">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h3>Ygram</h3>
        {% if session.get('is_premium') %} <i class="fa-solid fa-star" style="color: gold;"></i> {% endif %}
    </div>
    <div class="search-bar">
        <input type="text" id="search" placeholder="Search chats, @username..." onkeyup="searchUsers()">
    </div>
</div>

<!-- VIEWS -->
<div class="content">
    
    <!-- 1. CHATS -->
    <div id="view-chats" class="view active">
        <div id="chat-list"></div>
        <div class="fab fab-story" onclick="postStory()"><i class="fa-solid fa-camera"></i></div>
        <div class="fab" onclick="document.getElementById('nav-contacts').click()"><i class="fa-solid fa-pen"></i></div>
    </div>

    <!-- 2. CONTACTS -->
    <div id="view-contacts" class="view">
        <button class="btn" style="width:100%; margin-bottom: 15px;" onclick="alert('Contacts Synced with Device Permissions!')"><i class="fa-solid fa-sync"></i> Sync Device Contacts</button>
        <div id="contacts-list"></div>
    </div>

    <!-- 3. SETTINGS -->
    <div id="view-settings" class="view">
        <div class="setting-box">
            <div><i class="fa-solid fa-coins" style="color: gold;"></i> <strong>{{ user.ygram_coins }} Coins</strong></div>
            <button class="btn">Buy</button>
        </div>
        <div class="setting-box" onclick="alert('Gift features available!')">
            <div><i class="fa-solid fa-gift" style="color: #10b981;"></i> <strong>Send Gift</strong></div>
        </div>
        
        <form action="/api/settings" method="POST">
            <div class="setting-box">
                <div>Number Visibility</div>
                <select name="number_visible" style="background:var(--bg-main); color:white;">
                    <option value="1" {% if user.number_visible %}selected{% endif %}>Everyone</option>
                    <option value="0" {% if not user.number_visible %}selected{% endif %}>No Body</option>
                </select>
            </div>
            <div class="setting-box">
                <div>App Color (PRO)</div>
                <input type="color" name="theme_color" value="{{ user.theme_color }}" {% if not user.is_premium %}disabled{% endif %}>
            </div>
            <button class="btn" style="width:100%;">Save Settings</button>
        </form>
        {% if user.is_admin %}
        <button class="btn" style="width:100%; margin-top: 15px; background: #3b82f6;" onclick="window.location.href='/admin'">Admin Panel</button>
        {% endif %}
    </div>

    <!-- 4. PROFILE -->
    <div id="view-profile" class="view" style="text-align: center;">
        <div class="avatar" style="width: 80px; height: 80px; margin: 0 auto 15px auto; font-size: 30px;">{{ user.display_name[0] }}</div>
        <form action="/api/profile" method="POST" style="text-align: left;">
            <label>Name</label><input type="text" name="display_name" value="{{ user.display_name }}" class="btn" style="background:var(--bg-header); width:100%; margin-bottom:10px;">
            <label>Username</label><input type="text" name="username" value="{{ user.username or '' }}" placeholder="@username" class="btn" style="background:var(--bg-header); width:100%; margin-bottom:10px;">
            <label>Bio</label><input type="text" name="bio" value="{{ user.bio }}" class="btn" style="background:var(--bg-header); width:100%; margin-bottom:10px;">
            <button class="btn" style="width:100%; margin-bottom:15px;">Update Profile</button>
        </form>
        <div style="display:flex; gap:10px;">
            <button class="btn" style="flex:1; background:#8b5cf6;" onclick="alert('Group Created!')"><i class="fa-solid fa-users"></i> Group</button>
            <button class="btn" style="flex:1; background:#ec4899;" onclick="alert('Channel Created!')"><i class="fa-solid fa-bullhorn"></i> Channel</button>
        </div>
        <button class="btn" style="width:100%; background:#ef4444; margin-top: 15px;" onclick="window.location.href='/logout'">Log Out</button>
    </div>
</div>

<!-- BOTTOM NAV -->
<div class="bottom-nav">
    <div class="nav-btn active" id="nav-chats" onclick="switchTab('chats')"><i class="fa-solid fa-message"></i> Chats</div>
    <div class="nav-btn" id="nav-contacts" onclick="switchTab('contacts')"><i class="fa-solid fa-address-book"></i> Contacts</div>
    <div class="nav-btn" id="nav-settings" onclick="switchTab('settings')"><i class="fa-solid fa-gear"></i> Settings</div>
    <div class="nav-btn" id="nav-profile" onclick="switchTab('profile')"><i class="fa-solid fa-user"></i> Profile</div>
</div>

<!-- CHAT ROOM UI -->
<div id="chat-ui">
    <div class="header" style="flex-direction: row; align-items: center; gap: 15px;">
        <i class="fa-solid fa-arrow-left" onclick="closeChat()" style="font-size: 20px; cursor: pointer;"></i>
        <h3 id="chat-title">Name</h3>
    </div>
    <div id="messages"></div>
    <div class="chat-input">
        <input type="text" id="msg-input" placeholder="Message..." onkeypress="if(event.key==='Enter') sendMsg()">
        <button class="btn" onclick="sendMsg()"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
</div>

<script>
    let activePeer = null;
    let timer = null;

    function switchTab(tab) {
        document.querySelectorAll('.view').forEach(e => e.classList.remove('active'));
        document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
        document.getElementById('view-' + tab).classList.add('active');
        document.getElementById('nav-' + tab).classList.add('active');
        if(tab === 'chats' || tab === 'contacts') fetchUsers();
    }

    async function fetchUsers(query='') {
        const res = await fetch('/api/users?q=' + query);
        const users = await res.json();
        let html = '';
        users.forEach(u => {
            let phoneStr = u.number_visible ? u.phone : 'Hidden Number';
            let nameStr = u.display_name + (u.is_premium ? ' ⭐' : '');
            html += `<div class="list-item" onclick="openChat('${u.phone}', '${u.display_name}')">
                        <div class="avatar">${u.display_name[0]}</div>
                        <div><strong>${nameStr}</strong><br><small style="color:var(--text-muted)">${u.username || phoneStr}</small></div>
                     </div>`;
        });
        document.getElementById('chat-list').innerHTML = html;
        document.getElementById('contacts-list').innerHTML = html;
    }

    function searchUsers() { fetchUsers(document.getElementById('search').value); }

    function openChat(phone, name) {
        activePeer = phone;
        document.getElementById('chat-title').innerText = name;
        document.getElementById('chat-ui').style.display = 'flex';
        loadMsg();
        timer = setInterval(loadMsg, 3000);
    }
    
    function closeChat() {
        document.getElementById('chat-ui').style.display = 'none';
        activePeer = null;
        clearInterval(timer);
    }

    async function loadMsg() {
        if(!activePeer) return;
        const res = await fetch('/api/messages/' + activePeer);
        const msgs = await res.json();
        const box = document.getElementById('messages');
        box.innerHTML = msgs.map(m => `<div class="msg ${m.sender_phone === '{{ session.phone }}' ? 'out' : 'in'}">${m.content}</div>`).join('');
        box.scrollTop = box.scrollHeight;
    }

    async function sendMsg() {
        const inp = document.getElementById('msg-input');
        if(!inp.value.trim()) return;
        await fetch('/api/send', { method: 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({receiver: activePeer, content: inp.value}) });
        inp.value = '';
        loadMsg();
    }

    async function postStory() {
        const res = await fetch('/api/story/check');
        const data = await res.json();
        if(data.allowed) {
            alert("Camera Opened! 📸 Posting Story...");
            await fetch('/api/story/post', {method: 'POST'});
        } else {
            alert(`Limit Reached! (Used: ${data.used}/${data.limit}). PRO users get 3/week, Free get 1/week.`);
        }
    }

    fetchUsers();
</script>
{% endif %}
</body></html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html><head><title>Admin Panel</title>
<style>
    body { background: #1a0505; color: white; font-family: sans-serif; padding: 20px; }
    .card { background: #2d0a0a; padding: 15px; margin-bottom: 20px; border: 1px solid #ff3333; }
    input, button { padding: 10px; margin: 5px; }
    button { background: #ff3333; color: white; border: none; cursor: pointer; }
</style></head><body>
    <h2>🛡️ Ygram Admin Dashboard</h2>
    <a href="/" style="color:white;">&larr; Back to App</a>
    
    <div class="card">
        <h3>Broadcast Message (Send as Ygram group)</h3>
        <form action="/admin/broadcast" method="POST">
            <input type="text" name="receiver" placeholder="Phone (or 'all')" required>
            <input type="text" name="message" placeholder="Message content..." required>
            <button type="submit">Send</button>
        </form>
    </div>

    <div class="card">
        <h3>User Management (Profile Delete/Chat)</h3>
        <table border="1" style="width:100%; border-collapse: collapse; border-color: #555;">
            <tr><th>Phone</th><th>Name</th><th>Action</th></tr>
            {% for u in users %}
            {% if u.phone != 'termux' %}
            <tr>
                <td>{{ u.phone }}</td><td>{{ u.display_name }}</td>
                <td>
                    <form action="/admin/delete/{{ u.phone }}" method="POST" style="display:inline;"><button>Delete Profile</button></form>
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
    </div>
</body></html>
"""

# --- Routes ---

@app.route('/')
def index():
    user = None
    if 'phone' in session:
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE phone=?", (session['phone'],)).fetchone()
            if user: session['is_premium'], session['theme_color'] = user['is_premium'], user['theme_color']
    return render_template_string(HTML_TEMPLATE, user=user)

@app.route('/login', methods=['POST'])
def login_page():
    phone = request.form.get('phone')
    password = request.form.get('password')
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE phone=? OR username=?", (phone, phone)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True  # One device, keeps logged in permanently
            session['phone'], session['display_name'] = user['phone'], user['display_name']
            if user['is_admin']: return redirect(url_for('admin_panel'))
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    phone, name, pwd = request.form.get('phone'), request.form.get('display_name'), generate_password_hash(request.form.get('password'))
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO users (phone, display_name, password_hash) VALUES (?, ?, ?)", (phone, name, pwd))
            conn.commit()
            session.permanent = True
            session['phone'], session['display_name'] = phone, name
    except: pass
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/users')
@login_required
def api_users():
    q = request.args.get('q', '').lower()
    with get_db() as conn:
        users = conn.execute("SELECT phone, display_name, username, is_premium, number_visible FROM users WHERE phone != ? AND is_banned=0 AND (LOWER(display_name) LIKE ? OR phone LIKE ? OR LOWER(username) LIKE ?)", (session['phone'], f'%{q}%', f'%{q}%', f'%{q}%')).fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/api/messages/<peer>')
@login_required
def api_messages(peer):
    with get_db() as conn:
        msgs = conn.execute("SELECT sender_phone, content FROM messages WHERE (sender_phone=? AND receiver_phone=?) OR (sender_phone=? AND receiver_phone=?) ORDER BY timestamp ASC", (session['phone'], peer, peer, session['phone'])).fetchall()
    return jsonify([dict(m) for m in msgs])

@app.route('/api/send', methods=['POST'])
@login_required
def api_send():
    data = request.json
    with get_db() as conn:
        conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", (session['phone'], data['receiver'], data['content']))
        conn.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/settings', methods=['POST'])
@login_required
def save_settings():
    vis, color = request.form.get('number_visible'), request.form.get('theme_color')
    with get_db() as conn:
        user = conn.execute("SELECT is_premium FROM users WHERE phone=?", (session['phone'],)).fetchone()
        if user['is_premium']: conn.execute("UPDATE users SET number_visible=?, theme_color=? WHERE phone=?", (vis, color, session['phone']))
        else: conn.execute("UPDATE users SET number_visible=? WHERE phone=?", (vis, session['phone']))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    name, user_n, bio = request.form.get('display_name'), request.form.get('username'), request.form.get('bio')
    if user_n and not user_n.startswith('@'): user_n = '@' + user_n
    try:
        with get_db() as conn:
            conn.execute("UPDATE users SET display_name=?, username=?, bio=? WHERE phone=?", (name, user_n, bio, session['phone']))
            conn.commit()
    except: pass
    return redirect(url_for('index'))

@app.route('/api/story/check')
@login_required
def check_story():
    with get_db() as conn:
        user = conn.execute("SELECT is_premium FROM users WHERE phone=?", (session['phone'],)).fetchone()
        limit = 3 if user['is_premium'] else 1
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        count = conn.execute("SELECT COUNT(*) FROM stories WHERE user_phone=? AND timestamp > ?", (session['phone'], week_ago)).fetchone()[0]
        return jsonify({'allowed': count < limit, 'used': count, 'limit': limit})

@app.route('/api/story/post', methods=['POST'])
@login_required
def post_story():
    with get_db() as conn:
        conn.execute("INSERT INTO stories (user_phone) VALUES (?)", (session['phone'],))
        conn.commit()
    return jsonify({'status': 'ok'})

# --- ADMIN ROUTES ---
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    with get_db() as conn:
        users = conn.execute("SELECT * FROM users").fetchall()
    return render_template_string(ADMIN_TEMPLATE, users=users)

@app.route('/admin/broadcast', methods=['POST'])
@login_required
@admin_required
def admin_broadcast():
    receiver, msg = request.form.get('receiver'), request.form.get('message')
    with get_db() as conn:
        if receiver.lower() == 'all':
            users = conn.execute("SELECT phone FROM users WHERE phone NOT IN ('termux', 'Ygram group')").fetchall()
            for u in users: conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", ('Ygram group', u['phone'], msg))
        else: conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", ('Ygram group', receiver, msg))
        conn.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete/<phone>', methods=['POST'])
@login_required
@admin_required
def admin_delete(phone):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE phone=?", (phone,))
        # የ Ygram group መልዕክት ይላክለት (Deleted account)
        conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", ('Ygram group', phone, 'Your profile has been deleted by Admin.'))
        conn.commit()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
