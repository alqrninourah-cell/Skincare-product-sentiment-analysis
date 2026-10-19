from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from models import db, User

auth = Blueprint('auth', __name__)

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    skin_type = SelectField('Skin Type', choices=[
        ('', 'Select your skin type'),
        ('normal', 'Normal'),
        ('combination', 'Combination'),
        ('dry', 'Dry'),
        ('oily', 'Oily')
    ], validators=[DataRequired()])
    concerns = TextAreaField('Skin Concerns')
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class BrandRegisterForm(FlaskForm):
    name = SelectField('Brand Name', validators=[DataRequired()], choices=[], coerce=str)  # Dropdown with unique brand names
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class InfluencerRegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data, 
            skin_type=form.skin_type.data, 
            concerns=form.concerns.data,
            role='user'  # Default role for new users
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirect based on role
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif current_user.is_brand():
            return redirect(url_for('brand.dashboard'))
        elif current_user.is_influencer():
            return redirect(url_for('influencer.dashboard'))
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            # Validate and sanitize next_page to prevent open redirects and hash fragments
            if next_page:
                # Remove hash fragments (they shouldn't be in URL params, but just in case)
                next_page = next_page.split('#')[0]
                # Only allow relative URLs (starting with /) and not external URLs
                if next_page.startswith('/') and not next_page.startswith('//'):
                    # Additional check: ensure it's not trying to redirect to login again
                    if not next_page.startswith('/login'):
                        return redirect(next_page)
            # Redirect based on role after login
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            elif user.is_brand():
                return redirect(url_for('brand.dashboard'))
            elif user.is_influencer():
                return redirect(url_for('influencer.dashboard'))
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html', form=form)

@auth.route('/brand/login', methods=['GET', 'POST'])
def brand_login():
    """Brand login route - uses same login logic but renders brand template."""
    if current_user.is_authenticated:
        if current_user.is_brand():
            return redirect(url_for('brand.dashboard'))
        elif current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_brand():
                flash('This account is not a brand account. Please use the regular login.', 'error')
                return render_template('brand/login.html', form=form)
            login_user(user)
            next_page = request.args.get('next')
            # Validate next_page to prevent open redirects and remove hash fragments
            if next_page:
                # Remove hash fragments and validate it's a relative URL
                next_page = next_page.split('#')[0]  # Remove hash fragment
                # Only allow relative URLs (starting with /) or same domain
                if next_page.startswith('/') and not next_page.startswith('//'):
                    return redirect(next_page)
            return redirect(url_for('brand.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('brand/login.html', form=form)

@auth.route('/brand/register', methods=['GET', 'POST'])
def brand_register():
    """Brand registration route."""
    if current_user.is_authenticated:
        if current_user.is_brand():
            return redirect(url_for('brand.dashboard'))
        return redirect(url_for('main.index'))
    
    # Get unique brand names from products
    from models import Product
    unique_brands = db.session.query(Product.brand_name).distinct().order_by(Product.brand_name).all()
    brand_choices = [('', 'Select your brand')] + [(brand[0], brand[0]) for brand in unique_brands if brand[0]]
    
    form = BrandRegisterForm()
    form.name.choices = brand_choices
    
    if form.validate_on_submit():
        # Brand name validation is already handled by SelectField choices
        user = User(
            email=form.email.data,
            role='brand',  # Set role as brand
            brand_name=form.name.data  # Store brand name to match with products
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Brand registration successful! Please log in.', 'success')
        return redirect(url_for('auth.brand_login'))
    return render_template('brand/register.html', form=form)

@auth.route('/influencer/register', methods=['GET', 'POST'])
def influencer_register():
    """Influencer registration route."""
    if current_user.is_authenticated:
        if current_user.is_influencer():
            return redirect(url_for('influencer.dashboard'))
        return redirect(url_for('main.index'))
    
    form = InfluencerRegisterForm()
    
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            role='influencer'  # Set role as influencer
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Influencer registration successful! Please log in.', 'success')
        return redirect(url_for('auth.influencer_login'))
    return render_template('influencer/register.html', form=form)

@auth.route('/influencer/login', methods=['GET', 'POST'])
def influencer_login():
    """Influencer login route."""
    if current_user.is_authenticated:
        if current_user.is_influencer():
            return redirect(url_for('influencer.dashboard'))
        elif current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.is_influencer():
                flash('This account is not an influencer account. Please use the regular login.', 'error')
                return render_template('influencer/login.html', form=form)
            login_user(user)
            next_page = request.args.get('next')
            # Validate next_page to prevent open redirects and remove hash fragments
            if next_page:
                # Remove hash fragments and validate it's a relative URL
                next_page = next_page.split('#')[0]  # Remove hash fragment
                # Only allow relative URLs (starting with /) and not external URLs
                if next_page.startswith('/') and not next_page.startswith('//'):
                    # Additional check: ensure it's not trying to redirect to login again
                    if not next_page.startswith('/login') and not next_page.startswith('/influencer/login'):
                        return redirect(next_page)
            return redirect(url_for('influencer.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('influencer/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
