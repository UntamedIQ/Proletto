# API Key System Usage Guide

This guide explains how to use and test the database-backed API key system for Proletto.

## Overview

The Proletto API key system provides:
- Secure API key storage with PBKDF2 hashing
- Tiered rate limiting based on plan levels
- Usage tracking and metrics
- Key status management (active, expired, revoked)

## API Key Tiers

The system supports the following plan tiers, each with different rate limits:

- **Free**: 30 requests per minute
- **Pro**: 60 requests per minute
- **Partner**: 120 requests per minute
- **Admin**: 240 requests per minute

## Using API Keys

### In API Requests

API keys can be provided in requests using either:

1. A query parameter: `?key=YOUR_API_KEY`
2. A request header: `X-API-KEY: YOUR_API_KEY`

Example:
```bash
# Using query parameter
curl "https://api.myproletto.com/api/v2/health?key=YOUR_API_KEY" 

# Using header
curl -H "X-API-KEY: YOUR_API_KEY" "https://api.myproletto.com/api/v2/health"
```

### Response Headers

Rate limiting information is included in response headers:

- `X-RateLimit-Limit`: The maximum number of requests available
- `X-RateLimit-Remaining`: The number of requests remaining in the current window
- `X-RateLimit-Reset`: The time at which the rate limit window resets in UTC epoch seconds

## Testing the API Key System

The included `test_db_api_keys.py` script can be used to test the API key system:

```bash
python test_db_api_keys.py
```

This will:
1. Create test API keys for all plan tiers
2. Save them to `test_api_keys.txt` for reference
3. Verify the keys can be read from the database
4. Test that verification works
5. Test rate limit hit recording

## Generating and Managing API Keys

The database table `api_key` stores all API keys. Here's how to manage keys:

### Creating a New API Key

```python
from api_key_db_service import hash_key, engine
from sqlalchemy import insert, Table, MetaData
import random
import string
from datetime import datetime, timedelta

# Generate a random key
def generate_random_key(length=32):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Create a new key
def create_api_key(user_id, plan='free', days_valid=365):
    raw_key = generate_random_key()
    key_hash = hash_key(raw_key)
    key_prefix = raw_key[:8]
    
    metadata = MetaData()
    api_keys = Table('api_key', metadata, autoload_with=engine)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            stmt = insert(api_keys).values(
                key_hash=key_hash,
                key_prefix=key_prefix,
                name=f"{plan.capitalize()} API Key",
                plan=plan,
                user_id=user_id,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=days_valid),
                status='active',
                revoked_at=None,
                request_count=0,
                rate_limit_hits=0
            )
            result = conn.execute(stmt)
            trans.commit()
            return raw_key, result.inserted_primary_key[0]
        except Exception as e:
            trans.rollback()
            raise e
```

### Revoking an API Key

```python
from api_key_db_service import engine
from sqlalchemy import update, Table, MetaData
from datetime import datetime

def revoke_api_key(key_prefix):
    metadata = MetaData()
    api_keys = Table('api_key', metadata, autoload_with=engine)
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            stmt = update(api_keys).where(
                api_keys.c.key_prefix == key_prefix
            ).values(
                status='revoked',
                revoked_at=datetime.utcnow()
            )
            result = conn.execute(stmt)
            trans.commit()
            return result.rowcount > 0
        except Exception as e:
            trans.rollback()
            raise e
```

## Environmental Fallback

The system will automatically use the `API_KEY` environment variable as a master admin key if provided. This is useful for system operations and should be kept secure.

## Security Considerations

- API keys are stored using PBKDF2 hashing with salt
- Only the key hash and first 8 characters (prefix) are stored in the database 
- Keys automatically expire based on their `expires_at` timestamp
- Keys can be individually revoked
- Rate limiting protects against abuse
- Rate limit events are tracked and can trigger alerts

## Future Enhancements

Planned improvements to the API key system:

1. Automatic key rotation mechanism
2. Redis-based distributed rate limiting for better scaling
3. Admin interface for key management
4. Enhanced analytics dashboard
5. Auto-throttling for suspicious behavior