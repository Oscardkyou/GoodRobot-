"""Data preprocessing utilities for AI Agent."""
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text.
    
    Args:
        text: Input text
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove extra punctuation
    text = re.sub(r'[.!?]+', '.', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract entities from text.
    
    Args:
        text: Input text
        
    Returns:
        Dict with extracted entities
    """
    entities = {
        "phones": [],
        "emails": [],
        "addresses": []
    }
    
    # Extract phone numbers (simple pattern)
    phone_pattern = r'(?:\+?7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
    entities["phones"] = re.findall(phone_pattern, text)
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    entities["emails"] = re.findall(email_pattern, text)
    
    return entities

def prepare_context_for_model(context: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare context data for model input.
    
    Args:
        context: Raw context data
        
    Returns:
        Prepared context data
    """
    prepared = {}
    
    # Copy basic fields
    for key, value in context.items():
        if isinstance(value, (str, int, float, bool, list, dict)):
            prepared[key] = value
    
    # Clean text fields
    text_fields = ["description", "query", "message"]
    for field in text_fields:
        if field in prepared and isinstance(prepared[field], str):
            prepared[field] = clean_text(prepared[field])
    
    return prepared
