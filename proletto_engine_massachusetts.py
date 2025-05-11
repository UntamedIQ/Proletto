#!/usr/bin/env python3
"""
Proletto Engine Massachusetts - Specialized web scraper for Massachusetts art opportunities
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

# Massachusetts specific sites to scrape
MASSACHUSETTS_SITES = [
    # Massachusetts Arts Organizations
    "https://www.mass-culture.org/jobs_internships.aspx",
    "https://massculturalcouncil.org/artists-art/funding-for-artists/",
    "https://artsboston.org/jobs/",
    "https://www.bostonarts.org/opportunities/",
    "https://www.artsworcester.org/opportunities",
    "https://www.fortpointarts.org/opportunities/",
    "https://www.nefa.org/grants",
    "https://www.bostonusa.com/industry-resources/creative-economy/",
    "https://artsworcester.org/call-for-art/",
    "https://www.bostonculture.org/opportunities",
    "https://www.cambridgeart.org/opportunities/",
    
    # Massachusetts Museums and Institutions
    "https://www.mfa.org/employment",
    "https://www.icaboston.org/opportunities",
    "https://www.gardnermuseum.org/about/employment",
    "https://cmh.org/about/employment/",
    "https://decordova.org/about/opportunities/",
    "https://massart.edu/careers",
    "https://www.berkshiremuseum.org/about/employment/",
    "https://www.pem.org/about-pem/careers",
    "https://www.massmoca.org/employment/",
    "https://www.Norman-rockwell.org/about/employment/",
    
    # Massachusetts Universities and Art Schools
    "https://www.massart.edu/careers",
    "https://www.berklee.edu/careers",
    "https://www.northeastern.edu/art/opportunities/",
    "https://www.tufts.edu/about/work-at-tufts",
    "https://staffcareers.umass.edu/",
    "https://www.bu.edu/cfa/about/employment/",
    "https://boston.academyart.edu/about/jobs.html",
    "https://www.montserrat.edu/about/employment/",
    "https://smfa.tufts.edu/about/opportunities",
    
    # Boston/Massachusetts Galleries and Art Spaces
    "https://www.sashawaldfogel.com/opportunities",
    "https://www.kingstongallery.com/artist-opportunities",
    "https://mills-gallery.bcaonline.org/opportunities/",
    "https://www.gallerykayafine.com/opportunities/",
    "https://www.thegibsonhousegallery.com/opportunities/",
    "https://chasecontemporary.com/artist-submissions/",
    "https://abigailogilvy.com/call-for-art/",
    "https://www.followtheartroadgallery.com/submissions/",
    "https://www.liagallery.com/submissions",
    "https://www.howlandcreative.com/opportunities/"
]

# Massachusetts specific keywords
MASSACHUSETTS_KEYWORDS = [
    # Massachusetts specific terms
    "boston artist", "massachusetts artist", "boston arts", "massachusetts arts", "boston art scene",
    "ma grant", "massachusetts grant", "boston grant", "ma residency", "massachusetts residency", 
    "boston residency", "massachusetts opportunity", "boston opportunity", "ma opportunity",
    "massachusetts commission", "boston commission", "massachusetts fellowship", "boston fellowship",
    "ma fellowship", "massachusetts public art", "boston public art", "ma public art",
    "massachusetts artists council", "boston artists council", "ma artists council",
    "boston cultural council", "mass cultural council", "boston percent for art",
    "cambridge arts", "somerville arts", "worcester arts", "cape cod arts", "berkshires arts",
    "western mass arts", "pioneer valley arts"
]

# Massachusetts locations
MASSACHUSETTS_LOCATIONS = [
    # Boston and neighborhoods
    "boston", "cambridge", "somerville", "brookline", "newton", "quincy", "malden", "medford",
    "back bay", "south end", "beacon hill", "north end", "south boston", "dorchester", "roxbury",
    "jamaica plain", "charlestown", "east boston", "allston", "brighton", "fenway", "kenmore",
    "seaport", "fort point", "leather district", "chinatown", "downtown boston", "waterfront",
    "financial district", "west end", "harvard square", "central square", "kendall square", 
    "inman square", "porter square", "davis square", "union square",
    
    # Massachusetts regions and cities
    "worcester", "springfield", "lowell", "brockton", "new bedford", "lynn", "fall river",
    "salem", "northampton", "amherst", "pittsfield", "provincetown", "gloucester", "newburyport",
    "holyoke", "greenfield", "beverly", "framingham", "waltham", "concord", "lexington",
    "cape cod", "martha's vineyard", "nantucket", "berkshires", "pioneer valley", "merrimack valley",
    "south shore", "north shore", "metrowest", "western massachusetts", "central massachusetts", 
    
    # Massachusetts state
    "massachusetts", "ma", "mass", "commonwealth of massachusetts", "eastern massachusetts",
    "western mass", "central mass", "suffolk county", "middlesex county", "essex county",
    "norfolk county", "plymouth county", "bristol county", "barnstable county", "hampden county",
    "hampshire county", "berkshire county", "franklin county", "dukes county", "nantucket county",
    "greater boston", "metro boston"
]

# Create the Massachusetts engine using the factory
engine = create_state_engine(
    state_name="Massachusetts",
    state_sites=MASSACHUSETTS_SITES,
    state_keywords=MASSACHUSETTS_KEYWORDS,
    state_locations=MASSACHUSETTS_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Massachusetts scraper
    run()