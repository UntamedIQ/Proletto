#!/usr/bin/env python3
"""
Check what fixes need to be applied to the index.html file
"""
import re

# Paths to fix
fixes = {
    '/google/google_login': '/auth/google/google_login',
    'opportunities.html': '/opportunities',
    'portfolio.html': '/portfolio',
    'profile.html': '/profile',
    'index.html': '/',
    '/membership.html': '/membership'
}

file_path = 'templates/index.html'

# Read the file
with open(file_path, 'r', encoding='utf-8') as f:
    text = f.read()

# Check for each fix
for src, dst in fixes.items():
    # Find all occurrences in href attributes
    href_pattern = f'href=["\']({re.escape(src)})["\']'
    matches = re.findall(href_pattern, text)
    
    if matches:
        print(f"Found {len(matches)} occurrences of '{src}' in {file_path}")
        for match in matches:
            print(f"  - {match}")
    
    # Replace with escaped pattern
    new_text = re.sub(f'href=["\']({re.escape(src)})["\']',
                      lambda m: f'href="{dst}"', text)
    
    if new_text != text:
        print(f"Would fix '{src}' → '{dst}' in {file_path}")
        text = new_text

print("\nModified content would be:")
print("-" * 40)
print(text[:500] + "..." if len(text) > 500 else text)
print("-" * 40)