"""Text generation models for AI Agent."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TextGenerator:
    """Text generator for creating enhanced descriptions and responses."""
    
    def __init__(self):
        """Initialize the text generator."""
        # In a real implementation, this would load a pre-trained language model
        # For now, we'll use template-based generation
        pass
    
    async def generate_enhanced_description(self, original_description: str, category: str, 
                                          urgency: str, keywords: List[str]) -> str:
        """Generate an enhanced order description.
        
        Args:
            original_description: Original description from client
            category: Order category
            urgency: Urgency level
            keywords: Extracted keywords
            
        Returns:
            Enhanced description
        """
        # In a real implementation, this would use a language model to generate
        # a more detailed and structured description
        
        # For now, we'll enhance the description with structured information
        enhanced_parts = [
            f"Описание проблемы: {original_description}",
            f"Категория: {category}",
            f"Срочность: {urgency}",
            f"Ключевые слова: {', '.join(keywords) if keywords else 'не определены'}"
        ]
        
        return "\n\n".join(enhanced_parts)
    
    async def generate(self, context: Dict[str, Any]) -> str:
        """Generate response based on context.
        
        Args:
            context: Context information
            
        Returns:
            Generated response
        """
        # In a real implementation, this would use a language model
        # For now, we'll return a simple response based on context
        
        if "type" in context and context["type"] == "order_confirmation":
            return self._generate_order_confirmation(context)
        elif "type" in context and context["type"] == "master_recommendation":
            return self._generate_master_recommendation(context)
        else:
            return "Спасибо за ваш запрос. Я обработал вашу информацию и передал её соответствующему специалисту."
    
    def _generate_order_confirmation(self, context: Dict[str, Any]) -> str:
        """Generate order confirmation message.
        
        Args:
            context: Order context
            
        Returns:
            Confirmation message
        """
        order_id = context.get("order_id", "N/A")
        category = context.get("category", "услуга")
        urgency = context.get("urgency", "средняя")
        
        return (
            f"✅ Ваш заказ #{order_id} успешно создан!\n\n"
            f"Категория: {category}\n"
            f"Срочность: {urgency}\n\n"
            f"Мы уже ищем подходящего мастера для выполнения работ. "
            f"Вы получите уведомление, когда мастер откликнется на ваш заказ."
        )
    
    def _generate_master_recommendation(self, context: Dict[str, Any]) -> str:
        """Generate master recommendation message.
        
        Args:
            context: Recommendation context
            
        Returns:
            Recommendation message
        """
        category = context.get("category", "мастер")
        count = context.get("count", 0)
        
        if count > 0:
            return (
                f"🔍 Найдено {count} мастеров в категории '{category}'.\n\n"
                f"Вы можете выбрать одного из них или дождаться дополнительных предложений.\n"
                f"Для просмотра предложений нажмите на кнопку 'Мои заказы'."
            )
        else:
            return (
                f"😔 К сожалению, пока нет доступных мастеров в категории '{category}'.\n\n"
                f"Мы продолжаем поиск и уведомим вас, как только найдем подходящего специалиста."
            )
