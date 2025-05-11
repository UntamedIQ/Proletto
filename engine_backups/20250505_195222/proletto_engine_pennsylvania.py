#!/usr/bin/env python3
"""
Proletto Engine Pennsylvania - Specialized web scraper for Pennsylvania art opportunities
"""
import logging
from proletto_engine_state_factory import create_state_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot.log'
)

# Pennsylvania specific sites to scrape
PENNSYLVANIA_SITES = [
    # Pennsylvania Arts Organizations
    "https://www.pcah.us/grantopportunities",
    "https://www.pittsburghartscouncil.org/opportunities-for-artists-listing",
    "https://philadelphiaculturalalliance.org/opportunities/",
    "https://creativephl.org/opportunities/",
    "https://www.artsandculturepa.com/opportunties",
    "https://www.pcca.net/opportunities",
    "https://paarts.org/programs-and-services/opportunities/",
    "https://www.philaculture.org/what-we-do/job-bank",
    "https://culturaldata.org/what-we-do/for-arts-cultural-organizations/",
    "https://www.lancasterpublicart.com/opportunities",
    "https://www.artomat.org/opportunities/",
    "https://www.harrisburgpa.gov/arts-culture-and-tourism/",
    
    # Pennsylvania Museums and Institutions
    "https://philamuseum.org/employment",
    "https://cmoa.org/about/jobs/",
    "https://thewarhol.org/about/careers/",
    "https://www.pafa.org/museum/about/employment",
    "https://barnescollection.org/about/careers/",
    "https://www.phila.gov/departments/office-of-arts-culture-and-the-creative-economy/",
    "https://www.readingpublicmuseum.org/employment",
    "https://www.artmuseumgr.org/about/employment/",
    "https://brandywine.org/careers",
    "https://www.allendalearena.com/about/employment/",
    
    # Pennsylvania Universities and Art Schools
    "https://www.upenn.edu/life-at-penn/arts",
    "https://www.cmu.edu/cfa/about/employment/index.html",
    "https://www.temple.edu/academics/degree-programs/art",
    "https://www.uarts.edu/about/employment",
    "https://moore.edu/about/employment/",
    "https://www.poconoarts.org/opportunities",
    "https://www.muhlenberg.edu/main/aboutus/arts/",
    "https://drexel.edu/westphal/about/careers/faculty-search/",
    "https://jobs.psu.edu/",
    
    # Philadelphia/Pennsylvania Galleries and Art Spaces
    "https://www.InLiquid.org/opportunities",
    "https://www.havelerstudio.com/opportunities",
    "https://www.fleisher.org/opportunities/",
    "https://www.voxpopuligallery.org/opportunities/",
    "https://www.practicegallery.org/opportunities/",
    "https://www.gallerybomb.com/submissions",
    "https://springboardarts.org/submit-work/",
    "https://phillyartspace.com/artist-opportunities/",
    "https://boxheartgallery.com/submissions/",
    "https://www.framehousegalleries.com/submissions/",
    "https://www.3rdstreetgallery.com/submissions"
]

# Pennsylvania specific keywords
PENNSYLVANIA_KEYWORDS = [
    # Pennsylvania specific terms
    "philly artist", "philadelphia artist", "pittsburgh artist", "pennsylvania artist", 
    "philly arts", "philadelphia arts", "pittsburgh arts", "pennsylvania arts", 
    "philly art scene", "philadelphia art scene", "pittsburgh art scene",
    "pa grant", "pennsylvania grant", "philadelphia grant", "pittsburgh grant", 
    "pa residency", "pennsylvania residency", "philadelphia residency", "pittsburgh residency",
    "pennsylvania opportunity", "philadelphia opportunity", "pittsburgh opportunity", 
    "pa opportunity", "pennsylvania commission", "philadelphia commission", "pittsburgh commission",
    "pennsylvania fellowship", "philadelphia fellowship", "pittsburgh fellowship", 
    "pa fellowship", "pennsylvania public art", "philadelphia public art", "pittsburgh public art",
    "pa public art", "pennsylvania artists council", "philadelphia artists council", 
    "pittsburgh artists council", "pa artists council", "philadelphia mural arts",
    "philadelphia cultural affairs", "pittsburgh cultural commission", "philadelphia percent for art",
    "allegheny arts", "harrisburg arts", "lancaster arts", "allentown arts",
    "reading arts", "erie arts", "scranton arts", "bethlehem arts", "york arts"
]

# Pennsylvania locations
PENNSYLVANIA_LOCATIONS = [
    # Philadelphia and neighborhoods
    "philadelphia", "philly", "center city", "old city", "fishtown", "northern liberties",
    "kensington", "south philly", "west philly", "university city", "rittenhouse", 
    "fairmount", "chestnut hill", "mt. airy", "germantown", "manayunk", "east falls",
    "spring garden", "bella vista", "queen village", "society hill", "passyunk", 
    "point breeze", "graduate hospital", "brewerytown", "strawberry mansion", 
    "east passyunk", "south street", "chinatown", "east market", "logan square",
    
    # Pittsburgh and neighborhoods
    "pittsburgh", "shadyside", "squirrel hill", "oakland", "lawrenceville", "strip district",
    "bloomfield", "east liberty", "highland park", "south side", "north side", 
    "downtown pittsburgh", "hill district", "greenfield", "hazelwood", "brookline",
    "carrick", "allentown", "mount washington", "polish hill", "friendship", "garfield",
    
    # Pennsylvania regions and cities
    "harrisburg", "allentown", "erie", "reading", "scranton", "bethlehem", "lancaster",
    "levittown", "york", "state college", "wilkes-barre", "chester", "norristown",
    "williamsport", "chambersburg", "hazleton", "johnstown", "new castle", "monroeville",
    "lebanon", "easton", "pottstown", "west chester", "coatesville", "carlisle",
    "doylestown", "gettysburg", "jim thorpe", "new hope", "stroudsburg", "milford",
    
    # Pennsylvania regions
    "lehigh valley", "pocono mountains", "pennsylvania wilds", "delaware valley",
    "susquehanna valley", "endless mountains", "western pa", "eastern pa", "central pa",
    "southeast pa", "southwest pa", "northeast pa", "northwest pa", "dutch country",
    "allegheny mountains", "laurel highlands", "lake erie", "pennsylvania grand canyon",
    
    # Pennsylvania state
    "pennsylvania", "pa", "keystone state", "greater philadelphia", "greater pittsburgh",
    "philadelphia metro", "pittsburgh metro", "philadelphia area", "pittsburgh area",
    "montgomery county", "delaware county", "bucks county", "chester county", 
    "allegheny county", "berks county", "lancaster county", "york county", "dauphin county",
    "cumberland county", "beaver county", "northampton county", "lehigh county", 
    "westmoreland county", "luzerne county", "erie county", "monroe county"
]

# Create the Pennsylvania engine using the factory
engine = create_state_engine(
    state_name="Pennsylvania",
    state_sites=PENNSYLVANIA_SITES,
    state_keywords=PENNSYLVANIA_KEYWORDS,
    state_locations=PENNSYLVANIA_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Pennsylvania scraper
    run()