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
        status TEXT DEFAULT 'waiting_payment',
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
                      (5391287151, 'Главный продавец', 'diisk_shop'))
        cursor.execute("INSERT INTO sellers (id, name, username) VALUES (?, ?, ?)",
                      (1, 'Admin Seller', 'admin'))
    
    cursor.execute("SELECT COUNT(*) FROM payments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO payments (card_number, wallet_number, instruction) VALUES (?, ?, ?)",
                      ('2200 1234 5678 9012', '+7 999 123-45-67', '1. Переведите сумму на карту или кошелек\n2. Сделайте скриншот чека\n3. Нажмите "Я оплатил" и загрузите чек'))
    
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

# ==================== HTML ШАБЛОН ====================
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
            background: #000;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
        }
        
        /* iOS-стиль устройства */
        .device {
            width: 390px;
            height: 844px;
            background: #0a0a0f;
            border-radius: 48px;
            overflow-y: auto;
            overflow-x: hidden;
            position: relative;
            box-shadow: 0 30px 60px rgba(0,0,0,0.5), 0 0 0 8px #1c1c1e;
            scroll-behavior: smooth;
        }
        
        .device::-webkit-scrollbar { width: 0; display: none; }
        
        /* Dynamic Island */
        .dynamic-island {
            position: sticky;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(10,10,15,0.92);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 100;
            border-bottom: 0.5px solid rgba(255,255,255,0.1);
        }
        
        .time { 
            font-size: 16px; 
            font-weight: 590; 
            color: #fff;
            font-feature-settings: "tnum";
        }
        .status-icons { 
            display: flex; 
            gap: 4px; 
            font-size: 12px; 
            color: #fff;
        }
        
        /* Контент */
        .content {
            padding: 16px 20px 30px;
            position: relative;
            z-index: 1;
        }
        
        /* Навигация iOS-стиль */
        .nav-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .nav-title {
            font-size: 22px;
            font-weight: 590;
            color: #fff;
            letter-spacing: -0.5px;
        }
        
        .menu-btn {
            width: 36px;
            height: 36px;
            background: rgba(120,120,128,0.16);
            border-radius: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            border: none;
            font-size: 18px;
            color: #fff;
            transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
        }
        
        .menu-btn:active {
            background: rgba(120,120,128,0.3);
            transform: scale(0.95);
        }
        
        /* Боковое меню в стиле iOS */
        .side-menu {
            position: fixed;
            top: 0;
            left: -300px;
            width: 300px;
            height: 100%;
            background: rgba(28,28,30,0.98);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            z-index: 300;
            transition: left 0.35s cubic-bezier(0.32, 0.72, 0, 1);
            border-right: 0.5px solid rgba(255,255,255,0.1);
            padding: 60px 16px 30px;
        }
        
        .side-menu.open { left: 0; }
        
        .side-menu-header {
            padding: 0 16px 20px;
            border-bottom: 0.5px solid rgba(255,255,255,0.1);
            margin-bottom: 8px;
        }
        
        .side-menu-header h3 {
            color: #fff;
            font-size: 20px;
            font-weight: 590;
        }
        
        .side-menu a {
            display: flex;
            align-items: center;
            gap: 14px;
            color: #fff;
            text-decoration: none;
            padding: 14px 16px;
            border-radius: 12px;
            margin-bottom: 2px;
            transition: all 0.15s;
            font-size: 17px;
            font-weight: 400;
        }
        
        .side-menu a i {
            width: 28px;
            color: #8e8e93;
        }
        
        .side-menu a:active {
            background: rgba(120,120,128,0.16);
        }
        
        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.4);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            z-index: 250;
            display: none;
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .overlay.active { 
            display: block; 
            opacity: 1;
        }
        
        .close-menu {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 32px;
            height: 32px;
            background: rgba(120,120,128,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            color: #fff;
        }
        
        /* Карточки в стиле iOS */
        .section-title {
            font-size: 20px;
            font-weight: 590;
            color: #fff;
            margin-bottom: 12px;
            letter-spacing: -0.3px;
        }
        
        .ios-card {
            background: #1c1c1e;
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 16px;
            border: none;
            transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
        }
        
        .ios-card:active {
            transform: scale(0.98);
            background: #2c2c2e;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }
        
        .feature-item {
            background: #1c1c1e;
            border-radius: 16px;
            padding: 18px 12px;
            text-align: center;
            transition: all 0.2s;
        }
        
        .feature-icon {
            font-size: 28px;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #5e5ce6, #bf5af2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .feature-item h4 {
            color: #fff;
            font-size: 15px;
            font-weight: 590;
            margin-bottom: 4px;
        }
        
        .feature-item p {
            color: #8e8e93;
            font-size: 12px;
        }
        
        .catalog {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 24px;
        }
        
        .product-card {
            background: #1c1c1e;
            border-radius: 16px;
            padding: 18px 12px;
            text-align: center;
            transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
            border: 0.5px solid rgba(255,255,255,0.05);
        }
        
        .product-card:active {
            transform: scale(0.96);
            background: #2c2c2e;
        }
        
        .product-amount {
            font-size: 26px;
            font-weight: 700;
            background: linear-gradient(135deg, #5e5ce6, #bf5af2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .product-price {
            font-size: 18px;
            font-weight: 590;
            color: #fff;
            margin: 10px 0 14px;
        }
        
        .btn {
            display: inline-block;
            padding: 12px 20px;
            background: #5e5ce6;
            border: none;
            border-radius: 30px;
            color: white;
            font-weight: 590;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.25, 0.1, 0.25, 1);
            font-size: 15px;
            border: none;
        }
        
        .btn:active {
            transform: scale(0.95);
            background: #4a48c4;
        }
        
        .btn-secondary {
            background: rgba(120,120,128,0.16);
            color: #5e5ce6;
        }
        
        .btn-secondary:active {
            background: rgba(120,120,128,0.24);
        }
        
        .btn-sm { 
            padding: 8px 16px; 
            font-size: 13px; 
        }
        
        .btn-block { 
            width: 100%; 
            text-align: center; 
            display: block;
        }
        
        .form-group { 
            margin-bottom: 20px; 
        }
        
        .form-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-size: 14px; 
            color: #8e8e93;
            font-weight: 500;
        }
        
        .form-group input, 
        .form-group textarea, 
        .form-group select {
            width: 100%;
            padding: 14px 16px;
            background: #1c1c1e;
            border: 0.5px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            color: white;
            font-size: 16px;
            transition: all 0.2s;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #5e5ce6;
            background: #2c2c2e;
        }
        
        /* Статус бейджи */
        .status-badge {
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 590;
        }
        
        .status-waiting { 
            background: rgba(255,159,10,0.16); 
            color: #ff9f0a; 
        }
        
        .status-seller { 
            background: rgba(10,132,255,0.16); 
            color: #0a84ff; 
        }
        
        .status-completed { 
            background: rgba(48,209,88,0.16); 
            color: #30d158; 
        }
        
        /* Реквизиты */
        .payment-details {
            background: #1c1c1e;
            border-radius: 16px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .payment-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 0.5px solid rgba(255,255,255,0.1);
        }
        
        .payment-row:last-child {
            border-bottom: none;
        }
        
        .payment-label {
            color: #8e8e93;
            font-size: 14px;
        }
        
        .payment-value {
            color: #fff;
            font-size: 16px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .copy-btn {
            background: rgba(120,120,128,0.16);
            border: none;
            border-radius: 20px;
            padding: 6px 12px;
            color: #5e5ce6;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .copy-btn:active {
            background: rgba(120,120,128,0.3);
        }
        
        /* Футер */
        .footer {
            text-align: center;
            padding: 30px 20px;
            color: #8e8e93;
            font-size: 12px;
        }
        
        /* Анимации появления */
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .animate-in {
            animation: fadeInUp 0.4s cubic-bezier(0.25, 0.1, 0.25, 1) forwards;
        }
        
        /* Градиентный текст */
        .gradient-text {
            background: linear-gradient(135deg, #5e5ce6, #bf5af2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        @media (max-width: 420px) {
            .device { 
                width: 100%; 
                height: 100vh; 
                border-radius: 0; 
                box-shadow: none; 
            }
        }
    </style>
</head>
<body>
    <div class="device">
        <div class="dynamic-island">
            <div class="time" id="currentTime"></div>
            <div class="status-icons">
                <i class="fas fa-signal"></i>
                <i class="fas fa-wifi"></i>
                <i class="fas fa-battery-full"></i>
            </div>
        </div>
        
        <div class="menu-btn" onclick="toggleMenu()" style="position:fixed; top:60px; left:20px; z-index:200;">
            <i class="fas fa-bars"></i>
        </div>
        
        <div class="side-menu" id="sideMenu">
            <div class="close-menu" onclick="toggleMenu()">
                <i class="fas fa-times"></i>
            </div>
            <div class="side-menu-header">
                <h3>DiSK Delovoi UC</h3>
            </div>
            <a href="/" onclick="toggleMenu()"><i class="fas fa-house"></i> Главная</a>
            <a href="/catalog" onclick="toggleMenu()"><i class="fas fa-bag-shopping"></i> Каталог</a>
            <a href="/check" onclick="toggleMenu()"><i class="fas fa-magnifying-glass"></i> Проверить заказ</a>
            <a href="/support" onclick="toggleMenu()"><i class="fas fa-headphones"></i> Поддержка</a>
            <div style="margin-top: 20px; padding-top: 20px; border-top: 0.5px solid rgba(255,255,255,0.1);">
                <a href="/admin" onclick="toggleMenu()"><i class="fas fa-crown"></i> Админ-панель</a>
            </div>
        </div>
        
        <div class="overlay" id="overlay" onclick="toggleMenu()"></div>
        
        <div class="content">
'''

HTML_FOOTER = '''
        </div>
        
        <div class="footer">
            <p>© 2024 DiSK Delovoi UC</p>
            <p>⚡ Безопасная покупка UC для PUBG Mobile</p>
        </div>
    </div>
    
    <script>
        // Время для Dynamic Island
        function updateTime() {
            const now = new Date();
            document.getElementById('currentTime').textContent = now.toLocaleTimeString('ru-RU', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }
        updateTime();
        setInterval(updateTime, 1000);
        
        // Меню
        function toggleMenu() {
            const menu = document.getElementById('sideMenu');
            const overlay = document.getElementById('overlay');
            menu.classList.toggle('open');
            overlay.classList.toggle('active');
        }
        
        // Копирование текста
        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('Скопировано!');
            });
        }
        
        // Плавное появление элементов
        document.addEventListener('DOMContentLoaded', function() {
            const elements = document.querySelectorAll('.ios-card, .product-card, .feature-item');
            elements.forEach((el, index) => {
                el.style.opacity = '0';
                setTimeout(() => {
                    el.style.animation = 'fadeInUp 0.4s cubic-bezier(0.25, 0.1, 0.25, 1) forwards';
                }, index * 50);
            });
        });
    </script>
</body>
</html>
'''

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    content = '''
    <div class="nav-bar">
        <div class="nav-title">DiSK UC</div>
        <div style="width:36px;"></div>
    </div>
    
    <div style="margin-bottom: 24px;">
        <h1 style="font-size: 32px; font-weight: 700; color: #fff; margin-bottom: 8px;">
            <span class="gradient-text">Покупка UC</span>
        </h1>
        <p style="color: #8e8e93; font-size: 16px;">Для PUBG Mobile · Мгновенно · Безопасно</p>
    </div>
    
    <div class="features">
        <div class="feature-item">
            <div class="feature-icon"><i class="fas fa-shield"></i></div>
            <h4>Безопасность</h4>
            <p>100% гарантия</p>
        </div>
        <div class="feature-item">
            <div class="feature-icon"><i class="fas fa-bolt"></i></div>
            <h4>Мгновенно</h4>
            <p>Доставка за минуты</p>
        </div>
        <div class="feature-item">
            <div class="feature-icon"><i class="fas fa-tag"></i></div>
            <h4>Лучшие цены</h4>
            <p>На рынке UC</p>
        </div>
        <div class="feature-item">
            <div class="feature-icon"><i class="fas fa-clock"></i></div>
            <h4>Поддержка 24/7</h4>
            <p>Всегда на связи</p>
        </div>
    </div>
    
    <a href="/catalog" class="btn btn-block" style="margin-bottom: 24px;">
        <i class="fas fa-bag-shopping"></i> Перейти в каталог
    </a>
    
    <div class="ios-card">
        <h3 style="color:#fff; margin-bottom: 16px; font-size: 18px;">
            <i class="fas fa-magnifying-glass" style="margin-right: 8px;"></i>Проверить заказ
        </h3>
        <form method="post" action="/check-order">
            <div class="form-group">
                <input type="text" name="order_num" placeholder="Номер заказа" required style="background:#2c2c2e;">
            </div>
            <button type="submit" class="btn" style="width:100%;">Проверить статус</button>
        </form>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/catalog')
def catalog():
    items = ''
    for amount, price in UC_PRICES.items():
        items += f'''
        <div class="product-card" onclick="location.href='/order/{amount}'">
            <div class="product-amount">{amount} UC</div>
            <div class="product-price">{format_price(price)} ₽</div>
            <span class="btn btn-sm">Купить</span>
        </div>
        '''
    
    content = f'''
    <div class="nav-bar">
        <a href="/" style="color:#5e5ce6; text-decoration:none; font-size:17px;">
            <i class="fas fa-chevron-left"></i> Назад
        </a>
        <div class="nav-title">Каталог UC</div>
        <div style="width:36px;"></div>
    </div>
    
    <p style="color:#8e8e93; margin-bottom: 16px;">Выберите количество UC</p>
    
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
        VALUES (?, ?, ?, ?, ?, ?, ?, 'waiting_payment')
        ''', (order_num, user_name, user_phone, user_email, game_id, amount, price))
        conn.commit()
        conn.close()
        
        return redirect(url_for('payment_page', order_num=order_num))
    
    content = f'''
    <div class="nav-bar">
        <a href="/catalog" style="color:#5e5ce6; text-decoration:none; font-size:17px;">
            <i class="fas fa-chevron-left"></i> Назад
        </a>
        <div class="nav-title">Оформление</div>
        <div style="width:36px;"></div>
    </div>
    
    <div class="ios-card" style="text-align:center;">
        <div class="product-amount" style="font-size:32px;">{amount} UC</div>
        <div class="product-price" style="font-size:24px;">{format_price(price)} ₽</div>
    </div>
    
    <div class="ios-card">
        <form method="post">
            <div class="form-group">
                <label><i class="fas fa-user"></i> Ваше имя *</label>
                <input type="text" name="user_name" required placeholder="Иван Иванов">
            </div>
            <div class="form-group">
                <label><i class="fas fa-phone"></i> Телефон *</label>
                <input type="tel" name="user_phone" required placeholder="+7 999 123-45-67">
            </div>
            <div class="form-group">
                <label><i class="fas fa-envelope"></i> Email</label>
                <input type="email" name="user_email" placeholder="ivan@example.com">
            </div>
            <div class="form-group">
                <label><i class="fas fa-gamepad"></i> PUBG ID *</label>
                <input type="text" name="game_id" required placeholder="Ваш игровой ID">
                <p style="color:#8e8e93; font-size:12px; margin-top:6px;">Находится в профиле игры</p>
            </div>
            <button type="submit" class="btn btn-block">Перейти к оплате</button>
        </form>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/payment/<order_num>')
def payment_page(order_num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_num=?", (order_num,))
    order = cursor.fetchone()
    
    cursor.execute("SELECT * FROM payments LIMIT 1")
    payment = cursor.fetchone()
    conn.close()
    
    if not order:
        flash('Заказ не найден!')
        return redirect(url_for('catalog'))
    
    if order['status'] != 'waiting_payment':
        return redirect(url_for('order_status', order_num=order_num))
    
    content = f'''
    <div class="nav-bar">
        <a href="/catalog" style="color:#5e5ce6; text-decoration:none; font-size:17px;">
            <i class="fas fa-chevron-left"></i> Назад
        </a>
        <div class="nav-title">Оплата</div>
        <div style="width:36px;"></div>
    </div>
    
    <div class="ios-card" style="text-align:center;">
        <div style="font-size:40px; margin-bottom:10px;">💳</div>
        <div style="font-size:22px; font-weight:600; color:#fff;">{format_price(order['uc_price'])} ₽</div>
        <div style="color:#8e8e93; margin-top:6px;">Заказ #{order_num}</div>
        <div style="color:#8e8e93; font-size:13px;">{order['uc_amount']} UC для ID: {order['game_id']}</div>
    </div>
    
    <div class="payment-details">
        <h3 style="color:#fff; margin-bottom: 16px; font-size: 17px; font-weight: 590;">Реквизиты для оплаты</h3>
        
        <div class="payment-row">
            <span class="payment-label">💳 Карта</span>
            <span class="payment-value">
                {payment['card_number'] if payment else '2200 1234 5678 9012'}
                <button class="copy-btn" onclick="copyText('{payment['card_number'] if payment else '2200123456789012'}')">
                    <i class="fas fa-copy"></i>
                </button>
            </span>
        </div>
        
        <div class="payment-row">
            <span class="payment-label">📱 Кошелек</span>
            <span class="payment-value">
                {payment['wallet_number'] if payment else '+7 999 123-45-67'}
                <button class="copy-btn" onclick="copyText('{payment['wallet_number'] if payment else '+79991234567'}')">
                    <i class="fas fa-copy"></i>
                </button>
            </span>
        </div>
    </div>
    
    <div class="ios-card">
        <h4 style="color:#fff; margin-bottom: 12px; font-size: 15px;">📋 Инструкция</h4>
        <p style="color:#8e8e93; font-size: 14px; line-height: 1.6; white-space: pre-line;">
            {payment['instruction'] if payment else '1. Переведите сумму на карту или кошелек\n2. Сделайте скриншот чека\n3. Нажмите "Я оплатил" и загрузите чек'}
        </p>
    </div>
    
    <div class="ios-card">
        <form method="post" action="/confirm-payment/{order_num}" enctype="multipart/form-data">
            <div class="form-group">
                <label><i class="fas fa-image"></i> Скриншот оплаты</label>
                <input type="file" name="payment_proof" accept="image/*" required 
                       style="padding: 12px; background: #2c2c2e;">
            </div>
            <button type="submit" class="btn btn-block">
                <i class="fas fa-check-circle"></i> Я оплатил(а)
            </button>
        </form>
        <p style="color:#8e8e93; font-size: 12px; text-align:center; margin-top: 14px;">
            После проверки оплаты UC будут зачислены
        </p>
    </div>
    
    <div style="text-align:center;">
        <a href="/support" style="color:#5e5ce6; text-decoration:none; font-size:14px;">
            <i class="fas fa-headphones"></i> Нужна помощь? Напишите в поддержку
        </a>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/confirm-payment/<order_num>', methods=['POST'])
def confirm_payment(order_num):
    # В реальном приложении здесь должна быть обработка загрузки файла
    # Для простоты просто меняем статус
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status='waiting_seller' WHERE order_num=?", (order_num,))
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
        flash('Заказ не найден!')
        return redirect(url_for('catalog'))
    
    status_map = {
        'waiting_payment': ('⏳ Ожидает оплаты', 'status-waiting'),
        'waiting_seller': ('👨‍💼 Ожидает проверки', 'status-waiting'),
        'seller_assigned': ('✅ Оплата подтверждена', 'status-seller'),
        'completed': ('🎉 UC зачислены!', 'status-completed'),
        'cancelled': ('❌ Отменен', 'status-waiting')
    }
    
    status_text, status_class = status_map.get(order['status'], ('⏳ В обработке', 'status-waiting'))
    
    content = f'''
    <div class="nav-bar">
        <a href="/" style="color:#5e5ce6; text-decoration:none; font-size:17px;">
            <i class="fas fa-chevron-left"></i> Назад
        </a>
        <div class="nav-title">Статус заказа</div>
        <div style="width:36px;"></div>
    </div>
    
    <div class="ios-card" style="text-align:center;">
        <div style="font-size:48px; margin-bottom:12px;">
            {'🎉' if order['status'] == 'completed' else '📦'}
        </div>
        <div class="product-amount">{order['uc_amount']} UC</div>
        <div class="product-price">{format_price(order['uc_price'])} ₽</div>
        <p style="color:#8e8e93; margin-top:8px;">Заказ #{order_num}</p>
        <p style="color:#8e8e93; font-size:14px;">
            <i class="fas fa-gamepad"></i> ID: {order['game_id']}
        </p>
        <p style="color:#8e8e93; font-size:13px;">
            <i class="fas fa-calendar"></i> {order['created_at'][:16] if order['created_at'] else ''}
        </p>
        <div style="margin: 20px 0 10px;">
            <span class="status-badge {status_class}">{status_text}</span>
        </div>
    </div>
    
    <div class="ios-card" style="text-align:center;">
        <h4 style="color:#fff; margin-bottom: 16px;">Что дальше?</h4>
        <div style="display:flex; flex-direction:column; gap:12px;">
    '''
    
    if order['status'] == 'waiting_payment':
        content += f'''
            <a href="/payment/{order_num}" class="btn">💳 Перейти к оплате</a>
            <p style="color:#8e8e93; font-size:13px;">Оплатите заказ для продолжения</p>
        '''
    elif order['status'] == 'waiting_seller':
        content += '''
            <p style="color:#8e8e93;">⏳ Ожидайте подтверждения оплаты продавцом</p>
            <p style="color:#8e8e93; font-size:13px;">Обычно это занимает 5-15 минут</p>
        '''
    elif order['status'] == 'seller_assigned':
        content += '''
            <p style="color:#8e8e93;">✅ Оплата подтверждена! UC скоро будут зачислены</p>
        '''
    elif order['status'] == 'completed':
        content += '''
            <p style="color:#30d158;">🎉 Поздравляем! UC успешно зачислены!</p>
            <p style="color:#8e8e93; font-size:13px;">Проверьте баланс в игре</p>
        '''
    
    content += f'''
        </div>
    </div>
    
    <div style="text-align:center;">
        <a href="/catalog" class="btn btn-secondary">
            <i class="fas fa-bag-shopping"></i> Продолжить покупки
        </a>
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
    <div class="nav-bar">
        <a href="/" style="color:#5e5ce6; text-decoration:none; font-size:17px;">
            <i class="fas fa-chevron-left"></i> Назад
        </a>
        <div class="nav-title">Проверка заказа</div>
        <div style="width:36px;"></div>
    </div>
    
    <div class="ios-card">
        <div style="text-align:center; margin-bottom:20px;">
            <i class="fas fa-magnifying-glass" style="font-size:48px; color:#5e5ce6;"></i>
        </div>
        <form method="post" action="/check-order">
            <div class="form-group">
                <label>Номер заказа</label>
                <input type="text" name="order_num" placeholder="Например: 123456789012" required>
            </div>
            <button type="submit" class="btn btn-block">Проверить статус</button>
        </form>
        <p style="color:#8e8e93; font-size:13px; text-align:center; margin-top:16px;">
            Введите 12-значный номер заказа, полученный при оформлении
        </p>
    </div>
    '''
    return render_template_string(HTML_TEMPLATE + content + HTML_FOOTER, site_name=SITE_NAME)

@app.route('/support')
def support_page():
    content = '''
    <div class="nav-bar">
        <a href="/" style="color:#5e5ce6; text-decoration:none; font-size:17px;">
            <i class="fas fa-chevron-left"></i> Назад
        </a>
        <div class="nav-title">Поддержка</div>
        <div style="width:36px;"></div>
    </div>
    
    <div class="ios-card">
        <div style="text-align:center; margin-bottom:20px;">
            <i class="fas fa-headphones" style="font-size:48px; color:#5e5ce6;"></i>
            <h3 style="color:#fff; margin-top:12px;">Нужна помощь?</h3>
            <p style="color:#8e8e93; margin-top:6px;">Мы ответим в течение 15 минут</p>
        </div>
        <form method="post" action="/support/send-form">
            <div class="form-group">
                <label>Ваше имя</label>
                <input type="text" name="user_name" required>
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="user_email" required>
            </div>
            <div class="form-group">
                <label>Сообщение</label>
                <textarea name="message" rows="4" required placeholder="Опишите вашу проблему..."></textarea>
            </div>
            <button type="submit" class="btn btn-block">Отправить сообщение</button>
        </form>
    </div>
    
    <div class="ios-card">
        <h4 style="color:#fff; margin-bottom:12px;">📞 Контакты</h4>
        <p style="color:#8e8e93;"><i class="fab fa-telegram"></i> Telegram: @diisk_shop</p>
        <p style="color:#8e8e93;"><i class="fas fa-envelope"></i> support@disk-uc.ru</p>
        <p style="color:#8e8e93;"><i class="fas fa-clock"></i> Круглосуточно</p>
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
                font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                background: #000;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .login-card {
                background: #1c1c1e;
                border-radius: 20px;
                padding: 40px;
                width: 400px;
            }
            h2 { 
                text-align: center; 
                margin-bottom: 30px; 
                color: white; 
                font-size: 28px;
                font-weight: 590;
            }
            .form-group { margin-bottom: 20px; }
            .form-group label { 
                display: block; 
                margin-bottom: 8px; 
                color: #8e8e93; 
                font-size: 14px; 
            }
            .form-group input {
                width: 100%;
                padding: 14px;
                background: #2c2c2e;
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 16px;
            }
            .btn {
                width: 100%;
                padding: 14px;
                background: #5e5ce6;
                border: none;
                border-radius: 30px;
                color: white;
                font-weight: 590;
                cursor: pointer;
                font-size: 16px;
            }
            .btn:active { background: #4a48c4; }
            .error { 
                background: rgba(255,69,58,0.16); 
                padding: 12px; 
                border-radius: 12px; 
                margin-bottom: 20px; 
                text-align: center; 
                color: #ff453a; 
            }
        </style>
    </head>
    <body>
        <div class="login-card">
            <h2>👑 Админ-панель</h2>
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
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='waiting_payment'")
    waiting_payment = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='waiting_seller'")
    waiting_seller = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='completed'")
    completed_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(uc_price) FROM orders WHERE status='completed'")
    total_income = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")
    orders = cursor.fetchall()
    
    cursor.execute("SELECT * FROM sellers")
    sellers = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM support_messages WHERE status='new'")
    new_messages = cursor.fetchone()[0]
    
    conn.close()
    
    orders_html = ''
    for order in orders:
        status_map = {
            'waiting_payment': '💳 Ожидает оплаты',
            'waiting_seller': '⏳ Ожидает проверки',
            'seller_assigned': '👨‍💼 Продавец назначен',
            'completed': '✅ Завершен',
            'cancelled': '❌ Отменен'
        }
        status_text = status_map.get(order['status'], order['status'])
        
        orders_html += f'''
        <tr style="border-bottom:1px solid rgba(255,255,255,0.1);">
            <td style="padding:12px;">{order['order_num']}</td>
            <td style="padding:12px;">{order['user_name']}</td>
            <td style="padding:12px;">{order['uc_amount']}</td>
            <td style="padding:12px;">{format_price(order['uc_price'])} ₽</td>
            <td style="padding:12px;">{status_text}</td>
            <td style="padding:12px;">
        '''
        
        if order['status'] == 'waiting_seller':
            orders_html += f'''
                <form method="post" action="/admin/assign-seller/{order['id']}" style="display:flex;gap:8px;flex-wrap:wrap;">
                    <select name="seller_id" style="background:#2c2c2e;border:none;border-radius:12px;padding:8px;color:white;">
                        <option value="">Выбрать продавца</option>
                        {''.join([f'<option value="{s["id"]}">{s["name"]}</option>' for s in sellers])}
                    </select>
                    <button type="submit" style="background:#5e5ce6;border:none;border-radius:20px;padding:8px 16px;color:white;cursor:pointer;">Назначить</button>
                </form>
            '''
        elif order['status'] == 'seller_assigned':
            orders_html += f'''
                <form method="post" action="/admin/complete-order/{order['id']}">
                    <button type="submit" style="background:#30d158;border:none;border-radius:20px;padding:8px 16px;color:white;cursor:pointer;">Завершить</button>
                </form>
            '''
        
        orders_html += '''
            </td>
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
                font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                background: #000;
                min-height: 100vh;
                color: white;
                padding: 20px;
            }
            .container { max-width: 1400px; margin: 0 auto; }
            h1 { 
                margin-bottom: 30px; 
                font-size: 32px; 
                background: linear-gradient(135deg,#fff,#5e5ce6,#bf5af2); 
                -webkit-background-clip: text; 
                -webkit-text-fill-color: transparent; 
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #1c1c1e;
                border-radius: 16px;
                padding: 20px;
                text-align: center;
            }
            .stat-number { font-size: 32px; font-weight: 700; color: #5e5ce6; }
            .stat-label { color: #8e8e93; margin-top: 6px; }
            .card {
                background: #1c1c1e;
                border-radius: 16px;
                padding: 20px;
                margin-bottom: 24px;
            }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; }
            th { color: #8e8e93; font-weight: 500; }
            .btn {
                background: #5e5ce6;
                border: none;
                border-radius: 30px;
                color: white;
                padding: 10px 20px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                font-size: 14px;
                font-weight: 500;
            }
            .admin-actions { display: flex; gap: 12px; margin-bottom: 30px; flex-wrap: wrap; }
            @media (max-width: 768px) { 
                .stats { grid-template-columns: repeat(2,1fr); } 
                table { font-size: 12px; } 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>👑 DiSK Delovoi UC - Админ-панель</h1>
            
            <div class="admin-actions">
                <a href="/admin/payments" class="btn">💳 Реквизиты</a>
                <a href="/admin/add-seller" class="btn">➕ Добавить продавца</a>
                <a href="/admin/logout" class="btn">🚪 Выйти</a>
                <a href="/" class="btn">🏠 На сайт</a>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">''' + str(total_orders) + '''</div>
                    <div class="stat-label">Всего заказов</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">''' + str(waiting_payment) + '''</div>
                    <div class="stat-label">Ожидают оплаты</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">''' + str(waiting_seller) + '''</div>
                    <div class="stat-label">Ожидают проверки</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">''' + format_price(total_income) + ''' ₽</div>
                    <div class="stat-label">Оборот</div>
                </div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 20px; font-size:20px; font-weight:590;">📋 Последние заказы</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead><tr><th>№</th><th>Покупатель</th><th>UC</th><th>Сумма</th><th>Статус</th><th>Действия</th></tr></thead>
                        <tbody>''' + orders_html + '''</tbody>
                    </table>
                </div>
            </div>
            
            <div class="card">
                <h2 style="margin-bottom: 20px; font-size:20px; font-weight:590;">💬 Новых сообщений: ''' + str(new_messages) + '''</h2>
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

@app.route('/admin/complete-order/<int:order_id>', methods=['POST'])
@admin_required
def complete_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?", (order_id,))
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
    
    cursor.execute("SELECT * FROM payments LIMIT 1")
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
                font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                background: #000;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .card {
                background: #1c1c1e;
                border-radius: 20px;
                padding: 30px;
                width: 500px;
            }
            h2 { margin-bottom: 25px; color: white; font-size: 24px; font-weight: 590; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #8e8e93; }
            input, textarea {
                width: 100%;
                padding: 14px;
                background: #2c2c2e;
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 16px;
            }
            .btn {
                width: 100%;
                padding: 14px;
                background: #5e5ce6;
                border: none;
                border-radius: 30px;
                color: white;
                cursor: pointer;
                font-size: 16px;
                font-weight: 590;
            }
            .back-link { text-align:center; margin-top:20px; }
            .back-link a { color: #5e5ce6; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>💳 Настройка реквизитов</h2>
            <form method="post">
                <div class="form-group"><label>Номер карты</label><input type="text" name="card_number" value="''' + (payment['card_number'] if payment else '') + '''"></div>
                <div class="form-group"><label>Номер кошелька / Телефон</label><input type="text" name="wallet_number" value="''' + (payment['wallet_number'] if payment else '') + '''"></div>
                <div class="form-group"><label>Инструкция по оплате</label><textarea name="instruction" rows="5">''' + (payment['instruction'] if payment else '') + '''</textarea></div>
                <button type="submit" class="btn">💾 Сохранить</button>
            </form>
            <div class="back-link"><a href="/admin">← Назад в админ-панель</a></div>
        </div>
    </body>
    </html>
    ''', payment=payment)

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
                font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
                background: #000;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .card {
                background: #1c1c1e;
                border-radius: 20px;
                padding: 30px;
                width: 450px;
            }
            h2 { margin-bottom: 25px; color: white; font-size: 24px; font-weight: 590; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 8px; color: #8e8e93; }
            input {
                width: 100%;
                padding: 14px;
                background: #2c2c2e;
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 16px;
            }
            .btn {
                width: 100%;
                padding: 14px;
                background: #5e5ce6;
                border: none;
                border-radius: 30px;
                color: white;
                cursor: pointer;
                font-size: 16px;
                font-weight: 590;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>➕ Добавить продавца</h2>
            <form method="post">
                <div class="form-group"><label>Telegram ID</label><input type="number" name="seller_id" required placeholder="123456789"></div>
                <div class="form-group"><label>Имя</label><input type="text" name="name" required placeholder="Иван Иванов"></div>
                <div class="form-group"><label>Username</label><input type="text" name="username" placeholder="@username"></div>
                <button type="submit" class="btn">Добавить</button>
            </form>
        </div>
    </body>
    </html>
    ''')

@app.route('/admin/remove-seller/<int:seller_id>', methods=['POST'])
@admin_required
def remove_seller(seller_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sellers WHERE id=?", (seller_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
