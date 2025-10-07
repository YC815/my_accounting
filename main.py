from app import create_app

app = create_app()

if __name__ == "__main__":
    # 開發模式啟動（Gunicorn 生產環境不會用到這段）
    app.run(host='0.0.0.0', port=5001, debug=True)
