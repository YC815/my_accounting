from datetime import datetime
from decimal import Decimal
from uuid import uuid4
import enum

from sqlalchemy import Column, String, Numeric, Date, Boolean, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import pytz

Base = declarative_base()
taipei_tz = pytz.timezone('Asia/Taipei')


def taipei_today():
    """取得台北時區的今天日期"""
    return datetime.now(taipei_tz).date()


class CategoryEnum(enum.Enum):
    """5 固定類別"""
    FOOD = "伙食"
    INTERNET_PHONE = "網路/電話"
    TRANSPORT = "交通"
    HOUSEHOLD = "家庭日用品"
    DAILY_GOODS = "生活用品"


class Category(Base):
    __tablename__ = 'categories'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Enum(CategoryEnum), nullable=False, unique=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(Date, nullable=False, default=taipei_today)
    updated_at = Column(Date, nullable=False, default=taipei_today, onupdate=taipei_today)

    expenses = relationship('Expense', back_populates='category', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Category {self.name.value}>"


class Expense(Base):
    __tablename__ = 'expenses'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey('categories.id'), nullable=False, index=True)
    name = Column(String(200), nullable=False, index=True)  # 支出名稱
    amount = Column(Numeric(10, 2), nullable=False)
    date = Column(Date, nullable=False, default=taipei_today, index=True)
    created_at = Column(Date, nullable=False, default=taipei_today)
    updated_at = Column(Date, nullable=False, default=taipei_today, onupdate=taipei_today)

    category = relationship('Category', back_populates='expenses')

    def __repr__(self):
        return f"<Expense {self.name} ${self.amount}>"


class Repayment(Base):
    __tablename__ = 'repayments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    amount = Column(Numeric(10, 2), nullable=False)
    date = Column(Date, nullable=False, default=taipei_today, index=True)
    created_at = Column(Date, nullable=False, default=taipei_today)
    updated_at = Column(Date, nullable=False, default=taipei_today, onupdate=taipei_today)

    def __repr__(self):
        return f"<Repayment ${self.amount}>"


class Adjustment(Base):
    __tablename__ = 'adjustments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    amount = Column(Numeric(10, 2), nullable=False)
    description = Column(String(200), nullable=False)
    date = Column(Date, nullable=False, default=taipei_today, index=True)
    created_at = Column(Date, nullable=False, default=taipei_today)
    updated_at = Column(Date, nullable=False, default=taipei_today, onupdate=taipei_today)

    def __repr__(self):
        return f"<Adjustment {self.description} ${self.amount}>"
