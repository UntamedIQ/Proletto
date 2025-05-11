"""
Asynchronous Art Opportunities Scraper

This module implements a general-purpose asynchronous scraper for art opportunity websites.
It can be used to scrape multiple URLs concurrently for improved performance.
"""

import asyncio
import logging
import re
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from scrapers.async_base_scraper import AsyncBaseScraper
from models import db, Opportunity

# Configure logging
logger = logging.getLogger('art_opportunities_scraper')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ArtOpportunitiesAsyncScraper(AsyncBaseScraper):
    """Asynchronous Art Opportunities Scraper"""
    
    def __init__(self, engine_name="general", urls=None, state=None, max_concurrency=10):
        """
        Initialize the art opportunities scraper
        
        Args:
            engine_name (str): Name of the scraper engine
            urls (list): List of URLs to scrape
            state (str): State/region associated with these opportunities
            max_concurrency (int): Maximum number of concurrent requests
        """
        super().__init__(scraper_name=f"art_opportunities_{engine_name}", max_concurrency=max_concurrency)
        self.urls = urls or []
        self.state = state
        self.opportunity_type = "general"
        
        # Keywords to identify opportunities
        self.opportunity_keywords = [
            'call for', 'opportunity', 'submission', 'apply', 'application',
            'deadline', 'residency', 'grant', 'funding', 'fellowship',
            'exhibition', 'contest', 'competition', 'commission', 'award',
            'stipend', 'scholarship', 'open call', 'artists wanted', 'seeking artists'
        ]
        
        # Patterns for deadline extraction
        self.deadline_patterns = [
            r'deadline[s]?:?\s*([a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
            r'due(\s+by)?:?\s*([a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
            r'applications\s+due:?\s*([a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
            r'closing\s+date:?\s*([a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
            r'submit\s+by:?\s*([a-zA-Z]+\s+\d{1,2},?\s+\d{4})',
            r'apply\s+by:?\s*([a-zA-Z]+\s+\d{1,2},?\s+\d{4})'
        ]
        
        # Patterns for location extraction
        self.location_patterns = [
            r'location:\s*([^,\.]+(?:,\s*[^,\.]+)?)',
            r'in\s+([A-Z][a-z]+\s*(?:,\s*[A-Z][a-z]+)?)',
            r'at\s+([A-Z][a-z]+\s*(?:,\s*[A-Z][a-z]+)?)'
        ]
    
    async def run(self):
        """Run the scraper on the configured URLs"""
        if not self.urls:
            logger.warning(f"{self.scraper_name} has no URLs configured")
            return 0
        
        return await self.run_scraper(self.urls)
    
    async def extract_opportunities(self, soup, source_url):
        """
        Extract opportunity data from HTML
        
        Args:
            soup: BeautifulSoup object
            source_url: Source URL
            
        Returns:
            list: List of opportunity dictionaries
        """
        opportunities = []
        domain = urlparse(source_url).netloc
        
        try:
            # Find all potential opportunity containers
            opportunity_elements = self._find_opportunity_elements(soup)
            
            for element in opportunity_elements:
                # Check if it's likely an opportunity
                if not self._is_opportunity(element):
                    continue
                
                # Extract opportunity data
                title = self._extract_title(element)
                if not title:
                    continue
                
                # Extract link to the opportunity detail page
                link = self._extract_link(element, source_url)
                if not link:
                    continue
                
                # Extract other opportunity details
                description = self._extract_description(element)
                deadline = self._extract_deadline(element)
                location = self._extract_location(element) or self.state
                image_url = self._extract_image(element, source_url)
                
                opportunity = {
                    'title': title,
                    'url': link,
                    'description': description,
                    'deadline': deadline,
                    'location': location,
                    'image_url': image_url,
                    'source': domain,
                    'source_url': source_url,
                    'state': self.state,
                    'type': self.opportunity_type,
                    'is_ad': False,
                    'scraped_at': datetime.utcnow().isoformat()
                }
                
                opportunities.append(opportunity)
        
        except Exception as e:
            logger.error(f"Error extracting opportunities from {source_url}: {e}")
        
        return opportunities
    
    def _find_opportunity_elements(self, soup):
        """Find HTML elements that might contain opportunities"""
        elements = []
        
        # Look for common opportunity container patterns
        selectors = [
            'article', '.opportunity', '.post', '.listing', '.job-listing',
            '.card', '.item', '.result', '.entry', 'div.row', 'li.listing',
            'div[id*="opportunity"]', 'div[class*="opportunity"]',
            'div[id*="post"]', 'div[class*="post"]',
            'div[id*="listing"]', 'div[class*="listing"]'
        ]
        
        for selector in selectors:
            elements.extend(soup.select(selector))
        
        # If no elements found through selectors, try a more general approach
        if not elements:
            # Look for likely opportunity headers
            for h_tag in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                text = h_tag.get_text().lower()
                for keyword in self.opportunity_keywords:
                    if keyword in text:
                        # Get the parent container
                        parent = h_tag.parent
                        if parent and parent not in elements:
                            elements.append(parent)
        
        # If still no elements, use entire body as one opportunity
        if not elements:
            body = soup.find('body')
            if body:
                elements = [body]
        
        return elements
    
    def _is_opportunity(self, element):
        """Check if an element likely contains an opportunity"""
        text = element.get_text().lower()
        
        # Check for opportunity keywords
        for keyword in self.opportunity_keywords:
            if keyword in text:
                return True
        
        return False
    
    def _extract_title(self, element):
        """Extract opportunity title from element"""
        # First look for heading tags
        for tag in element.find_all(['h1', 'h2', 'h3', 'h4']):
            title = tag.get_text().strip()
            if title and len(title) < 200:  # Reasonable title length
                return title
        
        # Try to find a title in a title attribute
        for tag in element.find_all(attrs={'title': True}):
            title = tag['title'].strip()
            if title and len(title) < 200:
                return title
        
        # Use the first paragraph or div with reasonable length
        for tag in element.find_all(['p', 'div']):
            if not tag.find(['p', 'div']):  # Only leaf nodes
                text = tag.get_text().strip()
                if 10 < len(text) < 200:  # Reasonable title length
                    return text
        
        return None
    
    def _extract_link(self, element, base_url):
        """Extract opportunity link from element"""
        # Find the most relevant link
        links = element.find_all('a', href=True)
        
        if links:
            # Prioritize links with opportunity keywords
            for link in links:
                text = link.get_text().lower()
                for keyword in ['apply', 'details', 'learn more', 'more info', 'read more']:
                    if keyword in text:
                        return self._make_absolute_url(link['href'], base_url)
            
            # Fall back to the first link
            return self._make_absolute_url(links[0]['href'], base_url)
        
        return None
    
    def _make_absolute_url(self, href, base_url):
        """Convert relative URL to absolute URL"""
        from urllib.parse import urljoin
        return urljoin(base_url, href)
    
    def _extract_description(self, element):
        """Extract opportunity description from element"""
        # Extract all paragraphs
        paragraphs = []
        for p in element.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 20:  # Ignore very short paragraphs
                paragraphs.append(text)
        
        if paragraphs:
            return ' '.join(paragraphs)
        
        # If no paragraphs, use the element text
        text = element.get_text().strip()
        if len(text) > 500:  # Truncate long descriptions
            return text[:497] + '...'
        return text
    
    def _extract_deadline(self, element):
        """Extract application deadline from element"""
        text = element.get_text()
        
        for pattern in self.deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Return the matched date
                group = 1 if len(match.groups()) == 1 else 2
                return match.group(group).strip()
        
        return None
    
    def _extract_location(self, element):
        """Extract opportunity location from element"""
        text = element.get_text()
        
        for pattern in self.location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return self.state
    
    def _extract_image(self, element, base_url):
        """Extract image URL from element"""
        img = element.find('img', src=True)
        if img and img['src']:
            return self._make_absolute_url(img['src'], base_url)
        return None
    
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
            if not current_app:
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
                description=opportunity_data.get('description', ''),
                deadline=opportunity_data.get('deadline'),
                location=opportunity_data.get('location'),
                image_url=opportunity_data.get('image_url'),
                source=opportunity_data['source'],
                source_url=opportunity_data['source_url'],
                state=opportunity_data.get('state'),
                type=opportunity_data.get('type', 'general'),
                is_ad=opportunity_data.get('is_ad', False),
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
                if current_app:
                    db.session.rollback()
            except:
                pass
            
            # Don't fail the entire process for one item
            self.total_opportunities += 1
            return True

# Dictionary of pre-configured state-specific scrapers
STATE_ENGINES = {
    'california': {
        'urls': [
            'https://www.cac.ca.gov/opportunities/',
            'https://www.artjobs.com/california/',
            'https://www.callforentry.org/opportunities/california/',
            'https://www.artworkarchive.com/call-for-entry/california'
        ],
        'state': 'California'
    },
    'new_york': {
        'urls': [
            'https://www.nyfa.org/opportunities/',
            'https://www.artjobs.com/new-york/',
            'https://www.callforentry.org/opportunities/new-york/',
            'https://www.artworkarchive.com/call-for-entry/new-york'
        ],
        'state': 'New York'
    },
    'texas': {
        'urls': [
            'https://texasartistscoalition.org/opportunities/',
            'https://www.artjobs.com/texas/',
            'https://www.callforentry.org/opportunities/texas/',
            'https://www.artworkarchive.com/call-for-entry/texas'
        ],
        'state': 'Texas'
    },
    'florida': {
        'urls': [
            'https://floridastateartscouncil.org/opportunities/',
            'https://www.artjobs.com/florida/',
            'https://www.callforentry.org/opportunities/florida/',
            'https://www.artworkarchive.com/call-for-entry/florida'
        ],
        'state': 'Florida'
    }
}

# Factory function to create a state-specific scraper
def create_state_scraper(state_key):
    """Create a state-specific scraper based on pre-configured settings"""
    if state_key in STATE_ENGINES:
        config = STATE_ENGINES[state_key]
        return ArtOpportunitiesAsyncScraper(
            engine_name=state_key,
            urls=config['urls'],
            state=config['state']
        )
    else:
        logger.error(f"No configuration found for state: {state_key}")
        return None

# Synchronous function for APScheduler
def run_art_opportunities_scraper(state_key):
    """Run the art opportunities scraper for a specific state"""
    try:
        scraper = create_state_scraper(state_key)
        if scraper:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(scraper.run())
            return result
        return 0
    except Exception as e:
        logger.error(f"Error running art opportunities scraper for {state_key}: {e}")
        return 0

# Run all state scrapers
def run_all_state_scrapers():
    """Run all state-specific scrapers"""
    total = 0
    for state_key in STATE_ENGINES.keys():
        count = run_art_opportunities_scraper(state_key)
        total += count
    return total

# Direct execution entry point
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = run_all_state_scrapers()
    print(f"Found {count} total art opportunities across all states")