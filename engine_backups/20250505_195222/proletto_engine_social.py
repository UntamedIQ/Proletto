#!/usr/bin/env python3
"""
Proletto Engine Social - Specialized scraper for art opportunities on social media platforms
Available for all users (Free tier)
"""
import logging
import requests
import json
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger('proletto_engine_social')

# Social media and artist community sites to scrape (public/accessible ones)
SOCIAL_SITES = [
    # Artist job boards and community sites
    "https://www.callforentry.org/",
    "https://artistsnetwork.org/art-competitions/",
    "https://www.submittable.com/discover/",
    "https://www.artworkarchive.com/blog/category/opportunities",
    "https://www.artplaceamerica.org/blog",
    "https://artiststhrive.org/opportunities/",
    "https://www.artjobs.com/",
    "https://www.artsthread.com/",
    "https://www.artquest.org.uk/opportunities/",
    "https://www.resartis.org/open-calls",
    "https://www.transartists.org/en/map",
    "https://www.artopportunities.org/",
    "https://www.nyfa.org/opportunities/",
    "https://www.artrabbit.com/artist-opportunities",
    
    # Forums and community boards
    "https://www.reddit.com/r/artcommissions/",
    "https://www.reddit.com/r/artists/",
    "https://www.reddit.com/r/artbusiness/",
    "https://www.reddit.com/r/artjobs/",
    "https://www.wetcanvas.com/forums/",
    "https://www.deviantart.com/forum/jobs/offers/",
    "https://community.pixologic.com/forum/20",
    
    # Twitter/X hashtag pages (public/accessible)
    "https://nitter.net/search?f=tweets&q=%23artopportunity",
    "https://nitter.net/search?f=tweets&q=%23artistopportunity",
    "https://nitter.net/search?f=tweets&q=%23opencall",
    "https://nitter.net/search?f=tweets&q=%23artistcall",
    "https://nitter.net/search?f=tweets&q=%23artjobs",
    "https://nitter.net/search?f=tweets&q=%23artgrants",
    "https://nitter.net/search?f=tweets&q=%23residency%20%23art",
    
    # RSS feeds of art blogs and news (accessible without API)
    "https://hyperallergic.com/feed/",
    "https://news.artnet.com/feed",
    "https://www.artsjournal.com/feed",
    "https://www.artforum.com/feed",
    "https://www.theartnewspaper.com/rss",
    "https://www.artsy.net/rss/news",
    "https://www.artnews.com/feed/"
]

HEADERS = {
    'User-Agent': 'ProlettoBot/1.0 (+https://www.myproletto.com)'
}

# Keywords related to opportunities
KEYWORDS = [
    # General opportunity terms
    "opportunity", "call for", "open call", "submission", "apply", "application", 
    "deadline", "grant", "funding", "residency", "fellowship", "award", "prize",
    "competition", "exhibit", "exhibition", "showcase", "commission", "job", 
    "position", "hiring", "employment", "paid", "stipend", "honorarium", "entry",
    
    # Art-specific opportunity types
    "artist opportunity", "art opportunity", "call for artists", "call for art",
    "artist call", "art call", "artist grant", "art grant", "artist residency",
    "artist fellowship", "artist award", "artist prize", "art competition", 
    "art exhibit", "art exhibition", "art showcase", "art commission", 
    "artist job", "art job", "artist position", "artist employment", "artist stipend",
    "artist honorarium", "art entry", "artist submission", "art submission",
    
    # Deadline indicators
    "due by", "due date", "deadline is", "closes on", "submissions close",
    "applications close", "apply by", "submit by", "ends on"
]

def is_relevant(text):
    """Check if text contains any relevant keywords."""
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS)

def extract_date(text):
    """
    Try to extract a date from text that might indicate a deadline.
    This is a simple pattern matching approach, not full NLP.
    """
    import re
    
    # Most common date formats in US
    # Format: MM/DD/YYYY or MM-DD-YYYY
    us_date_pattern = r'\b(0?[1-9]|1[0-2])[/\-](0?[1-9]|[12][0-9]|3[01])[/\-](20\d{2})\b'
    
    # Format: Month DD, YYYY
    written_date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?,?\s+(20\d{2})\b'
    
    # Look for dates
    us_date_match = re.search(us_date_pattern, text)
    written_date_match = re.search(written_date_pattern, text, re.IGNORECASE)
    
    if us_date_match:
        return us_date_match.group(0)
    elif written_date_match:
        return written_date_match.group(0)
    return ""

def scrape_site(url):
    """Scrape a single social media site for art opportunities."""
    try:
        logger.info(f"Scraping social media site: {url}")
        response = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all posts/content blocks
        # This is a simplified approach - real social media would need API access
        # We're looking for common HTML structures that might contain posts
        content_blocks = []
        
        # Different sites have different structures, so we try multiple patterns
        # 1. Try to find divs that might be posts/cards
        cards = soup.find_all("div", class_=lambda c: c and any(x in c.lower() for x in 
                                          ["post", "card", "item", "entry", "job", "opportunity"]))
        content_blocks.extend(cards)
        
        # 2. Try to find article elements
        articles = soup.find_all("article")
        content_blocks.extend(articles)
        
        # 3. Try list items
        list_items = soup.find_all("li", class_=lambda c: c and any(x in c.lower() for x in 
                                              ["post", "item", "job", "result", "opportunity"]))
        content_blocks.extend(list_items)
        
        # If we still don't have much, try sections
        if len(content_blocks) < 5:
            sections = soup.find_all("section")
            content_blocks.extend(sections)
        
        # If we still don't have much, try generic divs with substantial content
        if len(content_blocks) < 5:
            divs = soup.find_all("div", class_=lambda c: c and len(c) > 0)
            longer_divs = [div for div in divs if len(div.get_text()) > 200 and len(div.get_text()) < 2000]
            content_blocks.extend(longer_divs[:10])  # Only take top 10 to avoid overwhelming
        
        # Extract opportunities
        opportunities = []
        
        for block in content_blocks:
            # Get the text of this content block
            block_text = block.get_text(strip=True)
            
            # Skip if too short or not relevant
            if len(block_text) < 50 or not is_relevant(block_text):
                continue
            
            # Try to extract a title
            title_tag = block.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
            title = title_tag.get_text(strip=True) if title_tag else ""
            
            # If no title is found, try to create one from the first 50 chars
            if not title:
                title = block_text[:50].strip() + "..."
            
            # Try to find a link
            link_tag = block.find("a")
            link = link_tag.get("href") if link_tag else ""
            
            # Format the URL correctly if it's relative
            if link and not link.startswith("http"):
                if link.startswith("/"):
                    base_url = "/".join(url.split("/")[:3])  # Get domain part of the URL
                    link = base_url + link
                else:
                    link = url.rstrip("/") + "/" + link
            
            # If no direct link, use the page URL
            if not link:
                link = url
            
            # Try to extract a date (deadline)
            date = extract_date(block_text)
            
            # Create a description from the text (truncated)
            description = block_text[:300].strip() + "..." if len(block_text) > 300 else block_text
            
            # Extract the source name from the URL
            source = url.split("//")[1].split("/")[0].replace("www.", "")
            
            # Only add if we have title and it's not too short
            if title and len(title) > 10:
                opportunities.append({
                    "title": title,
                    "url": link,
                    "description": description,
                    "location": date if date else "See post for details",  # Repurpose location for date
                    "source": f"Social: {source}",
                    "type": "social_media",
                    "state": "National",  # Social media is not state-specific
                    "scraped_date": datetime.utcnow().isoformat(),
                    "membership_level": "free"  # Available to free users
                })
        
        logger.info(f"Found {len(opportunities)} social media opportunities on {url}")
        return opportunities
    except Exception as e:
        logger.error(f"Failed to scrape social media site {url}: {e}")
        return []

def run_scraper():
    """Run the social media scraper on all target sites."""
    logger.info("Starting Proletto Engine Social - specialized scraper for social media")
    
    all_opportunities = []
    
    for site in SOCIAL_SITES:
        try:
            opportunities = scrape_site(site)
            all_opportunities.extend(opportunities)
            
            # Add a polite delay between requests
            delay = random.uniform(2.0, 4.0)
            logger.info(f"Waiting {delay:.2f} seconds before next request")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Error scraping {site}: {e}")
    
    logger.info(f"Social media scraping completed. Found {len(all_opportunities)} total opportunities")
    return all_opportunities

def merge_with_existing(new_opportunities, filename="opportunities.json"):
    """Merge new social media opportunities with existing ones, avoiding duplicates."""
    try:
        # Try to read existing file
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_opportunities = json.load(f)
            logger.info(f"Loaded {len(existing_opportunities)} existing opportunities from {filename}")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info(f"No existing opportunities file found or file is invalid. Creating new.")
            existing_opportunities = []
        
        # Create a set of existing URLs to check for duplicates
        existing_urls = {opp["url"] for opp in existing_opportunities}
        
        # Add only new opportunities
        added_count = 0
        for opp in new_opportunities:
            if opp["url"] not in existing_urls:
                existing_opportunities.append(opp)
                existing_urls.add(opp["url"])
                added_count += 1
        
        # Save the merged list
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_opportunities, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Added {added_count} new social media opportunities. Total: {len(existing_opportunities)}")
        return True
    except Exception as e:
        logger.error(f"Failed to merge social media opportunities: {e}")
        return False

def run():
    """Main function to run the social media scraper."""
    try:
        # Run the scraper
        opportunities = run_scraper()
        
        # Merge with existing opportunities
        success = merge_with_existing(opportunities)
        
        return success
    except Exception as e:
        logger.error(f"Error in Proletto Engine Social: {e}")
        return False

if __name__ == "__main__":
    # When run directly, execute the social media scraper
    run()