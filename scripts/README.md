# Proletto Scripts

This directory contains utility scripts for managing, testing, and maintaining the Proletto platform.

## Available Scripts

### Email Digest Smoke Test

`test_digest_send.py` - A smoke test for verifying the weekly email digest system.

#### How to Run:

1. Set up the test email addresses as an environment variable:

```bash
export DIGEST_TEST_EMAILS=test1@example.com,test2@example.com
```

2. Run the script:

```bash
python scripts/test_digest_send.py
```

3. Verify in each test email inbox:
   - HTML formatting is correct
   - Images and logo display properly
   - Opportunity links work correctly
   - Unsubscribe link is functional
   - Personalization elements show the correct user data

**Note:** This script requires the SENDGRID_API_KEY environment variable to be properly set.

## Adding New Scripts

When adding new utility scripts:

1. Follow the same pattern of importing from the parent directory
2. Add comprehensive docstrings and command-line help
3. Document the script in this README.md file
4. Use logging instead of print statements for better output control