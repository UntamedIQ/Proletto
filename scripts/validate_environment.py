#!/usr/bin/env python3
import os
import re
import sys

# 1) List all required env vars
REQUIRED_ENVS = {
    'DATABASE_URL': r'.+',
    'REDIS_URL': r'^(redis|rediss)://',
    'STRIPE_SECRET_KEY': r'^sk_',
    'STRIPE_PUBLIC_KEY': r'^pk_',
    'STRIPE_WEBHOOK_SECRET': r'^whsec_',
    'SENDGRID_API_KEY': r'.+',
    'SENDGRID_FROM_EMAIL': r'.+@.+\..+',  # Basic email format
    'API_KEY': r'.+',
    'GOOGLE_OAUTH_CLIENT_ID': r'.+\.apps\.googleusercontent\.com$',
    'GOOGLE_OAUTH_CLIENT_SECRET': r'.+'
}

def validate_environment():
    """Validates that all required environment variables are present and properly formatted."""
    errors = []
    for name, pattern in REQUIRED_ENVS.items():
        val = os.getenv(name)
        if not val:
            errors.append(f"Missing required env var: {name}")
        elif not re.match(pattern, val):
            errors.append(f"Env var {name} doesn't match expected pattern '{pattern}'")
    
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return False
    
    print("✅ All environment variables validated successfully!")
    return True

if __name__ == "__main__":
    # Exit with non-zero code if validation fails
    if not validate_environment():
        sys.exit(1)