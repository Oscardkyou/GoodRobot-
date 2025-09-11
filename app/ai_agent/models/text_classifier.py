"""Text classification models for AI Agent."""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TextClassifier:
    """Text classifier for categorizing user input."""
    
    def __init__(self):
        """Initialize the text classifier."""
        # In a real implementation, this would load a pre-trained model
        # For now, we'll use simple keyword-based classification
        self.order_categories = {
            "plumbing": ["водопровод", "труба", "сантехник", "вода", "кран"],
            "electrical": ["электрик", "розетка", "провод", "свет", "электричество"],
            "repair": ["ремонт", "починить", "сломался", "не работает"],
            "installation": ["установить", "установка", "монтаж", "собрать"],
            "cleaning": ["уборка", "чистка", "помыть", "грязь"],
            "other": []
        }
        
        self.query_categories = {
            "technical": ["не работает", "ошибка", "проблема", "технический"],
            "billing": ["оплата", "деньги", "стоимость", "тариф"],
            "general": ["вопрос", "справка", "информация", "как"],
            "support": ["помощь", "поддержка", "помочь", "помогите"]
        }
        
        self.urgency_levels = {
            "high": ["срочно", "немедленно", "нужно срочно", "авария", "протечка"],
            "medium": ["скоро", "в ближайшее время", "нужно"],
            "low": ["когда будет", "планирую", "в будущем"]
        }
    
    def classify_order_category(self, text: str) -> str:
        """Classify order category based on text content.
        
        Args:
            text: Order description text
            
        Returns:
            Category name
        """
        text_lower = text.lower()
        
        # Count matches for each category
        category_scores = {}
        for category, keywords in self.order_categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            category_scores[category] = score
        
        # Return category with highest score, or 'other' if no matches
        best_category = max(category_scores, key=category_scores.get)
        return best_category if category_scores[best_category] > 0 else "other"
    
    def classify_query_category(self, text: str) -> str:
        """Classify query category based on text content.
        
        Args:
            text: Query text
            
        Returns:
            Query category
        """
        text_lower = text.lower()
        
        # Count matches for each category
        category_scores = {}
        for category, keywords in self.query_categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            category_scores[category] = score
        
        # Return category with highest score, or 'general' if no matches
        best_category = max(category_scores, key=category_scores.get)
        return best_category if category_scores[best_category] > 0 else "general"
    
    def determine_urgency(self, text: str) -> str:
        """Determine urgency level of order.
        
        Args:
            text: Order description text
            
        Returns:
            Urgency level (high, medium, low)
        """
        text_lower = text.lower()
        
        # Check for urgency keywords
        for level, keywords in self.urgency_levels.items():
            if any(keyword in text_lower for keyword in keywords):
                return level
        
        # Default to medium urgency
        return "medium"
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract important keywords from text.
        
        Args:
            text: Input text
            max_keywords: Maximum number of keywords to return
            
        Returns:
            List of important keywords
        """
        # Simple keyword extraction based on word frequency
        # In a real implementation, this would use more sophisticated NLP techniques
        words = text.lower().split()
        # Remove common stop words
        stop_words = {"и", "в", "на", "с", "по", "к", "у", "о", "от", "для", "не", "но", "то", "ли"}
        keywords = [word.strip(".,!?;:") for word in words if word not in stop_words and len(word) > 2]
        
        # Return unique keywords (up to max_keywords)
        return list(dict.fromkeys(keywords))[:max_keywords]
