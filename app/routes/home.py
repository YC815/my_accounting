from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import func
from decimal import Decimal

from app.database import Session
from app.models import Category, Expense, Repayment, Adjustment, CategoryEnum, taipei_today

bp = Blueprint('home', __name__)


@bp.route('/')
def index():
    """首頁：Dashboard"""
    db = Session()

    try:
        # 計算總額 = Σ支出 - Σ還款 + Σ調整
        total_expenses = db.query(func.sum(Expense.amount)).scalar() or Decimal('0')
        total_repayments = db.query(func.sum(Repayment.amount)).scalar() or Decimal('0')
        total_adjustments = db.query(func.sum(Adjustment.amount)).scalar() or Decimal('0')
        balance = total_expenses - total_repayments + total_adjustments

        # 5 張摘要卡：各類別加總
        category_summaries = db.query(
            Category.name,
            func.sum(Expense.amount).label('total')
        ).join(Expense).filter(Category.active == True).group_by(Category.name).all()

        # 轉換為字典 {類別名稱: 金額}
        summaries = {cat_name.value: (total or Decimal('0')) for cat_name, total in category_summaries}

        # 確保所有類別都有值（即使為 0）
        for cat_enum in CategoryEnum:
            if cat_enum.value not in summaries:
                summaries[cat_enum.value] = Decimal('0')

        # 取得所有啟用的類別（用於下拉選單）
        categories = db.query(Category).filter(Category.active == True).all()

        return render_template(
            'home.html',
            balance=balance,
            summaries=summaries,
            categories=categories,
            today=taipei_today()
        )
    finally:
        db.close()


@bp.route('/expenses/add', methods=['POST'])
def add_expense():
    """新增支出（HTMX）"""
    db = Session()

    try:
        category_id = request.form.get('category_id')
        name = request.form.get('name', '').strip()
        amount = request.form.get('amount')
        date = request.form.get('date') or taipei_today()

        # 驗證
        if not all([category_id, name, amount]):
            flash('請填寫所有必填欄位', 'error')
            return redirect(url_for('home.index'))

        # 建立支出
        expense = Expense(
            category_id=category_id,
            name=name,
            amount=Decimal(amount),
            date=date
        )
        db.add(expense)
        db.commit()

        flash('✅ 支出已新增', 'success')
        return redirect(url_for('home.index'))

    except Exception as e:
        db.rollback()
        flash(f'❌ 新增失敗: {str(e)}', 'error')
        return redirect(url_for('home.index'))
    finally:
        db.close()


@bp.route('/repayments/add', methods=['POST'])
def add_repayment():
    """新增還款（HTMX）"""
    db = Session()

    try:
        amount = request.form.get('amount')
        date = request.form.get('date') or taipei_today()

        if not amount:
            flash('請輸入還款金額', 'error')
            return redirect(url_for('home.index'))

        repayment = Repayment(
            amount=Decimal(amount),
            date=date
        )
        db.add(repayment)
        db.commit()

        flash('✅ 還款已記錄', 'success')
        return redirect(url_for('home.index'))

    except Exception as e:
        db.rollback()
        flash(f'❌ 新增失敗: {str(e)}', 'error')
        return redirect(url_for('home.index'))
    finally:
        db.close()


@bp.route('/adjustments/add', methods=['POST'])
def add_adjustment():
    """新增調整項目"""
    db = Session()

    try:
        amount = request.form.get('amount')
        description = request.form.get('description', '').strip()
        date = request.form.get('date') or taipei_today()

        if not amount or not description:
            flash('請填寫所有必填欄位', 'error')
            return redirect(url_for('home.index'))

        adjustment = Adjustment(
            amount=Decimal(amount),
            description=description,
            date=date
        )
        db.add(adjustment)
        db.commit()

        flash('✅ 調整項目已新增', 'success')
        return redirect(url_for('home.index'))

    except Exception as e:
        db.rollback()
        flash(f'❌ 新增失敗: {str(e)}', 'error')
        return redirect(url_for('home.index'))
    finally:
        db.close()
