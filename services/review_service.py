"""
Review Service.

This service handles review-related operations including creation,
retrieval, and sentiment analysis.
"""

from typing import Optional, List
from models import db, Review, Product
from .sentiment_service import SentimentService
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReviewService:
    """
    Service for managing review operations.
    
    Handles CRUD operations for reviews and integrates with
    sentiment analysis service.
    """
    
    def __init__(self, sentiment_service: Optional[SentimentService] = None):
        """
        Initialize review service.
        
        Args:
            sentiment_service (SentimentService, optional): Sentiment analysis service.
                If not provided, creates a new instance.
        """
        self.sentiment_service = sentiment_service or SentimentService()
    
    def create_review(
        self,
        product_id: int,
        user_id: int,
        text: str,
        rating: int,
        skin_type: str
    ) -> Review:
        """
        Create a new review with automatic sentiment analysis.
        
        Args:
            product_id (int): ID of the product being reviewed
            user_id (int): ID of the user creating the review
            text (str): Review text content
            rating (int): Rating from 1 to 5
            skin_type (str): Reviewer's skin type
            
        Returns:
            Review: Created review object
            
        Raises:
            ValueError: If validation fails
            SQLAlchemyError: If database operation fails
        """
        # Validate inputs
        if not text or len(text.strip()) < 10:
            raise ValueError("Review text must be at least 10 characters")
        
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        if not skin_type:
            raise ValueError("Skin type is required")
        
        # Verify product exists
        product = Product.query.get(product_id)
        if not product:
            raise ValueError(f"Product with ID {product_id} not found")
        
        # Analyze sentiment
        sentiment_result = self.sentiment_service.analyze(text)
        sentiment = sentiment_result['sentiment']
        
        # Create review
        review = Review(
            product_id=product_id,
            user_id=user_id,
            text=text.strip(),
            rating=rating,
            sentiment=sentiment,
            skin_type=skin_type.strip().lower(),
            created_at=datetime.utcnow()
        )
        
        try:
            db.session.add(review)
            db.session.commit()
            
            logger.info(
                f"Created review {review.id} for product {product_id} "
                f"with sentiment: {sentiment}"
            )
            
            return review
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error creating review: {e}")
            raise
    
    def get_reviews_for_product(
        self,
        product_id: int,
        limit: Optional[int] = None,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> List[Review]:
        """
        Get reviews for a specific product.
        
        Args:
            product_id (int): Product ID
            limit (int, optional): Maximum number of reviews to return
            order_by (str): Field to order by (default: 'created_at')
            order_desc (bool): Order descending if True, ascending if False
            
        Returns:
            list: List of Review objects
        """
        query = Review.query.filter_by(product_id=product_id)
        
        # Order by specified field
        if order_by == 'created_at':
            query = query.order_by(
                Review.created_at.desc() if order_desc 
                else Review.created_at.asc()
            )
        elif order_by == 'rating':
            query = query.order_by(
                Review.rating.desc() if order_desc 
                else Review.rating.asc()
            )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def get_average_rating(self, product_id: int) -> float:
        """
        Calculate average rating for a product.
        
        Args:
            product_id (int): Product ID
            
        Returns:
            float: Average rating (0.0 if no reviews)
        """
        reviews = Review.query.filter_by(product_id=product_id).all()
        
        if not reviews:
            return 0.0
        
        ratings = [r.rating for r in reviews if r.rating is not None]
        
        if not ratings:
            return 0.0
        
        return sum(ratings) / len(ratings)
    
    def get_sentiment_distribution(self, product_id: int) -> dict:
        """
        Get sentiment distribution for a product's reviews.
        
        Args:
            product_id (int): Product ID
            
        Returns:
            dict: Sentiment counts and percentages:
                - positive (int): Count of positive reviews
                - negative (int): Count of negative reviews
                - neutral (int): Count of neutral reviews
                - total (int): Total review count
                - positive_percent (float): Percentage of positive reviews
                - negative_percent (float): Percentage of negative reviews
                - neutral_percent (float): Percentage of neutral reviews
        """
        reviews = Review.query.filter_by(product_id=product_id).all()
        
        total = len(reviews)
        positive = sum(1 for r in reviews if r.sentiment == 'positive')
        negative = sum(1 for r in reviews if r.sentiment == 'negative')
        neutral = sum(1 for r in reviews if r.sentiment == 'neutral')
        
        return {
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'total': total,
            'positive_percent': (positive / total * 100) if total > 0 else 0.0,
            'negative_percent': (negative / total * 100) if total > 0 else 0.0,
            'neutral_percent': (neutral / total * 100) if total > 0 else 0.0
        }
    
    def get_recommended_skin_types(self, product_id: int, min_positive_reviews: int = 3) -> List[str]:
        """
        Get skin types that have given positive reviews for a product.
        
        Args:
            product_id (int): Product ID
            min_positive_reviews (int): Minimum number of positive reviews 
                required for a skin type to be recommended (default: 3)
            
        Returns:
            list: List of skin type names (e.g., ['normal', 'dry', 'oily'])
        """
        reviews = Review.query.filter_by(product_id=product_id).all()
        
        # Count positive reviews by skin type
        skin_type_counts = {}
        for review in reviews:
            if review.sentiment == 'positive' and review.skin_type:
                skin_type = review.skin_type.lower().strip()
                skin_type_counts[skin_type] = skin_type_counts.get(skin_type, 0) + 1
        
        # Filter skin types that meet the minimum threshold
        recommended = [
            skin_type for skin_type, count 
            in skin_type_counts.items() 
            if count >= min_positive_reviews
        ]
        
        # Sort by count (descending) for better ordering
        recommended.sort(key=lambda x: skin_type_counts[x], reverse=True)
        
        return recommended
    
    def get_trustworthy_reviews(
        self,
        product_id: int,
        suspicious_threshold: float = 0.7,
        limit: Optional[int] = None,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> List[Review]:
        """
        Get trustworthy reviews filtered by suspicious score threshold.
        
        Args:
            product_id (int): Product ID
            suspicious_threshold (float): Maximum suspicious score (default: 0.7)
            limit (int, optional): Maximum number of reviews to return
            order_by (str): Field to order by (default: 'created_at')
            order_desc (bool): Order descending if True, ascending if False
            
        Returns:
            list: List of trustworthy Review objects
        """
        query = Review.query.filter_by(product_id=product_id)
        # Check if suspicious_score column exists before filtering
        try:
            query = query.filter(Review.suspicious_score < suspicious_threshold)
        except Exception:
            # Column doesn't exist yet, return all reviews (treat as trustworthy)
            pass
        # Order by specified field
        if order_by == 'created_at':
            query = query.order_by(
                Review.created_at.desc() if order_desc 
                else Review.created_at.asc()
            )
        elif order_by == 'rating':
            query = query.order_by(
                Review.rating.desc() if order_desc 
                else Review.rating.asc()
            )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def filter_by_suspicious_score(
        self,
        reviews: List[Review],
        max_suspicious_score: float = 0.7
    ) -> List[Review]:
        """
        Filter reviews by suspicious score threshold.
        
        Args:
            reviews (list): List of Review objects to filter
            max_suspicious_score (float): Maximum suspicious score allowed
            
        Returns:
            list: Filtered list of trustworthy reviews
        """
        return [
            review for review in reviews
            if review.suspicious_score is None or review.suspicious_score < max_suspicious_score
        ]

