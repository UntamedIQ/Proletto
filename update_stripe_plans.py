"""
Update Stripe Plans Support

This script adds support for the new subscription plans in Proletto:
- Essentials ($5/mo)
- Proletto Insider ($15/mo)
- Gallery/Event ($50/mo)
- Pay-Per-Post ($10 one-time)

It modifies the create-checkout-session endpoint to handle these new plans.
Uses a blueprint-based approach to avoid route conflicts.
"""
import os
import logging
import stripe
from flask import Flask, Blueprint, request, redirect, jsonify, current_app

logger = logging.getLogger(__name__)

# Create a blueprint for stripe plan routes
stripe_plans_bp = Blueprint('stripe_plans_v3', __name__, url_prefix='/stripe-plans-v3')

# Define the helper function to get price ID for a specific plan
def get_plan_price_id(plan_name):
    """Get the Stripe Price ID for a specific plan"""
    if plan_name == 'essentials':
        return current_app.config.get('STRIPE_PRICE_ESSENTIALS')
    elif plan_name == 'insider':
        return current_app.config.get('STRIPE_PRICE_INSIDER')
    elif plan_name == 'gallery':
        return current_app.config.get('STRIPE_PRICE_GALLERY')
    elif plan_name == 'payperpost':
        return current_app.config.get('STRIPE_PRICE_PAYPERPOST')
    else:
        # Legacy plan support
        return current_app.config.get(f'STRIPE_PRICE_{plan_name.upper()}')

# Direct checkout route using the blueprint
@stripe_plans_bp.route('/direct-checkout', methods=['GET'])
def direct_checkout():
    """Direct checkout link for non-authenticated users"""
    # Get plan from request
    plan = request.args.get('plan')
    if not plan:
        return jsonify({
            'error': 'Missing plan parameter', 
            'message': 'Please specify a plan'
        }), 400
    
    # Initialize Stripe
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Get email from request (for non-authenticated users)
    email = request.args.get('email')
    
    # Set price ID based on plan
    price_id = get_plan_price_id(plan)
    
    # Check if price IDs are configured
    if not price_id:
        current_app.logger.error(f"Missing Stripe price ID for plan: {plan}")
        return jsonify({
            'error': 'Stripe price ID not configured',
            'message': f'Please set the STRIPE_PRICE_{plan.upper()} environment variable in Replit. Contact support@myproletto.com for assistance.'
        }), 500
        
    # Log the price ID being used
    current_app.logger.info(f"Using Stripe price ID: {price_id} for plan: {plan}")
    
    # Get domain from request
    domain = request.host_url.rstrip('/')
    
    try:
        checkout_options = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': price_id,
                'quantity': 1,
            }],
            'success_url': domain + '/thankyou.html?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': domain + '/membership.html',
        }
        
        # Set mode based on plan
        if plan == 'payperpost':
            checkout_options['mode'] = 'payment'
        else:
            checkout_options['mode'] = 'subscription'
        
        # Add customer email if provided
        if email:
            checkout_options['customer_email'] = email
        
        # Create Checkout Session
        checkout_session = stripe.checkout.Session.create(**checkout_options)
        
        # Handle case where checkout URL might be None
        checkout_url = checkout_session.url
        if not checkout_url:
            current_app.logger.error("Stripe returned a checkout session with no URL")
            return jsonify({'error': 'Invalid checkout session'}), 500
        return redirect(checkout_url)
            
    except Exception as e:
        current_app.logger.error(f"Stripe checkout error: {e}")
        error_message = f"Stripe checkout error: {e}. Contact support@myproletto.com for assistance."
        from urllib.parse import quote
        encoded_message = quote(error_message)
        return redirect(f'/membership.html?error=checkout_failed&message={encoded_message}')

# Diagnostic endpoint using the blueprint
@stripe_plans_bp.route('/test', methods=['GET'])
def test_plans():
    """Check if Stripe plans are properly configured"""
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    essentials_price = os.environ.get('STRIPE_PRICE_ESSENTIALS')
    insider_price = os.environ.get('STRIPE_PRICE_INSIDER')
    gallery_price = os.environ.get('STRIPE_PRICE_GALLERY')
    payperpost_price = os.environ.get('STRIPE_PRICE_PAYPERPOST')
    
    return jsonify({
        'stripe_configured': bool(stripe_key),
        'key_length': len(stripe_key) if stripe_key else 0,
        'essentials_plan_configured': bool(essentials_price),
        'insider_plan_configured': bool(insider_price),
        'gallery_plan_configured': bool(gallery_price),
        'payperpost_plan_configured': bool(payperpost_price),
        'setup_instructions': 'Please add the following environment variables in Replit Secrets:\n'
                             '1. STRIPE_SECRET_KEY - Your Stripe secret key\n'
                             '2. STRIPE_PRICE_ESSENTIALS - Stripe price ID for Essentials tier\n'
                             '3. STRIPE_PRICE_INSIDER - Stripe price ID for Proletto Insider tier\n'
                             '4. STRIPE_PRICE_GALLERY - Stripe price ID for Gallery/Event tier\n'
                             '5. STRIPE_PRICE_PAYPERPOST - Stripe price ID for Pay-Per-Post option\n'
    })
    
def update_create_checkout_session(app):
    """
    Update the subscription system to support the new plan structure
    
    Args:
        app: Flask application instance
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Add the necessary environment variables to the app config
        app.config['STRIPE_PRICE_ESSENTIALS'] = os.environ.get('STRIPE_PRICE_ESSENTIALS')
        app.config['STRIPE_PRICE_INSIDER'] = os.environ.get('STRIPE_PRICE_INSIDER')
        app.config['STRIPE_PRICE_GALLERY'] = os.environ.get('STRIPE_PRICE_GALLERY')
        app.config['STRIPE_PRICE_PAYPERPOST'] = os.environ.get('STRIPE_PRICE_PAYPERPOST')
        
        # Check if the blueprint is already registered to avoid duplicate registration
        if 'stripe_plans_v3' not in app.blueprints:
            # Register the blueprint with the app only if not already registered
            app.register_blueprint(stripe_plans_bp)
        
        logger.info("Updated Stripe plans support successfully")
        return True
    except Exception as e:
        logger.error(f"Error updating Stripe plans support: {e}")
        return False

if __name__ == "__main__":
    # This can be run standalone to update an existing Flask app
    from main import app
    update_create_checkout_session(app)
    print("✅ Stripe plans support updated successfully")