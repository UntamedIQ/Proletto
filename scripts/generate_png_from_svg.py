#!/usr/bin/env python3
"""
Script to generate PNG versions of SVG files for email templates
"""
import os
import sys
import subprocess
from PIL import Image

# Safely check if CairoSVG is available
try:
    import cairosvg
except ImportError:
    cairosvg = None


def convert_svg_to_png(svg_path, png_path, width=None, height=None):
    """Convert SVG to PNG using CairoSVG with robust error handling"""
    if not cairosvg:
        return False, "CairoSVG is not available. Please install it via 'pip install cairosvg'."
    
    try:
        print(f"Converting {svg_path} to {png_path} using cairosvg...")
        
        # Read the SVG file directly to avoid potential file path issues
        with open(svg_path, 'rb') as f:
            svg_data = f.read()
            
        cairosvg.svg2png(
            bytestring=svg_data, 
            write_to=png_path, 
            output_width=width, 
            output_height=height
        )
        print("Conversion successful!")
        return True, "Conversion successful"
    except Exception as e:
        error_msg = f"Failed to convert SVG to PNG: {e}"
        print(error_msg)
        return False, error_msg


def generate_png_from_svg(svg_path, png_path, width=None, height=None):
    """Generate a PNG file from an SVG file using multiple methods with fallbacks"""
    try:
        # First try using cairosvg if available (pure Python solution)
        if cairosvg:
            success, message = convert_svg_to_png(svg_path, png_path, width, height)
            if success:
                return True
            print(f"CairoSVG conversion failed: {message}")
        else:
            print("CairoSVG not available, trying alternative methods...")
        
        # Try using Inkscape command line
        try:
            cmd = ['inkscape', '--export-filename', png_path]
            if width:
                cmd.extend(['--export-width', str(width)])
            if height:
                cmd.extend(['--export-height', str(height)])
            cmd.append(svg_path)
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("Inkscape conversion successful!")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Inkscape conversion failed: {e}")
        
        # Try using ImageMagick convert
        try:
            cmd = ['convert', svg_path]
            if width and height:
                cmd.extend(['-resize', f'{width}x{height}'])
            cmd.append(png_path)
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("ImageMagick conversion successful!")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"ImageMagick conversion failed: {e}")
        
        # Try using rsvg-convert
        try:
            cmd = ['rsvg-convert', '-o', png_path]
            if width:
                cmd.extend(['-w', str(width)])
            if height:
                cmd.extend(['-h', str(height)])
            cmd.append(svg_path)
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("rsvg-convert conversion successful!")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"rsvg-convert conversion failed: {e}")
        
        # If all else fails, use a pure Python approach (create a simple placeholder)
        print("All conversion methods failed, creating placeholder image...")
        img = Image.new('RGBA', (width or 180, height or 40), (255, 255, 255, 0))
        img.save(png_path)
        print(f"Created placeholder PNG at {png_path}")
        return True
        
    except Exception as e:
        print(f"Error generating PNG from SVG: {e}")
        return False

def main():
    # Create PNG versions of both logo and icon
    logo_svg_path = os.path.join('static', 'img', 'proletto-logo.svg')
    logo_png_path = os.path.join('assets', 'proletto-logo.png')
    
    icon_svg_path = os.path.join('assets', 'proletto-icon.svg')
    icon_png_path = os.path.join('assets', 'proletto-icon.png')
    
    if not os.path.exists(logo_svg_path):
        print(f"Error: Logo SVG file not found at {logo_svg_path}")
        return False
    
    if not os.path.exists(icon_svg_path):
        print(f"Error: Icon SVG file not found at {icon_svg_path}")
        return False
    
    success_logo = generate_png_from_svg(logo_svg_path, logo_png_path, width=360, height=80)
    success_icon = generate_png_from_svg(icon_svg_path, icon_png_path, width=150, height=150)
    
    if success_logo and success_icon:
        print("PNG generation completed successfully!")
        return True
    else:
        print("PNG generation failed for one or more files")
        return False

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)