from database import get_db_session, User, Transaction, Category, ChatHistory
from datetime import datetime, timedelta
import uuid
import hashlib
import pandas as pd

# ============== AUTH FUNCTIONS ==============


def hash_password(password: str) -> str:
    """Hash password dengan SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username: str, name: str, email: str, password: str):
    """
    Daftarkan user baru.
    Return: (True, user) jika berhasil, (False, pesan_error) jika gagal
    """
    db = get_db_session()

    # Cek username sudah ada
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        return False, "Username sudah digunakan"

    # Cek email sudah ada
    existing_email = db.query(User).filter(User.email == email).first()
    if existing_email:
        db.close()
        return False, "Email sudah terdaftar"

    new_user = User(
        user_id=str(uuid.uuid4()),
        username=username,
        name=name,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return True, new_user


def login_user(username: str, password: str):
    """
    Login user.
    Return: (True, user) jika berhasil, (False, pesan_error) jika gagal
    """
    db = get_db_session()
    user = db.query(User).filter(User.username == username).first()
    db.close()

    if not user:
        return False, "Username tidak ditemukan"

    if user.password_hash != hash_password(password):
        return False, "Password salah"

    return True, user


def get_user(user_id: str):
    """Get user by user_id"""
    db = get_db_session()
    user = db.query(User).filter(User.user_id == user_id).first()
    db.close()
    return user


# ============== TRANSACTION FUNCTIONS ==============


def add_transaction(
    user_id: str,
    amount: float,
    description: str,
    category: str,
    merchant: str,
    transaction_date: datetime = None,
):
    db = get_db_session()
    if transaction_date is None:
        transaction_date = datetime.now()

    transaction = Transaction(
        transaction_id=str(uuid.uuid4()),
        user_id=user_id,
        amount=amount,
        description=description,
        category=category,
        merchant=merchant,
        transaction_date=transaction_date,
    )
    db.add(transaction)
    db.commit()
    db.close()
    return transaction


def get_user_transactions(user_id: str, days: int = 30):
    db = get_db_session()
    start_date = datetime.now() - timedelta(days=days)
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
        )
        .order_by(Transaction.transaction_date.desc())
        .all()
    )
    db.close()
    return transactions


def get_transactions_df(user_id: str, days: int = 30):
    transactions = get_user_transactions(user_id, days)
    if not transactions:
        return pd.DataFrame()

    data = [
        {
            "Tanggal": t.transaction_date.strftime("%d-%m-%Y"),
            "Merchant": t.merchant,
            "Deskripsi": t.description,
            "Kategori": t.category,
            "Jumlah (Rp)": t.amount,
        }
        for t in transactions
    ]
    return pd.DataFrame(data)


def get_spending_by_category(user_id: str, days: int = 30):
    db = get_db_session()
    start_date = datetime.now() - timedelta(days=days)
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start_date,
        )
        .all()
    )
    db.close()

    spending = {}
    for t in transactions:
        spending[t.category] = spending.get(t.category, 0) + t.amount
    return spending


def get_total_spending(user_id: str, days: int = 30):
    return sum(get_spending_by_category(user_id, days).values())


def delete_transaction(transaction_id: str):
    db = get_db_session()
    db.query(Transaction).filter(Transaction.transaction_id == transaction_id).delete()
    db.commit()
    db.close()


# ============== CATEGORY FUNCTIONS ==============


def create_category(
    user_id: str,
    category_name: str,
    monthly_budget: float = 0,
    color_code: str = "#1f77b4",
):
    db = get_db_session()
    category = Category(
        category_id=str(uuid.uuid4()),
        user_id=user_id,
        category_name=category_name,
        monthly_budget=monthly_budget,
        color_code=color_code,
    )
    db.add(category)
    db.commit()
    db.close()
    return category


def get_user_categories(user_id: str):
    db = get_db_session()
    categories = db.query(Category).filter(Category.user_id == user_id).all()
    db.close()
    return categories


def get_or_create_default_categories(user_id: str):
    existing = get_user_categories(user_id)
    if existing:
        return existing

    defaults = [
        ("Food", 1000000, "#FF6B6B"),
        ("Transport", 500000, "#4ECDC4"),
        ("Entertainment", 300000, "#45B7D1"),
        ("Utility/Bills", 800000, "#FFA07A"),
        ("Shopping", 400000, "#98D8C8"),
        ("Other", 200000, "#C7CEEA"),
    ]
    created = []
    for name, budget, color in defaults:
        cat = create_category(user_id, name, budget, color)
        created.append(cat)
    return created


# ============== CHAT HISTORY FUNCTIONS ==============


def save_chat_message(user_id: str, role: str, message: str):
    db = get_db_session()
    chat = ChatHistory(
        chat_id=str(uuid.uuid4()),
        user_id=user_id,
        role=role,
        message=message,
    )
    db.add(chat)
    db.commit()
    db.close()


def get_chat_history(user_id: str, limit: int = 20):
    db = get_db_session()
    chats = (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id)
        .order_by(ChatHistory.timestamp.desc())
        .limit(limit)
        .all()
    )
    db.close()
    chats = list(reversed(chats))
    return [{"role": c.role, "content": c.message} for c in chats]


def clear_chat_history(user_id: str):
    db = get_db_session()
    db.query(ChatHistory).filter(ChatHistory.user_id == user_id).delete()
    db.commit()
    db.close()


# ============== UTILITY FUNCTIONS ==============


def generate_spending_summary(user_id: str, days: int = 30) -> str:
    transactions = get_user_transactions(user_id, days)
    spending = get_spending_by_category(user_id, days)
    total = get_total_spending(user_id, days)

    if not transactions:
        return "Belum ada transaksi yang tercatat."

    summary = f"Ringkasan Pengeluaran {days} hari terakhir:\n"
    summary += f"Total: Rp {total:,.0f}\n\nPer Kategori:\n"
    for category, amount in sorted(spending.items(), key=lambda x: x[1], reverse=True):
        pct = (amount / total * 100) if total > 0 else 0
        summary += f"- {category}: Rp {amount:,.0f} ({pct:.1f}%)\n"
    return summary


def get_dashboard_stats(user_id: str) -> dict:
    spending_7d = get_total_spending(user_id, 7)
    spending_30d = get_total_spending(user_id, 30)
    spending_by_cat = get_spending_by_category(user_id, 30)
    count = len(get_user_transactions(user_id, 30))

    return {
        "spending_7d": spending_7d,
        "spending_30d": spending_30d,
        "spending_by_category": spending_by_cat,
        "transaction_count": count,
        "avg_per_transaction": spending_30d / count if count > 0 else 0,
    }
