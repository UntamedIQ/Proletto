"""
Proletto Models

This module contains the database models for the Proletto platform.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON, Enum
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property
# Create a db instance that will be initialized later
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Initialize logger
logger = logging.getLogger(__name__)


class User(UserMixin, db.Model):
    """User model for authentication and profile information."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), index=True, unique=True)
    email = Column(String(120), index=True, unique=True)
    password_hash = Column(String(128))
    profile_image = Column(String(256), nullable=True)
    bio = Column(Text, nullable=True)
    location = Column(String(120), nullable=True)
    website = Column(String(256), nullable=True)
    instagram = Column(String(120), nullable=True)
    twitter = Column(String(120), nullable=True)
    
    # User settings and preferences
    email_notifications = Column(Boolean, default=True)
    weekly_digest = Column(Boolean, default=True)
    opportunity_alerts = Column(Boolean, default=True)
    
    # Membership info
    membership_tier = Column(String(32), default='free')  # free, essentials, insider, gallery
    stripe_customer_id = Column(String(120), nullable=True)
    subscription_id = Column(String(120), nullable=True)
    subscription_status = Column(String(32), nullable=True)  # active, canceled, past_due, etc.
    subscription_end_date = Column(DateTime, nullable=True)
    
    # Activity and metrics
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    login_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    portfolios = relationship('Portfolio', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    applications = relationship('Application', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    saved_opportunities = relationship('SavedOpportunity', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    notifications = relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        """Initialize a new user."""
        super(User, self).__init__(**kwargs)
        if 'password' in kwargs:
            self.set_password(kwargs['password'])
    
    def set_password(self, password):
        """Set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the user's password."""
        return check_password_hash(self.password_hash, password)
    
    def update_login_info(self):
        """Update login information when user logs in."""
        self.last_login = datetime.utcnow()
        self.login_count += 1
    
    def is_premium(self):
        """Check if the user has an active premium subscription."""
        if self.membership_tier in ['essentials', 'insider', 'gallery']:
            if self.subscription_status == 'active':
                return True
            if self.subscription_end_date and self.subscription_end_date > datetime.utcnow():
                return True
        return False
    
    def get_profile_image_url(self):
        """Get the URL for the user's profile image."""
        if self.profile_image:
            return self.profile_image
        return '/static/images/default_avatar.png'
    
    def to_dict(self):
        """Convert user to dictionary for API responses."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'profile_image': self.get_profile_image_url(),
            'bio': self.bio,
            'location': self.location,
            'website': self.website,
            'instagram': self.instagram,
            'twitter': self.twitter,
            'membership_tier': self.membership_tier,
            'is_premium': self.is_premium(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<User {self.username}>'


class Portfolio(db.Model):
    """Portfolio model for user portfolio items."""
    __tablename__ = 'portfolios'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String(120))
    description = Column(Text, nullable=True)
    image_url = Column(String(256), nullable=True)
    order = Column(Integer, default=0)
    
    # Portfolio metadata
    medium = Column(String(64), nullable=True)
    year = Column(Integer, nullable=True)
    dimensions = Column(String(64), nullable=True)
    tags = Column(Text, nullable=True)  # Comma-separated list of tags
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert portfolio to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'order': self.order,
            'medium': self.medium,
            'year': self.year,
            'dimensions': self.dimensions,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Portfolio {self.title}>'


class Opportunity(db.Model):
    """Opportunity model for art calls, grants, residencies, etc."""
    __tablename__ = 'opportunities'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(256))
    description = Column(Text)
    organization = Column(String(256), nullable=True)
    location = Column(String(256), nullable=True)
    url = Column(String(512))
    deadline = Column(DateTime, nullable=True)
    
    # Opportunity metadata
    type = Column(String(64))  # grant, residency, exhibition, etc.
    categories = Column(Text, nullable=True)  # Comma-separated list of art categories
    eligibility = Column(Text, nullable=True)
    fee_to_apply = Column(Boolean, default=False)
    fee_amount = Column(Float, nullable=True)
    
    # Source information
    source = Column(String(64))  # website or engine name where the opportunity was found
    source_id = Column(String(256), nullable=True)  # ID from the source
    
    # Internal tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = Column(Boolean, default=True)
    featured = Column(Boolean, default=False)
    
    # Relationships
    applications = relationship('Application', backref='opportunity', lazy='dynamic', cascade='all, delete-orphan')
    saved_by = relationship('SavedOpportunity', backref='opportunity', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert opportunity to dictionary for API responses."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'organization': self.organization,
            'location': self.location,
            'url': self.url,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'type': self.type,
            'categories': self.categories.split(',') if self.categories else [],
            'eligibility': self.eligibility,
            'fee_to_apply': self.fee_to_apply,
            'fee_amount': self.fee_amount,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'active': self.active,
            'featured': self.featured,
        }
    
    def __repr__(self):
        return f'<Opportunity {self.title}>'


class SavedOpportunity(db.Model):
    """Model for opportunities saved by users."""
    __tablename__ = 'saved_opportunities'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'))
    saved_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f'<SavedOpportunity user_id={self.user_id} opportunity_id={self.opportunity_id}>'


class Feedback(db.Model):
    """Model for user feedback on opportunity recommendations."""
    __tablename__ = 'feedback'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=False)
    opp_id = Column(String(64), nullable=True)  # Redundant with opportunity_id but kept for compatibility
    rating = Column(Integer, nullable=False)  # 1-5 rating scale
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to User model
    user = relationship('User', backref=backref('feedbacks', lazy='dynamic', cascade='all, delete-orphan'))
    
    @property
    def was_helpful(self):
        """For backwards compatibility - rating of 3 or above is considered helpful"""
        return self.rating >= 3
    
    def __repr__(self):
        return f'<Feedback user_id={self.user_id} opportunity_id={self.opportunity_id} rating={self.rating}>'


class Application(db.Model):
    """Model for user applications to opportunities."""
    __tablename__ = 'applications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'))
    
    # Application status
    status = Column(String(32), default='draft')  # draft, submitted, in_review, accepted, rejected
    
    # Application content
    artist_statement = Column(Text, nullable=True)
    project_proposal = Column(Text, nullable=True)
    cv_url = Column(String(512), nullable=True)
    
    # Portfolio items selected for this application
    portfolio_items = Column(Text, nullable=True)  # Comma-separated IDs of portfolio items
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    decision_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert application to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'opportunity_id': self.opportunity_id,
            'status': self.status,
            'artist_statement': self.artist_statement,
            'project_proposal': self.project_proposal,
            'cv_url': self.cv_url,
            'portfolio_items': [int(id) for id in self.portfolio_items.split(',')] if self.portfolio_items else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'decision_at': self.decision_at.isoformat() if self.decision_at else None,
        }
    
    def __repr__(self):
        return f'<Application user_id={self.user_id} opportunity_id={self.opportunity_id} status={self.status}>'


class Notification(db.Model):
    """Model for user notifications."""
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    # Notification content
    title = Column(String(256))
    message = Column(Text)
    link = Column(String(512), nullable=True)
    
    # Notification metadata
    type = Column(String(32))  # opportunity, application, system, etc.
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert notification to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'link': self.link,
            'type': self.type,
            'read': self.read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<Notification user_id={self.user_id} type={self.type}>'


class Engine(db.Model):
    """Model for opportunity engines (scrapers)."""
    __tablename__ = 'engines'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(64), unique=True)
    description = Column(Text, nullable=True)
    
    # Engine configuration
    type = Column(String(32))  # region, category, both
    region = Column(String(64), nullable=True)
    category = Column(String(64), nullable=True)
    url_pattern = Column(String(512), nullable=True)
    
    # Engine status
    active = Column(Boolean, default=True)
    schedule = Column(String(64), default='daily')  # daily, weekly, monthly, custom
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    opportunities_found = Column(Integer, default=0)
    opportunities_matched = Column(Integer, default=0)
    
    # Access control
    tier_access = Column(String(32), default='essentials')  # minimum tier required to access
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert engine to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'region': self.region,
            'category': self.category,
            'active': self.active,
            'schedule': self.schedule,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'opportunities_found': self.opportunities_found,
            'opportunities_matched': self.opportunities_matched,
            'tier_access': self.tier_access,
        }
    
    def __repr__(self):
        return f'<Engine {self.name}>'


class ApiKey(db.Model):
    """Model for API keys."""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    key = Column(String(64), unique=True)
    name = Column(String(128))
    
    # Key configuration
    scope = Column(String(256), default='read')  # read, write, admin
    
    # Key status
    active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=100)  # requests per day
    
    # Usage tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    
    # Relationship to user
    user = relationship('User', backref=backref('api_keys', lazy='dynamic'))
    
    def to_dict(self):
        """Convert API key to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key[:8] + '*****',  # Only show prefix for security
            'scope': self.scope,
            'active': self.active,
            'rate_limit': self.rate_limit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'usage_count': self.usage_count,
        }
    
    def __repr__(self):
        return f'<ApiKey name={self.name}>'


class SystemConfig(db.Model):
    """Model for system configuration settings."""
    __tablename__ = 'system_config'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True)
    value = Column(Text, nullable=True)
    type = Column(String(32), default='string')  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    
    # Configuration metadata
    category = Column(String(64), default='general')
    secret = Column(Boolean, default=False)
    editable = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_value(self):
        """Get the typed value of the configuration."""
        if not self.value:
            return None
        
        if self.type == 'int':
            return int(self.value)
        elif self.type == 'float':
            return float(self.value)
        elif self.type == 'bool':
            return self.value.lower() in ('true', 'yes', '1', 'on')
        elif self.type == 'json':
            try:
                return json.loads(self.value)
            except:
                return {}
        else:
            return self.value
    
    def set_value(self, value):
        """Set the value, converting to string if needed."""
        if value is None:
            self.value = None
        elif self.type == 'json':
            self.value = json.dumps(value)
        else:
            self.value = str(value)
    
    def to_dict(self):
        """Convert configuration to dictionary for API responses."""
        return {
            'key': self.key,
            'value': None if self.secret else self.get_value(),
            'type': self.type,
            'description': self.description,
            'category': self.category,
            'secret': self.secret,
            'editable': self.editable,
        }
    
    def __repr__(self):
        return f'<SystemConfig {self.key}>'