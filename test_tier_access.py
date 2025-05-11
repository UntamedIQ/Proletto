#!/usr/bin/env python3
"""
Test script to verify the membership tier-based access control for opportunities
"""

import os
import sys
import json
import argparse
import logging
from flask import Flask
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    """Create a Flask app for testing"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    return app

def test_api_tier_access(base_url=None):
    """Test tier-based access through the API endpoints"""
    # Use either provided URL or localhost
    if not base_url:
        base_url = 'http://localhost:5000'  # Changed to port 5000 (main app) from 5001 (API backend)
    
    # Test URLs for different tiers
    endpoints = [
        # Free tier
        {'url': f'{base_url}/opportunities/?tier=free', 'description': 'Free tier access'},
        # Supporter tier with states
        {'url': f'{base_url}/opportunities/?tier=supporter&state=CA&state=NY', 'description': 'Supporter tier with CA and NY states'},
        # Supporter tier without states
        {'url': f'{base_url}/opportunities/?tier=supporter', 'description': 'Supporter tier with no states'},
        # Premium tier
        {'url': f'{base_url}/opportunities/?tier=premium', 'description': 'Premium tier access'},
        # No tier (should show all)
        {'url': f'{base_url}/opportunities/', 'description': 'No tier filter (all opportunities)'}
    ]
    
    # Make requests for each endpoint
    results = []
    for endpoint in endpoints:
        try:
            logger.info(f"Testing {endpoint['description']} at {endpoint['url']}")
            response = requests.get(endpoint['url'], timeout=10)
            
            if response.status_code != 200:
                results.append({
                    'description': endpoint['description'],
                    'url': endpoint['url'],
                    'status': 'Error',
                    'status_code': response.status_code,
                    'message': f"Received status code {response.status_code}"
                })
                continue
                
            # Parse the response
            data = response.json()
            count = data.get('count', 0)
            total = data.get('total', 0)
            
            results.append({
                'description': endpoint['description'],
                'url': endpoint['url'],
                'status': 'Success',
                'count': count,
                'total': total,
                'message': f"Found {count} opportunities out of {total} total"
            })
            
            # Print some sample opportunities if available
            if count > 0:
                opportunities = data.get('opportunities', [])
                for i, opp in enumerate(opportunities[:3]):  # Show up to 3 opportunities
                    logger.info(f"  Sample opportunity {i+1}:")
                    logger.info(f"    Title: {opp.get('title')}")
                    logger.info(f"    Type: {opp.get('type')}")
                    logger.info(f"    State: {opp.get('state')}")
                    logger.info(f"    Membership level: {opp.get('membership_level')}")
            
        except Exception as e:
            logger.error(f"Error testing {endpoint['url']}: {str(e)}")
            results.append({
                'description': endpoint['description'],
                'url': endpoint['url'],
                'status': 'Error',
                'message': str(e)
            })
    
    # Print summary
    logger.info("=== Tier Access Test Summary ===")
    for result in results:
        status = '✅' if result['status'] == 'Success' else '❌'
        message = result.get('message', '')
        logger.info(f"{status} {result['description']}: {message}")
        
    # Return overall success
    return all(r['status'] == 'Success' for r in results)

def main():
    """Main entry point for the test script"""
    parser = argparse.ArgumentParser(description='Test membership tier-based access control for opportunities')
    parser.add_argument('--api-url', default=None, help='Base URL for the API (default: http://localhost:5001)')
    args = parser.parse_args()
    
    logger.info("Starting tier-based access control tests")
    
    # Test API tier access
    api_success = test_api_tier_access(args.api_url)
    
    # Print overall result
    logger.info("=== Overall Test Result ===")
    if api_success:
        logger.info("✅ All tests passed successfully")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())