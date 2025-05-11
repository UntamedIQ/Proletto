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

# Import improved scraper
from improved_scraper import improved_scrape_site

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
        """
        Wrapper for the improved scraper
        """
        try:
            return improved_scrape_site(url, KEYWORDS)
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