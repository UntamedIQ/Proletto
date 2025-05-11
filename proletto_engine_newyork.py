#!/usr/bin/env python3
"""
Proletto Engine New York - Specialized web scraper for New York art opportunities
"""
import logging
from proletto_engine_state_factory import create_state_engine

# Import improved scraper
from improved_scraper import improved_scrape_site

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

# New York specific sites to scrape
NEW_YORK_SITES = [
    # New York City Arts Organizations
    "https://www.culturalaffairs.nyc/opportunities",
    "https://www.nyfa.org/opportunities/",
    "https://www.nyfa.org/jobs/",
    "https://creative-capital.org/jobs/",
    "https://lmcc.net/resources/opportunities/",
    "https://www.artswestchester.org/artists/opportunities-for-artists/",
    "https://madamabutterfly.org/opportunities/",
    "https://www.nycgovparks.org/art-and-antiquities/public-art-opportunities",
    "https://www.newyorkfoundation.org/grants-fellowships/",
    "https://www.brooklynartscouncil.org/opportunities",
    "https://www.artsandbusinessny.org/careers/",
    
    # New York City Museums and Institutions
    "https://www.metmuseum.org/about-the-met/career-opportunities",
    "https://www.moma.org/about/get-involved/jobs/",
    "https://whitney.org/about/job-postings",
    "https://www.guggenheim.org/careers",
    "https://new.artmuseum.org/about/job-opportunities/",
    "https://www.nycmer.org/job-board",
    "https://www.thejewishmuseum.org/careers",
    "https://www.nbm.org/about-us/careers/",
    "https://bronxmuseum.org/careers",
    "https://www.brooklynmuseum.org/about/careers",
    "https://www.queensmuseum.org/opportunities",
    
    # New York Universities and Art Schools
    "https://nyadaa-csm.symplicity.com/",
    "https://www.nycoproductions.com/jobs-internships",
    "https://www.nyfa.edu/jobs/",
    "https://www.pratt.edu/the-institute/administration/human-resources/employment/",
    "https://jobs.sva.edu/",
    "https://www.newschool.edu/parsons/careers-opportunities/",
    "https://www.fitnyc.edu/careers/",
    "https://cooper.edu/about/employment-opportunities",
    
    # New York Galleries and Art Spaces
    "https://www.nyartbeat.com/opportunities/",
    "https://www.internationalartstudio.org/",
    "https://iscp-nyc.org/apply",
    "https://www.chashama.org/programs/",
    "https://pioneerworks.org/jobs/",
    "https://www.abladeofgrass.org/opportunities/",
    "https://www.pacegallery.com/careers/",
    "https://gagosian.com/careers/",
    "https://www.davidzwirner.com/careers",
    "https://www.mariangoodman.com/contact-us",
    "https://www.hauserwirth.com/careers"
]

# New York specific keywords
NEW_YORK_KEYWORDS = [
    # New York specific terms
    "new york artist", "nyc artist", "new york arts", "nyc arts", "new york art scene",
    "brooklyn artist", "queens artist", "bronx artist", "manhattan artist", "staten island artist",
    "ny grant", "new york grant", "nyc grant", "ny residency", "new york residency", "nyc residency",
    "new york opportunity", "nyc opportunity", "ny opportunity", "new york commission",
    "nyc commission", "new york fellowship", "nyc fellowship", "ny fellowship",
    "new york public art", "nyc public art", "ny public art", "new york artists council",
    "nyc artists council", "ny artists council", "new york cultural affairs",
    "percentage for art", "cultural affairs", "nyc cultural affairs"
]

# New York locations
NEW_YORK_LOCATIONS = [
    # New York City and boroughs
    "new york", "new york city", "nyc", "manhattan", "brooklyn", "queens", "the bronx", "staten island", 
    "long island", "williamsburg", "bushwick", "astoria", "harlem", "chelsea", "soho", "tribeca", 
    "dumbo", "lower east side", "upper east side", "upper west side", "midtown",
    
    # New York regions and cities
    "hudson valley", "westchester", "albany", "buffalo", "rochester", "syracuse", "ithaca",
    "poughkeepsie", "new rochelle", "yonkers", "utica", "binghamton", "schenectady",
    "kingston", "newburgh", "beacon", "cold spring", "woodstock", "new paltz", "sleepy hollow",
    "tarrytown", "saratoga springs", "lake placid", "montauk", "hamptons", "hudson",
    
    # New York state
    "new york state", "nys", "upstate new york", "downstate new york", "western new york", 
    "central new york", "finger lakes", "adirondacks", "catskills", "niagara falls"
]

# Create the New York engine using the factory
engine = create_state_engine(
    state_name="New York",
    state_sites=NEW_YORK_SITES,
    state_keywords=NEW_YORK_KEYWORDS,
    state_locations=NEW_YORK_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the New York scraper
    run()