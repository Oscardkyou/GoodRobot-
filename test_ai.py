"""Тестовый скрипт для проверки локальной модели DistilGPT-2.

Скрипт печатает краткие ответы без запуска pytest. Для автоматических тестов
используйте tests/test_ai_local.py
"""
import sys
import os

# Добавляем путь к проекту в sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.ai_agent.simple_ai import GeminiAI, get_ai_response
    print("✅ Модуль simple_ai успешно импортирован")
    
    # Создаем экземпляр локальной модели (обёртка GeminiAI)
    ai = GeminiAI()
    ai.initialize()
    print("✅ Локальная модель инициализирована")
    
    # Тестируем прямой запрос
    test_prompt = "Привет, расскажи о себе в двух предложениях"
    direct_response = ai.get_response(test_prompt)
    print("✅ Прямой ответ получен")
    print(f"Прямой ответ: {direct_response}")
    
    # Тестируем через функцию get_ai_response
    response = get_ai_response("Привет, как дела?")
    print("✅ Ответ через get_ai_response успешно сгенерирован")
    print(f"Ответ: {response}")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
