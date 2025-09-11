"""Response formatting utilities for AI Agent."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def format_order_summary(order_data: Dict[str, Any]) -> str:
    """Format order data as a summary string.
    
    Args:
        order_data: Order data dictionary
        
    Returns:
        Formatted summary string
    """
    summary_parts = [
        f"📦 Заказ #{order_data.get('id', 'N/A')}",
        f"Категория: {order_data.get('category', 'Не указана')}",
        f"Срочность: {order_data.get('urgency', 'Средняя')}",
        f"Статус: {order_data.get('status', 'Новый')}"
    ]
    
    if 'price' in order_data:
        summary_parts.append(f"Цена: {order_data['price']} KZT")
    
    if 'master_name' in order_data:
        summary_parts.append(f"Мастер: {order_data['master_name']}")
    
    return "\n".join(summary_parts)

def format_master_list(masters: List[Dict[str, Any]]) -> str:
    """Format list of masters as a string.
    
    Args:
        masters: List of master dictionaries
        
    Returns:
        Formatted master list string
    """
    if not masters:
        return "😔 Пока нет доступных мастеров в этой категории."
    
    lines = [f"🔍 Найдено мастеров: {len(masters)}\n"]
    
    for i, master in enumerate(masters[:5], 1):  # Show only first 5 masters
        name = master.get('name', 'Мастер')
        specialty = master.get('specialty', 'Специалист')
        rating = master.get('rating', 'Нет оценок')
        
        lines.append(f"{i}. {name} ({specialty}) - Рейтинг: {rating}")
    
    if len(masters) > 5:
        lines.append(f"\n... и ещё {len(masters) - 5} мастеров")
    
    return "\n".join(lines)

def format_ai_response(response: str, context: Dict[str, Any] = None) -> str:
    """Format AI response with appropriate styling.
    
    Args:
        response: AI response text
        context: Additional context for formatting
        
    Returns:
        Formatted response string
    """
    # Add AI indicator
    formatted = f"🤖 AI Помощник:\n{response}"
    
    # Add context-specific information if provided
    if context and context.get('confidence', 1.0) < 0.7:
        formatted += "\n\n⚠️ Внимание: Уверенность в ответе низкая. Рекомендуется уточнить информацию."
    
    return formatted
