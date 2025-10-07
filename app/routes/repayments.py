from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from datetime import timedelta
from decimal import Decimal

from app.database import Session
from app.models import Repayment, taipei_today

bp = Blueprint('repayments', __name__, url_prefix='/repayments')


def get_date_range(preset):
    """根據預設選項計算日期範圍（與 expenses 相同邏輯）"""
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
    """還款流水頁"""
    db = Session()

    try:
        # 篩選參數
        preset = request.args.get('preset', '')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        min_amount = request.args.get('min_amount')
        max_amount = request.args.get('max_amount')
        page = int(request.args.get('page', 1))

        # 建立查詢
        query = db.query(Repayment)

        # 日期篩選
        if preset and preset != 'custom':
            date_start, date_end = get_date_range(preset)
            if date_start and date_end:
                query = query.filter(Repayment.date >= date_start, Repayment.date <= date_end)
        elif start_date or end_date:
            if start_date:
                query = query.filter(Repayment.date >= start_date)
            if end_date:
                query = query.filter(Repayment.date <= end_date)

        # 金額範圍
        if min_amount:
            query = query.filter(Repayment.amount >= Decimal(min_amount))
        if max_amount:
            query = query.filter(Repayment.amount <= Decimal(max_amount))

        # 排序：日期新→舊
        query = query.order_by(Repayment.date.desc(), Repayment.created_at.desc())

        # 分頁（每頁 50 筆）
        per_page = 50
        total = query.count()
        total_pages = (total + per_page - 1) // per_page
        repayments = query.limit(per_page).offset((page - 1) * per_page).all()

        return render_template(
            'repayments.html',
            repayments=repayments,
            page=page,
            total_pages=total_pages,
            total=total,
            filters={
                'preset': preset,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount
            }
        )
    finally:
        db.close()


@bp.route('/<uuid:repayment_id>/edit', methods=['GET', 'POST'])
def edit(repayment_id):
    """編輯還款"""
    db = Session()

    try:
        repayment = db.query(Repayment).filter(Repayment.id == repayment_id).first()
        if not repayment:
            abort(404)

        if request.method == 'POST':
            repayment.amount = Decimal(request.form.get('amount'))
            repayment.date = request.form.get('date') or taipei_today()

            db.commit()
            flash('✅ 還款已更新', 'success')
            return redirect(url_for('repayments.index'))

        # GET: 顯示編輯表單
        return render_template('repayment_edit.html', repayment=repayment)

    except Exception as e:
        db.rollback()
        flash(f'❌ 更新失敗: {str(e)}', 'error')
        return redirect(url_for('repayments.index'))
    finally:
        db.close()


@bp.route('/<uuid:repayment_id>/delete', methods=['POST'])
def delete(repayment_id):
    """刪除還款"""
    db = Session()

    try:
        repayment = db.query(Repayment).filter(Repayment.id == repayment_id).first()
        if not repayment:
            abort(404)
        db.delete(repayment)
        db.commit()

        flash('✅ 還款已刪除', 'success')
        return redirect(url_for('repayments.index'))

    except Exception as e:
        db.rollback()
        flash(f'❌ 刪除失敗: {str(e)}', 'error')
        return redirect(url_for('repayments.index'))
    finally:
        db.close()
