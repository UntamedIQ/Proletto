#!/usr/bin/env python3
"""
Quick Fix Links

A lightweight version of find_fix_links.py that focuses only on fixing the 
specific broken links we've identified in the Proletto site.
"""
import os
import re
from urllib.parse import urlparse

# Specific fixes to apply
FIXES = {
    '/google/google_login': '/auth/google/google_login',
    'opportunities.html': '/opportunities',
    'portfolio.html': '/portfolio',
    'profile.html': '/profile',
    'index.html': '/',
    '/membership.html': '/membership'
}

# Directories to scan
DIRS_TO_SCAN = ['templates', 'static']

def fix_file(file_path):
    """Fix all broken links in a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # Fix href attributes in HTML/templates
        for src, dst in FIXES.items():
            # Handle variations of quotes and paths
            patterns = [
                (f'href="{src}"', f'href="{dst}"'),
                (f"href='{src}'", f"href='{dst}'"),
                # Also handle paths without leading slash
                (f'href="{src[1:]}"' if src.startswith('/') else None, 
                 f'href="{dst}"' if src.startswith('/') else None),
                (f"href='{src[1:]}'" if src.startswith('/') else None, 
                 f"href='{dst}'" if src.startswith('/') else None),
            ]
            
            for pattern in patterns:
                if pattern[0] is not None:
                    content = content.replace(pattern[0], pattern[1])
        
        # Only write back if changes were made
        if content != original_content:
            print(f"Fixing {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    
    except (UnicodeDecodeError, IOError) as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix links in all relevant files"""
    print("Starting quick link fix process...")
    files_changed = 0
    
    for dir_path in DIRS_TO_SCAN:
        if not os.path.exists(dir_path):
            continue
        
        for root, _, files in os.walk(dir_path):
            for filename in files:
                if filename.endswith(('.html', '.jinja2', '.js', '.css')):
                    file_path = os.path.join(root, filename)
                    if fix_file(file_path):
                        files_changed += 1
    
    print(f"Complete! Fixed links in {files_changed} files.")

if __name__ == "__main__":
    main()