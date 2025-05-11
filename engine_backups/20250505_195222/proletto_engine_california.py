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
    """Scrape a single site for art opportunities."""
    try:
        logger.info(f"Scraping California site: {url}")
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)
        
        gigs = []
        for link in links:
            title = link.get_text(strip=True)
            href = link['href']
            
            if not is_relevant(title) or not href or len(title) < 5:
                continue
                
            # Format the URL correctly
            job_url = href if href.startswith("http") else f"{url.rstrip('/')}/{href.lstrip('/')}"
            
            # Try to find any description or location near the link
            location = ""
            description = ""
            
            # Check for parent elements that might contain more info
            parent = link.parent
            if parent:
                # Look for location indicators
                location_text = parent.get_text()
                location_keywords = [
                    # California cities and regions
                    "los angeles", "san francisco", "san diego", "santa monica", "long beach",
                    "oakland", "berkeley", "sacramento", "san jose", "pasadena", "culver city",
                    "laguna beach", "palm springs", "santa barbara", "venice", "malibu", "carmel",
                    "monterey", "napa", "sonoma", "palo alto", "san luis obispo", "eureka",
                    "santa cruz", "oceanside", "la jolla", "encinitas", "joshua tree", "ojai",
                    "huntington beach", "redondo beach", "sausalito", "mill valley", "tiburon",
                    "healdsburg", "sebastopol", "petaluma", "davis", "santa rosa", "irvine",
                    "silver lake", "echo park", "downtown la", "arts district", "west hollywood",
                    "north hollywood", "mission district", "haight-ashbury", "castro", "venice beach",
                    "downtown san diego", "la mesa", "coronado", "carlsbad", "del mar",
                    "northern california", "southern california", "bay area", "socal", "norcal",
                    "los angeles county", "orange county", "san diego county", "alameda county",
                    "contra costa county", "san mateo county", "santa clara county", "marin county",
                    
                    # Terms indicating location info
                    "location:", "based in", "located in", "position in", "job in", "working in", 
                    "onsite at", "position at", "based at", "office in", "workplace in", 
                    
                    # Work arrangements
                    "remote", "remote work", "work from home", "hybrid", "onsite", "in-person",
                    "california", "ca", "california based"
                ]
                
                for keyword in location_keywords:
                    if keyword in location_text.lower():
                        # Extract a small snippet around the keyword
                        start = max(0, location_text.lower().find(keyword) - 5)
                        end = min(len(location_text), location_text.lower().find(keyword) + 20)
                        location = location_text[start:end].strip()
                        break
                
                # Try to extract a short description
                desc_siblings = parent.find_next_siblings()
                if desc_siblings and len(desc_siblings) > 0:
                    for sibling in desc_siblings[:2]:  # Check first two siblings
                        sibling_text = sibling.get_text(strip=True)
                        if sibling_text and len(sibling_text) > 20 and len(sibling_text) < 200:
                            description = sibling_text
                            break
            
            # Get the source name from the URL
            source = url.split("//")[1].split("/")[0].replace("www.", "")
            
            # Set the type to "california" for filtering purposes
            opp_type = "california"
            
            gigs.append({
                "title": title,
                "url": job_url,
                "location": location,
                "description": description,
                "source": source,
                "type": opp_type,
                "scraped_date": datetime.utcnow().isoformat()
            })
        
        logger.info(f"Found {len(gigs)} California opportunities on {url}")
        return gigs
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