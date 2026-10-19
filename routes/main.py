"""
Main routes blueprint (Refactored).

This module contains route handlers that delegate business logic to services.
Routes are kept thin - they handle HTTP requests/responses and delegate to services.
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_required, current_user
from models import db, User, Product, Review
from services import SentimentService, RecommendationService, ReviewService
from services.influencer_service import InfluencerService
from utils.validators import validate_skin_type, validate_concerns, validate_review_text, validate_rating
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

# Initialize services
sentiment_service = SentimentService()
recommendation_service = RecommendationService(sentiment_service)
review_service = ReviewService(sentiment_service)
influencer_service = InfluencerService()


@main.route('/')
def index():
    """Home page route."""
    return render_template('index.html')


@main.route('/about')
def about():
    """About page route."""
    return render_template('about.html')


@main.route('/contact')
def contact():
    """Contact page route."""
    return render_template('contact.html')


@main.route('/recommend', methods=['POST'])
def recommend():
    """
    Get product recommendations based on skin type and concerns.
    
    Handles both authenticated and anonymous users.
    """
    skin_type = request.form.get('skin_type')
    concerns = request.form.get('concerns')
    
    # Validate inputs
    is_valid, error_message = validate_skin_type(skin_type)
    if not is_valid:
        flash(error_message or 'Please select your skin type.', 'error')
        return redirect(url_for('main.index'))
    
    is_valid, error_message = validate_concerns(concerns)
    if not is_valid:
        flash(error_message or 'Please provide at least 3 characters describing your skin concerns.', 'error')
        return redirect(url_for('main.index'))
    
    # Process user data
    try:
        user_id = None
        if current_user.is_authenticated:
            # Update logged-in user's preferences
            current_user.skin_type = skin_type.strip().lower()
            current_user.concerns = concerns.strip()
            db.session.commit()
            user_id = current_user.id
        else:
            # Save anonymous user input (optional - for tracking)
            user = User(skin_type=skin_type.strip().lower(), concerns=concerns.strip())
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            
    except Exception as e:
        logger.error(f"Error processing user data: {e}")
        db.session.rollback()
        flash('An error occurred while processing your request. Please try again.', 'error')
        return redirect(url_for('main.index'))
    
    # Get recommendations using service
    try:
        products = recommendation_service.get_recommendations(
            skin_type=skin_type.strip().lower(),
            concerns=concerns.strip(),
            user_id=user_id
        )
        
        # Limit to 12 products
        products = products[:9]
        
        # Store search in session history
        if 'search_history' not in session:
            session['search_history'] = []
        
        search_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'skin_type': skin_type,
            'concerns': concerns,
            'product_count': len(products)
        }
        
        session['search_history'].insert(0, search_entry)
        session['search_history'] = session['search_history'][:9]  # Keep last 9
        session.modified = True
        
        return render_template('results.html', products=products, skin_type=skin_type)
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        flash('An error occurred while generating recommendations. Please try again.', 'error')
        return redirect(url_for('main.index'))


@main.route('/history')
@login_required
def history():
    """Display user's search history."""
    search_history = session.get('search_history', [])
    return render_template('history.html', history=search_history)


@main.route('/history/clear', methods=['POST'])
@login_required
def clear_history():
    """Clear user's search history."""
    session['search_history'] = []
    session.modified = True
    flash('Search history cleared successfully.', 'success')
    return redirect(url_for('main.history'))


@main.route('/product/<int:product_id>')
def product_detail(product_id):
    """
    Display product details with reviews.
    
    Args:
        product_id (int): Product ID
    """
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get reviews using service
        reviews = review_service.get_reviews_for_product(product_id)
        
        # Get average rating using service
        avg_rating = review_service.get_average_rating(product_id)
        
        # Get sentiment distribution
        sentiment_dist = review_service.get_sentiment_distribution(product_id)
        
        # Get recommended skin types based on positive reviews
        recommended_skin_types = review_service.get_recommended_skin_types(product_id)
        
        return render_template(
            'product_detail.html',
            product=product,
            reviews=reviews,
            avg_rating=avg_rating,
            sentiment_dist=sentiment_dist,
            recommended_skin_types=recommended_skin_types
        )
        
    except Exception as e:
        logger.error(f"Error loading product detail: {e}")
        flash('Error loading product details. Please try again.', 'error')
        return redirect(url_for('main.index'))


@main.route('/products/<int:product_id>/insights')
def product_insights_public(product_id):
    """
    Public product insights page - accessible to everyone via shared links.
    Shows pros/cons, sentiment analysis, and trustworthy reviews.
    """
    try:
        product = Product.query.get_or_404(product_id)
        
        # Get source page from query parameter
        source = request.args.get('source', 'public')
        
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
            'product_insights_public.html',
            product=product,
            pros=insights.get('pros', []),
            cons=insights.get('cons', []),
            sentiment_distribution=sentiment_dist,
            avg_rating=avg_rating,
            trustworthy_reviews=trustworthy_reviews,
            recommended_skin_types=recommended_skin_types,
            skin_type_breakdown=skin_type_breakdown,
            source_page=source,
            is_public=True
        )
        
    except Exception as e:
        logger.error(f"Error loading public product insights for product {product_id}: {e}")
        flash('Error loading product insights. Please try again.', 'error')
        return redirect(url_for('main.index'))


@main.route('/submit_review/<int:product_id>', methods=['GET', 'POST'])
@login_required
def submit_review(product_id):
    """
    Submit a review for a product.
    
    Args:
        product_id (int): Product ID
    """
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        text = request.form.get('review_text')
        rating_str = request.form.get('rating')
        skin_type = request.form.get('skin_type')
        
        # Validate inputs
        is_valid, error_message = validate_review_text(text)
        if not is_valid:
            flash(error_message, 'error')
            return render_template('submit_review.html', product=product)
        
        try:
            rating = int(rating_str)
        except (ValueError, TypeError):
            flash('Invalid rating. Please select a rating between 1 and 5.', 'error')
            return render_template('submit_review.html', product=product)
        
        is_valid, error_message = validate_rating(rating)
        if not is_valid:
            flash(error_message, 'error')
            return render_template('submit_review.html', product=product)
        
        is_valid, error_message = validate_skin_type(skin_type)
        if not is_valid:
            flash(error_message, 'error')
            return render_template('submit_review.html', product=product)
        
        # Create review using service
        try:
            review = review_service.create_review(
                product_id=product_id,
                user_id=current_user.id,
                text=text,
                rating=rating,
                skin_type=skin_type.strip().lower()
            )
            
            flash('Your review has been submitted successfully!', 'success')
            return redirect(url_for('main.product_detail', product_id=product_id))
            
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('submit_review.html', product=product)
        except Exception as e:
            logger.error(f"Error creating review: {e}")
            db.session.rollback()
            flash('An error occurred while submitting your review. Please try again.', 'error')
            return render_template('submit_review.html', product=product)
    
    return render_template('submit_review.html', product=product)

