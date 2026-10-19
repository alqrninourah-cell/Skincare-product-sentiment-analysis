"""
Input validation utilities.

This module provides validation functions for user inputs.
"""

from typing import Tuple, Optional


# Valid skin types
VALID_SKIN_TYPES = {'dry', 'oily', 'combination', 'normal', 'sensitive'}


def validate_skin_type(skin_type: Optional[str]) -> Tuple[bool, str]:
    """
    Validate skin type input.
    
    Args:
        skin_type (str, optional): Skin type to validate
        
    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): True if valid, False otherwise
            - error_message (str): Error message if invalid, empty string if valid
    """
    if not skin_type:
        return False, "Skin type is required"
    
    skin_type_clean = skin_type.strip().lower()
    
    if skin_type_clean not in VALID_SKIN_TYPES:
        return False, f"Invalid skin type. Must be one of: {', '.join(sorted(VALID_SKIN_TYPES))}"
    
    return True, ""


def validate_review_text(text: Optional[str], min_length: int = 10) -> Tuple[bool, str]:
    """
    Validate review text input.
    
    Args:
        text (str, optional): Review text to validate
        min_length (int): Minimum required length (default: 10)
        
    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): True if valid, False otherwise
            - error_message (str): Error message if invalid, empty string if valid
    """
    if not text:
        return False, "Review text is required"
    
    text_clean = text.strip()
    
    if len(text_clean) < min_length:
        return False, f"Review text must be at least {min_length} characters long"
    
    if len(text_clean) > 2000:
        return False, "Review text must not exceed 2000 characters"
    
    return True, ""


def validate_rating(rating: Optional[int]) -> Tuple[bool, str]:
    """
    Validate rating input.
    
    Args:
        rating (int, optional): Rating to validate (should be 1-5)
        
    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): True if valid, False otherwise
            - error_message (str): Error message if invalid, empty string if valid
    """
    if rating is None:
        return False, "Rating is required"
    
    if not isinstance(rating, int):
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            return False, "Rating must be a number"
    
    if rating < 1 or rating > 5:
        return False, "Rating must be between 1 and 5"
    
    return True, ""


def validate_concerns(concerns: Optional[str], min_length: int = 3) -> Tuple[bool, str]:
    """
    Validate concerns input.
    
    Args:
        concerns (str, optional): Concerns text to validate
        min_length (int): Minimum required length (default: 3)
        
    Returns:
        tuple: (is_valid, error_message)
            - is_valid (bool): True if valid, False otherwise
            - error_message (str): Error message if invalid, empty string if valid
    """
    if not concerns:
        return False, "Concerns description is required"
    
    concerns_clean = concerns.strip()
    
    if len(concerns_clean) < min_length:
        return False, f"Concerns must be at least {min_length} characters long"
    
    if len(concerns_clean) > 500:
        return False, "Concerns must not exceed 500 characters"
    
    return True, ""

