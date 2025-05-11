#!/usr/bin/env python3
"""
Stripe Price ID Fix Script

This script specifically fixes the STRIPE_PRICE_ID environment variable,
ensuring it has the correct format for Stripe price IDs (price_...).

Usage:
    python fix_stripe_price_id.py
"""

import os
import sys
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("stripe-price-fix")

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def fix_stripe_price_id():
    """Fix the STRIPE_PRICE_ID environment variable"""
    current_value = os.environ.get('STRIPE_PRICE_ID')
    if not current_value:
        logger.warning(f"{YELLOW}⚠️ STRIPE_PRICE_ID is not set{RESET}")
        return False, None
    
    # If it already matches the pattern, no fix needed
    if re.match(r'^price_\w+$', current_value):
        logger.info(f"{GREEN}✅ STRIPE_PRICE_ID is already correctly formatted{RESET}")
        return False, None
    
    # Common issues and their fixes
    if current_value.startswith(' ') or current_value.endswith(' '):
        # Remove leading/trailing whitespace
        fixed_value = current_value.strip()
        if re.match(r'^price_\w+$', fixed_value):
            logger.info(f"{GREEN}✅ Fixed whitespace in STRIPE_PRICE_ID{RESET}")
            return True, fixed_value
    
    # Try to extract a valid price ID from the current value
    price_id_match = re.search(r'(price_\w+)', current_value)
    if price_id_match:
        fixed_value = price_id_match.group(1)
        logger.info(f"{GREEN}✅ Extracted valid price_id from STRIPE_PRICE_ID{RESET}")
        return True, fixed_value
    
    # Extremely basic formatting (just add prefix if missing)
    if not current_value.startswith('price_'):
        fixed_value = 'price_' + current_value.strip()
        logger.info(f"{YELLOW}⚠️ Added 'price_' prefix to STRIPE_PRICE_ID - verify this is correct!{RESET}")
        return True, fixed_value
    
    logger.error(f"{RED}❌ Could not automatically fix STRIPE_PRICE_ID{RESET}")
    return False, None

def update_environment_variables(fixed_value):
    """Update the environment variable and .env file"""
    # Update the current environment
    os.environ['STRIPE_PRICE_ID'] = fixed_value
    logger.info(f"{GREEN}✅ Updated STRIPE_PRICE_ID in current environment{RESET}")
    
    # Update the .env file if it exists
    env_path = Path('.env')
    if not env_path.exists():
        # Create the .env file
        with open(env_path, 'w') as f:
            f.write(f"STRIPE_PRICE_ID={fixed_value}\n")
        logger.info(f"{GREEN}✅ Created .env file with fixed STRIPE_PRICE_ID{RESET}")
        return True
    
    # Read the current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Look for the variable in the file
    found = False
    updated_lines = []
    
    for line in lines:
        if line.strip().startswith('STRIPE_PRICE_ID='):
            updated_lines.append(f"STRIPE_PRICE_ID={fixed_value}\n")
            found = True
        else:
            updated_lines.append(line)
    
    # If not found, add it
    if not found:
        updated_lines.append(f"STRIPE_PRICE_ID={fixed_value}\n")
    
    # Write the updated content back to the file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    logger.info(f"{GREEN}✅ Updated STRIPE_PRICE_ID in .env file{RESET}")
    return True

def main():
    """Main function"""
    print(f"{BOLD}{BLUE}======================================{RESET}")
    print(f"{BOLD}{BLUE}Stripe Price ID Fixer{RESET}")
    print(f"{BOLD}{BLUE}======================================{RESET}")
    
    fixed, fixed_value = fix_stripe_price_id()
    
    if fixed and fixed_value:
        update_environment_variables(fixed_value)
        print(f"\n{GREEN}✅ Fixed STRIPE_PRICE_ID from invalid format to {fixed_value}{RESET}")
        print(f"\n{YELLOW}Note: If this is still incorrect, please manually set STRIPE_PRICE_ID to your actual Stripe price ID{RESET}")
    elif not fixed and fixed_value is None:
        print(f"\n{YELLOW}⚠️ Could not automatically fix STRIPE_PRICE_ID{RESET}")
        print(f"{YELLOW}⚠️ Please manually set STRIPE_PRICE_ID to your Stripe price ID (e.g., price_xyz123){RESET}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())