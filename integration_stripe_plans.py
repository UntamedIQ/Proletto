"""
Integrate Stripe Plans Update

This script integrates the Stripe plans update with the main application.
It needs to be imported in main.py after the app initialization.
"""

import os
import logging
from update_stripe_plans import update_create_checkout_session

logger = logging.getLogger(__name__)

def integrate_stripe_plans_update(app):
    """Add the Stripe plans update to the Flask app"""
    try:
        # Apply the update
        success = update_create_checkout_session(app)
        
        if success:
            logger.info("✅ Successfully integrated new Stripe plan structure")
            
            # Ensure environment variables are set
            missing_vars = []
            for plan in ['ESSENTIALS', 'INSIDER', 'GALLERY', 'PAYPERPOST']:
                env_var = f'STRIPE_PRICE_{plan}'
                if not os.environ.get(env_var):
                    # Set a default for development purposes - this would be replaced in production
                    if os.environ.get('FLASK_ENV') != 'production':
                        logger.warning(f"⚠️ Setting placeholder for {env_var} in development mode")
                        os.environ[env_var] = f"price_placeholder_{plan.lower()}"
                    else:
                        missing_vars.append(env_var)
            
            if missing_vars:
                missing_list = ', '.join(missing_vars)
                logger.warning(f"⚠️ Missing Stripe price IDs: {missing_list}")
                
            # Manually register our test endpoint 
            from flask import jsonify
            @app.route('/stripe/plans/test', methods=['GET'])
            def test_stripe_plans():
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
                
            return True
        else:
            logger.error("❌ Failed to integrate new Stripe plan structure")
            return False
    except Exception as e:
        logger.error(f"❌ Error integrating Stripe plans update: {e}")
        return False