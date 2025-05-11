
def improved_scrape_site(url, keywords):
    """
    Improved scraping function with better error handling
    
    This function should be used in place of the original scrape_site function
    in all Proletto engines for improved reliability.
    """
    import os
    import json
    from scrapers_improvement import scrape_opportunities
    
    # Try to load config if exists
    config = {}
    try:
        if os.path.exists('scraper_config.json'):
            with open('scraper_config.json', 'r') as f:
                config = json.load(f)
    except Exception:
        pass
    
    # Check for site-specific overrides
    domain = url.split('//')[1].split('/')[0].replace('www.', '') if '//' in url else url
    use_headless = False
    use_cache = config.get('general', {}).get('cache_enabled', True)
    
    # Look for domain in site_overrides
    if 'site_overrides' in config:
        for override in config['site_overrides']:
            if override.get('domain') == domain:
                use_headless = override.get('use_headless', False)
                break
                
    # Look for domain in problem_domains
    if 'problem_domains' in config:
        for problem in config['problem_domains']:
            if problem.get('domain') == domain:
                use_headless = use_headless or problem.get('use_headless', False)
                break
    
    # Check if headless mode is globally enabled
    if not use_headless and 'headless' in config:
        use_headless = config['headless'].get('enabled', False)
        
    return scrape_opportunities(url, keywords, use_cache=use_cache, try_headless=use_headless)
