# API Key System Documentation

## Overview

The Proletto API Key System provides a secure, database-backed authentication mechanism for the public API. The system features tiered rate limiting, usage tracking, and key management capabilities.

## Components

The API key system consists of the following components:

1. **Database Schema**: The `api_key` table in the PostgreSQL database stores API key information.

2. **Hashing Service**: The `api_key_db_service.py` module provides cryptographic functions for secure key storage and verification.

3. **Rate Limiting**: Plan-based rate limiting implemented through Flask-Limiter, providing different limits by plan tier.

4. **Key Management**: The `manage_api_keys.py` script provides CLI tools for creating, listing, revoking, and managing API keys.

5. **Testing Tools**: Scripts like `test_db_api_keys.py` and `test_rate_limits.py` for validating system functionality.

## Database Schema

The `api_key` table has the following structure:

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| key_hash | TEXT | PBKDF2 hash of the API key |
| key_prefix | TEXT | First 8 characters of the key (for lookup) |
| name | TEXT | Descriptive name for the key |
| user_id | INTEGER | Foreign key to user who owns the key |
| status | TEXT | Key status (active, revoked, expired) |
| plan | TEXT | Rate limit plan (free, pro, partner, admin) |
| created_at | TIMESTAMP | When the key was created |
| expires_at | TIMESTAMP | When the key expires |
| last_used_at | TIMESTAMP | When the key was last used |
| revoked_at | TIMESTAMP | When the key was revoked (if applicable) |
| request_count | INTEGER | Total number of requests made with this key |
| rate_limit_hits | INTEGER | Number of times rate limits were hit |

## Rate Limiting Tiers

| Plan | Rate Limit |
|------|------------|
| Free | 30 requests per minute |
| Pro | 60 requests per minute |
| Partner | 120 requests per minute |
| Admin | 240 requests per minute |

## Key Management

### Creating Keys

Using the management script:

```bash
python manage_api_keys.py create 1 pro "My API Key" 365
```

This creates a new Pro tier API key for user ID 1, named "My API Key" that's valid for 365 days.

In code:

```python
from manage_api_keys import create_api_key

# Create a key for user ID 1 with Pro plan
raw_key, key_id = create_api_key(1, plan='pro', name="My API Key", days_valid=365)
if raw_key:
    print(f"Created key: {raw_key}")
```

### Listing Keys

```bash
python manage_api_keys.py list 1
```

Lists all API keys for user ID 1.

### Revoking Keys

```bash
python manage_api_keys.py revoke 42
```

Revokes API key with ID 42.

### Changing Plan Tier

```bash
python manage_api_keys.py promote 42 partner
```

Upgrades API key with ID 42 to the Partner plan.

## API Key Usage

API keys can be provided in requests using one of two methods:

### Query Parameter

```
GET /api/v2/recommendations?key=YOUR_API_KEY
```

### Request Header

```
GET /api/v2/recommendations
X-API-KEY: YOUR_API_KEY
```

## Security Details

1. **Key Storage**: Only the hash of the API key is stored in the database, using PBKDF2 with a strong salt.

2. **Key Format**: API keys are 32-character random strings containing letters and numbers.

3. **Prefix Lookup**: For efficiency, the first 8 characters of each key are stored as a prefix for fast lookups.

4. **Expiration**: Keys automatically expire after a configurable period (default: 1 year).

5. **Revocation**: Administrators can revoke keys at any time, immediately invalidating them.

## Testing the System

### Database Verification

```bash
python test_db_api_keys.py
```

This creates test keys for all plans and verifies database operations.

### Rate Limiting Test

```bash
python test_rate_limits.py
```

This demonstrates the rate limiting behavior for different plan tiers.

## Future Enhancements

1. **Redis Integration**: Move rate limiting storage to Redis for better scaling.

2. **Automatic Rotation**: Implement automatic key rotation with grace periods.

3. **Web Admin Interface**: Create a web interface for key management.

4. **Usage Analytics**: Enhanced analytics and visualization of API key usage.

5. **Intelligent Throttling**: Adaptive rate limiting based on server load.

6. **Scope-Based Access**: Control feature access by key scope (read-only vs. full access).

## Troubleshooting

If API key verification fails, check:

1. Is the key being sent correctly (header or query parameter)?
2. Has the key expired or been revoked?
3. Does the key hash match what's in the database?
4. Is the `api_key` table (not `api_keys`) correctly set up?
5. Are there connection issues with the database?

The API key service provides detailed logging to help troubleshoot issues.