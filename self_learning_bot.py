#!/usr/bin/env python3
"""
Art Self-Learning Bot for Proletto

This module implements a recommendation system that continuously learns from
scraped opportunity data and user feedback to provide personalized art
opportunities for users.

Key components:
1. Data Pipeline - Processes opportunities and feedback data
2. Feature Engineering - Extracts meaningful features from text and metadata
3. Model Training - Trains and validates recommendation models
4. Inference API - Serves personalized recommendations
5. Self-Healing - Monitors system health and anomalies

The bot integrates with Proletto's existing database and scheduler systems.
"""

import os
import json
import pickle
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Core data processing libraries
import numpy as np
import pandas as pd

# Configuration
MODEL_DIR = 'data/models'
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, 'art_recommender.pkl')
VECTORIZER_PATH = os.path.join(MODEL_DIR, 'text_vectorizer.pkl')
STATS_PATH = os.path.join(MODEL_DIR, 'feature_stats.pkl')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("self_learning_bot")

# ML Libraries
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# Database connection via Flask context (initialized later)
db = None  # Will be set by the initialize_bot function


class ArtRecommendationBot:
    """Main class for the Art Self-Learning Bot"""
    
    def __init__(self):
        """Initialize the recommendation bot"""
        self.model = None
        self.vectorizer = None
        self.feature_stats = None
        self.db = None
        
        # Load existing model if available
        self.load_model_artifacts()
    
    def load_model_artifacts(self) -> None:
        """Load model, vectorizer and feature statistics from disk"""
        try:
            if os.path.exists(MODEL_PATH):
                with open(MODEL_PATH, 'rb') as f:
                    self.model = pickle.load(f)
                
                logger.info("Loaded existing recommendation model")
            
            if os.path.exists(VECTORIZER_PATH):
                with open(VECTORIZER_PATH, 'rb') as f:
                    self.vectorizer = pickle.load(f)
                
                logger.info("Loaded existing text vectorizer")
                
            if os.path.exists(STATS_PATH):
                with open(STATS_PATH, 'rb') as f:
                    self.feature_stats = pickle.load(f)
                
                logger.info("Loaded existing feature statistics")
        
        except Exception as e:
            logger.error(f"Error loading model artifacts: {e}")
            logger.error(traceback.format_exc())
    
    def save_model_artifacts(self) -> None:
        """Save model, vectorizer and feature statistics to disk"""
        try:
            if self.model is not None:
                with open(MODEL_PATH, 'wb') as f:
                    pickle.dump(self.model, f)
                
                logger.info("Saved recommendation model to disk")
            
            if self.vectorizer is not None:
                with open(VECTORIZER_PATH, 'wb') as f:
                    pickle.dump(self.vectorizer, f)
                
                logger.info("Saved text vectorizer to disk")
                
            if self.feature_stats is not None:
                with open(STATS_PATH, 'wb') as f:
                    pickle.dump(self.feature_stats, f)
                
                logger.info("Saved feature statistics to disk")
        
        except Exception as e:
            logger.error(f"Error saving model artifacts: {e}")
            logger.error(traceback.format_exc())
    
    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Load opportunities and feedback data from database
        
        Returns:
            Tuple of DataFrames (opportunities, feedback)
        """
        from models import Opportunity, Feedback
        
        # Load opportunities
        opportunities = Opportunity.query.all()
        opportunities_data = []
        
        for opp in opportunities:
            # Convert to dictionary
            opp_dict = {
                'id': opp.id,
                'title': opp.title,
                'description': opp.description or '',
                'url': opp.url or '',
                'deadline': opp.deadline,
                'source': opp.source or '',
                'location': opp.location or '',
                'category': opp.category or 'art',
                'tags': opp.tags or '',
                'created_at': opp.created_at,
                'updated_at': opp.updated_at
            }
            opportunities_data.append(opp_dict)
        
        # Load feedback
        feedback = Feedback.query.all()
        feedback_data = []
        
        for fb in feedback:
            fb_dict = {
                'id': fb.id,
                'user_id': fb.user_id,
                'opportunity_id': fb.opportunity_id,
                'rating': fb.rating,
                'comment': fb.comment or '',
                'created_at': fb.created_at
            }
            feedback_data.append(fb_dict)
        
        # Convert to DataFrame
        opportunities_df = pd.DataFrame(opportunities_data)
        feedback_df = pd.DataFrame(feedback_data)
        
        logger.info(f"Loaded {len(opportunities_df)} opportunities and {len(feedback_df)} feedback records")
        
        return opportunities_df, feedback_df
    
    def engineer_features(self, 
                          opportunities_df: pd.DataFrame, 
                          feedback_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Engineer features for opportunities
        
        Args:
            opportunities_df: DataFrame of opportunities
            feedback_df: Optional DataFrame of user feedback
            
        Returns:
            DataFrame with engineered features
        """
        # Create a copy of the opportunities DataFrame
        features_df = opportunities_df.copy()
        
        # Handle missing values
        features_df['description'] = features_df['description'].fillna('')
        features_df['title'] = features_df['title'].fillna('')
        features_df['source'] = features_df['source'].fillna('')
        features_df['location'] = features_df['location'].fillna('')
        features_df['category'] = features_df['category'].fillna('art')
        features_df['tags'] = features_df['tags'].fillna('')
        
        # Convert dates to numeric features
        features_df['days_to_deadline'] = np.nan
        current_time = datetime.utcnow()
        
        # Calculate days until deadline
        features_df.loc[features_df['deadline'].notna(), 'days_to_deadline'] = \
            features_df.loc[features_df['deadline'].notna(), 'deadline'].apply(
                lambda x: (x - current_time).total_seconds() / 86400 if x > current_time else -1
            )
        
        # Calculate days since creation
        features_df['days_since_creation'] = features_df['created_at'].apply(
            lambda x: (current_time - x).total_seconds() / 86400
        )
        
        # Text features - combine title, description, and tags
        features_df['text_content'] = features_df['title'] + ' ' + features_df['description'] + ' ' + features_df['tags']
        
        # Vectorize text content if vectorizer exists, otherwise create new one
        if self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 2)
            )
            text_features = self.vectorizer.fit_transform(features_df['text_content']).toarray()
            logger.info("Created new text vectorizer for opportunity content")
        else:
            text_features = self.vectorizer.transform(features_df['text_content']).toarray()
            logger.info("Used existing text vectorizer for opportunity content")
        
        # Create text feature column names
        text_feature_names = [f'text_{i}' for i in range(text_features.shape[1])]
        
        # Add text features to the dataframe
        text_features_df = pd.DataFrame(text_features, columns=text_feature_names)
        features_df = pd.concat([features_df, text_features_df], axis=1)
        
        # Source-based features (one-hot encoding)
        features_df['source_encoded'] = features_df['source'].str.lower()
        source_dummies = pd.get_dummies(features_df['source_encoded'], prefix='source')
        features_df = pd.concat([features_df, source_dummies], axis=1)
        
        # Location-based features (one-hot encoding)
        features_df['location_encoded'] = features_df['location'].str.lower()
        location_dummies = pd.get_dummies(features_df['location_encoded'], prefix='location')
        features_df = pd.concat([features_df, location_dummies], axis=1)
        
        # Category-based features (one-hot encoding)
        category_dummies = pd.get_dummies(features_df['category'], prefix='category')
        features_df = pd.concat([features_df, category_dummies], axis=1)
        
        # If feedback data is provided, add popularity and engagement features
        if feedback_df is not None and not feedback_df.empty:
            # Count feedback per opportunity
            feedback_counts = feedback_df.groupby('opportunity_id').size()
            features_df['feedback_count'] = features_df['id'].map(feedback_counts).fillna(0)
            
            # Average rating per opportunity
            avg_ratings = feedback_df.groupby('opportunity_id')['rating'].mean()
            features_df['avg_rating'] = features_df['id'].map(avg_ratings).fillna(2.5)  # Default to neutral
            
            # Rating variance per opportunity
            rating_variance = feedback_df.groupby('opportunity_id')['rating'].var()
            features_df['rating_variance'] = features_df['id'].map(rating_variance).fillna(0)
        else:
            # Default values when no feedback is available
            features_df['feedback_count'] = 0
            features_df['avg_rating'] = 2.5  # Neutral rating
            features_df['rating_variance'] = 0
        
        # Update feature statistics
        numeric_columns = ['days_to_deadline', 'days_since_creation', 'feedback_count', 
                          'avg_rating', 'rating_variance']
        
        # Calculate statistics for normalization
        self.feature_stats = {
            column: {
                'mean': features_df[column].mean(),
                'std': features_df[column].std() or 1.0,  # Avoid division by zero
                'min': features_df[column].min(),
                'max': features_df[column].max()
            }
            for column in numeric_columns
        }
        
        # Normalize numeric features
        for column in numeric_columns:
            stats = self.feature_stats[column]
            if stats['max'] > stats['min']:
                features_df[f'{column}_norm'] = (features_df[column] - stats['min']) / (stats['max'] - stats['min'])
            else:
                features_df[f'{column}_norm'] = 0.5  # Default to middle value if there's no range
        
        logger.info(f"Engineered features for {len(features_df)} opportunities")
        
        return features_df
    
    def prepare_training_data(self, 
                              features_df: pd.DataFrame, 
                              feedback_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from features and feedback
        
        Args:
            features_df: DataFrame with engineered features
            feedback_df: DataFrame with user feedback
            
        Returns:
            Tuple of (X, y) for training
        """
        # Get all feature columns (exclude non-feature columns)
        exclude_columns = ['id', 'title', 'description', 'url', 'deadline', 
                          'source', 'location', 'category', 'tags', 'created_at', 
                          'updated_at', 'text_content', 'source_encoded', 'location_encoded']
        
        feature_columns = [col for col in features_df.columns if col not in exclude_columns]
        
        # Create training data from feedback
        X_rows = []
        y_values = []
        
        for _, feedback in feedback_df.iterrows():
            opportunity_id = feedback['opportunity_id']
            
            # Find the opportunity in features_df
            opportunity = features_df[features_df['id'] == opportunity_id]
            
            if not opportunity.empty:
                # Get features for this opportunity
                X_row = opportunity[feature_columns].values[0]
                
                # Convert rating (1-5) to binary target (rating >= 3 is positive)
                y_value = 1 if feedback['rating'] >= 3 else 0
                
                X_rows.append(X_row)
                y_values.append(y_value)
        
        X = np.array(X_rows)
        y = np.array(y_values)
        
        # Check if we have enough data
        if len(y) < 10:
            logger.warning(f"Not enough training data available: only {len(y)} samples")
            return None, None
        
        logger.info(f"Prepared training data with {len(y)} samples and {X.shape[1]} features")
        
        return X, y
    
    def train_model(self, X: np.ndarray, y: np.ndarray) -> Optional[RandomForestClassifier]:
        """
        Train recommendation model
        
        Args:
            X: Feature matrix
            y: Target vector
            
        Returns:
            Trained model or None if training failed
        """
        # Check if we have enough data
        if X is None or y is None or len(y) < 10:
            logger.warning("Not enough data to train model")
            return None
        
        try:
            # Split data into train and validation sets
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y if len(np.unique(y)) > 1 else None
            )
            
            # Create and train RandomForest model
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=7,
                random_state=42,
                class_weight='balanced'
            )
            
            # RandomForest doesn't use eval_set, just fit the model directly
            model.fit(X_train, y_train)
            
            # Evaluate on validation set
            val_score = model.score(X_val, y_val)
            logger.info(f"Model validation accuracy: {val_score:.4f}")
            
            # Save the model
            self.model = model
            self.save_model_artifacts()
            
            return model
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def detect_anomalies(self, features_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect anomalies in feature distributions
        
        Args:
            features_df: DataFrame with engineered features
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        
        # Check for outliers in numeric features
        numeric_columns = ['days_to_deadline', 'days_since_creation', 'feedback_count', 
                          'avg_rating', 'rating_variance']
        
        for column in numeric_columns:
            if column in features_df.columns:
                # Skip columns with all identical values
                if features_df[column].nunique() <= 1:
                    continue
                
                # Calculate z-scores
                mean = features_df[column].mean()
                std = features_df[column].std()
                
                if std == 0:
                    continue
                
                z_scores = (features_df[column] - mean) / std
                
                # Find outliers (absolute z-score > 3)
                outliers = features_df[abs(z_scores) > 3]
                
                if not outliers.empty:
                    anomalies.append({
                        'type': 'outlier',
                        'feature': column,
                        'count': len(outliers),
                        'pct': len(outliers) / len(features_df) * 100,
                        'ids': outliers['id'].tolist()
                    })
        
        # Check for missing values
        for column in features_df.columns:
            missing_count = features_df[column].isna().sum()
            if missing_count > 0:
                anomalies.append({
                    'type': 'missing_values',
                    'feature': column,
                    'count': missing_count,
                    'pct': missing_count / len(features_df) * 100
                })
        
        logger.info(f"Detected {len(anomalies)} anomalies in feature distributions")
        
        return anomalies
    
    def get_recommendations(self, 
                           user_id: int, 
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a user
        
        Args:
            user_id: User ID to get recommendations for
            limit: Maximum number of recommendations to return
            
        Returns:
            List of recommended opportunities
        """
        # Import models in context to avoid circular imports
        from models import User, Feedback, Opportunity
        
        try:
            # Check if model is loaded
            if self.model is None or self.vectorizer is None:
                logger.warning("Model or vectorizer not loaded, trying to load...")
                self.load_model_artifacts()
                
                if self.model is None:
                    logger.warning("No trained model available, using recent opportunities")
                    # Return recent opportunities (fallback)
                    recent_opportunities = Opportunity.query.order_by(
                        Opportunity.created_at.desc()
                    ).limit(limit).all()
                    
                    return [opp.to_dict() for opp in recent_opportunities]
            
            # Get user instance
            user = User.query.get(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return []
            
            # Get user's previous feedback
            user_feedback = Feedback.query.filter_by(user_id=user_id).all()
            
            # Get user's previously viewed opportunities
            viewed_opportunity_ids = [fb.opportunity_id for fb in user_feedback]
            
            # Get all opportunities
            opportunities = Opportunity.query.all()
            
            # No opportunities available
            if not opportunities:
                logger.warning("No opportunities available in the database")
                return []
            
            # Convert opportunities to DataFrame for feature engineering
            opportunities_data = []
            for opp in opportunities:
                opp_dict = {
                    'id': opp.id,
                    'title': opp.title,
                    'description': opp.description or '',
                    'url': opp.url or '',
                    'deadline': opp.deadline,
                    'source': opp.source or '',
                    'location': opp.location or '',
                    'category': opp.category or 'art',
                    'tags': opp.tags or '',
                    'created_at': opp.created_at,
                    'updated_at': opp.updated_at
                }
                opportunities_data.append(opp_dict)
            
            opportunities_df = pd.DataFrame(opportunities_data)
            
            # Convert user feedback to DataFrame
            feedback_data = []
            for fb in user_feedback:
                fb_dict = {
                    'id': fb.id,
                    'user_id': fb.user_id,
                    'opportunity_id': fb.opportunity_id,
                    'rating': fb.rating,
                    'comment': fb.comment or '',
                    'created_at': fb.created_at
                }
                feedback_data.append(fb_dict)
            
            all_feedback_df = pd.DataFrame(feedback_data)
            
            # Engineer features for opportunities
            features_df = self.engineer_features(opportunities_df, all_feedback_df)
            
            # Get all feature columns (exclude non-feature columns)
            exclude_columns = ['id', 'title', 'description', 'url', 'deadline', 
                              'source', 'location', 'category', 'tags', 'created_at', 
                              'updated_at', 'text_content', 'source_encoded', 'location_encoded']
            
            feature_columns = [col for col in features_df.columns if col not in exclude_columns]
            
            # If we have a trained model, use it for predictions
            if self.model is not None:
                # Filter out opportunities that the user has already rated/viewed
                unrated_df = features_df[~features_df['id'].isin(viewed_opportunity_ids)]
                
                if unrated_df.empty:
                    logger.warning(f"User {user_id} has viewed all available opportunities")
                    # Return random unviewed opportunities
                    random_opportunities = Opportunity.query.filter(
                        ~Opportunity.id.in_(viewed_opportunity_ids)
                    ).order_by(Opportunity.created_at.desc()).limit(limit).all()
                    
                    return [opp.to_dict() for opp in random_opportunities]
                
                # Get features for prediction
                X_pred = unrated_df[feature_columns].values
                
                # Predict probability of positive rating
                if hasattr(self.model, 'predict_proba'):
                    pred_proba = self.model.predict_proba(X_pred)
                    # Get probability of positive class (index 1)
                    positive_proba = pred_proba[:, 1]
                else:
                    # Fallback to binary predictions
                    positive_proba = self.model.predict(X_pred)
                
                # Add predictions to DataFrame
                unrated_df['prediction_score'] = positive_proba
                
                # Sort by prediction score and get top opportunities
                top_opportunities = unrated_df.sort_values('prediction_score', ascending=False).head(limit)
                
                # Convert top opportunities to list of dictionaries
                recommendations = []
                for _, row in top_opportunities.iterrows():
                    opp = Opportunity.query.get(row['id'])
                    if opp:
                        opp_dict = opp.to_dict()
                        # Add prediction score (confidence)
                        opp_dict['confidence'] = float(row['prediction_score'])
                        recommendations.append(opp_dict)
                
                logger.info(f"Generated {len(recommendations)} personalized recommendations for user {user_id}")
                
                return recommendations
            else:
                logger.warning("No model available, using recent opportunities")
                # Fallback to recent opportunities
                recent_opportunities = Opportunity.query.order_by(
                    Opportunity.created_at.desc()
                ).limit(limit).all()
                
                return [opp.to_dict() for opp in recent_opportunities]
                
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            logger.error(traceback.format_exc())
            return []
    
    def retrain_recommender(self) -> bool:
        """
        Retrain the recommendation model with latest data
        
        Returns:
            bool: True if training was successful
        """
        try:
            # Load data
            opportunities_df, feedback_df = self.load_data()
            
            # Check if we have enough data
            if opportunities_df.empty or feedback_df.empty or len(feedback_df) < 10:
                logger.warning(f"Not enough data for training: {len(opportunities_df)} opportunities, {len(feedback_df)} feedback records")
                return False
            
            # Engineer features
            features_df = self.engineer_features(opportunities_df, feedback_df)
            
            # Prepare training data
            X, y = self.prepare_training_data(features_df, feedback_df)
            
            # Check if we have enough data after preprocessing
            if X is None or y is None or len(y) < 10:
                logger.warning(f"Not enough data after preprocessing: {len(y) if y is not None else 0} samples")
                return False
            
            # Train model
            model = self.train_model(X, y)
            
            # Check if training was successful
            if model is None:
                logger.error("Model training failed")
                return False
            
            # Save artifacts
            self.save_model_artifacts()
            
            logger.info("Recommender model retraining completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error retraining recommender: {e}")
            logger.error(traceback.format_exc())
            return False


# Global instance of the recommendation bot
_recommendation_bot = None

def initialize_bot(app=None):
    """Initialize the recommendation bot with Flask app context"""
    global _recommendation_bot
    
    try:
        if _recommendation_bot is None:
            _recommendation_bot = ArtRecommendationBot()
            logger.info("Art recommendation bot initialized")
        
        # Initialize database if app is provided
        if app is not None:
            with app.app_context():
                from models import db
                _recommendation_bot.db = db
                logger.info("Database connection initialized for recommendation bot")
        
        return _recommendation_bot
    
    except Exception as e:
        logger.error(f"Error initializing recommendation bot: {e}")
        logger.error(traceback.format_exc())
        return None

def retrain_recommender() -> bool:
    """
    Function to be called by scheduler for model retraining
    
    Returns:
        bool: True if retraining was successful
    """
    global _recommendation_bot
    
    try:
        if _recommendation_bot is None:
            _recommendation_bot = initialize_bot()
        
        if _recommendation_bot is None:
            logger.error("Could not initialize recommendation bot")
            return False
        
        return _recommendation_bot.retrain_recommender()
    
    except Exception as e:
        logger.error(f"Error retraining recommender: {e}")
        logger.error(traceback.format_exc())
        return False

def get_recommendations(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get personalized recommendations for a user
    
    Args:
        user_id: User ID to get recommendations for
        limit: Maximum number of recommendations to return
        
    Returns:
        List of recommended opportunities
    """
    global _recommendation_bot
    
    try:
        if _recommendation_bot is None:
            _recommendation_bot = initialize_bot()
        
        if _recommendation_bot is None:
            logger.error("Could not initialize recommendation bot")
            return []
        
        return _recommendation_bot.get_recommendations(user_id, limit)
    
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        logger.error(traceback.format_exc())
        return []

# Initialize bot when module is imported
bot = initialize_bot()