"""
Setup Subscriptions Module for Proletto

This module initializes the subscription system and adds necessary routes to the Flask application.
Uses a blueprint-based approach to avoid circular dependencies.
"""

import os
import logging
from datetime import datetime

from flask import Blueprint, current_app, request, jsonify, redirect, url_for, render_template, flash

# Create a blueprint for subscription routes
# This avoids top-level imports of db or models
subscription_bp = Blueprint('subscription_bp', __name__, url_prefix='/subscription')

# Set up logging
logger = logging.getLogger(__name__)

# Import stripe inside functions to avoid circular imports
# Routes using blueprint pattern to avoid circular imports

@subscription_bp.route('/billing')
def billing_dashboard():
    """Display the billing dashboard page"""
    # Import inside function to avoid circular imports
    from flask_login import current_user, login_required
    import stripe
    
    # Check if user is logged in
    if not current_user.is_authenticated:
        return redirect(url_for('email_auth.login'))
    
    # Set up Stripe with API key from environment
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Get Stripe customer data if available
    customer = None
    subscription = None
    if current_user.stripe_customer_id:
        try:
            customer = stripe.Customer.retrieve(current_user.stripe_customer_id)
            
            # Get user's active subscription if any
            subscriptions = stripe.Subscription.list(
                customer=current_user.stripe_customer_id,
                status='active',
                limit=1
            )
            
            if subscriptions and subscriptions.data:
                subscription = subscriptions.data[0]
        except Exception as e:
            logger.error(f"Error retrieving Stripe customer: {str(e)}")
    
    # Render the billing dashboard template
    return render_template(
        'payments/dashboard.html',
        user=current_user,
        customer=customer,
        subscription=subscription,
        stripe_pub_key=os.environ.get('STRIPE_PUBLIC_KEY', '')
    )

@subscription_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe Checkout session for subscription signup"""
    # Import inside function to avoid circular imports
    from flask_login import current_user, login_required
    import stripe
    
    # Check if user is logged in
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Set up Stripe with API key from environment
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Get the plan from the request
    plan = request.form.get('plan')
    if not plan:
        plan = 'insider'  # Default to Insider plan if not specified
    
    # Get the price ID based on the plan
    price_id = None
    if hasattr(current_app, 'get_plan_price_id'):
        # Use the helper function from update_stripe_plans if available
        price_id = current_app.get_plan_price_id(plan)
    else:
        # Fallback to different price IDs based on plan
        if plan == 'essentials':
            price_id = current_app.config.get('STRIPE_PRICE_ESSENTIALS')
        elif plan == 'insider':
            price_id = current_app.config.get('STRIPE_PRICE_INSIDER')
        elif plan == 'gallery':
            price_id = current_app.config.get('STRIPE_PRICE_GALLERY')
        elif plan == 'payperpost':
            price_id = current_app.config.get('STRIPE_PRICE_PAYPERPOST')
        else:
            # Legacy fallback
            price_id = os.environ.get('STRIPE_PRICE_ID')
    
    if not price_id:
        logger.error(f"Stripe price ID not found for plan: {plan}")
        return jsonify({'error': 'Stripe price ID not configured'}), 500
    
    # Create a new checkout session
    try:
        # Create or get customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.username,
                metadata={
                    'user_id': current_user.id
                }
            )
            
            # Store the customer ID
            with current_app.app_context():
                # Dynamically import to avoid circular dependencies
                from models import db
                current_user.stripe_customer_id = customer.id
                db.session.commit()
        else:
            customer = stripe.Customer.retrieve(current_user.stripe_customer_id)
        
        # Determine the mode based on the plan
        mode = 'payment' if plan == 'payperpost' else 'subscription'
        
        # Create the session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode=mode,
            success_url=url_for('subscription_bp.checkout_success', _external=True),
            cancel_url=url_for('subscription_bp.checkout_cancel', _external=True),
        )
        
        # Return the session ID to redirect to Stripe
        return jsonify({'id': checkout_session.id})
    
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/success')
def checkout_success():
    """Handle successful subscription checkout"""
    # Import inside function to avoid circular imports
    from flask_login import current_user
    
    # Set a flash message for the user
    flash('Thanks for subscribing to Proletto Premium!', 'success')
    
    # Render success template
    return render_template('payments/success.html')

@subscription_bp.route('/cancel')
def checkout_cancel():
    """Handle canceled subscription checkout"""
    # Import inside function to avoid circular imports
    from flask_login import current_user
    
    # Set a flash message for the user
    flash('Your subscription checkout was canceled.', 'info')
    
    # Render cancel template
    return render_template('payments/cancel.html')

@subscription_bp.route('/update-card', methods=['POST'])
def update_card():
    """Update the user's payment method (credit card)"""
    # Import inside function to avoid circular imports
    from flask_login import current_user, login_required
    import stripe
    
    # Check if user is logged in
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Set up Stripe with API key from environment
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Get the payment method ID from the request
    data = request.get_json() or {}
    payment_method_id = data.get('payment_method_id')
    
    if not payment_method_id:
        return jsonify({'error': 'Payment method ID is required'}), 400
    
    # Check if the user has a Stripe customer ID
    if not current_user.stripe_customer_id:
        return jsonify({'error': 'No Stripe customer found for user'}), 404
    
    try:
        # Attach the payment method to the customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=current_user.stripe_customer_id,
        )
        
        # Set the payment method as the default
        stripe.Customer.modify(
            current_user.stripe_customer_id,
            invoice_settings={
                'default_payment_method': payment_method_id,
            },
        )
        
        # If the user has an active subscription, update the payment method
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status='active',
            limit=1
        )
        
        if subscriptions and subscriptions.data:
            subscription = subscriptions.data[0]
            stripe.Subscription.modify(
                subscription.id,
                default_payment_method=payment_method_id,
            )
        
        return jsonify({'success': True, 'message': 'Payment method updated successfully'})
    
    except Exception as e:
        logger.error(f"Error updating payment method: {str(e)}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/cancel-subscription', methods=['POST'])
def cancel_subscription():
    """Cancel the user's subscription"""
    # Import inside function to avoid circular imports
    from flask_login import current_user, login_required
    import stripe
    
    # Check if user is logged in
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Set up Stripe with API key from environment
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Check if the user has a Stripe customer ID
    if not current_user.stripe_customer_id:
        return jsonify({'error': 'No Stripe customer found for user'}), 404
    
    try:
        # Find the active subscription
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status='active',
            limit=1
        )
        
        if not subscriptions or not subscriptions.data:
            return jsonify({'error': 'No active subscription found'}), 404
        
        subscription = subscriptions.data[0]
        
        # Cancel the subscription at period end
        stripe.Subscription.modify(
            subscription.id,
            cancel_at_period_end=True
        )
        
        # Update the subscription status in the database
        update_subscription_status(
            user=current_user,
            active=True,  # Still active until the end of the period
            stripe_subscription_id=subscription.id,
            cancel_at_period_end=True
        )
        
        return jsonify({
            'success': True, 
            'message': 'Subscription canceled successfully',
            'ends_at': datetime.fromtimestamp(subscription.current_period_end).isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return jsonify({'error': str(e)}), 500

@subscription_bp.route('/test', methods=['GET'])
def stripe_test():
    """Test page for Stripe integration"""
    # Import inside function to avoid circular imports
    from flask import render_template, request
    import stripe
    
    # Set up Stripe with API key from environment
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    
    # Get configuration values for display
    stripe_pub_key = os.environ.get('STRIPE_PUBLIC_KEY', '')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
    price_id = os.environ.get('STRIPE_PRICE_ID', '')
    
    # Render the test page
    return render_template(
        'payments/stripe_test.html',
        stripe_secret_key=bool(stripe.api_key),
        stripe_pub_key=bool(stripe_pub_key),
        endpoint_secret=bool(endpoint_secret),
        price_id=bool(price_id),
        request=request
    )

@subscription_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    import stripe
    
    # Set up Stripe with API key from environment
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Get the webhook data
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    # Verify webhook signature and extract event data
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        logger.error(f"Invalid Stripe webhook payload: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Invalid Stripe webhook signature: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle different event types
    event_type = event['type']
    logger.info(f"Processing Stripe webhook event: {event_type}")
    
    # Handle checkout session completion
    if event_type == 'checkout.session.completed':
        session = event['data']['object']
        
        # Process the checkout session completion
        with current_app.app_context():
            # Dynamically import to avoid circular dependencies
            from models import db, User
            
            # Get customer ID from session
            customer_id = session.get('customer')
            
            # Find the user by Stripe customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            
            if user:
                # Update user's subscription status
                user.membership_level = 'premium'
                
                # Update subscription related fields
                if session.get('subscription'):
                    try:
                        # Get the subscription details
                        subscription = stripe.Subscription.retrieve(session.get('subscription'))
                        
                        # Update the user record
                        update_subscription_status(
                            user=user,
                            active=True,
                            stripe_subscription_id=subscription.id,
                            current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                            current_period_end=datetime.fromtimestamp(subscription.current_period_end)
                        )
                        
                        # Record the payment
                        if subscription.latest_invoice:
                            invoice = stripe.Invoice.retrieve(subscription.latest_invoice)
                            
                            if invoice.payment_intent:
                                payment_intent = stripe.PaymentIntent.retrieve(invoice.payment_intent)
                                
                                record_payment(
                                    user_id=user.id,
                                    amount=invoice.amount_paid / 100,  # Convert from cents to dollars
                                    stripe_invoice_id=invoice.id,
                                    stripe_payment_intent_id=payment_intent.id,
                                    date=datetime.fromtimestamp(invoice.created)
                                )
                    
                    except Exception as e:
                        logger.error(f"Error processing subscription data: {str(e)}")
            else:
                logger.error(f"User not found for Stripe customer: {customer_id}")
    
    # Handle subscription updated event
    elif event_type == 'customer.subscription.updated':
        subscription = event['data']['object']
        
        with current_app.app_context():
            # Dynamically import to avoid circular dependencies
            from models import db, User
            
            # Get customer ID from subscription
            customer_id = subscription.get('customer')
            
            # Find the user by Stripe customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            
            if user:
                # Update the subscription status
                update_subscription_status(
                    user=user,
                    active=subscription.status == 'active',
                    stripe_subscription_id=subscription.id,
                    current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                    current_period_end=datetime.fromtimestamp(subscription.current_period_end),
                    cancel_at_period_end=subscription.cancel_at_period_end
                )
            else:
                logger.error(f"User not found for Stripe customer: {customer_id}")
    
    # Handle subscription canceled/deleted event
    elif event_type == 'customer.subscription.deleted':
        subscription = event['data']['object']
        
        with current_app.app_context():
            # Dynamically import to avoid circular dependencies
            from models import db, User
            
            # Get customer ID from subscription
            customer_id = subscription.get('customer')
            
            # Find the user by Stripe customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            
            if user:
                # Update the subscription status to inactive
                update_subscription_status(
                    user=user,
                    active=False,
                    stripe_subscription_id=subscription.id,
                    current_period_end=datetime.fromtimestamp(subscription.current_period_end)
                )
                
                # Update user's membership level to free (after any grace period)
                user.membership_level = 'free'
                db.session.commit()
            else:
                logger.error(f"User not found for Stripe customer: {customer_id}")
    
    # Return success response
    return jsonify({'status': 'success'})

def init_subscription_routes(app):
    """Initialize subscription routes by registering the blueprint with the app."""
    try:
        # Configure Stripe environment variables
        stripe_secret = os.environ.get('STRIPE_SECRET_KEY')
        stripe_pub_key = os.environ.get('STRIPE_PUBLIC_KEY')
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        price_id = os.environ.get('STRIPE_PRICE_ID')
        
        if not stripe_secret:
            logger.warning("STRIPE_SECRET_KEY not found in environment. Subscription features may not work correctly.")
        
        # Add config items for Stripe
        app.config['STRIPE_PUB_KEY'] = stripe_pub_key
        app.config['STRIPE_SECRET_KEY'] = stripe_secret
        app.config['STRIPE_WEBHOOK_SECRET'] = webhook_secret
        app.config['STRIPE_PRICE_ID'] = price_id
        
        # Register the blueprint with the app
        app.register_blueprint(subscription_bp)
        
        logger.info("Subscription routes initialized successfully via blueprint.")
        return True
    except Exception as e:
        logger.error(f"Error initializing subscription system: {str(e)}")
        return False

def configure_subscription_system(app):
    """Perform any necessary configuration for the subscription system."""
    try:
        # Load essential price configuration
        stripe_secret = os.environ.get('STRIPE_SECRET_KEY')
        stripe_pub_key = os.environ.get('STRIPE_PUBLIC_KEY')
        webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        price_id = os.environ.get('STRIPE_PRICE_ID')  # Legacy price ID
        
        # Load the new plan price IDs
        essentials_price = os.environ.get('STRIPE_PRICE_ESSENTIALS')
        insider_price = os.environ.get('STRIPE_PRICE_INSIDER')
        gallery_price = os.environ.get('STRIPE_PRICE_GALLERY')
        payperpost_price = os.environ.get('STRIPE_PRICE_PAYPERPOST')
        
        if not stripe_secret:
            logger.warning("STRIPE_SECRET_KEY not found in environment. Stripe features may not work correctly.")
        
        # Add config items for Stripe
        app.config['STRIPE_PUB_KEY'] = stripe_pub_key
        app.config['STRIPE_SECRET_KEY'] = stripe_secret
        app.config['STRIPE_WEBHOOK_SECRET'] = webhook_secret
        app.config['STRIPE_PRICE_ID'] = price_id
        
        # Add new plan price IDs to the app config
        app.config['STRIPE_PRICE_ESSENTIALS'] = essentials_price
        app.config['STRIPE_PRICE_INSIDER'] = insider_price
        app.config['STRIPE_PRICE_GALLERY'] = gallery_price
        app.config['STRIPE_PRICE_PAYPERPOST'] = payperpost_price
        
        logger.info("Subscription system configured with multi-plan support")
        return True
    except Exception as e:
        logger.error(f"Error configuring subscription system: {e}")
        return False

def update_stripe_customer_id(user, stripe_customer_id):
    """Update a user's Stripe customer ID."""
    try:
        # Get db from currently running app
        from flask import current_app
        db = current_app.extensions['sqlalchemy'].db
        
        user.stripe_customer_id = stripe_customer_id
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating Stripe customer ID: {str(e)}")
        # Get db from currently running app for rollback
        from flask import current_app
        db = current_app.extensions['sqlalchemy'].db
        db.session.rollback()
        return False

def update_subscription_status(user, active=False, 
                               stripe_subscription_id=None, 
                               current_period_start=None,
                               current_period_end=None,
                               cancel_at_period_end=False):
    """Update a user's subscription status."""
    try:
        # Get db and models from currently running app
        from flask import current_app
        import importlib
        
        db = current_app.extensions['sqlalchemy'].db
        models_subscription = importlib.import_module('models_subscription')
        Subscription = models_subscription.Subscription
        
        # Find or create subscription record
        subscription = Subscription.query.filter_by(
            user_id=user.id, 
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if not subscription and stripe_subscription_id:
            subscription = Subscription(
                user_id=user.id,
                stripe_customer_id=user.stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                active=active
            )
            db.session.add(subscription)
        
        if subscription:
            subscription.active = active
            
            if current_period_start:
                subscription.current_period_start = current_period_start
            
            if current_period_end:
                subscription.current_period_end = current_period_end
                user.subscription_end_date = current_period_end
            
            subscription.cancel_at_period_end = cancel_at_period_end
            
            # Update user's membership level based on subscription status
            if active:
                user.membership_level = 'premium'  # Assume premium for now; can be made configurable
            elif not active and user.membership_level == 'premium':
                user.membership_level = 'free'
        
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating subscription status: {str(e)}")
        # Get db from currently running app for rollback
        from flask import current_app
        db = current_app.extensions['sqlalchemy'].db
        db.session.rollback()
        return False

def record_payment(user_id, amount, stripe_invoice_id=None, stripe_payment_intent_id=None,
                  status='paid', date=None, subscription_id=None):
    """Record a payment in the database."""
    try:
        # Get db and models from currently running app
        from flask import current_app
        import importlib
        
        db = current_app.extensions['sqlalchemy'].db
        models_subscription = importlib.import_module('models_subscription')
        Subscription = models_subscription.Subscription
        Payment = models_subscription.Payment
        
        # Find the subscription if not provided
        if not subscription_id and subscription_id is not None:
            subscription = Subscription.query.filter_by(
                user_id=user_id,
                active=True
            ).first()
            
            if subscription:
                subscription_id = subscription.id
        
        # Create the payment record
        payment = Payment(
            user_id=user_id,
            subscription_id=subscription_id,
            stripe_invoice_id=stripe_invoice_id,
            stripe_payment_intent_id=stripe_payment_intent_id,
            amount=amount,
            date=date,
            status=status
        )
        
        db.session.add(payment)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error recording payment: {str(e)}")
        # Get db from currently running app for rollback
        from flask import current_app
        db = current_app.extensions['sqlalchemy'].db
        db.session.rollback()
        return False