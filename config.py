# config.py - Configuration for Proletto's Multi-Headed Dragon

import os
from datetime import timedelta

# Basic application config
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dragon-dev-key-CHANGE-IN-PRODUCTION')
DEBUG = os.environ.get('FLASK_ENV') == 'development'
TESTING = False
JSON_SORT_KEYS = False  # Keep JSON keys in their original order

# Cache configuration
CACHE_TYPE = os.environ.get('CACHE_TYPE', 'SimpleCache')
if CACHE_TYPE == 'RedisCache':
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = 3600  # 1 hour default timeout
else:
    CACHE_SIMPLE_MAX_SIZE = 1000  # For SimpleCache

# Database configuration - use from environment
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# Scheduler configuration
SCHEDULER_API_ENABLED = True
SCHEDULER_JOBS = [
    {
        'id': 'core_scraper',
        'func': 'dragon_core:scrape_all_sites',
        'trigger': 'interval',
        'minutes': 30,
        'max_instances': 1
    },
    {
        'id': 'maintenance',
        'func': 'maintenance.bot:run_maintenance',
        'trigger': 'interval',
        'minutes': 15,
        'max_instances': 1
    },
    {
        'id': 'daily_snapshot',
        'func': lambda: 'dragon_core:write_snapshot(dragon_core:load_from_db() or dragon_core:load_snapshot())',
        'trigger': 'cron',
        'hour': 0,
        'max_instances': 1
    }
]

# Scrapers configuration
SCRAPERS = {
    'all_scrapers_enabled': True,
    'scrapers': [
        {
            'name': 'instagram_ads',
            'module': 'scrapers.instagram_ads',
            'function': 'run_instagram_scraper',
            'interval_hours': 1,
            'enabled': True
        },
        {
            'name': 'grants',
            'module': 'scrapers.grants',
            'function': 'run_scraper',
            'interval_hours': 2,
            'enabled': True
        },
        {
            'name': 'residencies',
            'module': 'scrapers.residencies',
            'function': 'run_scraper',
            'interval_hours': 3,
            'enabled': True
        },
        {
            'name': 'exhibitions',
            'module': 'scrapers.exhibitions',
            'function': 'run_scraper',
            'interval_hours': 4,
            'enabled': True
        }
    ]
}

# Maintenance bot configuration
MAINTENANCE_CONFIG = {
    'enabled': True,
    'check_intervals': {
        'cache': 15,         # minutes
        'database': 30,      # minutes
        'opportunity_count': 60,  # minutes
        'api_health': 5      # minutes
    },
    'alert_thresholds': {
        'opportunity_count_min': 50,   # Alert if fewer than 50 opportunities
        'cache_hit_rate_min': 0.7,     # Alert if cache hit rate drops below 70%
        'database_connection_timeout': 5,  # seconds
        'api_response_timeout': 10     # seconds
    }
}

# Snapshot configuration
SNAPSHOT_CONFIG = {
    'path': 'data/snapshot.json',
    'backup_path': 'data/snapshot_backup.json',
    'max_backups': 5,
    'min_size': 10  # Minimum number of items for a valid snapshot
}

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/dragon.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'file']
    }
}