#!/usr/bin/env python3
"""
Proletto Engine Washington - Specialized web scraper for Washington art opportunities
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

# Washington specific sites to scrape
WASHINGTON_SITES = [
    # Washington Arts Organizations
    "https://www.arts.wa.gov/opportunities/",
    "https://www.seattleartistleague.com/opportunities/",
    "https://artisttrust.org/connect/opportunities/",
    "https://www.seattle.gov/arts/opportunities",
    "https://www.4culture.org/opportunities/",
    "https://www.artistsnetwork.org/art-opportunities/",
    "https://www.artsws.org/opportunities/",
    "https://www.tacomaartslive.org/opportunities/",
    "https://www.artscommission.org/opportunities",
    "https://www.artsbuildcommunities.com/opportunities/",
    "https://humanities.wa.gov/grants/",
    "https://www.artsfund.org/grants/",
    
    # Washington Museums and Institutions
    "https://www.seattleartmuseum.org/about-sam/careers",
    "https://www.tacomaartmuseum.org/about/careers/",
    "https://www.bellevuearts.org/about/careers",
    "https://www.henryart.org/about/opportunities",
    "https://www.themomentgallery.com/opportunities/",
    "https://fryemuseum.org/about/employment/",
    "https://www.burkemuseum.org/about/careers",
    "https://www.wingluke.org/about/careers/",
    "https://www.museumofglass.org/careers",
    "https://www.historymuseum.org/about/employment/",
    
    # Washington Universities and Art Schools
    "https://www.washington.edu/about/working-at-uw/",
    "https://www.cornish.edu/about/employment/",
    "https://www.digipen.edu/careers/",
    "https://www.evergreen.edu/humanresources/job-opportunities",
    "https://www.spu.edu/employment/",
    "https://www.seattleu.edu/careers/",
    "https://www.pnca.edu/about/employment",
    "https://www.wsu.edu/jobs/",
    "https://www.wwu.edu/hr/employment/",
    
    # Seattle/Washington Galleries and Art Spaces
    "https://www.gregkucera.com/about.htm",
    "https://fostergallery.com/opportunities/",
    "https://www.davidsongalleries.com/artists/submissions/",
    "https://roqlarue.com/submissions",
    "https://gageacademy.org/events-exhibitions/",
    "https://www.traver.gallery/contact",
    "https://www.koenigandclinton.com/contact/",
    "https://www.woodsidebrasethgallery.com/contact",
    "https://www.shirleymariesgallery.com/submissions/",
    "https://www.vestergallery.com/submissions/"
]

# Washington specific keywords
WASHINGTON_KEYWORDS = [
    # Washington specific terms
    "seattle artist", "washington artist", "seattle arts", "washington arts", "seattle art scene",
    "wa grant", "washington grant", "seattle grant", "wa residency", "washington residency", 
    "seattle residency", "washington opportunity", "seattle opportunity", "wa opportunity",
    "washington commission", "seattle commission", "washington fellowship", "seattle fellowship", 
    "wa fellowship", "washington public art", "seattle public art", "wa public art",
    "washington artists council", "seattle artists council", "wa artists council",
    "seattle cultural affairs", "washington cultural commission", "seattle percent for art",
    "tacoma arts", "bellevue arts", "spokane arts", "olympia arts", "bellingham arts",
    "pacific northwest arts", "puget sound arts", "cascadia arts"
]

# Washington locations
WASHINGTON_LOCATIONS = [
    # Seattle and neighborhoods
    "seattle", "capitol hill", "ballard", "fremont", "wallingford", "queen anne", "magnolia",
    "greenwood", "phinney ridge", "greenlake", "university district", "ravenna", "northgate",
    "west seattle", "georgetown", "columbia city", "beacon hill", "mount baker", "rainier valley",
    "central district", "madison park", "montlake", "eastlake", "south lake union", "belltown",
    "downtown seattle", "pioneer square", "international district", 
    
    # Washington regions and cities
    "tacoma", "bellevue", "spokane", "olympia", "bellingham", "redmond", "kirkland", "everett",
    "renton", "bothell", "kent", "auburn", "federal way", "lynnwood", "mercer island", "bremerton",
    "port townsend", "walla walla", "yakima", "pullman", "vancouver", "wenatchee", "ellensburg",
    "anacortes", "orcas island", "san juan islands", "whidbey island", "bainbridge island",
    "vashon island", "snoqualmie", "issaquah", "leavenworth", "palouse", "tri-cities",
    "kitsap peninsula", "peninsula", "olympic peninsula", "skagit valley",
    
    # Washington state
    "washington", "wa", "washington state", "evergreen state", "pacific northwest", "pnw",
    "puget sound", "cascadia", "eastern washington", "western washington", "southwest washington",
    "northwest washington", "king county", "pierce county", "snohomish county", "thurston county",
    "whatcom county", "clark county", "kitsap county", "spokane county", "yakima county",
    "skagit county", "greater seattle", "metro seattle"
]

# Create the Washington engine using the factory
engine = create_state_engine(
    state_name="Washington",
    state_sites=WASHINGTON_SITES,
    state_keywords=WASHINGTON_KEYWORDS,
    state_locations=WASHINGTON_LOCATIONS
)

# Export the run function
run = engine["run"]

if __name__ == "__main__":
    # When run directly, execute the Washington scraper
    run()