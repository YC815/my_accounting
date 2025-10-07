import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

from app.models import Base, Category, CategoryEnum

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL 環境變數未設定，請檢查 .env 檔案")

# 建立資料庫引擎
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# 建立 session factory
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """初始化資料庫：建表 + 插入 5 固定類別"""
    Base.metadata.create_all(engine)

    # 插入 5 固定類別（如果不存在）
    session = Session()
    try:
        existing_count = session.query(Category).count()
        if existing_count == 0:
            for category_enum in CategoryEnum:
                category = Category(name=category_enum, active=True)
                session.add(category)
            session.commit()
            print("✅ 已插入 5 固定類別")
        else:
            print(f"ℹ️  類別已存在 ({existing_count} 筆)")
    except Exception as e:
        session.rollback()
        print(f"❌ 初始化類別失敗: {e}")
        raise
    finally:
        session.close()


def get_db():
    """取得資料庫 session (用於 Flask request context)"""
    db = Session()
    try:
        yield db
    finally:
        db.close()
