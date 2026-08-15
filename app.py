import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, session, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ygram_ultimate_secret_key_2026')
# Persistent session like Telegram (stays logged in for 1 year)
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
                bio TEXT DEFAULT 'Using Ygram Messenger',
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
        
        # Create Admin Account (termux / @Yosephalganeh44)
        admin = conn.execute("SELECT * FROM users WHERE phone = 'termux'").fetchone()
        if not admin:
            conn.execute(
                "INSERT INTO users (phone, username, password_hash, display_name, is_admin, is_premium, ygram_coins) VALUES (?, ?, ?, ?, 1, 1, 99999)",
                ('termux', '@admin', generate_password_hash('@Yosephalganeh44'), 'Ygram Boss')
            )
        
        # Create Ygram Official / Group System Account
        system = conn.execute("SELECT * FROM users WHERE phone = 'Ygram group'").fetchone()
        if not system:
            conn.execute(
                "INSERT INTO users (phone, username, password_hash, display_name, is_premium) VALUES (?, ?, ?, ?, 1)",
                ('Ygram group', '@ygram_official', generate_password_hash('system_secure_pass'), 'Ygram Official 🔵')
            )
        conn.commit()

init_db()

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'phone' not in session:
            return redirect(url_for('index'))
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE phone = ?", (session['phone'],)).fetchone()
            if not user or user['is_banned']:
                session.clear()
                return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('phone') != 'termux':
            return "Access Denied: Admin Only!", 403
        return f(*args, **kwargs)
    return decorated_function

# --- Single Unified HTML & CSS Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Ygram Messenger</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-main: #1a0505;
            --bg-header: #2d0a0a;
            --bg-nav: #1a0505;
            --accent: {{ session.get('theme_color', '#ff3333') }};
            --text-main: #ffffff;
            --text-muted: #ffb3b3;
            --divider: #3d1414;
            --gold: #f59e0b;
            --bubble-in: #3d1414;
            --bubble-out: var(--accent);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-main); color: var(--text-main); height: 100vh; overflow: hidden; display: flex; flex-direction: column; }

        /* Auth Screen */
        .auth-container { display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100vh; background: var(--bg-main); padding: 20px; }
        .auth-box { width: 100%; max-width: 400px; background: var(--bg-header); padding: 30px; border-radius: 12px; border: 1px solid var(--accent); box-shadow: 0 4px 20px rgba(255, 51, 51, 0.2); }
        .auth-box h2 { text-align: center; color: var(--accent); margin-bottom: 20px; }
        .auth-box input { width: 100%; padding: 14px; margin-bottom: 15px; background: var(--bg-main); border: 1px solid var(--divider); color: #fff; border-radius: 8px; outline: none; }
        .auth-box button { width: 100%; padding: 14px; background: var(--accent); color: #fff; border: none; border-radius: 8px; font-weight: bold; font-size: 16px; cursor: pointer; }

        /* App Header */
        .app-header { background: var(--bg-header); padding: 12px 16px; display: flex; flex-direction: column; gap: 10px; border-bottom: 1px solid var(--divider); }
        .header-top { display: flex; justify-content: space-between; align-items: center; }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .header-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--accent); display: flex; justify-content: center; align-items: center; font-weight: bold; overflow: hidden; }
        .header-title { font-size: 20px; font-weight: 600; }
        .header-right { display: flex; align-items: center; gap: 20px; font-size: 20px; color: var(--text-main); }
        
        /* Search Bar */
        .search-bar { background: var(--bg-main); display: flex; align-items: center; padding: 8px 12px; border-radius: 20px; border: 1px solid var(--divider); }
        .search-bar input { background: transparent; border: none; color: white; outline: none; width: 100%; margin-left: 10px; }

        /* Top Tabs for Chats */
        .top-tabs { background: var(--bg-header); display: flex; overflow-x: auto; border-bottom: 1px solid var(--divider); }
        .top-tabs::-webkit-scrollbar { display: none; }
        .tab-item { padding: 12px 16px; white-space: nowrap; color: var(--text-muted); font-weight: 500; font-size: 15px; cursor: pointer; }
        .tab-item.active { color: var(--accent); border-bottom: 3px solid var(--accent); }

        /* Content Area */
        .content-area { flex: 1; overflow-y: auto; background: var(--bg-main); position: relative; }
        .view-section { display: none; flex-direction: column; min-height: 100%; padding-bottom: 80px; }
        .view-section.active { display: flex; }

        /* Lists */
        .list-item { display: flex; align-items: center; padding: 12px 16px; gap: 15px; cursor: pointer; border-bottom: 1px solid var(--divider); }
        .list-item:active { background: var(--bg-header); }
        .list-avatar { width: 50px; height: 50px; border-radius: 50%; background: #6b1010; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; }
        .list-details { flex: 1; display: flex; flex-direction: column; justify-content: center; }
        .list-name { font-weight: 600; font-size: 16px; color: var(--text-main); display: flex; align-items: center; gap: 5px; }
        .list-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

        /* Floating Action Buttons */
        .fab-container { position: absolute; bottom: 20px; right: 20px; display: flex; flex-direction: column; gap: 15px; align-items: center; z-index: 100; }
        .fab-small { width: 45px; height: 45px; border-radius: 50%; background: var(--bg-header); color: var(--text-main); display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); cursor: pointer; border: 1px solid var(--accent); }
        .fab-large { width: 60px; height: 60px; border-radius: 50%; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 24px; box-shadow: 0 4px 15px rgba(255,51,51,0.4); cursor: pointer; }

        /* Bottom Navigation */
        .bottom-nav { background: var(--bg-nav); border-top: 1px solid var(--divider); display: flex; justify-content: space-around; padding: 10px 0 20px 0; z-index: 20; position: fixed; bottom: 0; width: 100%; }
        .nav-item { display: flex; flex-direction: column; align-items: center; gap: 4px; color: var(--text-muted); font-size: 11px; font-weight: 500; cursor: pointer; width: 25%; }
        .nav-item i { font-size: 22px; }
        .nav-item.active { color: var(--accent); }

        /* Settings & Profile Blocks */
        .setting-block { background: var(--bg-header); padding: 15px; margin: 10px 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--divider); }
        .form-input { width: calc(100% - 30px); margin: 0 15px 15px 15px; padding: 12px; background: var(--bg-main); border: 1px solid var(--divider); color: #fff; border-radius: 8px; }
        .btn-action { background: var(--accent); color: white; border: none; padding: 12px; border-radius: 8px; cursor: pointer; font-weight: bold; width: calc(100% - 30px); margin: 0 15px 10px 15px; text-align: center; display: block; text-decoration: none; }

        /* Chat Room Overlay */
        .chat-room { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: var(--bg-main); z-index: 200; display: none; flex-direction: column; }
        .room-header { background: var(--bg-header); padding: 12px 16px; display: flex; align-items: center; gap: 15px; border-bottom: 1px solid var(--divider); }
        .room-messages { flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; background: url('https://i.pinimg.com/originals/8f/ba/cb/8fbacbd464e996966eb9d4a6b7a9c21e.jpg') center/cover; }
        .bubble { max-width: 75%; padding: 10px 14px; border-radius: 16px; font-size: 15px; line-height: 1.4; word-wrap: break-word; }
        .bubble-in { background: var(--bubble-in); color: #fff; align-self: flex-start; }
        .bubble-out { background: var(--bubble-out); color: #fff; align-self: flex-end; }
        .room-input { background: var(--bg-header); padding: 10px 15px; display: flex; align-items: center; gap: 10px; }
        .room-input input { flex: 1; padding: 12px; border-radius: 20px; border: none; background: var(--bg-main); color: #fff; outline: none; }
        .room-input button { background: var(--accent); color: #fff; border: none; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; }

        /* Admin Panel Styles */
        .admin-card { background: var(--bg-header); padding: 15px; margin: 15px; border-radius: 8px; border: 1px solid var(--accent); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        th, td { border: 1px solid var(--divider); padding: 8px; text-align: left; }
    </style>
</head>
<body>

{% if not session.get('phone') %}
<!-- Login & Registration Screen -->
<div class="auth-container">
    <div class="auth-box">
        <h2><i class="fa-brands fa-telegram"></i> Ygram Red</h2>
        <form action="/login" method="POST" id="loginForm">
            <input type="text" name="phone" placeholder="Phone Number or Username (Admin: termux)" required>
            <input type="password" name="password" placeholder="Password (Admin: @Yosephalganeh44)" required>
            <button type="submit">Sign In</button>
            <div style="text-align: center; margin-top: 15px;">
                <a href="#" onclick="toggleAuth()" style="color: var(--accent); text-decoration: none;">Create New Account</a>
            </div>
        </form>

        <form action="/register" method="POST" id="regForm" style="display:none;">
            <input type="text" name="display_name" placeholder="Full Name" required>
            <input type="text" name="phone" placeholder="Phone Number (Unique ID)" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit" style="background: #10b981;">Register Account</button>
            <div style="text-align: center; margin-top: 15px;">
                <a href="#" onclick="toggleAuth()" style="color: var(--accent); text-decoration: none;">Back to Login</a>
            </div>
        </form>
    </div>
</div>
<script>
    function toggleAuth() {
        const l = document.getElementById('loginForm');
        const r = document.getElementById('regForm');
        l.style.display = l.style.display === 'none' ? 'block' : 'none';
        r.style.display = r.style.display === 'none' ? 'block' : 'none';
    }
</script>

{% else %}

{% if session.get('is_admin') and request.path == '/admin' %}
<!-- ADMIN PANEL VIEW -->
<div style="padding: 20px; overflow-y: auto; height: 100vh; padding-bottom: 60px;">
    <h2 style="color: var(--accent); margin-bottom: 15px;"><i class="fa-solid fa-shield-halved"></i> Ygram Admin Panel</h2>
    <a href="/" class="btn-action" style="background: #444; margin-bottom: 20px;">&larr; Back to Messenger</a>

    <div class="admin-card">
        <h3>Broadcast / Official Message</h3>
        <form action="/admin/broadcast" method="POST" style="margin-top: 10px;">
            <input type="text" class="form-input" name="receiver" placeholder="Receiver Phone or 'all'" required style="margin: 0 0 10px 0; width:100%;">
            <input type="text" class="form-input" name="message" placeholder="Type message as Ygram Official..." required style="margin: 0 0 10px 0; width:100%;">
            <button type="submit" class="btn-action" style="margin:0; width:100%;">Send Broadcast</button>
        </form>
    </div>

    <div class="admin-card">
        <h3>Pending Payments (Premium, Coins, Gifts)</h3>
        <table>
            <tr><th>Phone</th><th>Plan</th><th>Tx Ref</th><th>Action</th></tr>
            {% for p in admin_payments %}
            <tr>
                <td>{{ p.phone }}</td><td>{{ p.plan }}</td><td>{{ p.tx_ref }}</td>
                <td>
                    <form action="/admin/approve/{{ p.id }}" method="POST"><button style="background:green; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">Confirm</button></form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="admin-card">
        <h3>User Profile Management</h3>
        <table>
            <tr><th>Phone</th><th>Name</th><th>PRO</th><th>Coins</th><th>Action</th></tr>
            {% for u in admin_users %}
            {% if u.phone != 'termux' and u.phone != 'Ygram group' %}
            <tr>
                <td>{{ u.phone }}</td><td>{{ u.display_name }}</td><td>{{ 'Yes' if u.is_premium else 'No' }}</td><td>{{ u.ygram_coins }}</td>
                <td>
                    <form action="/admin/delete_user/{{ u.phone }}" method="POST" onsubmit="return confirm('Delete this user?');"><button style="background:red; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">Delete</button></form>
                </td>
            </tr>
            {% endif %}
            {% endfor %}
        </table>
    </div>
</div>

{% else %}

<!-- Main App Header -->
<header class="app-header">
    <div class="header-top">
        <div class="header-left">
            <div class="header-avatar">{{ session.get('display_name')[0] | upper }}</div>
            <div class="header-title">Ygram</div>
        </div>
        <div class="header-right">
            {% if session.get('phone') == 'termux' %}
            <a href="/admin" style="color: var(--gold); font-size: 18px;" title="Admin Panel"><i class="fa-solid fa-shield"></i></a>
            {% endif %}
            <i class="fa-solid fa-lock" onclick="alert('Device Secure & Locked')"></i>
            <i class="fa-solid fa-ellipsis-vertical" onclick="alert('Ygram Red Edition v2.6')"></i>
        </div>
    </div>
    <div class="search-bar">
        <i class="fa-solid fa-magnifying-glass" style="color: var(--text-muted);"></i>
        <input type="text" id="searchInput" placeholder="Search chats, @username, or phone..." oninput="searchApp()">
    </div>
</header>

<!-- Content Area (4 Views) -->
<div class="content-area">

    <!-- 1. CHATS VIEW -->
    <div id="view-chats" class="view-section active">
        <nav class="top-tabs">
            <div class="tab-item active">All</div>
            <div class="tab-item">Unread</div>
            <div class="tab-item">Private</div>
            <div class="tab-item">Groups</div>
        </nav>
        <div class="list-container" id="chatList"></div>

        <div class="fab-container">
            <div class="fab-small" onclick="postStory()" title="Camera / Story"><i class="fa-solid fa-camera"></i></div>
            <div class="fab-large" onclick="switchView('contacts', document.getElementById('nav-contacts'))" title="Plus / New Chat"><i class="fa-solid fa-plus"></i></div>
        </div>
    </div>

    <!-- 2. CONTACTS VIEW -->
    <div id="view-contacts" class="view-section">
        <div style="padding: 15px; font-weight: bold; color: var(--accent);">
            <i class="fa-solid fa-address-book"></i> Contacts & Plus Menu
        </div>
        <div style="padding: 0 15px 15px 15px;">
            <button class="btn-action" style="margin:0; width:100%;" onclick="syncContacts()"><i class="fa-solid fa-rotate"></i> Sync Device Phone Contacts</button>
        </div>
        <div class="list-container" id="contactList"></div>
    </div>

    <!-- 3. SETTINGS VIEW -->
    <div id="view-settings" class="view-section" style="padding-top: 10px;">
        <h3 style="color: var(--accent); margin: 15px;"><i class="fa-solid fa-gear"></i> Settings</h3>
        
        <div class="setting-block">
            <div><strong>Ygram Coins</strong><br><small style="color: var(--gold);"><i class="fa-solid fa-coins"></i> {{ coins }} Coins Balance</small></div>
            <button class="btn-action" style="width: auto; margin:0; background: var(--gold);" onclick="window.location.href='/upgrade'">Get Coins</button>
        </div>

        <div class="setting-block">
            <div><strong>PRO Version Status</strong><br><small>{{ 'Active PRO Member ⭐' if session.get('is_premium') else 'Free Account' }}</small></div>
            {% if not session.get('is_premium') %}
            <button class="btn-action" style="width: auto; margin:0;" onclick="window.location.href='/upgrade'">Upgrade</button>
            {% endif %}
        </div>

        <div class="setting-block" onclick="alert('Gift system: Send stickers and coins to friends instantly!')" style="cursor: pointer;">
            <div><strong>Gifts & Stickers</strong><br><small>Send custom gifts & emojis</small></div>
            <i class="fa-solid fa-gift" style="color: #10b981; font-size: 20px;"></i>
        </div>

        <form action="/api/update_settings" method="POST">
            <div class="setting-block">
                <div><strong>Phone Visibility</strong><br><small>Show number in search</small></div>
                <select name="number_visible" style="background: var(--bg-main); color: white; border: 1px solid var(--divider); padding: 5px; border-radius: 4px;">
                    <option value="1">Everyone</option>
                    <option value="0">Hidden</option>
                </select>
            </div>

            <div class="setting-block">
                <div><strong>Theme Color (PRO)</strong><br><small>Custom app color</small></div>
                <input type="color" name="theme_color" value="{{ session.get('theme_color', '#ff3333') }}" {% if not session.get('is_premium') %}disabled{% endif %}>
            </div>
            <button type="submit" class="btn-action">Save Settings</button>
        </form>
    </div>

    <!-- 4. PROFILE VIEW -->
    <div id="view-profile" class="view-section" style="padding-top: 10px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <div class="header-avatar" style="width: 90px; height: 90px; font-size: 36px; margin: 0 auto 10px auto;">{{ session.get('display_name')[0] | upper }}</div>
            <div style="font-weight: bold; font-size: 18px;">{{ session.get('display_name') }}</div>
            <div style="color: var(--text-muted); font-size: 13px;">{{ session.get('phone') }}</div>
        </div>

        <form action="/api/update_profile" method="POST">
            <label style="color: var(--text-muted); font-size: 12px; margin-left: 15px;">Display Name</label>
            <input type="text" class="form-input" name="display_name" value="{{ session.get('display_name') }}">
            
            <label style="color: var(--text-muted); font-size: 12px; margin-left: 15px;">Username (@)</label>
            <input type="text" class="form-input" name="username" value="{{ current_user_data.username if current_user_data else '' }}">
            
            <label style="color: var(--text-muted); font-size: 12px; margin-left: 15px;">Bio</label>
            <input type="text" class="form-input" name="bio" value="{{ current_user_data.bio if current_user_data else '' }}">
            
            <button type="submit" class="btn-action">Update Profile</button>
        </form>

        <div style="display: flex; gap: 10px; padding: 0 15px; margin-bottom: 10px;">
            <button class="btn-action" style="background: #3f51b5; margin:0;" onclick="createGroup(0)"><i class="fa-solid fa-users"></i> New Group</button>
            <button class="btn-action" style="background: #9c27b0; margin:0;" onclick="createGroup(1)"><i class="fa-solid fa-bullhorn"></i> New Channel</button>
        </div>

        <form action="/api/delete_my_account" method="POST" onsubmit="return confirm('Are you sure you want to delete your Ygram account?');">
            <button type="submit" class="btn-action" style="background: #eab308; color: black;"><i class="fa-solid fa-user-slash"></i> Delete Profile</button>
        </form>

        <a href="/logout" class="btn-action" style="background: #ef4444;"><i class="fa-solid fa-right-from-bracket"></i> Log Out</a>
    </div>

</div>

<!-- Bottom Navigation Bar -->
<nav class="bottom-nav">
    <div class="nav-item active" id="nav-chats" onclick="switchView('chats', this)"><i class="fa-solid fa-message"></i> Chats</div>
    <div class="nav-item" id="nav-contacts" onclick="switchView('contacts', this)"><i class="fa-regular fa-address-book"></i> Contacts</div>
    <div class="nav-item" id="nav-settings" onclick="switchView('settings', this)"><i class="fa-solid fa-gear"></i> Settings</div>
    <div class="nav-item" id="nav-profile" onclick="switchView('profile', this)"><i class="fa-solid fa-circle-user"></i> Profile</div>
</nav>

<!-- Chat Room Overlay -->
<div class="chat-room" id="chatRoom">
    <div class="room-header">
        <i class="fa-solid fa-arrow-left" style="font-size: 20px; cursor: pointer;" onclick="closeChat()"></i>
        <div class="header-avatar" id="chatRoomAvatar" style="width: 35px; height: 35px;"></div>
        <div>
            <div style="font-weight: 600; font-size: 16px;" id="chatRoomName">Name</div>
            <div style="font-size: 12px; color: var(--text-muted);">online</div>
        </div>
    </div>
    <div class="room-messages" id="messagesContainer"></div>
    <div class="room-input">
        <input type="text" id="messageInput" placeholder="Message..." onkeypress="if(event.key==='Enter') sendMsg()">
        <button onclick="sendMsg()"><i class="fa-solid fa-paper-plane"></i></button>
    </div>
</div>

<script>
    let activePeer = null;
    let pollInterval = null;

    function switchView(viewName, element) {
        document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
        document.getElementById('view-' + viewName).classList.add('active');
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        if(element) element.classList.add('active');
        
        if(viewName === 'chats') loadUsers('chatList');
        if(viewName === 'contacts') loadUsers('contactList');
    }

    async function loadUsers(containerId, query='') {
        const res = await fetch('/api/users?q=' + encodeURIComponent(query));
        const users = await res.json();
        const list = document.getElementById(containerId);
        if(!list) return;
        list.innerHTML = '';
        users.forEach(u => {
            const displaySub = u.username ? u.username : u.phone;
            list.innerHTML += `
            <div class="list-item" onclick="openChat('${u.phone}', '${u.display_name}', ${u.is_premium})">
                <div class="list-avatar">${u.display_name[0].toUpperCase()}</div>
                <div class="list-details">
                    <div class="list-name">${u.display_name} ${u.is_premium ? '<i class="fa-solid fa-star" style="color:var(--gold); font-size:12px;"></i>' : ''}</div>
                    <div class="list-sub">${displaySub} • ${u.bio}</div>
                </div>
            </div>`;
        });
    }

    function searchApp() {
        const q = document.getElementById('searchInput').value;
        loadUsers('chatList', q);
    }

    function syncContacts() {
        alert("Device Permissions Requested: Contacts synced successfully into Ygram!");
        loadUsers('contactList');
    }

    async function postStory() {
        const res = await fetch('/api/story/check');
        const data = await res.json();
        if(data.allowed) {
            alert(`Camera Opened 📸\nStory posted successfully! (${data.used + 1}/${data.limit} used this week)`);
            await fetch('/api/story/post', {method: 'POST'});
        } else {
            alert(`Story Limit Reached!\nFree Account: 1 story per week.\nPRO Account: 3 stories per week.\nUpgrade to PRO for more!`);
        }
    }

    function createGroup(isChannel) {
        const name = prompt(isChannel ? "Enter Channel Name:" : "Enter Group Name:");
        if(name) alert(isChannel ? "Channel created successfully!" : "Group created successfully!");
    }

    function openChat(phone, name, premium) {
        activePeer = phone;
        document.getElementById('chatRoom').style.display = 'flex';
        document.getElementById('chatRoomName').innerHTML = name + (premium ? ' <i class="fa-solid fa-star" style="color:var(--gold); font-size:10px;"></i>' : '');
        document.getElementById('chatRoomAvatar').innerText = name[0].toUpperCase();
        loadMessages();
        pollInterval = setInterval(loadMessages, 3000);
    }

    function closeChat() {
        document.getElementById('chatRoom').style.display = 'none';
        activePeer = null;
        clearInterval(pollInterval);
    }

    async function loadMessages() {
        if(!activePeer) return;
        const res = await fetch('/api/messages/' + activePeer);
        const msgs = await res.json();
        const container = document.getElementById('messagesContainer');
        container.innerHTML = '';
        msgs.forEach(m => {
            const isMe = m.sender_phone === '{{ session.phone }}';
            container.innerHTML += `<div class="bubble ${isMe ? 'bubble-out' : 'bubble-in'}">${m.content}</div>`;
        });
        container.scrollTop = container.scrollHeight;
    }

    async function sendMsg() {
        const input = document.getElementById('messageInput');
        const text = input.value.trim();
        if(!text || !activePeer) return;
        await fetch('/api/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({receiver_phone: activePeer, content: text})
        });
        input.value = '';
        loadMessages();
    }

    loadUsers('chatList');
</script>
{% endif %}
{% endif %}
</body>
</html>
"""

UPGRADE_TEMPLATE = """
<!DOCTYPE html>
<html><body style="background: #1a0505; color: white; font-family: sans-serif; text-align: center; padding: 40px;">
    <h1 style="color: #f59e0b;">Upgrade to Ygram PRO & Get Coins</h1>
    <p>Unlock custom themes, emojis, stickers, and 3 stories per week!</p>
    <div style="background: #2d0a0a; padding: 20px; border-radius: 10px; display: inline-block; margin: 20px 0; border: 1px solid #ff3333;">
        <p>USDT (BSC): <code style="color: #ff3333;">0x9084bb251960ef2c9fd5a569d32c5b2d7174e0f4</code></p>
        <p>Telebirr: <code style="color: #ff3333;">+251957786001</code></p>
    </div>
    <form action="/api/subscribe" method="POST">
        <select name="plan" style="padding: 10px; width: 300px; background: #2d0a0a; color: white; border: 1px solid #ff3333; border-radius: 5px; margin-bottom: 10px;">
            <option value="PRO 1 Month + 100 Coins">PRO 1 Month + 100 Coins ($5)</option>
            <option value="PRO 3 Months + 500 Coins">PRO 3 Months + 500 Coins ($12)</option>
        </select><br>
        <input type="text" name="tx_ref" placeholder="Paste Transaction Reference / Hash" required style="padding: 10px; width: 300px; background: #1a0505; color: white; border: 1px solid #ff3333; border-radius: 5px; margin-bottom: 20px;"><br>
        <button type="submit" style="padding: 12px 25px; background: #f59e0b; color: black; border: none; font-weight: bold; border-radius: 5px; cursor: pointer;">Submit Payment for Confirmation</button>
    </form>
    <br><a href="/" style="color: #ffb3b3; text-decoration: none;">&larr; Return to App</a>
</body></html>
"""

# --- Flask Server Routes ---

@app.route('/')
def index():
    current_user_data = None
    coins = 0
    admin_payments = []
    admin_users = []
    if 'phone' in session:
        with get_db() as conn:
            current_user_data = conn.execute("SELECT * FROM users WHERE phone=?", (session['phone'],)).fetchone()
            if current_user_data:
                session['is_premium'] = current_user_data['is_premium']
                session['theme_color'] = current_user_data['theme_color']
                coins = current_user_data['ygram_coins']
            if session['phone'] == 'termux':
                admin_payments = conn.execute("SELECT * FROM payments WHERE status='pending'").fetchall()
                admin_users = conn.execute("SELECT * FROM users").fetchall()
    return render_template_string(
        HTML_TEMPLATE, 
        current_user_data=current_user_data, 
        coins=coins, 
        admin_payments=admin_payments, 
        admin_users=admin_users
    )

@app.route('/login', methods=['POST'])
def login():
    phone = request.form.get('phone').strip()
    password = request.form.get('password')
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE phone = ? OR username = ?", (phone, phone)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True  # Keeps login session persistent like Telegram
            session['phone'] = user['phone']
            session['display_name'] = user['display_name']
            session['theme_color'] = user['theme_color']
            session['is_premium'] = user['is_premium']
            if user['is_admin']:
                return redirect(url_for('admin_panel'))
            return redirect(url_for('index'))
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    phone = request.form.get('phone').strip()
    password = generate_password_hash(request.form.get('password'))
    name = request.form.get('display_name').strip()
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO users (phone, password_hash, display_name) VALUES (?, ?, ?)", (phone, password, name))
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

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    return redirect(url_for('index'))

@app.route('/admin/approve/<int:pid>', methods=['POST'])
@login_required
@admin_required
def approve_payment(pid):
    with get_db() as conn:
        payment = conn.execute("SELECT * FROM payments WHERE id=?", (pid,)).fetchone()
        if payment:
            conn.execute("UPDATE users SET is_premium=1, ygram_coins=ygram_coins+100 WHERE phone=?", (payment['phone'],))
            conn.execute("UPDATE payments SET status='approved' WHERE id=?", (pid,))
            conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)",
                         ('Ygram group', payment['phone'], 'Congratulations! Your payment has been confirmed by Admin. PRO features & coins added! ⭐'))
            conn.commit()
    return redirect(url_for('index'))

@app.route('/admin/delete_user/<phone>', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(phone):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE phone=?", (phone,))
        conn.execute("DELETE FROM messages WHERE sender_phone=? OR receiver_phone=?", (phone, phone))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/admin/broadcast', methods=['POST'])
@login_required
@admin_required
def admin_broadcast():
    receiver = request.form.get('receiver').strip()
    message = request.form.get('message').strip()
    with get_db() as conn:
        if receiver.lower() == 'all':
            users = conn.execute("SELECT phone FROM users WHERE phone NOT IN ('termux', 'Ygram group')").fetchall()
            for u in users:
                conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", ('Ygram group', u['phone'], message))
        else:
            conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)", ('Ygram group', receiver, message))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/api/users')
@login_required
def api_users():
    q = request.args.get('q', '').lower()
    current_phone = session['phone']
    with get_db() as conn:
        if q:
            users = conn.execute("SELECT phone, display_name, username, bio, is_premium, number_visible FROM users WHERE phone != ? AND is_banned = 0 AND (LOWER(display_name) LIKE ? OR LOWER(username) LIKE ? OR phone LIKE ?)", (current_phone, f'%{q}%', f'%{q}%', f'%{q}%')).fetchall()
        else:
            users = conn.execute("SELECT phone, display_name, username, bio, is_premium, number_visible FROM users WHERE phone != ? AND is_banned = 0", (current_phone,)).fetchall()
    return jsonify([dict(u) for u in users])

@app.route('/api/messages/<peer>')
@login_required
def api_messages(peer):
    current = session['phone']
    with get_db() as conn:
        msgs = conn.execute('''SELECT sender_phone, receiver_phone, content FROM messages 
                               WHERE (sender_phone = ? AND receiver_phone = ?) OR (sender_phone = ? AND receiver_phone = ?) 
                               ORDER BY timestamp ASC''', (current, peer, peer, current)).fetchall()
    return jsonify([dict(m) for m in msgs])

@app.route('/api/send', methods=['POST'])
@login_required
def api_send():
    data = request.json
    with get_db() as conn:
        conn.execute("INSERT INTO messages (sender_phone, receiver_phone, content) VALUES (?, ?, ?)",
                     (session['phone'], data['receiver_phone'], data['content']))
        conn.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('display_name').strip()
    username = request.form.get('username').strip()
    bio = request.form.get('bio').strip()
    if username and not username.startswith('@'):
        username = '@' + username
    with get_db() as conn:
        try:
            conn.execute("UPDATE users SET display_name=?, username=?, bio=? WHERE phone=?", (name, username, bio, session['phone']))
            conn.commit()
            session['display_name'] = name
        except:
            pass
    return redirect(url_for('index'))

@app.route('/api/delete_my_account', methods=['POST'])
@login_required
def delete_my_account():
    phone = session['phone']
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE phone=?", (phone,))
        conn.execute("DELETE FROM messages WHERE sender_phone=? OR receiver_phone=?", (phone, phone))
        conn.commit()
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/update_settings', methods=['POST'])
@login_required
def update_settings():
    vis = request.form.get('number_visible')
    color = request.form.get('theme_color')
    with get_db() as conn:
        user = conn.execute("SELECT is_premium FROM users WHERE phone=?", (session['phone'],)).fetchone()
        if user['is_premium']:
            conn.execute("UPDATE users SET number_visible=?, theme_color=? WHERE phone=?", (vis, color, session['phone']))
            session['theme_color'] = color
        else:
            conn.execute("UPDATE users SET number_visible=? WHERE phone=?", (vis, session['phone']))
        conn.commit()
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

@app.route('/upgrade')
@login_required
def upgrade():
    return render_template_string(UPGRADE_TEMPLATE)

@app.route('/api/subscribe', methods=['POST'])
@login_required
def api_subscribe():
    plan = request.form.get('plan')
    tx_ref = request.form.get('tx_ref').strip()
    with get_db() as conn:
        conn.execute("INSERT INTO payments (phone, plan, tx_ref) VALUES (?, ?, ?)", (session['phone'], plan, tx_ref))
        conn.commit()
    return "Payment reference submitted successfully! The admin will confirm and activate your PRO status soon. <a href='/' style='color:#ff3333;'>Return to Ygram</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
