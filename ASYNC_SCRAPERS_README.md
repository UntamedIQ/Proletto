# Proletto Asynchronous Scraper System

This document provides an overview of the asynchronous scraper system used in Proletto to collect art opportunities efficiently.

## Overview

The asynchronous scraper system replaces the older synchronous scraper architecture with a more efficient implementation based on Python's `asyncio` and `aiohttp` libraries. This new system provides significant performance improvements and enhanced reliability.

Key benefits:

- **5-10x faster execution** through concurrent HTTP requests
- **More efficient resource usage** by avoiding thread blocking
- **Enhanced error handling** with exponential backoff and jitter
- **Better scalability** for adding new opportunity sources
- **Simplified maintenance** through a unified base scraper class

## Architecture

The system consists of the following main components:

### 1. AsyncBaseScraper Class

All specialized scrapers inherit from this class, which provides:

- Connection pooling and session management
- Rate limiting and throttling
- Retry logic with exponential backoff
- Error handling and recovery
- Standardized logging

### 2. Specialized Scrapers

Concrete implementations for different opportunity sources:

- **InstagramAdsAsyncScraper**: Scrapes art opportunities from Instagram hashtags
- **ArtOpportunitiesAsyncScraper**: Base class for state-specific art opportunity scrapers
  - California, New York, Texas, Florida specialized scrapers
  - General art opportunities scraper for non-state-specific sources

### 3. APScheduler Integration

The `ap_scheduler_async.py` module handles:

- Scheduling scraper jobs at appropriate intervals
- Tracking job execution statistics
- Maintaining state between application restarts
- Implementing circuit breaker patterns for reliability

### 4. Bot Scheduler Integration

The `bot_scheduler.py` has been updated to:

- Use the asynchronous scheduler for improved performance
- Support nested event loops via nest_asyncio
- Provide backward compatibility with existing systems

## Benchmarks

Benchmarks show substantial performance improvements compared to the synchronous implementation:

| Scraper             | Sync Execution | Async Execution | Improvement |
|---------------------|----------------|-----------------|-------------|
| Instagram Ads       | 45-60 seconds  | 5-8 seconds     | ~8x faster  |
| California          | 90-120 seconds | 10-15 seconds   | ~9x faster  |
| New York            | 80-110 seconds | 9-13 seconds    | ~8x faster  |
| All States          | 8-10 minutes   | 50-70 seconds   | ~7x faster  |
| Social Media        | 3-4 minutes    | 25-35 seconds   | ~7x faster  |

## Usage

### Running a Scraper Directly

```python
import asyncio
from scrapers.instagram_ads_async import InstagramAdsAsyncScraper

# Create an instance of the scraper
scraper = InstagramAdsAsyncScraper()

# Run the scraper
asyncio.run(scraper.run_scraper())
```

### Configuring the Scheduler

```python
import ap_scheduler_async as scheduler

# Initialize the scheduler
scheduler_instance = scheduler.init_scheduler()

# The scheduler will automatically start the scrapers based on configured intervals
```

## Monitoring

The system logs detailed metrics for each scraper run, including:

- Execution time
- Opportunities found
- Success/failure rates
- Error details and recovery attempts

## Development

### Adding a New Scraper

1. Create a new class that inherits from `AsyncBaseScraper`
2. Implement the required methods:
   - `__init__`: Configure scraper-specific settings
   - `extract_opportunities`: Parse the HTML for opportunity data
   - `process_opportunity`: Process and store the opportunity

Example:

```python
from scrapers.async_base_scraper import AsyncBaseScraper

class MyNewAsyncScraper(AsyncBaseScraper):
    def __init__(self):
        super().__init__(
            engine_name="my_new_scraper",
            urls=["https://example.com/opportunities"],
            concurrent_requests=5,
            rate_limit=2.0
        )
    
    async def extract_opportunities(self, soup, source_url):
        # Extract and return opportunity data from the soup
        opportunities = []
        # ... parsing logic ...
        return opportunities
    
    async def process_opportunity(self, opportunity_data):
        # Process and save the opportunity
        # ... processing logic ...
        return True
```

3. Add the scraper to the scheduler in `ap_scheduler_async.py`

## Troubleshooting

### Common Issues

- **Connection Errors**: Check network connectivity and rate limits
- **Parse Errors**: The site structure may have changed, update the parsing logic
- **Event Loop Errors**: Make sure to use `nest_asyncio.apply()` when running in environments with existing event loops

### Debugging

Enable debug logging to get detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration

Use the `update_to_async_scrapers.py` script to:

- Check for required dependencies
- Test async scraper implementations
- Generate performance reports
- Migrate to the async system

Example:
```bash
python update_to_async_scrapers.py --test-all --migrate
```

## Credits

This system was built by the Proletto development team, leveraging modern Python asynchronous programming patterns to create a high-performance art opportunity discovery engine.