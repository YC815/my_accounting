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
        # 本月 1 日到月底
        start = today.replace(day=1)
        # 計算月底
        if today.month == 12:
            end = today.replace(day=31)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
            end = next_month - timedelta(days=1)
        return start, end
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
        from datetime import date

        # 篩選參數
        category_id = request.args.get('category_id')
        category_name = request.args.get('category_name')
        preset = request.args.get('preset', '')
        year = request.args.get('year')
        month = request.args.get('month')
        page = int(request.args.get('page', 1))

        # 建立查詢
        query = db.query(Expense).join(Category)

        # 類別篩選
        if category_id:
            query = query.filter(Expense.category_id == category_id)
        elif category_name:
            query = query.filter(Category.name == CategoryEnum(category_name))

        # 日期篩選：自訂月份優先
        date_start, date_end = None, None
        if year and month:
            try:
                y, m = int(year), int(month)
                date_start = date(y, m, 1)
                # 計算該月最後一天
                if m == 12:
                    date_end = date(y, 12, 31)
                else:
                    date_end = date(y, m + 1, 1) - timedelta(days=1)
            except (ValueError, TypeError):
                pass
        elif preset:
            date_start, date_end = get_date_range(preset)

        if date_start and date_end:
            query = query.filter(Expense.date >= date_start, Expense.date <= date_end)

        # 排序：日期新→舊
        query = query.order_by(Expense.date.desc(), Expense.created_at.desc())

        # 分頁（每頁 50 筆）
        per_page = 50
        total = query.count()
        total_pages = (total + per_page - 1) // per_page  # 無條件進位
        expenses = query.limit(per_page).offset((page - 1) * per_page).all()

        # 取得所有啟用的類別（用於按鈕導覽）
        categories = db.query(Category).filter(Category.active == True).all()

        # 計算顯示變數
        today = taipei_today()
        current_year = today.year
        current_month = today.month

        # 計算顯示的時間範圍文字
        if year and month:
            display_period = f"{year}年 {month}月"
        elif preset == 'this_month':
            display_period = f"{current_year}年 {current_month}月"
        elif preset == 'last_month':
            first_of_month = today.replace(day=1)
            last_month_date = first_of_month - timedelta(days=1)
            display_period = f"{last_month_date.year}年 {last_month_date.month}月"
        else:
            display_period = "全部時間"

        # 構建時間參數字串（用於分類按鈕保留時間篩選）
        time_params = ''
        if year and month:
            time_params = f"year={year}&month={month}"
        elif preset:
            time_params = f"preset={preset}"

        return render_template(
            'expenses.html',
            expenses=expenses,
            categories=categories,
            page=page,
            total_pages=total_pages,
            total=total,
            current_year=current_year,
            current_month=current_month,
            display_period=display_period,
            time_params=time_params,
            # 保留篩選條件（用於分頁連結和表單）
            filters={
                'category_id': category_id,
                'category_name': category_name,
                'preset': preset,
                'year': year,
                'month': month
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
