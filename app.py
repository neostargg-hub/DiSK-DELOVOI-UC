from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
import random
import string
import hashlib
import os
from functools import wraps

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
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password_hash TEXT
    )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM admin WHERE username='admin'")
    if cursor.fetchone()[0] == 0:
        password_hash = hashlib.sha256('admin123'.encode()).hexdigest()
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DiSK Delovoi UC - Покупка UC для PUBG Mobile</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: radial-gradient(ellipse at center, #0a0a2a 0%, #050510 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }
        
        /* Летающие буквы UC */
        .floating-uc {
            position: fixed;
            font-family: 'Orbitron', monospace;
            font-weight: 900;
            font-size: 50px;
            pointer-events: none;
            z-index: 0;
            animation: floatUC 12s infinite ease-in-out;
            text-shadow: 0 0 20px rgba(124, 58, 237, 0.5);
        }
        
        @keyframes floatUC {
            0% { transform: translateY(100vh) rotate(0deg); opacity: 0; }
            10% { opacity: 0.3; }
            50% { opacity: 0.5; }
            90% { opacity: 0.3; }
            100% { transform: translateY(-100px) rotate(360deg); opacity: 0; }
        }
        
        /* Треугольники */
        .triangle {
            position: fixed;
            width: 0;
            height: 0;
            border-left: 25px solid transparent;
            border-right: 25px solid transparent;
            border-bottom: 45px solid rgba(124, 58, 237, 0.15);
            pointer-events: none;
            z-index: 0;
            animation: spin 20s infinite linear;
        }
        
        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* Шарики */
        .orb {
            position: fixed;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, rgba(124,58,237,0.2), rgba(0,0,0,0));
            pointer-events: none;
            z-index: 0;
            animation: pulse 6s infinite ease-in-out;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.3; }
            50% { transform: scale(1.3); opacity: 0.6; }
        }
        
        .navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            padding: 16px 32px;
            background: rgba(10, 10, 30, 0.9);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid rgba(124, 58, 237, 0.3);
        }
        
        .nav-container {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-family: 'Orbitron', monospace;
            font-size: 28px;
            font-weight: 800;
            background: linear-gradient(135deg, #a8b5e6 0%, #7c3aed 50%, #ff6b6b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 2px;
        }
        
        .nav-links {
            display: flex;
            gap: 32px;
        }
        
        .nav-links a {
            color: rgba(255, 255, 255, 0.8);
            text-decoration: none;
            transition: all 0.3s;
        }
        
        .nav-links a:hover {
            color: #7c3aed;
            text-shadow: 0 0 10px rgba(124, 58, 237, 0.5);
        }
        
        .hero {
            padding: 160px 24px 100px;
            text-align: center;
            position: relative;
            z-index: 1;
        }
        
        .hero h1 {
            font-family: 'Orbitron', monospace;
            font-size: 72px;
            font-weight: 800;
            background: linear-gradient(135deg, #fff 0%, #a8b5e6 30%, #7c3aed 60%, #ff6b6b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 24px;
        }
        
        .hero p {
            font-size: 20px;
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
            gap: 30px;
            margin-bottom: 80px;
        }
        
        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            border: 1px solid rgba(124, 58, 237, 0.2);
            padding: 32px 24px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .glass-card:hover {
            transform: translateY(-10px);
            border-color: rgba(124, 58, 237, 0.5);
            box-shadow: 0 20px 40px rgba(124, 58, 237, 0.2);
        }
        
        .feature-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        
        .catalog-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 30px;
            margin-bottom: 80px;
        }
        
        .product-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border-radius: 24px;
            border: 1px solid rgba(124, 58, 237, 0.2);
            padding: 32px;
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .product-card:hover {
            transform: translateY(-5px);
            border-color: #7c3aed;
            box-shadow: 0 10px 30px rgba(124, 58, 237, 0.3);
        }
        
        .product-amount {
            font-family: 'Orbitron', monospace;
            font-size: 36px;
            font-weight: 800;
            color: #a8b5e6;
            margin-bottom: 12px;
        }
        
        .product-price {
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 20px;
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
            box-shadow: 0 10px 20px rgba(124, 58, 237, 0.4);
        }
        
        .form-container {
            max-width: 550px;
            margin: 0 auto;
            padding: 40px;
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border-radius: 32px;
            border: 1px solid rgba(124, 58, 237, 0.2);
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
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 16px;
            color: white;
            font-size: 16px;
        }
        
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #7c3aed;
            box-shadow: 0 0 15px rgba(124, 58, 237, 0.3);
        }
        
        .payment-info {
            background: rgba(124, 58, 237, 0.1);
            border-radius: 20px;
            padding: 24px;
            margin: 20px 0;
            border: 1px solid rgba(124, 58, 237, 0.2);
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 24px;
            margin-bottom: 40px;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 24px;
            padding: 24px;
            text-align: center;
            border: 1px solid rgba(124, 58, 237, 0.2);
        }
        
        .stat-number {
            font-family: 'Orbitron', monospace;
            font-size: 36px;
            font-weight: 700;
            color: #a8b5e6;
        }
        
        .admin-actions {
            display: flex;
            gap: 16px;
            justify-content: center;
            margin-bottom: 40px;
        }
        
        .btn-outline {
            background: transparent;
            border: 1px solid rgba(124, 58, 237, 0.5);
        }
        
        .btn-outline:hover {
            background: rgba(124, 58, 237, 0.2);
        }
        
        .orders-table {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 24px;
            padding: 24px;
            overflow-x: auto;
            border: 1px solid rgba(124, 58, 237, 0.2);
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        th {
            color: #a8b5e6;
        }
        
        .flash-message {
            padding: 16px;
            border-radius: 16px;
            margin-bottom: 24px;
            background: rgba(124, 58, 237, 0.2);
            border: 1px solid rgba(124, 58, 237, 0.3);
            text-align: center;
        }
        
        .footer {
            text-align: center;
            padding: 40px 24px;
            border-top: 1px solid rgba(124, 58, 237, 0.2);
            margin-top: 80px;
            color: rgba(255, 255, 255, 0.4);
            position: relative;
            z-index: 1;
        }
        
        @media (max-width: 768px) {
            .hero h1 { font-size: 40px; }
            .features-grid { grid-template-columns: repeat(2, 1fr); }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .nav-links { display: none; }
            .catalog-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
'''

HTML_FOOT = '''
    <div class="footer">
        <p>© 2024 DiSK Delovoi UC. Все права защищены.</p>
        <p style="margin-top: 8px;">⚡ Киберпространство ждёт тебя ⚡</p>
    </div>
    
    <script>
        // Создание летающих объектов
        function createFloatingObjects() {
            const letters = ['U', 'C', '▲', '●', '◆', 'UC', '60', '120', '180', '325', '660', '1320', '1800'];
            
            for (let i = 0; i < 40; i++) {
                const obj = document.createElement('div');
                const randomObj = letters[Math.floor(Math.random() * letters.length)];
                
                if (randomObj === 'U' || randomObj === 'C' || randomObj === 'UC') {
                    obj.className = 'floating-uc';
                    obj.innerHTML = randomObj;
                    obj.style.fontSize = Math.random() * 40 + 30 + 'px';
                    obj.style.left = Math.random() * 100 + '%';
                    obj.style.animationDelay = Math.random() * 15 + 's';
                    obj.style.animationDuration = Math.random() * 15 + 10 + 's';
                    obj.style.color = `rgba(124, 58, 237, ${Math.random() * 0.3 + 0.1})`;
                } else if (randomObj === '▲') {
                    obj.className = 'triangle';
                    obj.style.left = Math.random() * 100 + '%';
                    obj.style.top = Math.random() * 100 + '%';
                    obj.style.animationDelay = Math.random() * 20 + 's';
                    obj.style.animationDuration = Math.random() * 20 + 15 + 's';
                    obj.style.borderBottomColor = `rgba(124, 58, 237, ${Math.random() * 0.2 + 0.05})`;
                } else if (randomObj === '●') {
                    obj.className = 'orb';
                    obj.style.width = Math.random() * 80 + 40 + 'px';
                    obj.style.height = obj.style.width;
                    obj.style.left = Math.random() * 100 + '%';
                    obj.style.top = Math.random() * 100 + '%';
                    obj.style.animationDelay = Math.random() * 8 + 's';
                    obj.style.animationDuration = Math.random() * 10 + 5 + 's';
                } else {
                    obj.className = 'floating-uc';
                    obj.innerHTML = randomObj;
                    obj.style.fontSize = Math.random() * 20 + 12 + 'px';
                    obj.style.left = Math.random() * 100 + '%';
                    obj.style.animationDelay = Math.random() * 15 + 's';
                    obj.style.animationDuration = Math.random() * 15 + 10 + 's';
                    obj.style.color = `rgba(168, 181, 230, ${Math.random() * 0.4 + 0.1})`;
                }
                
                document.body.appendChild(obj);
            }
        }
        
        createFloatingObjects();
    </script>
</body>
</html>
'''

# ==================== МАРШРУТЫ ====================
@app.route('/')
def index():
    return HTML_TEMPLATE + '''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/catalog">Каталог</a>
                <a href="/check">Проверить заказ</a>
                ''' + ("<a href='/admin'>Админ-панель</a>" if session.get('admin_logged_in') else "") + '''
            </div>
        </div>
    </nav>
    
    <div class="hero">
        <h1>🛡️ DISK Delovoi UC</h1>
        <p>Безопасная покупка UC для PUBG Mobile в киберпространстве</p>
    </div>
    
    <div class="container">
        <div class="features-grid">
            <div class="glass-card"><div class="feature-icon">🔒</div><h3>100% Безопасность</h3><p>Гарантия получения UC</p></div>
            <div class="glass-card"><div class="feature-icon">⚡</div><h3>Мгновенная доставка</h3><p>UC приходят сразу</p></div>
            <div class="glass-card"><div class="feature-icon">💰</div><h3>Лучшие цены</h3><p>Низкие цены на рынке</p></div>
            <div class="glass-card"><div class="feature-icon">🌐</div><h3>Поддержка 24/7</h3><p>Поможем в любой ситуации</p></div>
        </div>
        
        <div style="text-align: center; margin-bottom: 60px;">
            <a href="/catalog" class="btn">🚀 Войти в каталог UC</a>
        </div>
        
        <div class="glass-card" style="padding: 40px; text-align: center;">
            <h3 style="margin-bottom: 20px;">🔍 Проверить статус заказа</h3>
            <form method="post" action="/check-order" style="max-width: 400px; margin: 0 auto;">
                <div class="form-group">
                    <input type="text" name="order_num" placeholder="Введите номер заказа" required>
                </div>
                <button type="submit" class="btn">Проверить</button>
            </form>
        </div>
    </div>
    ''' + HTML_FOOT

@app.route('/catalog')
def catalog():
    items = ''
    for amount, price in UC_PRICES.items():
        items += f'''
        <div class="product-card">
            <div class="product-amount">{amount} UC</div>
            <div class="product-price">{format_price(price)} ₽</div>
            <a href="/order/{amount}" class="btn">Купить</a>
        </div>
        '''
    
    return HTML_TEMPLATE + '''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/catalog">Каталог</a>
                <a href="/check">Проверить заказ</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>🛒 Каталог UC</h1>
            <p>Выберите нужное количество UC для вашего аккаунта</p>
        </div>
        <div class="catalog-grid">
            ''' + items + '''
        </div>
    </div>
    ''' + HTML_FOOT

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
        INSERT INTO orders (order_num, user_name, user_phone, user_email, game_id, uc_amount, uc_price)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_num, user_name, user_phone, user_email, game_id, amount, price))
        conn.commit()
        conn.close()
        
        return redirect(url_for('payment', order_num=order_num))
    
    return HTML_TEMPLATE + f'''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/catalog">Каталог</a>
                <a href="/check">Проверить заказ</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>📝 Оформление заказа</h1>
        </div>
        <div class="form-container">
            <div style="text-align: center; margin-bottom: 30px;">
                <div class="product-amount">{amount} UC</div>
                <div class="product-price">{format_price(price)} ₽</div>
            </div>
            <form method="post">
                <div class="form-group">
                    <label>👤 Ваше имя *</label>
                    <input type="text" name="user_name" required placeholder="Иван Иванов">
                </div>
                <div class="form-group">
                    <label>📞 Телефон *</label>
                    <input type="tel" name="user_phone" required placeholder="+7 999 123-45-67">
                </div>
                <div class="form-group">
                    <label>📧 Email</label>
                    <input type="email" name="user_email" placeholder="ivan@example.com">
                </div>
                <div class="form-group">
                    <label>🎮 PUBG ID *</label>
                    <input type="text" name="game_id" required placeholder="Введите ваш игровой ID">
                </div>
                <button type="submit" class="btn" style="width: 100%;">✅ Перейти к оплате</button>
            </form>
        </div>
    </div>
    ''' + HTML_FOOT

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
    
    return HTML_TEMPLATE + f'''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/catalog">Каталог</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>💳 Оплата заказа</h1>
            <p>Заказ #{order_num}</p>
        </div>
        <div class="form-container">
            <div style="text-align: center; margin-bottom: 30px;">
                <div class="product-amount">{order['uc_amount']} UC</div>
                <div class="product-price">{format_price(order['uc_price'])} ₽</div>
                <p style="margin-top: 10px;">🎮 ID: {order['game_id']}</p>
            </div>
            
            <div class="payment-info">
                <h3 style="margin-bottom: 16px;">💳 Реквизиты для оплаты</h3>
                <p><strong>Карта:</strong> {payment['card_number'] or 'Не указана'}</p>
                <p><strong>Кошелек:</strong> {payment['wallet_number'] or 'Не указан'}</p>
                <p><strong>Инструкция:</strong> {payment['instruction']}</p>
                <p style="margin-top: 16px; color: #f87171;">⚠️ Важно: Переведите точную сумму {format_price(order['uc_price'])} ₽</p>
            </div>
            
            <form method="post" action="/payment-proof/{order_num}" enctype="multipart/form-data">
                <div class="form-group">
                    <label>📎 Прикрепите чек (скриншот или фото)</label>
                    <input type="file" name="proof_file" accept="image/*">
                </div>
                <div class="form-group">
                    <label>Или введите текст подтверждения</label>
                    <textarea name="proof_text" rows="3" placeholder="Номер транзакции, дата, сумма..."></textarea>
                </div>
                <button type="submit" class="btn" style="width: 100%;">📨 Отправить чек</button>
            </form>
        </div>
    </div>
    ''' + HTML_FOOT

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
        flash('Заказ не найден!')
        return redirect(url_for('catalog'))
    
    status_text = "🆕 Новый" if order['status'] == 'new' else "✅ Завершен" if order['status'] == 'completed' else "❌ Отменен"
    
    return HTML_TEMPLATE + f'''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/catalog">Каталог</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>📋 Статус заказа</h1>
            <p>Заказ #{order_num}</p>
        </div>
        <div class="glass-card" style="padding: 40px; max-width: 600px; margin: 0 auto; text-align: center;">
            <div class="product-amount">{order['uc_amount']} UC</div>
            <div class="product-price">{format_price(order['uc_price'])} ₽</div>
            <p style="margin-top: 16px;">🎮 ID: {order['game_id']}</p>
            <p style="margin-top: 8px;">📅 {order['created_at'][:19]}</p>
            <div style="margin: 20px 0; padding: 12px; border-radius: 16px; background: rgba(124,58,237,0.1);">
                <strong>Статус:</strong> {status_text}
            </div>
            <a href="/catalog" class="btn">🛒 Продолжить покупки</a>
        </div>
    </div>
    ''' + HTML_FOOT

@app.route('/check-order', methods=['POST'])
def check_order():
    order_num = request.form.get('order_num')
    return redirect(url_for('order_status', order_num=order_num))

@app.route('/check')
def check_page():
    return HTML_TEMPLATE + '''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/catalog">Каталог</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>🔍 Проверка заказа</h1>
            <p>Введите номер заказа для проверки статуса</p>
        </div>
        <div class="form-container">
            <form method="post" action="/check-order">
                <div class="form-group">
                    <input type="text" name="order_num" placeholder="Номер заказа" required>
                </div>
                <button type="submit" class="btn" style="width: 100%;">Проверить</button>
            </form>
        </div>
    </div>
    ''' + HTML_FOOT

# ==================== АДМИН-ПАНЕЛЬ ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
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
            error = 'Неверный логин или пароль!'
    
    return HTML_TEMPLATE + f'''
    <div class="container">
        <div class="hero" style="padding-top: 120px;">
            <h1>👑 Вход в админ-панель</h1>
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
                <button type="submit" class="btn" style="width: 100%;">Войти</button>
            </form>
        </div>
    </div>
    ''' + HTML_FOOT

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
    conn.close()
    
    orders_html = ''
    for order in orders:
        status_class = 'Новый' if order['status'] == 'new' else 'Завершен' if order['status'] == 'completed' else 'Отменен'
        orders_html += f'''
        <tr>
            <td>{order['order_num']}</td>
            <td>{order['user_name']}</td>
            <td>{order['uc_amount']}</td>
            <td>{format_price(order['uc_price'])} ₽</td>
            <td>{status_class}</td>
            <td>
                <form method="post" action="/admin/order/{order['id']}" style="display: flex; gap: 8px;">
                    <select name="status" style="background: rgba(255,255,255,0.1); border: 1px solid rgba(124,58,237,0.3); padding: 6px 12px; border-radius: 12px; color: white;">
                        <option value="new">Новый</option>
                        <option value="completed">Завершен</option>
                        <option value="cancelled">Отменен</option>
                    </select>
                    <button type="submit" class="btn" style="padding: 6px 16px;">Обновить</button>
                </form>
            </td>
        </tr>
        '''
    
    return HTML_TEMPLATE + f'''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/">Главная</a>
                <a href="/admin/logout">Выйти</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>👑 Админ-панель</h1>
            <p>Управление заказами и реквизитами</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card"><div class="stat-number">{total_orders}</div><p>Всего заказов</p></div>
            <div class="stat-card"><div class="stat-number">{new_orders}</div><p>Новых заказов</p></div>
            <div class="stat-card"><div class="stat-number">{completed_orders}</div><p>Завершено</p></div>
            <div class="stat-card"><div class="stat-number">{format_price(total_income)} ₽</div><p>Оборот</p></div>
        </div>
        
        <div class="admin-actions">
            <a href="/admin/payments" class="btn btn-outline">💳 Реквизиты</a>
            <a href="/admin/logout" class="btn btn-outline">🚪 Выйти</a>
        </div>
        
        <div class="orders-table">
            <h3 style="margin-bottom: 20px;">📋 Список заказов</h3>
            <table>
                <thead>
                    <tr><th>№</th><th>Покупатель</th><th>UC</th><th>Сумма</th><th>Статус</th><th>Действия</th></tr>
                </thead>
                <tbody>{orders_html}</tbody>
            </table>
        </div>
    </div>
    ''' + HTML_FOOT

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
        flash('Реквизиты обновлены!')
    
    cursor.execute("SELECT card_number, wallet_number, instruction FROM payments LIMIT 1")
    payment = cursor.fetchone()
    conn.close()
    
    msg = '<div class="flash-message">Реквизиты обновлены!</div>' if request.method == 'POST' else ''
    
    return HTML_TEMPLATE + f'''
    <nav class="navbar">
        <div class="nav-container">
            <div class="logo">DISK Delovoi UC</div>
            <div class="nav-links">
                <a href="/admin">Админ-панель</a>
                <a href="/admin/logout">Выйти</a>
            </div>
        </div>
    </nav>
    
    <div class="container">
        <div class="hero" style="padding-top: 100px;">
            <h1>💳 Настройка реквизитов</h1>
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
                <button type="submit" class="btn" style="width: 100%;">💾 Сохранить</button>
            </form>
            <div style="text-align: center; margin-top: 20px;"><a href="/admin" style="color: rgba(255,255,255,0.7);">← Назад</a></div>
        </div>
    </div>
    ''' + HTML_FOOT

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
