import os

from admin.app import create_app

# Создаем экземпляр FastAPI приложения
app = create_app()

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("ADMIN_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
