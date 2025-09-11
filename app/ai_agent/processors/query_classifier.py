"""Query classification for AI Agent."""
import logging

logger = logging.getLogger(__name__)

class QueryClassifier:
    """Classifier for determining query categories."""
    
    def __init__(self, text_classifier):
        """Initialize the query classifier.
        
        Args:
            text_classifier: Text classifier instance
        """
        self.text_classifier = text_classifier
    
    async def classify(self, query: str) -> str:
        """Classify user query.
        
        Args:
            query: User query text
            
        Returns:
            Query category
        """
        try:
            return self.text_classifier.classify_query_category(query)
        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            return "general"
