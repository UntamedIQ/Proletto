#!/usr/bin/env python3
"""
Proletto Engine Texas - Specialized web scraper for Texas art opportunities
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

# Texas specific sites to scrape
TEXAS_SITES = [
    # Texas Arts Organizations
    "https://www.austintexas.gov/department/art-grants",
    "https://www.houstonartsalliance.com/opportunities",
    "https://artshound.com/category/job-postings",
    "https://www.taca-arts.org/grants/",
    "https://www.arts.texas.gov/resources/jobs-opportunities/",
    "https://www.texascommissiononthearts.org/",
    "https://www.dallasfoundation.org/grant-database.aspx",
    "https://dallasculture.org/opportunities/",
    "https://www.sanantonio.gov/arts/grants",
    "https://www.cultureworks.art/artvitality",
    
    # Texas Museums and Institutions
    "https://www.mfah.org/about/careers/",
    "https://www.blafferartmuseum.org/opportunities/",
    "https://thecontemporaryaustin.org/about/#careers",
    "https://blantonmuseum.org/about/career-opportunities/",
    "https://www.samuseum.org/about/opportunities/",
    "https://themodern.org/about/careers/",
    "https://www.kimbellart.org/careers-and-opportunities",
    "https://dma.org/about/career-opportunities",
    "https://www.nassaubaygallery.com/opportunities",
    "https://www.amoa.org/opportunities/",
    
    # Texas Universities and Art Schools
    "https://art.utexas.edu/resources/opportunities",
    "https://www.uh.edu/kgmca/about/employment/",
    "https://art.tamu.edu/employment/",
    "https://www.utdallas.edu/ah/about/employment/",
    "https://www.uta.edu/academics/schools-colleges/liberal-arts/departments/art/resources/opportunities",
    "https://www.utsa.edu/art/opportunities/",
    "https://txstatejobs.peopleadmin.com/",
    
    # Texas Galleries and Art Spaces
    "https://www.grayducktx.com/",
    "https://norternlightsstudio.com/events/",
    "https://www.flatlandgallery.com/",
    "https://www.grayduckgallery.com/",
    "https://www.lawndaleart.org/opportunities",
    "https://diverseworks.org/opportunities/",
    "https://www.projectrowhouses.org/opportunities",
    "https://graycontemporary.com/opportunities/",
    "https://hopeandthebutterflyeffect.com/index.htm",
    "https://galvestonartscenter.org/opportunities/",
    "https://www.camh.org/opportunities/",
    "https://www.glasstire.com/category/newswire/opportunities/",
    "https://www.facebook.com/groups/TexasArtistsJobs/"
]

# Texas specific keywords
TEXAS_KEYWORDS = [
    # Texas specific terms
    "texas artist", "austin artist", "houston artist", "dallas artist", "san antonio artist", 
    "fort worth artist", "el paso artist", "texas arts", "texas art scene", "lone star artist",
    "tx grant", "texas grant", "austin grant", "houston grant", "dallas grant", "tx residency", 
    "texas residency", "austin residency", "houston residency", "dallas residency",
    "texas opportunity", "austin opportunity", "houston opportunity", "dallas opportunity", 
    "tx opportunity", "texas commission", "austin commission", "houston commission",
    "texas fellowship", "austin fellowship", "houston fellowship", "dallas fellowship", 
    "tx fellowship", "texas public art", "austin public art", "houston public art",
    "dallas public art", "tx public art", "texas artists council", "austin arts commission",
    "houston arts alliance", "dallas cultural affairs", "texas cultural commission"
]

# Texas locations
TEXAS_LOCATIONS = [
    # Major cities
    "austin", "houston", "dallas", "san antonio", "fort worth", "el paso", "arlington", "corpus christi", 
    "plano", "lubbock", "irving", "laredo", "garland", "amarillo", "grand prairie", "brownsville", 
    "mckinney", "frisco", "pasadena", "killeen", "waco", "denton", "round rock", "galveston",
    "college station", "beaumont", "midland", "odessa", "tyler", "san marcos", "wichita falls",
    
    # Regions and areas
    "north texas", "east texas", "west texas", "south texas", "central texas", "texas gulf coast",
    "texas hill country", "dallas-fort worth", "dfw", "houston area", "austin area", "rio grande valley",
    "texas panhandle", "big bend", "east austin", "south austin", "north austin", "west austin", 
    "montrose", "the heights", "museum district", "deep ellum", "bishop arts district", 
    "southtown", "north side", "king william district", "pearl district",
    
    # Texas state
    "texas", "tx", "lone star state", "travis county", "harris county", "dallas county", 
    "bexar county", "tarrant county", "el paso county", "hidalgo county", "collin county"
]

# Create the Texas engine using the factory
engine = create_state_engine(
    state_name="Texas",
    state_sites=TEXAS_SITES,
    state_keywords=TEXAS_KEYWORDS,
    state_locations=TEXAS_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Texas scraper
    run()