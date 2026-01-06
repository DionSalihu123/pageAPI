# apps.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_database, close_database, init_db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_strong_secret_key_change_this_now!'

# Initialize DB (creates tables if needed)
init_db(app)

@app.teardown_appcontext
def teardown_db(exception):
    close_database(exception)

def get_user_id():
    return session.get('user_id')

@app.route('/')
def index():
    db = get_database()
    cursor = db.cursor()

    # Load books from DB
    cursor.execute("""
        SELECT category, 
               GROUP_CONCAT(id || '|' || title || '|' || img || '|' || price, ',') AS book_data
        FROM books 
        GROUP BY category
    """)
    rows = cursor.fetchall()

    books = {}
    nav_categories = []

    for row in rows:
        category = row['category']
        book_strings = row['book_data'].split(',')

        book_list = []
        for b in book_strings:
            parts = b.split('|')
            if len(parts) == 4:
                book_id, title, img, price = parts
                book_list.append({"id": int(book_id), "title": title, "img": img, "price": price})

        books[category] = book_list
        nav_categories.append((
            category.lower().replace(' ', '-'),
            category.split()[0],
            category
        ))

    user_id = get_user_id()

    cart_count = 0
    favorites_count = 0
    favorite_ids = []

    if user_id:
        # Cart count
        cursor.execute("SELECT SUM(quantity) FROM cart WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        cart_count = row[0] or 0

        # Favorites
        cursor.execute("SELECT book_id FROM favorites WHERE user_id = ?", (user_id,))
        favorite_ids = [row['book_id'] for row in cursor.fetchall()]
        favorites_count = len(favorite_ids)

    return render_template(
        'index.html',
        books=books,
        nav_categories=nav_categories,
        cart_count=cart_count,
        favorites_count=favorites_count,
        favorite_ids=favorite_ids
    )

# === SIGNUP ===
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email'].lower()
        password = request.form['password']

        db = get_database()
        cursor = db.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            flash('Ky email është tashmë i regjistruar!', 'error')
            db.close()
            return redirect(url_for('signup'))

        hashed = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (name, surname, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (name, surname, email, hashed))
        db.commit()
        db.close()

        flash('Llogaria u krijua me sukses! Tani mund të kyçesh.', 'success')
        return redirect(url_for('login'))

    return render_template('sign.html')  # Your existing signup page

# === LOGIN ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']

        db = get_database()
        cursor = db.cursor()
        cursor.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        db.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = email
            flash('Ke hyrë me sukses!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ose fjalëkalim i gabuar!', 'error')

    return render_template('login.html')  # Your existing login page

# === LOGOUT ===
@app.route('/logout')
def logout():
    session.clear()
    flash('Ke dalë me sukses!', 'info')
    return redirect(url_for('index'))

# === CART ===
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    user_id = get_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Duhet të kyçesh së pari!'})

    data = request.get_json()
    book_id = data['book_id']

    db = get_database()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM cart WHERE user_id = ? AND book_id = ?", (user_id, book_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = ?", (existing['id'],))
    else:
        cursor.execute("INSERT INTO cart (user_id, book_id, quantity) VALUES (?, ?, 1)", (user_id, book_id))

    db.commit()
    db.close()
    return jsonify({'success': True, 'message': 'Shtuar në shportë!'})

@app.route('/cart')
def cart():
    user_id = get_user_id()
    if not user_id:
        flash('Duhet të kyçesh!', 'error')
        return redirect(url_for('login'))

    db = get_database()
    cursor = db.cursor()

    cursor.execute("""
        SELECT c.quantity, b.id, b.title, b.img, b.price
        FROM cart c
        JOIN books b ON c.book_id = b.id
        WHERE c.user_id = ?
    """, (user_id,))
    items = cursor.fetchall()

    total = sum(float(item['price'].replace('$', '')) * item['quantity'] for item in items)
    db.close()

    return render_template('cart.html', cart_items=items, total_price=f"{total:.2f}$")

@app.route('/remove_from_cart/<int:book_id>')
def remove_from_cart(book_id):
    user_id = get_user_id()
    if user_id:
        db = get_database()
        db.execute("DELETE FROM cart WHERE user_id = ? AND book_id = ?", (user_id, book_id))
        db.commit()
        db.close()
    return redirect(url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    user_id = get_user_id()
    if user_id:
        db = get_database()
        db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        db.commit()
        db.close()
    return redirect(url_for('cart'))

@app.route('/place_order', methods=['POST'])
def place_order():
    user_id = get_user_id()
    if not user_id:
        flash('Duhet të kyçesh për të porositur!', 'error')
        return redirect(url_for('login'))

    db = get_database()
    cursor = db.cursor()

    # Get current cart items
    cursor.execute("""
        SELECT b.id, b.title, b.price, c.quantity 
        FROM cart c 
        JOIN books b ON c.book_id = b.id 
        WHERE c.user_id = ?
    """, (user_id,))
    items = cursor.fetchall()

    if not items:
        flash('Shporta është bosh!', 'error')
        db.close()
        return redirect(url_for('cart'))

    # Calculate total
    total = sum(float(item['price'].replace('$', '')) * item['quantity'] for item in items)
    total_str = f"{total:.2f}$"

    # Create order
    cursor.execute("INSERT INTO orders (user_id, total_price) VALUES (?, ?)", (user_id, total_str))
    order_id = cursor.lastrowid

    # Add items to order_items
    for item in items:
        price_per_book = item['price']
        cursor.execute("""
            INSERT INTO order_items (order_id, book_id, quantity, price)
            VALUES (?, ?, ?, ?)
        """, (order_id, item['id'], item['quantity'], price_per_book))

    # Clear cart
    cursor.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))

    db.commit()
    db.close()

    flash('Porosia u krye me sukses! Faleminderit për blerjen ❤️', 'success')
    return redirect(url_for('index'))

# === FAVORITES ===
@app.route('/add_to_favorites', methods=['POST'])
def add_to_favorites():
    user_id = get_user_id()
    if not user_id:
        return jsonify({'success': False, 'message': 'Duhet të kyçesh së pari!'})

    data = request.get_json()
    book_id = data['book_id']

    db = get_database()
    cursor = db.cursor()

    cursor.execute("SELECT id FROM favorites WHERE user_id = ? AND book_id = ?", (user_id, book_id))
    if cursor.fetchone():
        db.close()
        return jsonify({'success': False, 'message': 'Tashmë në të preferuara!'})

    cursor.execute("INSERT INTO favorites (user_id, book_id) VALUES (?, ?)", (user_id, book_id))
    db.commit()
    db.close()
    return jsonify({'success': True, 'message': 'Shtuar në të preferuara!'})

@app.route('/favorites')
def favorites_page():
    user_id = get_user_id()
    if not user_id:
        flash('Duhet të kyçesh!', 'error')
        return redirect(url_for('login'))

    db = get_database()
    cursor = db.cursor()

    cursor.execute("""
        SELECT b.id, b.title, b.img, b.price
        FROM favorites f
        JOIN books b ON f.book_id = b.id
        WHERE f.user_id = ?
    """, (user_id,))
    items = cursor.fetchall()
    db.close()

    return render_template('favorites.html', favorites=items)

@app.route('/remove_from_favorites/<int:book_id>')
def remove_from_favorites(book_id):
    user_id = get_user_id()
    if user_id:
        db = get_database()
        db.execute("DELETE FROM favorites WHERE user_id = ? AND book_id = ?", (user_id, book_id))
        db.commit()
        db.close()
    return redirect(url_for('favorites_page'))

if __name__ == '__main__':
    app.run(debug=True)
