#!/usr/bin/env python3
"""
Proletto Engine Colorado - Specialized web scraper for Colorado art opportunities
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

# Colorado specific sites to scrape
COLORADO_SITES = [
    # Colorado Arts Organizations
    "https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Denver-Arts-and-Venues/Denver-Public-Art",
    "https://www.colorado.gov/pacific/coarts/opportunities",
    "https://coloradocreativeindustries.org/opportunities/",
    "https://www.arts.gov/grants",
    "https://www.cbca.org/opportunities/",
    "https://redlineart.org/opportunities/",
    "https://denverarts.org/opportunities",
    "https://www.artsresourcenetwork.org/opportunities/",
    "https://artworks-loveland.org/opportunities/",
    "https://www.boulderarts.org/opportunities/",
    "https://www.culturaloffice.org/programs-services/peak-radar/peak-radar-jobs/",
    "https://www.artsfoco.org/opportunities/",
    
    # Colorado Museums and Institutions
    "https://denverartmuseum.org/en/about/careers",
    "https://www.clyffordstillmuseum.org/about-us/employment/",
    "https://www.botanicgardens.org/about/careers",
    "https://www.mca.org/about/employment/",
    "https://www.boulder.museum/about/employment/",
    "https://www.aspenartmuseum.org/about/job-opportunities",
    "https://www.coloradospringspioneersmuseum.org/about/employment/",
    "https://www.kirklandmuseum.org/about/employment-opportunities/",
    "https://www.colordmuseum.org/about/jobs-and-internships/",
    "https://www.cmbgallery.com/opportunities",
    
    # Colorado Universities and Art Schools
    "https://www.du.edu/human-resources/careers-at-du",
    "https://jobs.colorado.edu/",
    "https://www.coloradocollege.edu/offices/humanresources/employment/",
    "https://www.mines.edu/human-resources/careers/",
    "https://www.rmcad.edu/about/employment/",
    "https://www.uccs.edu/hr/employment-opportunities",
    "https://www.naropa.edu/about-naropa/employment/",
    "https://www.unco.edu/careers/",
    "https://www.csupueblo.edu/human-resources/",
    
    # Denver/Colorado Galleries and Art Spaces
    "https://www.davidevansstudio.com/opportunities/",
    "https://robischongallery.com/submissions/",
    "https://www.walkerfineart.com/call-for-artists",
    "https://www.showpenart.com/call-for-artists/",
    "https://www.abendgallery.com/submissions/",
    "https://www.tincollective.com/call-for-entries/",
    "https://www.soniashandleygallery.com/call-for-artists/",
    "https://www.k-contemporaryart.com/submissions",
    "https://www.forevergalleries.com/artist-submissions/",
    "https://www.rule.gallery/submissions/",
    "https://www.vailcollective.com/art-submissions/"
]

# Colorado specific keywords
COLORADO_KEYWORDS = [
    # Colorado specific terms
    "denver artist", "colorado artist", "denver arts", "colorado arts", "denver art scene",
    "co grant", "colorado grant", "denver grant", "co residency", "colorado residency", 
    "denver residency", "colorado opportunity", "denver opportunity", "co opportunity",
    "colorado commission", "denver commission", "colorado fellowship", "denver fellowship", 
    "co fellowship", "colorado public art", "denver public art", "co public art",
    "colorado artists council", "denver artists council", "co artists council",
    "denver cultural affairs", "colorado cultural commission", "denver percent for art",
    "boulder arts", "fort collins arts", "colorado springs arts", "aspen arts",
    "santa fe drive arts", "art district on santa fe", "rino art district",
    "rocky mountain artist", "colorado creative", "front range arts"
]

# Colorado locations
COLORADO_LOCATIONS = [
    # Denver and neighborhoods
    "denver", "downtown denver", "rino", "river north art district", "lodo", "lower downtown", 
    "lohi", "lower highlands", "highland", "five points", "capitol hill", "cherry creek", 
    "washington park", "baker", "south broadway", "santa fe arts district", "art district on santa fe", 
    "golden triangle", "city park", "congress park", "uptown", "curtis park", "cole", "whittier", 
    "berkeley", "tennyson", "sunnyside", "sloan lake", "west colfax", "park hill", "stapleton", 
    "montbello", "green valley ranch", "montclair", "hale", "mayfair", "virginia village", 
    "glendale", "university", "university hills", "hampden", "south denver", "north denver", 
    "east denver", "west denver",
    
    # Colorado regions and cities
    "boulder", "fort collins", "colorado springs", "aurora", "lakewood", "arvada", "westminster",
    "thornton", "centennial", "pueblo", "grand junction", "greeley", "longmont", "loveland",
    "broomfield", "castle rock", "parker", "littleton", "northglenn", "commerce city", "englewood",
    "wheat ridge", "lafayette", "golden", "louisville", "evans", "brighton", "montrose",
    "aspen", "vail", "breckenridge", "steamboat springs", "telluride", "durango", "estes park",
    "glenwood springs", "crested butte", "salida", "evergreen", "conifer", "idaho springs",
    
    # Colorado regions
    "front range", "western slope", "eastern plains", "san luis valley", "rocky mountains",
    "northern colorado", "southern colorado", "central colorado", "western colorado",
    "eastern colorado", "boulder county", "jefferson county", "arapahoe county", "douglas county",
    "el paso county", "larimer county", "weld county", "pueblo county", "mesa county",
    
    # Colorado state
    "colorado", "co", "centennial state", "denver metro", "greater denver", "metro denver",
    "denver metro area", "colorado rockies", "mile high city", "denver county", "adams county",
    "denver area", "boulder area", "fort collins area", "colorado springs area", "front range region"
]

# Create the Colorado engine using the factory
engine = create_state_engine(
    state_name="Colorado",
    state_sites=COLORADO_SITES,
    state_keywords=COLORADO_KEYWORDS,
    state_locations=COLORADO_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Colorado scraper
    run()