"""
Influencer Service.

This service provides features specifically for beauty influencers including
trending products, highly recommended products, pros/cons insights, and filtering.

Note: Reviews are sourced from Sephora dataset. The fake review detection
service handles both dataset reviews (using original_author_id) and 
user-generated reviews (using user_id).
"""

from typing import List, Dict, Optional
from models import db, Product, Review
from datetime import datetime, timedelta
from sqlalchemy import func, desc, case
from .pros_cons_service import ProsConsService
from .fake_review_detection_service import FakeReviewDetectionService
import logging

logger = logging.getLogger(__name__)


class InfluencerService:
    """
    Service for influencer-specific features.
    
    Provides:
    - Trending products based on consumer sentiment
    - Highly recommended products
    - Product pros/cons insights
    - Filtering by customer profile (skin type)
    """
    
    def __init__(self):
        """Initialize influencer service."""
        self.pros_cons_service = ProsConsService()
        self.fake_review_service = FakeReviewDetectionService()
    
    def get_trending_products(
        self,
        time_period: str = 'month',
        limit: int = 20,
        skin_type: Optional[str] = None,
        min_reviews: int = 5
    ) -> List[Dict]:
        """
        Get trending products based on consumer sentiment.
        
        Args:
            time_period (str): 'day', 'week', or 'month'
            limit (int): Maximum number of products to return
            skin_type (str, optional): Filter by skin type
            min_reviews (int): Minimum number of reviews required
            
        Returns:
            list: List of product dictionaries with trending metrics
        """
        try:
            # Calculate time threshold
            if time_period == 'day':
                threshold = datetime.utcnow() - timedelta(days=1)
            elif time_period == 'week':
                threshold = datetime.utcnow() - timedelta(weeks=1)
            else:  # month
                threshold = datetime.utcnow() - timedelta(days=30)
            
            # Base query for recent reviews
            review_query = Review.query.filter(Review.created_at >= threshold)
            
            # Filter by skin type if provided
            if skin_type:
                review_query = review_query.filter(
                    func.lower(Review.skin_type) == skin_type.lower()
                )
            
            # Get product statistics
            product_stats = db.session.query(
                Product.id,
                Product.name,
                Product.brand_name,
                Product.category,
                Product.image_url,
                Product.rating,
                func.count(Review.id).label('recent_review_count'),
                func.avg(Review.rating).label('avg_rating'),
                func.sum(case((Review.sentiment == 'positive', 1), else_=0)).label('positive_count')
            ).join(
                Review, Product.id == Review.product_id
            ).filter(
                Review.created_at >= threshold
            )
            
            if skin_type:
                product_stats = product_stats.filter(
                    func.lower(Review.skin_type) == skin_type.lower()
                )
            
            product_stats = product_stats.group_by(
                Product.id, Product.name, Product.brand_name, 
                Product.category, Product.image_url, Product.rating
            ).having(
                func.count(Review.id) >= min_reviews
            ).all()
            
            # Calculate trend scores
            trending_products = []
            for stat in product_stats:
                total_recent = int(stat.recent_review_count or 0)
                positive_count = int(stat.positive_count or 0)
                avg_rating = float(stat.avg_rating or 0)
                
                # Calculate positive sentiment percentage
                positive_pct = (positive_count / total_recent * 100.0) if total_recent > 0 else 0.0
                
                # Normalize rating (0-1 scale)
                rating_normalized = avg_rating / 5.0
                
                # Recency bonus (reviews in last 7 days get bonus)
                recent_week = datetime.utcnow() - timedelta(days=7)
                week_reviews = Review.query.filter(
                    Review.product_id == stat.id,
                    Review.created_at >= recent_week
                ).count()
                recency_bonus = min(1.0, float(week_reviews) / 10.0)  # Max bonus at 10 reviews/week
                
                # Trend score calculation
                # recent_review_count * 0.4 + positive_sentiment_pct * 0.3 + avg_rating_normalized * 0.2 + recency_bonus * 0.1
                trend_score = (
                    (min(total_recent, 100) / 100.0) * 0.4 +  # Normalize review count
                    (positive_pct / 100.0) * 0.3 +
                    rating_normalized * 0.2 +
                    recency_bonus * 0.1
                )
                
                trending_products.append({
                    'product_id': stat.id,
                    'name': stat.name,
                    'brand_name': stat.brand_name,
                    'category': stat.category,
                    'image_url': stat.image_url,
                    'rating': round(avg_rating, 1),
                    'recent_review_count': total_recent,
                    'positive_count': positive_count,
                    'positive_percentage': round(positive_pct, 1),
                    'trend_score': round(trend_score, 3)
                })
            
            # Sort by trend score
            trending_products.sort(key=lambda x: x['trend_score'], reverse=True)
            
            return trending_products[:limit]
            
        except Exception as e:
            logger.error(f"Error getting trending products: {e}")
            raise
    
    def get_highly_recommended_products(
        self,
        skin_type: Optional[str] = None,
        limit: int = 20,
        min_reviews: int = 10,
        min_positive_pct: float = 70.0
    ) -> List[Dict]:
        """
        Get highly recommended products (high positive sentiment, high ratings).
        
        Args:
            skin_type (str, optional): Filter by skin type
            limit (int): Maximum number of products to return
            min_reviews (int): Minimum number of reviews required
            min_positive_pct (float): Minimum positive sentiment percentage
            
        Returns:
            list: List of highly recommended products
        """
        try:
            # Base query
            query = db.session.query(
                Product.id,
                Product.name,
                Product.brand_name,
                Product.category,
                Product.image_url,
                Product.rating,
                func.count(Review.id).label('total_reviews'),
                func.avg(Review.rating).label('avg_rating'),
                func.sum(case((Review.sentiment == 'positive', 1), else_=0)).label('positive_count')
            ).join(
                Review, Product.id == Review.product_id
            )
            
            # Filter by skin type if provided
            if skin_type:
                query = query.filter(
                    func.lower(Review.skin_type) == skin_type.lower()
                )
            
            # Group and filter
            results = query.group_by(
                Product.id, Product.name, Product.brand_name,
                Product.category, Product.image_url, Product.rating
            ).having(
                func.count(Review.id) >= min_reviews
            ).all()
            
            recommended = []
            for result in results:
                total = int(result.total_reviews or 0)
                positive_count = int(result.positive_count or 0)
                positive_pct = (positive_count / total * 100.0) if total > 0 else 0.0
                avg_rating = float(result.avg_rating or 0)
                
                # Filter by minimum positive percentage
                if positive_pct < min_positive_pct:
                    continue
                
                # Recommendation score (weighted combination)
                recommendation_score = (
                    (positive_pct / 100.0) * 0.5 +  # Positive sentiment weight
                    (avg_rating / 5.0) * 0.3 +     # Rating weight
                    (min(total, 100) / 100.0) * 0.2  # Review count weight (normalized)
                )
                
                recommended.append({
                    'product_id': result.id,
                    'name': result.name,
                    'brand_name': result.brand_name,
                    'category': result.category,
                    'image_url': result.image_url,
                    'rating': round(avg_rating, 1),
                    'total_reviews': total,
                    'positive_count': positive_count,
                    'positive_percentage': round(positive_pct, 1),
                    'recommendation_score': round(recommendation_score, 3)
                })
            
            # Sort by recommendation score
            recommended.sort(key=lambda x: x['recommendation_score'], reverse=True)
            
            return recommended[:limit]
            
        except Exception as e:
            logger.error(f"Error getting highly recommended products: {e}")
            raise
    
    def get_product_pros_cons(self, product_id: int, limit: int = 10) -> Dict:
        """
        Get pros and cons for a product.
        
        Args:
            product_id (int): Product ID
            limit (int): Maximum number of pros/cons to return
            
        Returns:
            dict: Dictionary with 'pros' and 'cons' lists
        """
        return self.pros_cons_service.get_product_insights(product_id, limit)
    
    def filter_by_customer_profile(
        self,
        products: List[Product],
        skin_type: Optional[str] = None,
        min_rating: Optional[float] = None,
        min_positive_pct: Optional[float] = None
    ) -> List[Product]:
        """
        Filter products by customer profile attributes.
        
        Args:
            products (list): List of Product objects to filter
            skin_type (str, optional): Filter by skin type
            min_rating (float, optional): Minimum average rating
            min_positive_pct (float, optional): Minimum positive sentiment percentage
            
        Returns:
            list: Filtered list of products
        """
        try:
            filtered = []
            
            for product in products:
                # Get reviews for this product
                review_query = Review.query.filter_by(product_id=product.id)
                
                # Filter by skin type
                if skin_type:
                    review_query = review_query.filter(
                        func.lower(Review.skin_type) == skin_type.lower()
                    )
                
                reviews = review_query.all()
                
                if not reviews:
                    continue
                
                # Check minimum rating
                if min_rating:
                    rating_list = [float(r.rating) for r in reviews if r.rating]
                    avg_rating = sum(rating_list) / len(rating_list) if rating_list else 0.0
                    if avg_rating < min_rating:
                        continue
                
                # Check minimum positive percentage
                if min_positive_pct:
                    positive_count = sum(1 for r in reviews if r.sentiment == 'positive')
                    positive_pct = (positive_count / len(reviews)) * 100.0 if reviews else 0.0
                    if positive_pct < min_positive_pct:
                        continue
                
                filtered.append(product)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering by customer profile: {e}")
            raise
    
    def get_trustworthy_reviews(
        self,
        product_id: int,
        threshold: float = 0.7,
        limit: Optional[int] = None
    ) -> List[Review]:
        """
        Get trustworthy reviews (filtered by suspicious score).
        
        Args:
            product_id (int): Product ID
            threshold (float): Maximum suspicious score (default: 0.7)
            limit (int, optional): Maximum number of reviews to return
            
        Returns:
            list: List of trustworthy Review objects
        """
        try:
            query = Review.query.filter_by(product_id=product_id)
            # Check if suspicious_score column exists before filtering
            try:
                query = query.filter(Review.suspicious_score < threshold)
            except Exception:
                # Column doesn't exist yet, return all reviews
                logger.warning("suspicious_score column not found, returning all reviews")
            query = query.order_by(desc(Review.created_at))
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error getting trustworthy reviews for product {product_id}: {e}")
            raise

