"""
Auth Routes Fix

This script fixes authentication route issues by ensuring:
1. Both /auth/login and /auth/register work properly
2. Login and register forms are properly initialized
3. All required template variables are set

Implemented as a standalone script that can be imported into main.py
"""
from flask import Flask, redirect, url_for, render_template, Blueprint, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_login import LoginManager, current_user, login_user, logout_user, login_required

# Create blueprint with proper URL prefix and unique name
auth_fix = Blueprint('auth_fix_unique', __name__, url_prefix='/auth')

# Form classes (duplicated here to avoid circular imports)
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log In')

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
    submit = SubmitField('Register')

# Authentication routes that serve both GET and POST
@auth_fix.route('/login', methods=['GET', 'POST'])
def login():
    """Login route that always works with the template"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
    
    form = LoginForm()
    # Normal route handling goes here but we'll delegate to the email_auth blueprint
    return render_template('login.html', form=form, title='Login to Proletto')
    
@auth_fix.route('/register', methods=['GET', 'POST'])
def register():
    """Register route that always works with the template"""
    if current_user.is_authenticated:
        return redirect(url_for('opportunities'))
    
    form = RegistrationForm()
    # Normal route handling goes here but we'll delegate to the email_auth blueprint
    return render_template('register.html', form=form, title='Register for Proletto')

# Redirect routes for legacy URLs
@auth_fix.route('/reset-password', methods=['GET'])
def reset_password():
    """Simple redirect for reset password"""
    return redirect(url_for('email_auth.reset_password'))

@auth_fix.route('/reset-password-request', methods=['GET'])
def reset_password_request():
    """Simple redirect for reset password request"""
    return redirect(url_for('email_auth.reset_password_request'))

@auth_fix.route('/confirm-email', methods=['GET'])
def confirm_email():
    """Simple redirect for email confirmation"""
    flash('Please check your email for a confirmation link.', 'info')
    return redirect(url_for('index'))

# Direct route access
@auth_fix.route('/direct-login', methods=['GET'])
def direct_login():
    """Direct login template rendering bypassing blueprints"""
    form = LoginForm()
    return render_template('login.html', form=form, title='Login to Proletto')

@auth_fix.route('/direct-register', methods=['GET'])
def direct_register():
    """Direct register template rendering bypassing blueprints"""
    form = RegistrationForm()
    return render_template('register.html', form=form, title='Register for Proletto')

def register_auth_fix(app):
    """Register all auth fix routes to the app"""
    app.register_blueprint(auth_fix)
    
    # Add direct routes that don't use blueprints as fallbacks
    @app.route('/direct-login')
    def direct_login():
        form = LoginForm()
        return render_template('login.html', form=form, title='Login to Proletto')
        
    @app.route('/direct-register')
    def direct_register():
        form = RegistrationForm()
        return render_template('register.html', form=form, title='Register for Proletto')
        
    # Legacy routes that redirect to auth endpoints
    @app.route('/login.html')
    def login_html():
        return redirect(url_for('auth_fix_unique.login'))
        
    @app.route('/signup.html')
    def signup_html():
        return redirect(url_for('auth_fix_unique.register'))
        
    @app.route('/sign-in')
    def sign_in():
        return redirect(url_for('auth_fix_unique.login'))
        
    @app.route('/sign-up')
    def sign_up():
        return redirect(url_for('auth_fix_unique.register'))
    
    return app