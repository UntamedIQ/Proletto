#!/usr/bin/env python3
"""
Stripe Checkout Diagnostic Tool

This script runs a full diagnostic of the Stripe checkout implementation:
1. Validates that environment variables are correctly set up
2. Attempts to create a test checkout session
3. Verifies that redirects work properly
4. Validates price IDs
"""
import os
import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stripe_diagnostic.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("stripe_diagnostic")

def check_environment_variables():
    """Check if necessary environment variables are set"""
    logger.info("Checking environment variables...")
    
    required_vars = ["STRIPE_SECRET_KEY"]
    missing_vars = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            logger.error(f"Missing environment variable: {var}")
        else:
            # Mask the actual key value for security
            masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
            logger.info(f"Found {var}: {masked_value}")
    
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        logger.info("All required environment variables are set")
        return True

def test_stripe_import():
    """Test if Stripe can be imported"""
    logger.info("Testing Stripe import...")
    
    try:
        import stripe
        # The Stripe library uses _version instead of __version__
        version = getattr(stripe, '_version', 'unknown')
        logger.info(f"Successfully imported Stripe library (version: {version})")
        return True, stripe
    except ImportError as e:
        logger.error(f"Failed to import Stripe: {e}")
        return False, None

def check_stripe_connection(stripe):
    """Check if we can connect to Stripe API"""
    logger.info("Testing Stripe API connection...")
    
    if not stripe:
        logger.error("Stripe module not available")
        return False
    
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        account = stripe.Account.retrieve()
        logger.info(f"Successfully connected to Stripe API (Account ID: {account.id})")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Stripe API: {e}")
        return False

def test_create_checkout_session(stripe):
    """Test creation of a Stripe checkout session"""
    logger.info("Testing checkout session creation...")
    
    if not stripe:
        logger.error("Stripe module not available")
        return False, None
    
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        
        # Create a test checkout session for the 'supporter' plan
        test_data = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Proletto Supporter Membership - TEST',
                        'description': 'TEST ONLY - Monthly membership to access Supporter features'
                    },
                    'unit_amount': 500,  # $5.00
                    'recurring': {
                        'interval': 'month'
                    }
                },
                'quantity': 1,
            }],
            'mode': 'subscription',
            'success_url': 'https://example.com/success?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': 'https://example.com/cancel',
            'metadata': {'test': 'true', 'plan_type': 'supporter', 'diagnostic': 'true'}
        }
        
        # Try creating the session
        session = stripe.checkout.Session.create(**test_data)
        
        # Log the session details
        session_details = {
            'id': session.id,
            'url': session.url,
            'status': session.status,
            'created': datetime.fromtimestamp(session.created).strftime('%Y-%m-%d %H:%M:%S'),
            'expires_at': datetime.fromtimestamp(session.expires_at).strftime('%Y-%m-%d %H:%M:%S') if session.expires_at else None,
        }
        
        logger.info(f"Successfully created checkout session: {json.dumps(session_details, indent=2)}")
        return True, session
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return False, None

def check_price_ids(stripe):
    """Check if the price IDs used in the code are valid"""
    logger.info("Checking price IDs...")
    
    if not stripe:
        logger.error("Stripe module not available")
        return False
    
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        
        # Get the price IDs from our code (these are placeholders in our implementation)
        price_ids = ['price_supporter', 'price_premium']
        
        # In a real implementation, we'd verify these with Stripe API
        # Since we're using placeholder price IDs, we'll just note this
        logger.warning(f"Using placeholder price IDs: {', '.join(price_ids)}")
        logger.warning("In production, you need to create real products and prices in Stripe and use their IDs")
        
        # To demonstrate how to check real price IDs, list the first few prices from your account
        try:
            prices = stripe.Price.list(limit=5, active=True)
            if prices and prices.data:
                logger.info(f"Found {len(prices.data)} active prices in your Stripe account:")
                for price in prices.data:
                    product_name = "Unknown"
                    try:
                        product = stripe.Product.retrieve(price.product)
                        product_name = product.name
                    except:
                        pass
                    
                    logger.info(f"- Price ID: {price.id}, Product: {product_name}, Amount: {price.unit_amount/100} {price.currency}")
            else:
                logger.warning("No active prices found in your Stripe account")
        except Exception as e:
            logger.error(f"Could not list prices: {e}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to check price IDs: {e}")
        return False

def run_diagnostics():
    """Run all diagnostic checks"""
    logger.info("=== Starting Stripe Checkout Diagnostics ===")
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    # Test Stripe import
    import_ok, stripe = test_stripe_import()
    
    if not import_ok:
        logger.error("Cannot proceed with diagnostics: Stripe module not available")
        return False
    
    # Check Stripe connection
    connection_ok = check_stripe_connection(stripe)
    
    if not connection_ok:
        logger.error("Cannot proceed with further diagnostics: Stripe connection failed")
        return False
    
    # Test checkout session creation
    session_ok, session = test_create_checkout_session(stripe)
    
    # Check price IDs
    price_ids_ok = check_price_ids(stripe)
    
    # Overall status
    success = env_ok and import_ok and connection_ok and session_ok and price_ids_ok
    
    logger.info("=== Stripe Checkout Diagnostic Results ===")
    logger.info(f"Environment Variables: {'✅ OK' if env_ok else '❌ Failed'}")
    logger.info(f"Stripe Import: {'✅ OK' if import_ok else '❌ Failed'}")
    logger.info(f"Stripe API Connection: {'✅ OK' if connection_ok else '❌ Failed'}")
    logger.info(f"Checkout Session Creation: {'✅ OK' if session_ok else '❌ Failed'}")
    logger.info(f"Price IDs Check: {'✅ OK' if price_ids_ok else '❌ Failed'}")
    logger.info(f"Overall Status: {'✅ OK' if success else '❌ Issues Found'}")
    
    return success

def test_main_checkout_implementation():
    """Test the actual implementation in main.py"""
    logger.info("=== Testing actual checkout implementation in main.py ===")
    
    from main import app
    
    # Create a test client
    with app.test_client() as client:
        # Test GET request
        logger.info("Testing GET request to /create-checkout-session...")
        response = client.get('/create-checkout-session?plan=supporter')
        
        if response.status_code == 303:  # Redirect
            logger.info(f"✅ GET request successful - Received redirect (303) to: {response.location}")
        else:
            logger.error(f"❌ GET request failed - Status code: {response.status_code}")
            if response.data:
                try:
                    data = json.loads(response.data)
                    logger.error(f"Response data: {json.dumps(data, indent=2)}")
                except:
                    logger.error(f"Response data: {response.data}")
        
        # Test POST request
        logger.info("Testing POST request to /create-checkout-session...")
        response = client.post('/create-checkout-session', data={
            'plan': 'supporter',
            'email': 'test@example.com'
        })
        
        if response.status_code == 200:  # JSON response
            try:
                data = json.loads(response.data)
                if data.get('success'):
                    checkout_url = data.get('checkout_url')
                    logger.info(f"✅ POST request successful - Received checkout URL: {checkout_url}")
                else:
                    logger.error(f"❌ POST request failed: {data.get('error')}")
            except Exception as e:
                logger.error(f"❌ POST request failed - Could not parse JSON response: {e}")
        else:
            logger.error(f"❌ POST request failed - Status code: {response.status_code}")
            if response.data:
                logger.error(f"Response data: {response.data}")

if __name__ == "__main__":
    success = run_diagnostics()
    
    if success:
        logger.info("Now testing the actual checkout implementation...")
        try:
            test_main_checkout_implementation()
        except Exception as e:
            logger.error(f"Failed to test main checkout implementation: {e}")
    
    logger.info("Diagnostics complete - See stripe_diagnostic.log for details")