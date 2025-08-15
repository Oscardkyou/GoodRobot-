import asyncio
import os
import uvicorn
import multiprocessing
from admin.app import create_app
from app.bot import bot

def run_admin_panel():
    """Запуск админ-панели"""
    port = int(os.environ.get("ADMIN_PORT", 8000))
    uvicorn.run(
        "run_admin:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )

def run_bot():
    """Запуск Telegram бота"""
    asyncio.run(bot.polling())

if __name__ == "__main__":
    # Создаем процессы для бота и админ-панели
    admin_process = multiprocessing.Process(target=run_admin_panel)
    bot_process = multiprocessing.Process(target=run_bot)
    
    try:
        print("Запуск админ-панели...")
        admin_process.start()
        
        print("Запуск Telegram бота...")
        bot_process.start()
        
        # Ожидаем завершения процессов
        admin_process.join()
        bot_process.join()
    except KeyboardInterrupt:
        print("Завершение работы...")
    finally:
        # Корректно завершаем процессы при выходе
        if admin_process.is_alive():
            admin_process.terminate()
        if bot_process.is_alive():
            bot_process.terminate()
        
        print("Все процессы остановлены.")