#!/usr/bin/env python3

"""
Test Stripe Configuration

This script tests the Stripe configuration to ensure that we have the necessary
environment variables set up for the new membership tiers.
"""

import os
import json

def test_stripe_configuration():
    """Test the Stripe configuration."""
    print("Testing Stripe configuration...")
    
    # Check if the Stripe secret key is set
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    print(f"Stripe secret key configured: {bool(stripe_key)}")
    if stripe_key:
        # Don't print the actual key, just the prefix to confirm it's valid
        print(f"Stripe key prefix: {stripe_key[:7]}...")
    
    # Check price IDs for each plan
    plans = {
        'ESSENTIALS': os.environ.get('STRIPE_PRICE_ESSENTIALS'),
        'INSIDER': os.environ.get('STRIPE_PRICE_INSIDER'),
        'GALLERY': os.environ.get('STRIPE_PRICE_GALLERY'),
        'PAYPERPOST': os.environ.get('STRIPE_PRICE_PAYPERPOST'),
        
        # Legacy plan support
        'SUPPORTER': os.environ.get('STRIPE_PRICE_SUPPORTER'),
        'PREMIUM': os.environ.get('STRIPE_PRICE_PREMIUM'),
        'PRICE_ID': os.environ.get('STRIPE_PRICE_ID')
    }
    
    print("\nPlan price IDs:")
    for plan, price_id in plans.items():
        print(f"  {plan}: {'✅ Configured' if price_id else '❌ Missing'}")
    
    if all(price_id for plan, price_id in plans.items() if plan in ['ESSENTIALS', 'INSIDER', 'GALLERY', 'PAYPERPOST']):
        print("\n✅ All new plan price IDs are configured.")
    else:
        print("\n❌ Some new plan price IDs are missing.")
        print("\nYou need to set up the following environment variables:")
        for plan in ['ESSENTIALS', 'INSIDER', 'GALLERY', 'PAYPERPOST']:
            if not plans.get(plan):
                print(f"  - STRIPE_PRICE_{plan}")
    
    print("\nStripe documentation:")
    print("1. Create products and prices in the Stripe dashboard: https://dashboard.stripe.com/products")
    print("2. Copy the price IDs (starting with 'price_') and set them as environment variables")
    print("3. Restart the application to apply the changes")

if __name__ == "__main__":
    test_stripe_configuration()