"""
Admin routes for admin portal.

This module contains routes for admin users to manage the application,
including user management, product management, and system analytics.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Product, Review
from decorators import admin_required, role_required
from sqlalchemy import func
from sqlalchemy import desc
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

admin = Blueprint('admin', __name__, url_prefix='/admin')


@admin.route('/')
@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system overview."""
    try:
        # Get statistics
        total_users = User.query.count()
        total_products = Product.query.count()
        total_reviews = Review.query.count()
        
        # Get recent users (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = User.query.filter(User.created_at >= week_ago).count()
        
        # Get reviews by sentiment
        positive_reviews = Review.query.filter_by(sentiment='positive').count()
        negative_reviews = Review.query.filter_by(sentiment='negative').count()
        neutral_reviews = Review.query.filter_by(sentiment='neutral').count()
        
        # Get users by role
        admin_count = User.query.filter_by(role='admin').count()
        brand_count = User.query.filter_by(role='brand').count()
        user_count = User.query.filter_by(role='user').count()
        
        # Get recent reviews
        recent_reviews = Review.query.order_by(desc(Review.created_at)).limit(10).all()
        
        # Get top products by review count
        top_products = db.session.query(
            Product,
            func.count(Review.id).label('review_count')
        ).join(Review).group_by(Product.id).order_by(desc('review_count')).limit(10).all()
        
        return render_template(
            'admin/dashboard.html',
            total_users=total_users,
            total_products=total_products,
            total_reviews=total_reviews,
            recent_users=recent_users,
            positive_reviews=positive_reviews,
            negative_reviews=negative_reviews,
            neutral_reviews=neutral_reviews,
            admin_count=admin_count,
            brand_count=brand_count,
            user_count=user_count,
            recent_reviews=recent_reviews,
            top_products=top_products
        )
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('main.index'))


@admin.route('/users')
@login_required
@admin_required
def users():
    """User management page."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        search = request.args.get('search', '')
        role_filter = request.args.get('role', '')
        
        query = User.query
        
        # Apply search filter
        if search:
            query = query.filter(
                User.email.ilike(f'%{search}%')
            )
        
        # Apply role filter
        if role_filter:
            query = query.filter(User.role == role_filter)
        
        users = query.order_by(desc(User.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            'admin/users.html',
            users=users,
            search=search,
            role_filter=role_filter
        )
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        flash('An error occurred while loading users.', 'error')
        return redirect(url_for('admin.dashboard'))


@admin.route('/users/<int:user_id>/update-role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    """Update user role."""
    try:
        user = User.query.get_or_404(user_id)
        new_role = request.form.get('role')
        
        if new_role not in ['user', 'brand', 'admin']:
            flash('Invalid role specified.', 'error')
            return redirect(url_for('admin.users'))
        
        # Prevent removing last admin
        if user.role == 'admin' and new_role != 'admin':
            admin_count = User.query.filter_by(role='admin').count()
            if admin_count <= 1:
                flash('Cannot remove the last admin user.', 'error')
                return redirect(url_for('admin.users'))
        
        user.role = new_role
        db.session.commit()
        flash(f'User role updated to {new_role}.', 'success')
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        db.session.rollback()
        flash('An error occurred while updating user role.', 'error')
    
    return redirect(url_for('admin.users'))


@admin.route('/products')
@login_required
@admin_required
def products():
    """Product management page."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        search = request.args.get('search', '')
        
        query = Product.query
        
        if search:
            query = query.filter(
                Product.name.ilike(f'%{search}%') |
                Product.brand_name.ilike(f'%{search}%')
            )
        
        products = query.order_by(desc(Product.id)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            'admin/products.html',
            products=products,
            search=search
        )
    except Exception as e:
        logger.error(f"Error loading products: {e}")
        flash('An error occurred while loading products.', 'error')
        return redirect(url_for('admin.dashboard'))


@admin.route('/reviews')
@login_required
@admin_required
def reviews():
    """Review management page for admins."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        sentiment_filter = request.args.get('sentiment', '')
        
        query = Review.query
        
        if sentiment_filter:
            query = query.filter(Review.sentiment == sentiment_filter)
        
        reviews = query.order_by(desc(Review.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template(
            'admin/reviews.html',
            reviews=reviews,
            sentiment_filter=sentiment_filter
        )
    except Exception as e:
        logger.error(f"Error loading reviews: {e}")
        flash('An error occurred while loading reviews.', 'error')
        return redirect(url_for('admin.dashboard'))


@admin.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_review(review_id):
    """Delete a review."""
    try:
        review = Review.query.get_or_404(review_id)
        db.session.delete(review)
        db.session.commit()
        flash('Review deleted successfully.', 'success')
    except Exception as e:
        logger.error(f"Error deleting review: {e}")
        db.session.rollback()
        flash('An error occurred while deleting the review.', 'error')
    
    return redirect(url_for('admin.reviews'))

