from sqlalchemy import (
    create_engine,
    Column,
    String,
    Float,
    DateTime,
    Text,
    inspect,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./finance_chatbot.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============== MODELS ==============


class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    amount = Column(Float)
    description = Column(String)
    category = Column(String)
    merchant = Column(String)
    transaction_date = Column(DateTime)
    receipt_image_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    category_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    category_name = Column(String)
    monthly_budget = Column(Float, default=0)
    color_code = Column(String, default="#1f77b4")
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatHistory(Base):
    __tablename__ = "chat_history"

    chat_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True)
    role = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


def _migrate(conn):
    """
    Tambah kolom baru ke tabel yang sudah ada jika belum ada.
    SQLite tidak support ALTER TABLE ADD COLUMN IF NOT EXISTS,
    jadi kita cek manual dulu.
    """
    inspector = inspect(conn)

    # Migrasi tabel users
    if "users" in inspector.get_table_names():
        existing_cols = [c["name"] for c in inspector.get_columns("users")]

        if "username" not in existing_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR"))
            # Isi username lama dengan user_id supaya tidak NULL
            conn.execute(
                text("UPDATE users SET username = user_id WHERE username IS NULL")
            )

        if "password_hash" not in existing_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR"))


def init_db():
    # Buat tabel baru yang belum ada
    Base.metadata.create_all(bind=engine)

    # Migrasi kolom yang mungkin belum ada di tabel lama
    with engine.begin() as conn:
        _migrate(conn)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    return SessionLocal()
