#!/usr/bin/env python3
"""
Stripe Environment Variable Fixer

This script validates Stripe-related environment variables and attempts to fix common issues:
1. Checks if STRIPE_PUBLIC_KEY starts with 'pk_' (no leading spaces)
2. Checks if STRIPE_SECRET_KEY starts with 'sk_'
3. Checks if STRIPE_WEBHOOK_SECRET starts with 'whsec_'
4. Checks if STRIPE_PRICE_ID is set correctly

Usage:
    python fix_stripe_env.py

"""
import os
import sys
import re
import logging
import json
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stripe_env_fix.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("stripe-env-fix")

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def check_environment_variables():
    """Check Stripe environment variables for common issues"""
    logger.info(f"{BLUE}Checking Stripe environment variables for issues...{RESET}")
    
    issues_found = False
    fixes_applied = False
    env_var_fixes = {}
    
    # Rules for environment variables (regex patterns they should match)
    env_rules = {
        'STRIPE_PUBLIC_KEY': r'^pk_(test|live)_\w+$',
        'STRIPE_SECRET_KEY': r'^sk_(test|live)_\w+$',
        'STRIPE_WEBHOOK_SECRET': r'^whsec_\w+$',
        'STRIPE_PRICE_ID': r'^price_\w+$'
    }
    
    # Check each variable against its rule
    for var_name, pattern in env_rules.items():
        value = os.environ.get(var_name)
        if not value:
            logger.warning(f"{YELLOW}⚠️ {var_name} is not set{RESET}")
            issues_found = True
            continue
        
        logger.info(f"Checking {var_name}: {'*' * (len(value) - 8)}")
        
        # Check if the value matches the expected pattern
        if not re.match(pattern, value):
            logger.error(f"{RED}❌ {var_name} does not match the expected pattern{RESET}")
            
            # Check for specific issues and fix them
            if var_name == 'STRIPE_PUBLIC_KEY' and value.strip().startswith('pk_'):
                # The value has leading/trailing whitespace but otherwise looks correct
                fixed_value = value.strip()
                logger.info(f"{GREEN}✅ Fixed whitespace issues in {var_name}{RESET}")
                env_var_fixes[var_name] = fixed_value
                fixes_applied = True
            elif var_name == 'STRIPE_SECRET_KEY' and value.strip().startswith('sk_'):
                # The value has leading/trailing whitespace but otherwise looks correct
                fixed_value = value.strip()
                logger.info(f"{GREEN}✅ Fixed whitespace issues in {var_name}{RESET}")
                env_var_fixes[var_name] = fixed_value
                fixes_applied = True
            elif var_name == 'STRIPE_WEBHOOK_SECRET' and value.strip().startswith('whsec_'):
                # The value has leading/trailing whitespace but otherwise looks correct
                fixed_value = value.strip()
                logger.info(f"{GREEN}✅ Fixed whitespace issues in {var_name}{RESET}")
                env_var_fixes[var_name] = fixed_value
                fixes_applied = True
            else:
                logger.error(f"{RED}⚠️ Could not automatically fix {var_name} - manual intervention required{RESET}")
                logger.error(f"{RED}⚠️ The value should match pattern: {pattern}{RESET}")
                issues_found = True
        else:
            logger.info(f"{GREEN}✅ {var_name} is correctly formatted{RESET}")
    
    return issues_found, fixes_applied, env_var_fixes

def update_env_file(env_var_fixes):
    """Update the .env file with fixes"""
    logger.info(f"{BLUE}Updating .env file with fixed variables...{RESET}")
    
    env_path = Path('.env')
    
    # If .env doesn't exist, create it
    if not env_path.exists():
        logger.info(f"{YELLOW}⚠️ .env file not found. Creating new file.{RESET}")
        with open(env_path, 'w') as f:
            for var_name, value in env_var_fixes.items():
                f.write(f"{var_name}={value}\n")
        logger.info(f"{GREEN}✅ Created new .env file with fixed variables{RESET}")
        return True
    
    # Read the current .env file
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    # Update existing variables or add new ones
    updated_lines = []
    vars_updated = set()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            updated_lines.append(line)
            continue
        
        # Check if this line is defining a variable we need to fix
        for var_name, value in env_var_fixes.items():
            if line.startswith(f"{var_name}=") or line.startswith(f"{var_name}="):
                updated_lines.append(f"{var_name}={value}")
                vars_updated.add(var_name)
                logger.info(f"{GREEN}✅ Updated {var_name} in .env file{RESET}")
                break
        else:
            # If we didn't break out of the loop, this line isn't being fixed
            updated_lines.append(line)
    
    # Add any variables that weren't already in the file
    for var_name, value in env_var_fixes.items():
        if var_name not in vars_updated:
            updated_lines.append(f"{var_name}={value}")
            logger.info(f"{GREEN}✅ Added {var_name} to .env file{RESET}")
    
    # Write the updated content back to the file
    with open(env_path, 'w') as f:
        f.write('\n'.join(updated_lines) + '\n')
    
    logger.info(f"{GREEN}✅ Successfully updated .env file{RESET}")
    return True

def run_stripe_diagnostic():
    """Run the Stripe diagnostic tool if it exists"""
    logger.info(f"{BLUE}Running Stripe diagnostic tool...{RESET}")
    
    diagnostic_path = Path('stripe_diagnostic.py')
    if not diagnostic_path.exists():
        logger.warning(f"{YELLOW}⚠️ stripe_diagnostic.py not found. Skipping diagnostics.{RESET}")
        return False
    
    try:
        # Add execution permission if needed
        if not os.access(diagnostic_path, os.X_OK):
            subprocess.run(['chmod', '+x', str(diagnostic_path)], check=True)
        
        # Run the diagnostic tool
        logger.info(f"{BLUE}Executing stripe_diagnostic.py...{RESET}")
        result = subprocess.run(['python3', str(diagnostic_path)], 
                                capture_output=True, text=True, check=False)
        
        # Log the output
        logger.info(f"{BLUE}Diagnostic output:{RESET}")
        for line in result.stdout.splitlines():
            logger.info(line)
        
        if result.stderr:
            logger.error(f"{RED}Diagnostic errors:{RESET}")
            for line in result.stderr.splitlines():
                logger.error(line)
        
        return result.returncode == 0
    except Exception as e:
        logger.error(f"{RED}Error running diagnostic tool: {e}{RESET}")
        return False

def main():
    """Main function"""
    print(f"{BOLD}{BLUE}======================================{RESET}")
    print(f"{BOLD}{BLUE}Stripe Environment Variable Fixer{RESET}")
    print(f"{BOLD}{BLUE}======================================{RESET}")
    
    issues_found, fixes_applied, env_var_fixes = check_environment_variables()
    
    if fixes_applied:
        # Update the environment for the current process
        for var_name, value in env_var_fixes.items():
            os.environ[var_name] = value
            logger.info(f"{GREEN}✅ Updated {var_name} in current environment{RESET}")
        
        # Update the .env file
        update_env_file(env_var_fixes)
        
        print(f"\n{GREEN}✅ Fixed Stripe environment variable issues{RESET}")
    elif not issues_found:
        print(f"\n{GREEN}✅ No Stripe environment variable issues found{RESET}")
    else:
        print(f"\n{RED}❌ Stripe environment variable issues found that couldn't be fixed automatically{RESET}")
        print(f"{YELLOW}⚠️ Please fix the issues manually by setting correct environment variables{RESET}")
    
    # Run the Stripe diagnostic tool
    print(f"\n{BLUE}Running Stripe diagnostic tool...{RESET}")
    diagnostic_success = run_stripe_diagnostic()
    
    if diagnostic_success:
        print(f"\n{GREEN}✅ Stripe diagnostic checks passed{RESET}")
    else:
        print(f"\n{RED}❌ Stripe diagnostic checks failed{RESET}")
        print(f"{YELLOW}⚠️ Please check the logs for more details and fix any remaining issues{RESET}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())