"""
Stripe Endpoint Fix

This script modifies the existing create-checkout-session endpoint to ensure
it properly supports both GET and POST methods and returns appropriate CORS headers.
"""
import os
import stripe
from flask import Flask, request, redirect, jsonify
from flask_cors import CORS

def fix_stripe_endpoints(app):
    """
    Register fixed Stripe endpoints on the given Flask app
    """
    # Ensure CORS is properly configured for Stripe endpoints
    CORS(app, resources={
        "/create-checkout-session": {"origins": "*"},
        "/stripe/*": {"origins": "*"},
        "/webhook": {"origins": "*"}
    })
    
    # Fix the create-checkout-session endpoint
    @app.route('/create-checkout-session', methods=['GET', 'POST'])
    def create_checkout_session():
        # Set API key from environment variable
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        
        # Check if API key exists
        if not stripe.api_key:
            return jsonify({
                'error': 'Stripe API key is not configured',
                'message': 'Please set the STRIPE_SECRET_KEY environment variable'
            }), 500
        
        # Get plan from request (either query param or JSON body)
        if request.method == 'POST' and request.is_json:
            data = request.get_json()
            plan = data.get('plan', 'supporter')
        else:
            plan = request.args.get('plan', 'supporter')
        
        # Set price ID based on plan - using actual Stripe product price IDs
        # These must be configured using environment variables with your actual Stripe price IDs
        if plan == 'supporter':
            price_id = os.environ.get('STRIPE_PRICE_SUPPORTER')
        else:
            price_id = os.environ.get('STRIPE_PRICE_PREMIUM')
            
        # Check if price IDs are configured
        if not price_id:
            app.logger.error(f"Missing Stripe price ID for plan: {plan}")
            return jsonify({
                'error': 'Stripe price ID not configured',
                'message': f'Please set the STRIPE_PRICE_{plan.upper()} environment variable in Replit. Contact support@myproletto.com for assistance.'
            }), 500
            
        # Log the price ID being used
        app.logger.info(f"Using Stripe price ID: {price_id} for plan: {plan}")
        
        # Get domain from request
        domain = request.host_url.rstrip('/')
        
        try:
            # Create Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=domain + '/thankyou.html?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain + '/membership.html',
            )
            
            # Return appropriate response based on request method
            if request.method == 'POST':
                return jsonify({'id': checkout_session.id})
            else:
                return redirect(checkout_session.url)
                
        except Exception as e:
            app.logger.error(f"Stripe checkout error: {e}")
            error_message = f"Stripe checkout error: {e}. Contact support@myproletto.com for assistance."
            if request.method == 'POST':
                return jsonify({'error': error_message}), 500
            else:
                from urllib.parse import quote
                encoded_message = quote(error_message)
                return redirect(f'/membership.html?error=checkout_failed&message={encoded_message}')
    
    # Add a diagnostic endpoint
    @app.route('/stripe/test', methods=['GET'])
    def test_stripe():
        """Check if Stripe is properly configured"""
        stripe_key = os.environ.get('STRIPE_SECRET_KEY')
        supporter_price = os.environ.get('STRIPE_PRICE_SUPPORTER')
        premium_price = os.environ.get('STRIPE_PRICE_PREMIUM')
        
        return jsonify({
            'stripe_configured': bool(stripe_key),
            'key_length': len(stripe_key) if stripe_key else 0,
            'supporter_price_configured': bool(supporter_price),
            'premium_price_configured': bool(premium_price),
            'setup_instructions': 'Please add the following environment variables in Replit Secrets:\n'
                                 '1. STRIPE_SECRET_KEY - Your Stripe secret key\n'
                                 '2. STRIPE_PRICE_SUPPORTER - Stripe price ID for Supporter tier\n'
                                 '3. STRIPE_PRICE_PREMIUM - Stripe price ID for Premium tier\n'
                                 'You can find these in your Stripe Dashboard under Products > Prices\n'
                                 'For assistance, contact support@myproletto.com'
        })
        
    return app