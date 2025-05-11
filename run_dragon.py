#!/usr/bin/env python3
"""
Run Dragon - Launch script for Proletto's Multi-Headed Dragon

This script serves as the entry point for deploying the Multi-Headed Dragon system,
which integrates cache management, scraper jobs, maintenance bot, and monitoring
into a single coordinated system.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('dragon.log', maxBytes=10485760, backupCount=5),  # 10MB max file size
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger("dragon")

def setup_environment():
    """Set up the environment for the dragon"""
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Set environment variables
    if 'FLASK_ENV' not in os.environ:
        os.environ['FLASK_ENV'] = 'production'
    
    # Ensure PORT is set - use 5002 since 5001 is used by the API Backend
    if 'PORT' not in os.environ:
        os.environ['PORT'] = '5002'  # Use a different port than main app and API
    
    logger.info(f"Environment prepared: PORT={os.environ['PORT']}, FLASK_ENV={os.environ['FLASK_ENV']}")

def run_dragon():
    """Run the Dragon Core application"""
    try:
        # Set up environment
        setup_environment()
        
        # Import dragon core
        from dragon_core import create_app
        app = create_app()
        
        # Get port from environment or use default
        port = int(os.environ.get('PORT', 5002))
        
        # Log startup
        logger.info(f"Starting Dragon Core on port {port}")
        
        # Determine if we're in development or production
        is_dev = os.environ.get('FLASK_ENV') == 'development'
        
        # Run the application
        if is_dev:
            # In development mode, use Flask's built-in server with hot reload
            app.run(host='0.0.0.0', port=port, debug=True)
        else:
            # In production, use a more robust server
            try:
                # Try to use Gunicorn if available
                from gunicorn.app.base import BaseApplication
                
                class GunicornApp(BaseApplication):
                    def __init__(self, app, options=None):
                        self.options = options or {}
                        self.application = app
                        super().__init__()
                        
                    def load_config(self):
                        for key, value in self.options.items():
                            if key in self.cfg.settings and value is not None:
                                self.cfg.set(key.lower(), value)
                                
                    def load(self):
                        return self.application
                
                # Configure Gunicorn
                options = {
                    'bind': f'0.0.0.0:{port}',
                    'workers': 3,
                    'accesslog': 'logs/dragon_access.log',
                    'errorlog': 'logs/dragon_error.log',
                    'timeout': 120,  # 2 minute timeout for long-running tasks
                    'preload_app': True,
                    'worker_class': 'sync'  # Use sync for simplicity
                }
                
                # Start Gunicorn
                GunicornApp(app, options).run()
                
            except ImportError:
                # Fall back to Flask's built-in server
                logger.warning("Gunicorn not available, using Flask's built-in server")
                app.run(host='0.0.0.0', port=port, debug=False)
    
    except Exception as e:
        logger.error(f"Failed to start Dragon Core: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    run_dragon()