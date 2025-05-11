#!/usr/bin/env python3
"""
Proletto Engine Monitoring Dashboard

This script provides a simple dashboard for monitoring the health and performance
of the Proletto opportunity scraper engines. It shows success rates, latency metrics,
and circuit breaker status for each site being scraped.

Usage:
    python scrapers_dashboard.py
"""

import time
import os
import argparse
import sys
from datetime import datetime
from scrapers_improvement import get_site_health_metrics, generate_health_report

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_site_health(site_health):
    """Format site health data for display"""
    if not site_health:
        return "No site health data available yet. Run some scrapes first."
    
    lines = []
    lines.append("=" * 100)
    lines.append(f"{'DOMAIN':<30} {'STATUS':<10} {'SUCCESS':<10} {'FAILURE':<10} {'SUCCESS RATE':<15} {'AVG LATENCY':<15} {'LAST SUCCESS':<25}")
    lines.append("=" * 100)
    
    for domain, data in sorted(site_health.items()):
        status = "OPEN" if data.get('circuit_open', False) else "CLOSED"
        success_count = data.get('success_count', 0)
        failure_count = data.get('failure_count', 0)
        total = success_count + failure_count
        
        if total > 0:
            success_rate = f"{(success_count / total) * 100:.1f}%"
        else:
            success_rate = "N/A"
            
        avg_latency = data.get('avg_latency', 0)
        if avg_latency > 0:
            avg_latency_str = f"{avg_latency:.2f}s"
        else:
            avg_latency_str = "N/A"
            
        last_success = data.get('last_success')
        if last_success:
            if isinstance(last_success, datetime):
                last_success_str = last_success.strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_success_str = str(last_success)
        else:
            last_success_str = "Never"
            
        status_display = status
        if status == "OPEN":
            status_display = f"\033[91m{status}\033[0m"  # Red for open
        else:
            status_display = f"\033[92m{status}\033[0m"  # Green for closed
            
        # Color code success rate
        if total > 0:
            rate = (success_count / total) * 100
            if rate >= 90:
                success_rate = f"\033[92m{success_rate}\033[0m"  # Green for good
            elif rate >= 75:
                success_rate = f"\033[93m{success_rate}\033[0m"  # Yellow for caution
            else:
                success_rate = f"\033[91m{success_rate}\033[0m"  # Red for bad
                
        lines.append(f"{domain:<30} {status_display:<10} {success_count:<10} {failure_count:<10} {success_rate:<15} {avg_latency_str:<15} {last_success_str:<25}")
    
    return "\n".join(lines)

def interactive_dashboard():
    """Display an interactive dashboard"""
    try:
        while True:
            clear_screen()
            
            print("=" * 100)
            print("PROLETTO ENGINE MONITORING DASHBOARD")
            print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 100)
            
            # Get current metrics
            site_health = get_site_health_metrics()
            print(format_site_health(site_health))
            
            print("\n")
            print("Press Ctrl+C to exit, refreshing in 5 seconds...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nExiting dashboard...")

def export_report():
    """Export a CSV report of site health metrics"""
    report = generate_health_report()
    
    filename = f"scraper_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, 'w') as f:
        f.write(report)
        
    print(f"Report exported to {filename}")
    return filename

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Proletto Engine Monitoring Dashboard')
    parser.add_argument('--export', action='store_true', help='Export a CSV report instead of showing interactive dashboard')
    
    args = parser.parse_args()
    
    if args.export:
        export_report()
    else:
        interactive_dashboard()

if __name__ == "__main__":
    main()