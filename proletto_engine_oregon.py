#!/usr/bin/env python3
"""
Proletto Engine Oregon - Specialized web scraper for Oregon art opportunities
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

# Oregon specific sites to scrape
OREGON_SITES = [
    # Oregon Arts Organizations
    "https://racc.org/resources/opportunities/",
    "https://oregonartscommission.org/grants/",
    "https://www.oregonartswatch.org/jobs-opportunities/",
    "https://portlandartmuseum.org/about/careers/",
    "https://calligram.org/opportunities/",
    "https://www.pica.org/jobs-and-internships/",
    "https://www.artslandia.com/category/opportunities/",
    "https://www.artswatch.org/jobs-opportunities/",
    "https://artsimpact.org/programs/",
    "https://orartswatch.org/jobs-opportunities/",
    "https://www.oregonsymphony.org/about/careers/",
    "https://www.artcityeugene.com/opportunities",
    
    # Oregon Museums and Institutions
    "https://portlandartmuseum.org/about/careers/",
    "https://www.jordanschnitzer.org/opportunities/",
    "https://www.highdesertmuseum.org/about/jobs/",
    "https://powellsbooks.com/info/jobs",
    "https://www.ohs.org/about-us/employment.cfm",
    "https://museumofsex.com/jobs-internships/",
    "https://www.tillamookheadlightherald.com/community/arts/",
    "https://pittockmuseum.org/about/jobs-volunteer-opportunities/",
    "https://omonline.org/about-omsi/jobs/",
    
    # Oregon Universities and Art Schools
    "https://www.pdx.edu/careers/",
    "https://careers.uoregon.edu/",
    "https://jobs.oregonstate.edu/",
    "https://www.pnca.edu/about/employment",
    "https://www.reed.edu/human_resources/staffsearch/",
    "https://www.lclark.edu/offices/human_resources/employment/",
    "https://www.linfield.edu/hr/employment-opportunities.html",
    "https://www.willamette.edu/offices/hr/employment/",
    "https://www.sou.edu/hrs/employment/",
    
    # Portland/Oregon Galleries and Art Spaces
    "https://www.blueskygallery.org/submit",
    "https://www.froelickgallery.com/artist-submissions",
    "https://www.pdxcontemporaryart.com/submissions",
    "https://www.adamsandsolliersgallery.com/submissions",
    "https://www.disjecta.org/opportunities",
    "https://www.nationalgallery.com/opportunities",
    "https://www.portlandartdealers.org/",
    "https://stumptown.com/art-submissions",
    "https://www.grayliterature.org/submissions",
    "https://www.wiswallartcollective.com/submissions/",
    "https://www.scalehouse.org/opportunities/"
]

# Oregon specific keywords
OREGON_KEYWORDS = [
    # Oregon specific terms
    "portland artist", "oregon artist", "portland arts", "oregon arts", "portland art scene",
    "or grant", "oregon grant", "portland grant", "or residency", "oregon residency", 
    "portland residency", "oregon opportunity", "portland opportunity", "or opportunity",
    "oregon commission", "portland commission", "oregon fellowship", "portland fellowship", 
    "or fellowship", "oregon public art", "portland public art", "or public art",
    "oregon artists council", "portland artists council", "or artists council",
    "portland cultural affairs", "oregon cultural commission", "portland percent for art",
    "portland open studios", "pacific northwest arts", "willamette valley arts",
    "eugene arts", "bend arts", "salem arts", "ashland arts", "oregon shakespeare",
    "portland creative", "portland makers", "pnw artist"
]

# Oregon locations
OREGON_LOCATIONS = [
    # Portland and neighborhoods
    "portland", "northwest portland", "pearl district", "downtown portland", "old town", "chinatown", 
    "goose hollow", "southwest portland", "south waterfront", "sellwood", "southeast portland", 
    "hawthorne", "belmont", "division", "clinton", "richmond", "brooklyn", "eastmoreland", 
    "woodstock", "reed", "mt tabor", "montavilla", "foster-powell", "lents", "northeast portland", 
    "alberta arts district", "mississippi", "williams", "irvington", "lloyd district", "hollywood", 
    "rose city park", "beaumont", "cully", "north portland", "st johns", "university park", 
    "portsmouth", "kenton", "arbor lodge", "overlook", "boise", "eliot", "piedmont",
    
    # Oregon regions and cities
    "eugene", "salem", "bend", "corvallis", "springfield", "albany", "medford", "ashland",
    "grants pass", "klamath falls", "roseburg", "astoria", "cannon beach", "lincoln city",
    "newport", "florence", "hood river", "pendleton", "la grande", "baker city", "ontario",
    "coos bay", "the dalles", "mcminnville", "newberg", "tigard", "beaverton", "hillsboro",
    "gresham", "clackamas", "lake oswego", "west linn", "oregon city", "milwaukie", "tualatin",
    "wilsonville", "woodburn", "tillamook", "seaside",
    
    # Oregon regions
    "willamette valley", "columbia river gorge", "oregon coast", "southern oregon",
    "central oregon", "eastern oregon", "mt hood", "crater lake", "pacific northwest",
    "rogue valley", "umpqua valley", "high desert", "cascade mountains", "blue mountains",
    
    # Oregon state
    "oregon", "or", "beaver state", "portland metro", "greater portland", "multnomah county",
    "washington county", "clackamas county", "lane county", "marion county", "jackson county",
    "deschutes county", "linn county", "douglas county", "yamhill county", "josephine county",
    "clatsop county", "hood river county", "columbia county", "coos county", "curry county",
    "tillamook county", "lincoln county", "polk county", "benton county", "jefferson county"
]

# Create the Oregon engine using the factory
engine = create_state_engine(
    state_name="Oregon",
    state_sites=OREGON_SITES,
    state_keywords=OREGON_KEYWORDS,
    state_locations=OREGON_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Oregon scraper
    run()