"""
Unified models module to avoid circular imports

This module imports all model definitions in the correct order to avoid 
circular dependencies between User and Subscription models.
"""

# Import base libraries
import os
import sys
import json
import uuid
import hashlib
from datetime import datetime, timedelta

# SQLAlchemy imports
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import relationship, backref
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Create a new db instance without importing from main
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Create SQLAlchemy instance with the base class
db = SQLAlchemy(model_class=Base)

# Function to initialize this module with an app
def init_app(app):
    """Initialize the database and models with the given Flask app"""
    if 'sqlalchemy' not in app.extensions:
        db.init_app(app)
    return db

# Serializer for tokens
def get_serializer(secret_key=None):
    if secret_key is None:
        secret_key = os.environ.get('FLASK_SECRET_KEY', 'default-key-for-development-only')
    return URLSafeTimedSerializer(secret_key)

# User model
class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicitly set table name for clarity
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    is_supporter = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Profile fields
    bio = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    
    # Authentication fields
    auth_type = db.Column(db.String(20), default='email')  # 'email', 'google', 'facebook', etc.
    role = db.Column(db.String(20), default='user')  # 'user', 'admin', 'bot', etc.
    last_login = db.Column(db.DateTime, nullable=True)
    
    # For email/password auth
    password_hash = db.Column(db.String(128), nullable=True)
    password_salt = db.Column(db.String(32), nullable=True)
    password_reset_token = db.Column(db.String(100), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirm_token = db.Column(db.String(100), nullable=True)
    
    # For supporter tier (payment and subscription fields)
    membership_level = db.Column(db.String(20), default='free')  # 'free', 'supporter', 'premium'
    stripe_customer_id = db.Column(db.String(120), nullable=True)
    stripe_subscription_id = db.Column(db.String(120), nullable=True)
    
    # For Supporter tier - store selected states
    _selected_states = db.Column(db.Text, nullable=True)
    
    # Subscription dates
    subscription_start_date = db.Column(db.DateTime, nullable=True)
    subscription_end_date = db.Column(db.DateTime, nullable=True)
    
    # Referral system
    referral_code = db.Column(db.String(20), unique=True, nullable=True)
    referred_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    referral_credits = db.Column(db.Integer, default=0)
    
    # Portfolio and activity tracking
    portfolio_count = db.Column(db.Integer, default=0)
    opportunity_views = db.Column(db.Integer, default=0)
    application_count = db.Column(db.Integer, default=0)
    ai_uses = db.Column(db.Integer, default=0)
    
    # Badges and gamification
    _badges = db.Column(db.Text, nullable=True)
    
    # Store user interests for AI suggestions
    _interests = db.Column(db.Text, nullable=True)
    
    # Store last AI suggestions timestamp
    last_suggestion_time = db.Column(db.DateTime, nullable=True)
    
    # Email digest preferences
    digest_enabled = db.Column(db.Boolean, default=True)
    digest_day_of_week = db.Column(db.Integer, default=0)  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    digest_failure_count = db.Column(db.Integer, default=0)  # Track consecutive failures
    last_digest_sent = db.Column(db.DateTime, nullable=True)
    
    # Relationship with subscription model is defined below after Subscription model
    
    @property
    def selected_states(self):
        """Get the selected states as a list"""
        if not self._selected_states:
            return []
        return json.loads(self._selected_states)
    
    @selected_states.setter
    def selected_states(self, states):
        """Set the selected states from a list or JSON string"""
        if isinstance(states, list):
            self._selected_states = json.dumps(states)
        elif isinstance(states, str):
            # Check if it's already a valid JSON string
            try:
                json.loads(states)
                self._selected_states = states
            except:
                # If not, assume it's a comma-separated string
                state_list = [s.strip() for s in states.split(',')]
                self._selected_states = json.dumps(state_list)
    
    def has_access_to_state(self, state_name):
        """Check if the subscriber has access to a specific state"""
        if self.membership_level == 'premium':
            return True  # Premium members have access to all states
        if self.membership_level == 'supporter':
            return state_name.lower() in [s.lower() for s in self.selected_states]
        return False  # Free members don't have access to state-specific opportunities
    
    @property
    def badges(self):
        """Get user badges as a list of dictionaries"""
        if not self._badges:
            return []
        return json.loads(self._badges)
    
    @badges.setter
    def badges(self, badge_list):
        """Set user badges from a list of dictionaries or JSON string"""
        if isinstance(badge_list, list):
            self._badges = json.dumps(badge_list)
        elif isinstance(badge_list, str):
            try:
                json.loads(badge_list)  # Validate JSON
                self._badges = badge_list
            except:
                raise ValueError("Invalid badge data format")
    
    def add_badge(self, badge_id, badge_name, badge_description, badge_icon):
        """Add a new badge to the user's collection if they don't already have it"""
        current_badges = self.badges
        
        # Check if badge already exists
        for badge in current_badges:
            if badge.get('id') == badge_id:
                return False
        
        # Add new badge
        new_badge = {
            'id': badge_id,
            'name': badge_name,
            'description': badge_description,
            'icon': badge_icon,
            'earned_at': datetime.utcnow().isoformat()
        }
        
        current_badges.append(new_badge)
        self.badges = current_badges
        return True
    
    @property
    def interests(self):
        """Get user interests as a list"""
        if not self._interests:
            return []
        return json.loads(self._interests)
    
    @interests.setter
    def interests(self, interest_list):
        """Set user interests from a list or JSON string"""
        if isinstance(interest_list, list):
            self._interests = json.dumps(interest_list)
        elif isinstance(interest_list, str):
            try:
                json.loads(interest_list)  # Validate JSON
                self._interests = interest_list
            except:
                # Assume comma-separated string
                interest_items = [i.strip() for i in interest_list.split(',')]
                self._interests = json.dumps(interest_items)
    
    def generate_referral_code(self):
        """Generate a unique referral code for the user"""
        if not self.referral_code:
            # Create a code using username (or email) and random characters
            username = self.name or self.email.split('@')[0]
            random_suffix = ''.join(str(uuid.uuid4()).split('-')[0:1])
            code = f"{username.upper()[:5]}{random_suffix[:5]}".replace(' ', '')
            
            # Ensure code is unique
            while User.query.filter_by(referral_code=code).first() is not None:
                random_suffix = ''.join(str(uuid.uuid4()).split('-')[0:1])
                code = f"{username.upper()[:5]}{random_suffix[:5]}".replace(' ', '')
            
            self.referral_code = code
        
        return self.referral_code
    
    def get_referral_count(self):
        """Get the number of successful referrals"""
        return User.query.filter_by(referred_by_id=self.id).count()
        
    def add_referral_credit(self):
        """Add a referral credit to the user's account"""
        self.referral_credits += 1
        return self.referral_credits
        
    def use_referral_credit(self):
        """Use a referral credit from the user's account"""
        if self.referral_credits > 0:
            self.referral_credits -= 1
            # Extend subscription by 30 days if user is a paid member
            if self.subscription_end_date and self.membership_level in ['supporter', 'premium']:
                if self.subscription_end_date > datetime.utcnow():
                    self.subscription_end_date += timedelta(days=30)
                else:
                    self.subscription_end_date = datetime.utcnow() + timedelta(days=30)
            return True
        return False
    
    def check_and_award_badges(self):
        """Check user's activity and award badges as appropriate"""
        badges_awarded = []
        
        # Early Adopter badge
        if self.created_at < datetime.strptime('2025-04-01', '%Y-%m-%d'):
            if self.add_badge('early_adopter', 'Early Adopter', 'Joined during our beta phase', '🚀'):
                badges_awarded.append('Early Adopter')
        
        # Community Builder badge
        if self.get_referral_count() >= 3:
            if self.add_badge('community_builder', 'Community Builder', 'Referred 3+ artists', '👥'):
                badges_awarded.append('Community Builder')
        
        # Portfolio Master badge
        if self.portfolio_count >= 10:
            if self.add_badge('portfolio_master', 'Portfolio Master', 'Uploaded 10+ portfolio pieces', '🎨'):
                badges_awarded.append('Portfolio Master')
        
        # Application Pro badge
        if self.application_count >= 20:
            if self.add_badge('application_pro', 'Application Pro', 'Applied to 20+ opportunities', '📝'):
                badges_awarded.append('Application Pro')
        
        # Premium Supporter badge
        if self.membership_level == 'premium':
            if self.add_badge('premium_supporter', 'Premium Supporter', 'Premium member of Proletto', '💎'):
                badges_awarded.append('Premium Supporter')
        
        # Opportunity Hunter badge
        if self.opportunity_views >= 50:
            if self.add_badge('opportunity_hunter', 'Opportunity Hunter', 'Viewed 50+ opportunities', '🔍'):
                badges_awarded.append('Opportunity Hunter')
        
        # AI Master badge
        if self.ai_uses >= 20:
            if self.add_badge('ai_master', 'AI Master', 'Used AI tools 20+ times', '⭐'):
                badges_awarded.append('AI Master')
        
        # Ambassador badge
        if self.get_referral_count() >= 10:
            if self.add_badge('ambassador', 'Proletto Ambassador', 'Referred 10+ artists', '🏅'):
                badges_awarded.append('Proletto Ambassador')
        
        return badges_awarded
    
    # Password management methods
    def set_password(self, password):
        """Set the password hash and salt for the user"""
        # Generate a random salt
        self.password_salt = os.urandom(16).hex()
        # Create password hash
        self.password_hash = self._hash_password(password, self.password_salt)
        # Set auth type to email
        self.auth_type = 'email'
        return True
    
    def verify_password(self, password):
        """Verify a password against the stored hash"""
        if not self.password_hash or not self.password_salt:
            return False
        
        hashed = self._hash_password(password, self.password_salt)
        return hashed == self.password_hash
    
    def _hash_password(self, password, salt):
        """Hash a password with the given salt"""
        # Use a strong hashing algorithm (SHA-256)
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # Number of iterations (higher is more secure but slower)
        )
        return key.hex()
    
    def generate_email_confirmation_token(self):
        """Generate a token for email confirmation"""
        serializer = get_serializer()
        self.email_confirm_token = serializer.dumps(self.email, salt='email-confirm')
        return self.email_confirm_token
    
    def confirm_email(self, token, expiration=86400):
        """Confirm user's email with the given token"""
        serializer = get_serializer()
        try:
            email = serializer.loads(token, salt='email-confirm', max_age=expiration)
            if email == self.email:
                self.email_confirmed = True
                self.email_confirm_token = None
                return True
        except (SignatureExpired, BadSignature):
            return False
        return False
    
    def generate_reset_token(self):
        """Generate a token for password reset"""
        serializer = get_serializer()
        token = serializer.dumps(self.email, salt='password-reset')
        self.password_reset_token = token
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        return token
    
    def verify_reset_token(self, token, expiration=86400):
        """Verify a password reset token"""
        serializer = get_serializer()
        try:
            email = serializer.loads(token, salt='password-reset', max_age=expiration)
            return email == self.email
        except (SignatureExpired, BadSignature):
            return False

    def __repr__(self):
        return f'<User {self.email} ({self.membership_level})>'

# For backward compatibility, maintain the Subscriber model as an alias to User
Subscriber = User

# Subscription model
class Subscription(db.Model):
    """Subscription model representing a user's subscription to a plan."""
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    plan_id = db.Column(db.String(120), nullable=True)  # Stripe price ID
    
    stripe_customer_id = db.Column(db.String(120), nullable=True)
    stripe_subscription_id = db.Column(db.String(120), nullable=True, unique=True)
    
    active = db.Column(db.Boolean, default=False)
    
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)
    
    cancel_at_period_end = db.Column(db.Boolean, default=False)
    canceled_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Subscription {self.id} - User {self.user_id} - Active: {self.active}>'
    
    @property
    def is_trialing(self):
        """Check if the subscription is in trial period."""
        if not self.current_period_end:
            return False
        return self.current_period_start and datetime.utcnow() < self.current_period_end and self.active

    @property
    def is_cancelled(self):
        """Check if the subscription is cancelled."""
        return self.cancel_at_period_end or bool(self.canceled_at)
    
    @property
    def status_description(self):
        """Get a human-readable description of the subscription status."""
        if not self.active:
            return "Inactive"
        if self.cancel_at_period_end:
            return "Cancelling"
        if self.is_trialing:
            return "Trial"
        return "Active"

# Payment model
class Payment(db.Model):
    """Payment model representing a payment for a subscription."""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id', ondelete='SET NULL'), nullable=True)
    
    stripe_invoice_id = db.Column(db.String(120), nullable=True, unique=True)
    stripe_payment_intent_id = db.Column(db.String(120), nullable=True, unique=True)
    
    amount = db.Column(db.Float, nullable=False, default=0.0)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, paid, failed
    
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.id} - User {self.user_id} - Amount: {self.amount} {self.currency}>'

# Now that all models are defined, set up relationships
User.subscriptions = db.relationship('Subscription', 
                               backref=db.backref('user', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

User.payments = db.relationship('Payment', 
                          backref=db.backref('user', lazy='joined'),
                          lazy='dynamic',
                          cascade='all, delete-orphan')

# Workspace Models
class Workspace(db.Model):
    """Collaborative workspace for artists and clients"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')  # active, archived, completed
    
    # Workspace can be created by an artist or a client
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    creator = db.relationship('User', foreign_keys=[creator_id], backref='owned_workspaces')
    
    # Define relationships
    projects = db.relationship('Project', backref='workspace', lazy=True, cascade="all, delete-orphan")
    members = db.relationship('WorkspaceMember', backref='workspace', lazy=True, cascade="all, delete-orphan")
    
    def add_member(self, user_id, role='viewer'):
        """Add a member to the workspace"""
        # Check if user is already a member
        existing = WorkspaceMember.query.filter_by(workspace_id=self.id, user_id=user_id).first()
        if existing:
            return existing
        
        member = WorkspaceMember(workspace_id=self.id, user_id=user_id, role=role)
        db.session.add(member)
        return member
    
    def remove_member(self, user_id):
        """Remove a member from the workspace"""
        member = WorkspaceMember.query.filter_by(workspace_id=self.id, user_id=user_id).first()
        if member:
            db.session.delete(member)
            return True
        return False
    
    def get_members(self):
        """Get all members of the workspace"""
        return WorkspaceMember.query.filter_by(workspace_id=self.id).all()

class WorkspaceMember(db.Model):
    """Association table for workspace members"""
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='viewer')  # admin, editor, viewer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='workspace_memberships')
    
    __table_args__ = (
        db.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_member'),
    )

class Project(db.Model):
    """Project within a workspace"""
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, on_hold
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)
    
    tasks = db.relationship('Task', backref='project', lazy=True, cascade="all, delete-orphan")
    files = db.relationship('ProjectFile', backref='project', lazy=True, cascade="all, delete-orphan")
    
    def add_task(self, title, description=None, assigned_to=None, due_date=None):
        """Add a task to the project"""
        task = Task(
            project_id=self.id, 
            title=title,
            description=description,
            assigned_to_id=assigned_to,
            due_date=due_date
        )
        db.session.add(task)
        return task

class Task(db.Model):
    """Task within a project"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='to_do')  # to_do, in_progress, review, completed
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id], backref='assigned_tasks')
    assigned_by = db.relationship('User', foreign_keys=[assigned_by_id], backref='created_tasks')
    comments = db.relationship('TaskComment', backref='task', lazy=True, cascade="all, delete-orphan")
    
    def complete(self):
        """Mark task as completed"""
        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = datetime.utcnow()
            return True
        return False
    
    def add_comment(self, user_id, content):
        """Add a comment to the task"""
        comment = TaskComment(task_id=self.id, user_id=user_id, content=content)
        db.session.add(comment)
        return comment

class TaskComment(db.Model):
    """Comment on a task"""
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='task_comments')

class ProjectFile(db.Model):
    """File attached to a project"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # Size in bytes
    description = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    folder_id = db.Column(db.String(50), nullable=True)  # Can be 'all', 'images', 'documents', 'other', or a custom folder ID
    
    uploader = db.relationship('User', backref='uploaded_files')

class Message(db.Model):
    """Messages between workspace members"""
    id = db.Column(db.Integer, primary_key=True)
    workspace_id = db.Column(db.Integer, db.ForeignKey('workspace.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    workspace = db.relationship('Workspace', backref='messages')
    sender = db.relationship('User', backref='sent_messages')
    
    read_receipts = db.relationship('MessageReadReceipt', backref='message', lazy=True, cascade="all, delete-orphan")

class MessageReadReceipt(db.Model):
    """Tracks when users read messages"""
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    read_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='read_receipts')
    
    __table_args__ = (
        db.UniqueConstraint('message_id', 'user_id', name='uq_message_read'),
    )

class Opportunity(db.Model):
    """Art opportunities from various sources"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(500), nullable=True)
    deadline = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(50), nullable=True)  # US state (for state-based filtering)
    category = db.Column(db.String(100), nullable=True)
    tags = db.Column(db.String(500), nullable=True)  # Comma-separated tags
    scraped_at = db.Column(db.DateTime, nullable=True)  # When this opportunity was last scraped
    engine = db.Column(db.String(100), nullable=True)  # Which scraper engine found this opportunity
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Fields for membership tier access control
    membership_level = db.Column(db.String(20), default='premium')  # 'free', 'supporter', 'premium'
    type = db.Column(db.String(50), nullable=True)  # 'social_media', 'grant', 'residency', etc.
    
    # Indexes for efficient queries
    __table_args__ = (
        db.Index('idx_opportunity_source', 'source'),
        db.Index('idx_opportunity_category', 'category'),
        db.Index('idx_opportunity_scraped_at', 'scraped_at'),
        db.Index('idx_opportunity_engine', 'engine'),
        db.Index('idx_opportunity_state', 'state'),
        db.Index('idx_opportunity_membership_level', 'membership_level'),
        db.Index('idx_opportunity_type', 'type'),
    )
    
    feedback = db.relationship('Feedback', backref='opportunity', lazy=True)
    
    def __repr__(self):
        return f'<Opportunity {self.id} - {self.title}>'
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'source': self.source,
            'location': self.location,
            'state': self.state,
            'category': self.category,
            'tags': self.tags.split(',') if self.tags else [],
            'engine': self.engine,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'membership_level': self.membership_level,
            'type': self.type
        }
        
    @classmethod
    def from_json(cls, json_data):
        """Create an Opportunity instance from JSON data"""
        opportunity = cls(
            title=json_data.get('title'),
            description=json_data.get('description'),
            url=json_data.get('url'),
            deadline=datetime.fromisoformat(json_data.get('deadline')) if json_data.get('deadline') else None,
            source=json_data.get('source'),
            location=json_data.get('location'),
            state=json_data.get('state'),
            category=json_data.get('category'),
            tags=','.join(json_data.get('tags', [])) if json_data.get('tags') else None,
            engine=json_data.get('engine'),
            scraped_at=datetime.utcnow(),
            membership_level=json_data.get('membership_level', 'premium'),
            type=json_data.get('type')
        )
        return opportunity

class Feedback(db.Model):
    """User feedback on opportunities"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunity.id'), nullable=False)
    opp_id = db.Column(db.String(64), nullable=True)  # Keep for backwards compatibility
    rating = db.Column(db.Integer, nullable=False)  # 1-5 rating scale
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='feedback')
    
    def __repr__(self):
        return f'<Feedback {self.id} - User {self.user_id} - Opp {self.opportunity_id} - Rating {self.rating}>'

class APIKey(db.Model):
    """API Key model for tracking and managing API access keys"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Hashed key for security
    key_hash = db.Column(db.String(128), nullable=False, unique=True)
    
    # First 8 characters of key for display/reference
    key_prefix = db.Column(db.String(8), nullable=False, unique=True)
    
    # Key name for user reference
    name = db.Column(db.String(100), nullable=False)
    
    # FK to user who owns this key
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Key status
    status = db.Column(db.String(20), default='active')  # active, revoked, expired
    
    # Tier/plan for this key
    plan = db.Column(db.String(20), default='free')  # free, pro, partner, admin
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    
    # Usage statistics
    request_count = db.Column(db.Integer, default=0)
    rate_limit_hits = db.Column(db.Integer, default=0)
    
    # Relationship with user
    user = db.relationship('User', backref='api_keys')
    
    @classmethod
    def generate_key(cls):
        """Generate a new random API key"""
        # Format: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # Where x is a random hex character
        key = f"pk_live_{''.join([uuid.uuid4().hex for _ in range(2)])}"
        return key
    
    @classmethod
    def hash_key(cls, key):
        """Hash an API key for secure storage"""
        return hashlib.sha256(key.encode('utf-8')).hexdigest()
    
    @classmethod
    def create_for_user(cls, user_id, name, plan='free', expires_in_days=None):
        """Create a new API key for a user"""
        # Generate a new key
        key = cls.generate_key()
        key_hash = cls.hash_key(key)
        key_prefix = key[:8]
        
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create key record
        api_key = cls(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
            user_id=user_id,
            plan=plan,
            expires_at=expires_at
        )
        
        return api_key, key
    
    def verify_key(self, key):
        """Verify if a provided key matches this record"""
        hashed = self.hash_key(key)
        return hashed == self.key_hash
    
    def is_valid(self):
        """Check if key is still valid (not expired or revoked)"""
        if self.status != 'active':
            return False
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def revoke(self):
        """Revoke this API key"""
        self.status = 'revoked'
        self.revoked_at = datetime.utcnow()
        return True
    
    def record_usage(self):
        """Record usage of this API key"""
        self.request_count += 1
        self.last_used_at = datetime.utcnow()
        return self.request_count
    
    def record_rate_limit_hit(self):
        """Record a rate limit hit"""
        self.rate_limit_hits += 1
        return self.rate_limit_hits
    
    @classmethod
    def get_by_key(cls, api_key):
        """Find an API key record by the raw API key"""
        if not api_key:
            return None
        
        # Hash the provided key
        key_hash = cls.hash_key(api_key)
        
        # Find matching key in database
        return cls.query.filter_by(key_hash=key_hash).first()
    
    def __repr__(self):
        return f"<APIKey {self.key_prefix}... ({self.plan})>"

class DigestEmail(db.Model):
    """Model to track weekly digest emails sent to users"""
    __tablename__ = 'digest_emails'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='sent')  # 'sent', 'failed', 'test'
    email_type = db.Column(db.String(50), nullable=True)  # 'weekly', 'welcome', 'special', etc.
    
    # Store metadata about the digest (like opportunities included)
    digest_metadata = db.Column(db.Text, nullable=True)
    
    # Store any errors during sending
    error = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('digest_emails', lazy='dynamic', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f"<DigestEmail {self.id} - User {self.user_id} - Type {self.email_type} - Status {self.status}>"