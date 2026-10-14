
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "expense_tracker.db"

CATEGORIES = [
    "Food", "Travel", "Shopping", "Education",
    "Bills", "Healthcare", "Entertainment",
    "Rent", "Salary", "Freelance", "Other"
]


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                transaction_type TEXT NOT NULL
                    CHECK(transaction_type IN ('Income', 'Expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                description TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                UNIQUE(month, category)
            )
        """)


def add_transaction(date, transaction_type, category,
                    amount, description):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO transactions
            (date, transaction_type, category, amount, description)
            VALUES (?, ?, ?, ?, ?)
        """, (
            date, transaction_type, category,
            amount, description.strip()
        ))


def get_transactions():
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT id, date, transaction_type, category,
                   amount, description
            FROM transactions
            ORDER BY date DESC, id DESC
        """).fetchall()
    return [dict(row) for row in rows]


def update_transaction(transaction_id, date, transaction_type,
                       category, amount, description):
    with get_connection() as conn:
        conn.execute("""
            UPDATE transactions
            SET date = ?, transaction_type = ?, category = ?,
                amount = ?, description = ?
            WHERE id = ?
        """, (
            date, transaction_type, category,
            amount, description.strip(), transaction_id
        ))


def delete_transaction(transaction_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM transactions WHERE id = ?",
            (transaction_id,)
        )


def save_budget(month, category, amount):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO budgets (month, category, amount)
            VALUES (?, ?, ?)
            ON CONFLICT(month, category)
            DO UPDATE SET amount = excluded.amount
        """, (month, category, amount))


def get_budgets(month=None):
    with get_connection() as conn:
        if month:
            rows = conn.execute("""
                SELECT id, month, category, amount
                FROM budgets
                WHERE month = ?
                ORDER BY category
            """, (month,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, month, category, amount
                FROM budgets
                ORDER BY month DESC, category
            """).fetchall()

    return [dict(row) for row in rows]


def delete_budget(budget_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM budgets WHERE id = ?",
            (budget_id,)
        )
