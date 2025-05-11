#!/usr/bin/env python3
"""
Proletto Engine California - Specialized web scraper for California art opportunities
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
logger = logging.getLogger('proletto_engine_california')

HEADERS = {
    'User-Agent': 'ProlettoBot/1.0 (+https://www.myproletto.com)'
}

# California-focused sites
CALIFORNIA_SITES = [
    # California City Art Programs
    "https://www.lacountyarts.org/funding/grants-opportunities",
    "https://sfac.org/grants/",
    "https://www.sfartscommission.org/content/public-art-opportunities",
    "https://culture.lacity.org/grants",
    "https://www.santamonica.gov/arts/opportunities",
    "https://www.culvercity.org/Services/Parks-Recreation-Culture/Cultural-Affairs/Opportunities-for-Artists",
    "https://www.sandiego.gov/arts-culture/funding",
    "https://www.oaklandca.gov/topics/public-art-in-oakland",
    "https://www.artslb.org/grants",
    "https://www.ci.berkeley.ca.us/city_manager/civic_arts/civic_arts_grants.asp",
    "https://www.cityofsacramento.org/Convention-Cultural-Services/Cultural-Services/Arts-Education/Funding-Opportunities",
    "https://www.sanjoseca.gov/your-government/departments/office-of-cultural-affairs/grants",
    "https://www.anaheim.net/570/Public-Art-Program",
    "https://www.cityofpasadena.net/planning/arts-and-cultural-affairs/cultural-grants/",
    "https://www.fresnoarts.org/opportunities",
    "https://www.cityofpalmssprings.com/642/Arts-Commission",
    
    # California Arts Organizations
    "https://www.calartscouncil.org/grant-opportunities/",
    "https://www.artsforla.org/opportunities",
    "https://www.artsoc.org/grants-and-scholarships",
    "https://www.grantmakers.io/profiles/v0/942681711-san-francisco-foundation/",
    "https://arts.berkeley.edu/opportunities/",
    "https://www.sdvisualarts.net/sdvan_new/opportunity.php",
    "https://www.artsconnectionnetwork.org/opportunities/",
    "https://www.sonomaarts.org/grants-and-funding/",
    "https://nomadartsca.org/opportunities",
    "https://www.artelagunanow.com/",
    
    # California Arts Schools
    "https://arts.ucdavis.edu/opportunities-and-jobs",
    "https://arts.ucla.edu/opportunities/",
    "https://art.ucsc.edu/opportunities",
    "https://calarts.edu/information-for/for-students/career-resources/opportunities",
    "https://www.otis.edu/career-services",
    "https://arts.stanford.edu/student-opportunities/",
    "https://www.artcenter.edu/about/get-involved/job-opportunities.html",
    
    # California Museums and Galleries
    "https://www.hammer.ucla.edu/opportunities",
    "https://moca.org/about/jobs",
    "https://www.getty.edu/about/opportunities/",
    "https://www.lacma.org/about/careers",
    "https://www.sfmoma.org/careers/",
    "https://www.thebroad.org/employment",
    "https://gettycenter.edu/opportunities/",
    "https://www.huntington.org/employment",
    "https://www.norton-simon.org/about/careers/",
    "https://www.crockerart.org/careers",
    "https://mcasd.org/about/job-opportunities",
    "https://www.sdmart.org/get-involved/careers/",
    
    # California Artist Residencies
    "https://headlands.org/program/artist-in-residence/",
    "https://www.djerassi.org/apply/",
    "https://www.montalvoarts.org/programs/sally_and_don_lucas/",
    "https://www.facebook.com/groups/laartistresidencyopp/",
    "https://apply.airsenal.org",
    "https://www.oxbowschool.org/fellowship",
    "https://heybardstudios.org/residency/",
    "https://www.yaddo.org/apply/",
    "https://www.grandcentralartcenter.com/artist-in-residence-program/",
    "https://www.hemisfair.org/arts-culture/artist-in-residence/"
]

CALIFORNIA_KEYWORDS = [
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
    "art scholarship", "cultural funding", "creative funding", "art support", "arts grant",
    
    # California-specific keywords
    "california artist", "california grant", "california residency", "california opportunity",
    "california public art", "california commission", "california fellowship", "california artists"
]

def is_relevant(text):
    """Check if text contains any relevant keywords."""
    return any(keyword in text.lower() for keyword in CALIFORNIA_KEYWORDS)

def scrape_site(url):
    """
    Wrapper for the improved scraper
    """
    try:
        return improved_scrape_site(url, CALIFORNIA_KEYWORDS)
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return []

def run_scraper():
    """Run the California scraper on all target sites."""
    logger.info("Starting Proletto Engine California - specialized scraper")
    
    all_gigs = []
    for site in CALIFORNIA_SITES:
        gigs = scrape_site(site)
        all_gigs.extend(gigs)
        # Add a polite delay between requests
        delay = random.uniform(1.5, 3.5)
        logger.info(f"Waiting {delay:.2f} seconds before next request")
        time.sleep(delay)
    
    logger.info(f"California scraping completed. Found {len(all_gigs)} total opportunities")
    return all_gigs

def merge_with_existing(new_gigs, filename="opportunities.json"):
    """Merge new California gigs with existing ones, avoiding duplicates."""
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
        
        logger.info(f"Added {added_count} new California opportunities. Total: {len(existing_gigs)}")
        return True
    except Exception as e:
        logger.error(f"Failed to merge opportunities: {e}")
        return False

def run():
    """Main function to run the California scraper."""
    try:
        # Run the scraper
        gigs = run_scraper()
        
        # Merge with existing opportunities
        success = merge_with_existing(gigs)
        
        return success
    except Exception as e:
        logger.error(f"Error in Proletto Engine California: {e}")
        return False

if __name__ == "__main__":
    # When run directly, execute the California scraper
    run()