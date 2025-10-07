from flask import Flask
from app.database import init_db, Session


def create_app():
    """Flask app factory"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'  # 生產環境需改用環境變數

    # 初始化資料庫
    with app.app_context():
        init_db()

    # 註冊路由藍圖
    from app.routes import home, expenses, repayments, reports
    app.register_blueprint(home.bp)
    app.register_blueprint(expenses.bp)
    app.register_blueprint(repayments.bp)
    app.register_blueprint(reports.bp)

    # 清理 session（每次請求結束後）
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        Session.remove()

    return app
