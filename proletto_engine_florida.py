#!/usr/bin/env python3
"""
Proletto Engine Florida - Specialized web scraper for Florida art opportunities
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

# Florida specific sites to scrape
FLORIDA_SITES = [
    # Florida Arts Organizations
    "https://www.arts.gov/grants",
    "https://floridaarts.org/opportunities/",
    "https://www.miamidadearts.org/opportunities/jobs-opportunities",
    "https://miaminewdramatists.org/opportunities",
    "https://artscalendar.com/jobs-calls/",
    "https://www.browardarts.org/programs/opportunities/",
    "https://arts.pensacola.org/opportunities/",
    "https://creativepinellas.org/opportunities/",
    "https://tampaarts.org/opportunities/",
    "https://www.orlandoatplay.com/categories/job-opportunities/",
    "https://unitedarts.cc/grantsstipends/",
    "https://www.artsbrevard.org/for-artists/",
    
    # Florida Museums and Institutions
    "https://www.pamm.org/en/about/jobs/",
    "https://www.bocamuseum.org/about/employment-opportunities",
    "https://www.norton.org/about/careers",
    "https://www.moafl.org/about/employment",
    "https://www.morikami.org/about/careers/",
    "https://www.dali.org/about-us/employment/",
    "https://www.thebass.org/about/career-opportunities",
    "https://www.ringling.org/careers",
    "https://www.morsemuseum.org/employment-opportunities",
    "https://www.frogtowngreen.com/join-us/",
    
    # Florida Universities and Art Schools
    "https://www.ufl.edu/work-at-ufl/",
    "https://www.fsu.edu/faculty-staff/employment/",
    "https://www.usf.edu/work-at-usf/",
    "https://www.fau.edu/jobs/",
    "https://www.miami.edu/careers/",
    "https://www.fit.edu/employment/",
    "https://www.ringling.edu/careers-at-ringling/",
    "https://www.newcollege.edu/about/employment/",
    "https://www.fscj.edu/human-resources/employment",
    
    # Florida Galleries and Art Spaces
    "https://www.miamilivearts.org/opportunities/",
    "https://www.artbasel.com/",
    "https://www.thewolf.fiu.edu/opportunities/",
    "https://yelenart.com/opportunities/",
    "https://www.artandculturecenter.org/open-calls",
    "https://www.maccfineart.com/artists/submissions/",
    "https://www.bakehouseartcomplex.org/opportunities",
    "https://www.dimensionsvariable.net/opportunities/",
    "https://www.emmanuellegalleriesinc.com/submissions/",
    "https://www.artroomgalleries.com/call-for-artists/",
    "https://www.bocaguild.org/calls-for-artists/"
]

# Florida specific keywords
FLORIDA_KEYWORDS = [
    # Florida specific terms
    "miami artist", "orlando artist", "tampa artist", "florida artist", "miami arts", "florida arts",
    "miami art scene", "florida art scene", "fl grant", "florida grant", "miami grant", "fl residency", 
    "florida residency", "miami residency", "florida opportunity", "miami opportunity", "fl opportunity",
    "florida commission", "miami commission", "florida fellowship", "miami fellowship", 
    "fl fellowship", "florida public art", "miami public art", "fl public art",
    "florida artists council", "miami artists council", "fl artists council",
    "miami arts commission", "florida cultural affairs", "art basel miami",
    "wynwood arts", "little havana arts", "design district", "art palm beach", "art ft lauderdale",
    "south florida arts", "gulf coast arts"
]

# Florida locations
FLORIDA_LOCATIONS = [
    # Miami and neighborhoods
    "miami", "miami beach", "south beach", "wynwood", "design district", "little havana", 
    "brickell", "downtown miami", "coral gables", "coconut grove", "midtown miami",
    "edgewater", "upper east side", "little haiti", "overtown", "allapattah",
    "key biscayne", "doral", "hialeah", "north miami", "miami shores", "aventura",
    "sunny isles", "bal harbour", "surfside", 
    
    # Florida regions and cities
    "orlando", "tampa", "st. petersburg", "jacksonville", "fort lauderdale", "west palm beach",
    "boca raton", "delray beach", "hollywood", "pompano beach", "sarasota", "naples",
    "tallahassee", "gainesville", "pensacola", "clearwater", "lakeland", "daytona beach",
    "melbourne", "ocala", "winter park", "winter garden", "st. augustine", "key west",
    "panama city", "destin", "fort myers", "cape coral", "bradenton", "palm beach",
    "jupiter", "vero beach", "port st. lucie", "kissimmee", "cocoa beach",
    
    # Florida state
    "florida", "fl", "sunshine state", "south florida", "central florida", "north florida",
    "florida panhandle", "florida keys", "treasure coast", "space coast", "nature coast",
    "emerald coast", "gold coast", "first coast", "tampa bay area", "greater orlando",
    "greater miami", "metro miami", "metro orlando", "gulf coast", "atlantic coast",
    "broward county", "miami-dade county", "palm beach county", "pinellas county",
    "hillsborough county", "orange county", "duval county", "leon county", "volusia county",
    "alachua county", "escambia county", "seminole county", "sarasota county", "brevard county"
]

# Create the Florida engine using the factory
engine = create_state_engine(
    state_name="Florida",
    state_sites=FLORIDA_SITES,
    state_keywords=FLORIDA_KEYWORDS,
    state_locations=FLORIDA_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Florida scraper
    run()