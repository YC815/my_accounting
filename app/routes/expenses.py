from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from sqlalchemy import or_
from datetime import datetime, timedelta
from decimal import Decimal

from app.database import Session
from app.models import Category, Expense, CategoryEnum, taipei_today
import pytz

bp = Blueprint('expenses', __name__, url_prefix='/expenses')
taipei_tz = pytz.timezone('Asia/Taipei')


def get_date_range(preset):
    """根據預設選項計算日期範圍"""
    today = taipei_today()

    if preset == 'today':
        return today, today
    elif preset == 'this_week':
        # 本週（週一到今天）
        start = today - timedelta(days=today.weekday())
        return start, today
    elif preset == 'this_month':
        # 本月 1 日到今天
        start = today.replace(day=1)
        return start, today
    elif preset == 'last_month':
        # 上月 1 日到月底
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end

    return None, None


@bp.route('/')
def index():
    """支出流水頁"""
    db = Session()

    try:
        # 篩選參數
        category_id = request.args.get('category_id')
        category_name = request.args.get('category_name')
        search = request.args.get('search', '').strip()
        preset = request.args.get('preset', '')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        min_amount = request.args.get('min_amount')
        max_amount = request.args.get('max_amount')
        page = int(request.args.get('page', 1))

        # 建立查詢
        query = db.query(Expense).join(Category)

        # 類別篩選
        if category_id:
            query = query.filter(Expense.category_id == category_id)
        elif category_name:
            query = query.filter(Category.name == CategoryEnum(category_name))

        # 名稱搜尋
        if search:
            query = query.filter(Expense.name.ilike(f'%{search}%'))

        # 日期篩選
        if preset and preset != 'custom':
            date_start, date_end = get_date_range(preset)
            if date_start and date_end:
                query = query.filter(Expense.date >= date_start, Expense.date <= date_end)
        elif start_date or end_date:
            if start_date:
                query = query.filter(Expense.date >= start_date)
            if end_date:
                query = query.filter(Expense.date <= end_date)

        # 金額範圍
        if min_amount:
            query = query.filter(Expense.amount >= Decimal(min_amount))
        if max_amount:
            query = query.filter(Expense.amount <= Decimal(max_amount))

        # 排序：日期新→舊
        query = query.order_by(Expense.date.desc(), Expense.created_at.desc())

        # 分頁（每頁 50 筆）
        per_page = 50
        total = query.count()
        total_pages = (total + per_page - 1) // per_page  # 無條件進位
        expenses = query.limit(per_page).offset((page - 1) * per_page).all()

        # 取得所有啟用的類別（用於下拉選單）
        categories = db.query(Category).filter(Category.active == True).all()

        return render_template(
            'expenses.html',
            expenses=expenses,
            categories=categories,
            page=page,
            total_pages=total_pages,
            total=total,
            # 保留篩選條件（用於分頁連結）
            filters={
                'category_id': category_id,
                'search': search,
                'preset': preset,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount
            }
        )
    finally:
        db.close()


@bp.route('/<uuid:expense_id>/edit', methods=['GET', 'POST'])
def edit(expense_id):
    """編輯支出"""
    db = Session()

    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            abort(404)

        if request.method == 'POST':
            expense.category_id = request.form.get('category_id')
            expense.name = request.form.get('name', '').strip()
            expense.amount = Decimal(request.form.get('amount'))
            expense.date = request.form.get('date') or taipei_today()

            db.commit()
            flash('✅ 支出已更新', 'success')
            return redirect(url_for('expenses.index'))

        # GET: 顯示編輯表單
        categories = db.query(Category).filter(Category.active == True).all()
        return render_template('expense_edit.html', expense=expense, categories=categories)

    except Exception as e:
        db.rollback()
        flash(f'❌ 更新失敗: {str(e)}', 'error')
        return redirect(url_for('expenses.index'))
    finally:
        db.close()


@bp.route('/<uuid:expense_id>/delete', methods=['POST'])
def delete(expense_id):
    """刪除支出"""
    db = Session()

    try:
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        if not expense:
            abort(404)
        db.delete(expense)
        db.commit()

        flash('✅ 支出已刪除', 'success')
        return redirect(url_for('expenses.index'))

    except Exception as e:
        db.rollback()
        flash(f'❌ 刪除失敗: {str(e)}', 'error')
        return redirect(url_for('expenses.index'))
    finally:
        db.close()
