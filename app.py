import os
from flask import Flask, render_template
from flask_session import Session
from flask_login import LoginManager
from config import Config
from models import db, User
from routes import main, admin, brand, influencer
from auth import auth

app = Flask(__name__)
app.config.from_object(Config)
# SECRET_KEY is now loaded from Config class (which reads from environment variable)
# SESSION_TYPE is also loaded from Config

Session(app)
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    """Load user based on ID."""
    return User.query.get(int(user_id))

app.register_blueprint(main)
app.register_blueprint(auth)
app.register_blueprint(admin)
app.register_blueprint(brand)
app.register_blueprint(influencer)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
