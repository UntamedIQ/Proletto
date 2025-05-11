#!/usr/bin/env python3
"""
Compare broken links between main Proletto application and Dragon feature.
"""

import os
import json
import subprocess
import requests
from tabulate import tabulate
from datetime import datetime

# Set up console colors for better readability
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_service_status(port):
    """Check if a service is running on a specific port."""
    try:
        response = requests.get(f"http://localhost:{port}", timeout=2)
        return True, response.status_code
    except Exception:
        return False, None

def print_header(text):
    """Print formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")

def run_link_check(name, url, max_pages=10, check_external=False, output_file=None):
    """Run link check on a specific service."""
    if output_file is None:
        output_file = f"{name.lower().replace(' ', '_')}_links_report.json"
    
    print_header(f"Running link check on {name} ({url})")
    
    cmd = [
        "python", "check_broken_links.py",
        "--url", url,
        "--max-pages", str(max_pages),
        "--output", output_file
    ]
    
    if not check_external:
        cmd.append("--no-external")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"{Colors.GREEN}Link check completed for {name}{Colors.ENDC}")
        return output_file
    except subprocess.CalledProcessError:
        print(f"{Colors.RED}Failed to run link check for {name}{Colors.ENDC}")
        return None

def load_report(filename):
    """Load a link check report from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def compare_reports(main_report, dragon_report):
    """Compare link check reports and print differences."""
    if not main_report or not dragon_report:
        print(f"{Colors.RED}One or both reports are missing. Cannot compare.{Colors.ENDC}")
        return
    
    print_header("Comparison Results")
    
    # Overall statistics
    stats = [
        ["Base URL", main_report["base_url"], dragon_report["base_url"]],
        ["Pages Checked", main_report["pages_checked"], dragon_report["pages_checked"]],
        ["Internal Links", main_report["internal_links_count"], dragon_report["internal_links_count"]],
        ["External Links", main_report["external_links_count"], dragon_report["external_links_count"]],
        ["Broken Links", main_report["broken_links_count"], dragon_report["broken_links_count"]]
    ]
    
    print(f"{Colors.BOLD}Overall Statistics:{Colors.ENDC}")
    print(tabulate(stats, headers=["Metric", "Main App", "Dragon Feature"], tablefmt="grid"))
    print()
    
    # Broken links in main app but not in dragon
    main_broken_urls = {link["url"] for link in main_report["broken_links"]}
    dragon_broken_urls = {link["url"] for link in dragon_report["broken_links"]}
    
    only_in_main = main_broken_urls - dragon_broken_urls
    only_in_dragon = dragon_broken_urls - main_broken_urls
    in_both = main_broken_urls.intersection(dragon_broken_urls)
    
    if only_in_main:
        print(f"{Colors.WARNING}Broken links in Main App but not in Dragon Feature:{Colors.ENDC}")
        for url in only_in_main:
            parent = next(link["parent"] for link in main_report["broken_links"] if link["url"] == url)
            print(f"- {url} (found on {parent})")
        print()
    
    if only_in_dragon:
        print(f"{Colors.WARNING}Broken links in Dragon Feature but not in Main App:{Colors.ENDC}")
        for url in only_in_dragon:
            parent = next(link["parent"] for link in dragon_report["broken_links"] if link["url"] == url)
            print(f"- {url} (found on {parent})")
        print()
    
    if in_both:
        print(f"{Colors.RED}Broken links in BOTH applications:{Colors.ENDC}")
        for url in in_both:
            main_parent = next(link["parent"] for link in main_report["broken_links"] if link["url"] == url)
            dragon_parent = next(link["parent"] for link in dragon_report["broken_links"] if link["url"] == url)
            print(f"- {url}")
            print(f"  Found on Main App: {main_parent}")
            print(f"  Found on Dragon Feature: {dragon_parent}")
        print()

def main():
    """Main function to run link checks and compare results."""
    # Service ports
    main_port = 5000  # Main Proletto application
    dragon_port = 5002  # Dragon feature
    
    # Verify services are running
    main_running, main_status = get_service_status(main_port)
    dragon_running, dragon_status = get_service_status(dragon_port)
    
    print_header("Service Status Check")
    
    if main_running:
        print(f"{Colors.GREEN}Main Proletto application is running on port {main_port} (Status: {main_status}){Colors.ENDC}")
    else:
        print(f"{Colors.RED}Main Proletto application is NOT running on port {main_port}{Colors.ENDC}")
    
    if dragon_running:
        print(f"{Colors.GREEN}Dragon feature is running on port {dragon_port} (Status: {dragon_status}){Colors.ENDC}")
    else:
        print(f"{Colors.RED}Dragon feature is NOT running on port {dragon_port}{Colors.ENDC}")
    
    # Run link checks
    main_report_file = run_link_check(
        "Main Proletto Application", 
        f"http://localhost:{main_port}", 
        max_pages=15,
        output_file="main_app_links_report.json"
    )
    
    dragon_report_file = run_link_check(
        "Dragon Feature", 
        f"http://localhost:{dragon_port}", 
        max_pages=15,
        output_file="dragon_links_report.json"
    )
    
    # Load reports
    main_report = load_report(main_report_file) if main_report_file else None
    dragon_report = load_report(dragon_report_file) if dragon_report_file else None
    
    # Compare reports
    compare_reports(main_report, dragon_report)
    
    print_header("Analysis Complete")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Main App Report: {main_report_file}")
    print(f"Dragon Feature Report: {dragon_report_file}")

if __name__ == "__main__":
    main()