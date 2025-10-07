from flask import Blueprint, render_template, request, make_response
from sqlalchemy import func, extract
from datetime import timedelta
from decimal import Decimal
import csv
from io import StringIO

from app.database import Session
from app.models import Category, Expense, Repayment, taipei_today

bp = Blueprint('reports', __name__, url_prefix='/reports')


def get_date_range(preset):
    """根據預設選項計算日期範圍"""
    today = taipei_today()

    if preset == 'today':
        return today, today
    elif preset == 'this_week':
        start = today - timedelta(days=today.weekday())
        return start, today
    elif preset == 'this_month':
        start = today.replace(day=1)
        return start, today
    elif preset == 'last_month':
        first_of_month = today.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end

    return None, None


@bp.route('/')
def index():
    """報表頁"""
    db = Session()

    try:
        # 日期範圍（預設本月）
        preset = request.args.get('preset', 'this_month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 計算日期範圍
        if preset and preset != 'custom':
            date_start, date_end = get_date_range(preset)
        else:
            date_start = start_date
            date_end = end_date

        # 1. 圓餅圖：各分類支出占比
        pie_data = db.query(
            Category.name,
            func.sum(Expense.amount).label('total')
        ).join(Expense).filter(Category.active == True)

        if date_start and date_end:
            pie_data = pie_data.filter(Expense.date >= date_start, Expense.date <= date_end)

        pie_data = pie_data.group_by(Category.name).all()

        pie_chart = {
            'labels': [cat_name.value for cat_name, total in pie_data],
            'data': [float(total or 0) for cat_name, total in pie_data]
        }

        # 2. 長條圖：按月支出總額
        bar_data = db.query(
            extract('year', Expense.date).label('year'),
            extract('month', Expense.date).label('month'),
            func.sum(Expense.amount).label('total')
        )

        if date_start and date_end:
            bar_data = bar_data.filter(Expense.date >= date_start, Expense.date <= date_end)

        bar_data = bar_data.group_by('year', 'month').order_by('year', 'month').all()

        bar_chart = {
            'labels': [f"{int(year)}-{int(month):02d}" for year, month, total in bar_data],
            'data': [float(total or 0) for year, month, total in bar_data]
        }

        # 3. 折線圖：累積餘額（支出 - 還款）
        # 取得所有支出與還款，排序後計算累積
        expenses = db.query(Expense.date, Expense.amount).order_by(Expense.date)
        repayments = db.query(Repayment.date, Repayment.amount).order_by(Repayment.date)

        if date_start and date_end:
            expenses = expenses.filter(Expense.date >= date_start, Expense.date <= date_end)
            repayments = repayments.filter(Repayment.date >= date_start, Repayment.date <= date_end)

        # 合併成時間序列
        transactions = []
        for date, amount in expenses.all():
            transactions.append((date, float(amount)))
        for date, amount in repayments.all():
            transactions.append((date, -float(amount)))  # 還款為負

        transactions.sort(key=lambda x: x[0])

        # 計算累積餘額
        cumulative = 0
        line_chart_dates = []
        line_chart_data = []

        for date, amount in transactions:
            cumulative += amount
            line_chart_dates.append(str(date))
            line_chart_data.append(cumulative)

        line_chart = {
            'labels': line_chart_dates,
            'data': line_chart_data
        }

        return render_template(
            'reports.html',
            pie_chart=pie_chart,
            bar_chart=bar_chart,
            line_chart=line_chart,
            preset=preset,
            start_date=start_date,
            end_date=end_date
        )
    finally:
        db.close()


@bp.route('/export')
def export():
    """CSV 匯出"""
    db = Session()

    try:
        export_type = request.args.get('type', 'expenses')  # expenses / repayments / combined
        preset = request.args.get('preset', '')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 計算日期範圍
        if preset and preset != 'custom':
            date_start, date_end = get_date_range(preset)
        else:
            date_start = start_date
            date_end = end_date

        output = StringIO()
        writer = csv.writer(output)

        if export_type == 'expenses':
            # 支出匯出
            writer.writerow(['日期', '類別', '名稱', '金額'])

            query = db.query(Expense).join(Category).order_by(Expense.date.desc())
            if date_start and date_end:
                query = query.filter(Expense.date >= date_start, Expense.date <= date_end)

            for expense in query.all():
                writer.writerow([
                    expense.date,
                    expense.category.name.value,
                    expense.name,
                    expense.amount
                ])

            filename = 'expenses.csv'

        elif export_type == 'repayments':
            # 還款匯出
            writer.writerow(['日期', '金額'])

            query = db.query(Repayment).order_by(Repayment.date.desc())
            if date_start and date_end:
                query = query.filter(Repayment.date >= date_start, Repayment.date <= date_end)

            for repayment in query.all():
                writer.writerow([repayment.date, repayment.amount])

            filename = 'repayments.csv'

        else:  # combined
            # 合併匯出
            writer.writerow(['類型', '日期', '類別', '名稱', '金額'])

            # 支出
            expenses_query = db.query(Expense).join(Category).order_by(Expense.date.desc())
            if date_start and date_end:
                expenses_query = expenses_query.filter(Expense.date >= date_start, Expense.date <= date_end)

            for expense in expenses_query.all():
                writer.writerow([
                    'expense',
                    expense.date,
                    expense.category.name.value,
                    expense.name,
                    expense.amount
                ])

            # 還款
            repayments_query = db.query(Repayment).order_by(Repayment.date.desc())
            if date_start and date_end:
                repayments_query = repayments_query.filter(Repayment.date >= date_start, Repayment.date <= date_end)

            for repayment in repayments_query.all():
                writer.writerow([
                    'repayment',
                    repayment.date,
                    '',
                    '',
                    repayment.amount
                ])

            filename = 'combined.csv'

        # 建立回應（UTF-8 with BOM for Excel）
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response

    finally:
        db.close()
