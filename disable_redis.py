#!/usr/bin/env python3
"""
Redis Disabler

This script completely disables Redis and forces the application to use SimpleCache.
It's useful when Redis authentication is persistently failing or when deploying
in environments where Redis is unnecessary or unavailable.

Usage:
    python disable_redis.py
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('redis-disabler')

def disable_redis():
    """Disable Redis by setting environment variable REDIS_DISABLED=1."""
    logger.info("=== REDIS DISABLER ===")
    
    # Check if REDIS_DISABLED is already set
    redis_disabled = os.environ.get('REDIS_DISABLED')
    if redis_disabled == '1':
        logger.info("Redis is already disabled (REDIS_DISABLED=1)")
        return True
    
    # Set REDIS_DISABLED to 1
    os.environ['REDIS_DISABLED'] = '1'
    logger.info("Redis has been disabled for the current process (REDIS_DISABLED=1)")
    
    # Write to .env file if it exists
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        redis_disabled_found = False
        with open(env_file, 'w') as f:
            for line in lines:
                if line.startswith('REDIS_DISABLED='):
                    f.write('REDIS_DISABLED=1\n')
                    redis_disabled_found = True
                else:
                    f.write(line)
            
            if not redis_disabled_found:
                f.write('REDIS_DISABLED=1\n')
        
        logger.info(f"Updated {env_file} to disable Redis")
    
    # Check if deploy.py exists and update it to disable Redis
    deploy_file = 'deploy.py'
    if os.path.exists(deploy_file):
        try:
            with open(deploy_file, 'r') as f:
                content = f.read()
            
            if 'REDIS_DISABLED' not in content:
                # Find a good place to insert REDIS_DISABLED=1
                if 'os.environ[\'FLASK_ENV\'] = \'production\'' in content:
                    content = content.replace(
                        'os.environ[\'FLASK_ENV\'] = \'production\'',
                        'os.environ[\'FLASK_ENV\'] = \'production\'\n    os.environ[\'REDIS_DISABLED\'] = \'1\'  # Force SimpleCache'
                    )
                    
                    with open(deploy_file, 'w') as f:
                        f.write(content)
                    
                    logger.info(f"Updated {deploy_file} to disable Redis during deployment")
        except Exception as e:
            logger.error(f"Failed to update {deploy_file}: {str(e)}")
    
    # Update cache_utils.py to check for REDIS_DISABLED
    cache_utils_file = 'cache_utils.py'
    if os.path.exists(cache_utils_file):
        try:
            with open(cache_utils_file, 'r') as f:
                content = f.read()
            
            if 'REDIS_DISABLED' not in content:
                # Find the init_cache function and modify it
                if 'def init_cache(app):' in content:
                    # Find where we start Redis initialization
                    init_pos = content.find('def init_cache(app):')
                    next_line_pos = content.find('\n', init_pos) + 1
                    
                    # Add REDIS_DISABLED check
                    modified_content = (
                        content[:next_line_pos] + 
                        '    # Check if Redis is explicitly disabled\n' +
                        '    if os.environ.get(\'REDIS_DISABLED\') == \'1\':\n' +
                        '        app.logger.info("Redis explicitly disabled via REDIS_DISABLED. Using SimpleCache.")\n' +
                        '        backend = {\n' +
                        '            \'type\': \'simple\',\n' +
                        '            \'client\': None,\n' +
                        '            \'error\': "Redis explicitly disabled"\n' +
                        '        }\n' +
                        '        cache = Cache(config={\n' +
                        '            \'CACHE_TYPE\': \'SimpleCache\',\n' +
                        '            \'CACHE_DEFAULT_TIMEOUT\': 300\n' +
                        '        })\n' +
                        '        cache.init_app(app)\n' +
                        '        app.cache_backend = backend\n' +
                        '        return cache\n\n' +
                        content[next_line_pos:]
                    )
                    
                    with open(cache_utils_file, 'w') as f:
                        f.write(modified_content)
                    
                    logger.info(f"Updated {cache_utils_file} to check for REDIS_DISABLED flag")
        except Exception as e:
            logger.error(f"Failed to update {cache_utils_file}: {str(e)}")
    
    logger.info("Redis has been successfully disabled")
    logger.info("The application will now use SimpleCache instead")
    logger.info("This change will persist across application restarts")
    
    return True

if __name__ == "__main__":
    success = disable_redis()
    sys.exit(0 if success else 1)