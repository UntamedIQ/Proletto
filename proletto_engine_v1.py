#!/usr/bin/env python3
"""
Proletto Engine v1 - Web scraper for art opportunities
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import logging
from datetime import datetime

# Import improved scraper
from improved_scraper import improved_scrape_site

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)
logger = logging.getLogger('proletto_engine')

HEADERS = {
    'User-Agent': 'ProlettoBot/1.0 (+https://www.myproletto.com)'
}

TARGET_SITES = [
    # Top art job boards
    "https://creative-capital.org/jobs/",
    "https://www.artjobs.com/",
    "https://www.nyfa.org/jobs/",
    "https://www.artsthread.com/jobs/",
    "https://www.artsy.net/jobs",
    "https://www.collegeart.org/jobs/",
    "https://www.creativehotlist.com/",
    "https://www.aiga.org/job-board",
    
    # Museum and institution job boards
    "https://www.aam-us.org/job-board/",
    "https://www.museumjobs.com/",
    "https://www.artmuseum.jobs/",
    "https://www.nycmer.org/job-board",
    
    # University art department jobs
    "https://careers.collegeart.org/jobs/",
    "https://jobs.arteducators.org/",
    
    # Gallery and commercial art jobs
    "https://www.artnet.com/careers/",
    "https://www.gagosian.com/careers",
    "https://jobs.theguardian.com/jobs/arts-heritage/",
    "https://www.idealist.org/en/careers?sectorId=ARTS",
    
    # City Artist Programs, Grants and Residencies
    "https://www.artistcommunities.org/residencies",
    "https://resartis.org/listings/",
    "https://www.transartists.org/en/map",
    "https://www.nyfa.org/opportunities/",
    "https://grantspace.org/find-funding/",
    "https://www.foundationcenter.org/find-funding",
    "https://www.arts.gov/grants",
    "https://www.americansforthearts.org/by-topic/funding-resources",
    "https://www.culturalaffairs.nyc/opportunities",
    "https://www.chicago.gov/city/en/depts/dca/provdrs/grants.html",
    
    # These California sites are now handled by proletto_engine_california.py
    
    # Other City Programs
    "https://www.seattle.gov/arts/opportunities",
    "https://www.austintexas.gov/department/art-grants",
    
    # Creative industry job boards
    "https://www.coroflot.com/jobs",
    "https://www.creativeguild.com/jobs",
    "https://www.artforum.com/jobs",
    "https://www.mediabistro.com/jobs/",
    "https://www.behance.net/joblist",
    
    # Opportunity aggregators and open calls
    "https://artistopportunities.org/",
    "https://www.callforentry.org/",
    "https://www.artopportunitiesmonthly.com/",
    "https://www.artshub.com.au/careers/",
    "https://www.transartists.org/en/map",
    "https://www.artrabbit.com/artist-opportunities",
    "https://www.artconnect.com/opportunities",
    "https://artjobs.artsearch.us/",
    "https://www.artdeadline.com/",
    "https://findartinfo.com/",
    
    # Social media sources for art opportunities and open calls
    # Instagram hashtag archives (handled through dedicated Instagram scraper)
    "https://www.instagram.com/explore/tags/artistopportunity/",
    "https://www.instagram.com/explore/tags/opencall/",
    "https://www.instagram.com/explore/tags/artopportunities/",
    "https://www.instagram.com/explore/tags/artistresidency/",
    "https://www.instagram.com/explore/tags/artjobs/",
    "https://www.instagram.com/explore/tags/artopp/",
    
    # Instagram accounts dedicated to art opportunities
    "https://www.instagram.com/artistopportunitiesmonthly/",
    "https://www.instagram.com/artshub/",
    "https://www.instagram.com/artcalls_/",
    "https://www.instagram.com/residencyunlimited/",
    "https://www.instagram.com/artdeadlinecom/",
    "https://www.instagram.com/artopportunitiessubmission/",
    
    # Facebook groups and pages (handled through dedicated Facebook scraper)
    "https://www.facebook.com/groups/artistcallsandopportunities/",
    "https://www.facebook.com/groups/OpenCallsforArtists/",
    "https://www.facebook.com/artistopportunities/",
    "https://www.facebook.com/ArtJobsAndOpportunities/",
    "https://www.facebook.com/artconnectopportunities/",
    "https://www.facebook.com/callforentry/"
]

KEYWORDS = [
    # General job terms
    "job", "employment", "position", "career", "hiring", "opportunity", "full-time", "part-time", "remote work",
    
    # Art-specific job titles
    "artist job", "creative job", "designer job", "art director", "curator", "gallery assistant", 
    "museum job", "art educator", "studio assistant", "graphic designer", "illustrator", "photographer", 
    "art handler", "art consultant", "exhibition designer", "conservator", "preparator", "archivist",
    "art therapist", "public art", "artist residency", "teaching artist", "art administrator",
    
    # Education positions
    "teaching position", "professor", "instructor", "faculty", "lecturer", "art teacher", 
    "adjunct", "visiting artist", "department chair",
    
    # Digital and new media
    "digital artist", "3D artist", "game artist", "concept artist", "UI designer", "UX designer",
    "multimedia artist", "animation", "motion graphics", "VR artist", "AR designer",
    
    # Art market and commercial
    "art sales", "gallery director", "art advisor", "art appraiser", "art dealer", "auction house",
    "collection manager", "registrar", "arts marketing", "development officer", "fundraiser",
    
    # Public and non-profit
    "arts administrator", "program director", "grant writer", "community arts", "outreach coordinator",
    "public art manager", "cultural affairs", "arts council", "nonprofit arts",
    
    # City artist programs and municipal arts opportunities
    "city artist", "municipal artist", "percent for art", "public art program", "city fellowship",
    "artist in residence", "civic artist", "city commission", "municipal grant", "city residency",
    "public works artist", "civic art", "city art program", "urban artist", "public installation",
    
    # Grants, residencies and funding
    "grant", "funding", "residency", "fellowship", "stipend", "award", "scholarship", "open call",
    "commission", "artist grant", "artist fellowship", "art prize", "artist funding", "artist award",
    "artist residency", "artist retreat", "art funding", "creative grant", "project grant", 
    "art scholarship", "cultural funding", "creative funding", "art support", "arts grant"
]

def is_relevant(text):
    """Check if text contains any relevant keywords."""
    return any(keyword in text.lower() for keyword in KEYWORDS)

def scrape_site(url):
    """
    Wrapper for the improved scraper
    """
    try:
        return improved_scrape_site(url, KEYWORDS)
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return []

def run_scraper():
    """Run the scraper on all target sites."""
    logger.info("Starting Proletto Engine v1 scraper")
    
    all_gigs = []
    for site in TARGET_SITES:
        gigs = scrape_site(site)
        all_gigs.extend(gigs)
        # Add a polite delay between requests
        delay = random.uniform(1.5, 3.5)
        logger.info(f"Waiting {delay:.2f} seconds before next request")
        time.sleep(delay)
    
    logger.info(f"Scraping completed. Found {len(all_gigs)} total opportunities")
    return all_gigs

def save_to_json(gigs, filename="opportunities.json"):
    """Save the scraped opportunities to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(gigs, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(gigs)} opportunities to {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to save to {filename}: {e}")
        return False

def merge_with_existing(new_gigs, filename="opportunities.json"):
    """Merge new gigs with existing ones, avoiding duplicates."""
    try:
        # Try to read existing file
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                existing_gigs = json.load(f)
            logger.info(f"Loaded {len(existing_gigs)} existing opportunities from {filename}")
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info(f"No existing opportunities file found or file is invalid. Creating new.")
            existing_gigs = []
        
        # Create a set of existing URLs to check for duplicates
        existing_urls = {gig["url"] for gig in existing_gigs}
        
        # Add only new gigs
        added_count = 0
        for gig in new_gigs:
            if gig["url"] not in existing_urls:
                existing_gigs.append(gig)
                existing_urls.add(gig["url"])
                added_count += 1
        
        # Save the merged list
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_gigs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Added {added_count} new opportunities. Total: {len(existing_gigs)}")
        return True
    except Exception as e:
        logger.error(f"Failed to merge opportunities: {e}")
        return False

def run():
    """Main function to run the Proletto Engine scraper."""
    try:
        # Run the scraper
        gigs = run_scraper()
        
        # Merge with existing opportunities
        success = merge_with_existing(gigs)
        
        return success
    except Exception as e:
        logger.error(f"Error in Proletto Engine: {e}")
        return False

if __name__ == "__main__":
    # When run directly, execute the scraper
    run()