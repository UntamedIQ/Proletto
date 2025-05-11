"""
Referral System Routes for Proletto

This module provides routes for the referral system including:
- Viewing referral codes
- Generating referral QR codes
- Tracking referral stats
"""
import os
import io
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, current_app, send_file
from flask_login import login_required, current_user
from flask_jwt_extended import jwt_required, get_jwt_identity

from qr_code_generator import generate_referral_qr_code

# Create blueprint
referral_routes = Blueprint('referral_routes', __name__, url_prefix='/referral')

# Import models inside functions to avoid circular imports
def get_user_model():
    from models import User
    return User

def get_db():
    from models import db
    return db

# Web Routes
@referral_routes.route('/', methods=['GET'])
@login_required
def referral_page():
    """Referral dashboard page for logged-in users"""
    # Ensure user has a referral code
    if not current_user.referral_code:
        current_user.generate_referral_code()
        db = get_db()
        db.session.commit()
    
    # Get base URL
    base_url = request.host_url.rstrip('/')
    if 'X-Forwarded-Host' in request.headers:
        protocol = 'https'
        host = request.headers.get('X-Forwarded-Host')
        base_url = f"{protocol}://{host}"
    
    referral_url = f"{base_url}/register?ref={current_user.referral_code}"
    
    # Get referred users
    User = get_user_model()
    referred_users = User.query.filter_by(referred_by_id=current_user.id).all()
    
    return render_template(
        'referral.html', 
        referral_code=current_user.referral_code,
        referral_url=referral_url,
        referral_count=len(referred_users),
        referral_credits=current_user.referral_credits,
        referred_users=referred_users
    )

@referral_routes.route('/qr-code', methods=['GET'])
@login_required
def get_referral_qr_code():
    """Generate and return a QR code for the user's referral code"""
    # Ensure user has a referral code
    if not current_user.referral_code:
        current_user.generate_referral_code()
        db = get_db()
        db.session.commit()
    
    # Get base URL
    base_url = request.host_url.rstrip('/')
    if 'X-Forwarded-Host' in request.headers:
        protocol = 'https'
        host = request.headers.get('X-Forwarded-Host')
        base_url = f"{protocol}://{host}"
    
    # Get QR code size from query params (default to 200)
    size = request.args.get('size', 200, type=int)
    
    # Generate QR code
    qr_code_data = generate_referral_qr_code(current_user.referral_code, base_url, size)
    
    if not qr_code_data:
        return jsonify({"error": "Failed to generate QR code"}), 500
    
    # Return the QR code as an image
    return send_file(
        io.BytesIO(qr_code_data),
        mimetype='image/png'
    )

# API Routes
@referral_routes.route('/api/info', methods=['GET'])
@jwt_required()
def api_get_referral_info():
    """Get referral information for the current user via API"""
    # Get current user from JWT
    user_id = get_jwt_identity()
    User = get_user_model()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Ensure user has a referral code
    if not user.referral_code:
        user.generate_referral_code()
        db = get_db()
        db.session.commit()
    
    # Get base URL (for frontend to construct full URL)
    base_url = request.host_url.rstrip('/')
    if 'X-Forwarded-Host' in request.headers:
        protocol = 'https'
        host = request.headers.get('X-Forwarded-Host')
        base_url = f"{protocol}://{host}"
    
    # Get referred users
    referred_users = User.query.filter_by(referred_by_id=user.id).all()
    referred_users_data = [
        {
            "id": referred.id,
            "name": referred.name,
            "email": referred.email,
            "joined_at": referred.created_at.isoformat() if referred.created_at else None,
            "membership_level": referred.membership_level
        }
        for referred in referred_users
    ]
    
    return jsonify({
        "referral_code": user.referral_code,
        "referral_url": f"{base_url}/register?ref={user.referral_code}",
        "referral_count": len(referred_users),
        "referral_credits": user.referral_credits,
        "referred_users": referred_users_data
    })