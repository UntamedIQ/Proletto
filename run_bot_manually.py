#!/usr/bin/env python3
"""
Utility script to run the bot manually.
This can be used to test the bot or to run it outside of its scheduled times.
"""
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)  # Also log to console
    ]
)
logger = logging.getLogger('manual_run')

def main():
    logger.info("Starting manual bot execution at %s", datetime.now())
    
    try:
        # Import the bot code
        import bot_code
        
        # Run the bot
        success = bot_code.run()
        
        if success:
            logger.info("Bot execution completed successfully")
        else:
            logger.warning("Bot execution completed with warnings")
    except Exception as e:
        logger.error("Error running bot: %s", str(e))
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)