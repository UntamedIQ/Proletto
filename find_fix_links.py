#!/usr/bin/env python3
import csv, os, re, subprocess, glob
from urllib.parse import urlparse
from datetime import datetime

# Base URL of the Proletto site
BASE_URL = "https://myproletto.replit.app"

# 1) Find latest check results and capture broken internal URLs
os.makedirs('audits', exist_ok=True)

# Run the site checker and save to file
print(f"Running site check on {BASE_URL}...")
subprocess.run(
    'python proletto_site_checker.py',
    shell=True, check=True
)

# Find the most recent check file
check_files = glob.glob('proletto_check_*.csv')
if not check_files:
    print("No check files found. Try running proletto_site_checker.py manually.")
    exit(1)
    
latest_check = max(check_files)
print(f"Using results from {latest_check}")

# Parse the results and find broken links
broken = []
with open(latest_check, 'r', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Look for broken links with 404 errors that are html pages or have typos
        if row['Status'] == 'BROKEN' and row['Type'] == 'Link':
            broken.append(row['URL'])
            print(f"Found broken link: {row['URL']} (Status Code: {row['Status Code']})")
# Normalize unique set
broken = sorted(set(broken))
print(f"Found {len(broken)} broken links to fix:")

# 2) Map broken URLs to fixes (strip ".html" or trailing slash)
fixes = {}
for url in broken:
    path = urlparse(url).path
    print(f"Processing path: {path}")
    
    if path.endswith('.html'):
        fixed_path = path[:-5] or '/'
        fixes[path] = fixed_path
        print(f"  HTML fix: {path} → {fixed_path}")
    elif path.endswith('/'):
        fixed_path = path.rstrip('/') or '/'
        fixes[path] = fixed_path
        print(f"  Trailing slash fix: {path} → {fixed_path}")
    elif '/google/google_login' in path:
        # Special case for Google login redirect
        fixed_path = path.replace('/google/google_login', '/auth/google/google_login')
        fixes[path] = fixed_path
        print(f"  Google login fix: {path} → {fixed_path}")
    else:
        print(f"  No fix pattern matched for: {path}")
        
print(f"Generated {len(fixes)} fix mappings")
        
# If no broken internal links, exit
if not fixes:
    print("✨ No internal fixes needed.")
    exit(0)

# 3) Apply fixes across all relevant files
patterns = [(re.escape(src), dst) for src, dst in fixes.items()]
files_changed = []

# Directories to check - include templates, static, and any other potential directories
check_dirs = ['templates', 'static', '.']

for check_dir in check_dirs:
    if not os.path.exists(check_dir):
        continue
        
    for root, _, files in os.walk(check_dir):
        for fn in files:
            # Match HTML, template, React/JSX, JavaScript, and CSS files
            if fn.endswith(('.html', '.jinja2', '.jsx', '.js', '.css', '.json', '.vue', '.svelte')):
                path = os.path.join(root, fn)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    new_text = text
                    
                    # Fix href attributes (HTML/template links)
                    for src_pat, dst in patterns:
                        new_text = re.sub(r'href=["\']'+src_pat+'["\']',
                                        f'href="{dst}"', new_text)
                        
                        # Also fix JavaScript url assignments
                        new_text = re.sub(r'url:\s*["\']'+src_pat+'["\']',
                                        f'url: "{dst}"', new_text)
                        
                        # Also fix path/route assignments in JS
                        new_text = re.sub(r'(path|route):\s*["\']'+src_pat+'["\']',
                                        f'\\1: "{dst}"', new_text)
                    
                    if new_text != text:
                        print(f"Fixing links in {path}")
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(new_text)
                        files_changed.append(path)
                except (UnicodeDecodeError, IOError) as e:
                    print(f"Error processing {path}: {e}")

# 4) Commit & open PR
if files_changed:
    branch = f"fix/broken-links-{os.getpid()}"
    subprocess.run(f"git checkout -b {branch}", shell=True, check=True)
    subprocess.run("git add " + " ".join(files_changed), shell=True, check=True)
    subprocess.run(f'git commit -m "Auto-fix internal broken links"', shell=True, check=True)
    subprocess.run(f"git push --set-upstream origin {branch}", shell=True, check=True)
    # Create a draft PR (you can remove --draft if you want it published)
    subprocess.run(
        f'gh pr create --fill --title "chore: auto-fix internal broken links" --body "This PR fixes legacy `.html` links and trailing-slash typos." --draft',
        shell=True, check=True
    )
    print(f"🛠️ Fixed {len(files_changed)} files, PR created on branch {branch}.")
else:
    print("✨ No files needed updating.")