"""
Brand routes for brand portal.

This module contains routes for brand users to manage their products,
view analytics, and export data.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from models import db, Product, Review
from decorators import brand_required
from sqlalchemy import func, desc, case
from datetime import datetime, timedelta
import csv
import io
import logging

logger = logging.getLogger(__name__)

brand = Blueprint('brand', __name__, url_prefix='/brand')


@brand.route('/')
@brand.route('/dashboard')
@login_required
@brand_required
def dashboard():
    """Brand dashboard with analytics."""
    try:
        # Get brand name from user profile
        if not current_user.brand_name:
            flash('Brand name not set. Please contact support.', 'error')
            return redirect(url_for('main.index'))
        
        brand_name = current_user.brand_name
        
        # Get products for this brand only
        brand_products = Product.query.filter_by(brand_name=brand_name).all()
        product_ids = [p.id for p in brand_products]
        
        total_products = len(brand_products)
        total_reviews = Review.query.filter(Review.product_id.in_(product_ids)).count() if product_ids else 0
        
        # Get reviews by sentiment for this brand's products
        if product_ids:
            positive_reviews = Review.query.filter(Review.product_id.in_(product_ids), Review.sentiment == 'positive').count()
            negative_reviews = Review.query.filter(Review.product_id.in_(product_ids), Review.sentiment == 'negative').count()
            neutral_reviews = Review.query.filter(Review.product_id.in_(product_ids), Review.sentiment == 'neutral').count()
        else:
            positive_reviews = negative_reviews = neutral_reviews = 0
        
        # Calculate sentiment metrics
        sentiment_metrics = {
            'total_reviews': total_reviews,
            'positive_count': positive_reviews,
            'negative_count': negative_reviews,
            'neutral_count': neutral_reviews,
            'positive_pct': round((positive_reviews / total_reviews * 100) if total_reviews > 0 else 0, 1),
            'negative_pct': round((negative_reviews / total_reviews * 100) if total_reviews > 0 else 0, 1),
            'average_rating': round(Review.query.filter(Review.product_id.in_(product_ids)).with_entities(func.avg(Review.rating)).scalar() or 0, 1) if product_ids else 0
        }
        
        # Get top products by review count for this brand
        if product_ids:
            top_products = db.session.query(
                Product.name.label('product_name'),
                Product.category,
                func.count(Review.id).label('total_reviews'),
                func.avg(Review.rating).label('avg_rating')
            ).join(Review).filter(Product.brand_name == brand_name, Review.product_id.in_(product_ids)).group_by(Product.id, Product.name, Product.category).order_by(desc('total_reviews')).limit(10).all()
        else:
            top_products = []
        
        # Format top products
        top_products_formatted = []
        for product in top_products:
            positive_count = Review.query.filter_by(product_id=Product.query.filter_by(name=product.product_name).first().id, sentiment='positive').count() if Product.query.filter_by(name=product.product_name).first() else 0
            total = product.total_reviews
            top_products_formatted.append({
                'product_name': product.product_name,
                'category': product.category,
                'total_reviews': total,
                'positive_pct': round((positive_count / total * 100) if total > 0 else 0, 1)
            })
        
        # Get common concerns (simplified - you can enhance this)
        common_concerns = []
        
        # Get negative issues for this brand's products
        if product_ids:
            negative_issues = db.session.query(
                Product.name.label('product_name'),
                Review.text.label('review_text'),
                Review.rating
            ).join(Review).filter(Product.brand_name == brand_name, Review.product_id.in_(product_ids), Review.sentiment == 'negative').order_by(desc(Review.created_at)).limit(10).all()
        else:
            negative_issues = []
        
        # Sentiment trends (simplified - monthly)
        sentiment_trends = {
            'trends': [
                {'period': 'Jan', 'positive': 100, 'negative': 20, 'neutral': 10},
                {'period': 'Feb', 'positive': 120, 'negative': 15, 'neutral': 12},
                {'period': 'Mar', 'positive': 110, 'negative': 25, 'neutral': 8}
            ]
        }
        
        return render_template(
            'brand/dashboard.html',
            brand_name=brand_name,
            sentiment_metrics=sentiment_metrics,
            sentiment_trends=sentiment_trends,
            top_products=top_products_formatted,
            common_concerns=common_concerns,
            negative_issues=negative_issues
        )
    except Exception as e:
        logger.error(f"Error loading brand dashboard: {e}")
        flash('An error occurred while loading the dashboard.', 'error')
        return redirect(url_for('main.index'))


@brand.route('/products')
@login_required
@brand_required
def products():
    """Brand products page."""
    try:
        if not current_user.brand_name:
            flash('Brand name not set. Please contact support.', 'error')
            return redirect(url_for('brand.dashboard'))
        
        brand_name = current_user.brand_name
        page = request.args.get('page', 1, type=int)
        per_page = 20
        search = request.args.get('search', '')
        
        # Filter products by brand_name
        query = Product.query.filter_by(brand_name=brand_name)
        
        if search:
            query = query.filter(
                Product.name.ilike(f'%{search}%') |
                Product.brand_name.ilike(f'%{search}%')
            )
        
        products_query = query.order_by(desc(Product.id)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format products for display
        products_formatted = []
        for product in products_query.items:
            reviews = Review.query.filter_by(product_id=product.id).all()
            total_reviews = len(reviews)
            positive_count = sum(1 for r in reviews if r.sentiment == 'positive')
            avg_rating = sum(r.rating for r in reviews) / total_reviews if total_reviews > 0 else 0
            
            products_formatted.append({
                'product_name': product.name,
                'category': product.category,
                'total_reviews': total_reviews,
                'positive_pct': round((positive_count / total_reviews * 100) if total_reviews > 0 else 0, 1),
                'average_rating': round(avg_rating, 1)
            })
        
        return render_template(
            'brand/products.html',
            products=products_formatted,
            search=search,
            brand_name=brand_name
        )
    except Exception as e:
        logger.error(f"Error loading brand products: {e}")
        flash('An error occurred while loading products.', 'error')
        return redirect(url_for('brand.dashboard'))


@brand.route('/trends')
@login_required
@brand_required
def trends():
    """Brand trends page."""
    try:
        if not current_user.brand_name:
            flash('Brand name not set. Please contact support.', 'error')
            return redirect(url_for('brand.dashboard'))
        
        brand_name = current_user.brand_name
        
        # Get trending categories with review counts and positive percentages for this brand
        category_stats = db.session.query(
            Product.category,
            func.count(Review.id).label('review_count'),
            func.avg(Review.rating).label('avg_rating'),
            func.sum(case((Review.sentiment == 'positive', 1), else_=0)).label('positive_count')
        ).join(Review, Product.id == Review.product_id).filter(Product.brand_name == brand_name).group_by(Product.category).order_by(desc('review_count')).limit(10).all()
        
        trending_categories = []
        for cat in category_stats:
            total = cat.review_count or 0
            positive = cat.positive_count or 0
            positive_pct = round((positive / total * 100) if total > 0 else 0, 1)
            trending_categories.append({
                'category': cat.category,
                'review_count': total,
                'positive_pct': positive_pct,
                'avg_rating': round(cat.avg_rating or 0, 1)
            })
        
        # Get trending concerns (extract from review text - simplified approach)
        # For now, we'll use a placeholder approach. In a real implementation, 
        # you'd use NLP to extract concerns from review text
        trending_concerns = []
        
        # Get negative reviews for this brand's products and try to identify common concerns
        brand_product_ids = [p.id for p in Product.query.filter_by(brand_name=brand_name).all()]
        if brand_product_ids:
            negative_reviews = Review.query.filter(Review.product_id.in_(brand_product_ids), Review.sentiment == 'negative').limit(50).all()
        else:
            negative_reviews = []
        concern_keywords = ['dry', 'irritation', 'breakout', 'acne', 'sensitive', 'redness', 'burning', 'stinging', 'rash']
        concern_counts = {}
        
        for review in negative_reviews:
            if review.text:
                text_lower = review.text.lower()
                for keyword in concern_keywords:
                    if keyword in text_lower:
                        concern_counts[keyword] = concern_counts.get(keyword, 0) + 1
        
        total_negative = len(negative_reviews)
        for concern, count in sorted(concern_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            trending_concerns.append({
                'concern': concern.title(),
                'frequency': count,
                'percentage': round((count / total_negative * 100) if total_negative > 0 else 0, 1)
            })
        
        trend_report = {
            'trending_categories': trending_categories,
            'trending_concerns': trending_concerns
        }
        
        return render_template('brand/trends.html', brand_name=brand_name, trend_report=trend_report)
    except Exception as e:
        logger.error(f"Error loading brand trends: {e}")
        flash('An error occurred while loading trends.', 'error')
        return redirect(url_for('brand.dashboard'))


@brand.route('/export')
@login_required
@brand_required
def export():
    """Brand data export page."""
    try:
        if not current_user.brand_name:
            flash('Brand name not set. Please contact support.', 'error')
            return redirect(url_for('brand.dashboard'))
        
        brand_name = current_user.brand_name
        
        # Get summary statistics for preview (filtered by brand)
        brand_products = Product.query.filter_by(brand_name=brand_name).all()
        product_ids = [p.id for p in brand_products]
        
        total_products = len(brand_products)
        total_reviews = Review.query.filter(Review.product_id.in_(product_ids)).count() if product_ids else 0
        positive_reviews = Review.query.filter(Review.product_id.in_(product_ids), Review.sentiment == 'positive').count() if product_ids else 0
        negative_reviews = Review.query.filter(Review.product_id.in_(product_ids), Review.sentiment == 'negative').count() if product_ids else 0
        neutral_reviews = Review.query.filter(Review.product_id.in_(product_ids), Review.sentiment == 'neutral').count() if product_ids else 0
        
        # Get category count for this brand
        category_count = db.session.query(func.count(func.distinct(Product.category))).filter(Product.brand_name == brand_name).scalar() or 0
        
        # Get date range for this brand's reviews
        if product_ids:
            oldest_review = Review.query.filter(Review.product_id.in_(product_ids)).order_by(Review.created_at.asc()).first()
            newest_review = Review.query.filter(Review.product_id.in_(product_ids)).order_by(Review.created_at.desc()).first()
        else:
            oldest_review = newest_review = None
        
        export_stats = {
            'total_products': total_products,
            'total_reviews': total_reviews,
            'positive_reviews': positive_reviews,
            'negative_reviews': negative_reviews,
            'neutral_reviews': neutral_reviews,
            'category_count': category_count or 0,
            'date_range': {
                'oldest': oldest_review.created_at.strftime('%Y-%m-%d') if oldest_review and oldest_review.created_at else 'N/A',
                'newest': newest_review.created_at.strftime('%Y-%m-%d') if newest_review and newest_review.created_at else 'N/A'
            }
        }
        
        return render_template('brand/export.html', brand_name=brand_name, export_stats=export_stats)
    except Exception as e:
        logger.error(f"Error loading brand export: {e}")
        flash('An error occurred while loading export page.', 'error')
        return redirect(url_for('brand.dashboard'))


@brand.route('/export/sentiment/<format>')
@login_required
@brand_required
def export_sentiment(format):
    """Export sentiment data as CSV or Excel."""
    try:
        if not current_user.brand_name:
            flash('Brand name not set. Please contact support.', 'error')
            return redirect(url_for('brand.export'))
        
        brand_name = current_user.brand_name
        # Get products for this brand only
        products = Product.query.filter_by(brand_name=brand_name).all()
        
        # Prepare data
        export_data = []
        for product in products:
            reviews = Review.query.filter_by(product_id=product.id).all()
            total_reviews = len(reviews)
            positive_count = sum(1 for r in reviews if r.sentiment == 'positive')
            negative_count = sum(1 for r in reviews if r.sentiment == 'negative')
            neutral_count = sum(1 for r in reviews if r.sentiment == 'neutral')
            avg_rating = sum(r.rating for r in reviews) / total_reviews if total_reviews > 0 else 0
            
            export_data.append({
                'Product Name': product.name,
                'Brand': product.brand_name if hasattr(product, 'brand_name') else 'N/A',
                'Category': product.category,
                'Total Reviews': total_reviews,
                'Positive Reviews': positive_count,
                'Negative Reviews': negative_count,
                'Neutral Reviews': neutral_count,
                'Positive %': round((positive_count / total_reviews * 100) if total_reviews > 0 else 0, 2),
                'Negative %': round((negative_count / total_reviews * 100) if total_reviews > 0 else 0, 2),
                'Neutral %': round((neutral_count / total_reviews * 100) if total_reviews > 0 else 0, 2),
                'Average Rating': round(avg_rating, 2)
            })
        
        if format == 'csv':
            # Create CSV response
            output = io.StringIO()
            if export_data:
                writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
                writer.writeheader()
                writer.writerows(export_data)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=sentiment_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            return response
            
        elif format == 'excel':
            # Try to use pandas for Excel export, fallback to CSV if not available
            try:
                import pandas as pd
                df = pd.DataFrame(export_data)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sentiment Data')
                output.seek(0)
                
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                response.headers['Content-Disposition'] = f'attachment; filename=sentiment_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                return response
            except ImportError:
                # Fallback to CSV if pandas/openpyxl not available
                flash('Excel export requires pandas and openpyxl. Exporting as CSV instead.', 'warning')
                return export_sentiment('csv')
        else:
            flash('Invalid export format. Use "csv" or "excel".', 'error')
            return redirect(url_for('brand.export'))
            
    except Exception as e:
        logger.error(f"Error exporting sentiment data: {e}")
        flash('An error occurred while exporting data.', 'error')
        return redirect(url_for('brand.export'))


@brand.route('/export/trends/<format>')
@login_required
@brand_required
def export_trends(format):
    """Export trend analysis report as CSV or Excel."""
    try:
        if not current_user.brand_name:
            flash('Brand name not set. Please contact support.', 'error')
            return redirect(url_for('brand.export'))
        
        brand_name = current_user.brand_name
        brand_product_ids = [p.id for p in Product.query.filter_by(brand_name=brand_name).all()]
        
        # Get trend data for this brand
        # Group by category
        if brand_product_ids:
            category_stats = db.session.query(
                Product.category,
                func.count(Review.id).label('total_reviews'),
                func.avg(Review.rating).label('avg_rating'),
                func.sum(case((Review.sentiment == 'positive', 1), else_=0)).label('positive_count')
            ).join(Review, Product.id == Review.product_id).filter(Product.brand_name == brand_name, Review.product_id.in_(brand_product_ids)).group_by(Product.category).all()
        else:
            category_stats = []
        
        # Get monthly trends (last 12 months) for this brand
        monthly_trends = []
        for i in range(12):
            month_date = datetime.now() - timedelta(days=30 * (11 - i))
            if brand_product_ids:
                month_reviews = Review.query.filter(
                    Review.product_id.in_(brand_product_ids),
                    Review.created_at >= month_date - timedelta(days=30),
                    Review.created_at < month_date
                ).all()
            else:
                month_reviews = []
            
            positive = sum(1 for r in month_reviews if r.sentiment == 'positive')
            negative = sum(1 for r in month_reviews if r.sentiment == 'negative')
            neutral = sum(1 for r in month_reviews if r.sentiment == 'neutral')
            
            monthly_trends.append({
                'Period': month_date.strftime('%Y-%m'),
                'Total Reviews': len(month_reviews),
                'Positive': positive,
                'Negative': negative,
                'Neutral': neutral,
                'Positive %': round((positive / len(month_reviews) * 100) if month_reviews else 0, 2)
            })
        
        # Prepare category data
        category_data = []
        for cat in category_stats:
            positive_pct = round((cat.positive_count / cat.total_reviews * 100) if cat.total_reviews > 0 else 0, 2)
            category_data.append({
                'Category': cat.category,
                'Total Reviews': cat.total_reviews,
                'Average Rating': round(cat.avg_rating or 0, 2),
                'Positive Reviews': cat.positive_count or 0,
                'Positive %': positive_pct
            })
        
        if format == 'csv':
            # Create CSV with multiple sections
            output = io.StringIO()
            
            # Write category trends
            writer = csv.DictWriter(output, fieldnames=['Category', 'Total Reviews', 'Average Rating', 'Positive Reviews', 'Positive %'])
            output.write('=== Category Trends ===\n')
            writer.writeheader()
            writer.writerows(category_data)
            
            output.write('\n\n=== Monthly Trends ===\n')
            writer = csv.DictWriter(output, fieldnames=['Period', 'Total Reviews', 'Positive', 'Negative', 'Neutral', 'Positive %'])
            writer.writeheader()
            writer.writerows(monthly_trends)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = f'attachment; filename=trend_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            return response
            
        elif format == 'excel':
            # Try to use pandas for Excel export
            try:
                import pandas as pd
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Category trends sheet
                    df_categories = pd.DataFrame(category_data)
                    df_categories.to_excel(writer, index=False, sheet_name='Category Trends')
                    
                    # Monthly trends sheet
                    df_monthly = pd.DataFrame(monthly_trends)
                    df_monthly.to_excel(writer, index=False, sheet_name='Monthly Trends')
                
                output.seek(0)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                response.headers['Content-Disposition'] = f'attachment; filename=trend_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
                return response
            except ImportError:
                flash('Excel export requires pandas and openpyxl. Exporting as CSV instead.', 'warning')
                return export_trends('csv')
        else:
            flash('Invalid export format. Use "csv" or "excel".', 'error')
            return redirect(url_for('brand.export'))
            
    except Exception as e:
        logger.error(f"Error exporting trend data: {e}")
        flash('An error occurred while exporting trend data.', 'error')
        return redirect(url_for('brand.export'))

