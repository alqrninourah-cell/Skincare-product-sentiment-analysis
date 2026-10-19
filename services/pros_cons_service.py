"""
Pros/Cons Extraction Service.

This service extracts and aggregates pros and cons from product reviews
by analyzing positive and negative reviews separately.
"""

from typing import List, Dict, Optional
from models import db, Review, Product
from collections import Counter
import re
import logging

logger = logging.getLogger(__name__)


class ProsConsService:
    """
    Service for extracting pros and cons from product reviews.
    
    Aggregates common themes from positive reviews (pros) and
    negative reviews (cons) using keyword extraction and frequency analysis.
    """
    
    def __init__(self):
        """Initialize pros/cons service."""
        # Common positive keywords/phrases
        self.positive_keywords = [
            'love', 'amazing', 'great', 'excellent', 'wonderful', 'perfect',
            'works well', 'effective', 'good', 'best', 'recommend', 'happy',
            'smooth', 'soft', 'hydrated', 'moisturized', 'glowing', 'radiant',
            'cleared', 'improved', 'reduced', 'helped', 'fast', 'quick',
            'gentle', 'non-irritating', 'suitable', 'perfect for', 'ideal',
            'affordable', 'worth it', 'value', 'quality', 'results', 'visible'
        ]
        
        # Common negative keywords/phrases
        self.negative_keywords = [
            'disappointed', 'waste', 'not work', "doesn't work", 'ineffective',
            'irritating', 'burning', 'stinging', 'redness', 'breakout', 'acne',
            'dry', 'oily', 'greasy', 'sticky', 'pilling', 'peeling', 'rash',
            'allergic', 'sensitive', 'harsh', 'too strong', 'too weak',
            'expensive', 'overpriced', 'not worth', 'poor quality', 'bad',
            'worst', 'terrible', 'awful', 'avoid', 'return', 'refund'
        ]
        
        # Skin concern keywords
        self.concern_keywords = [
            'acne', 'breakout', 'irritation', 'dry', 'dryness', 'oily', 'oiliness',
            'redness', 'burning', 'stinging', 'allergic', 'rash', 'peeling',
            'sensitivity', 'texture', 'greasy', 'sticky', 'pilling', 'wrinkles',
            'fine lines', 'dark spots', 'hyperpigmentation', 'pores', 'blackheads'
        ]
    
    def get_product_insights(self, product_id: int, limit: int = 10) -> Dict:
        """
        Get comprehensive product insights including pros, cons, and sentiment breakdown.
        
        Args:
            product_id (int): Product ID
            limit (int): Maximum number of pros/cons to return
            
        Returns:
            dict: Dictionary containing:
                - pros (list): List of pros with frequency
                - cons (list): List of cons with frequency
                - sentiment_distribution (dict): Sentiment breakdown
                - total_reviews (int): Total review count
        """
        try:
            reviews = Review.query.filter_by(product_id=product_id).all()
            
            if not reviews:
                return {
                    'pros': [],
                    'cons': [],
                    'sentiment_distribution': {
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0,
                        'total': 0
                    },
                    'total_reviews': 0
                }
            
            # Extract pros from positive reviews
            positive_reviews = [r for r in reviews if r.sentiment == 'positive']
            pros = self.extract_pros(positive_reviews, limit)
            
            # Extract cons from negative reviews
            negative_reviews = [r for r in reviews if r.sentiment == 'negative']
            cons = self.extract_cons(negative_reviews, limit)
            
            # Get sentiment distribution
            sentiment_dist = {
                'positive': len(positive_reviews),
                'negative': len(negative_reviews),
                'neutral': len([r for r in reviews if r.sentiment == 'neutral']),
                'total': len(reviews)
            }
            
            return {
                'pros': pros,
                'cons': cons,
                'sentiment_distribution': sentiment_dist,
                'total_reviews': len(reviews)
            }
            
        except Exception as e:
            logger.error(f"Error getting product insights for product {product_id}: {e}")
            raise
    
    def extract_pros(self, reviews: List[Review], limit: int = 10) -> List[Dict]:
        """
        Extract pros (positive aspects) from positive reviews.
        
        Args:
            reviews (list): List of positive Review objects
            limit (int): Maximum number of pros to return
            
        Returns:
            list: List of dictionaries with 'theme' and 'frequency'
        """
        if not reviews:
            return []
        
        try:
            # Extract keywords and phrases from positive reviews
            themes = Counter()
            
            for review in reviews:
                if not review.text:
                    continue
                
                text_lower = review.text.lower()
                
                # Extract positive keywords
                for keyword in self.positive_keywords:
                    if keyword in text_lower:
                        themes[keyword] += 1
                
                # Extract positive phrases (2-3 word combinations)
                sentences = re.split(r'[.!?]+', text_lower)
                for sentence in sentences:
                    words = sentence.strip().split()
                    # Look for positive phrases
                    for i in range(len(words) - 1):
                        phrase = f"{words[i]} {words[i+1]}"
                        if any(kw in phrase for kw in self.positive_keywords):
                            themes[phrase] += 1
            
            # Get top themes
            top_themes = themes.most_common(limit * 2)
            
            # Group similar themes and format
            pros = []
            seen = set()
            
            for theme, frequency in top_themes:
                # Skip if too similar to already added theme
                if any(self._similar(theme, t['theme']) for t in pros):
                    continue
                
                pros.append({
                    'theme': theme.title(),
                    'frequency': frequency,
                    'percentage': round((frequency / len(reviews)) * 100, 1) if reviews else 0
                })
                
                if len(pros) >= limit:
                    break
            
            return pros
            
        except Exception as e:
            logger.error(f"Error extracting pros: {e}")
            return []
    
    def extract_cons(self, reviews: List[Review], limit: int = 10) -> List[Dict]:
        """
        Extract cons (negative aspects) from negative reviews.
        
        Args:
            reviews (list): List of negative Review objects
            limit (int): Maximum number of cons to return
            
        Returns:
            list: List of dictionaries with 'theme' and 'frequency'
        """
        if not reviews:
            return []
        
        try:
            # Extract keywords and phrases from negative reviews
            themes = Counter()
            
            for review in reviews:
                if not review.text:
                    continue
                
                text_lower = review.text.lower()
                
                # Extract negative keywords
                for keyword in self.negative_keywords:
                    if keyword in text_lower:
                        themes[keyword] += 1
                
                # Extract concern keywords
                for concern in self.concern_keywords:
                    if concern in text_lower:
                        themes[concern] += 1
                
                # Extract negative phrases
                sentences = re.split(r'[.!?]+', text_lower)
                for sentence in sentences:
                    words = sentence.strip().split()
                    for i in range(len(words) - 1):
                        phrase = f"{words[i]} {words[i+1]}"
                        if any(kw in phrase for kw in self.negative_keywords):
                            themes[phrase] += 1
            
            # Get top themes
            top_themes = themes.most_common(limit * 2)
            
            # Group similar themes and format
            cons = []
            
            for theme, frequency in top_themes:
                # Skip if too similar to already added theme
                if any(self._similar(theme, c['theme']) for c in cons):
                    continue
                
                cons.append({
                    'theme': theme.title(),
                    'frequency': frequency,
                    'percentage': round((frequency / len(reviews)) * 100, 1) if reviews else 0
                })
                
                if len(cons) >= limit:
                    break
            
            return cons
            
        except Exception as e:
            logger.error(f"Error extracting cons: {e}")
            return []
    
    def _similar(self, theme1: str, theme2: str) -> bool:
        """
        Check if two themes are similar (simple word overlap check).
        
        Args:
            theme1 (str): First theme
            theme2 (str): Second theme
            
        Returns:
            bool: True if themes are similar
        """
        words1 = set(theme1.lower().split())
        words2 = set(theme2.lower().split())
        
        if not words1 or not words2:
            return False
        
        # Check if significant overlap
        overlap = len(words1 & words2)
        min_len = min(len(words1), len(words2))
        
        # Consider similar if >50% word overlap
        return overlap > 0 and (overlap / min_len) > 0.5

