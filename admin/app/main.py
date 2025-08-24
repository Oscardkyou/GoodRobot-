from datetime import datetime
import os

# Импортируем функцию create_app из admin/app/__init__.py
from admin.app import create_app

# Создаем приложение с помощью функции create_app
app = create_app()

# Добавляем дополнительный маршрут для проверки работоспособности
@app.get("/health")
async def health_check():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}