#!/usr/bin/env python3
"""
Update existing scrapers to populate the new tier-based access fields
- state field for state-based filtering
- membership_level field for tier-based access
- type field for opportunity type categorization
"""

import os
import sys
import argparse
import logging
import re
from datetime import datetime
from importlib import import_module, reload

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# List of scraper modules to modify
SCRAPER_MODULES = [
    'scrapers.art_opportunities_async',
    'scrapers.instagram_ads_async',
    'scrapers.async_base_scraper',
    'bot_code'
]

def detect_states_from_location(location):
    """Detect US state from location field if possible"""
    if not location:
        return None
        
    location = location.lower()
    
    # Dictionary of state names and abbreviations
    states = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
        'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
        'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
        'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
        'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
        'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
        'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
        'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
        # Add abbreviations as keys too
        'al': 'AL', 'ak': 'AK', 'az': 'AZ', 'ar': 'AR', 'ca': 'CA',
        'co': 'CO', 'ct': 'CT', 'de': 'DE', 'fl': 'FL', 'ga': 'GA',
        'hi': 'HI', 'id': 'ID', 'il': 'IL', 'in': 'IN', 'ia': 'IA',
        'ks': 'KS', 'ky': 'KY', 'la': 'LA', 'me': 'ME', 'md': 'MD',
        'ma': 'MA', 'mi': 'MI', 'mn': 'MN', 'ms': 'MS', 'mo': 'MO',
        'mt': 'MT', 'ne': 'NE', 'nv': 'NV', 'nh': 'NH', 'nj': 'NJ',
        'nm': 'NM', 'ny': 'NY', 'nc': 'NC', 'nd': 'ND', 'oh': 'OH',
        'ok': 'OK', 'or': 'OR', 'pa': 'PA', 'ri': 'RI', 'sc': 'SC',
        'sd': 'SD', 'tn': 'TN', 'tx': 'TX', 'ut': 'UT', 'vt': 'VT',
        'va': 'VA', 'wa': 'WA', 'wv': 'WV', 'wi': 'WI', 'wy': 'WY'
    }
    
    # Check for state names in the location
    words = location.replace(',', ' ').split()
    for word in words:
        if word in states:
            return states[word]
            
    # Check if the entire location contains a state name
    for state_name in states:
        if state_name in location and len(state_name) > 2:  # Only check full state names, not abbreviations
            return states[state_name]
    
    return None

def detect_opportunity_type(title, description, source, tags=None, category=None):
    """Determine the opportunity type based on various fields"""
    # Normalize inputs
    title = title.lower() if title else ''
    description = description.lower() if description else ''
    source = source.lower() if source else ''
    tags = tags.lower() if tags else ''
    category = category.lower() if category else ''
    
    # Check for social media indicators
    social_media_keywords = ['instagram', 'facebook', 'twitter', 'linkedin', 'social', 'post', 'platform']
    for keyword in social_media_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'social_media'
    
    # Check for grant indicators
    grant_keywords = ['grant', 'funding', 'award', 'prize', 'scholarship', 'fellowship', 'financial']
    for keyword in grant_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'grant'
    
    # Check for residency indicators
    residency_keywords = ['residency', 'resident', 'residence', 'studio']
    for keyword in residency_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'residency'
    
    # Check for exhibition indicators
    exhibition_keywords = ['exhibition', 'exhibit', 'gallery', 'show', 'showcase', 'museum']
    for keyword in exhibition_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'exhibition'
    
    # Check for opportunity indicators
    opportunity_keywords = ['opportunity', 'call', 'application', 'submit', 'apply']
    for keyword in opportunity_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'opportunity'
    
    # Default type
    return 'general'

def determine_membership_level(opportunity_type, state=None):
    """Determine appropriate membership level for an opportunity"""
    # Default premium level for most opportunities
    if not opportunity_type:
        return 'premium'
        
    # Social media opportunities are free tier
    if opportunity_type == 'social_media':
        return 'free'
    
    # General opportunities are free tier
    if opportunity_type == 'general':
        return 'free'
    
    # Grants and residencies are usually premium
    if opportunity_type in ['grant', 'residency']:
        return 'premium'
    
    # Exhibitions could be supporter tier depending on state
    if opportunity_type == 'exhibition':
        # If we have state information, it's for supporter tier
        if state:
            return 'supporter'
        return 'premium'
    
    # Default to premium for anything else
    return 'premium'

def update_async_base_scraper(dry_run=False):
    """Update the async_base_scraper module to include tier-based access code"""
    try:
        file_path = 'scrapers/async_base_scraper.py'
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the code already has the tier-based access logic
        if 'def detect_states_from_location' in content:
            logger.info(f"Skipping {file_path} - already contains tier-based access code")
            return False
        
        # Find the import section
        import_section_end = content.find('class AsyncBaseScraper')
        if import_section_end == -1:
            logger.error(f"Could not find import section in {file_path}")
            return False
            
        # Add the new functions
        new_imports = """
# State detection and tier-based access functions
def detect_states_from_location(location):
    \"\"\"Detect US state from location field if possible\"\"\"
    if not location:
        return None
        
    location = location.lower()
    
    # Dictionary of state names and abbreviations
    states = {
        'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR', 'california': 'CA',
        'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA',
        'hawaii': 'HI', 'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
        'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
        'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
        'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV', 'new hampshire': 'NH', 'new jersey': 'NJ',
        'new mexico': 'NM', 'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH',
        'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
        'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
        'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV', 'wisconsin': 'WI', 'wyoming': 'WY',
        # Add abbreviations as keys too
        'al': 'AL', 'ak': 'AK', 'az': 'AZ', 'ar': 'AR', 'ca': 'CA',
        'co': 'CO', 'ct': 'CT', 'de': 'DE', 'fl': 'FL', 'ga': 'GA',
        'hi': 'HI', 'id': 'ID', 'il': 'IL', 'in': 'IN', 'ia': 'IA',
        'ks': 'KS', 'ky': 'KY', 'la': 'LA', 'me': 'ME', 'md': 'MD',
        'ma': 'MA', 'mi': 'MI', 'mn': 'MN', 'ms': 'MS', 'mo': 'MO',
        'mt': 'MT', 'ne': 'NE', 'nv': 'NV', 'nh': 'NH', 'nj': 'NJ',
        'nm': 'NM', 'ny': 'NY', 'nc': 'NC', 'nd': 'ND', 'oh': 'OH',
        'ok': 'OK', 'or': 'OR', 'pa': 'PA', 'ri': 'RI', 'sc': 'SC',
        'sd': 'SD', 'tn': 'TN', 'tx': 'TX', 'ut': 'UT', 'vt': 'VT',
        'va': 'VA', 'wa': 'WA', 'wv': 'WV', 'wi': 'WI', 'wy': 'WY'
    }
    
    # Check for state names in the location
    words = location.replace(',', ' ').split()
    for word in words:
        if word in states:
            return states[word]
            
    # Check if the entire location contains a state name
    for state_name in states:
        if state_name in location and len(state_name) > 2:  # Only check full state names, not abbreviations
            return states[state_name]
    
    return None

def detect_opportunity_type(title, description, source, tags=None, category=None):
    \"\"\"Determine the opportunity type based on various fields\"\"\"
    # Normalize inputs
    title = title.lower() if title else ''
    description = description.lower() if description else ''
    source = source.lower() if source else ''
    tags = tags.lower() if tags else ''
    category = category.lower() if category else ''
    
    # Check for social media indicators
    social_media_keywords = ['instagram', 'facebook', 'twitter', 'linkedin', 'social', 'post', 'platform']
    for keyword in social_media_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'social_media'
    
    # Check for grant indicators
    grant_keywords = ['grant', 'funding', 'award', 'prize', 'scholarship', 'fellowship', 'financial']
    for keyword in grant_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'grant'
    
    # Check for residency indicators
    residency_keywords = ['residency', 'resident', 'residence', 'studio']
    for keyword in residency_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'residency'
    
    # Check for exhibition indicators
    exhibition_keywords = ['exhibition', 'exhibit', 'gallery', 'show', 'showcase', 'museum']
    for keyword in exhibition_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'exhibition'
    
    # Check for opportunity indicators
    opportunity_keywords = ['opportunity', 'call', 'application', 'submit', 'apply']
    for keyword in opportunity_keywords:
        if (keyword in source or keyword in category or keyword in tags or 
            keyword in title or keyword in description):
            return 'opportunity'
    
    # Default type
    return 'general'

def determine_membership_level(opportunity_type, state=None):
    \"\"\"Determine appropriate membership level for an opportunity\"\"\"
    # Default premium level for most opportunities
    if not opportunity_type:
        return 'premium'
        
    # Social media opportunities are free tier
    if opportunity_type == 'social_media':
        return 'free'
    
    # General opportunities are free tier
    if opportunity_type == 'general':
        return 'free'
    
    # Grants and residencies are usually premium
    if opportunity_type in ['grant', 'residency']:
        return 'premium'
    
    # Exhibitions could be supporter tier depending on state
    if opportunity_type == 'exhibition':
        # If we have state information, it's for supporter tier
        if state:
            return 'supporter'
        return 'premium'
    
    # Default to premium for anything else
    return 'premium'

"""
        
        # Add the new import code at the correct position
        updated_content = content[:import_section_end] + new_imports + content[import_section_end:]
        
        # Now find the opportunity creation methods and update them
        # Pattern matches a Python dictionary with opportunity properties
        opportunity_pattern = r'opportunity\s*=\s*\{[^}]+\}'
        
        def add_tier_fields(match):
            """Add tier-based access fields to an opportunity dict"""
            opp_dict = match.group(0)
            
            # Check if already has membership_level
            if 'membership_level' in opp_dict:
                return opp_dict
                
            # Add state field based on location
            opp_dict = opp_dict.replace('}', """
    # Add tier-based access fields
    'state': detect_states_from_location(location),
    'type': detect_opportunity_type(title, description, source, tags, category),
    'membership_level': determine_membership_level(
        detect_opportunity_type(title, description, source, tags, category),
        detect_states_from_location(location)
    ),
}""")
            return opp_dict
            
        updated_content = re.sub(opportunity_pattern, add_tier_fields, updated_content)
        
        if dry_run:
            logger.info(f"Would update {file_path} (dry run)")
            return True
            
        # Write the updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        logger.info(f"Successfully updated {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error updating {file_path}: {str(e)}")
        return False

def update_scraper_modules(dry_run=False):
    """Update all scraper modules to add tier-based access fields"""
    success_count = 0
    
    # Update the base scraper first
    if update_async_base_scraper(dry_run):
        success_count += 1
    
    # Reload modules to get updated code
    if not dry_run:
        try:
            base_module = import_module('scrapers.async_base_scraper')
            reload(base_module)
            logger.info("Reloaded async_base_scraper module")
        except Exception as e:
            logger.warning(f"Could not reload async_base_scraper: {str(e)}")
    
    return success_count

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Update scrapers to add tier-based access fields')
    parser.add_argument('--dry-run', action='store_true', help='Do not modify files, just show what would change')
    args = parser.parse_args()
    
    logger.info("Starting scraper updates for tier-based access fields")
    
    # Update all scraper modules
    success_count = update_scraper_modules(args.dry_run)
    
    # Report results
    action = "would be" if args.dry_run else "were"
    logger.info(f"{success_count} scraper modules {action} successfully updated")
    
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main())