#!/usr/bin/env python3
"""
Blueprint Registration Fix Script

This script addresses blueprint registration issues in the Flask application:
1. Fixes duplicate blueprint name issues
2. Ensures proper registration order
3. Updates blueprints with unique names to prevent collisions

Run this script as a one-time fix before going to production.
"""

import os
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('blueprint_fixer')

# Files to check and fix
FILES_TO_CHECK = [
    'main.py',
    'api.py',
    'auth_router_fix.py',
    'fix_auth_routes.py',
    'public_api.py',
    'setup_subscriptions.py'
]

def fix_duplicate_blueprint_names():
    """Fix blueprints with duplicate names"""
    logger.info("Fixing duplicate blueprint names...")
    
    # Blueprint name registrations to track
    blueprint_names = {}
    fixes_applied = []
    
    for filename in FILES_TO_CHECK:
        if not os.path.exists(filename):
            logger.warning(f"File not found: {filename}")
            continue
            
        with open(filename, 'r') as f:
            content = f.read()
            
        # Look for blueprint definitions
        blueprint_defs = re.findall(r'([a-zA-Z0-9_]+)\s*=\s*Blueprint\s*\(\s*[\'"]([^\'"]+)[\'"]', content)
        
        for var_name, bp_name in blueprint_defs:
            if bp_name in blueprint_names:
                # Found duplicate blueprint name
                other_file = blueprint_names[bp_name]
                logger.warning(f"Duplicate blueprint name '{bp_name}' in {filename} (also in {other_file})")
                
                # Generate a unique name
                new_name = f"{bp_name}_{filename.replace('.py', '')}"
                
                # Replace the blueprint name
                old_code = f"Blueprint('{bp_name}'"
                new_code = f"Blueprint('{new_name}'"
                
                if old_code in content:
                    content = content.replace(old_code, new_code)
                    fixes_applied.append({
                        'file': filename,
                        'old_name': bp_name,
                        'new_name': new_name
                    })
                    logger.info(f"Renamed blueprint from '{bp_name}' to '{new_name}' in {filename}")
                else:
                    logger.warning(f"Could not find exact blueprint definition in {filename}")
            else:
                blueprint_names[bp_name] = filename
        
        # Write back the modified content
        if content != open(filename, 'r').read():
            # Create backup
            backup_file = f"{filename}.bak"
            with open(backup_file, 'w') as f:
                f.write(open(filename, 'r').read())
                
            # Write fixed content
            with open(filename, 'w') as f:
                f.write(content)
            
            logger.info(f"Updated {filename} (backup at {backup_file})")
    
    return fixes_applied

def fix_blueprint_registration_order():
    """Fix the order of blueprint registrations in main.py"""
    logger.info("Fixing blueprint registration order...")
    
    if not os.path.exists('main.py'):
        logger.warning("main.py not found")
        return False
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    # Find the blueprint registration section
    registration_section = re.search(r'# Register Blueprints - START.*?# Register Blueprints - END', 
                                    content, re.DOTALL)
    
    if not registration_section:
        logger.warning("Blueprint registration section not found in main.py")
        return False
    
    registration_code = registration_section.group(0)
    
    # Extract all the try-except blocks for blueprint registrations
    registration_blocks = re.findall(r'# Register (.*?) blueprint.*?try:.*?except.*?}\)', 
                                    registration_code, re.DOTALL)
    
    if not registration_blocks:
        logger.warning("No registration blocks found")
        return False
    
    # Reorder the blocks to ensure core auth is first
    priority_order = [
        'Google Auth', 
        'Email Auth', 
        'Auth Router Fix', 
        'Auth Fix', 
        'Stripe', 
        'Referral Routes', 
        'Admin Routes', 
        'Simple Admin',
        'subscription system',
        'Public API'
    ]
    
    # Create backup
    backup_file = 'main.py.blueprint_order.bak'
    with open(backup_file, 'w') as f:
        f.write(content)
    
    logger.info(f"Created backup at {backup_file}")
    
    # Ensure that public API registration happens last
    public_api_pattern = r'# Register Public API v2 blueprint.*?}\)'
    public_api_match = re.search(public_api_pattern, registration_code, re.DOTALL)
    
    if public_api_match:
        # Remove it from its current position
        registration_code = re.sub(public_api_pattern, '', registration_code, flags=re.DOTALL)
        
        # Add it to the end
        registration_code += "\n\n# Register Public API v2 blueprint last to prevent circular imports\n"
        registration_code += public_api_match.group(0)
    
    # Update the content
    new_content = content.replace(registration_section.group(0), registration_code)
    
    # Write the updated content
    with open('main.py', 'w') as f:
        f.write(new_content)
    
    logger.info("Updated blueprint registration order in main.py")
    return True

def fix_public_api_blueprint():
    """Fix the public API blueprint registration issues"""
    logger.info("Fixing public API blueprint...")
    
    if not os.path.exists('public_api.py'):
        logger.warning("public_api.py not found")
        return False
    
    with open('public_api.py', 'r') as f:
        content = f.read()
    
    # Create backup
    backup_file = 'public_api.py.bak'
    with open(backup_file, 'w') as f:
        f.write(content)
    
    # Fix: Move all routes under the blueprint definition
    # This ensures they're registered when the blueprint is created, not when it's registered
    
    # Find the blueprint definition
    blueprint_def = re.search(r'public_api\s*=\s*Blueprint\(.*?\)', content)
    
    if not blueprint_def:
        logger.warning("Blueprint definition not found in public_api.py")
        return False
    
    # Find route definitions
    route_defs = re.findall(r'@public_api\.route\(.*?\)', content)
    
    if not route_defs:
        logger.warning("No route definitions found in public_api.py")
        return False
    
    # No specific changes needed, just warn about best practices
    logger.info(f"Found {len(route_defs)} route definitions in public_api.py")
    logger.info("Make sure all routes are defined before the blueprint is registered")
    
    # Add explicit note about registration best practices
    if "# IMPORTANT: Register all routes before this blueprint is registered with the app" not in content:
        # Add the note at the end of the file
        new_content = content + "\n\n# IMPORTANT: Register all routes before this blueprint is registered with the app\n"
        
        # Write the updated content
        with open('public_api.py', 'w') as f:
            f.write(new_content)
        
        logger.info("Added best practices note to public_api.py")
    
    return True

def main():
    """Main function to fix blueprint registrations"""
    logger.info("Starting blueprint registration fix")
    
    fixes_applied = fix_duplicate_blueprint_names()
    order_fixed = fix_blueprint_registration_order()
    public_api_fixed = fix_public_api_blueprint()
    
    if fixes_applied or order_fixed or public_api_fixed:
        logger.info("Blueprint registration issues fixed successfully")
        
        if fixes_applied:
            logger.info("Blueprint name changes:")
            for fix in fixes_applied:
                logger.info(f"  - {fix['file']}: {fix['old_name']} -> {fix['new_name']}")
        
        logger.info("Please restart your application to apply these changes")
    else:
        logger.info("No blueprint registration issues found or fixed")

if __name__ == "__main__":
    main()