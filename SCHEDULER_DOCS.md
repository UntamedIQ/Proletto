# Proletto Scheduler Documentation

## Overview

Proletto uses APScheduler for scheduled jobs including:
1. Opportunity scraping from various sources
2. Maintenance bot for system health monitoring
3. Email digest automation for personalized weekly recommendations

## Email Digest Scheduler

The Email Digest Scheduler is responsible for sending personalized weekly digest emails to Pro subscribers containing art opportunities matched to their profile and preferences.

### Key Features

- Weekly emails with personalized recommendations
- Usage of the Self-Learning Bot for recommendation generation
- Tracking of sent emails in the database
- Admin interface for monitoring and manual triggering

### Configuration

The scheduler is configured to send digest emails every Monday at 8:00 AM. This can be modified in the `init_digest_scheduler` function in `email_digest_scheduler.py`.

### Database Model

The `DigestEmail` model tracks all sent digest emails, with the following fields:
- `id`: Primary key
- `user_id`: Foreign key to the User model
- `sent_at`: Timestamp of when the email was sent
- `opportunity_count`: Number of opportunities included in the email
- `status`: Status of the email ('sent', 'failed', 'test')
- `opened_at`: Timestamp of when the email was opened (if tracked)
- `clicked_at`: Timestamp of when a link in the email was clicked (if tracked)

### Email Content

The weekly digest emails use a template defined in `email_templates.py` as `WEEKLY_DIGEST`. The template includes:
- Personalized greeting
- List of 5 personalized art opportunities
- Link to view all opportunities on the platform
- Unsubscribe link

### API Endpoints

The Email Digest Scheduler exposes the following admin API endpoints:

1. **Get Scheduler Status**  
   `GET /admin/api/digest-scheduler-status`  
   Returns the current status of the scheduler and information about scheduled jobs.

2. **Run Digest Job Immediately**  
   `GET /admin/api/run-digest-now`  
   Manually triggers the digest email job to run immediately.

3. **Send Test Digest Email**  
   `GET /admin/api/test-digest-email/<user_id>`  
   Sends a test digest email to a specific user, regardless of their subscription status.

### Process Flow

1. The scheduler runs every Monday at 8:00 AM
2. It queries the database for all Pro subscribers
3. For each subscriber, it:
   - Gets personalized recommendations from the Self-Learning Bot
   - Formats the email content using the template
   - Sends the email via the email service
   - Logs the sent email in the database
4. The scheduler logs success and failure information

### Enabling/Disabling

The Email Digest Scheduler can be enabled/disabled through the `ENABLE_SCHEDULER` environment variable. When set to "true", both the main APScheduler and the Email Digest Scheduler are enabled.

For production environments, the scheduler is automatically enabled when `REPLIT_DEPLOYMENT` is set to "true".

### Testing

To test the Email Digest Scheduler:

1. Ensure you have at least one Pro subscriber in the database
2. Use the `test_digest_email` function or API endpoint to send a test email to a specific user
3. Check the logs for any errors
4. Verify the email was received and rendered correctly