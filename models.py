from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    skin_type = db.Column(db.String(50))
    concerns = db.Column(db.String(200))
    role = db.Column(db.String(20), default='user', nullable=False)  # user, brand, admin, influencer
    brand_name = db.Column(db.String(100), nullable=True)  # Brand name for brand users (matches Product.brand_name)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role):
        """Check if user has a specific role."""
        return self.role == role
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.role == 'admin'
    
    def is_brand(self):
        """Check if user is a brand."""
        return self.role == 'brand'
    
    def is_influencer(self):
        """Check if user is an influencer."""
        return self.role == 'influencer'
    
    def can_manage_users(self):
        """Check if user can manage other users (admin only)."""
        return self.role == 'admin'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    brand_name = db.Column(db.String(100))  # Brand name from dataset
    category = db.Column(db.String(50))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))  # Product image URL (can be external URL or local file path)
    read_more = db.Column(db.String(500))  # Amazon product URL (read_more field)
    original_product_id = db.Column(db.String(50))  # Original product_id from CSV (e.g., P439055)
    rating = db.Column(db.Float)  # Average rating from dataset

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    text = db.Column(db.Text)
    rating = db.Column(db.Integer)  # Rating from 1 to 5 stars
    sentiment = db.Column(db.String(20))  # positive, negative, neutral
    skin_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    original_author_id = db.Column(db.String(50))  # Original author_id from CSV
    suspicious_score = db.Column(db.Float, default=0.0)  # Score from 0.0 to 1.0 for fake review detection
    is_verified = db.Column(db.Boolean, default=False)  # Manual verification flag

