#!/usr/bin/env python3
"""
Scraper Monitoring Script

This script monitors the health of the Proletto Engine scrapers by:
1. Checking the scraper logs for errors
2. Testing the connection to each opportunity source
3. Verifying that the opportunity data is being properly stored
4. Alerting via Slack for any critical issues

Run this script periodically to ensure scrapers are functioning properly.
"""

import os
import re
import json
import logging
import time
import datetime
import requests
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='scraper_monitor.log'
)
logger = logging.getLogger('scraper_monitor')

# Add console output
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)

# Define scraper source URLs to monitor
SCRAPER_SOURCES = [
    'https://www.nyfa.org/jobs/',
    'https://www.artsthread.com/jobs/',
    'https://www.artsy.net/jobs',
    'https://www.collegeart.org/jobs/',
    'https://www.creativehotlist.com/',
    'https://www.aiga.org/job-board',
    'https://www.aam-us.org/job-board/',
    'https://www.museumjobs.com/',
    'https://www.artmuseum.jobs/',
    'https://www.artjobs.com/',
    'https://creative-capital.org/open-opportunities/',
    'https://jobs.arteducators.org/'
]

# Define paths to scraper log files
LOG_FILES = [
    'bot.log',
    'ap_scheduler.log',
    'api.log'
]

class ScraperMonitor:
    def __init__(self):
        self.opportunities_file = 'opportunities.json'
        self.slack_token = os.environ.get('SLACK_BOT_TOKEN')
        self.slack_channel = os.environ.get('SLACK_CHANNEL_ID')
        self.error_summary = defaultdict(list)
        self.connectivity_results = {}
        self.opportunity_counts = {}
        
    def check_log_files(self):
        """Parse log files for scraper errors"""
        logger.info("Checking log files for scraper errors...")
        
        # Error patterns to search for
        error_patterns = [
            r'ERROR.*scrape',
            r'ERROR.*opportunity',
            r'ERROR.*fetch',
            r'ERROR.*connection',
            r'WARNING.*timed out',
            r'WARNING.*rate limit',
            r'ERROR.*parse',
            r'Exception.*scraper'
        ]
        
        for log_file in LOG_FILES:
            if not os.path.exists(log_file):
                logger.warning(f"Log file not found: {log_file}")
                continue
                
            try:
                with open(log_file, 'r') as f:
                    log_content = f.read()
                    
                for pattern in error_patterns:
                    matches = re.findall(f'.*{pattern}.*', log_content, re.MULTILINE)
                    for match in matches:
                        # Extract timestamp if present
                        timestamp_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', match)
                        timestamp = timestamp_match.group(0) if timestamp_match else "Unknown time"
                        
                        # Extract domain from error if present
                        domain_match = re.search(r'https?://([^/\s]+)', match)
                        domain = domain_match.group(1) if domain_match else "Unknown source"
                        
                        # Add to error summary
                        self.error_summary[domain].append({
                            'log_file': log_file,
                            'timestamp': timestamp,
                            'error': match.strip()
                        })
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
        
        # Summarize errors
        for domain, errors in self.error_summary.items():
            logger.info(f"Found {len(errors)} errors for {domain}")
    
    def test_source_connectivity(self):
        """Test connectivity to each scraper source"""
        logger.info("Testing connectivity to scraper sources...")
        
        # User agent to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        for source in SCRAPER_SOURCES:
            try:
                logger.info(f"Testing connection to {source}")
                start_time = time.time()
                response = requests.get(source, headers=headers, timeout=30)
                response_time = time.time() - start_time
                
                status = {
                    'status_code': response.status_code,
                    'response_time': round(response_time, 2),
                    'accessible': response.status_code == 200,
                    'content_length': len(response.content)
                }
                
                self.connectivity_results[source] = status
                logger.info(f"Status for {source}: {status}")
                
                # Add a small delay to avoid being rate-limited
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error testing connectivity to {source}: {e}")
                self.connectivity_results[source] = {
                    'status_code': None,
                    'response_time': None,
                    'accessible': False,
                    'error': str(e)
                }
    
    def check_opportunity_data(self):
        """Check the opportunity data file for freshness and quality"""
        logger.info("Checking opportunity data...")
        
        if not os.path.exists(self.opportunities_file):
            logger.error(f"Opportunities file not found: {self.opportunities_file}")
            return
            
        try:
            # Check file modification time
            mod_time = os.path.getmtime(self.opportunities_file)
            mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            
            # Read the opportunity data
            with open(self.opportunities_file, 'r') as f:
                opportunities = json.load(f)
                
            # Count opportunities by source
            sources = Counter()
            total_count = len(opportunities)
            
            for opp in opportunities:
                source = opp.get('source', 'Unknown')
                sources[source] += 1
                
            # Count opportunities added in the last day
            now = time.time()
            one_day_ago = now - (24 * 60 * 60)
            recent_opps = sum(1 for opp in opportunities if 'date_added' in opp and opp['date_added'] > one_day_ago)
            
            self.opportunity_counts = {
                'total': total_count,
                'by_source': dict(sources),
                'file_modified': mod_time_str,
                'recent_24h': recent_opps
            }
            
            logger.info(f"Found {total_count} opportunities, {recent_opps} added in the last 24 hours")
            logger.info(f"File last modified: {mod_time_str}")
            for source, count in sources.most_common():
                logger.info(f"  {source}: {count} opportunities")
                
        except Exception as e:
            logger.error(f"Error checking opportunity data: {e}")
    
    def send_alerts(self):
        """Send alerts for critical issues via Slack"""
        # Skip if Slack is not configured
        if not self.slack_token or not self.slack_channel:
            logger.warning("Slack not configured, skipping alerts")
            return
            
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            client = WebClient(token=self.slack_token)
            
            # Check for critical issues
            critical_issues = []
            
            # Issue 1: Inaccessible sources
            inaccessible_sources = [
                source for source, status in self.connectivity_results.items()
                if not status.get('accessible', False)
            ]
            if inaccessible_sources:
                critical_issues.append(f"⚠️ {len(inaccessible_sources)} sources are inaccessible: {', '.join(inaccessible_sources)}")
            
            # Issue 2: Frequent errors
            frequent_errors = [
                domain for domain, errors in self.error_summary.items()
                if len(errors) >= 5  # Threshold for frequent errors
            ]
            if frequent_errors:
                critical_issues.append(f"⚠️ {len(frequent_errors)} sources have frequent errors: {', '.join(frequent_errors)}")
            
            # Issue 3: No recent opportunities
            if self.opportunity_counts.get('recent_24h', 0) < 5:  # Threshold for minimum recent opps
                critical_issues.append(f"⚠️ Only {self.opportunity_counts.get('recent_24h', 0)} new opportunities in the last 24 hours")
            
            # Send alert if there are critical issues
            if critical_issues:
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🚨 Proletto Scraper Alert 🚨"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Critical Issues Detected:*"
                        }
                    }
                ]
                
                for issue in critical_issues:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": issue
                        }
                    })
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Opportunity Counts:*\nTotal: {self.opportunity_counts.get('total', 0)}\nLast 24h: {self.opportunity_counts.get('recent_24h', 0)}"
                    }
                })
                
                # Send the message
                response = client.chat_postMessage(
                    channel=self.slack_channel,
                    blocks=blocks
                )
                logger.info(f"Alert sent to Slack, response: {response['ts']}")
            else:
                logger.info("No critical issues to alert about")
                
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
    
    def generate_report(self):
        """Generate a comprehensive report"""
        report = {
            'timestamp': datetime.datetime.now().isoformat(),
            'errors': dict(self.error_summary),
            'connectivity': self.connectivity_results,
            'opportunities': self.opportunity_counts
        }
        
        # Output as both JSON and a readable summary
        with open('scraper_health_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info("Report generated: scraper_health_report.json")
        
        # Print a readable summary
        print("\n===== SCRAPER HEALTH SUMMARY =====")
        print(f"Report Time: {report['timestamp']}")
        print(f"Opportunities: {self.opportunity_counts.get('total', 0)} total, {self.opportunity_counts.get('recent_24h', 0)} in last 24h")
        
        print("\nSource Connectivity:")
        accessible = sum(1 for status in self.connectivity_results.values() if status.get('accessible', False))
        print(f"  {accessible}/{len(SCRAPER_SOURCES)} sources accessible")
        
        print("\nErrors by Source:")
        for domain, errors in self.error_summary.items():
            print(f"  {domain}: {len(errors)} errors")
        
        return report
    
    def run(self):
        """Run the full monitoring process"""
        logger.info("Starting scraper monitoring")
        
        self.check_log_files()
        self.test_source_connectivity()
        self.check_opportunity_data()
        self.generate_report()
        self.send_alerts()
        
        logger.info("Scraper monitoring complete")

if __name__ == "__main__":
    monitor = ScraperMonitor()
    monitor.run()