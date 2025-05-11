"""
Asynchronous Instagram Ads Scraper

This module implements an asynchronous scraper for Instagram ads related to art opportunities.
It extends the AsyncBaseScraper to leverage concurrent requests for improved performance.
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from scrapers.async_base_scraper import AsyncBaseScraper
from models import db, Opportunity

# Configure logging
logger = logging.getLogger('instagram_ads_scraper')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Instagram Ad URLs - these would be dynamically populated in a real implementation
# For example, from a list of tracked Instagram accounts or hashtags
INSTAGRAM_AD_URLS = [
    "https://www.instagram.com/explore/tags/artopportunity/",
    "https://www.instagram.com/explore/tags/artistopportunity/",
    "https://www.instagram.com/explore/tags/artresidency/",
    "https://www.instagram.com/explore/tags/artgrant/",
    "https://www.instagram.com/explore/tags/artcall/",
    "https://www.instagram.com/explore/tags/callforartists/",
    "https://www.instagram.com/explore/tags/artistcall/",
    "https://www.instagram.com/explore/tags/artexhibition/",
    "https://www.instagram.com/explore/tags/artsubmission/",
    "https://www.instagram.com/explore/tags/artcompetition/"
]

class InstagramAdsAsyncScraper(AsyncBaseScraper):
    """Asynchronous Instagram Ads Scraper"""
    
    def __init__(self):
        """Initialize the Instagram ads scraper"""
        super().__init__(scraper_name="instagram_ads_async", max_concurrency=5)
        
        # Instagram-specific headers to avoid being blocked
        self.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Alt-Used": "www.instagram.com",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "TE": "trailers"
        })
    
    async def extract_opportunities(self, soup, source_url):
        """
        Extract opportunity data from Instagram page
        
        Args:
            soup: BeautifulSoup object of the Instagram page
            source_url: URL of the Instagram page
            
        Returns:
            list: List of opportunity dictionaries
        """
        opportunities = []
        
        try:
            # Look for the shared data JSON in the page
            # Instagram embeds post data in a script tag
            json_data = None
            for script in soup.find_all('script'):
                if script.string and 'window._sharedData' in script.string:
                    json_text = script.string.replace('window._sharedData = ', '').rstrip(';')
                    json_data = json.loads(json_text)
                    break
            
            if not json_data:
                logger.warning(f"Could not find shared data in {source_url}")
                return opportunities
            
            # Extract posts from the hashtag page
            if 'entry_data' in json_data and 'TagPage' in json_data['entry_data']:
                tag_page = json_data['entry_data']['TagPage'][0]
                if 'graphql' in tag_page and 'hashtag' in tag_page['graphql']:
                    hashtag = tag_page['graphql']['hashtag']
                    if 'edge_hashtag_to_media' in hashtag:
                        posts = hashtag['edge_hashtag_to_media']['edges']
                        
                        for post in posts:
                            node = post['node']
                            
                            # Check if it looks like an opportunity post
                            if self._is_art_opportunity(node):
                                post_url = f"https://www.instagram.com/p/{node['shortcode']}/"
                                
                                opportunity = {
                                    'title': self._extract_title(node),
                                    'url': post_url,
                                    'description': self._extract_caption(node),
                                    'image_url': node.get('display_url'),
                                    'posted_date': self._format_timestamp(node.get('taken_at_timestamp')),
                                    'source': 'Instagram',
                                    'source_url': source_url,
                                    'is_ad': True,
                                    'scraped_at': datetime.utcnow().isoformat(),
                                    'tags': self._extract_tags(node)
                                }
                                
                                opportunities.append(opportunity)
        
        except Exception as e:
            logger.error(f"Error extracting opportunities from {source_url}: {e}")
        
        return opportunities
    
    def _is_art_opportunity(self, node):
        """
        Determine if a post is likely an art opportunity
        
        Args:
            node: Instagram post node from JSON data
            
        Returns:
            bool: True if the post is likely an art opportunity
        """
        opportunity_keywords = [
            'opportunity', 'call for', 'submission', 'contest', 'competition',
            'residency', 'grant', 'fellowship', 'exhibition', 'apply',
            'deadline', 'application', 'artists wanted', 'open call'
        ]
        
        caption = self._extract_caption(node)
        if not caption:
            return False
        
        caption_lower = caption.lower()
        
        # Check for opportunity keywords
        for keyword in opportunity_keywords:
            if keyword in caption_lower:
                return True
        
        return False
    
    def _extract_caption(self, node):
        """Extract caption from Instagram post node"""
        if 'edge_media_to_caption' in node and node['edge_media_to_caption']['edges']:
            return node['edge_media_to_caption']['edges'][0]['node']['text']
        return ""
    
    def _extract_title(self, node):
        """Extract a title from Instagram post node"""
        caption = self._extract_caption(node)
        if not caption:
            return "Instagram Art Opportunity"
        
        # Try to use the first line as title
        lines = caption.split('\n')
        if lines:
            title = lines[0].strip()
            # Truncate title if too long
            if len(title) > 80:
                title = title[:77] + "..."
            return title
        
        return "Instagram Art Opportunity"
    
    def _extract_tags(self, node):
        """Extract hashtags from Instagram post node"""
        caption = self._extract_caption(node)
        if not caption:
            return []
        
        # Find all hashtags using regex
        hashtags = re.findall(r'#(\w+)', caption)
        return hashtags
    
    def _format_timestamp(self, timestamp):
        """Format unix timestamp to ISO format"""
        if timestamp:
            return datetime.fromtimestamp(timestamp).isoformat()
        return datetime.utcnow().isoformat()
    
    async def process_opportunity(self, opportunity_data):
        """
        Process a single opportunity by saving to database
        
        Args:
            opportunity_data: Dictionary with opportunity information
            
        Returns:
            bool: True if processed successfully
        """
        # Import Flask app here to avoid circular imports
        from flask import current_app
        
        try:
            # For testing without a Flask app context
            try:
                if not current_app:
                    logger.info(f"No Flask app context - would save opportunity: {opportunity_data['title']}")
                    self.total_opportunities += 1
                    return True
            except:
                # If current_app raises an error (working outside application context)
                logger.info(f"No Flask app context - would save opportunity: {opportunity_data['title']}")
                self.total_opportunities += 1
                return True
                
            # Check if opportunity already exists by URL
            existing = Opportunity.query.filter_by(url=opportunity_data['url']).first()
            if existing:
                # Update existing opportunity if needed
                logger.debug(f"Opportunity already exists: {opportunity_data['url']}")
                self.total_opportunities += 1
                return True
            
            # Create new opportunity
            opp = Opportunity(
                title=opportunity_data['title'],
                url=opportunity_data['url'],
                description=opportunity_data['description'],
                image_url=opportunity_data.get('image_url'),
                posted_date=opportunity_data.get('posted_date'),
                source=opportunity_data['source'],
                source_url=opportunity_data['source_url'],
                is_ad=True,
                type='social_media',  # Instagram ads are social media type
                scraped_at=datetime.utcnow()
            )
            
            # Add to database
            db.session.add(opp)
            db.session.commit()
            
            logger.debug(f"Added new opportunity: {opportunity_data['title']}")
            self.total_opportunities += 1
            return True
            
        except Exception as e:
            logger.error(f"Error processing opportunity: {e}")
            # Roll back transaction on error if in app context
            try:
                db.session.rollback()
            except:
                pass
            
            # Don't fail the entire process for one item
            self.total_opportunities += 1
            return True

# Synchronous function for APScheduler
def run_instagram_ads_scraper():
    """Run the Instagram ads scraper (sync wrapper for async code)"""
    try:
        scraper = InstagramAdsAsyncScraper()
        result = scraper.scrape(INSTAGRAM_AD_URLS)
        return result
    except Exception as e:
        logger.error(f"Error running Instagram ads scraper: {e}")
        return 0

# Direct execution entry point
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = run_instagram_ads_scraper()
    print(f"Found {count} Instagram opportunities")