"""Core AI Agent implementation for GoodRobot project."""
import logging
from typing import Dict, Any, Optional

from app.ai_agent.models.text_classifier import TextClassifier
from app.ai_agent.models.text_generator import TextGenerator
from app.ai_agent.processors.order_processor import OrderProcessor
from app.ai_agent.processors.query_classifier import QueryClassifier

logger = logging.getLogger(__name__)

class AIAgent:
    """Main AI Agent class that orchestrates all AI functionality."""

    def __init__(self):
        """Initialize the AI Agent with all necessary components."""
        from app.ai_agent.simple_ai import GeminiAI  # local CPU LLM wrapper (DistilGPT-2)
        self.gemini = GeminiAI()
        self.text_classifier = TextClassifier()
        self.text_generator = TextGenerator()
        self.order_processor = OrderProcessor(self.text_generator, self.text_classifier)
        self.query_classifier = QueryClassifier(self.text_classifier)

    async def initialize(self):
        # Initialize local LLM pipeline lazily
        self.gemini.initialize()

    async def process_order_description(self, description: str) -> Dict[str, Any]:
        """Process and enhance order description using AI.

        Args:
            description: Raw order description from client

        Returns:
            Dict with enhanced description and extracted metadata
        """
        try:
            return await self.order_processor.process_description(description)
        except Exception as e:
            logger.error(f"Error processing order description: {e}")
            # Return original description if AI processing fails
            return {
                "enhanced_description": description,
                "category": "other",
                "urgency": "medium",
                "keywords": []
            }

    async def process_query(self, query: str) -> str:
        """Обработка запроса с приоритетом локальной модели (DistilGPT-2)"""
        gemini_res = self.gemini.get_response(query)
        if gemini_res:
            return gemini_res

        # Fallback логика
        return await self.query_classifier.classify(query)

    async def classify_query(self, query: str) -> str:
        """Classify user query to determine appropriate response.

        Args:
            query: User query text

        Returns:
            Query category (e.g., "technical", "billing", "general")
        """
        try:
            return await self.query_classifier.classify(query)
        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            return "general"

    async def generate_response(self, context: Dict[str, Any]) -> str:
        """Generate AI response based on context.

        Args:
            context: Context information for response generation

        Returns:
            Generated response text
        """
        try:
            return await self.text_generator.generate(context)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Извините, я не могу обработать ваш запрос в данный момент."

# Global instance
ai_agent = AIAgent()

def get_ai_agent() -> AIAgent:
    """Get the global AI Agent instance."""
    return ai_agent
