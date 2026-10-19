"""
Recommendation Service.

This service handles product recommendation logic based on user skin type,
concerns, and review sentiment analysis.
"""

from typing import List, Optional
from models import db, Product, Review, User
from .sentiment_service import SentimentService
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service for generating product recommendations.
    
    Generates personalized product recommendations based on:
    - User skin type
    - User concerns
    - Positive sentiment reviews
    - Product ratings and review counts
    """
    
    def __init__(self, sentiment_service: Optional[SentimentService] = None):
        """
        Initialize recommendation service.
        
        Args:
            sentiment_service (SentimentService, optional): Sentiment analysis service.
                If not provided, creates a new instance.
        """
        self.sentiment_service = sentiment_service or SentimentService()
    
    def get_recommendations(
        self,
        skin_type: str,
        concerns: str,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Product]:
        """
        Get product recommendations based on skin type and concerns.
        
        Args:
            skin_type (str): User's skin type (dry, oily, combination, normal, sensitive)
            concerns (str): User's skin concerns
            user_id (int, optional): User ID if authenticated, None for anonymous users
            limit (int): Maximum number of recommendations to return (default: 20)
            
        Returns:
            list: List of Product objects recommended for the user
            
        Raises:
            ValueError: If skin_type is empty or invalid
            SQLAlchemyError: If database query fails
        """
        if not skin_type or not skin_type.strip():
            raise ValueError("Skin type is required")
        
        skin_type = skin_type.strip().lower()
        
        try:
            # Get reviews matching skin_type
            reviews = Review.query.filter_by(skin_type=skin_type).all()
            
            if not reviews:
                logger.warning(f"No reviews found for skin type: {skin_type}")
                return []
            
            # Analyze sentiment for reviews that don't have sentiment yet
            self._ensure_sentiment_analyzed(reviews)
            
            # Filter positive reviews
            positive_reviews = [
                r for r in reviews 
                if r.sentiment and r.sentiment == 'positive'
            ]
            
            if not positive_reviews:
                logger.warning(f"No positive reviews found for skin type: {skin_type}")
                return []
            
            # Get unique product IDs from positive reviews
            product_ids = list(set([r.product_id for r in positive_reviews]))
            
            # Get products
            products = Product.query.filter(Product.id.in_(product_ids)).all()
            
            # Sort by number of positive reviews (simple ranking)
            products_with_counts = []
            for product in products:
                positive_count = sum(
                    1 for r in positive_reviews if r.product_id == product.id
                )
                products_with_counts.append((product, positive_count))
            
            # Sort by positive review count (descending)
            products_with_counts.sort(key=lambda x: x[1], reverse=True)
            
            # Extract products and limit results
            recommended_products = [p for p, _ in products_with_counts[:limit]]
            
            logger.info(
                f"Generated {len(recommended_products)} recommendations "
                f"for skin_type={skin_type}, user_id={user_id}"
            )
            
            return recommended_products
            
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_recommendations: {e}")
            db.session.rollback()
            raise
    
    def _ensure_sentiment_analyzed(self, reviews: List[Review]) -> None:
        """
        Ensure all reviews have sentiment analyzed.
        
        Analyzes sentiment for reviews that don't have sentiment yet.
        Updates database in batch for efficiency.
        
        Args:
            reviews (list): List of Review objects to check/analyze
        """
        reviews_to_update = []
        
        for review in reviews:
            if not review.sentiment and review.text:
                result = self.sentiment_service.analyze(review.text)
                review.sentiment = result['sentiment']
                reviews_to_update.append(review)
        
        # Commit in batch
        if reviews_to_update:
            try:
                db.session.commit()
                logger.debug(f"Updated sentiment for {len(reviews_to_update)} reviews")
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Error updating sentiment: {e}")
                raise
    
    def get_recommendations_with_scores(
        self,
        skin_type: str,
        concerns: str,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> List[dict]:
        """
        Get recommendations with confidence scores and metadata.
        
        Similar to get_recommendations but returns additional information
        including recommendation scores and review counts.
        
        Args:
            skin_type (str): User's skin type
            concerns (str): User's skin concerns
            user_id (int, optional): User ID if authenticated
            limit (int): Maximum number of recommendations
            
        Returns:
            list: List of dicts with product and recommendation metadata:
                - product (Product): Product object
                - positive_reviews_count (int): Number of positive reviews
                - total_reviews_count (int): Total reviews for product
                - recommendation_score (float): Recommendation confidence score
        """
        products = self.get_recommendations(skin_type, concerns, user_id, limit)
        reviews = Review.query.filter_by(skin_type=skin_type).all()
        
        recommendations = []
        for product in products:
            product_reviews = [r for r in reviews if r.product_id == product.id]
            positive_count = sum(
                1 for r in product_reviews 
                if r.sentiment == 'positive'
            )
            total_count = len(product_reviews)
            
            # Simple recommendation score (could be enhanced)
            score = positive_count / total_count if total_count > 0 else 0.0
            
            recommendations.append({
                'product': product,
                'positive_reviews_count': positive_count,
                'total_reviews_count': total_count,
                'recommendation_score': score
            })
        
        return recommendations

