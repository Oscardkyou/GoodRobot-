"""Order processing with AI enhancement."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class OrderProcessor:
    """Processor for enhancing order descriptions using AI."""
    
    def __init__(self, text_generator, text_classifier):
        """Initialize the order processor.
        
        Args:
            text_generator: Text generator instance
            text_classifier: Text classifier instance
        """
        self.text_generator = text_generator
        self.text_classifier = text_classifier
    
    async def process_description(self, description: str) -> Dict[str, Any]:
        """Process and enhance order description.
        
        Args:
            description: Original order description
            
        Returns:
            Dict with enhanced description and metadata
        """
        try:
            # Classify the order category
            category = self.text_classifier.classify_order_category(description)
            
            # Determine urgency
            urgency = self.text_classifier.determine_urgency(description)
            
            # Extract keywords
            keywords = self.text_classifier.extract_keywords(description)
            
            # Generate enhanced description
            enhanced_description = await self.text_generator.generate_enhanced_description(
                description, category, urgency, keywords
            )
            
            return {
                "original_description": description,
                "enhanced_description": enhanced_description,
                "category": category,
                "urgency": urgency,
                "keywords": keywords
            }
        except Exception as e:
            logger.error(f"Error processing order description: {e}")
            # Return basic information if processing fails
            return {
                "original_description": description,
                "enhanced_description": description,
                "category": "other",
                "urgency": "medium",
                "keywords": []
            }
