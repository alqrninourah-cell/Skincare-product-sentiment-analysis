"""
Influencer routes for beauty influencer portal.

This module contains routes for influencer users to discover trending products,
analyze consumer sentiment, view pros/cons, and access highly recommended products.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Product, Review
from decorators import influencer_required
from services import InfluencerService, ReviewService
from services.fake_review_detection_service import FakeReviewDetectionService
import logging

logger = logging.getLogger(__name__)

influencer = Blueprint('influencer', __name__, url_prefix='/influencer')

# Initialize services
influencer_service = InfluencerService()
review_service = ReviewService()
fake_review_service = FakeReviewDetectionService()


@influencer.route('/')
@influencer.route('/dashboard')
@login_required
@influencer_required
def dashboard():
    """Influencer dashboard with overview of trending products and stats."""
    try:
        # Get trending products (last month)
        try:
            trending = influencer_service.get_trending_products(
                time_period='month',
                limit=6
            )
        except Exception as e:
            logger.warning(f"Error getting trending products: {e}")
            trending = []
        
        # Get highly recommended products
        try:
            recommended = influencer_service.get_highly_recommended_products(
                limit=6
            )
        except Exception as e:
            logger.warning(f"Error getting recommended products: {e}")
            recommended = []
        
        # Get stats
        try:
            total_products = Product.query.count()
            total_reviews = Review.query.count()
            
            # Handle suspicious_score query - may not exist in database yet
            try:
                trustworthy_reviews = Review.query.filter(Review.suspicious_score < 0.7).count()
            except Exception as e:
                # If suspicious_score column doesn't exist, treat all reviews as trustworthy for now
                logger.warning(f"suspicious_score column may not exist: {e}. Treating all reviews as trustworthy.")
                trustworthy_reviews = total_reviews
            
            stats = {
                'total_products': total_products,
                'total_reviews': total_reviews,
                'trustworthy_reviews': trustworthy_reviews,
                'trustworthy_percentage': round((trustworthy_reviews / total_reviews * 100) if total_reviews > 0 else 0, 1)
            }
        except Exception as e:
            logger.warning(f"Error getting stats: {e}")
            stats = {
                'total_products': 0,
                'total_reviews': 0,
                'trustworthy_reviews': 0,
                'trustworthy_percentage': 0
            }
        
        return render_template(
            'influencer/dashboard.html',
            trending_products=trending or [],
            recommended_products=recommended or [],
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error loading influencer dashboard: {e}", exc_info=True)
        flash(f'An error occurred while loading the dashboard: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@influencer.route('/trending')
@login_required
@influencer_required
def trending():
    """Trending products page with filters."""
    try:
        # Get filter parameters
        time_period = request.args.get('time_period', 'month')
        skin_type = request.args.get('skin_type', '')
        limit = int(request.args.get('limit', 20))
        
        # Validate time period
        if time_period not in ['day', 'week', 'month']:
            time_period = 'month'
        
        # Get trending products
        trending_products = influencer_service.get_trending_products(
            time_period=time_period,
            skin_type=skin_type if skin_type else None,
            limit=limit
        )
        
        return render_template(
            'influencer/trending.html',
            trending_products=trending_products,
            time_period=time_period,
            skin_type=skin_type,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error loading trending products: {e}")
        flash('An error occurred while loading trending products.', 'error')
        return redirect(url_for('influencer.dashboard'))


@influencer.route('/products/<int:product_id>/insights')
@login_required
@influencer_required
def product_insights(product_id):
    """Detailed product insights page with pros/cons and trustworthy reviews."""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get source page from query parameter or referrer
        source = request.args.get('source', '')
        if not source:
            # Try to determine from referrer
            referrer = request.referrer or ''
            if 'trending' in referrer:
                source = 'trending'
            elif 'recommended' in referrer:
                source = 'recommended'
            elif 'filter' in referrer:
                source = 'filter'
            elif 'dashboard' in referrer or referrer.endswith('/influencer'):
                source = 'dashboard'
        
        # Get pros and cons
        insights = influencer_service.get_product_pros_cons(product_id, limit=10)
        
        # Get trustworthy reviews only
        trustworthy_reviews = influencer_service.get_trustworthy_reviews(
            product_id=product_id,
            threshold=0.7,
            limit=20
        )
        
        # Get sentiment distribution
        sentiment_dist = review_service.get_sentiment_distribution(product_id)
        
        # Get average rating
        avg_rating = review_service.get_average_rating(product_id)
        
        # Get recommended skin types
        recommended_skin_types = review_service.get_recommended_skin_types(product_id)
        
        # Get skin type breakdown
        skin_type_breakdown = {}
        all_reviews = Review.query.filter_by(product_id=product_id).all()
        for review in all_reviews:
            if review.skin_type:
                skin_type = review.skin_type.lower()
                if skin_type not in skin_type_breakdown:
                    skin_type_breakdown[skin_type] = {
                        'total': 0,
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0
                    }
                skin_type_breakdown[skin_type]['total'] += 1
                if review.sentiment:
                    skin_type_breakdown[skin_type][review.sentiment] = \
                        skin_type_breakdown[skin_type].get(review.sentiment, 0) + 1
        
        return render_template(
            'influencer/product_insights.html',
            product=product,
            pros=insights.get('pros', []),
            cons=insights.get('cons', []),
            sentiment_distribution=sentiment_dist,
            avg_rating=avg_rating,
            trustworthy_reviews=trustworthy_reviews,
            recommended_skin_types=recommended_skin_types,
            skin_type_breakdown=skin_type_breakdown,
            source_page=source
        )
        
    except Exception as e:
        logger.error(f"Error loading product insights for product {product_id}: {e}")
        flash('Error loading product insights. Please try again.', 'error')
        return redirect(url_for('influencer.dashboard'))


@influencer.route('/recommended')
@login_required
@influencer_required
def recommended():
    """Highly recommended products list."""
    try:
        # Get filter parameters
        skin_type = request.args.get('skin_type', '')
        limit = int(request.args.get('limit', 20))
        
        # Get highly recommended products
        recommended_products = influencer_service.get_highly_recommended_products(
            skin_type=skin_type if skin_type else None,
            limit=limit
        )
        
        return render_template(
            'influencer/recommended.html',
            recommended_products=recommended_products,
            skin_type=skin_type,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error loading recommended products: {e}")
        flash('An error occurred while loading recommended products.', 'error')
        return redirect(url_for('influencer.dashboard'))


@influencer.route('/filter')
@login_required
@influencer_required
def filter_products():
    """Filter products by customer profile."""
    try:
        # Get filter parameters
        skin_type = request.args.get('skin_type', '')
        min_rating = request.args.get('min_rating', type=float)
        min_positive_pct = request.args.get('min_positive_pct', type=float)
        
        # Get all products
        all_products = Product.query.all()
        
        # Filter by customer profile
        filtered_products = influencer_service.filter_by_customer_profile(
            products=all_products,
            skin_type=skin_type if skin_type else None,
            min_rating=min_rating,
            min_positive_pct=min_positive_pct
        )
        
        # Get additional info for each product
        products_with_info = []
        for product in filtered_products[:50]:  # Limit to 50 for performance
            reviews = Review.query.filter_by(product_id=product.id).all()
            total_reviews = len(reviews)
            positive_count = sum(1 for r in reviews if r.sentiment == 'positive')
            positive_pct = (positive_count / total_reviews * 100) if total_reviews > 0 else 0
            avg_rating = sum(r.rating for r in reviews if r.rating) / len([r for r in reviews if r.rating]) if reviews else 0
            
            products_with_info.append({
                'product': product,
                'total_reviews': total_reviews,
                'positive_percentage': round(positive_pct, 1),
                'average_rating': round(avg_rating, 1)
            })
        
        return render_template(
            'influencer/filter.html',
            products=products_with_info,
            skin_type=skin_type,
            min_rating=min_rating,
            min_positive_pct=min_positive_pct
        )
        
    except Exception as e:
        logger.error(f"Error filtering products: {e}")
        flash('An error occurred while filtering products.', 'error')
        return redirect(url_for('influencer.dashboard'))

