"""
Fake Review Detection Service.

This service provides ML-based fake review detection using scikit-learn
to identify suspicious reviews based on various patterns and features.

Note: This service handles both:
- User-generated reviews (uses user_id for author tracking)
- Dataset reviews from Sephora (uses original_author_id for author tracking)

The detection algorithm works the same for both types, identifying suspicious
patterns regardless of the review source.
"""

from typing import List, Dict, Optional
from models import db, Review, User, Product
from datetime import datetime, timedelta
from collections import Counter
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)


class FakeReviewDetectionService:
    """
    Service for detecting fake or biased reviews using ML-based approach.
    
    Uses Isolation Forest algorithm to identify outliers based on:
    - Rating distribution patterns
    - Review text similarity
    - Temporal patterns
    - Sentiment-rating correlation
    - Review length patterns
    """
    
    def __init__(self, contamination=0.1):
        """
        Initialize fake review detection service.
        
        Args:
            contamination (float): Expected proportion of outliers (default: 0.1 = 10%)
        """
        self.contamination = contamination
        self.scaler = StandardScaler()
        self.model = None
    
    def calculate_suspicious_score(self, review: Review) -> float:
        """
        Calculate suspicious score for a single review.
        
        Args:
            review (Review): Review object to analyze
            
        Returns:
            float: Suspicious score from 0.0 to 1.0 (higher = more suspicious)
        """
        try:
            # Get all reviews for feature extraction
            all_reviews = Review.query.filter(
                Review.product_id == review.product_id
            ).all()
            
            if len(all_reviews) < 3:
                # Not enough reviews to detect patterns
                return 0.0
            
            # Extract features for this review
            features = self._extract_features(review, all_reviews)
            
            # Use ML model to predict if suspicious
            if self.model is None:
                # Train model on all reviews if not already trained
                self._train_model(all_reviews)
            
            if self.model is None:
                # Fallback to heuristic-based scoring
                return self._heuristic_score(review, all_reviews)
            
            # Normalize features
            features_array = np.array([features]).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            
            # Predict using Isolation Forest
            prediction = self.model.predict(features_scaled)[0]
            decision_score = self.model.decision_function(features_scaled)[0]
            
            # Convert to suspicious score (0-1)
            # Isolation Forest: -1 = outlier, 1 = inlier
            # Decision function: negative = more suspicious
            if prediction == -1:
                # Outlier detected
                suspicious_score = min(1.0, abs(decision_score) / 2.0)
            else:
                # Normal review
                suspicious_score = max(0.0, (1.0 + decision_score) / 2.0)
            
            return round(suspicious_score, 4)
            
        except Exception as e:
            logger.error(f"Error calculating suspicious score for review {review.id}: {e}")
            # Fallback to heuristic
            return self._heuristic_score(review, all_reviews)
    
    def detect_fake_reviews(
        self, 
        reviews: Optional[List[Review]] = None,
        product_id: Optional[int] = None,
        threshold: float = 0.7
    ) -> List[Review]:
        """
        Detect fake reviews and update their suspicious_score.
        
        Args:
            reviews (list, optional): List of reviews to analyze. If None, analyzes all reviews.
            product_id (int, optional): If provided, only analyze reviews for this product
            threshold (float): Suspicious score threshold (default: 0.7)
            
        Returns:
            list: List of reviews flagged as suspicious (suspicious_score >= threshold)
        """
        try:
            # Get reviews to analyze
            if reviews is None:
                if product_id:
                    reviews = Review.query.filter_by(product_id=product_id).all()
                else:
                    reviews = Review.query.all()
            
            if not reviews:
                return []
            
            # Train model on all reviews
            self._train_model(reviews)
            
            suspicious_reviews = []
            
            for review in reviews:
                # Calculate suspicious score
                score = self.calculate_suspicious_score(review)
                
                # Update review in database
                review.suspicious_score = score
                
                if score >= threshold:
                    suspicious_reviews.append(review)
            
            # Commit all updates
            db.session.commit()
            
            logger.info(f"Detected {len(suspicious_reviews)} suspicious reviews out of {len(reviews)}")
            
            return suspicious_reviews
            
        except Exception as e:
            logger.error(f"Error detecting fake reviews: {e}")
            db.session.rollback()
            raise
    
    def _extract_features(self, review: Review, all_reviews: List[Review]) -> List[float]:
        """
        Extract features for ML model.
        
        Args:
            review (Review): Review to extract features for
            all_reviews (list): All reviews for context
            
        Returns:
            list: Feature vector
        """
        features = []
        
        # 1. Rating features
        rating = review.rating or 0
        features.append(rating)
        
        # Average rating for product
        product_ratings = [r.rating for r in all_reviews if r.rating]
        avg_rating = np.mean(product_ratings) if product_ratings else 0
        features.append(avg_rating)
        features.append(abs(rating - avg_rating))  # Rating deviation
        
        # 2. Review length features
        text_length = len(review.text) if review.text else 0
        features.append(text_length)
        
        # Average review length
        lengths = [len(r.text) for r in all_reviews if r.text]
        avg_length = np.mean(lengths) if lengths else 0
        features.append(avg_length)
        features.append(abs(text_length - avg_length) if avg_length > 0 else 0)  # Length deviation
        
        # 3. Sentiment-rating correlation
        sentiment_score = 1.0 if review.sentiment == 'positive' else (-1.0 if review.sentiment == 'negative' else 0.0)
        rating_normalized = (rating - 1) / 4.0  # Normalize to 0-1
        sentiment_rating_mismatch = abs(sentiment_score - rating_normalized)
        features.append(sentiment_rating_mismatch)
        
        # 4. Temporal features
        if review.created_at:
            # Days since review was created
            days_ago = (datetime.utcnow() - review.created_at).days
            features.append(days_ago)
            
            # Check for burst pattern (multiple reviews in short time)
            recent_reviews = [r for r in all_reviews 
                            if r.created_at and 
                            abs((r.created_at - review.created_at).days) <= 1]
            burst_count = len(recent_reviews)
            features.append(burst_count)
        else:
            features.extend([0, 0])
        
        # 5. User/Author pattern features
        # For dataset reviews (Sephora), use original_author_id; for user-generated reviews, use user_id
        author_reviews = []
        if review.user_id:
            # User-generated review
            author_reviews = Review.query.filter_by(user_id=review.user_id).all()
        elif review.original_author_id:
            # Dataset review (Sephora) - use original_author_id
            author_reviews = Review.query.filter_by(original_author_id=review.original_author_id).all()
        
        if author_reviews:
            author_review_count = len(author_reviews)
            features.append(author_review_count)
            
            # Check if author always gives same rating
            author_ratings = [r.rating for r in author_reviews if r.rating]
            if author_ratings:
                rating_variance = np.var(author_ratings) if len(author_ratings) > 1 else 0
                features.append(rating_variance)
            else:
                features.append(0)
        else:
            features.extend([0, 0])
        
        # 6. Text similarity (check for duplicate/similar reviews)
        similarity_score = self._calculate_text_similarity(review, all_reviews)
        features.append(similarity_score)
        
        return features
    
    def _calculate_text_similarity(self, review: Review, all_reviews: List[Review]) -> float:
        """
        Calculate maximum text similarity with other reviews.
        
        Args:
            review (Review): Review to check
            all_reviews (list): All reviews to compare against
            
        Returns:
            float: Maximum similarity score (0-1)
        """
        if not review.text or len(review.text.strip()) < 10:
            return 0.0
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            # Get all review texts
            texts = [r.text for r in all_reviews if r.text and r.id != review.id]
            
            if not texts:
                return 0.0
            
            # Add current review text
            all_texts = texts + [review.text]
            
            # Vectorize
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            vectors = vectorizer.fit_transform(all_texts)
            
            # Calculate cosine similarity
            current_vector = vectors[-1]
            other_vectors = vectors[:-1]
            
            similarities = cosine_similarity(current_vector, other_vectors)[0]
            max_similarity = float(np.max(similarities)) if len(similarities) > 0 else 0.0
            
            return max_similarity
            
        except Exception as e:
            logger.warning(f"Error calculating text similarity: {e}")
            # Fallback: simple word overlap
            review_words = set(review.text.lower().split())
            max_overlap = 0.0
            
            for other_review in all_reviews:
                if other_review.id == review.id or not other_review.text:
                    continue
                other_words = set(other_review.text.lower().split())
                overlap = len(review_words & other_words) / max(len(review_words), 1)
                max_overlap = max(max_overlap, overlap)
            
            return max_overlap
    
    def _train_model(self, reviews: List[Review]):
        """
        Train Isolation Forest model on reviews.
        
        Args:
            reviews (list): List of reviews to train on
        """
        try:
            if len(reviews) < 10:
                # Not enough data to train model
                self.model = None
                return
            
            # Extract features for all reviews
            feature_matrix = []
            for review in reviews:
                features = self._extract_features(review, reviews)
                feature_matrix.append(features)
            
            if not feature_matrix:
                self.model = None
                return
            
            # Convert to numpy array
            X = np.array(feature_matrix)
            
            # Standardize features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train Isolation Forest
            self.model = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
            self.model.fit(X_scaled)
            
            logger.debug(f"Trained fake review detection model on {len(reviews)} reviews")
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            self.model = None
    
    def _heuristic_score(self, review: Review, all_reviews: List[Review]) -> float:
        """
        Fallback heuristic-based suspicious score.
        
        Args:
            review (Review): Review to score
            all_reviews (list): All reviews for context
            
        Returns:
            float: Heuristic suspicious score (0-1)
        """
        score = 0.0
        
        # Check 1: Rating extremes
        if review.rating == 5 or review.rating == 1:
            score += 0.2
        
        # Check 2: Very short review
        if review.text and len(review.text.strip()) < 20:
            score += 0.2
        
        # Check 3: Sentiment-rating mismatch
        if review.sentiment == 'positive' and review.rating and review.rating <= 2:
            score += 0.3
        elif review.sentiment == 'negative' and review.rating and review.rating >= 4:
            score += 0.3
        
        # Check 4: Rating deviation from average
        product_ratings = [r.rating for r in all_reviews if r.rating]
        if product_ratings:
            avg_rating = np.mean(product_ratings)
            if review.rating:
                deviation = abs(review.rating - avg_rating)
                if deviation > 2:
                    score += 0.2
        
        # Check 5: Author pattern (if author has multiple reviews)
        # Handle both user-generated reviews (user_id) and dataset reviews (original_author_id)
        author_reviews = []
        if review.user_id:
            author_reviews = Review.query.filter_by(user_id=review.user_id).all()
        elif review.original_author_id:
            author_reviews = Review.query.filter_by(original_author_id=review.original_author_id).all()
        
        if len(author_reviews) > 1:
            author_ratings = [r.rating for r in author_reviews if r.rating]
            if author_ratings and len(set(author_ratings)) == 1:
                # Author always gives same rating (suspicious pattern)
                score += 0.1
        
        return min(1.0, score)

