"""
Sentiment Analysis Service.

This service provides sentiment analysis functionality using a dual-engine
approach combining VADER and TextBlob for improved accuracy.
"""

from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os
from typing import Dict, Optional


class SentimentService:
    """
    Service for analyzing text sentiment using dual-engine approach.
    
    Uses VADER and TextBlob to analyze sentiment and combines results
    for improved accuracy. Thresholds are configurable via environment
    variables or use defaults.
    
    Attributes:
        POSITIVE_THRESHOLD (float): Threshold for positive sentiment (default: 0.1)
        NEGATIVE_THRESHOLD (float): Threshold for negative sentiment (default: -0.1)
        vader_analyzer (SentimentIntensityAnalyzer): VADER sentiment analyzer instance
    """
    
    # Configurable thresholds (can be overridden via environment variables)
    POSITIVE_THRESHOLD = float(os.environ.get('SENTIMENT_THRESHOLD_POSITIVE', '0.1'))
    NEGATIVE_THRESHOLD = float(os.environ.get('SENTIMENT_THRESHOLD_NEGATIVE', '-0.1'))
    
    def __init__(self):
        """Initialize the sentiment analyzer."""
        self.vader_analyzer = SentimentIntensityAnalyzer()
    
    def analyze(self, text: str) -> Dict[str, any]:
        """
        Analyze sentiment of given text using dual-engine approach.
        
        Args:
            text (str): Text to analyze. Can be None or empty string.
            
        Returns:
            dict: Sentiment analysis result with keys:
                - sentiment (str): 'positive', 'negative', or 'neutral'
                - vader_score (float): VADER sentiment score (-1 to 1)
                - blob_score (float): TextBlob sentiment score (-1 to 1)
                - combined_score (float): Average of both scores
                - confidence (float): Absolute value of combined score (0 to 1)
                
        Example:
            >>> service = SentimentService()
            >>> result = service.analyze("I love this product!")
            >>> print(result['sentiment'])
            'positive'
            >>> print(result['confidence'])
            0.85
        """
        # Handle empty or None text
        if not text or not str(text).strip():
            return {
                'sentiment': 'neutral',
                'vader_score': 0.0,
                'blob_score': 0.0,
                'combined_score': 0.0,
                'confidence': 0.0
            }
        
        # Convert to string if not already
        text_str = str(text).strip()
        
        # VADER analysis - optimized for social media style reviews
        vader_scores = self.vader_analyzer.polarity_scores(text_str)
        vader_score = vader_scores['compound']  # Range: -1 to +1
        
        # TextBlob analysis - strong on grammatical structure
        blob = TextBlob(text_str)
        blob_score = blob.sentiment.polarity  # Range: -1 to +1
        
        # Combine scores using average (mean fusion)
        combined_score = (vader_score + blob_score) / 2.0
        
        # Classify sentiment based on thresholds
        sentiment = self._classify(combined_score)
        
        # Calculate confidence as absolute value of combined score
        confidence = abs(combined_score)
        
        return {
            'sentiment': sentiment,
            'vader_score': vader_score,
            'blob_score': blob_score,
            'combined_score': combined_score,
            'confidence': confidence
        }
    
    def _classify(self, score: float) -> str:
        """
        Classify sentiment based on combined score and thresholds.
        
        Args:
            score (float): Combined sentiment score (-1 to 1)
            
        Returns:
            str: 'positive', 'negative', or 'neutral'
        """
        if score > self.POSITIVE_THRESHOLD:
            return 'positive'
        elif score < self.NEGATIVE_THRESHOLD:
            return 'negative'
        else:
            return 'neutral'
    
    def analyze_batch(self, texts: list) -> list:
        """
        Analyze sentiment for multiple texts in batch.
        
        Args:
            texts (list): List of text strings to analyze
            
        Returns:
            list: List of sentiment analysis results (same structure as analyze())
        """
        return [self.analyze(text) for text in texts]
    
    def get_sentiment_label(self, text: str) -> str:
        """
        Get only the sentiment label (positive/negative/neutral).
        
        Convenience method that returns only the sentiment classification.
        
        Args:
            text (str): Text to analyze
            
        Returns:
            str: 'positive', 'negative', or 'neutral'
        """
        result = self.analyze(text)
        return result['sentiment']

