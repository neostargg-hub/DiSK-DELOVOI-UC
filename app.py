"""
DiSK Delovoi UC - Premium Shop for PUBG Mobile UC
Стиль: Apple Glassmorphism
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
import sqlite3
import random
import string
import hashlib
import hmac
import secrets
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)

# ==================== СЕКРЕТНЫЙ КЛЮЧ ====================
# Как получить секретный ключ:
# 1. Откройте терминал (командную строку)
# 2. Запустите Python: python
# 3. Введите: import secrets; print(secrets.token_hex(32))
# 4. Скопируйте результат и вставьте ниже

SECRET_KEY = '-ZsB;T)J$.wm(eQ;;c(KEVGT&kI3BJzv'  # ЗАМЕНИТЕ НА СВОЙ!
app.secret_key = SECRET_KEY

# ==================== КОНФИГУРАЦИЯ ====================
SITE_NAME = "DiSK Delovoi UC"
SITE_DOMAIN = "delovoi-uc.ru"  # Ваш домен

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
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password_hash TEXT
    )
    ''')
    
    # Хешируем пароль admin123
    password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    
    cursor.execute("SELECT COUNT(*) FROM admin")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO admin (username, password_hash) VALUES (?, ?)", ('admin', password_hash))
    
    cursor.execute("SELECT COUNT(*) FROM payments")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO payments (card_number, wallet_number, instruction) VALUES (?, ?, ?)",
                      ('', '', 'Оплатите на указанные реквизиты'))
    
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

# ==================== ДЕКОРАТОР АДМИНА ====================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ==================== HTML ШАБЛОН (ВЕСЬ САЙТ В ОДНОМ ФАЙЛЕ) ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>{{ site_name }} - Покупка UC для PUBG Mobile</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
        }
        
        /* Glassmorphism эффект */
        .glass {
            background: rgba(255, 255, 255, 0.07);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 32px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: all 0.3s ease;
        }
        
        .glass-card:hover {
            transform: translateY(-5px);
            border-color: rgba(255, 255, 255, 0.2);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        }
        
        /* Навигация */
        .navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            padding: 16px 24px;
            background: rgba(26, 26, 46, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .nav-container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 24px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #a8b5e6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .nav-links {
            display: flex;
            gap: 32px;
        }
        
        .nav-links a {
            color: rgba(255, 255, 255, 0.7);
            text-decoration: none;
            transition: color 0.3s;
        }
        
        .nav-links a:hover {
            color: #fff;
        }
        
        /* Hero секция */
        .hero {
            padding: 120px 24px 80px;
            text-align: center;
        }
        
        .hero h1 {
            font-size: 64px;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, #a8b5e6 50%, #7c3aed 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 24px;
        }
        
        .hero p {
            font-size: 20px;
            color: rgba(255, 255, 255, 0.6);
            max-width: 600px;
            margin: 0 auto;
        }
        
        /* Контейнер */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 24px;
        }
        
        /* Сетка преимуществ */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin-bottom: 80px;
        }
        
        .feature-card {
            padding: 32px 24px;
            text-align: center;
        }
        
        .feature-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        
        .feature-card h3 {
            font-size: 20px;
            margin-bottom: 8px;
        }
        
        .feature-card p {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.5);
        }
        
        /* Каталог */
        .section-title {
            font-size: 36px;
            font-weight: 600;
            margin-bottom: 40px;
            text-align: center;
        }
        
        .catalog-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 80px;
        }
        
        .product-card {
            padding: 28px;
            text-align: center;
        }
        
        .product-amount {
            font-size: 32px;
            font-weight: 700;
            color: #a8b5e6;
            margin-bottom: 12px;
        }
        
        .product-price {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 20px;
        }
        
        .product-price small {
            font-size: 14px;
            color: rgba(255, 255, 255, 0.4);
        }
        
        .btn {
            display: inline-block;
            padding: 12px 32px;
            background: linear-gradient(135deg, #7c3aed 0%, #a8b5e6 100%);
            border: none;
            border-radius: 40px;
            color: white;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn:hover {
            transform: scale(1.05);
            box-shadow: 0 10px 20px rgba(124, 58, 237, 0.3);
        }
        
        .btn-outline {
            background: transparent;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .btn-outline:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: scale(1.05);
        }
        
        /* Формы */
        .form-container {
            max-width: 500px;
            margin: 0 auto;
            padding: 40px;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .form-group input, .form-group textarea {
            width: 100%;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            color: white;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #7c3aed;
            background: rgba(255, 255, 255, 0.12);
        }
        
        /* Flash сообщения */
        .flash-message {
            padding: 16px 24px;
            border-radius: 16px;
            margin-bottom: 24px;
            background: rgba(124, 58, 237, 0.2);
            border: 1px solid rgba(124, 58, 237, 0.3);
            color: #a8b5e6;
        }
        
        .flash-error {
            background: rgba(239, 68, 68, 0.2);
            border-color: rgba(239, 68, 68, 0.3);
            color: #f87171;
        }
        
        /* Статус заказа */
        .status-timeline {
            display: flex;
            justify-content: space-between;
            margin: 40px 0;
            position: relative;
        }
        
        .status-step {
            text-align: center;
            flex: 1;
            position: relative;
            z-index: 1;
        }
        
        .status-dot {
            width: 48px;
            height: 48px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 12px;
            font-size: 24px;
        }
        
        .status-step.active .status-dot {
            background: linear-gradient(135deg, #7c3aed, #a8b5e6);
            box-shadow: 0 0 20px rgba(124, 58, 237, 0.5);
        }
        
        .status-step.completed .status-dot {
            background: #10b981;
        }
        
        /* Футер */
        .footer {
            text-align: center;
            padding: 40px 24px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            margin-top: 80px;
            color: rgba(255, 255, 255, 0.4);
            font-size: 14px;
        }
        
        /* Адаптив */
        @media (max-width: 768px) {
            .hero h1 { font-size: 40px; }
            .features-grid { grid-template-columns: repeat(2, 1fr); }
            .catalog-grid { grid-template-columns: repeat(2, 1fr); }
            .nav-links { display: none; }
        }
        
        @media (max-width: 480px) {
            .features-grid { grid-template-columns: 1fr; }
            .catalog-grid { grid-template-columns: 1fr; }
        }
        
        /* Анимации */
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
        
        .animated {
            animation: float 3s ease-in-out infinite;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">{{ site_name }}</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/catalog">Каталог</a>
                <a href="/check">Проверить заказ</a>
                {% if session.admin_logged_in %}
                <a href="/admin">Админ-панель</a>
                {% endif %}
            </div>
        </div>
    </nav>
    
    {% block content %}{% endblock %}
    
    <div class="footer">
        <p>© 2024 {{ site_name }}. Все права защищены.</p>
        <p style="margin-top: 8px;">Безопасная покупка UC для PUBG Mobile</p>
    </div>
</body>
</html>
"""

# ==================== ГЛАВНАЯ СТРАНИЦА ====================
INDEX_PAGE = """
{% extends "base.html" %}
{% block content %}
<div class="hero">
    <h1 class="animated">🛡️ {{ site_name }}</h1>
    <p>Безопасная покупка UC для PUBG Mobile по лучшим ценам</p>
</div>

<div class="container">
    <div class="features-grid">
        <div class="feature-card glass-card">
            <div class="feature-icon">✅</div>
            <h3>100% Безопасность</h3>
            <p>Гарантия получения UC на аккаунт</p>
        </div>
        <div class="feature-card glass-card">
            <div class="feature-icon">⚡</div>
            <h3>Мгновенная доставка</h3>
            <p>UC приходят сразу после оплаты</p>
        </div>
        <div class="feature-card glass-card">
            <div class="feature-icon">💰</div>
            <h3>Лучшие цены</h3>
            <p>Самые низкие цены на рынке</p>
        </div>
        <div class="feature-card glass-card">
            <div class="feature-icon">💬</div>
            <h3>Поддержка 24/7</h3>
            <p>Поможем в любой ситуации</p>
        </div>
    </div>
    
    <div style="text-align: center; margin-bottom: 60px;">
        <a href="/catalog" class="btn">🛒 Перейти в каталог</a>
    </div>
    
    <div class="glass-card" style="padding: 40px; text-align: center;">
        <h3 style="margin-bottom: 20px;">Проверить статус заказа</h3>
        <form method="post" action="/check-order" style="max-width: 400px; margin: 0 auto;">
            <div class="form-group">
                <input type="text" name="order_num" placeholder="Введите номер заказа" required>
            </div>
            <button type="submit" class="btn">Проверить</button>
        </form>
    </div>
</div>
{% endblock %}
"""

# ==================== КАТАЛОГ ====================
CATALOG_PAGE = """
{% extends "base.html" %}
{% block content %}
<div class="container">
    <div class="hero" style="padding-top: 100px;">
        <h1>🛒 Каталог UC</h1>
        <p>Выберите нужное количество UC</p>
    </div>
    
    <div class="catalog-grid">
        {% for amount, price in uc_prices.items() %}
        <div class="product-card glass-card">
            <div class="product-amount">{{ amount }} UC</div>
            <div class="product-price">{{ format_price(price) }} ₽</div>
            <a href="/order/{{ amount }}" class="btn">Купить</a>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# ==================== ФОРМА ЗАКАЗА ====================
ORDER_PAGE = """
{% extends "base.html" %}
{% block content %}
<div class="container">
    <div class="hero" style="padding-top: 100px;">
        <h1>📝 Оформление заказа</h1>
    </div>
    
    <div class="glass-card form-container">
        <div style="text-align: center; margin-bottom: 30px;">
            <div class="product-amount">{{ amount }} UC</div>
            <div class="product-price">{{ format_price(price) }} ₽</div>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="flash-message {% if category == 'error' %}flash-error{% endif %}">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        
        <form method="post">
            <div class="form-group">
                <label>Ваше имя *</label>
                <input type="text" name="user_name" required placeholder="Иван Иванов">
            </div>
            <div class="form-group">
                <label>Телефон *</label>
                <input type="tel" name="user_phone" required placeholder="+7 999 123-45-67">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="user_email" placeholder="ivan@example.com">
            </div>
            <div class="form-group">
                <label>PUBG ID *</label>
                <input type="text" name="game_id" required placeholder="Введите ваш игровой ID">
            </div>
            <button type="submit" class="btn" style="width: 100%;">✅ Перейти к оплате</button>
        </form>
    </div>
</div>
{% endblock %}
"""

# ==================== ОПЛАТА ====================
PAYMENT_PAGE = """
{% extends "base.html" %}
{% block content %}
<div class="container">
    <div class="hero" style="padding-top: 100px;">
        <h1>💳 Оплата заказа</h1>
        <p>Заказ #{{ order_num }}</p>
    </div>
    
    <div class="glass-card form-container">
        <div style="text-align: center; margin-bottom: 30px;">
            <div class="product-amount">{{ amount }} UC</div>
            <div class="product-price">{{ format_price(price) }} ₽</div>
            <p style="margin-top: 10px;">🎮 ID: {{ game_id }}</p>
        </div>
        
        <div class="glass-card" style="padding: 24px; margin-bottom: 30px; background: rgba(124,58,237,0.1);">
            <h3 style="margin-bottom: 16px;">💳 Реквизиты для оплаты</h3>
            <p><strong>Карта:</strong> <code style="background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 8px;">{{ card or 'Не указана' }}</code></p>
            <p><strong>Кошелек:</strong> <code style="background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 8px;">{{ wallet or 'Не указан' }}</code></p>
            <p><strong>Инструкция:</strong> {{ instruction }}</p>
            <p style="margin-top: 16px; color: #f87171;">⚠️ Важно: Переведите точную сумму {{ format_price(price) }} ₽</p>
        </div>
        
        <form method="post" action="/payment-proof/{{ order_num }}" enctype="multipart/form-data">
            <div class="form-group">
                <label>📎 Прикрепите чек (скриншот или фото)</label>
                <input type="file" name="proof_file" accept="image/*" style="padding: 10px;">
            </div>
            <div class="form-group">
                <label>Или введите текст подтверждения</label>
                <textarea name="proof_text" rows="3" placeholder="Номер транзакции, дата, сумма..."></textarea>
            </div>
            <button type="submit" class="btn" style="width: 100%;">📨 Отправить чек</button>
        </form>
    </div>
</div>
{% endblock %}
"""

# ==================== СТАТУС ЗАКАЗА ====================
STATUS_PAGE = """
{% extends "base.html" %}
{% block content %}
<div class="container">
    <div class="hero" style="padding-top: 100px;">
        <h1>📋 Статус заказа</h1>
        <p>Заказ #{{ order.order_num }}</p>
    </div>
    
    <div class="glass-card" style="padding: 40px; max-width: 800px; margin: 0 auto;">
        <div class="status-timeline">
            <div class="status-step {% if order.status != 'new' %}completed{% endif %}">
                <div class="status-dot">📝</div>
                <div>Заказ создан</div>
            </div>
            <div class="status-step {% if order.status == 'completed' %}completed{% elif order.status != 'new' %}active{% endif %}">
                <div class="status-dot">💳</div>
                <div>Оплата</div>
            </div>
            <div class="status-step {% if order.status == 'completed' %}completed{% endif %}">
                <div class="status-dot">🎮</div>
                <div>Доставка</div>
            </div>
            <div class="status-step {% if order.status == 'completed' %}completed{% endif %}">
                <div class="status-dot">✅</div>
                <div>Завершен</div>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 30px;">
            <div class="product-amount">{{ order.uc_amount }} UC</div>
            <div class="product-price">{{ format_price(order.uc_price) }} ₽</div>
            <p style="margin-top: 16px;">🎮 ID: {{ order.game_id }}</p>
            <p style="margin-top: 8px;">📅 {{ order.created_at[:19] }}</p>
        </div>
    </div>
</div>
{% endblock %}
"""

# ==================== АДМИН-ПАНЕЛЬ ====================
ADMIN_LOGIN_PAGE = """
{% extends "base.html" %}
{% block content %}
<div class="container">
    <div class="hero" style="padding-top: 100px;">
        <h1>👑 Вход в админ-панель</h1>
    </div>
    
    <div class="glass-card form-container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% for category, message in messages %}
                <div class="flash-message flash-error">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        
        <form method="post">
            <div class="form-group">
                <label>Логин</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Пароль</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn" style="width: 100%;">Войти</button>
        </form>
    </div>
</div>
{% endblock %}
"""

ADMIN_DASHBOARD = """
{% extends "base.html" %}
{% block content %}
<div class="container">
    <div class="hero" style="padding-top: 100px;">
        <h1>👑 Админ-панель</h1>
        <p>Управление заказами и реквизитами</p>
    </div>
    
    <div class="features-grid">
        <div class="feature-card glass-card">
            <div class="feature-icon">📦</div>
            <h3>{{ total_orders }}</h3>
            <p>Всего заказов</p>
        </div>
        <div class="feature-card glass-card">
            <div class="feature-icon">🆕</div>
            <h3>{{ new_orders }}</h3>
            <p>Новых заказов</p>
        </div>
        <div class="feature-card glass-card">
            <div class="feature-icon">✅</div>
            <h3>{{ completed_orders }}</h3>
            <p>Завершено</p>
        </div>
        <div class="feature-card glass-card">
            <div class="feature-icon">💰</div>
            <h3>{{ format_price(total_income) }} ₽</h3>
            <p>Оборот</p>
        </div>
    </div>
    
    <div style="margin-bottom: 30px; display: flex; gap: 16px; justify-content: center;">
        <a href="/admin/payments" class="btn btn-outline">💳 Реквизиты</a>
        <a href="/admin/logout" class="btn btn-outline">🚪 Выйти</a>
    </div>
    
    <div class="glass-card" style="padding: 24px;">
        <h3 style="margin-bottom: 20px;">📋 Список заказов</h3>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                        <th style="text-align: left; padding: 12px;">№</th>
                        <th style="text-align: left; padding: 12px;">Покупатель</th>
                        <th style="text-align: left; padding: 12px;">UC</th>
                        <th style="text-align: left; padding: 12px;">Сумма</th>
                        <th style="text-align: left; padding: 12px;">Статус</th>
                        <th style="text-align: left; padding: 12px;">Действия</th>
                    </tr>
                </thead>
                <tbody>
                    {% for order in orders %}
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 12px;">{{ order.order_num }}</td>
                        <td style="padding: 12px;">{{ order.user_name }}</td>
                        <td style="padding: 12px;">{{ order.uc_amount }}</td>
                        <td style="padding: 12px;">{{ format_price(order.uc_price) }} ₽</td>
                        <td style="padding: 12px;">
                            <span style="padding: 4px 12px; border-radius: 20px; background: {% if order.status == 'new' %}rgba(245,158,11,0.2){% elif order.status == 'completed' %}rgba(16,185,129,0.2){% else %}rgba(239,68,68,0.2){% endif %};">
                                {% if order.status == 'new' %}🆕 Новый
                                {% elif order.status == 'completed' %}✅ Завершен
                                {% else %}❌ Отменен{% endif %}
                            </span>
                        </td>
                        <td style="padding: 12px;">
                            <form method="post" action="/admin/order/{{ order.id }}" style="display: flex; gap: 8px;">
                                <select name="status" style="background: rgba(255,255,255,0.1); border: none; padding: 6px 12px; border-radius: 12px; color: white;">
                                    <option value="new">Новый</option>
                                    <option value="completed">Завершен</option>
                                    <option value="cancelled">Отменен</option>
                                </select>
                                <button type="submit" class="btn" style="padding: 6px 16px;">Обновить</button>
                            </form>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
"""

ADMIN_PAYMENTS = """
{% extends "base.html" %}
{% block content %}
<div class="container">
    <div class="hero" style="padding-top: 100px;">
        <h1>💳 Настройка реквизитов</h1>
        <p>Управление платежными данными</p>
    </div>
    
    <div class="glass-card form-container">
        {% with messages = get_flashed_messages() %}
            {% for message in messages %}
                <div class="flash-message">{{ message }}</div>
            {% endfor %}
        {% endwith %}
        
        <form method="post">
            <div class="form-group">
                <label>Номер карты</label>
                <input type="text" name="card_number" value="{{ card }}" placeholder="1234 5678 9012 3456">
            </div>
            <div class="form-group">
                <label>Номер кошелька</label>
                <input type="text" name="wallet_number" value="{{ wallet }}" placeholder="+7 999 123-45-67">
            </div>
            <div class="form-group">
                <label>Инструкция по оплате</label>
                <textarea name="instruction" rows="4" placeholder="Инструкция...">{{ instruction }}</textarea>
            </div>
            <button type="submit" class="btn" style="width: 100%;">💾 Сохранить</button>
        </form>
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="/admin" class="btn-outline" style="display: inline-block; padding: 10px 24px; border-radius: 40px; text-decoration: none; color: white;">← Назад в админ-панель</a>
        </div>
    </div>
</div>
{% endblock %}
"""

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE + INDEX_PAGE, site_name=SITE_NAME)

@app.route('/catalog')
def catalog():
    return render_template_string(HTML_TEMPLATE + CATALOG_PAGE, 
                                site_name=SITE_NAME, 
                                uc_prices=UC_PRICES, 
                                format_price=format_price)

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
            flash('Пожалуйста, заполните все обязательные поля!', 'error')
            return render_template_string(HTML_TEMPLATE + ORDER_PAGE, 
                                        site_name=SITE_NAME, 
                                        amount=amount, 
                                        price=price, 
                                        format_price=format_price)
        
        order_num = generate_order_num()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO orders (order_num, user_name, user_phone, user_email, game_id, uc_amount, uc_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_num, user_name, user_phone, user_email, game_id, amount, price))
        conn.commit()
        
        cursor.execute("SELECT card_number, wallet_number, instruction FROM payments LIMIT 1")
        payment = cursor.fetchone()
        conn.close()
        
        return render_template_string(HTML_TEMPLATE + PAYMENT_PAGE,
                                    site_name=SITE_NAME,
                                    order_num=order_num,
                                    amount=amount,
                                    price=price,
                                    game_id=game_id,
                                    card=payment['card_number'] if payment else '',
                                    wallet=payment['wallet_number'] if payment else '',
                                    instruction=payment['instruction'] if payment else '',
                                    format_price=format_price)
    
    return render_template_string(HTML_TEMPLATE + ORDER_PAGE, 
                                site_name=SITE_NAME, 
                                amount=amount, 
                                price=price, 
                                format_price=format_price)

@app.route('/payment-proof/<order_num>', methods=['POST'])
def payment_proof(order_num):
    proof_text = request.form.get('proof_text')
    proof_file = request.files.get('proof_file')
    
    conn = get_db()
    cursor = conn.cursor()
    
    proof_data = proof_text if proof_text else 'Файл отправлен'
    if proof_file and proof_file.filename:
        proof_data = f'Файл: {proof_file.filename}'
    
    cursor.execute("UPDATE orders SET payment_proof=?, status='waiting_confirm' WHERE order_num=?", 
                  (proof_data, order_num))
    conn.commit()
    conn.close()
    
    flash('Чек отправлен! Администратор проверит оплату в ближайшее время.', 'success')
    return redirect(url_for('order_status', order_num=order_num))

@app.route('/status/<order_num>')
def order_status(order_num):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_num=?", (order_num,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        flash('Заказ не найден!', 'error')
        return redirect(url_for('index'))
    
    return render_template_string(HTML_TEMPLATE + STATUS_PAGE,
                                site_name=SITE_NAME,
                                order=order,
                                format_price=format_price)

@app.route('/check-order', methods=['POST'])
def check_order():
    order_num = request.form.get('order_num')
    return redirect(url_for('order_status', order_num=order_num))

@app.route('/check')
def check_page():
    return render_template_string(HTML_TEMPLATE + '''
    {% extends "base.html" %}
    {% block content %}
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>🔍 Проверка заказа</h1>
            <p>Введите номер заказа для проверки статуса</p>
        </div>
        <div class="glass-card form-container">
            <form method="post" action="/check-order">
                <div class="form-group">
                    <input type="text" name="order_num" placeholder="Номер заказа" required>
                </div>
                <button type="submit" class="btn" style="width: 100%;">Проверить</button>
            </form>
        </div>
    </div>
    {% endblock %}
    ''', site_name=SITE_NAME)

# ==================== АДМИН МАРШРУТЫ ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admin WHERE username=? AND password_hash=?", (username, password_hash))
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Неверный логин или пароль!', 'error')
    
    return render_template_string(HTML_TEMPLATE + ADMIN_LOGIN_PAGE, site_name=SITE_NAME)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
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
    
    conn.close()
    
    return render_template_string(HTML_TEMPLATE + ADMIN_DASHBOARD,
                                site_name=SITE_NAME,
                                total_orders=total_orders,
                                new_orders=new_orders,
                                completed_orders=completed_orders,
                                total_income=total_income,
                                orders=orders,
                                format_price=format_price)

@app.route('/admin/order/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    new_status = request.form.get('status')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()
    conn.close()
    
    flash('Статус заказа обновлен!', 'success')
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
        flash('Реквизиты обновлены!', 'success')
    
    cursor.execute("SELECT card_number, wallet_number, instruction FROM payments LIMIT 1")
    payments = cursor.fetchone()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE + ADMIN_PAYMENTS,
                                site_name=SITE_NAME,
                                card=payments['card_number'] if payments else '',
                                wallet=payments['wallet_number'] if payments else '',
                                instruction=payments['instruction'] if payments else '')

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    init_db()
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║              🛡️  DiSK Delovoi UC  🛡️                       ║
║                                                              ║
║         💎 Стиль: Apple Glassmorphism                        ║
║                                                              ║
║         🔗 Админ-панель: http://localhost:5000/admin        ║
║         👤 Логин: admin                                     ║
║         🔑 Пароль: admin123                                 ║
║                                                              ║
║         ⚠️  ИЗМЕНИТЕ СЕКРЕТНЫЙ КЛЮЧ! ⚠️                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)
