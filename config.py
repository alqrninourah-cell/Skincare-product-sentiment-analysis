import os
import secrets

class Config:
    """Base configuration class."""
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///skincare_demo.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Sentiment Analysis Configuration
    # These values match the standardized threshold used across the application
    # Threshold: 0.1 (standardized across EDA and application)
    SENTIMENT_THRESHOLD_POSITIVE = float(os.environ.get('SENTIMENT_THRESHOLD_POSITIVE', '0.1'))
    SENTIMENT_THRESHOLD_NEGATIVE = float(os.environ.get('SENTIMENT_THRESHOLD_NEGATIVE', '-0.1'))
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Override with production database URL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or Config.SQLALCHEMY_DATABASE_URI
    
    # Production logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
