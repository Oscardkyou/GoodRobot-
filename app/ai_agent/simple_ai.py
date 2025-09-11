"""Simple AI implementation using Gemini API."""
import logging
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiAI:
    def __init__(self):
        self.api_key = os.getenv("API_GEMINI_FREE")
        self._model = None

    def initialize(self):
        if not self.api_key:
            raise ValueError("API_GEMINI_FREE не найден в .env")

        try:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            logger.error(f"Ошибка инициализации Gemini: {e}")

    def get_response(self, prompt: str) -> str:
        if not self._model:
            return None

        try:
            response = self._model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Ошибка Gemini API: {e}")
            return None

def get_ai_response(user_input: str, use_gemini: bool = True) -> str:
    """
    Генерирует ответ на основе пользовательского ввода.

    Args:
        user_input: Текст от пользователя
        use_gemini: Использовать ли Gemini API вместо локальной модели

    Returns:
        Сгенерированный ответ
    """
    try:
        # Используем только Gemini API для ответов
        logger.info("Используем Gemini API для ответа")
        
        # Создаем экземпляр GeminiAI
        gemini = GeminiAI()
        gemini.initialize()
        
        # Создаем промпт для Gemini
        prompt = f"Вы - помощник в сервисе поиска мастеров. Дайте краткий и ясный ответ на вопрос клиента. Отвечайте только на заданный вопрос, не добавляйте лишнюю информацию.\nВопрос: {user_input}\nОтвет:"
        
        # Получаем ответ от Gemini
        logger.info(f"Отправка запроса в Gemini API: {user_input}")
        generated_text = gemini.get_response(prompt)
        logger.info("Ответ от Gemini получен успешно")
        
        if not generated_text:
            return "Извините, я не могу дать точный ответ на этот вопрос. Попробуйте задать более конкретный вопрос."
        
        # Обрезаем до разумной длины для Telegram
        if len(generated_text) > 200:  # Увеличиваем максимальную длину для Gemini
            generated_text = generated_text[:200] + "..."
        
        logger.info(f"Сгенерированный ответ: {generated_text}")
        return generated_text

    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}")
        return "Извините, в настоящее время у меня технические трудности. Попробуйте позже."
