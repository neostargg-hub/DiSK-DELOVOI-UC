from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
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
    
    # Таблица заказов
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
        status TEXT DEFAULT 'waiting_seller',
        payment_proof TEXT,
        seller_id INTEGER,
        seller_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP
    )
    ''')
    
    # Таблица продавцов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sellers (
        id INTEGER PRIMARY KEY,
        name TEXT,
        username TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица реквизитов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_number TEXT,
        wallet_number TEXT,
        instruction TEXT
    )
    ''')
    
    # Таблица сообщений поддержки
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
    
    # Добавляем продавцов
    cursor.execute("SELECT COUNT(*) FROM sellers")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO sellers (id, name, username) VALUES (?, ?, ?)",
                      (1, 'Admin Seller', 'admin'))
        cursor.execute("INSERT INTO sellers (id, name, username) VALUES (?, ?, ?)",
                      (5391287151, 'Главный продавец', 'diisk_shop'))
    
    cursor.execute("SELECT COUNT(*) FROM payments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO payments (card_number, wallet_number, instruction) VALUES (?, ?, ?)",
                      ('2200 1234 5678 9012', '+7 999 123-45-67', 'Оплатите на карту или кошелек, затем отправьте чек'))
    
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

# ==================== HTML ШАБЛОН (iPhone стиль) ====================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes, viewport-fit=cover">
    <title>{{ site_name }} - Покупка UC для PUBG Mobile</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        
        body {
            background: #1a1a2e;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: 'Inter', sans-serif;
        }
        
        /* iPhone рамка */
        .phone {
            width: 390px;
            height: 844px;
            background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
            border-radius: 44px;
            overflow-y: auto;
            overflow-x: hidden;
            position: relative;
            box-shadow: 0 30px 50px rgba(0,0,0,0.3), 0 0 0 8px #2a2a3e;
            scroll-behavior: smooth;
        }
        
        .phone::-webkit-scrollbar { width: 4px; }
        .phone::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
        .phone::-webkit-scrollbar-thumb { background: #a855f7; border-radius: 10px; }
        
        /* Динамический остров */
        .dynamic-island {
            position: sticky;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(15,12,41,0.95);
            backdrop-filter: blur(20px);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 100;
            border-bottom: 1px solid rgba(168,85,247,0.2);
        }
        
        .time { font-size: 17px; font-weight: 600; color: white; }
        .status-icons { display: flex; gap: 6px; font-size: 12px; color: white; }
        
        /* Летающие элементы */
        .animated-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
        }
        
        .floating-item {
            position: absolute;
            font-family: monospace;
            font-weight: bold;
            animation: floatUp 12s infinite ease-in-out;
        }
        
        @keyframes floatUp {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.15; }
            80% { opacity: 0.15; }
            100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
        }
        
        /* Боковое меню */
        .menu-btn {
            position: fixed;
            top: 65px;
            left: 15px;
            width: 40px;
            height: 40px;
            background: rgba(168,85,247,0.2);
            backdrop-filter: blur(10px);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 200;
            border: 1px solid rgba(168,85,247,0.3);
            font-size: 20px;
        }
        
        .side-menu {
            position: fixed;
            top: 0;
            left: -280px;
            width: 280px;
            height: 100%;
            background: rgba(15,12,41,0.98);
            backdrop-filter: blur(20px);
            z-index: 300;
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
            padding: 14px 20px;
            border-radius: 16px;
            margin-bottom: 8px;
            transition: 0.2s;
        }
        
        .side-menu a:hover, .side-menu a.active { background: rgba(168,85,247,0.2); color: #c084fc; }
        
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.6);
            z-index: 250;
            display: none;
        }
        
        .overlay.active { display: block; }
        
        .close-menu {
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 24px;
            cursor: pointer;
            color: rgba(255,255,255,0.6);
        }
        
        /* Контент */
        .content {
            padding: 20px 16px 30px;
            position: relative;
            z-index: 1;
        }
        
        .hero h1 {
            font-size: 28px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff, #a855f7, #e879f9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }
        
        .hero p { font-size: 14px; color: rgba(255,255,255,0.6); margin-bottom: 20px; }
        
        .features {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 30px;
        }
        
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(168,85,247,0.2);
            padding: 16px;
            text-align: center;
            transition: 0.3s;
        }
        
        .card-icon { font-size: 28px; margin-bottom: 8px; }
        .card h3 { font-size: 14px; margin-bottom: 4px; }
        .card p { font-size: 11px; color: rgba(255,255,255,0.5); }
        
        .catalog {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 30px;
        }
        
        .product {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(168,85,247,0.2);
            padding: 16px;
            text-align: center;
            transition: 0.3s;
        }
        
        .product:hover { transform: translateY(-3px); border-color: #a855f7; }
        .product-amount { font-size: 20px; font-weight: 700; color: #c084fc; }
        .product-price { font-size: 16px; font-weight: 600; margin: 8px 0; }
        
        .btn {
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border: none;
            border-radius: 30px;
            color: white;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: 0.3s;
            font-size: 13px;
        }
        
        .btn-sm { padding: 6px 16px; font-size: 12px; }
        .btn-block { width: 100%; text-align: center; }
        
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 6px; font-size: 12px; color: rgba(255,255,255,0.7); }
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 12px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(168,85,247,0.3);
            border-radius: 16px;
            color: white;
            font-size: 14px;
        }
        .form-group input:focus { outline: none; border-color: #a855f7; }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }
        .status-waiting { background: rgba(245,158,11,0.2); color: #fbbf24; }
        .status-seller { background: rgba(59,130,246,0.2); color: #60a5fa; }
        .status-completed { background: rgba(16,185,129,0.2); color: #34d399; }
        
        .footer {
            text-align: center;
            padding: 20px;
            border-top: 1px solid rgba(168,85,247,0.1);
            margin-top: 30px;
            color: rgba(255,255,255,0.4);
            font-size: 10px;
        }
        
        /* Чат */
        .chat-widget {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 200;
        }
        
        .chat-btn {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 5px 20px rgba(168,85,247,0.4);
            font-size: 22px;
        }
        
        .chat-window {
            position: absolute;
            bottom: 70px;
            right: 0;
            width: 320px;
            height: 450px;
            background: rgba(15,12,41,0.98);
            border-radius: 24px;
            border: 1px solid rgba(168,85,247,0.3);
            display: none;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-window.open { display: flex; }
        
        .chat-header {
            padding: 14px;
            background: rgba(168,85,247,0.15);
            border-bottom: 1px solid rgba(168,85,247,0.3);
            display: flex;
            justify-content: space-between;
        }
        
        .chat-msgs { flex: 1; padding: 12px; overflow-y: auto; }
        .msg { margin-bottom: 10px; padding: 8px 12px; border-radius: 16px; max-width: 85%; font-size: 13px; }
        .msg.user { background: linear-gradient(135deg, #a855f7, #e879f9); margin-left: auto; }
        .msg.support { background: rgba(255,255,255,0.1); margin-right: auto; }
        
        .chat-input {
            display: flex;
            padding: 12px;
            border-top: 1px solid rgba(168,85,247,0.2);
            gap: 8px;
        }
        .chat-input input {
            flex: 1;
            padding: 10px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(168,85,247,0.3);
            border-radius: 25px;
            color: white;
            font-size: 13px;
        }
        .chat-input button {
            padding: 10px 16px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border: none;
            border-radius: 25px;
            color: white;
            cursor: pointer;
        }
        
        @media (max-width: 400px) {
            .phone { width: 100%; height: 100vh; border-radius: 0; box-shadow: none; }
        }
    </style>
</head>
<body>
    <div class="phone">
        <div class="dynamic-island">
            <div class="time" id="currentTime"></div>
            <div class="status-icons">
                <i class="fas fa-signal"></i>
                <i class="fas fa-wifi"></i>
                <i class="fas fa-battery-full"></i>
            </div>
        </div>
        
        <div class="menu-btn" onclick="toggleMenu()">☰</div>
        
        <div class="side-menu" id="sideMenu">
            <div class="close-menu" onclick="toggleMenu()">✕</div>
            <a href="/" onclick="toggleMenu()"><i class="fas fa-home"></i> Главная</a>
            <a href="/catalog" onclick="toggleMenu()"><i class="fas fa-store"></i> Каталог</a>
            <a href="/check" onclick="toggleMenu()"><i class="fas fa-search"></i> Проверить заказ</a>
            <a href="/support" onclick="toggleMenu()"><i class="fas fa-headset"></i> Поддержка</a>
            <hr style="margin: 10px 0; border-color: rgba(168,85,247,0.2);">
            <a href="/admin" onclick="toggleMenu()"><i class="fas fa-crown"></i> Админ-панель</a>
        </div>
        
        <div class="overlay" id="overlay" onclick="toggleMenu()"></div>
        
        <div class="animated-bg" id="animatedBg"></div>
        
        <div class="content">
'''

HTML_FOOTER = '''
        </div>
        
        <div class="chat-widget">
            <div class="chat-btn" onclick="toggleChat()"><i class="fas fa-headset"></i></div>
            <div class="chat-window" id="chatWindow">
                <div class="chat-header">
                    <strong><i class="fas fa-headset"></i> Поддержка</strong>
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
            <p>⚡ UC для PUBG Mobile</p>
        </div>
    </div>
    
    <script>
        // Время
        function updateTime() {
            const now = new Date();
            document.getElementById('currentTime').textContent = now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
        }
        updateTime();
        setInterval(updateTime, 1000);
        
        // Летающие элементы
        const items = ['U', 'C', 'UC', '60', '120', '180', '325', '660', '1320', '1800', '▲', '●', '◆'];
        for (let i = 0; i < 30; i++) {
            const el = document.createElement('div');
            el.className = 'floating-item';
            el.innerHTML = items[Math.floor(Math.random() * items.length)];
            el.style.left = Math.random() * 100 + '%';
            el.style.fontSize = (Math.random() * 25 + 15) + 'px';
            el.style.animationDelay = Math.random() * 10 + 's';
            el.style.animationDuration = (Math.random() * 10 + 8) + 's';
            el.style.opacity = Math.random() * 0.15 + 0.05;
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
    content = '''
    <div class="hero">
        <h1>🛡️ DiSK Delovoi UC</h1>
        <p>Безопасная покупка UC для PUBG Mobile</p>
    </div>
    
    <div class="features">
        <div class="card"><div class="card-icon">🔒</div><h3>100% Безопасность</h3><p>Гарантия получения</p></div>
        <div class="card"><div class="card-icon">⚡</div><h3>Мгновенная доставка</h3><p>UC приходят быстро</p></div>
        <div class="card"><div class="card-icon">💰</div><h3>Лучшие цены</h3><p>Низкие цены</p></div>
        <div class="card"><div class="card-icon">🌐</div><h3>Поддержка 24/7</h3><p>Поможем всегда</p></div>
    </div>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <a href="/catalog" class="btn">🚀 В каталог UC</a>
    </div>
    
    <div class="card" style="padding: 20px; text-align: center;">
        <h3 style="margin-bottom: 12px;">🔍 Проверить заказ</h3>
        <form method="post" action="/check-order">
            <div class="form-group">
                <input type="text" name="order_num" placeholder="Номер заказа" required>
            </div>
            <button type="submit" class="btn btn-sm">Проверить</button>
        </form>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/catalog')
def catalog():
    items = ''
    for amount, price in list(UC_PRICES.items())[:12]:
        items += f'''
        <div class="product">
            <div class="product-amount">{amount} UC</div>
            <div class="product-price">{format_price(price)} ₽</div>
            <a href="/order/{amount}" class="btn btn-sm">Купить</a>
        </div>
        '''
    
    content = f'''
    <div class="hero">
        <h1>🛒 Каталог UC</h1>
        <p>Выберите нужное количество</p>
    </div>
    <div class="catalog">
        {items}
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

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
            flash('Заполните все поля!')
            return redirect(url_for('order', amount=amount))
        
        order_num = generate_order_num()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO orders (order_num, user_name, user_phone, user_email, game_id, uc_amount, uc_price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting_seller')
        ''', (order_num, user_name, user_phone, user_email, game_id, amount, price))
        conn.commit()
        conn.close()
        
        return redirect(url_for('order_status', order_num=order_num))
    
    content = f'''
    <div class="hero">
        <h1>📝 Оформление заказа</h1>
    </div>
    <div class="card" style="padding: 20px;">
        <div class="product-amount" style="text-align:center;">{amount} UC</div>
        <div class="product-price" style="text-align:center;">{format_price(price)} ₽</div>
        <form method="post">
            <div class="form-group"><label>👤 Ваше имя *</label><input type="text" name="user_name" required placeholder="Иван Иванов"></div>
            <div class="form-group"><label>📞 Телефон *</label><input type="tel" name="user_phone" required placeholder="+7 999 123-45-67"></div>
            <div class="form-group"><label>📧 Email</label><input type="email" name="user_email" placeholder="ivan@example.com"></div>
            <div class="form-group"><label>🎮 PUBG ID *</label><input type="text" name="game_id" required placeholder="Введите ID"></div>
            <button type="submit" class="btn btn-block">✅ Оформить заказ</button>
        </form>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/status/<order_num>')
def order_status(order_num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_num=?", (order_num,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        flash('Заказ не найден!')
        return redirect(url_for('catalog'))
    
    if order['status'] == 'waiting_seller':
        status_text = "⏳ Ожидание продавца"
        status_color = "#fbbf24"
        btn_text = "Ожидайте, продавец скоро назначится"
        btn_disabled = "disabled"
    elif order['status'] == 'seller_assigned':
        status_text = "👨‍💼 Продавец назначен"
        status_color = "#60a5fa"
        btn_text = "Ожидайте выполнения заказа"
        btn_disabled = "disabled"
    elif order['status'] == 'completed':
        status_text = "✅ Заказ завершен"
        status_color = "#34d399"
        btn_text = "Заказ выполнен"
        btn_disabled = "disabled"
    else:
        status_text = "❌ Заказ отменен"
        status_color = "#f87171"
        btn_text = "Заказ отменен"
        btn_disabled = "disabled"
    
    content = f'''
    <div class="hero">
        <h1>📋 Статус заказа</h1>
        <p>Заказ #{order_num}</p>
    </div>
    <div class="card" style="padding: 20px; text-align:center;">
        <div class="product-amount">{order['uc_amount']} UC</div>
        <div class="product-price">{format_price(order['uc_price'])} ₽</div>
        <p><i class="fas fa-gamepad"></i> ID: {order['game_id']}</p>
        <p><i class="fas fa-calendar"></i> {order['created_at'][:16]}</p>
        <div style="margin: 16px 0; padding: 12px; background: rgba({int(status_color[1:3],16)},{int(status_color[3:5],16)},{int(status_color[5:7],16)},0.1); border-radius: 16px;">
            <strong>Статус:</strong> <span style="color: {status_color};">{status_text}</span>
        </div>
        {f'<a href="/catalog" class="btn btn-sm">🛒 Продолжить покупки</a>' if btn_disabled == "disabled" else ''}
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/check-order', methods=['POST'])
def check_order():
    order_num = request.form.get('order_num')
    return redirect(url_for('order_status', order_num=order_num))

@app.route('/check')
def check_page():
    content = '''
    <div class="hero">
        <h1>🔍 Проверка заказа</h1>
    </div>
    <div class="card" style="padding: 20px;">
        <form method="post" action="/check-order">
            <div class="form-group">
                <input type="text" name="order_num" placeholder="Номер заказа" required>
            </div>
            <button type="submit" class="btn btn-block">Проверить</button>
        </form>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/support')
def support_page():
    content = '''
    <div class="hero">
        <h1>💬 Поддержка</h1>
    </div>
    <div class="card" style="padding: 20px;">
        <form method="post" action="/support/send-form">
            <div class="form-group"><label>👤 Ваше имя</label><input type="text" name="user_name" required></div>
            <div class="form-group"><label>📧 Email</label><input type="email" name="user_email" required></div>
            <div class="form-group"><label>💬 Сообщение</label><textarea name="message" rows="4" required></textarea></div>
            <button type="submit" class="btn btn-block">📨 Отправить</button>
        </form>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

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
        flash('Сообщение отправлено!')
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
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .login-card {
                background: rgba(255,255,255,0.05);
                backdrop-filter: blur(10px);
                border-radius: 32px;
                border: 1px solid rgba(168,85,247,0.3);
                padding: 40px;
                width: 350px;
            }
            h2 { text-align: center; margin-bottom: 30px; color: white; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 8px; color: rgba(255,255,255,0.7); font-size: 14px; }
            .form-group input {
                width: 100%;
                padding: 14px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 16px;
                color: white;
                font-size: 15px;
            }
            .btn {
                width: 100%;
                padding: 14px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 30px;
                color: white;
                font-weight: 600;
                cursor: pointer;
            }
            .error { background: rgba(239,68,68,0.2); padding: 12px; border-radius: 16px; margin-bottom: 20px; text-align: center; color: #f87171; }
        </style>
    </head>
    <body>
        <div class="login-card">
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
    
    # Статистика
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='waiting_seller'")
    waiting_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='seller_assigned'")
    assigned_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='completed'")
    completed_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(uc_price) FROM orders WHERE status='completed'")
    total_income = cursor.fetchone()[0] or 0
    
    # Заказы
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    orders = cursor.fetchall()
    
    # Продавцы
    cursor.execute("SELECT * FROM sellers")
    sellers = cursor.fetchall()
    
    # Сообщения
    cursor.execute("SELECT COUNT(*) FROM support_messages WHERE status='new'")
    new_messages = cursor.fetchone()[0]
    cursor.execute("SELECT * FROM support_messages ORDER BY created_at DESC")
    messages = cursor.fetchall()
    
    conn.close()
    
    orders_html = ''
    for order in orders:
        status_text = '⏳ Ожидает продавца' if order['status'] == 'waiting_seller' else '👨‍💼 Продавец назначен' if order['status'] == 'seller_assigned' else '✅ Завершен' if order['status'] == 'completed' else '❌ Отменен'
        orders_html += f'''
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:10px;">{order['order_num']}</td>
            <td style="padding:10px;">{order['user_name']}</td>
            <td style="padding:10px;">{order['uc_amount']}</td>
            <td style="padding:10px;">{format_price(order['uc_price'])} ₽</td>
            <td style="padding:10px;">{status_text}</td>
            <td style="padding:10px;">
                <form method="post" action="/admin/assign-seller/{order['id']}" style="display:flex;gap:8px;">
                    <select name="seller_id" style="background:#1e1b4b;border:1px solid #a855f7;border-radius:12px;padding:6px;color:white;">
                        <option value="">Выбрать продавца</option>
                        ''' + ''.join([f'<option value="{s["id"]}">{s["name"]} (@{s["username"]})</option>' for s in sellers]) + '''
                    </select>
                    <button type="submit" class="btn" style="padding:6px 12px;">Назначить</button>
                </form>
            </td>
        </tr>
        '''
    
    sellers_html = ''
    for seller in sellers:
        sellers_html += f'''
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:10px;">{seller['id']}</td>
            <td style="padding:10px;">{seller['name']}</td>
            <td style="padding:10px;">@{seller['username']}</td>
            <td style="padding:10px;">{"🟢 Активен" if seller['is_active'] else "🔴 Неактивен"}</td>
            <td style="padding:10px;">
                <form method="post" action="/admin/remove-seller/{seller['id']}" style="display:inline;">
                    <button type="submit" class="btn" style="padding:4px 12px;background:#ef4444;">Удалить</button>
                </form>
            </td>
        </tr>
        '''
    
    messages_html = ''
    for msg in messages:
        messages_html += f'''
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
            <td style="padding:10px;">{msg['created_at'][:16]}</td>
            <td style="padding:10px;">{msg['user_name']}</td>
            <td style="padding:10px;">{msg['user_email']}</td>
            <td style="padding:10px;">{msg['message'][:50]}...</td>
            <td style="padding:10px;">{"🆕 Новое" if msg['status'] == 'new' else "✅ Прочитано"}</td>
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
                color: white;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { margin-bottom: 20px; font-size: 28px; background: linear-gradient(135deg,#fff,#a855f7,#e879f9); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .stats {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(255,255,255,0.05);
                border-radius: 20px;
                padding: 20px;
                text-align: center;
                border: 1px solid rgba(168,85,247,0.2);
            }
            .stat-number { font-size: 32px; font-weight: 700; color: #c084fc; }
            .card {
                background: rgba(255,255,255,0.05);
                border-radius: 24px;
                padding: 20px;
                margin-bottom: 30px;
                border: 1px solid rgba(168,85,247,0.2);
            }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
            th { color: #c084fc; }
            .btn {
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 30px;
                color: white;
                padding: 8px 16px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
            }
            select, option { background: #1e1b4b; color: white; padding: 6px; border-radius: 12px; }
            .admin-actions { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
            @media (max-width: 768px) { .stats { grid-template-columns: repeat(2,1fr); } table { font-size: 12px; } }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="admin-actions">
                <a href="/admin/payments" class="btn">💳 Реквизиты</a>
                <a href="/admin/add-seller" class="btn">➕ Добавить продавца</a>
                <a href="/admin/logout" class="btn">🚪 Выйти</a>
                <a href="/" class="btn">🏠 На сайт</a>
            </div>
            
            <div class="stats">
                <div class="stat-card"><div class="stat-number">''' + str(total_orders) + '''</div><p>Всего заказов</p></div>
                <div class="stat-card"><div class="stat-number">''' + str(waiting_orders) + '''</div><p>Ожидают продавца</p></div>
                <div class="stat-card"><div class="stat-number">''' + str(assigned_orders) + '''</div><p>В работе</p></div>
                <div class="stat-card"><div class="stat-number">''' + format_price(total_income) + ''' ₽</div><p>Оборот</p></div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 20px;">📋 Заказы</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead><tr><th>№</th><th>Покупатель</th><th>UC</th><th>Сумма</th><th>Статус</th><th>Действия</th></tr></thead>
                        <tbody>''' + orders_html + '''</tbody>
                    </table>
                </div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 20px;">👨‍💼 Продавцы</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead><tr><th>ID</th><th>Имя</th><th>Username</th><th>Статус</th><th>Действия</th></tr></thead>
                        <tbody>''' + sellers_html + '''</tbody>
                    </table>
                </div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 20px;">💬 Сообщения поддержки</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead><tr><th>Дата</th><th>Имя</th><th>Email</th><th>Сообщение</th><th>Статус</th></tr></thead>
                        <tbody>''' + messages_html + '''</tbody>
                    </table>
                </div>
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/admin/assign-seller/<int:order_id>', methods=['POST'])
@admin_required
def assign_seller(order_id):
    seller_id = request.form.get('seller_id')
    
    if seller_id:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sellers WHERE id=?", (seller_id,))
        seller = cursor.fetchone()
        if seller:
            cursor.execute("UPDATE orders SET seller_id=?, seller_name=?, status='seller_assigned' WHERE id=?", 
                          (seller_id, seller['name'], order_id))
            conn.commit()
        conn.close()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/remove-seller/<int:seller_id>', methods=['POST'])
@admin_required
def remove_seller(seller_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sellers WHERE id=?", (seller_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add-seller', methods=['GET', 'POST'])
@admin_required
def add_seller():
    if request.method == 'POST':
        seller_id = request.form.get('seller_id')
        name = request.form.get('name')
        username = request.form.get('username')
        
        if seller_id and name:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sellers (id, name, username) VALUES (?, ?, ?)", (seller_id, name, username))
            conn.commit()
            conn.close()
            return redirect(url_for('admin_dashboard'))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Добавить продавца</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .card {
                background: rgba(255,255,255,0.05);
                border-radius: 24px;
                padding: 30px;
                width: 400px;
                border: 1px solid rgba(168,85,247,0.2);
            }
            h2 { margin-bottom: 20px; color: white; }
            .form-group { margin-bottom: 16px; }
            label { display: block; margin-bottom: 6px; color: rgba(255,255,255,0.7); }
            input {
                width: 100%;
                padding: 12px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 16px;
                color: white;
            }
            .btn {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 30px;
                color: white;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>➕ Добавить продавца</h2>
            <form method="post">
                <div class="form-group"><label>Telegram ID</label><input type="number" name="seller_id" required placeholder="123456789"></div>
                <div class="form-group"><label>Имя</label><input type="text" name="name" required placeholder="Иван Иванов"></div>
                <div class="form-group"><label>Username</label><input type="text" name="username" placeholder="ivan123"></div>
                <button type="submit" class="btn">Добавить</button>
            </form>
        </div>
    </body>
    </html>
    ''')

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
        <title>Реквизиты - Админ-панель</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {
                font-family: 'Inter', sans-serif;
                background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .card {
                background: rgba(255,255,255,0.05);
                border-radius: 24px;
                padding: 30px;
                width: 450px;
                border: 1px solid rgba(168,85,247,0.2);
            }
            h2 { margin-bottom: 20px; color: white; }
            .form-group { margin-bottom: 16px; }
            label { display: block; margin-bottom: 6px; color: rgba(255,255,255,0.7); }
            input, textarea {
                width: 100%;
                padding: 12px;
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(168,85,247,0.3);
                border-radius: 16px;
                color: white;
            }
            .btn {
                width: 100%;
                padding: 12px;
                background: linear-gradient(135deg, #a855f7, #e879f9);
                border: none;
                border-radius: 30px;
                color: white;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>💳 Настройка реквизитов</h2>
            <form method="post">
                <div class="form-group"><label>Номер карты</label><input type="text" name="card_number" value="''' + (payment['card_number'] or '') + '''"></div>
                <div class="form-group"><label>Номер кошелька</label><input type="text" name="wallet_number" value="''' + (payment['wallet_number'] or '') + '''"></div>
                <div class="form-group"><label>Инструкция</label><textarea name="instruction" rows="4">''' + (payment['instruction'] or '') + '''</textarea></div>
                <button type="submit" class="btn">💾 Сохранить</button>
            </form>
            <div style="text-align:center; margin-top:20px;"><a href="/admin" style="color:#a855f7;">← Назад</a></div>
        </div>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
