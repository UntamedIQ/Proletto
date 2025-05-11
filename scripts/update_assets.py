#!/usr/bin/env python3
"""
Script to update assets including PNG versions of SVG files
This script should be run after updating any SVG logo or icon files
"""
import os
import sys
import shutil
import subprocess
import time
from datetime import datetime

def run_command(command):
    """Run a command and return its output"""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Command failed with exit code {e.returncode}: {e.stderr}"
    except Exception as e:
        return False, f"Error running command: {e}"

def copy_svg_files():
    """Copy SVG files from static/img to assets if newer"""
    files_to_copy = {
        os.path.join('static', 'img', 'proletto-logo.svg'): os.path.join('assets', 'proletto-logo.svg'),
        os.path.join('static', 'img', 'proletto-icon.svg'): os.path.join('assets', 'proletto-icon.svg'),
    }
    
    copied = []
    for src, dest in files_to_copy.items():
        if not os.path.exists(src):
            print(f"Warning: Source file {src} does not exist, skipping")
            continue
            
        # Check if dest doesn't exist or src is newer
        if not os.path.exists(dest) or os.path.getmtime(src) > os.path.getmtime(dest):
            try:
                # Make sure the destination directory exists
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                copied.append((src, dest))
                print(f"Copied {src} to {dest}")
            except Exception as e:
                print(f"Error copying {src} to {dest}: {e}")
    
    return copied

def check_cairosvg_installed():
    """Check if CairoSVG is installed and ready to use"""
    try:
        import cairosvg
        return True, "CairoSVG is available"
    except ImportError:
        return False, "CairoSVG is not available. If needed, install with: pip install cairosvg"
    except Exception as e:
        return False, f"Error importing CairoSVG: {e}"

def generate_png_files():
    """Generate PNG versions of SVG files"""
    # First check if CairoSVG is installed
    cairo_available, cairo_message = check_cairosvg_installed()
    if not cairo_available:
        print(f"Warning: {cairo_message}")
        print("PNG generation will try alternative methods.")
    
    # Run the PNG generation script
    success, output = run_command(["python", "scripts/generate_png_from_svg.py"])
    if not success:
        print(f"Error generating PNG files: {output}")
        return False
    
    print(output)
    return True

def update_favicon():
    """Update favicon.ico from the icon SVG"""
    # Try to update favicon.ico if possible tools are available
    icon_svg_path = os.path.join('static', 'img', 'proletto-icon.svg')
    favicon_path = os.path.join('static', 'favicon.ico')
    
    # Check if we have ImageMagick available for favicon generation
    try:
        success, output = run_command(["convert", "--version"])
        if success:
            print("ImageMagick is available, attempting to create favicon...")
            # Create a 32x32 favicon from the SVG
            cmd = ["convert", icon_svg_path, "-resize", "32x32", favicon_path]
            success, output = run_command(cmd)
            
            if success:
                print(f"Created favicon at {favicon_path}")
                return True
            else:
                print(f"Failed to create favicon: {output}")
        else:
            print("ImageMagick not available, skipping favicon generation")
    except Exception as e:
        print(f"Error checking for ImageMagick: {e}")
    
    print("Note: favicon.ico should be updated manually if needed")
    return True

def main():
    print(f"Starting asset update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Copy SVG files from static/img to assets if needed
    copied = copy_svg_files()
    if copied:
        print(f"Copied {len(copied)} SVG files")
    else:
        print("No SVG files needed copying")
    
    # Generate PNG versions
    if generate_png_files():
        print("PNG generation successful")
    else:
        print("PNG generation failed")
        return False
    
    # Update favicon if needed
    update_favicon()
    
    print(f"Asset update completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return True

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)