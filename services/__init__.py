"""
Services module for business logic.

This module contains service classes that handle business logic,
separating it from route handlers and database models.
"""

from .sentiment_service import SentimentService
from .recommendation_service import RecommendationService
from .review_service import ReviewService
from .brand_analytics_service import BrandAnalyticsService
from .trend_service import TrendService
from .export_service import ExportService
from .influencer_service import InfluencerService
from .pros_cons_service import ProsConsService
from .fake_review_detection_service import FakeReviewDetectionService

__all__ = [
    'SentimentService', 
    'RecommendationService', 
    'ReviewService',
    'BrandAnalyticsService',
    'TrendService',
    'ExportService',
    'InfluencerService',
    'ProsConsService',
    'FakeReviewDetectionService'
]

