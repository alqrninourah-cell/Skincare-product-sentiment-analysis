"""
Trend Analysis Service.

This service provides trend analysis functionality including
trending categories, concerns, and time-based trends.
"""

from typing import Dict, List
from datetime import datetime, timedelta
from models import db, Product, Review
from sqlalchemy import func
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class TrendService:
    """Service for trend analysis and reporting."""
    
    def get_trending_categories(self, time_period: str = 'month', limit: int = 10) -> List[Dict]:
        """
        Get trending product categories based on review volume and sentiment.
        
        Args:
            time_period (str): 'day', 'week', or 'month'
            limit (int): Number of top categories to return
            
        Returns:
            list: List of trending category dictionaries
        """
        try:
            # Calculate time threshold
            if time_period == 'day':
                threshold = datetime.utcnow() - timedelta(days=1)
            elif time_period == 'week':
                threshold = datetime.utcnow() - timedelta(weeks=1)
            else:  # month
                threshold = datetime.utcnow() - timedelta(days=30)
            
            # Get recent reviews
            recent_reviews = Review.query.filter(
                Review.created_at >= threshold
            ).all()
            
            if not recent_reviews:
                return []
            
            # Get products for these reviews
            product_ids = [r.product_id for r in recent_reviews]
            products = Product.query.filter(Product.id.in_(product_ids)).all()
            
            # Create product_id to category mapping
            product_category_map = {p.id: p.category for p in products if p.category}
            
            # Count reviews by category
            category_counts = Counter()
            category_sentiment = {}
            
            for review in recent_reviews:
                category = product_category_map.get(review.product_id)
                if category:
                    category_counts[category] += 1
                    
                    if category not in category_sentiment:
                        category_sentiment[category] = {'positive': 0, 'negative': 0, 'neutral': 0}
                    
                    sentiment = review.sentiment or 'neutral'
                    if sentiment in category_sentiment[category]:
                        category_sentiment[category][sentiment] += 1
            
            # Calculate trend scores (review count + positive sentiment weight)
            trending = []
            for category, count in category_counts.most_common(limit * 2):
                sentiment_data = category_sentiment.get(category, {})
                positive_count = sentiment_data.get('positive', 0)
                total_sentiment = sum(sentiment_data.values())
                
                # Trend score: review count + positive sentiment percentage
                positive_pct = (positive_count / total_sentiment * 100) if total_sentiment > 0 else 0
                trend_score = count + (positive_pct * 0.1)  # Weight sentiment slightly
                
                trending.append({
                    'category': category,
                    'review_count': count,
                    'positive_count': positive_count,
                    'negative_count': sentiment_data.get('negative', 0),
                    'neutral_count': sentiment_data.get('neutral', 0),
                    'positive_pct': round(positive_pct, 2),
                    'trend_score': round(trend_score, 2)
                })
            
            # Sort by trend score
            trending.sort(key=lambda x: x['trend_score'], reverse=True)
            
            return trending[:limit]
            
        except Exception as e:
            logger.error(f"Error getting trending categories: {e}")
            raise
    
    def get_trending_concerns(self, time_period: str = 'month', limit: int = 10) -> List[Dict]:
        """
        Get most common concerns mentioned in reviews.
        
        Args:
            time_period (str): 'day', 'week', or 'month'
            limit (int): Number of top concerns to return
            
        Returns:
            list: List of concern dictionaries
        """
        try:
            # Calculate time threshold
            if time_period == 'day':
                threshold = datetime.utcnow() - timedelta(days=1)
            elif time_period == 'week':
                threshold = datetime.utcnow() - timedelta(weeks=1)
            else:  # month
                threshold = datetime.utcnow() - timedelta(days=30)
            
            # Get recent reviews
            recent_reviews = Review.query.filter(
                Review.created_at >= threshold,
                Review.text.isnot(None)
            ).all()
            
            if not recent_reviews:
                return []
            
            # Common concern keywords
            concern_keywords = [
                'acne', 'breakout', 'irritation', 'dry', 'dryness', 'oily', 'oiliness',
                'redness', 'burning', 'stinging', 'allergic', 'rash', 'peeling',
                'sensitivity', 'texture', 'greasy', 'sticky', 'pilling',
                'doesn\'t work', 'not effective', 'waste', 'disappointed',
                'wrinkles', 'fine lines', 'dark spots', 'hyperpigmentation',
                'pores', 'blackheads', 'whiteheads', 'clogged pores'
            ]
            
            concern_counts = Counter()
            
            for review in recent_reviews:
                text_lower = review.text.lower()
                for keyword in concern_keywords:
                    if keyword in text_lower:
                        concern_counts[keyword] += 1
            
            # Return top concerns
            trending_concerns = [
                {
                    'concern': concern,
                    'frequency': count,
                    'percentage': round((count / len(recent_reviews) * 100), 2)
                }
                for concern, count in concern_counts.most_common(limit)
            ]
            
            return trending_concerns
            
        except Exception as e:
            logger.error(f"Error getting trending concerns: {e}")
            raise
    
    def generate_trend_report(self, brand_name: str, time_period: str = 'month') -> Dict:
        """
        Generate comprehensive trend report for a brand.
        
        Args:
            brand_name (str): Brand name
            time_period (str): 'day', 'week', or 'month'
            
        Returns:
            dict: Comprehensive trend report
        """
        try:
            from services.brand_analytics_service import BrandAnalyticsService
            
            brand_service = BrandAnalyticsService()
            
            # Get brand metrics
            sentiment_metrics = brand_service.get_brand_sentiment_metrics(brand_name)
            sentiment_trends = brand_service.get_sentiment_trends(brand_name, time_period)
            common_concerns = brand_service.get_common_concerns(brand_name)
            product_performance = brand_service.get_product_performance(brand_name)
            
            # Get overall trending categories and concerns
            trending_categories = self.get_trending_categories(time_period)
            trending_concerns = self.get_trending_concerns(time_period)
            
            return {
                'brand_name': brand_name,
                'time_period': time_period,
                'generated_at': datetime.utcnow().isoformat(),
                'sentiment_metrics': sentiment_metrics,
                'sentiment_trends': sentiment_trends,
                'common_concerns': common_concerns,
                'product_performance': product_performance[:10],  # Top 10 products
                'trending_categories': trending_categories,
                'trending_concerns': trending_concerns
            }
            
        except Exception as e:
            logger.error(f"Error generating trend report for {brand_name}: {e}")
            raise
    
    def get_trending_products(
        self,
        time_period: str = 'month',
        limit: int = 20,
        min_reviews: int = 5
    ) -> List[Dict]:
        """
        Get trending products based on review volume, positive sentiment, and recency.
        
        Args:
            time_period (str): 'day', 'week', or 'month'
            limit (int): Number of top products to return
            min_reviews (int): Minimum number of reviews required
            
        Returns:
            list: List of trending product dictionaries with metrics
        """
        try:
            # Calculate time threshold
            if time_period == 'day':
                threshold = datetime.utcnow() - timedelta(days=1)
            elif time_period == 'week':
                threshold = datetime.utcnow() - timedelta(weeks=1)
            else:  # month
                threshold = datetime.utcnow() - timedelta(days=30)
            
            # Get product statistics
            product_stats = db.session.query(
                Product.id,
                Product.name,
                Product.brand_name,
                Product.category,
                Product.image_url,
                func.count(Review.id).label('recent_review_count'),
                func.avg(Review.rating).label('avg_rating'),
                func.sum(func.case((Review.sentiment == 'positive', 1), else_=0)).label('positive_count')
            ).join(
                Review, Product.id == Review.product_id
            ).filter(
                Review.created_at >= threshold
            ).group_by(
                Product.id, Product.name, Product.brand_name, 
                Product.category, Product.image_url
            ).having(
                func.count(Review.id) >= min_reviews
            ).all()
            
            # Calculate trend scores
            trending = []
            for stat in product_stats:
                total_recent = stat.recent_review_count or 0
                positive_count = stat.positive_count or 0
                avg_rating = float(stat.avg_rating or 0)
                
                # Calculate positive sentiment percentage
                positive_pct = (positive_count / total_recent * 100) if total_recent > 0 else 0
                
                # Normalize rating (0-1 scale)
                rating_normalized = avg_rating / 5.0
                
                # Recency bonus (reviews in last 7 days)
                recent_week = datetime.utcnow() - timedelta(days=7)
                week_reviews = Review.query.filter(
                    Review.product_id == stat.id,
                    Review.created_at >= recent_week
                ).count()
                recency_bonus = min(1.0, week_reviews / 10.0)
                
                # Trend score: recent_review_count * 0.4 + positive_sentiment_pct * 0.3 + avg_rating_normalized * 0.2 + recency_bonus * 0.1
                trend_score = (
                    (min(total_recent, 100) / 100.0) * 0.4 +
                    (positive_pct / 100.0) * 0.3 +
                    rating_normalized * 0.2 +
                    recency_bonus * 0.1
                )
                
                trending.append({
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
            trending.sort(key=lambda x: x['trend_score'], reverse=True)
            
            return trending[:limit]
            
        except Exception as e:
            logger.error(f"Error getting trending products: {e}")
            raise
    
    def get_category_trends(self, category: str, time_period: str = 'month') -> Dict:
        """
        Get trends for a specific category.
        
        Args:
            category (str): Product category
            time_period (str): 'day', 'week', or 'month'
            
        Returns:
            dict: Category trend data
        """
        try:
            # Calculate time threshold
            if time_period == 'day':
                threshold = datetime.utcnow() - timedelta(days=1)
            elif time_period == 'week':
                threshold = datetime.utcnow() - timedelta(weeks=1)
            else:  # month
                threshold = datetime.utcnow() - timedelta(days=30)
            
            # Get products in category
            products = Product.query.filter(
                func.lower(Product.category) == category.lower()
            ).all()
            
            if not products:
                return {'category': category, 'trends': []}
            
            product_ids = [p.id for p in products]
            
            # Get recent reviews
            recent_reviews = Review.query.filter(
                Review.product_id.in_(product_ids),
                Review.created_at >= threshold
            ).all()
            
            # Calculate metrics
            total_reviews = len(recent_reviews)
            sentiment_counts = Counter(r.sentiment for r in recent_reviews if r.sentiment)
            
            ratings = [r.rating for r in recent_reviews if r.rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
            
            return {
                'category': category,
                'time_period': time_period,
                'total_reviews': total_reviews,
                'positive_count': sentiment_counts.get('positive', 0),
                'negative_count': sentiment_counts.get('negative', 0),
                'neutral_count': sentiment_counts.get('neutral', 0),
                'average_rating': round(avg_rating, 2),
                'products_count': len(products)
            }
            
        except Exception as e:
            logger.error(f"Error getting category trends for {category}: {e}")
            raise

