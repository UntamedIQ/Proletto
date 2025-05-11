#!/usr/bin/env python3
"""
Update Proletto Engines

This script updates all Proletto engine files to use the improved scraper.
It backs up the original files, then modifies them to use the new scraping methods.
"""

import os
import shutil
import glob
import re
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('update_engines')

# Engine files to update
ENGINE_PATTERNS = [
    'proletto_engine_*.py',
    'proletto_engine_v*.py'
]

# Backup directory
BACKUP_DIR = 'engine_backups'

def create_backup_directory():
    """
    Create a backup directory for the original engine files
    """
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        logger.info(f"Created backup directory: {BACKUP_DIR}")
    
    # Create a timestamp directory inside the backup directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_subdir = os.path.join(BACKUP_DIR, timestamp)
    os.makedirs(backup_subdir)
    logger.info(f"Created backup subdirectory: {backup_subdir}")
    
    return backup_subdir

def backup_engine_files(backup_dir):
    """
    Backup all engine files
    """
    backed_up_files = []
    
    for pattern in ENGINE_PATTERNS:
        for file_path in glob.glob(pattern):
            # Create backup
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            backed_up_files.append(file_path)
            logger.info(f"Backed up {file_path} to {backup_path}")
    
    return backed_up_files

def update_import_section(content):
    """
    Update the import section of an engine file
    """
    # Check if improved_scraper is already imported
    if 'from improved_scraper import improved_scrape_site' in content:
        return content
    
    # Add the import after the last import line
    import_pattern = re.compile(r'(^import .*$|^from .* import .*$)', re.MULTILINE)
    matches = list(import_pattern.finditer(content))
    
    if matches:
        last_import = matches[-1]
        last_import_end = last_import.end()
        
        updated_content = (
            content[:last_import_end] + 
            '\n\n# Import improved scraper\nfrom improved_scraper import improved_scrape_site' +
            content[last_import_end:]
        )
        return updated_content
    
    # If no imports found, add it at the top
    return '# Import improved scraper\nfrom improved_scraper import improved_scrape_site\n\n' + content

def update_scrape_site_function(content):
    """
    Update the scrape_site function to use the improved version
    """
    # Check for different function signatures
    patterns = [
        r'def scrape_site\(url\):',
        r'def scrape_site\(url, keywords=None\):',
        r'def scrape_site\(url, keywords=KEYWORDS\):'
    ]
    
    for pattern in patterns:
        if re.search(pattern, content):
            # Modify the scrape_site function to use the improved version
            modified_content = re.sub(
                r'def scrape_site\((.*?)\):(.*?)return gigs',
                lambda m: f'def scrape_site({m.group(1)}):\n    """\n    Wrapper for the improved scraper\n    """\n    return improved_scrape_site(url, KEYWORDS)',
                content,
                flags=re.DOTALL
            )
            
            if modified_content != content:
                return modified_content
    
    # If no matches were found or replaced, return the original content
    logger.warning("Could not find or replace scrape_site function")
    return content

def update_engine_files(files_to_update):
    """
    Update engine files to use the improved scraper
    """
    updated_files = []
    
    for file_path in files_to_update:
        logger.info(f"Updating {file_path}...")
        
        try:
            # Read the file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Update the import section
            updated_content = update_import_section(content)
            
            # Update the scrape_site function
            updated_content = update_scrape_site_function(updated_content)
            
            # Write the updated content back to the file
            if updated_content != content:
                with open(file_path, 'w') as f:
                    f.write(updated_content)
                
                updated_files.append(file_path)
                logger.info(f"Updated {file_path}")
            else:
                logger.warning(f"No changes made to {file_path}")
                
        except Exception as e:
            logger.error(f"Error updating {file_path}: {e}")
    
    return updated_files

def main():
    """
    Main function
    """
    logger.info("Starting Proletto Engines update process")
    
    # Create backup directory
    backup_dir = create_backup_directory()
    
    # Backup engine files
    backed_up_files = backup_engine_files(backup_dir)
    logger.info(f"Backed up {len(backed_up_files)} engine files")
    
    # Update engine files
    updated_files = update_engine_files(backed_up_files)
    logger.info(f"Updated {len(updated_files)} engine files")
    
    # Generate improved_scraper.py
    import scrapers_improvement
    scrapers_improvement.apply_improvements()
    
    logger.info("Engine update process completed successfully")
    
    return True

if __name__ == "__main__":
    main()