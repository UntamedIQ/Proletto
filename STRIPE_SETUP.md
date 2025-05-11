# Stripe Setup for Proletto

This document describes how to set up and configure Stripe for payment processing in Proletto.

## Prerequisites

Before setting up Stripe, ensure you have the following:

1. A Stripe account (create one at [stripe.com](https://stripe.com) if needed)
2. Admin access to the Proletto application
3. The necessary environment variables configured

## Environment Variables

The following environment variables must be set for Stripe integration to work properly:

- `STRIPE_SECRET_KEY`: Your Stripe secret key (starts with `sk_`)
- `STRIPE_PUBLIC_KEY`: Your Stripe publishable key (starts with `pk_`)
- `STRIPE_WEBHOOK_SECRET`: The signing secret for your webhook endpoint (optional but recommended)
- `STRIPE_PRICE_ID`: The ID of the price object in Stripe for the subscription (e.g., `price_1OQcJrXYZ9cV4yZw6f0Xn7Wy`)

## Stripe Dashboard Setup

### 1. Create a Product and Price

1. Log in to your [Stripe Dashboard](https://dashboard.stripe.com/)
2. Navigate to **Products** in the sidebar
3. Click **Add Product**
4. Fill in the product details:
   - **Name**: Proletto Premium Subscription
   - **Description**: Premium access to Proletto's art opportunity platform
5. Under **Pricing**, set up your recurring price:
   - **Price**: $12.00 USD (or your desired price)
   - **Billing period**: Monthly
   - **Pricing behavior**: Standard pricing
6. Click **Save Product**
7. Take note of the **Price ID** (e.g., `price_1OQcJrXYZ9cV4yZw6f0Xn7Wy`) for the `STRIPE_PRICE_ID` environment variable

### 2. Set Up Webhook Endpoint

1. In your Stripe Dashboard, navigate to **Developers** > **Webhooks**
2. Click **Add Endpoint**
3. Enter your webhook URL: `https://your-domain.com/stripe-webhook` (replace with your actual domain)
4. Under **Events to send**, select the following events:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.paid`
5. Click **Add Endpoint**
6. Once created, you'll see the **Signing Secret**. Copy this value for the `STRIPE_WEBHOOK_SECRET` environment variable

## Testing the Integration

1. To test the Stripe integration, visit the test page at `/stripe/test`
2. Click "Test Checkout Flow" to start a test checkout session
3. You should be redirected to Stripe's checkout page
4. Use Stripe's test card numbers to complete the checkout:
   - Test Card Number: `4242 4242 4242 4242`
   - Expiration: Any future date
   - CVC: Any 3 digits
   - ZIP: Any 5 digits

## Subscription Management

Users can manage their subscriptions from the billing dashboard at `/billing`:

- View subscription status
- Update payment method
- Cancel subscription
- See payment history

## Troubleshooting

If you encounter issues with the Stripe integration:

1. Check that all environment variables are set correctly
2. Verify that the webhook endpoint is correctly configured in Stripe
3. Check the application logs for error messages
4. Ensure the `STRIPE_PRICE_ID` corresponds to an active price in your Stripe account

For more help, refer to the [Stripe Documentation](https://stripe.com/docs) or contact support@myproletto.com.