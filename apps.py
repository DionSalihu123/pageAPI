# apps.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import get_database, close_database, init_db
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_strong_secret_key_change_this_now!'

# Initialize DB
init_db(app)

@app.teardown_appcontext
def teardown_db(exception):
    close_database(exception)

def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


@app.route('/')
def index():
    db = get_database()
    cursor = db.cursor()

    # Get books from DB
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

    # Session ID
    session_id = get_session_id()

    # Cart count
    cursor.execute("SELECT SUM(quantity) FROM cart WHERE session_id = ?", (session_id,))
    cart_count = cursor.fetchone()[0] or 0

    # Favorites count and IDs
    cursor.execute("SELECT book_id FROM favorites WHERE session_id = ?", (session_id,))
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

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    book_id = data['book_id']
    session_id = get_session_id()

    db = get_database()
    cursor = db.cursor()

    # Check if already in cart
    cursor.execute("SELECT * FROM cart WHERE session_id = ? AND book_id = ?", (session_id, book_id))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = ?", (existing['id'],))
    else:
        cursor.execute("INSERT INTO cart (session_id, book_id, quantity) VALUES (?, ?, 1)",
                       (session_id, book_id))

    db.commit()
    db.close()

    return jsonify({'success': True, 'message': 'Shtuar në shportë!'})

@app.route('/add_to_favorites', methods=['POST'])
def add_to_favorites():
    data = request.get_json()
    book_id = data['book_id']
    session_id = get_session_id()

    db = get_database()
    cursor = db.cursor()

    # Check if already favorited
    cursor.execute("SELECT * FROM favorites WHERE session_id = ? AND book_id = ?", (session_id, book_id))
    existing = cursor.fetchone()

    if existing:
        db.close()
        return jsonify({'success': False, 'message': 'Ky libër është tashmë në të preferuara!'})

    cursor.execute("INSERT INTO favorites (session_id, book_id) VALUES (?, ?)", (session_id, book_id))
    db.commit()
    db.close()

    return jsonify({'success': True, 'message': 'Shtuar në të preferuara!'})

@app.route('/favorites')
def favorites_page():
    session_id = get_session_id()
    db = get_database()
    cursor = db.cursor()

    cursor.execute("""
        SELECT b.id, b.title, b.img, b.price 
        FROM favorites f 
        JOIN books b ON f.book_id = b.id 
        WHERE f.session_id = ?
    """, (session_id,))
    fav_items = cursor.fetchall()
    db.close()

    return render_template('favorites.html', favorites=fav_items)

@app.route('/remove_from_favorites/<int:book_id>')
def remove_from_favorites(book_id):
    session_id = get_session_id()
    db = get_database()
    db.execute("DELETE FROM favorites WHERE session_id = ? AND book_id = ?", (session_id, book_id))
    db.commit()
    db.close()
    return redirect(url_for('favorites_page'))

@app.route('/login')
def login():
    session['user_id'] = 1
    session['user_email'] = 'test@example.com'
    flash('Je kyçur me sukses (demo mode)!', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    session_id = get_session_id()
    db = get_database()
    cursor = db.cursor()

    cursor.execute("""
        SELECT c.quantity, b.id, b.title, b.img, b.price 
        FROM cart c 
        JOIN books b ON c.book_id = b.id 
        WHERE c.session_id = ?
    """, (session_id,))
    items = cursor.fetchall()

    total = sum(float(item['price'].replace('$', '')) * item['quantity'] for item in items)

    return render_template('cart.html', cart_items=items, total_price=f"{total:.2f}$")

@app.route('/remove_from_cart/<int:book_id>')
def remove_from_cart(book_id):
    session_id = get_session_id()
    db = get_database()
    db.execute("DELETE FROM cart WHERE session_id = ? AND book_id = ?", (session_id, book_id))
    db.commit()
    db.close()
    return redirect(url_for('cart'))

@app.route('/clear_cart')
def clear_cart():
    session_id = get_session_id()
    db = get_database()
    db.execute("DELETE FROM cart WHERE session_id = ?", (session_id,))
    db.commit()
    db.close()
    flash('Shporta u pastërua!', 'success')
    return redirect(url_for('cart'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    flash('Ke dalë me sukses!', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
