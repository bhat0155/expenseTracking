import sqlite3
from datetime import date
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent.parent / "expense_tracker.db"

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()

    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    password_hash = generate_password_hash("demo123")
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cursor.lastrowid

    today = date.today()

    def day(day_of_month):
        return today.replace(day=min(day_of_month, today.day)).isoformat()

    sample_expenses = [
        (user_id, 45.50, "Food", day(2), "Groceries at Trader Joe's"),
        (user_id, 18.75, "Transport", day(4), "Uber ride"),
        (user_id, 120.00, "Bills", day(5), "Electricity bill"),
        (user_id, 60.00, "Health", day(8), "Pharmacy — prescription"),
        (user_id, 32.00, "Entertainment", day(11), "Movie tickets"),
        (user_id, 89.99, "Shopping", day(13), "New headphones"),
        (user_id, 15.00, "Other", day(15), "Miscellaneous"),
        (user_id, 22.30, "Food", day(17), "Lunch with coworkers"),
    ]

    conn.executemany(
        """
        INSERT INTO expenses (user_id, amount, category, date, description)
        VALUES (?, ?, ?, ?, ?)
        """,
        sample_expenses,
    )
    conn.commit()
    conn.close()


def create_user(name, email, password_hash):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def update_user(user_id, name, email):
    conn = get_db()
    conn.execute(
        "UPDATE users SET name = ?, email = ? WHERE id = ?",
        (name, email, user_id),
    )
    conn.commit()
    conn.close()


def get_expenses_by_user(user_id):
    conn = get_db()
    expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return expenses
