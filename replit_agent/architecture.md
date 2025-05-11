# Proletto Architecture

## 1. Overview

Proletto is an AI-powered platform for visual artists to discover and apply for relevant opportunities such as grants, residencies, exhibitions, and public commissions. The platform leverages AI to match artists with opportunities based on their profiles and portfolios, provides workspace functionality for artist-client interactions, and offers portfolio optimization tools.

The system follows a multi-tier architecture consisting of:
- Flask-based web application backend
- HTML/CSS/JavaScript frontend
- PostgreSQL database for data persistence
- AI integration via OpenAI API
- Various external service integrations (Google, Stripe, SendGrid)

## 2. System Architecture

### 2.1. High-Level Architecture

Proletto employs a client-server architecture with the following main components:

1. **Web Application**: A Flask-based web application serving HTML templates with embedded JavaScript
2. **API Backend**: A separate Flask API service running on a different port (5001) for data operations
3. **Bot Scheduler**: A background process that periodically scrapes art opportunities from the web
4. **Database**: PostgreSQL database for storing user data, opportunities, and application tracking
5. **External Services**: Integrations with OpenAI, Google Drive, Google OAuth, Stripe, and SendGrid

The system is designed to run on Replit, with multiple components orchestrated through Replit's workflow system.

### 2.2. Component Diagram

```
┌─────────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│                     │     │                     │     │                    │
│  Web Application    │────▶│  API Backend        │────▶│  Database          │
│  (Flask - Port 3000)│     │  (Flask - Port 5001)│     │  (PostgreSQL)      │
│                     │◀────│                     │◀────│                    │
└─────────────────────┘     └─────────────────────┘     └────────────────────┘
         │                             │                          ▲
         │                             │                          │
         ▼                             ▼                          │
┌─────────────────────┐     ┌─────────────────────┐              │
│                     │     │                     │              │
│  Frontend Templates │     │  External Services  │              │
│  (HTML/CSS/JS)      │     │  (OAuth, Stripe,    │              │
│                     │     │   OpenAI, etc.)     │              │
└─────────────────────┘     └─────────────────────┘              │
                                      ▲                          │
                                      │                          │
                                      ▼                          │
                            ┌─────────────────────┐              │
                            │                     │              │
                            │  Bot Scheduler      │──────────────┘
                            │  (Opportunity       │
                            │   Scraper)          │
                            └─────────────────────┘
```

## 3. Key Components

### 3.1. Backend Application (main.py)

The main Flask application handles web page rendering, user authentication, and serves as the central coordination point for the system. It initializes the database connection, authentication systems, and registers various blueprints for different functional areas.

**Key features:**
- User authentication (email/password and Google OAuth)
- Template rendering for web pages
- Session management
- Database connection initialization
- Blueprint registration for modular functionality

### 3.2. API Backend (api.py)

A separate Flask application running on port 5001 that provides JSON API endpoints for data operations. This separation allows for better scaling and enables the frontend to interact with data services independently.

**Key features:**
- RESTful API endpoints
- JWT authentication for secure access
- CORS support for cross-domain requests
- Rate limiting for API protection
- Portfolio optimization endpoints

### 3.3. Bot Scheduler (bot_scheduler.py)

A background process that schedules and executes the opportunity scraping bots at regular intervals. It maintains state between runs, handles errors gracefully, and ensures opportunities are regularly refreshed.

**Key features:**
- Scheduled execution of scraper bots
- Error handling and retry mechanisms
- State persistence across runs
- Logging of bot activities

### 3.4. Opportunity Scrapers

Multiple specialized scraper engines that collect art opportunities from various sources. The system includes different engines for different geographic regions and opportunity types.

**Key features:**
- Specialized scraping for different sites
- Throttling to prevent overloading source websites
- Data cleaning and normalization
- Integration with Google Drive for storage

### 3.5. Database Models (models.py)

SQLAlchemy models defining the database schema, including User, Workspace, Project, Task, and other entities.

**Key entities:**
- **User**: Core user information with authentication and profile data
- **Workspace**: Collaborative spaces for artist-client interactions
- **Project**: Projects within workspaces
- **Task**: Tasks within projects
- **Message**: Communication between users

### 3.6. Authentication System

Multi-strategy authentication system supporting both traditional email/password login and Google OAuth. JWT tokens are used for API authentication.

**Key features:**
- Email/password authentication with password hashing
- Google OAuth integration
- JWT token generation and verification
- Role-based access control

### 3.7. AI Integration

Integration with OpenAI's API for various AI-powered features:

**Key features:**
- Portfolio analysis and optimization
- Opportunity matching based on artist profiles
- Application form auto-filling assistance
- Personalized suggestions

## 4. Data Flow

### 4.1. User Registration and Authentication

1. User registers via email/password or Google OAuth
2. Authentication credentials are verified
3. Session is created for web application
4. JWT tokens are issued for API access
5. User profile is stored in the database

### 4.2. Opportunity Discovery

1. Bot scheduler triggers scrapers at regular intervals
2. Scrapers collect opportunities from various sources
3. Opportunities are stored in the database and/or Google Drive
4. API endpoints expose opportunities to the frontend
5. AI matching suggests relevant opportunities to users based on their profiles

### 4.3. Portfolio Management

1. Users upload portfolio items
2. AI analyzes portfolio for strengths and weaknesses
3. System provides optimization suggestions
4. Portfolio is matched against available opportunities
5. Portfolio data is stored in database and/or Google Drive

### 4.4. Application Process

1. User selects an opportunity to apply for
2. System assists in filling application forms
3. User submits application
4. Application is tracked for status updates
5. Application data is stored for future reference

## 5. External Dependencies

### 5.1. Authentication Services

- **Google OAuth**: For social login functionality
- **JWT**: For secure API authentication

### 5.2. Payment Processing

- **Stripe**: For subscription billing (supporter and premium tiers)

### 5.3. Email Services

- **SendGrid**: For transactional emails

### 5.4. AI Services

- **OpenAI API**: For AI-powered features like portfolio optimization and opportunity matching

### 5.5. Storage Services

- **Google Drive API**: For storing opportunities and user portfolios

## 6. Deployment Strategy

### 6.1. Hosting Environment

Proletto is deployed on Replit, a cloud-based development and hosting platform. The deployment leverages Replit's workflow system to orchestrate multiple components.

### 6.2. Domain Architecture

The platform uses a multi-domain architecture:
- **www.myproletto.com**: Main website
- **app.myproletto.com**: Core application
- **dashboard.myproletto.com**: User dashboards
- **digest.myproletto.com**: Weekly digests
- **api.myproletto.com**: Backend API (Replit)
- **assets.myproletto.com**: Static assets (CDN)
- **status.myproletto.com**: System status
- **payments.myproletto.com**: Payment processing (Stripe)

### 6.3. Deployment Process

1. Code is developed and tested in the Replit environment
2. The deployment script (deploy.py) prepares the environment
3. Replit's workflow system starts the various components:
   - Main Flask application on port 3000
   - API backend on port 5001
   - Bot scheduler for opportunity scraping
4. Services are configured with appropriate environment variables

### 6.4. Environment Configuration

The application uses environment variables for configuration, including:
- Database connection strings
- API keys for external services
- Authentication credentials
- Feature flags

## 7. Security Considerations

### 7.1. Authentication Security

- Password hashing for email/password authentication
- JWT with appropriate expiration for API access
- OAuth for delegated authentication to Google

### 7.2. API Security

- Rate limiting to prevent abuse
- CORS configuration for allowed origins
- JWT validation for protected endpoints

### 7.3. Data Security

- Google Drive integration for secure file storage
- Database connection with SSL (when available)
- Environment variables for sensitive configuration

## 8. Scalability Considerations

### 8.1. Current Limitations

- Single instance deployment on Replit
- Shared resources between components
- Limited database connection pool

### 8.2. Future Scaling Options

- Separate API backend to dedicated hosting
- Move database to managed PostgreSQL service
- Implement CDN for static assets
- Containerize components for independent scaling