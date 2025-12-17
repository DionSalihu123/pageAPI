# apps.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Favorite, CartItem
# Wait — we'll use session for now, but add login_required later if needed

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_strong_secret_key_change_this_now!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pageapi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Books data
books = {
    "Programming General": [
        {"img": "desginPetterns.jpeg", "title": "Desgin Patterns", "price": "30.00$"},
        {"img": "clean-code.jpeg", "title": "Clean Code", "price": "25.00$"},
        {"img": "python-crash.jpeg", "title": "Python Crash Course", "price": "20.00$"},
        {"img": "pragmatic.jpeg", "title": "The Pragmatic Programmer", "price": "15.00$"},
    ],
    "Interaction with hardware": [
        {"img": "operating-systems.jpeg", "title": "Operating Systems-Three pieces", "price": "20.00$"},
        {"img": "computer-arch.jpeg", "title": "Computer Architecture", "price": "17.00$"},
        {"img": "low.jpeg", "title": "Low-Level Programming", "price": "22.00$"},
        {"img": "kernel.jpeg", "title": "Linux-Kernel Development", "price": "19.00$"},
    ],
    "Secure Systmes": [
        {"img": "black-hat.jpeg", "title": "Black-Hat Python", "price": "23.00$"},
        {"img": "metasploit.jpeg", "title": "Metasploit", "price": "31.00$"},
        {"img": "social.jpeg", "title": "Social Eengineering", "price": "15.00$"},
        {"img": "net.jpeg", "title": "Networking Top-Down Approach", "price": "19.00$"},
    ]
}

nav_categories = [
    ("two", "Programming", "Programming General"),
    ("three", "Low Level", "Interaction with hardware"),
    ("four", "Security", "Secure Systmes")
]

@app.route('/')
def index():
    return render_template('index.html', books=books, nav_categories=nav_categories)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email'].lower()
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash('Ky email është tashmë i regjistruar.', 'error')
            return redirect(url_for('signup'))

        new_user = User(name=name, surname=surname, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Llogaria u krijua me sukses! Tani mund të kyçeni.', 'success')
        return redirect(url_for('login'))

    return render_template('sign.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].lower()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            flash('Ke hyrë me sukses!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ose fjalëkalim i gabuar.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_email', None)
    flash('Ke dalë me sukses.', 'info')
    return redirect(url_for('index'))

# === FAVORITES ===
@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        flash('Duhet të kyçesh për të parë të preferuarat.', 'error')
        return redirect(url_for('login'))

    user_favorites = Favorite.query.filter_by(user_id=session['user_id']).all()
    return render_template('favorites.html', favorites=user_favorites)

@app.route('/add_to_favorites', methods=['POST'])
def add_to_favorites():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Duhet të kyçesh së pari!'})

    data = request.get_json()
    title = data.get('title')
    img = data.get('img')
    price = data.get('price')

    # Check if already in favorites
    existing = Favorite.query.filter_by(
        user_id=session['user_id'],
        book_title=title
    ).first()

    if existing:
        return jsonify({'success': False, 'message': 'Ky libër është tashmë në të preferuarat!'})

    new_fav = Favorite(
        user_id=session['user_id'],
        book_title=title,
        book_img=img,
        book_price=price
    )
    db.session.add(new_fav)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Shtuar në të preferuarat!'})

@app.route('/remove_from_favorites/<int:fav_id>', methods=['POST'])
def remove_from_favorites(fav_id):
    if 'user_id' not in session:
        flash('Duhet të kyçesh.', 'error')
        return redirect(url_for('login'))

    fav = Favorite.query.get_or_404(fav_id)
    if fav.user_id != session['user_id']:
        flash('Nuk mund ta heqësh këtë!', 'error')
        return redirect(url_for('favorites'))

    db.session.delete(fav)
    db.session.commit()
    flash('Libri u hoq nga të preferuarat.', 'success')
    return redirect(url_for('favorites'))

# === CART ===
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Duhet të kyçesh për të parë shportën.', 'error')
        return redirect(url_for('login'))

    cart_items = CartItem.query.filter_by(user_id=session['user_id']).all()

    # Calculate total
    total = 0.0
    for item in cart_items:
        price = float(item.book_price.replace('$', '').replace(',', ''))
        total += price * item.quantity

    total_price = f"{total:.2f}$"

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Duhet të kyçesh së pari!'})

    data = request.get_json()
    title = data.get('title')
    img = data.get('img')
    price = data.get('price')

    # Check if already in cart
    existing = CartItem.query.filter_by(
        user_id=session['user_id'],
        book_title=title
    ).first()

    if existing:
        existing.quantity += 1
    else:
        new_item = CartItem(
            user_id=session['user_id'],
            book_title=title,
            book_img=img,
            book_price=price,
            quantity=1
        )
        db.session.add(new_item)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Shtuar në shportë!'})

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    if 'user_id' not in session:
        flash('Duhet të kyçesh.', 'error')
        return redirect(url_for('login'))

    item = CartItem.query.get_or_404(item_id)
    if item.user_id != session['user_id']:
        flash('Nuk mund ta heqësh këtë!', 'error')
        return redirect(url_for('cart'))

    db.session.delete(item)
    db.session.commit()
    flash('Libri u hoq nga shporta.', 'success')
    return redirect(url_for('cart'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
