# Stripe Integration

Wriveted integrate with Stripe via webhooks.

## Stripe Webhooks

Stripe webhooks are used to notify Wriveted when events relating to subscriptions, customers and payments occur.

The Wriveted API includes a webhook that receives Stripe events and updates the relevant Wriveted data.


## Local Testing

To test Stripe webhooks locally, you can use [Stripe CLI](https://stripe.com/docs/stripe-cli). This allows you to send Stripe events to your local running Wriveted API.

Example of sending a customer.subscription.created event to the local API

First set up the Stripe CLI to use your Stripe API keys:

    stripe login

Then start the Stripe CLI webhook proxy:

    stripe listen --forward-to localhost:8000/v1/stripe/webhook

Note this will print out a local webhook secret. You will need to set this as the `STRIPE_WEBHOOK_SECRET` environment variable.

Then send a test event to the Stripe CLI webhook proxy:
    
    stripe trigger customer.subscription.created


## Non Production Environments


https://dashboard.stripe.com/test/webhooks

## Stripe Webhook Events


### customer.created

When a new Stripe customer is created we link to the Wriveted User.
Adding a `stripe_customer_id` to the User's `info` object.

### customer.subscription.created

When a customer subscribes to a plan, a customer.subscription.created event is sent to the webhook. 

We store the `stripe_subscription_id` on the `User.info` as well
as ensuring `is_active` is `True`.

### customer.subscription.deleted

When a customer unsubscribes from a plan, a customer.subscription.deleted event is sent to the webhook and we mark the `User.is_active` to `False`.

