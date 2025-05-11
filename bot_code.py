import os
import logging
import json
import time
import requests
from datetime import datetime, timedelta

# Import Google Drive integration
try:
    from drive_integration import get_drive_service
    DRIVE_ENABLED = True
except (ImportError, Exception) as e:
    DRIVE_ENABLED = False
    logging.error(f"Google Drive integration not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger('bot_code')

# Constants for API authentication
API_BASE_URL = os.environ.get('API_URL', 'http://localhost:5001/api')
BOT_EMAIL = os.environ.get('BOT_EMAIL', 'bot@proletto.com')
BOT_PASSWORD = os.environ.get('BOT_PASSWORD', 'bot_secure_password')

# Bot user credentials have been verified with ID: 2, Role: bot, Membership Level: premium
# These credentials give the bot access to add opportunities via protected API endpoints

# Cache for API token to avoid requesting it on every call
api_token_cache = {
    'token': None,
    'expires_at': None
}

def get_api_auth_token():
    """
    Get authentication token for API access.
    Uses caching to avoid requesting a new token for every request.
    Includes retry mechanism and fallback for robust operation.
    """
    global api_token_cache
    
    # Check if we have a cached token that's still valid
    now = datetime.now()
    if api_token_cache['token'] and api_token_cache['expires_at'] and api_token_cache['expires_at'] > now:
        logger.debug("Using cached API token")
        return api_token_cache['token']
    
    # Retry mechanism parameters
    max_retries = 3
    retry_delay = 2  # seconds
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Request new token
            auth_url = f"{API_BASE_URL}/auth/login"
            logger.info(f"Attempting to obtain API token from {auth_url} (attempt {retry_count + 1}/{max_retries})")
            
            response = requests.post(
                auth_url,
                json={
                    'email': BOT_EMAIL,
                    'password': BOT_PASSWORD
                },
                headers={'Content-Type': 'application/json'},
                timeout=10  # Add timeout to prevent hanging requests
            )
            
            # Log response details for debugging
            logger.debug(f"Auth API response status: {response.status_code}")
            logger.debug(f"Auth API response headers: {response.headers}")
            
            try:
                resp_json = response.json()
                logger.debug(f"Auth API response body (partial): {str(resp_json)[:100]}...")
            except Exception as json_err:
                logger.warning(f"Failed to parse API response as JSON: {json_err}")
                logger.debug(f"Raw response text (partial): {response.text[:100]}...")
            
            if response.status_code == 200 and response.json().get('success'):
                logger.info("Successfully obtained new API token")
                token_data = response.json()
                
                # Cache the token with expiration time (default: 1 hour before actual expiry)
                api_token_cache['token'] = token_data['access_token']
                api_token_cache['expires_at'] = now + timedelta(hours=23)  # Tokens usually last 24 hours
                
                return api_token_cache['token']
            else:
                logger.warning(f"Failed to obtain API token (status {response.status_code}): {response.text}")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error obtaining API token: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            
        except Exception as e:
            logger.error(f"Unexpected error obtaining API token: {e}")
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
    
    # All retries failed - check if we have an old token to use as fallback
    # Not optimal, but better than failing completely
    if api_token_cache['token']:
        logger.warning("Using expired token as fallback after all retries failed")
        return api_token_cache['token']
            
    logger.error("All attempts to obtain API token failed")
    return None

def run():
    """
    Main function to run Proletto opportunity scraper bot.
    Run the general engine and all state-specific engines.
    """
    logger.info("Proletto Bot is running at %s", datetime.now())
    
    # Track successful runs
    success_count = 0
    total_engines = 0
    
    try:
        # Run the social media scraper first (available to all users)
        logger.info("Starting the social media scraper (free tier)")
        from proletto_engine_social import run as run_social_scraper
        total_engines += 1
        if run_social_scraper():
            success_count += 1
            logger.info("Social media opportunities scraper completed successfully")
        else:
            logger.warning("Social media opportunities scraper failed")
            
        # Run the main Proletto Engine scraper for general opportunities
        logger.info("Starting the general opportunities scraper")
        from proletto_engine_v1 import run as run_general_scraper
        total_engines += 1
        if run_general_scraper():
            success_count += 1
            logger.info("General opportunities scraper completed successfully")
        else:
            logger.warning("General opportunities scraper failed")
        
        # Import and run all state-specific scrapers
        
        # California
        try:
            logger.info("Starting the California-specific scraper")
            from proletto_engine_california import run as run_california_scraper
            total_engines += 1
            if run_california_scraper():
                success_count += 1
                logger.info("California opportunities scraper completed successfully")
            else:
                logger.warning("California opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running California scraper: {e}")
        
        # New York
        try:
            logger.info("Starting the New York-specific scraper")
            from proletto_engine_newyork import run as run_newyork_scraper
            total_engines += 1
            if run_newyork_scraper():
                success_count += 1
                logger.info("New York opportunities scraper completed successfully")
            else:
                logger.warning("New York opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running New York scraper: {e}")
        
        # Illinois
        try:
            logger.info("Starting the Illinois-specific scraper")
            from proletto_engine_illinois import run as run_illinois_scraper
            total_engines += 1
            if run_illinois_scraper():
                success_count += 1
                logger.info("Illinois opportunities scraper completed successfully")
            else:
                logger.warning("Illinois opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Illinois scraper: {e}")
        
        # Texas
        try:
            logger.info("Starting the Texas-specific scraper")
            from proletto_engine_texas import run as run_texas_scraper
            total_engines += 1
            if run_texas_scraper():
                success_count += 1
                logger.info("Texas opportunities scraper completed successfully")
            else:
                logger.warning("Texas opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Texas scraper: {e}")
            
        # Massachusetts
        try:
            logger.info("Starting the Massachusetts-specific scraper")
            from proletto_engine_massachusetts import run as run_massachusetts_scraper
            total_engines += 1
            if run_massachusetts_scraper():
                success_count += 1
                logger.info("Massachusetts opportunities scraper completed successfully")
            else:
                logger.warning("Massachusetts opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Massachusetts scraper: {e}")
            
        # Washington
        try:
            logger.info("Starting the Washington-specific scraper")
            from proletto_engine_washington import run as run_washington_scraper
            total_engines += 1
            if run_washington_scraper():
                success_count += 1
                logger.info("Washington opportunities scraper completed successfully")
            else:
                logger.warning("Washington opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Washington scraper: {e}")
            
        # Florida
        try:
            logger.info("Starting the Florida-specific scraper")
            from proletto_engine_florida import run as run_florida_scraper
            total_engines += 1
            if run_florida_scraper():
                success_count += 1
                logger.info("Florida opportunities scraper completed successfully")
            else:
                logger.warning("Florida opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Florida scraper: {e}")
            
        # Oregon
        try:
            logger.info("Starting the Oregon-specific scraper")
            from proletto_engine_oregon import run as run_oregon_scraper
            total_engines += 1
            if run_oregon_scraper():
                success_count += 1
                logger.info("Oregon opportunities scraper completed successfully")
            else:
                logger.warning("Oregon opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Oregon scraper: {e}")
            
        # Colorado
        try:
            logger.info("Starting the Colorado-specific scraper")
            from proletto_engine_colorado import run as run_colorado_scraper
            total_engines += 1
            if run_colorado_scraper():
                success_count += 1
                logger.info("Colorado opportunities scraper completed successfully")
            else:
                logger.warning("Colorado opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Colorado scraper: {e}")
            
        # Pennsylvania
        try:
            logger.info("Starting the Pennsylvania-specific scraper")
            from proletto_engine_pennsylvania import run as run_pennsylvania_scraper
            total_engines += 1
            if run_pennsylvania_scraper():
                success_count += 1
                logger.info("Pennsylvania opportunities scraper completed successfully")
            else:
                logger.warning("Pennsylvania opportunities scraper failed")
        except Exception as e:
            logger.error(f"Error running Pennsylvania scraper: {e}")
        
        # Summary of scraper successes
        logger.info(f"Completed {success_count} out of {total_engines} scrapers successfully")
        
        # If at least one scraper succeeds, consider it a success and notify
        if success_count > 0:
            # Check the latest opportunities
            notify_new_opportunities()
            
            logger.info("Proletto Bot tasks completed successfully")
            return True
        else:
            logger.error("All Proletto Engine scrapers failed")
            return False
    except Exception as e:
        logger.error("Error in Proletto Bot execution: %s", str(e))
        return False

def notify_new_opportunities():
    """
    Function to notify about new opportunities.
    In a production environment, this could send emails or update a database.
    """
    try:
        # Read the scraped opportunities
        with open('opportunities.json', 'r', encoding='utf-8') as f:
            opportunities = json.load(f)
        
        # Back up to Google Drive if enabled
        if DRIVE_ENABLED:
            try:
                drive_service = get_drive_service()
                logger.info("Backing up opportunities to Google Drive")
                file_id = drive_service.save_opportunities(opportunities)
                logger.info(f"Successfully backed up opportunities to Google Drive with ID: {file_id}")
            except Exception as e:
                logger.error(f"Failed to back up to Google Drive: {e}")
        
        # Get recent opportunities (scraped in the last run)
        current_time = datetime.utcnow()
        recent_opportunities = []
        
        for opp in opportunities:
            try:
                scraped_date = datetime.fromisoformat(opp['scraped_date'])
                # Calculate how many hours ago this was scraped
                hours_ago = (current_time - scraped_date).total_seconds() / 3600
                
                # If it was scraped less than 1 hour ago, consider it new
                if hours_ago < 1:
                    recent_opportunities.append(opp)
            except (ValueError, KeyError):
                continue
        
        if recent_opportunities:
            logger.info(f"Found {len(recent_opportunities)} new opportunities")
            
            # Log the new opportunities
            for i, opp in enumerate(recent_opportunities, 1):
                logger.info(f"New opportunity {i}: {opp['title']} - {opp['url']}")
                
                # Post to API to make real-time updates
                try:
                    # Default to local API in development
                    api_url = os.environ.get('API_URL', 'http://localhost:5001/api/opportunities/add')
                    
                    # Get authentication token for API - this uses our bot credentials with ID: 2, role: bot
                    auth_token = get_api_auth_token()
                    
                    if not auth_token:
                        logger.error("Unable to obtain authentication token - cannot post opportunity")
                        continue
                    
                    # Log authentication details (without exposing actual token)
                    logger.info(f"Using bot authentication for API access (ID: 2, role: bot)")
                    
                    # Send the opportunity to the API with authentication
                    response = requests.post(
                        api_url,
                        json=opp,
                        headers={
                            'Content-Type': 'application/json',
                            'Authorization': f'Bearer {auth_token}'
                        },
                        timeout=15  # Add timeout to prevent hanging requests
                    )
                    
                    # Log the API response for monitoring
                    if response.status_code == 200 and response.json().get('success'):
                        logger.info(f"Successfully posted opportunity to API: {opp['title']}")
                    else:
                        logger.warning(f"Failed to post opportunity to API: Status {response.status_code}, Response: {response.text}")
                except Exception as e:
                    logger.error(f"Error posting to API: {e}")
            
            # In a production environment, send these to subscribers
            # send_email_notifications(recent_opportunities)
        else:
            logger.info("No new opportunities found in this run")
        
        return True
    except Exception as e:
        logger.error(f"Error in notify_new_opportunities: {e}")
        return False

if __name__ == "__main__":
    # This allows the bot to be run directly for testing
    run()