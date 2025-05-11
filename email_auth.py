"""
Email and Password Authentication for Proletto
This module provides traditional email/password authentication functionality.
"""
import json
import os
from datetime import datetime
from functools import wraps

from flask import Blueprint, redirect, request, url_for, current_app, jsonify, render_template, flash
from flask_login import login_required, login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, ValidationError
from wtforms.validators import DataRequired, Email, Length, EqualTo

# Create blueprint with the url_prefix explicitly set
email_auth = Blueprint("email_auth", __name__, url_prefix='/auth')

# Import models inside functions to avoid circular imports
def get_user_model():
    from models import User
    return User

def get_db():
    from models import db
    return db

# Form classes
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')

class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    
    def validate_email(self, email):
        User = get_user_model()
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is already registered. Please use a different one.')

class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])

class PasswordResetForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])

# Routes for API access
@email_auth.route("/register", methods=["POST"])
def api_register():
    """Register a new user via API"""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Invalid request data"}), 400
    
    # Validate required fields
    required_fields = ['email', 'password', 'name']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False, 
                "error": f"Missing required field: {field}"
            }), 400
    
    User = get_user_model()
    db = get_db()
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({
            "success": False, 
            "error": "Email already registered"
        }), 400
    
    # Create new user
    user = User(
        email=data['email'],
        name=data['name'],
        membership_level="free",
        auth_type="email",
        email_confirmed=False
    )
    
    # Set password
    user.set_password(data['password'])
    
    # Generate confirmation token
    token = user.generate_email_confirmation_token()
    
    # Track referral if provided
    if 'referral_code' in data and data['referral_code']:
        referrer = User.query.filter_by(referral_code=data['referral_code']).first()
        if referrer:
            user.referred_by_id = referrer.id
            current_app.logger.info(f"User {user.email} was referred by {referrer.email}")
    
    # Always generate a referral code for new users
    user.generate_referral_code()
    
    # Save user to database
    db.session.add(user)
    db.session.commit()
    
    # Send confirmation email
    from email_service import get_email_service
    email_service = get_email_service()
    
    # Get base URL from request
    base_url = request.host_url.rstrip('/')
    if 'X-Forwarded-Host' in request.headers:
        # Use forwarded host if available (for proxied environments)
        protocol = 'https'
        host = request.headers.get('X-Forwarded-Host')
        base_url = f"{protocol}://{host}"
    
    # Send the email
    email_sent = email_service.send_email_confirmation(user, token, base_url)
    
    if not email_sent and not email_service.is_available:
        # Log but don't reveal to user that email service is unavailable
        from main import app
        app.logger.error(f"Email confirmation could not be sent for {user.email} - email service unavailable")
    
    return jsonify({
        "success": True,
        "message": "User registered successfully. Please check your email for confirmation.",
        "user_id": user.id,
        "email": user.email,
        "name": user.name
    })

@email_auth.route("/login", methods=["POST"])
def api_login():
    """Login a user via API"""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Invalid request data"}), 400
    
    # Validate required fields
    required_fields = ['email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False, 
                "error": f"Missing required field: {field}"
            }), 400
    
    # Use Flask app context to get user
    User = get_user_model()
    from main import app
    with app.app_context():
        user = User.query.filter_by(email=data['email']).first()
        
        # Check if user exists and password is correct
        if not user or not user.verify_password(data['password']):
            return jsonify({
                "success": False, 
                "error": "Invalid email or password"
            }), 401
        
        # User exists and password is correct
        # Update last login time
        db = get_db()
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Log in user
        login_user(user, remember=data.get('remember', False))
        
        # Generate JWT tokens for API access
        try:
            # Import within function to avoid circular imports
            from flask_jwt_extended import create_access_token, create_refresh_token
            from api import app as api_app
            
            with api_app.app_context():
                access_token = create_access_token(identity=user.id)
                refresh_token = create_refresh_token(identity=user.id)
                
                return jsonify({
                    "success": True,
                    "message": "Login successful",
                    "user_id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "membership_level": user.membership_level,
                    "access_token": access_token,
                    "refresh_token": refresh_token
                })
        except Exception as e:
            # If JWT token generation fails, return successful login without tokens
            return jsonify({
                "success": True,
                "message": "Login successful (without API tokens)",
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "membership_level": user.membership_level
            })

@email_auth.route("/reset-password-request", methods=["POST"])
def api_reset_password_request():
    """Request a password reset via API"""
    data = request.json
    if not data or 'email' not in data:
        return jsonify({"success": False, "error": "Email is required"}), 400
    
    # Get user
    User = get_user_model()
    from main import app
    with app.app_context():
        user = User.query.filter_by(email=data['email']).first()
        
        # Even if user doesn't exist, don't reveal that to avoid security issues
        if not user:
            return jsonify({
                "success": True,
                "message": "If your email is registered, you will receive reset instructions."
            })
    
        # Generate reset token for user within app context
        token = user.generate_reset_token()
        db = get_db()
        db.session.commit()
        
        # Send password reset email with the token
        from email_service import get_email_service
        email_service = get_email_service()
        
        # Get base URL from request or environment
        base_url = request.host_url.rstrip('/')
        if 'X-Forwarded-Host' in request.headers:
            # Use forwarded host if available (for proxied environments)
            protocol = 'https'
            host = request.headers.get('X-Forwarded-Host')
            base_url = f"{protocol}://{host}"
        
        # Send the email
        email_sent = email_service.send_password_reset_email(user, token, base_url)
        
        if not email_sent and not email_service.is_available:
            # Log but don't reveal to user that email service is unavailable
            app.logger.error("Password reset requested but email service unavailable")
        
        return jsonify({
            "success": True,
            "message": "If your email is registered, you will receive reset instructions."
        })

@email_auth.route("/reset-password", methods=["POST"])
def api_reset_password():
    """Reset a password via API"""
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Invalid request data"}), 400
    
    # Validate required fields
    required_fields = ['token', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "success": False, 
                "error": f"Missing required field: {field}"
            }), 400
    
    # Get user from token
    User = get_user_model()
    db = get_db()
    from main import app
    
    with app.app_context():
        # Find user with this token
        user = User.query.filter_by(password_reset_token=data['token']).first()
        
        if not user:
            return jsonify({
                "success": False, 
                "error": "Invalid or expired reset token"
            }), 400
        
        # Verify token is valid and not expired
        if not user.verify_reset_token(data['token']):
            return jsonify({
                "success": False, 
                "error": "Invalid or expired reset token"
            }), 400
        
        # Reset password
        user.set_password(data['password'])
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Password reset successful. You can now log in with your new password."
    })

@email_auth.route("/confirm-email", methods=["POST"])
def api_confirm_email():
    """Confirm a user's email via API"""
    data = request.json
    if not data or 'token' not in data:
        return jsonify({"success": False, "error": "Token is required"}), 400
    
    # Find user with this token
    User = get_user_model()
    db = get_db()
    from main import app
    
    with app.app_context():
        user = User.query.filter_by(email_confirm_token=data['token']).first()
        
        if not user:
            return jsonify({
                "success": False, 
                "error": "Invalid or expired confirmation token"
            }), 400
        
        # Verify token and confirm email
        if user.confirm_email(data['token']):
            db.session.commit()
            
            # Send welcome email
            from email_service import get_email_service
            email_service = get_email_service()
            
            # Get base URL from request
            base_url = request.host_url.rstrip('/')
            if 'X-Forwarded-Host' in request.headers:
                # Use forwarded host if available (for proxied environments)
                protocol = 'https'
                host = request.headers.get('X-Forwarded-Host')
                base_url = f"{protocol}://{host}"
            
            # Send welcome email in the background (don't wait for response)
            email_service.send_welcome_email(user, base_url)
            
            # If user was referred, add a badge to the referrer
            if user.referred_by_id:
                referrer = User.query.get(user.referred_by_id)
                if referrer:
                    # Add Referrer badge if they don't have it yet
                    referrer.add_badge('referrer', 'Referrer', 'Referred a new artist to Proletto', '👋')
                    db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Email confirmed successfully. You can now log in."
            })
        else:
            return jsonify({
                "success": False, 
                "error": "Invalid or expired confirmation token"
            }), 400

# Web form routes (for traditional web forms)
@email_auth.route("/login", methods=["GET", "POST"])
def login():
    """Login page for web form"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
        
    form = LoginForm()
    if form.validate_on_submit():
        User = get_user_model()
        user = User.query.filter_by(email=form.email.data).first()
        
        if user and user.verify_password(form.password.data):
            # Update last login time
            db = get_db()
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            
            return redirect(next_page or url_for('opportunities'))
        else:
            flash('Login failed. Please check your email and password.', 'danger')
    
    return render_template('login.html', form=form, title='Login')

@email_auth.route("/register", methods=["GET", "POST"])
def register():
    """Registration page for web form - redirects to membership page"""
    # Redirect to membership page to choose a plan first
    return redirect(url_for('public_routes.membership'))
    
    # This code is preserved but not executed due to the redirect above
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        User = get_user_model()
        db = get_db()
        
        user = User(
            name=form.name.data,
            email=form.email.data,
            membership_level="free",
            auth_type="email",
            email_confirmed=False
        )
        
        # Set password
        user.set_password(form.password.data)
        
        # Generate confirmation token
        token = user.generate_email_confirmation_token()
        
        # Track referral if provided in query params
        referral_code = request.args.get('ref')
        if referral_code:
            referrer = User.query.filter_by(referral_code=referral_code).first()
            if referrer:
                user.referred_by_id = referrer.id
                current_app.logger.info(f"User {user.email} was referred by {referrer.email}")
        
        # Always generate a referral code for new users
        user.generate_referral_code()
        
        # Save user to database
        db.session.add(user)
        db.session.commit()
        
        # Send confirmation email
        from email_service import get_email_service
        email_service = get_email_service()
        
        # Get base URL from request
        base_url = request.host_url.rstrip('/')
        if 'X-Forwarded-Host' in request.headers:
            # Use forwarded host if available (for proxied environments)
            protocol = 'https'
            host = request.headers.get('X-Forwarded-Host')
            base_url = f"{protocol}://{host}"
        
        # Send the email
        email_sent = email_service.send_email_confirmation(user, token, base_url)
        
        if not email_sent and not email_service.is_available:
            # Log but don't reveal to user that email service is unavailable
            current_app.logger.error("Email confirmation could not be sent - email service unavailable")
        
        flash('Your account has been created! You will receive an email to confirm your registration.', 'success')
        return redirect(url_for('email_auth.login'))
    
    return render_template('register.html', form=form, title='Register')

@email_auth.route("/reset-password", methods=["GET", "POST"])
def reset_password_request():
    """Password reset request page for web form"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
        
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        User = get_user_model()
        user = User.query.filter_by(email=form.email.data).first()
        
        if user:
            db = get_db()
            token = user.generate_reset_token()
            db.session.commit()
            
            # Send password reset email
            from email_service import get_email_service
            email_service = get_email_service()
            
            # Get base URL from request
            base_url = request.host_url.rstrip('/')
            if 'X-Forwarded-Host' in request.headers:
                # Use forwarded host if available (for proxied environments)
                protocol = 'https'
                host = request.headers.get('X-Forwarded-Host')
                base_url = f"{protocol}://{host}"
            
            # Send the email
            email_sent = email_service.send_password_reset_email(user, token, base_url)
            
            if not email_sent and not email_service.is_available:
                # Log but don't reveal to user that email service is unavailable
                current_app.logger.error("Password reset requested but email service unavailable")
        
        flash('If your email is registered, you will receive instructions to reset your password.', 'info')
        return redirect(url_for('email_auth.login'))
    
    return render_template('reset_password_request.html', form=form, title='Reset Password')

@email_auth.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Password reset page for web form"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
        
    User = get_user_model()
    db = get_db()
    
    # Find user with this token
    user = User.query.filter_by(password_reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash('Invalid or expired reset token. Please request a new password reset.', 'danger')
        return redirect(url_for('email_auth.reset_password_request'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
        
        flash('Your password has been reset. You can now log in with your new password.', 'success')
        return redirect(url_for('email_auth.login'))
    
    return render_template('reset_password.html', form=form, title='Reset Password')

@email_auth.route("/confirm-email/<token>")
def confirm_email(token):
    """Email confirmation page"""
    User = get_user_model()
    db = get_db()
    
    user = User.query.filter_by(email_confirm_token=token).first()
    
    if not user:
        flash('Invalid or expired confirmation token.', 'danger')
        return redirect(url_for('index'))
    
    if user.confirm_email(token):
        db.session.commit()
        flash('Your email has been confirmed. You can now log in.', 'success')
    else:
        flash('Invalid or expired confirmation token.', 'danger')
    
    return redirect(url_for('email_auth.login'))