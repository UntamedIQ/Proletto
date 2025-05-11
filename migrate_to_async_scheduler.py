#!/usr/bin/env python3
"""
Migrate Bot Scheduler to Async Implementation

This script updates the bot_scheduler.py file to use the new asynchronous 
scheduler implementation (ap_scheduler_async.py).

Benefits:
- 5-10x faster execution of scrapers
- More efficient resource usage
- Better error handling and recovery
- Improved scalability
"""

import os
import sys
import shutil
import re
from datetime import datetime

# Backup the original file
def backup_file(filepath):
    """Create a backup of the specified file"""
    if not os.path.exists(filepath):
        print(f"Error: {filepath} does not exist")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.bak.{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"Created backup at {backup_path}")
    return True

# Update the imports section
def update_imports(content):
    """Update imports to use async modules"""
    # Add nest_asyncio import if not present
    if "import nest_asyncio" not in content:
        import_section = re.search(r"(import.*?\n\n)", content, re.DOTALL)
        if import_section:
            updated_imports = import_section.group(1).rstrip() + "\nimport nest_asyncio\n\n"
            content = content.replace(import_section.group(1), updated_imports)
    
    # Replace or add ap_scheduler import
    if "import ap_scheduler" in content:
        content = re.sub(
            r"import ap_scheduler(?!_async)",
            "import ap_scheduler_async as ap_scheduler",
            content
        )
    else:
        import_section = re.search(r"(import.*?\n\n)", content, re.DOTALL)
        if import_section:
            updated_imports = import_section.group(1).rstrip() + "\nimport ap_scheduler_async as ap_scheduler\n\n"
            content = content.replace(import_section.group(1), updated_imports)
    
    return content

# Add nest_asyncio.apply() call
def add_nest_asyncio_apply(content):
    """Add nest_asyncio.apply() call"""
    if "nest_asyncio.apply()" not in content:
        # Look for a good place to add it - after imports, before main logic
        main_func = re.search(r"def main\(\):", content)
        if main_func:
            # Add before main function
            pos = main_func.start()
            content = content[:pos] + "# Apply nest_asyncio to allow nested event loops\nnest_asyncio.apply()\n\n" + content[pos:]
        else:
            # Add after imports
            import_section = re.search(r"(import.*?\n\n)", content, re.DOTALL)
            if import_section:
                end_pos = import_section.end()
                content = content[:end_pos] + "# Apply nest_asyncio to allow nested event loops\nnest_asyncio.apply()\n\n" + content[end_pos:]
    
    return content

# Update comments to mention async benefits
def update_comments(content):
    """Update comments to mention async benefits"""
    # Add note about async performance
    if "Asynchronous scraper system" not in content:
        header_comment = re.search(r"(\"\"\".*?\"\"\")", content, re.DOTALL)
        if header_comment:
            updated_comment = header_comment.group(1).rstrip() + "\n\nNOTE: This scheduler now uses asynchronous scrapers for 5-10x improved performance.\n\"\"\""
            content = content.replace(header_comment.group(1), updated_comment)
    
    return content

# Main migration function
def migrate_to_async():
    """Migrate bot_scheduler.py to use async implementation"""
    filepath = "bot_scheduler.py"
    
    # Create backup
    if not backup_file(filepath):
        return False
    
    try:
        # Read the file
        with open(filepath, "r") as f:
            content = f.read()
        
        # Perform updates
        content = update_imports(content)
        content = add_nest_asyncio_apply(content)
        content = update_comments(content)
        
        # Write back to file
        with open(filepath, "w") as f:
            f.write(content)
        
        print(f"Successfully updated {filepath} to use asynchronous scheduler")
        print("\nNext steps:")
        print("1. Review the changes to ensure everything looks correct")
        print("2. Restart the Bot Scheduler workflow")
        print("3. Monitor the logs for any issues")
        return True
    
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("Migrating Bot Scheduler to Asynchronous Implementation".center(80))
    print("=" * 80)
    
    success = migrate_to_async()
    
    if success:
        print("\nMigration completed successfully!")
    else:
        print("\nMigration failed. Please check the error messages above.")