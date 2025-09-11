тлично! У вас уже есть хорошая структура для ИИ-помощника в телеграм боте. Давайте интегрируем модель ai-forever/rugpt3small_based_on_gpt2 в ваш код.

Создадим файл app/ai_agent/simple_ai.py с реализацией:

python
"""Simple AI implementation using Hugging Face transformers."""
import logging
from transformers import pipeline
import asyncio
from functools import lru_cache

logger = logging.getLogger(__name__)

# Глобальная переменная для кэширования pipeline
_ai_pipeline = None

@lru_cache(maxsize=1)
def get_ai_pipeline():
    """Создает и кэширует AI pipeline для генерации текста."""
    global _ai_pipeline
    if _ai_pipeline is None:
        try:
            logger.info("Загрузка AI модели...")
            _ai_pipeline = pipeline(
                "text-generation",
                model="ai-forever/rugpt3small_based_on_gpt2",
                device=-1  # Используем CPU (-1) или GPU (0, 1, ...)
            )
            logger.info("AI модель успешно загружена!")
        except Exception as e:
            logger.error(f"Ошибка загрузки AI модели: {e}")
            raise
    return _ai_pipeline

def get_ai_response(user_input: str) -> str:
    """
    Генерирует ответ на основе пользовательского ввода.

    Args:
        user_input: Текст от пользователя

    Returns:
        Сгенерированный ответ
    """
    try:
        # Получаем pipeline (загрузится при первом вызове)
        pipe = get_ai_pipeline()

        # Генерируем ответ
        result = pipe(
            user_input,
            max_length=150,
            num_return_sequences=1,
            temperature=0.7,
            top_k=50,
            top_p=0.9,
            pad_token_id=50256,
            do_sample=True
        )

        # Извлекаем сгенерированный текст
        generated_text = result[0]['generated_text']

        # Убираем исходный запрос из ответа, если он там есть
        if generated_text.startswith(user_input):
            generated_text = generated_text[len(user_input):].strip()

        # Обрезаем до разумной длины для Telegram
        if len(generated_text) > 4000:
            generated_text = generated_text[:4000] + "..."

        return generated_text if generated_text else "Извините, не удалось сгенерировать ответ."

    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}")
        return "Извините, в настоящее время у меня технические трудности. Попробуйте позже."
Теперь обновим ваш обработчик в handlers/ai_assistant.py:

python
"""AI Assistant handler for GoodRobot bot."""
import logging
from asyncio import get_running_loop

from aiogram import F, Router
from aiogram.types import Message

# Импортируем нашу реализацию ИИ
from app.ai_agent.simple_ai import get_ai_response

logger = logging.getLogger(__name__)
router = Router()

# Состояния для отслеживания диалога с ИИ
ai_users = set()

@router.message(F.text == "🤖 ИИ-помощник")
async def ai_assistant_button(message: Message) -> None:
    """Обработчик кнопки ИИ-помощника для клиентов."""
    # Добавляем пользователя в режим ИИ
    ai_users.add(message.from_user.id)

    await message.answer(
        "🤖 Привет! Я ИИ-помощник. Задайте мне вопрос, и я постараюсь вам помочь.\n\n"
        "Например, вы можете спросить:\n"
        "- Как создать заказ?\n"
        "- Как выбрать мастера?\n"
        "- Что делать, если возникла проблема?\n\n"
        "Просто напишите ваш вопрос, и я отвечу!\n\n"
        "Чтобы выйти из режима ИИ, отправьте /stop"
    )

@router.message(F.text == "/stop")
async def stop_ai_mode(message: Message) -> None:
    """Выход из режима ИИ-помощника."""
    if message.from_user.id in ai_users:
        ai_users.discard(message.from_user.id)
        await message.answer("Вы вышли из режима ИИ-помощника.")
    else:
        await message.answer("Вы не в режиме ИИ-помощника.")

@router.message(F.text)
async def ai_assistant_query(message: Message) -> None:
    """Обработчик вопросов к ИИ-помощнику."""
    # Проверяем, что пользователь в режиме ИИ
    if message.from_user.id not in ai_users:
        return  # Игнорируем сообщения не в режиме ИИ

    # Показываем статус "печатает"
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    user_question = message.text

    # Запускаем генерацию ответа в отдельном потоке, чтобы не блокировать бота
    loop = get_running_loop()
    try:
        response = await loop.run_in_executor(None, get_ai_response, user_question)
        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка в ИИ-помощнике: {e}")
        await message.answer("Извините, произошла ошибка при обработке вашего запроса.")
Также добавьте обработку выхода из режима ИИ при команде /start или других командах:

python
@router.message(F.text == "/start")
async def start_command(message: Message) -> None:
    """Обработчик команды /start."""
    # Выходим из режима ИИ при старте
    if message.from_user.id in ai_users:
        ai_users.discard(message.from_user.id)

    await message.answer("Добро пожаловать в бота! Используйте меню для навигации.")
Это решение:

Автоматически загружает модель из интернета при первом использовании

Кэширует pipeline для последующих запросов

Работает асинхронно - не блокирует бота во время генерации

Имеет систему состояний - отслеживает, кто общается с ИИ

Обрабатывает ошибки и ограничивает длину сообщений для Telegram

Убирает повторение вопроса из ответа модели

Модель будет автоматически загружена из интернета при первом запросе к ИИ-помощнику и останется в памяти для последующих запросов.