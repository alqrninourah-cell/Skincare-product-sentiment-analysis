"""
Brand Analytics Service.

This service provides analytics functionality for skincare brands,
including sentiment metrics, product performance, and trend analysis.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from models import db, Product, Review
from sqlalchemy import func, and_
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class BrandAnalyticsService:
    """Service for brand-level analytics and insights."""
    
    def get_brand_sentiment_metrics(self, brand_name: str) -> Dict:
        """
        Get overall sentiment metrics for a brand.
        
        Args:
            brand_name (str): Brand name
            
        Returns:
            dict: Sentiment metrics including:
                - total_reviews (int)
                - positive_count (int)
                - negative_count (int)
                - neutral_count (int)
                - positive_pct (float)
                - negative_pct (float)
                - neutral_pct (float)
                - average_rating (float)
        """
        try:
            # Get all products for the brand
            products = Product.query.filter(
                func.lower(Product.brand_name) == brand_name.lower()
            ).all()
            
            if not products:
                return {
                    'total_reviews': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0,
                    'positive_pct': 0.0,
                    'negative_pct': 0.0,
                    'neutral_pct': 0.0,
                    'average_rating': 0.0
                }
            
            product_ids = [p.id for p in products]
            
            # Get all reviews for brand products
            reviews = Review.query.filter(Review.product_id.in_(product_ids)).all()
            
            total_reviews = len(reviews)
            if total_reviews == 0:
                return {
                    'total_reviews': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'neutral_count': 0,
                    'positive_pct': 0.0,
                    'negative_pct': 0.0,
                    'neutral_pct': 0.0,
                    'average_rating': 0.0
                }
            
            # Count sentiment
            sentiment_counts = Counter(r.sentiment for r in reviews if r.sentiment)
            positive_count = sentiment_counts.get('positive', 0)
            negative_count = sentiment_counts.get('negative', 0)
            neutral_count = sentiment_counts.get('neutral', 0)
            
            # Calculate percentages
            positive_pct = (positive_count / total_reviews * 100) if total_reviews > 0 else 0
            negative_pct = (negative_count / total_reviews * 100) if total_reviews > 0 else 0
            neutral_pct = (neutral_count / total_reviews * 100) if total_reviews > 0 else 0
            
            # Calculate average rating
            ratings = [r.rating for r in reviews if r.rating]
            average_rating = sum(ratings) / len(ratings) if ratings else 0.0
            
            return {
                'total_reviews': total_reviews,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': neutral_count,
                'positive_pct': round(positive_pct, 2),
                'negative_pct': round(negative_pct, 2),
                'neutral_pct': round(neutral_pct, 2),
                'average_rating': round(average_rating, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting brand sentiment metrics for {brand_name}: {e}")
            raise
    
    def get_brand_products(self, brand_name: str) -> List[Product]:
        """
        Get all products for a brand.
        
        Args:
            brand_name (str): Brand name
            
        Returns:
            list: List of Product objects
        """
        try:
            products = Product.query.filter(
                func.lower(Product.brand_name) == brand_name.lower()
            ).all()
            return products
        except Exception as e:
            logger.error(f"Error getting products for brand {brand_name}: {e}")
            raise
    
    def get_sentiment_trends(self, brand_name: str, time_period: str = 'month') -> Dict:
        """
        Get sentiment trends over time for a brand.
        
        Args:
            brand_name (str): Brand name
            time_period (str): 'day', 'week', or 'month'
            
        Returns:
            dict: Trend data with time periods and sentiment counts
        """
        try:
            products = Product.query.filter(
                func.lower(Product.brand_name) == brand_name.lower()
            ).all()
            
            if not products:
                return {'trends': []}
            
            product_ids = [p.id for p in products]
            
            # Get reviews with timestamps
            reviews = Review.query.filter(
                Review.product_id.in_(product_ids),
                Review.created_at.isnot(None)
            ).order_by(Review.created_at).all()
            
            if not reviews:
                return {'trends': []}
            
            # Group by time period
            trends = {}
            for review in reviews:
                if not review.created_at:
                    continue
                
                # Format date based on time_period
                if time_period == 'day':
                    key = review.created_at.strftime('%Y-%m-%d')
                elif time_period == 'week':
                    # Get week start (Monday)
                    week_start = review.created_at - timedelta(days=review.created_at.weekday())
                    key = week_start.strftime('%Y-W%W')
                else:  # month
                    key = review.created_at.strftime('%Y-%m')
                
                if key not in trends:
                    trends[key] = {'positive': 0, 'negative': 0, 'neutral': 0}
                
                sentiment = review.sentiment or 'neutral'
                if sentiment in trends[key]:
                    trends[key][sentiment] += 1
            
            # Convert to list format
            trend_list = [
                {
                    'period': period,
                    'positive': data['positive'],
                    'negative': data['negative'],
                    'neutral': data['neutral'],
                    'total': sum(data.values())
                }
                for period, data in sorted(trends.items())
            ]
            
            return {'trends': trend_list}
            
        except Exception as e:
            logger.error(f"Error getting sentiment trends for {brand_name}: {e}")
            raise
    
    def get_common_concerns(self, brand_name: str, limit: int = 10) -> List[Dict]:
        """
        Extract most common concerns from negative reviews.
        
        Args:
            brand_name (str): Brand name
            limit (int): Number of top concerns to return
            
        Returns:
            list: List of concern dictionaries with text and frequency
        """
        try:
            products = Product.query.filter(
                func.lower(Product.brand_name) == brand_name.lower()
            ).all()
            
            if not products:
                return []
            
            product_ids = [p.id for p in products]
            
            # Get negative reviews
            negative_reviews = Review.query.filter(
                Review.product_id.in_(product_ids),
                Review.sentiment == 'negative',
                Review.text.isnot(None)
            ).all()
            
            # Extract keywords (simple approach - can be enhanced with NLP)
            concern_keywords = [
                'acne', 'breakout', 'irritation', 'dry', 'oily', 'redness',
                'burning', 'stinging', 'allergic', 'rash', 'peeling',
                'sensitivity', 'texture', 'greasy', 'sticky', 'pilling',
                'doesn\'t work', 'not effective', 'waste', 'disappointed'
            ]
            
            concern_counts = Counter()
            
            for review in negative_reviews:
                text_lower = review.text.lower()
                for keyword in concern_keywords:
                    if keyword in text_lower:
                        concern_counts[keyword] += 1
            
            # Return top concerns
            top_concerns = [
                {'concern': concern, 'frequency': count}
                for concern, count in concern_counts.most_common(limit)
            ]
            
            return top_concerns
            
        except Exception as e:
            logger.error(f"Error getting common concerns for {brand_name}: {e}")
            raise
    
    def get_product_performance(self, brand_name: str) -> List[Dict]:
        """
        Get performance metrics for all brand products.
        
        Args:
            brand_name (str): Brand name
            
        Returns:
            list: List of product performance dictionaries
        """
        try:
            products = Product.query.filter(
                func.lower(Product.brand_name) == brand_name.lower()
            ).all()
            
            if not products:
                return []
            
            performance_list = []
            
            for product in products:
                reviews = Review.query.filter_by(product_id=product.id).all()
                
                if not reviews:
                    continue
                
                # Calculate metrics
                total_reviews = len(reviews)
                sentiment_counts = Counter(r.sentiment for r in reviews if r.sentiment)
                positive_count = sentiment_counts.get('positive', 0)
                negative_count = sentiment_counts.get('negative', 0)
                neutral_count = sentiment_counts.get('neutral', 0)
                
                ratings = [r.rating for r in reviews if r.rating]
                avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
                
                positive_pct = (positive_count / total_reviews * 100) if total_reviews > 0 else 0
                
                performance_list.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'category': product.category,
                    'total_reviews': total_reviews,
                    'positive_count': positive_count,
                    'negative_count': negative_count,
                    'neutral_count': neutral_count,
                    'positive_pct': round(positive_pct, 2),
                    'average_rating': round(avg_rating, 2)
                })
            
            # Sort by positive percentage (descending)
            performance_list.sort(key=lambda x: x['positive_pct'], reverse=True)
            
            return performance_list
            
        except Exception as e:
            logger.error(f"Error getting product performance for {brand_name}: {e}")
            raise
    
    def get_negative_issues(self, brand_name: str, limit: int = 20) -> List[Dict]:
        """
        Get recurring negative issues from reviews.
        
        Args:
            brand_name (str): Brand name
            limit (int): Maximum number of issues to return
            
        Returns:
            list: List of negative issue dictionaries
        """
        try:
            products = Product.query.filter(
                func.lower(Product.brand_name) == brand_name.lower()
            ).all()
            
            if not products:
                return []
            
            product_ids = [p.id for p in products]
            
            # Get negative reviews
            negative_reviews = Review.query.filter(
                Review.product_id.in_(product_ids),
                Review.sentiment == 'negative',
                Review.text.isnot(None)
            ).order_by(Review.created_at.desc()).limit(limit * 5).all()  # Get more for variety
            
            issues = []
            
            for review in negative_reviews[:limit]:
                issues.append({
                    'review_id': review.id,
                    'product_id': review.product_id,
                    'product_name': Product.query.get(review.product_id).name if Product.query.get(review.product_id) else 'Unknown',
                    'review_text': review.text[:200] + '...' if len(review.text) > 200 else review.text,
                    'rating': review.rating,
                    'created_at': review.created_at.isoformat() if review.created_at else None
                })
            
            return issues
            
        except Exception as e:
            logger.error(f"Error getting negative issues for {brand_name}: {e}")
            raise

