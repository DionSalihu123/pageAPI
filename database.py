# database.py
import sqlite3
from flask import g, current_app

DATABASE = '/home/dion/pageAPI/booksAPI.db'  # Your DB path

def connect_to_database():
    sql = sqlite3.connect(DATABASE)
    sql.row_factory = sqlite3.Row
    return sql

def get_database():
    if not hasattr(g, 'books_db'):
        g.books_db = connect_to_database()
    return g.books_db

def close_database(e=None):
    db = g.pop('books_db', None)
    if db is not None:
        db.close()

def init_db(app):
    with app.app_context():
        db = get_database()
        cursor = db.cursor()

        # Create books table (only if not exists)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                img TEXT NOT NULL,
                price TEXT NOT NULL,
                category TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                book_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                book_id INTEGER NOT NULL,
                UNIQUE(user_id, book_id),
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
                

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                surname TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_price TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE
            )
        ''')

        # Insert default books ONLY if table is empty
        cursor.execute("SELECT COUNT(*) FROM books")
        if cursor.fetchone()[0] == 0:
            default_books = [
                ("Desgin Patterns", "desginPetterns.jpeg", "30.00$", "Programming General"),
                ("Clean Code", "clean-code.jpeg", "25.00$", "Programming General"),
                ("Python Crash Course", "python-crash.jpeg", "20.00$", "Programming General"),
                ("The Pragmatic Programmer", "pragmatic.jpeg", "15.00$", "Programming General"),
                ("Operating Systems-Three pieces", "operating-systems.jpeg", "20.00$", "Interaction with hardware"),
                ("Computer Architecture", "computer-arch.jpeg", "17.00$", "Interaction with hardware"),
                ("Low-Level Programming", "low.jpeg", "22.00$", "Interaction with hardware"),
                ("Linux-Kernel Development", "kernel.jpeg", "19.00$", "Interaction with hardware"),
                ("Black-Hat Python", "black-hat.jpeg", "23.00$", "Secure Systmes"),
                ("Metasploit", "metasploit.jpeg", "31.00$", "Secure Systmes"),
                ("Social Eengineering", "social.jpeg", "15.00$", "Secure Systmes"),
                ("Networking Top-Down Approach", "net.jpeg", "19.00$", "Secure Systmes"),
            ]

            cursor.executemany('''
                INSERT INTO books (title, img, price, category)
                VALUES (?, ?, ?, ?)
            ''', default_books)

            db.commit()
            print("Default books inserted!")

        db.commit()
