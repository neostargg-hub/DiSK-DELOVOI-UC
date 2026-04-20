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

# ==================== HTML ТЕМПЛЕЙТ ====================
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>DiSK Delovoi UC - Покупка UC для PUBG Mobile</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0c29 0%, #1a1a3e 50%, #24243e 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }
        
        /* Анимированный фон - яркие летающие элементы */
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
        
        .floating-uc {
            position: absolute;
            font-family: 'Orbitron', monospace;
            font-weight: 900;
            font-size: 45px;
            opacity: 0.25;
            animation: floatUC 12s infinite ease-in-out;
            text-shadow: 0 0 15px rgba(168,85,247,0.6);
        }
        
        @keyframes floatUC {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.25; }
            80% { opacity: 0.25; }
            100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
        }
        
        .floating-number {
            position: absolute;
            font-family: 'Orbitron', monospace;
            font-weight: 700;
            font-size: 28px;
            opacity: 0.2;
            animation: floatNumber 15s infinite ease-in-out;
            text-shadow: 0 0 10px rgba(232,121,249,0.5);
        }
        
        @keyframes floatNumber {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.2; }
            80% { opacity: 0.2; }
            100% { transform: translateY(-150px) rotate(360deg); opacity: 0; }
        }
        
        .floating-shape {
            position: absolute;
            opacity: 0.15;
            animation: floatShape 20s infinite linear;
        }
        
        @keyframes floatShape {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.15; }
            80% { opacity: 0.15; }
            100% { transform: translateY(-200px) rotate(720deg); opacity: 0; }
        }
        
        /* Солнце в углу */
        .sun {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 80px;
            height: 80px;
            background: radial-gradient(circle, #fbbf24, #f59e0b, #d97706);
            border-radius: 50%;
            z-index: 50;
            box-shadow: 0 0 50px rgba(251,191,36,0.5);
            animation: sunGlow 3s infinite alternate;
            cursor: pointer;
        }
        
        @keyframes sunGlow {
            0% { box-shadow: 0 0 20px rgba(251,191,36,0.3); transform: scale(1); }
            100% { box-shadow: 0 0 60px rgba(251,191,36,0.8); transform: scale(1.05); }
        }
        
        /* Боковое меню */
        .menu-toggle {
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
            transition: all 0.3s;
        }
        
        .menu-toggle:hover {
            transform: scale(1.05);
        }
        
        .side-menu {
            position: fixed;
            top: 0;
            left: -300px;
            width: 280px;
            height: 100%;
            background: rgba(15, 12, 41, 0.98);
            backdrop-filter: blur(20px);
            z-index: 150;
            transition: left 0.4s ease;
            border-right: 1px solid rgba(168,85,247,0.3);
            padding: 80px 20px 30px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .side-menu.open {
            left: 0;
        }
        
        .side-menu a {
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            padding: 12px 20px;
            border-radius: 12px;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 16px;
        }
        
        .side-menu a:hover {
            background: rgba(168,85,247,0.2);
            color: #c084fc;
            transform: translateX(5px);
        }
        
        .side-menu .close-menu {
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 24px;
            cursor: pointer;
            color: rgba(255,255,255,0.6);
        }
        
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
        
        .overlay.active {
            display: block;
        }
        
        .navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            padding: 16px 32px;
            background: rgba(15, 12, 41, 0.9);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(168,85,247,0.3);
        }
        
        .nav-container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .logo {
            font-family: 'Orbitron', monospace;
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, #a855f7, #e879f9, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 2px;
        }
        
        .hero {
            padding: 120px 24px 70px;
            text-align: center;
            position: relative;
            z-index: 1;
        }
        
        .hero h1 {
            font-family: 'Orbitron', monospace;
            font-size: 64px;
            font-weight: 800;
            background: linear-gradient(135deg, #fff, #a855f7, #e879f9, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        
        .hero p {
            font-size: 18px;
            color: rgba(255, 255, 255, 0.7);
            max-width: 600px;
            margin: 0 auto;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 24px;
            position: relative;
            z-index: 1;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 25px;
            margin-bottom: 70px;
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            border-radius: 28px;
            border: 1px solid rgba(168,85,247,0.25);
            padding: 30px 20px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .glass-card:hover {
            transform: translateY(-8px);
            border-color: #a855f7;
            box-shadow: 0 20px 40px rgba(168,85,247,0.2);
            background: rgba(255,255,255,0.08);
        }
        
        .feature-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .catalog-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
            margin-bottom: 70px;
        }
        
        .product-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            border-radius: 28px;
            border: 1px solid rgba(168,85,247,0.25);
            padding: 28px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .product-card:hover {
            transform: translateY(-5px);
            border-color: #a855f7;
            box-shadow: 0 15px 35px rgba(168,85,247,0.2);
        }
        
        .product-amount {
            font-family: 'Orbitron', monospace;
            font-size: 34px;
            font-weight: 800;
            color: #c084fc;
            margin-bottom: 10px;
        }
        
        .product-price {
            font-size: 26px;
            font-weight: 600;
            margin-bottom: 20px;
        }
        
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
            transition: all 0.3s;
            font-size: 15px;
        }
        
        .btn:hover {
            transform: scale(1.03);
            box-shadow: 0 8px 25px rgba(168,85,247,0.4);
        }
        
        .form-container {
            max-width: 550px;
            margin: 0 auto;
            padding: 40px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(12px);
            border-radius: 32px;
            border: 1px solid rgba(168,85,247,0.25);
        }
        
        .form-group {
            margin-bottom: 22px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            color: rgba(255, 255, 255, 0.7);
        }
        
        .form-group input, .form-group textarea, .form-group select {
            width: 100%;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(168,85,247,0.3);
            border-radius: 18px;
            color: white;
            font-size: 15px;
        }
        
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #a855f7;
            box-shadow: 0 0 12px rgba(168,85,247,0.3);
        }
        
        .payment-info {
            background: linear-gradient(135deg, rgba(168,85,247,0.12), rgba(232,121,249,0.08));
            border-radius: 24px;
            padding: 24px;
            margin: 25px 0;
            border: 1px solid rgba(168,85,247,0.3);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 24px;
            padding: 24px;
            text-align: center;
            border: 1px solid rgba(168,85,247,0.25);
        }
        
        .stat-number {
            font-family: 'Orbitron', monospace;
            font-size: 38px;
            font-weight: 700;
            color: #c084fc;
        }
        
        .admin-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 40px;
            flex-wrap: wrap;
        }
        
        .orders-table {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 24px;
            padding: 24px;
            overflow-x: auto;
            border: 1px solid rgba(168,85,247,0.25);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 14px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }
        
        th {
            color: #c084fc;
        }
        
        .flash-message {
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
            color: rgba(255, 255, 255, 0.4);
            position: relative;
            z-index: 1;
        }
        
        /* Чат виджет */
        .chat-widget {
            position: fixed;
            bottom: 30px;
            right: 30px;
            z-index: 200;
        }
        
        .chat-button {
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #a855f7, #e879f9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            box-shadow: 0 5px 25px rgba(168,85,247,0.5);
        }
        
        .chat-window {
            position: absolute;
            bottom: 80px;
            right: 0;
            width: 350px;
            height: 480px;
            background: rgba(15, 12, 41, 0.98);
            backdrop-filter: blur(20px);
            border-radius: 28px;
            border: 1px solid rgba(168,85,247,0.35);
            display: none;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-window.open {
            display: flex;
        }
        
        .chat-header {
            padding: 18px;
            background: linear-gradient(135deg, rgba(168,85,247,0.2), rgba(232,121,249,0.1));
            border-bottom: 1px solid rgba(168,85,247,0.3);
            display: flex;
            justify-content: space-between;
        }
        
        .chat-messages {
            flex: 1;
            padding: 16px;
            overflow-y: auto;
        }
        
        .chat-message {
            margin-bottom: 12px;
            padding: 10px 14px;
            border-radius: 18px;
            max-width: 85%;
        }
        
        .chat-message.user {
            background: linear-gradient(135deg, #a855f7, #e879f9);
            margin-left: auto;
        }
        
        .chat-message.support {
            background: rgba(255, 255, 255, 0.1);
            margin-right: auto;
        }
        
        .chat-input {
            display: flex;
            padding: 16px;
            border-top: 1px solid rgba(168,85,247,0.25);
            gap: 10px;
        }
        
        .chat-input input {
            flex: 1;
            padding: 12px;
            background: rgba(255, 255, 255, 0.08);
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
        
        .badge {
            background: #e879f9;
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 12px;
        }
        
        @media (max-width: 768px) {
            .hero h1 { font-size: 40px; }
            .features-grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: 1fr; }
            .catalog-grid { grid-template-columns: 1fr; }
            .chat-window { width: 300px; height: 450px; right: -10px; }
            .sun { width: 50px; height: 50px; top: 15px; right: 15px; }
        }
        
        select, option {
            background: #1e1b4b;
            color: white;
        }
    </style>
</head>
<body>
    <div class="sun"></div>
    
    <div class="menu-toggle" onclick="toggleMenu()">
        <i class="fas fa-bars" style="font-size: 24px; color: white;"></i>
    </div>
    
    <div class="side-menu" id="sideMenu">
        <div class="close-menu" onclick="toggleMenu()">✕</div>
        <a href="/"><i class="fas fa-home"></i> Главная</a>
        <a href="/catalog"><i class="fas fa-store"></i> Каталог UC</a>
        <a href="/check"><i class="fas fa-search"></i> Проверить заказ</a>
        <a href="/support"><i class="fas fa-headset"></i> Поддержка</a>
        <hr style="margin: 10px 0; border-color: rgba(168,85,247,0.3);">
        <a href="/admin"><i class="fas fa-crown"></i> Админ-панель</a>
    </div>
    
    <div class="overlay" id="overlay" onclick="toggleMenu()"></div>
    
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo"><i class="fas fa-dragon"></i> DiSK Delovoi UC</div>
        </div>
    </nav>
'''

BASE_FOOTER = '''
    <div class="chat-widget">
        <div class="chat-button" onclick="toggleChat()">
            <i class="fas fa-headset" style="font-size: 26px;"></i>
        </div>
        <div class="chat-window" id="chatWindow">
            <div class="chat-header">
                <strong><i class="fas fa-headset"></i> Поддержка DiSK</strong>
                <span onclick="toggleChat()" style="cursor: pointer;">✕</span>
            </div>
            <div class="chat-messages" id="chatMessages">
                <div class="chat-message support">
                    <i class="fas fa-robot"></i> Привет! Я помощник. Напишите ваш вопрос!
                </div>
            </div>
            <div class="chat-input">
                <input type="text" id="chatInput" placeholder="Введите сообщение..." onkeypress="if(event.key==='Enter') sendMessage()">
                <button onclick="sendMessage()"><i class="fas fa-paper-plane"></i></button>
            </div>
        </div>
    </div>
    
    <div class="animated-bg" id="animatedBg"></div>
    
    <div class="footer">
        <p>© 2024 DiSK Delovoi UC. Все права защищены.</p>
        <p>⚡ Киберпространство ждёт тебя | UC для PUBG Mobile</p>
    </div>
    
    <script>
        // Создание летающих элементов
        const ucLetters = ['U', 'C', 'UC', '60', '120', '180', '325', '660', '1320', '1800', '3850', '8100', '▲', '●', '◆', '★'];
        
        for (let i = 0; i < 50; i++) {
            const el = document.createElement('div');
            const item = ucLetters[Math.floor(Math.random() * ucLetters.length)];
            const isUC = item === 'U' || item === 'C' || item === 'UC';
            
            if (isUC) {
                el.className = 'floating-uc';
                el.innerHTML = item;
                el.style.fontSize = (Math.random() * 40 + 30) + 'px';
                el.style.color = `rgba(168, 85, 247, ${Math.random() * 0.3 + 0.15})`;
            } else if (item === '▲' || item === '●' || item === '◆' || item === '★') {
                el.className = 'floating-shape';
                el.innerHTML = item;
                el.style.fontSize = (Math.random() * 30 + 20) + 'px';
                el.style.color = `rgba(232, 121, 249, ${Math.random() * 0.3 + 0.15})`;
            } else {
                el.className = 'floating-number';
                el.innerHTML = item + ' UC';
                el.style.fontSize = (Math.random() * 25 + 18) + 'px';
                el.style.color = `rgba(251, 191, 36, ${Math.random() * 0.3 + 0.15})`;
            }
            
            el.style.left = Math.random() * 100 + '%';
            el.style.animationDelay = Math.random() * 12 + 's';
            el.style.animationDuration = (Math.random() * 12 + 8) + 's';
            document.getElementById('animatedBg').appendChild(el);
        }
        
        // Меню
        function toggleMenu() {
            const menu = document.getElementById('sideMenu');
            const overlay = document.getElementById('overlay');
            menu.classList.toggle('open');
            overlay.classList.toggle('active');
        }
        
        // Чат
        function toggleChat() {
            const chatWindow = document.getElementById('chatWindow');
            chatWindow.classList.toggle('open');
        }
        
        function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            if (!message) return;
            
            const messagesDiv = document.getElementById('chatMessages');
            const userMsg = document.createElement('div');
            userMsg.className = 'chat-message user';
            userMsg.innerHTML = '<i class="fas fa-user"></i> ' + escapeHtml(message);
            messagesDiv.appendChild(userMsg);
            
            fetch('/support/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'message=' + encodeURIComponent(message)
            });
            
            const supportMsg = document.createElement('div');
            supportMsg.className = 'chat-message support';
            supportMsg.innerHTML = '<i class="fas fa-robot"></i> Спасибо! Мы ответим вам.';
            messagesDiv.appendChild(supportMsg);
            
            input.value = '';
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
    <script src="https://kit.fontawesome.com/a2b8d7c8c1.js" crossorigin="anonymous"></script>
</body>
</html>
'''

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    content = '''
    <div class="hero">
        <h1><i class="fas fa-gem"></i> DiSK Delovoi UC</h1>
        <p>Безопасная покупка UC для PUBG Mobile в киберпространстве</p>
    </div>
    <div class="container">
        <div class="features-grid">
            <div class="glass-card"><div class="feature-icon"><i class="fas fa-shield-alt"></i></div><h3>100% Безопасность</h3><p>Гарантия получения UC</p></div>
            <div class="glass-card"><div class="feature-icon"><i class="fas fa-bolt"></i></div><h3>Мгновенная доставка</h3><p>UC приходят сразу</p></div>
            <div class="glass-card"><div class="feature-icon"><i class="fas fa-tag"></i></div><h3>Лучшие цены</h3><p>Низкие цены на рынке</p></div>
            <div class="glass-card"><div class="feature-icon"><i class="fas fa-clock"></i></div><h3>Поддержка 24/7</h3><p>Поможем в любой ситуации</p></div>
        </div>
        <div style="text-align: center; margin-bottom: 60px;">
            <a href="/catalog" class="btn"><i class="fas fa-rocket"></i> Войти в каталог UC</a>
        </div>
        <div class="glass-card" style="padding: 40px; text-align: center;">
            <h3><i class="fas fa-search"></i> Проверить статус заказа</h3>
            <form method="post" action="/check-order" style="max-width: 400px; margin: 20px auto 0;">
                <div class="form-group">
                    <input type="text" name="order_num" placeholder="Введите номер заказа" required>
                </div>
                <button type="submit" class="btn">Проверить</button>
            </form>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

@app.route('/catalog')
def catalog():
    items = ''
    for amount, price in UC_PRICES.items():
        items += f'''
        <div class="product-card">
            <div class="product-amount">{amount} UC</div>
            <div class="product-price">{format_price(price)} ₽</div>
            <a href="/order/{amount}" class="btn"><i class="fas fa-shopping-cart"></i> Купить</a>
        </div>
        '''
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-store"></i> Каталог UC</h1>
            <p>Выберите нужное количество UC</p>
        </div>
        <div class="catalog-grid">{items}</div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

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
            flash('Пожалуйста, заполните все обязательные поля!')
            return redirect(url_for('order', amount=amount))
        
        order_num = generate_order_num()
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO orders (order_num, user_name, user_phone, user_email, game_id, uc_amount, uc_price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
        ''', (order_num, user_name, user_phone, user_email, game_id, amount, price))
        conn.commit()
        conn.close()
        
        # Перенаправляем на страницу оплаты
        return redirect(url_for('payment', order_num=order_num))
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-file-alt"></i> Оформление заказа</h1>
        </div>
        <div class="form-container">
            <div style="text-align: center; margin-bottom: 30px;">
                <div class="product-amount">{amount} UC</div>
                <div class="product-price">{format_price(price)} ₽</div>
            </div>
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
                    <input type="text" name="game_id" required placeholder="Введите ваш игровой ID">
                </div>
                <button type="submit" class="btn" style="width: 100%;"><i class="fas fa-credit-card"></i> Перейти к оплате</button>
            </form>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

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
        flash('Заказ не найден!')
        return redirect(url_for('catalog'))
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-credit-card"></i> Оплата заказа</h1>
            <p>Заказ #{order_num}</p>
        </div>
        <div class="form-container">
            <div style="text-align: center; margin-bottom: 30px;">
                <div class="product-amount">{order['uc_amount']} UC</div>
                <div class="product-price">{format_price(order['uc_price'])} ₽</div>
                <p><i class="fas fa-gamepad"></i> ID: {order['game_id']}</p>
            </div>
            
            <div class="payment-info">
                <h3><i class="fas fa-credit-card"></i> Реквизиты для оплаты</h3>
                <p><strong>Карта:</strong> {payment['card_number'] or 'Не указана'}</p>
                <p><strong>Кошелек:</strong> {payment['wallet_number'] or 'Не указан'}</p>
                <p><strong>Инструкция:</strong> {payment['instruction']}</p>
                <p style="margin-top: 16px; color: #f472b6;"><i class="fas fa-exclamation-triangle"></i> Важно: Переведите точную сумму {format_price(order['uc_price'])} ₽</p>
            </div>
            
            <form method="post" action="/payment-proof/{order_num}" enctype="multipart/form-data">
                <div class="form-group">
                    <label><i class="fas fa-image"></i> Прикрепите чек</label>
                    <input type="file" name="proof_file" accept="image/*">
                </div>
                <div class="form-group">
                    <label><i class="fas fa-pen"></i> Или введите текст подтверждения</label>
                    <textarea name="proof_text" rows="3" placeholder="Номер транзакции, дата, сумма..."></textarea>
                </div>
                <button type="submit" class="btn" style="width: 100%;"><i class="fas fa-paper-plane"></i> Отправить чек</button>
            </form>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

@app.route('/payment-proof/<order_num>', methods=['POST'])
def payment_proof(order_num):
    proof_text = request.form.get('proof_text', 'Чек отправлен')
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET payment_proof=?, status='waiting_confirm' WHERE order_num=?", 
                  (proof_text, order_num))
    conn.commit()
    conn.close()
    
    flash('Чек отправлен! Администратор проверит оплату.')
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
    
    status_text = "🆕 Новый" if order['status'] == 'new' else "⏳ Ожидает" if order['status'] == 'waiting_confirm' else "✅ Завершен" if order['status'] == 'completed' else "❌ Отменен"
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-clipboard-list"></i> Статус заказа</h1>
            <p>Заказ #{order_num}</p>
        </div>
        <div class="glass-card" style="padding: 40px; max-width: 600px; margin: 0 auto; text-align: center;">
            <div class="product-amount">{order['uc_amount']} UC</div>
            <div class="product-price">{format_price(order['uc_price'])} ₽</div>
            <p><i class="fas fa-gamepad"></i> ID: {order['game_id']}</p>
            <p><i class="fas fa-calendar"></i> {order['created_at'][:19]}</p>
            <div style="margin: 25px 0; padding: 15px; border-radius: 20px; background: rgba(168,85,247,0.1);">
                <strong>Статус:</strong> {status_text}
            </div>
            <a href="/catalog" class="btn"><i class="fas fa-shopping-cart"></i> Продолжить покупки</a>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

@app.route('/check-order', methods=['POST'])
def check_order():
    order_num = request.form.get('order_num')
    return redirect(url_for('order_status', order_num=order_num))

@app.route('/check')
def check_page():
    content = '''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-search"></i> Проверка заказа</h1>
        </div>
        <div class="form-container">
            <form method="post" action="/check-order">
                <div class="form-group">
                    <input type="text" name="order_num" placeholder="Номер заказа" required>
                </div>
                <button type="submit" class="btn" style="width: 100%;"><i class="fas fa-search"></i> Проверить</button>
            </form>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

@app.route('/support')
def support_page():
    content = '''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-headset"></i> Служба поддержки</h1>
        </div>
        <div class="form-container">
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
                    <textarea name="message" rows="5" required></textarea>
                </div>
                <button type="submit" class="btn" style="width: 100%;"><i class="fas fa-paper-plane"></i> Отправить</button>
            </form>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

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
        flash('Сообщение отправлено! Мы ответим вам.')
    else:
        flash('Пожалуйста, заполните все поля!')
    
    return redirect(url_for('support_page'))

# ==================== АДМИН-ПАНЕЛЬ ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
        
        if username == 'admin' and password_hash == admin_hash:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Неверный логин или пароль!'
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 120px;">
            <h1><i class="fas fa-crown"></i> Вход в админ-панель</h1>
        </div>
        <div class="form-container">
            {f'<div class="flash-message">{error}</div>' if error else ''}
            <form method="post">
                <div class="form-group">
                    <label>Логин</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>Пароль</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn" style="width: 100%;"><i class="fas fa-sign-in-alt"></i> Войти</button>
            </form>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

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
    support_messages = cursor.fetchall()
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
                    <select name="status" style="padding: 6px 12px; border-radius: 12px;">
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
    for msg in support_messages:
        messages_html += f'''
        <tr>
            <td>{msg['created_at'][:16]}</td>
            <td>{msg['user_name']}</td>
            <td>{msg['user_email']}</td>
            <td>{msg['message'][:80]}...</td>
            <td>{"🆕 Новое" if msg['status'] == 'new' else "✅ Прочитано"}</td>
        </tr>
        '''
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-crown"></i> Админ-панель</h1>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">{total_orders}</div><p>Всего заказов</p></div>
            <div class="stat-card"><div class="stat-number">{new_orders}</div><p>Новых заказов</p></div>
            <div class="stat-card"><div class="stat-number">{completed_orders}</div><p>Завершено</p></div>
            <div class="stat-card"><div class="stat-number">{format_price(total_income)} ₽</div><p>Оборот</p></div>
        </div>
        
        <div class="admin-actions">
            <a href="/admin/payments" class="btn btn-outline"><i class="fas fa-credit-card"></i> Реквизиты</a>
            <a href="/admin/messages" class="btn btn-outline"><i class="fas fa-envelope"></i> Сообщения <span class="badge">{new_messages}</span></a>
            <a href="/admin/logout" class="btn btn-outline"><i class="fas fa-sign-out-alt"></i> Выйти</a>
        </div>
        
        <div class="orders-table">
            <h3><i class="fas fa-box"></i> Список заказов</h3>
            <div style="overflow-x: auto;">
                <table><thead><tr><th>№</th><th>Покупатель</th><th>UC</th><th>Сумма</th><th>Статус</th><th>Действия</th></tr></thead>
                <tbody>{orders_html}</tbody></table>
            </div>
        </div>
        
        <div class="orders-table" style="margin-top: 30px;">
            <h3><i class="fas fa-comments"></i> Сообщения поддержки</h3>
            <div style="overflow-x: auto;">
                <table><thead><tr><th>Дата</th><th>Имя</th><th>Email</th><th>Сообщение</th><th>Статус</th></tr></thead>
                <tbody>{messages_html}</tbody></table>
            </div>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

@app.route('/admin/order/<int:order_id>', methods=['POST'])
@admin_required
def admin_update_order(order_id):
    new_status = request.form.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()
    conn.close()
    flash('Статус заказа обновлен!')
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
        flash('Реквизиты обновлены!')
    
    cursor.execute("SELECT card_number, wallet_number, instruction FROM payments LIMIT 1")
    payment = cursor.fetchone()
    conn.close()
    
    msg = '<div class="flash-message">Реквизиты обновлены!</div>' if request.method == 'POST' else ''
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-credit-card"></i> Настройка реквизитов</h1>
        </div>
        <div class="form-container">
            {msg}
            <form method="post">
                <div class="form-group">
                    <label>Номер карты</label>
                    <input type="text" name="card_number" value="{payment['card_number'] or ''}" placeholder="1234 5678 9012 3456">
                </div>
                <div class="form-group">
                    <label>Номер кошелька</label>
                    <input type="text" name="wallet_number" value="{payment['wallet_number'] or ''}" placeholder="+7 999 123-45-67">
                </div>
                <div class="form-group">
                    <label>Инструкция по оплате</label>
                    <textarea name="instruction" rows="4">{payment['instruction'] or ''}</textarea>
                </div>
                <button type="submit" class="btn" style="width: 100%;"><i class="fas fa-save"></i> Сохранить</button>
            </form>
            <div style="text-align: center; margin-top: 20px;"><a href="/admin">← Назад</a></div>
        </div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

@app.route('/admin/messages')
@admin_required
def admin_messages():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM support_messages ORDER BY created_at DESC")
    messages = cursor.fetchall()
    cursor.execute("UPDATE support_messages SET status='read'")
    conn.commit()
    conn.close()
    
    messages_html = ''
    for msg in messages:
        messages_html += f'''
        <div class="glass-card" style="margin-bottom: 16px; padding: 20px;">
            <p><strong><i class="fas fa-calendar"></i> {msg['created_at'][:19]}</strong></p>
            <p><strong><i class="fas fa-user"></i> {msg['user_name']}</strong> ({msg['user_email']})</p>
            <p><i class="fas fa-comment"></i> {msg['message']}</p>
        </div>
        '''
    
    content = f'''
    <div class="container">
        <div class="hero" style="padding-top: 110px;">
            <h1><i class="fas fa-envelope"></i> Сообщения поддержки</h1>
        </div>
        {messages_html if messages_html else '<div class="glass-card" style="padding: 40px; text-align: center;">📭 Нет сообщений</div>'}
        <div style="text-align: center; margin-top: 30px;"><a href="/admin" class="btn">← Назад</a></div>
    </div>
    '''
    return BASE_TEMPLATE + content + BASE_FOOTER

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
