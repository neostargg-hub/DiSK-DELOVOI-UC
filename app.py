from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
import random
import string
import hashlib
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'd7f9a3e2b1c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2'

SITE_NAME = "DiSK Delovoi UC"

# ==================== БАЗА ДАННЫХ ====================
def get_db():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_num TEXT UNIQUE,
        user_name TEXT,
        user_phone TEXT,
        user_email TEXT,
        game_id TEXT,
        uc_amount INTEGER,
        uc_price INTEGER,
        status TEXT DEFAULT 'new',
        payment_proof TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_number TEXT,
        wallet_number TEXT,
        instruction TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS support_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT,
        user_email TEXT,
        message TEXT,
        status TEXT DEFAULT 'new',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM payments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO payments (card_number, wallet_number, instruction) VALUES (?, ?, ?)",
                      ('2200 1234 5678 9012', '+7 999 123-45-67', 'Оплатите на карту или кошелек'))
    
    conn.commit()
    conn.close()

# ==================== ЦЕНЫ ====================
UC_PRICES = {
    60: 78, 120: 154, 180: 230, 240: 306, 325: 380,
    385: 456, 445: 532, 660: 759, 720: 835, 985: 1137,
    1320: 1516, 1800: 1896, 1920: 2048, 2125: 2275, 2460: 2653,
    3850: 3787, 4510: 4544, 5650: 5681, 8100: 7528, 9900: 9671,
    11950: 11611, 16200: 15452, 24300: 23178, 32400: 30904,
    40500: 38630, 81000: 77259
}

def format_price(price):
    return f"{price:,}".replace(',', ' ')

def generate_order_num():
    return ''.join(random.choices(string.digits, k=12))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ==================== HTML ШАБЛОНЫ ====================
BASE_HTML = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ site_name }} - Покупка UC для PUBG Mobile</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        /* Летающие элементы */
        .floating {
            position: fixed;
            font-family: monospace;
            font-weight: bold;
            pointer-events: none;
            z-index: 0;
            animation: floatAnim 12s infinite ease-in-out;
        }
        
        @keyframes floatAnim {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.15; }
            80% { opacity: 0.15; }
            100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
        }
        
        /* Боковое меню */
        .menu-btn {
            position: fixed;
            top: 20px;
            left: 20px;
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 200;
            box-shadow: 0 5px 20px rgba(168,85,247,0.4);
            font-size: 24px;
        }
        
        .side-menu {
            position: fixed;
            top: 0;
            left: -280px;
            width: 280px;
            height: 100%;
            background: rgba(15, 12, 41, 0.98);
            backdrop-filter: blur(10px);
            z-index: 150;
            transition: left 0.3s ease;
            border-right: 1px solid rgba(168,85,247,0.3);
            padding: 80px 20px 30px;
        }
        
        .side-menu.open { left: 0; }
        
        .side-menu a {
            display: flex;
            align-items: center;
            gap: 12px;
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            padding: 12px 20px;
            border-radius: 12px;
            margin-bottom: 10px;
        }
        
        .side-menu a:hover { background: rgba(168,85,247,0.2); color: #c084fc; }
        
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 140;
            display: none;
        }
        
        .overlay.active { display: block; }
        
        .close-menu {
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 24px;
            cursor: pointer;
        }
        
        .navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            padding: 16px 32px;
            background: rgba(15, 12, 41, 0.9);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(168,85,247,0.3);
            text-align: center;
        }
        
        .logo {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff, #a855f7, #e879f9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .hero {
            padding: 120px 24px 70px;
            text-align: center;
            position: relative;
            z-index: 1;
        }
        
        .hero h1 {
            font-size: 56px;
            background: linear-gradient(135deg, #fff, #a855f7, #e879f9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        
        .hero p { font-size: 18px; color: rgba(255,255,255,0.7); }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 24px;
            position: relative;
            z-index: 1;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 25px;
            margin-bottom: 70px;
        }
        
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            border: 1px solid rgba(168,85,247,0.25);
            padding: 30px 20px;
            text-align: center;
            transition: 0.3s;
        }
        
        .card:hover { transform: translateY(-5px); border-color: #a855f7; }
        
        .card-icon { font-size: 48px; margin-bottom: 15px; }
        
        .catalog {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 70px;
        }
        
        .product {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            border: 1px solid rgba(168,85,247,0.25);
            padding: 28px;
            text-align: center;
        }
        
        .product:hover { transform: translateY(-5px); border-color: #a855f7; }
        
        .product-amount { font-size: 34px; font-weight: 700; color: #c084fc; margin-bottom: 10px; }
        .product-price { font-size: 26px; font-weight: 600; margin-bottom: 20px; }
        
        .btn {
            display: inline-block;
            padding: 12px 32px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border: none;
            border-radius: 50px;
            color: white;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: 0.3s;
        }
        
        .btn:hover { transform: scale(1.03); box-shadow: 0 8px 25px rgba(168,85,247,0.4); }
        
        .form-container {
            max-width: 550px;
            margin: 0 auto;
            padding: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 32px;
            border: 1px solid rgba(168,85,247,0.25);
        }
        
        .form-group { margin-bottom: 22px; }
        .form-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); }
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 14px 16px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(168,85,247,0.3);
            border-radius: 18px;
            color: white;
            font-size: 15px;
        }
        .form-group input:focus { outline: none; border-color: #a855f7; }
        
        .payment-info {
            background: rgba(168,85,247,0.1);
            border-radius: 20px;
            padding: 24px;
            margin: 25px 0;
            border: 1px solid rgba(168,85,247,0.3);
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 24px;
            padding: 24px;
            text-align: center;
        }
        
        .stat-number { font-size: 38px; font-weight: 700; color: #c084fc; }
        
        .admin-actions { display: flex; gap: 15px; justify-content: center; margin-bottom: 40px; flex-wrap: wrap; }
        
        .orders-table {
            background: rgba(255,255,255,0.05);
            border-radius: 24px;
            padding: 24px;
            overflow-x: auto;
        }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 14px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
        th { color: #c084fc; }
        
        .flash {
            padding: 16px;
            border-radius: 18px;
            margin-bottom: 25px;
            background: rgba(168,85,247,0.15);
            border: 1px solid rgba(168,85,247,0.35);
            text-align: center;
        }
        
        .footer {
            text-align: center;
            padding: 40px 24px;
            border-top: 1px solid rgba(168,85,247,0.15);
            margin-top: 80px;
            color: rgba(255,255,255,0.4);
        }
        
        /* Чат */
        .chat-widget {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 200;
        }
        
        .chat-btn {
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 5px 25px rgba(168,85,247,0.5);
            font-size: 26px;
        }
        
        .chat-window {
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 350px;
            height: 450px;
            background: rgba(15,12,41,0.98);
            border-radius: 28px;
            border: 1px solid rgba(168,85,247,0.35);
            display: none;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-window.open { display: flex; }
        
        .chat-header {
            padding: 18px;
            background: rgba(168,85,247,0.15);
            border-bottom: 1px solid rgba(168,85,247,0.3);
            display: flex;
            justify-content: space-between;
        }
        
        .chat-msgs { flex: 1; padding: 16px; overflow-y: auto; }
        
        .msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 18px; max-width: 85%; }
        .msg.user { background: linear-gradient(135deg, #a855f7, #e879f9); margin-left: auto; }
        .msg.support { background: rgba(255,255,255,0.1); margin-right: auto; }
        
        .chat-input {
            display: flex;
            padding: 16px;
            border-top: 1px solid rgba(168,85,247,0.25);
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 12px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(168,85,247,0.3);
            border-radius: 25px;
            color: white;
        }
        
        .chat-input button {
            padding: 10px 18px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border: none;
            border-radius: 25px;
            color: white;
            cursor: pointer;
        }
        
        @media (max-width: 768px) {
            .hero h1 { font-size: 36px; }
            .features { grid-template-columns: 1fr; }
            .stats { grid-template-columns: 1fr; }
            .catalog { grid-template-columns: 1fr; }
            .chat-window { width: 300px; right: -10px; }
        }
        
        select, option { background: #1e1b4b; color: white; }
    </style>
</head>
<body>
    <div class="menu-btn" onclick="toggleMenu()">☰</div>
    
    <div class="side-menu" id="sideMenu">
        <div class="close-menu" onclick="toggleMenu()">✕</div>
        <a href="/">🏠 Главная</a>
        <a href="/catalog">🛒 Каталог UC</a>
        <a href="/check">🔍 Проверить заказ</a>
        <a href="/support">💬 Поддержка</a>
        <hr style="margin: 10px 0; border-color: rgba(168,85,247,0.3);">
        <a href="/admin">👑 Админ-панель</a>
    </div>
    
    <div class="overlay" id="overlay" onclick="toggleMenu()"></div>
    
    <nav class="navbar">
        <div class="logo">✨ DiSK Delovoi UC ✨</div>
    </nav>
    
    <div id="animatedBg"></div>
    
    <div class="hero">
        <h1>🛡️ DiSK Delovoi UC</h1>
        <p>Безопасная покупка UC для PUBG Mobile</p>
    </div>
    
    <div class="container">
        <div class="features">
            <div class="card"><div class="card-icon">🔒</div><h3>100% Безопасность</h3><p>Гарантия получения UC</p></div>
            <div class="card"><div class="card-icon">⚡</div><h3>Мгновенная доставка</h3><p>UC приходят сразу</p></div>
            <div class="card"><div class="card-icon">💰</div><h3>Лучшие цены</h3><p>Низкие цены на рынке</p></div>
            <div class="card"><div class="card-icon">🌐</div><h3>Поддержка 24/7</h3><p>Поможем в любой ситуации</p></div>
        </div>
        
        <div style="text-align: center; margin-bottom: 60px;">
            <a href="/catalog" class="btn">🚀 Перейти в каталог UC</a>
        </div>
        
        <div class="card" style="padding: 40px; text-align: center;">
            <h3>🔍 Проверить статус заказа</h3>
            <form method="post" action="/check-order" style="max-width: 400px; margin: 20px auto 0;">
                <div class="form-group">
                    <input type="text" name="order_num" placeholder="Введите номер заказа" required>
                </div>
                <button type="submit" class="btn">Проверить</button>
            </form>
        </div>
    </div>
    
    <div class="chat-widget">
        <div class="chat-btn" onclick="toggleChat()">💬</div>
        <div class="chat-window" id="chatWindow">
            <div class="chat-header">
                <strong>💬 Поддержка</strong>
                <span onclick="toggleChat()" style="cursor:pointer;">✕</span>
            </div>
            <div class="chat-msgs" id="chatMsgs">
                <div class="msg support">👋 Здравствуйте! Чем могу помочь?</div>
            </div>
            <div class="chat-input">
                <input type="text" id="chatInput" placeholder="Введите сообщение..." onkeypress="if(event.key==='Enter') sendMsg()">
                <button onclick="sendMsg()">📨</button>
            </div>
        </div>
    </div>
    
    <div class="footer">
        <p>© 2024 DiSK Delovoi UC. Все права защищены.</p>
        <p>⚡ Киберпространство ждёт тебя | UC для PUBG Mobile</p>
    </div>
    
    <script>
        // Летающие элементы
        const items = ['U', 'C', 'UC', '60', '120', '180', '325', '660', '1320', '1800', '3850', '8100', '▲', '●', '◆'];
        
        for (let i = 0; i < 40; i++) {
            const el = document.createElement('div');
            el.className = 'floating';
            el.innerHTML = items[Math.floor(Math.random() * items.length)];
            el.style.left = Math.random() * 100 + '%';
            el.style.fontSize = (Math.random() * 35 + 20) + 'px';
            el.style.animationDelay = Math.random() * 10 + 's';
            el.style.animationDuration = (Math.random() * 10 + 8) + 's';
            el.style.opacity = Math.random() * 0.2 + 0.1;
            el.style.color = ['#a855f7', '#e879f9', '#c084fc'][Math.floor(Math.random() * 3)];
            document.getElementById('animatedBg').appendChild(el);
        }
        
        function toggleMenu() {
            document.getElementById('sideMenu').classList.toggle('open');
            document.getElementById('overlay').classList.toggle('active');
        }
        
        function toggleChat() {
            document.getElementById('chatWindow').classList.toggle('open');
        }
        
        function sendMsg() {
            const input = document.getElementById('chatInput');
            const msg = input.value.trim();
            if (!msg) return;
            
            const msgsDiv = document.getElementById('chatMsgs');
            const userMsg = document.createElement('div');
            userMsg.className = 'msg user';
            userMsg.innerHTML = msg;
            msgsDiv.appendChild(userMsg);
            
            fetch('/support/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'message=' + encodeURIComponent(msg)
            });
            
            const replyMsg = document.createElement('div');
            replyMsg.className = 'msg support';
            replyMsg.innerHTML = '✅ Спасибо! Мы ответим вам.';
            msgsDiv.appendChild(replyMsg);
            
            input.value = '';
            msgsDiv.scrollTop = msgsDiv.scrollHeight;
        }
    </script>
</body>
</html>
'''

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    return render_template_string(BASE_HTML, site_name=SITE_NAME)

@app.route('/catalog')
def catalog():
    items = ''
    for amount, price in UC_PRICES.items():
        items += f'''
        <div class="product">
            <div class="product-amount">{amount} UC</div>
            <div class="product-price">{format_price(price)} ₽</div>
            <a href="/order/{amount}" class="btn">Купить</a>
        </div>
        '''
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Каталог UC - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 1400px; margin: 0 auto; padding: 100px 24px 70px; }
            .catalog { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; }
            .product {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 24px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 28px;
                text-align: center;
                transition: 0.3s;
            }
            .product:hover { transform: translateY(-5px); border-color: #a855f7; }
            .product-amount { font-size: 34px; font-weight: 700; color: #c084fc; margin-bottom: 10px; }
            .product-price { font-size: 26px; font-weight: 600; margin-bottom: 20px; }
            .btn {
                display: inline-block;
                padding: 12px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
                transition: 0.3s;
            }
            .btn:hover { transform: scale(1.03); }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
            @media (max-width: 768px) { .catalog { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="catalog">''' + items + '''</div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
    </body>
    </html>
    ''')

@app.route('/order/<int:amount>', methods=['GET', 'POST'])
def order(amount):
    if amount not in UC_PRICES:
        return redirect(url_for('catalog'))
    
    price = UC_PRICES[amount]
    
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        user_phone = request.form.get('user_phone')
        user_email = request.form.get('user_email')
        game_id = request.form.get('game_id')
        
        if not all([user_name, user_phone, game_id]):
            return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><title>Ошибка</title><link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
            <style>body{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#0f0c29,#1a1a3e,#24243e);color:#fff;display:flex;justify-content:center;align-items:center;height:100vh;}</style>
            </head>
            <body><div style="text-align:center;background:rgba(255,255,255,0.05);padding:40px;border-radius:24px;"><h2>❌ Ошибка</h2><p>Пожалуйста, заполните все обязательные поля!</p><a href="/order/''' + str(amount) + '''" class="btn" style="display:inline-block;padding:12px 32px;background:linear-gradient(135deg,#a855f7,#e879f9);border-radius:50px;color:white;text-decoration:none;margin-top:20px;">← Назад</a></div></body>
            </html>
            ''')
        
        order_num = generate_order_num()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO orders (order_num, user_name, user_phone, user_email, game_id, uc_amount, uc_price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
        ''', (order_num, user_name, user_phone, user_email, game_id, amount, price))
        conn.commit()
        conn.close()
        
        return redirect(url_for('payment', order_num=order_num))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Оформление заказа - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 550px; margin: 0 auto; padding: 100px 24px 70px; }
            .form-container {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 40px;
            }
            .product-amount { font-size: 34px; font-weight: 700; color: #c084fc; text-align: center; margin-bottom: 10px; }
            .product-price { font-size: 26px; font-weight: 600; text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 22px; }
            .form-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); }
            .form-group input {
                width: 100%;
                padding: 14px 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 18px;
                color: white;
                font-size: 15px;
            }
            .form-group input:focus { outline: none; border-color: #a855f7; }
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
                width: 100%;
                font-size: 16px;
            }
            .btn:hover { transform: scale(1.02); }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="form-container">
                <div class="product-amount">''' + str(amount) + ''' UC</div>
                <div class="product-price">''' + format_price(price) + ''' ₽</div>
                <form method="post">
                    <div class="form-group"><label>👤 Ваше имя *</label><input type="text" name="user_name" required placeholder="Иван Иванов"></div>
                    <div class="form-group"><label>📞 Телефон *</label><input type="tel" name="user_phone" required placeholder="+7 999 123-45-67"></div>
                    <div class="form-group"><label>📧 Email</label><input type="email" name="user_email" placeholder="ivan@example.com"></div>
                    <div class="form-group"><label>🎮 PUBG ID *</label><input type="text" name="game_id" required placeholder="Введите ваш игровой ID"></div>
                    <button type="submit" class="btn">✅ Перейти к оплате</button>
                </form>
            </div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
    </body>
    </html>
    ''')

@app.route('/payment/<order_num>')
def payment(order_num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_num=?", (order_num,))
    order = cursor.fetchone()
    cursor.execute("SELECT card_number, wallet_number, instruction FROM payments LIMIT 1")
    payment = cursor.fetchone()
    conn.close()
    
    if not order:
        return redirect(url_for('catalog'))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Оплата заказа - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 550px; margin: 0 auto; padding: 100px 24px 70px; }
            .form-container {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 40px;
            }
            .product-amount { font-size: 34px; font-weight: 700; color: #c084fc; text-align: center; margin-bottom: 10px; }
            .product-price { font-size: 26px; font-weight: 600; text-align: center; margin-bottom: 10px; }
            .payment-info {
                background: rgba(168,85,247,0.1);
                border-radius: 20px;
                padding: 24px;
                margin: 25px 0;
                border: 1px solid rgba(168,85,247,0.3);
            }
            .form-group { margin-bottom: 22px; }
            .form-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); }
            .form-group input, .form-group textarea {
                width: 100%;
                padding: 14px 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 18px;
                color: white;
                font-size: 15px;
            }
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
                width: 100%;
                font-size: 16px;
            }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
            .warning { color: #f472b6; margin-top: 16px; text-align: center; }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="form-container">
                <div class="product-amount">''' + str(order['uc_amount']) + ''' UC</div>
                <div class="product-price">''' + format_price(order['uc_price']) + ''' ₽</div>
                <p style="text-align:center;"><i class="fas fa-gamepad"></i> ID: ''' + order['game_id'] + '''</p>
                <p style="text-align:center;">📦 Заказ #''' + order_num + '''</p>
                
                <div class="payment-info">
                    <h3 style="margin-bottom: 16px;">💳 Реквизиты для оплаты</h3>
                    <p><strong>Карта:</strong> ''' + (payment['card_number'] or 'Не указана') + '''</p>
                    <p><strong>Кошелек:</strong> ''' + (payment['wallet_number'] or 'Не указан') + '''</p>
                    <p><strong>Инструкция:</strong> ''' + (payment['instruction'] or 'Оплатите на реквизиты') + '''</p>
                    <p class="warning">⚠️ Важно: Переведите точную сумму ''' + format_price(order['uc_price']) + ''' ₽</p>
                </div>
                
                <form method="post" action="/payment-proof/''' + order_num + '''" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>📎 Прикрепите чек (скриншот или фото)</label>
                        <input type="file" name="proof_file" accept="image/*">
                    </div>
                    <div class="form-group">
                        <label>✏️ Или введите текст подтверждения</label>
                        <textarea name="proof_text" rows="3" placeholder="Номер транзакции, дата, сумма..."></textarea>
                    </div>
                    <button type="submit" class="btn">📨 Отправить чек</button>
                </form>
            </div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
        <script src="https://kit.fontawesome.com/a2b8d7c8c1.js" crossorigin="anonymous"></script>
    </body>
    </html>
    ''')

@app.route('/payment-proof/<order_num>', methods=['POST'])
def payment_proof(order_num):
    proof_text = request.form.get('proof_text', 'Чек отправлен')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET payment_proof=?, status='waiting_confirm' WHERE order_num=?", 
                  (proof_text, order_num))
    conn.commit()
    conn.close()
    
    return redirect(url_for('order_status', order_num=order_num))

@app.route('/status/<order_num>')
def order_status(order_num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_num=?", (order_num,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        return redirect(url_for('catalog'))
    
    status_text = "🆕 Новый" if order['status'] == 'new' else "⏳ Ожидает" if order['status'] == 'waiting_confirm' else "✅ Завершен" if order['status'] == 'completed' else "❌ Отменен"
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Статус заказа - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 550px; margin: 0 auto; padding: 100px 24px 70px; }
            .card {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 40px;
                text-align: center;
            }
            .product-amount { font-size: 34px; font-weight: 700; color: #c084fc; margin-bottom: 10px; }
            .product-price { font-size: 26px; font-weight: 600; margin-bottom: 20px; }
            .status-box { margin: 25px 0; padding: 15px; border-radius: 20px; background: rgba(168,85,247,0.1); }
            .btn {
                display: inline-block;
                padding: 12px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                text-decoration: none;
                margin-top: 20px;
            }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="card">
                <div class="product-amount">''' + str(order['uc_amount']) + ''' UC</div>
                <div class="product-price">''' + format_price(order['uc_price']) + ''' ₽</div>
                <p><i class="fas fa-gamepad"></i> ID: ''' + order['game_id'] + '''</p>
                <p><i class="fas fa-calendar"></i> ''' + order['created_at'][:19] + '''</p>
                <div class="status-box"><strong>Статус:</strong> ''' + status_text + '''</div>
                <a href="/catalog" class="btn">🛒 Продолжить покупки</a>
            </div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
        <script src="https://kit.fontawesome.com/a2b8d7c8c1.js" crossorigin="anonymous"></script>
    </body>
    </html>
    ''')

@app.route('/check-order', methods=['POST'])
def check_order():
    order_num = request.form.get('order_num')
    return redirect(url_for('order_status', order_num=order_num))

@app.route('/check')
def check_page():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Проверка заказа - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 550px; margin: 0 auto; padding: 100px 24px 70px; }
            .form-container {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 40px;
            }
            .form-group { margin-bottom: 22px; }
            .form-group input {
                width: 100%;
                padding: 14px 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 18px;
                color: white;
                font-size: 15px;
            }
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
                width: 100%;
                font-size: 16px;
            }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="form-container">
                <h2 style="text-align:center; margin-bottom:30px;">🔍 Проверка заказа</h2>
                <form method="post" action="/check-order">
                    <div class="form-group">
                        <input type="text" name="order_num" placeholder="Номер заказа" required>
                    </div>
                    <button type="submit" class="btn">Проверить</button>
                </form>
            </div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
    </body>
    </html>
    ''')

@app.route('/support')
def support_page():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Поддержка - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 550px; margin: 0 auto; padding: 100px 24px 70px; }
            .form-container {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 40px;
            }
            .form-group { margin-bottom: 22px; }
            .form-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); }
            .form-group input, .form-group textarea {
                width: 100%;
                padding: 14px 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 18px;
                color: white;
                font-size: 15px;
            }
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
                width: 100%;
                font-size: 16px;
            }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="form-container">
                <h2 style="text-align:center; margin-bottom:30px;">💬 Служба поддержки</h2>
                <form method="post" action="/support/send-form">
                    <div class="form-group"><label>👤 Ваше имя</label><input type="text" name="user_name" required></div>
                    <div class="form-group"><label>📧 Email</label><input type="email" name="user_email" required></div>
                    <div class="form-group"><label>💬 Сообщение</label><textarea name="message" rows="5" required></textarea></div>
                    <button type="submit" class="btn">📨 Отправить</button>
                </form>
            </div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
    </body>
    </html>
    ''')

@app.route('/support/send', methods=['POST'])
def send_support_message():
    message = request.form.get('message', '')
    if message:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO support_messages (user_name, user_email, message) VALUES (?, ?, ?)",
                      ('Чат пользователь', 'chat@user.com', message))
        conn.commit()
        conn.close()
    return '', 200

@app.route('/support/send-form', methods=['POST'])
def send_support_form():
    user_name = request.form.get('user_name')
    user_email = request.form.get('user_email')
    message = request.form.get('message')
    
    if all([user_name, user_email, message]):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO support_messages (user_name, user_email, message) VALUES (?, ?, ?)",
                      (user_name, user_email, message))
        conn.commit()
        conn.close()
    
    return redirect(url_for('support_page'))

# ==================== АДМИН-ПАНЕЛЬ ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Неверный логин или пароль!'
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Вход в админ-панель</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .form-container {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 40px;
                width: 400px;
            }
            h2 { text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 22px; }
            .form-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); }
            .form-group input {
                width: 100%;
                padding: 14px 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 18px;
                color: white;
                font-size: 15px;
            }
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                font-size: 16px;
            }
            .error { background: rgba(239,68,68,0.2); border: 1px solid rgba(239,68,68,0.3); padding: 12px; border-radius: 16px; margin-bottom: 20px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h2>👑 Вход в админ-панель</h2>
            ''' + (f'<div class="error">{error}</div>' if error else '') + '''
            <form method="post">
                <div class="form-group"><label>Логин</label><input type="text" name="username" required></div>
                <div class="form-group"><label>Пароль</label><input type="password" name="password" required></div>
                <button type="submit" class="btn">Войти</button>
            </form>
        </div>
    </body>
    </html>
    ''')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='new'")
    new_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='completed'")
    completed_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(uc_price) FROM orders WHERE status='completed'")
    total_income = cursor.fetchone()[0] or 0
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    orders = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM support_messages WHERE status='new'")
    new_messages = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM support_messages ORDER BY created_at DESC")
    messages = cursor.fetchall()
    conn.close()
    
    orders_html = ''
    for order in orders:
        status_class = 'Новый' if order['status'] == 'new' else 'Ожидает' if order['status'] == 'waiting_confirm' else 'Завершен' if order['status'] == 'completed' else 'Отменен'
        orders_html += f'''
        <tr>
            <td>{order['order_num']}</td>
            <td>{order['user_name']}</td>
            <td>{order['uc_amount']}</td>
            <td>{format_price(order['uc_price'])} ₽</td>
            <td>{status_class}</td>
            <td>
                <form method="post" action="/admin/order/{order['id']}" style="display: flex; gap: 8px;">
                    <select name="status">
                        <option value="new">Новый</option>
                        <option value="waiting_confirm">Ожидает</option>
                        <option value="completed">Завершен</option>
                        <option value="cancelled">Отменен</option>
                    </select>
                    <button type="submit" class="btn" style="padding: 6px 16px;">Обновить</button>
                </form>
            </td>
        </tr>
        '''
    
    messages_html = ''
    for msg in messages:
        messages_html += f'''
        <tr>
            <td>{msg['created_at'][:16]}</td>
            <td>{msg['user_name']}</td>
            <td>{msg['user_email']}</td>
            <td>{msg['message'][:80]}...</td>
            <td>{"🆕 Новое" if msg['status'] == 'new' else "✅ Прочитано"}</td>
        </tr>
        '''
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Админ-панель - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 1400px; margin: 0 auto; padding: 100px 24px 70px; }
            .stats {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin-bottom: 40px;
            }
            .stat-card {
                background: rgba(255,255,255,0.05);
                border-radius: 24px;
                padding: 24px;
                text-align: center;
            }
            .stat-number { font-size: 38px; font-weight: 700; color: #c084fc; }
            .admin-actions { display: flex; gap: 15px; justify-content: center; margin-bottom: 40px; }
            .btn {
                display: inline-block;
                padding: 10px 24px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                text-decoration: none;
                cursor: pointer;
            }
            .btn-outline { background: transparent; border: 1px solid rgba(168,85,247,0.5); }
            .orders-table {
                background: rgba(255,255,255,0.05);
                border-radius: 24px;
                padding: 24px;
                overflow-x: auto;
                margin-bottom: 30px;
            }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 14px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); }
            th { color: #c084fc; }
            select, option { background: #1e1b4b; color: white; padding: 6px 12px; border-radius: 12px; }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
            @media (max-width: 768px) { .stats { grid-template-columns: 1fr; } }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="stats">
                <div class="stat-card"><div class="stat-number">''' + str(total_orders) + '''</div><p>Всего заказов</p></div>
                <div class="stat-card"><div class="stat-number">''' + str(new_orders) + '''</div><p>Новых заказов</p></div>
                <div class="stat-card"><div class="stat-number">''' + str(completed_orders) + '''</div><p>Завершено</p></div>
                <div class="stat-card"><div class="stat-number">''' + format_price(total_income) + ''' ₽</div><p>Оборот</p></div>
            </div>
            
            <div class="admin-actions">
                <a href="/admin/payments" class="btn btn-outline">💳 Реквизиты</a>
                <a href="/admin/logout" class="btn btn-outline">🚪 Выйти</a>
            </div>
            
            <div class="orders-table">
                <h3 style="margin-bottom: 20px;">📋 Заказы</h3>
                <table><thead><tr><th>№</th><th>Покупатель</th><th>UC</th><th>Сумма</th><th>Статус</th><th>Действия</th></tr></thead>
                <tbody>''' + orders_html + '''</tbody></table>
            </div>
            
            <div class="orders-table">
                <h3 style="margin-bottom: 20px;">💬 Сообщения поддержки <span class="badge" style="background:#e879f9;padding:2px 8px;border-radius:20px;margin-left:10px;">''' + str(new_messages) + '''</span></h3>
                <table><thead><tr><th>Дата</th><th>Имя</th><th>Email</th><th>Сообщение</th><th>Статус</th></tr></thead>
                <tbody>''' + messages_html + '''</tbody></table>
            </div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
    </body>
    </html>
    ''')

@app.route('/admin/order/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    new_status = request.form.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/payments', methods=['GET', 'POST'])
@admin_required
def admin_payments():
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        card_number = request.form.get('card_number')
        wallet_number = request.form.get('wallet_number')
        instruction = request.form.get('instruction')
        cursor.execute("UPDATE payments SET card_number=?, wallet_number=?, instruction=?", 
                      (card_number, wallet_number, instruction))
        conn.commit()
    
    cursor.execute("SELECT card_number, wallet_number, instruction FROM payments LIMIT 1")
    payment = cursor.fetchone()
    conn.close()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Реквизиты - DiSK Delovoi UC</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                color: #fff;
            }
            .navbar {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                padding: 16px 32px;
                background: rgba(15,12,41,0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(168,85,247,0.3);
                text-align: center;
                z-index: 100;
            }
            .logo { font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #fff, #a855f7, #e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .container { max-width: 550px; margin: 0 auto; padding: 100px 24px 70px; }
            .form-container {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.25);
                padding: 40px;
            }
            .form-group { margin-bottom: 22px; }
            .form-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); }
            .form-group input, .form-group textarea {
                width: 100%;
                padding: 14px 16px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 18px;
                color: white;
                font-size: 15px;
            }
            .btn {
                display: inline-block;
                padding: 14px 32px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 50px;
                color: white;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                font-size: 16px;
            }
            .footer { text-align: center; padding: 40px 24px; border-top: 1px solid rgba(168,85,247,0.15); margin-top: 80px; color: rgba(255,255,255,0.4); }
        </style>
    </head>
    <body>
        <nav class="navbar"><div class="logo">✨ DiSK Delovoi UC ✨</div></nav>
        <div class="container">
            <div class="form-container">
                <h2 style="text-align:center; margin-bottom:30px;">💳 Настройка реквизитов</h2>
                <form method="post">
                    <div class="form-group"><label>Номер карты</label><input type="text" name="card_number" value="''' + (payment['card_number'] or '') + '''" placeholder="1234 5678 9012 3456"></div>
                    <div class="form-group"><label>Номер кошелька</label><input type="text" name="wallet_number" value="''' + (payment['wallet_number'] or '') + '''" placeholder="+7 999 123-45-67"></div>
                    <div class="form-group"><label>Инструкция</label><textarea name="instruction" rows="4">''' + (payment['instruction'] or '') + '''</textarea></div>
                    <button type="submit" class="btn">💾 Сохранить</button>
                </form>
                <div style="text-align:center; margin-top:20px;"><a href="/admin" style="color:rgba(255,255,255,0.7);">← Назад</a></div>
            </div>
        </div>
        <div class="footer"><p>© 2024 DiSK Delovoi UC. Все права защищены.</p></div>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
