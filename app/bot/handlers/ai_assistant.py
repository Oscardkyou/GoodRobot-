"""AI Assistant handler for GoodRobot bot (local LLM)."""
import logging
from asyncio import get_running_loop

from aiogram import F, Router
from aiogram.types import Message

# Импортируем локальную реализацию ИИ (DistilGPT-2 через Transformers)
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

@router.message(F.text == "/start")
async def start_command(message: Message) -> None:
    """Обработчик команды /start."""
    # Выходим из режима ИИ при старте
    if message.from_user.id in ai_users:
        ai_users.discard(message.from_user.id)

    await message.answer("Добро пожаловать в бота! Используйте меню для навигации.")

@router.message(F.text)
async def ai_assistant_query(message: Message) -> None:
    """Обработчик запроса к локальной модели (DistilGPT-2)."""
    if message.from_user.id not in ai_users:
        return

    try:
        loop = get_running_loop()
        response = await loop.run_in_executor(
            None,
            get_ai_response,
            message.text,
            True  # параметр сохраняем для совместимости; внутри игнорируется
        )
        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка ИИ: {e}")
        await message.answer("Извините, не могу обработать запрос")
