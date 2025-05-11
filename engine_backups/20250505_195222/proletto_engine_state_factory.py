#!/usr/bin/env python3
"""
Proletto Engine State Factory - Template for creating state-specific scrapers
This file contains common functions and patterns to be used by all state-specific scrapers
"""
import requests
from bs4 import BeautifulSoup
import json
import time
import random
import logging
from datetime import datetime

def create_state_engine(state_name, state_sites, state_keywords, state_locations, logger_name=None):
    """
    Factory function to create a state-specific scraper engine
    
    Args:
        state_name (str): Name of the state (e.g., "New York", "California")
        state_sites (list): List of state-specific websites to scrape
        state_keywords (list): List of state-specific keywords to search for
        state_locations (list): List of state-specific locations to identify
        logger_name (str, optional): Custom logger name. Defaults to f"proletto_engine_{state_name.lower().replace(' ', '_')}".
    
    Returns:
        dict: A dictionary containing all the necessary functions for a state engine
    """
    if logger_name is None:
        logger_name = f"proletto_engine_{state_name.lower().replace(' ', '_')}"
    
    logger = logging.getLogger(logger_name)
    
    HEADERS = {
        'User-Agent': 'ProlettoBot/1.0 (+https://www.myproletto.com)'
    }
    
    # Base keywords that are common across all states
    BASE_KEYWORDS = [
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
        "art scholarship", "cultural funding", "creative funding", "art support", "arts grant"
    ]
    
    # Combine base keywords with state-specific keywords
    KEYWORDS = BASE_KEYWORDS + state_keywords
    
    def is_relevant(text):
        """Check if text contains any relevant keywords."""
        return any(keyword in text.lower() for keyword in KEYWORDS)
    
    def scrape_site(url):
        """Scrape a single site for art opportunities."""
        try:
            logger.info(f"Scraping {state_name} site: {url}")
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
                    
                    # Common location identifiers plus state-specific locations
                    location_keywords = [
                        # Terms indicating location info
                        "location:", "based in", "located in", "position in", "job in", "working in", 
                        "onsite at", "position at", "based at", "office in", "workplace in", 
                        
                        # Work arrangements
                        "remote", "remote work", "work from home", "hybrid", "onsite", "in-person",
                    ] + state_locations
                    
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
                
                # Set the type to the state name for filtering purposes
                opp_type = state_name.lower().replace(" ", "_")
                
                gigs.append({
                    "title": title,
                    "url": job_url,
                    "location": location,
                    "description": description,
                    "source": source,
                    "type": opp_type,
                    "state": state_name,
                    "scraped_date": datetime.utcnow().isoformat()
                })
            
            logger.info(f"Found {len(gigs)} {state_name} opportunities on {url}")
            return gigs
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return []
    
    def run_scraper():
        """Run the state-specific scraper on all target sites."""
        logger.info(f"Starting Proletto Engine {state_name} - specialized scraper")
        
        all_gigs = []
        for site in state_sites:
            gigs = scrape_site(site)
            all_gigs.extend(gigs)
            # Add a polite delay between requests
            delay = random.uniform(1.5, 3.5)
            logger.info(f"Waiting {delay:.2f} seconds before next request")
            time.sleep(delay)
        
        logger.info(f"{state_name} scraping completed. Found {len(all_gigs)} total opportunities")
        return all_gigs
    
    def merge_with_existing(new_gigs, filename="opportunities.json"):
        """Merge new state-specific gigs with existing ones, avoiding duplicates."""
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
            
            logger.info(f"Added {added_count} new {state_name} opportunities. Total: {len(existing_gigs)}")
            return True
        except Exception as e:
            logger.error(f"Failed to merge {state_name} opportunities: {e}")
            return False
    
    def run():
        """Main function to run the state-specific scraper."""
        try:
            # Run the scraper
            gigs = run_scraper()
            
            # Merge with existing opportunities
            success = merge_with_existing(gigs)
            
            return success
        except Exception as e:
            logger.error(f"Error in Proletto Engine {state_name}: {e}")
            return False
    
    # Return the engine functions
    return {
        "run": run,
        "run_scraper": run_scraper,
        "merge_with_existing": merge_with_existing,
        "scrape_site": scrape_site,
        "is_relevant": is_relevant,
        "state_name": state_name,
        "logger": logger
    }

if __name__ == "__main__":
    # This file is not meant to be run directly
    print("This is a factory module for creating state-specific scrapers. Import it in your state engine files.")