# Proletto - AI-Powered Artist Opportunity Platform

Proletto is a Flask-based web application that helps artists discover and apply for opportunities including grants, residencies, exhibitions, and public commissions.

## Key Features

- **AI-powered opportunity matching**: Automatically matches artists with relevant opportunities based on their profiles and portfolios
- **Specialized scraper engines**: Separate engines for different geographic regions and opportunity types
- **Workspace functionality**: Collaborative spaces for artist-client interactions
- **Portfolio optimization**: Tools to help artists improve their portfolios
- **Referral system**: Built-in mechanisms for community growth
- **Tiered membership model**: Controls access to specialized scraper engines
- **Automated opportunity discovery**: APScheduler-based system for continuous opportunity scraping
- **Alerting infrastructure**: Slack and email alerts for system monitoring

## Technical Stack

- **Backend**: Python/Flask web application
- **Database**: PostgreSQL
- **Authentication**: JWT and OAuth (Google)
- **Email Integration**: SendGrid for transactional emails
- **AI Processing**: OpenAI API integration

## Deployment Notes

This is a Flask web application (not a static HTML site). It includes both a main web interface and an API backend. It should be deployed with:

```bash
# Start the main web interface
python main.py

# Start the API backend (separate process)
python api.py
```

The main application binds to port 3000 by default (configured via PORT environment variable).
The API backend binds to port 5001 by default (configured via API_PORT environment variable).

### Automated Scrapers

Proletto uses an advanced scheduler system based on APScheduler to automatically run opportunity scrapers in Replit's Always-On environment. The scheduler:

- Runs in the API backend process
- Automatically activates in production environments
- Schedules scraper jobs based on membership tiers (premium, supporter, free)
- Provides failure recovery and state persistence

For detailed documentation on the scheduler system, see [SCHEDULER_DOCS.md](SCHEDULER_DOCS.md).

## Development

To run the application locally:

1. Install dependencies: `pip install -r requirements.txt`
2. Start the main application: `python main.py`
3. Start the API backend in a separate terminal: `python api.py`
4. Access the web interface at http://localhost:3000
5. The API will be available at http://localhost:5001

### Testing the Scheduler

The APScheduler implementation can be tested without affecting production:

```bash
# Test scheduler in dev mode (jobs scheduled but not executed)
python test_ap_scheduler.py

# Test scheduler in simulated production mode
python test_ap_scheduler.py --simulate-production
```

### Testing Alerts

The alerting system can be tested independently:

```bash
# Test Slack alerts
python test_slack_alerts.py

# Test all alerts (Slack and email)
python -c "from alerts import test_alerts; test_alerts()"
```

## Authentication

The application uses a combination of OAuth (Google) and email-based authentication with JWT tokens for secure access.

## Infrastructure

Proletto's infrastructure is designed as a three-part system:

1. **"Serverless" Scrapers**: APScheduler-based system running in Replit's Always-On environment
   - Automatically schedules and executes opportunity scraper engines
   - Differentiates scraper frequency based on membership tiers
   - Maintains state between application restarts
   - Implements recovery mechanisms for handling failures

2. **Alerting System**: Integrated monitoring and notification system
   - Slack alerts for critical system events
   - Email notifications for administrative issues
   - Specialized alerts for different scenarios (scraper errors, system health, API errors)

3. **Feedback System**: User feedback collection for continuous improvement
   - Feedback widget UI components on opportunity pages
   - API endpoint for capturing user feedback
   - Database model for storing and analyzing feedback
   - Infrastructure for retraining recommendation models based on user input# proletto
# Proletto
