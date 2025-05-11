"""
Subscription Routes for Proletto

This module provides routes for managing subscriptions and payments.
"""

import os
import logging
import datetime
import stripe
import json

from flask import render_template, request, redirect, url_for, jsonify, flash, current_app
from flask import abort
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest

from models import db, User
from models_subscription import Subscription, Payment

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

logger = logging.getLogger(__name__)

# Subscription routes

@login_required
def billing_dashboard():
    """Display the billing dashboard for the user."""
    # Fetch active subscription for the user
    subscription = Subscription.query.filter_by(
        user_id=current_user.id, active=True
    ).order_by(Subscription.created_at.desc()).first()
    
    # Fetch payment history
    payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.date.desc()).limit(10).all()
    
    # Calculate next renewal date if subscription exists
    renewal_date = None
    if subscription and subscription.current_period_end:
        renewal_date = subscription.current_period_end
    
    return render_template(
        'payments/dashboard.html',
        subscription=subscription,
        payments=payments,
        renewal_date=renewal_date
    )

@login_required
def checkout_session():
    """Create a checkout session for the user."""
    try:
        price_id = current_app.config.get('STRIPE_PRICE_ID')
        if not price_id:
            logger.error("STRIPE_PRICE_ID not configured")
            flash("Subscription configuration error. Please contact support.", "error")
            return redirect(url_for('billing_dashboard'))
        
        domain_url = 'https://' + request.host
        
        # Create customer if not exists
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.name or current_user.email
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=domain_url + url_for('checkout_success') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain_url + url_for('checkout_cancel'),
            client_reference_id=str(current_user.id),
        )
        
        return redirect(checkout_session.url)
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        flash("There was an error processing your payment. Please try again.", "error")
        return redirect(url_for('billing_dashboard'))
    
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}")
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('billing_dashboard'))

@login_required
def checkout_success():
    """Handle successful checkout."""
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect(url_for('billing_dashboard'))
    
    try:
        # Retrieve the session to verify it belongs to this user
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if str(checkout_session.client_reference_id) != str(current_user.id):
            flash("Invalid session ID", "error")
            return redirect(url_for('billing_dashboard'))
        
        # Show success page
        return render_template('payments/success.html')
    except Exception as e:
        logger.error(f"Error on checkout success: {str(e)}")
        flash("There was an error verifying your payment. If you were charged, please contact support.", "error")
        return redirect(url_for('billing_dashboard'))

@login_required
def checkout_cancel():
    """Handle canceled checkout."""
    return render_template('payments/cancel.html')

def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    if not sig_header or not endpoint_secret:
        logger.warning("Missing signature header or endpoint secret")
        return jsonify({'status': 'missing signature'}), 400
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        logger.warning(f"Invalid payload: {str(e)}")
        return jsonify({'status': 'invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.warning(f"Invalid signature: {str(e)}")
        return jsonify({'status': 'invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        # Get the session
        session = event['data']['object']
        handle_checkout_session_completed(session)
    elif event['type'] == 'invoice.paid':
        # Handle successful payment
        invoice = event['data']['object']
        handle_invoice_paid(invoice)
    elif event['type'] == 'invoice.payment_failed':
        # Handle failed payment
        invoice = event['data']['object']
        handle_invoice_payment_failed(invoice)
    elif event['type'] == 'customer.subscription.updated':
        # Handle subscription updates
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    elif event['type'] == 'customer.subscription.deleted':
        # Handle subscription cancellation
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    return jsonify({'status': 'success'})

def handle_checkout_session_completed(session):
    """Process a successful checkout session."""
    try:
        user_id = int(session.get('client_reference_id'))
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"User not found for ID: {user_id}")
            return
        
        # Update user's subscription information
        user.membership_level = 'premium'
        user.stripe_subscription_id = session.get('subscription')
        
        # Create or update subscription record
        subscription = Subscription.query.filter_by(
            user_id=user.id,
            stripe_subscription_id=session.get('subscription')
        ).first()
        
        if not subscription:
            # Retrieve subscription details from Stripe
            stripe_sub = stripe.Subscription.retrieve(session.get('subscription'))
            
            subscription = Subscription(
                user_id=user.id,
                plan_id=stripe_sub.items.data[0].price.id,
                stripe_customer_id=session.get('customer'),
                stripe_subscription_id=session.get('subscription'),
                active=True,
                current_period_start=datetime.datetime.fromtimestamp(stripe_sub.current_period_start),
                current_period_end=datetime.datetime.fromtimestamp(stripe_sub.current_period_end),
                created_at=datetime.datetime.utcnow()
            )
            db.session.add(subscription)
        
        # Set user subscription dates
        user.subscription_start_date = datetime.datetime.utcnow()
        user.subscription_end_date = subscription.current_period_end
        
        db.session.commit()
        logger.info(f"Subscription created for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error handling checkout session: {str(e)}")
        db.session.rollback()

def handle_invoice_paid(invoice):
    """Process a paid invoice."""
    try:
        # Find the customer
        customer_id = invoice.get('customer')
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return
        
        # Record the payment
        payment = Payment(
            user_id=user.id,
            subscription_id=Subscription.query.filter_by(
                user_id=user.id,
                active=True
            ).first().id if Subscription.query.filter_by(user_id=user.id, active=True).first() else None,
            stripe_invoice_id=invoice.get('id'),
            stripe_payment_intent_id=invoice.get('payment_intent'),
            amount=invoice.get('amount_paid') / 100.0,  # Convert cents to dollars
            date=datetime.datetime.fromtimestamp(invoice.get('created')),
            status='paid',
            created_at=datetime.datetime.utcnow()
        )
        
        db.session.add(payment)
        db.session.commit()
        logger.info(f"Payment recorded for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error handling invoice paid: {str(e)}")
        db.session.rollback()

def handle_invoice_payment_failed(invoice):
    """Process a failed invoice payment."""
    try:
        # Find the customer
        customer_id = invoice.get('customer')
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return
        
        # Record the failed payment
        payment = Payment(
            user_id=user.id,
            subscription_id=Subscription.query.filter_by(
                user_id=user.id,
                active=True
            ).first().id if Subscription.query.filter_by(user_id=user.id, active=True).first() else None,
            stripe_invoice_id=invoice.get('id'),
            stripe_payment_intent_id=invoice.get('payment_intent'),
            amount=invoice.get('amount_due') / 100.0,  # Convert cents to dollars
            date=datetime.datetime.fromtimestamp(invoice.get('created')),
            status='failed',
            created_at=datetime.datetime.utcnow()
        )
        
        db.session.add(payment)
        db.session.commit()
        logger.info(f"Failed payment recorded for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error handling invoice payment failed: {str(e)}")
        db.session.rollback()

def handle_subscription_updated(subscription):
    """Process a subscription update."""
    try:
        # Find the customer
        customer_id = subscription.get('customer')
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return
        
        # Update subscription record
        sub_record = Subscription.query.filter_by(
            user_id=user.id,
            stripe_subscription_id=subscription.get('id')
        ).first()
        
        if not sub_record:
            logger.error(f"Subscription record not found for user {user.id}")
            return
        
        # Update subscription details
        sub_record.active = subscription.get('status') == 'active'
        sub_record.current_period_start = datetime.datetime.fromtimestamp(subscription.get('current_period_start'))
        sub_record.current_period_end = datetime.datetime.fromtimestamp(subscription.get('current_period_end'))
        sub_record.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        
        if subscription.get('canceled_at'):
            sub_record.canceled_at = datetime.datetime.fromtimestamp(subscription.get('canceled_at'))
        
        # Update user subscription dates
        user.subscription_end_date = sub_record.current_period_end
        
        # Update membership level based on subscription status
        if not sub_record.active:
            user.membership_level = 'free'
        
        db.session.commit()
        logger.info(f"Subscription updated for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription update: {str(e)}")
        db.session.rollback()

def handle_subscription_deleted(subscription):
    """Process a subscription deletion."""
    try:
        # Find the customer
        customer_id = subscription.get('customer')
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if not user:
            logger.error(f"User not found for customer: {customer_id}")
            return
        
        # Update subscription record
        sub_record = Subscription.query.filter_by(
            user_id=user.id,
            stripe_subscription_id=subscription.get('id')
        ).first()
        
        if not sub_record:
            logger.error(f"Subscription record not found for user {user.id}")
            return
        
        # Update subscription details
        sub_record.active = False
        sub_record.canceled_at = datetime.datetime.fromtimestamp(subscription.get('canceled_at')) if subscription.get('canceled_at') else datetime.datetime.utcnow()
        
        # Update user membership level
        user.membership_level = 'free'
        
        db.session.commit()
        logger.info(f"Subscription deleted for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {str(e)}")
        db.session.rollback()

@login_required
def update_card():
    """Update the user's payment method."""
    try:
        payment_method_id = request.json.get('payment_method')
        if not payment_method_id:
            return jsonify({'success': False, 'error': 'No payment method provided'}), 400
        
        # Get the user's subscription
        subscription = Subscription.query.filter_by(
            user_id=current_user.id,
            active=True
        ).first()
        
        if not subscription or not subscription.stripe_subscription_id:
            return jsonify({'success': False, 'error': 'No active subscription found'}), 400
        
        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            payment_method_id,
            customer=current_user.stripe_customer_id
        )
        
        # Set as default payment method
        stripe.Customer.modify(
            current_user.stripe_customer_id,
            invoice_settings={
                'default_payment_method': payment_method_id
            }
        )
        
        return jsonify({'success': True})
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error updating card: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"Error updating card: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

@login_required
def cancel_subscription():
    """Cancel the user's subscription."""
    try:
        # Get the user's subscription
        subscription = Subscription.query.filter_by(
            user_id=current_user.id,
            active=True
        ).first()
        
        if not subscription or not subscription.stripe_subscription_id:
            return jsonify({'success': False, 'error': 'No active subscription found'}), 400
        
        # Cancel at period end
        stripe.Subscription.modify(
            subscription.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update local subscription record
        subscription.cancel_at_period_end = True
        db.session.commit()
        
        return jsonify({'success': True})
    
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error canceling subscription: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400
    
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500


def init_app(app):
    """Initialize subscription routes and add them to the Flask app."""
    try:
        # Register route handlers
        app.add_url_rule('/billing', 'billing_dashboard', billing_dashboard, methods=['GET'])
        app.add_url_rule('/subscription/billing', 'subscription_billing', billing_dashboard, methods=['GET'])
        app.add_url_rule('/subscription/create-checkout-session', 'create_checkout_session', checkout_session, methods=['POST'])
        app.add_url_rule('/subscription/success', 'checkout_success', checkout_success, methods=['GET'])
        app.add_url_rule('/subscription/cancel', 'checkout_cancel', checkout_cancel, methods=['GET'])
        app.add_url_rule('/subscription/webhook', 'stripe_webhook', stripe_webhook, methods=['POST'])
        app.add_url_rule('/subscription/update-card', 'update_card', update_card, methods=['POST'])
        app.add_url_rule('/subscription/cancel-subscription', 'cancel_subscription', cancel_subscription, methods=['POST'])
        
        # Configure Stripe API Key
        app.config['STRIPE_SECRET_KEY'] = stripe.api_key
        
        # Add webhook secret if available
        if endpoint_secret:
            app.config['STRIPE_WEBHOOK_SECRET'] = endpoint_secret
        
        # Add custom test route
        if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('REPLIT_ENVIRONMENT') == 'development':
            app.add_url_rule('/stripe/test', 'stripe_test', lambda: render_template(
                'payments/stripe_test.html',
                stripe_pub_key=os.environ.get('STRIPE_PUBLIC_KEY', ''),
                stripe_secret_key=bool(stripe.api_key),
                endpoint_secret=bool(endpoint_secret),
                price_id=bool(app.config.get('STRIPE_PRICE_ID'))
            ), methods=['GET'])
        
        logger.info("Subscription routes initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing subscription routes: {str(e)}")
        return False