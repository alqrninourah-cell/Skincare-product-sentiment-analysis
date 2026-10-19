"""Authorization decorators for role-based access control."""
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to require specific role(s) for a route.
    
    Usage:
        @role_required('admin')
        @role_required('admin', 'brand')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login'))
            
            # Check if user has one of the required roles
            if not hasattr(current_user, 'role') or current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not hasattr(current_user, 'is_admin') or not current_user.is_admin():
            flash('Admin access required.', 'error')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def brand_required(f):
    """Decorator to require brand role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        
        if not hasattr(current_user, 'is_brand') or not current_user.is_brand():
            flash('Brand access required.', 'error')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

def influencer_required(f):
    """Decorator to require influencer role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.influencer_login'))
        
        if not hasattr(current_user, 'is_influencer') or not current_user.is_influencer():
            flash('Influencer access required.', 'error')
            abort(403)
        
        return f(*args, **kwargs)
    return decorated_function

