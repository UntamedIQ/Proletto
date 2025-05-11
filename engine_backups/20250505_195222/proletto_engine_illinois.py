#!/usr/bin/env python3
"""
Proletto Engine Illinois - Specialized web scraper for Illinois art opportunities
"""
import logging
from proletto_engine_state_factory import create_state_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

# Illinois specific sites to scrape
ILLINOIS_SITES = [
    # Chicago and Illinois Arts Organizations
    "https://www.chicago.gov/city/en/depts/dca/provdrs/grants.html",
    "https://www.chicagoartistscoalition.org/resources",
    "https://arts.illinois.gov/grants-programs/grants",
    "https://www.ilhumanities.org/program/grants/",
    "https://www.artsandculture.google.com/partner/art-institute-of-chicago",
    "https://www.artschicago.org/resources",
    "https://www.cpag.net/calls-for-artists",
    "https://www.hydeparkart.org/opportunities/",
    "https://threewalls.org/apply/",
    "https://www.3arts.org/apply/",
    "https://www.chicagoartistsresource.org/",
    "https://www.artsclubchicago.org/programs/",
    
    # Illinois Museums and Institutions
    "https://www.artic.edu/careers",
    "https://mcachicago.org/About/Jobs",
    "https://www.fieldmuseum.org/about/careers",
    "https://www.smartmuseum.uchicago.edu/about/opportunities/",
    "https://nationalmuseumofmexicanart.org/about-us/employment",
    "https://www.dusablemuseum.org/jobs-internships/",
    "https://wrightwood659.org/opportunities/",
    "https://www.ilholocaustmuseum.org/careers/",
    
    # Illinois Universities and Art Schools
    "https://www.saic.edu/about/work-at-saic",
    "https://art.illinois.edu/index.php/prospective/opportunities",
    "https://careers.colum.edu/postings/search",
    "https://www.niu.edu/artsci/art/jobs/index.shtml",
    "https://www.siu.edu/jobs/",
    "https://illinoisstate.edu/jobs/",
    
    # Chicago Galleries and Art Spaces
    "https://www.hydeparkcenter.org/artists-in-residence",
    "https://www.richardnortongallery.com/",
    "https://www.kavigupta.com/",
    "https://www.corbettvsdempsey.com/",
    "https://rhona.hoffman.com/opportunities/",
    "https://www.documentspace.com/submissions",
    "https://www.prairieartsguild.org/artist-opportunities",
    "https://www.chicagogallerynews.com/calls-for-artists",
    "https://www.chistudiovacancy.com/",
    "https://www.chicagoartistscoalition.org/field-trip",
    "https://www.artsincubatorchicago.org/"
]

# Illinois specific keywords
ILLINOIS_KEYWORDS = [
    # Illinois specific terms
    "chicago artist", "illinois artist", "chicago arts", "illinois arts", "chicago art scene",
    "il grant", "illinois grant", "chicago grant", "il residency", "illinois residency", "chicago residency",
    "illinois opportunity", "chicago opportunity", "il opportunity", "illinois commission",
    "chicago commission", "illinois fellowship", "chicago fellowship", "il fellowship",
    "illinois public art", "chicago public art", "il public art", "illinois artists council",
    "chicago artists council", "il artists council", "chicago cultural affairs",
    "chicago dept of cultural affairs", "chicago public art program", "chicago percent for art"
]

# Illinois locations
ILLINOIS_LOCATIONS = [
    # Chicago and neighborhoods
    "chicago", "downtown chicago", "loop", "river north", "wicker park", "bucktown", "logan square", 
    "pilsen", "bridgeport", "hyde park", "bronzeville", "south loop", "west loop", "south side", 
    "north side", "gold coast", "lincoln park", "lakeview", "andersonville", "uptown", "rogers park",
    "edgewater", "ravenswood", "ukrainian village", "humboldt park", "avondale", "old town",
    
    # Illinois regions and cities
    "evanston", "oak park", "cicero", "naperville", "schaumburg", "joliet", "rockford", "peoria",
    "springfield", "champaign", "urbana", "bloomington", "normal", "decatur", "galesburg",
    "carbondale", "quad cities", "aurora", "waukegan", "elgin", "dekalb", "skokie", "wilmette",
    "winnetka", "lake forest", "highland park", "glencoe", "northbrook", "glenview",
    
    # Illinois state
    "illinois", "il", "northern illinois", "southern illinois", "western illinois", 
    "central illinois", "chicagoland", "metro chicago", "cook county", "lake county",
    "dupage county", "kane county", "will county", "mchenry county"
]

# Create the Illinois engine using the factory
engine = create_state_engine(
    state_name="Illinois",
    state_sites=ILLINOIS_SITES,
    state_keywords=ILLINOIS_KEYWORDS,
    state_locations=ILLINOIS_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Illinois scraper
    run()