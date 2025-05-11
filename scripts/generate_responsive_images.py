#!/usr/bin/env python3
"""
Responsive Image Generator

This script generates responsive image variations for the Proletto website.
It processes images in the static/img directory, creating small, medium, and large
versions, plus 2x variants for high-DPI displays.

Usage:
  python generate_responsive_images.py [--directory=DIR] [--force]

Options:
  --directory=DIR    Specify the directory to process (default: static/img)
  --force            Regenerate existing images

Dependencies:
  - PIL (Pillow)
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image, UnidentifiedImageError

# Image size configurations (width in pixels)
IMAGE_SIZES = {
    "small": 320,      # Mobile
    "medium": 640,     # Tablet
    "large": 1024,     # Desktop
}

def generate_responsive_images(image_path, force=False):
    """Generate responsive image variations for a given image."""
    try:
        # Check if the image is valid
        original_image = Image.open(image_path)
        
        # Get image properties
        width, height = original_image.size
        aspect_ratio = height / width
        
        # Get the base path without extension
        base_path = os.path.splitext(image_path)[0]
        extension = os.path.splitext(image_path)[1].lower()
        
        # Only process certain image types
        if extension not in ['.jpg', '.jpeg', '.png']:
            print(f"Skipping {image_path} - not a supported image type")
            return
        
        # Process each size
        for size_name, size_width in IMAGE_SIZES.items():
            # Calculate height maintaining aspect ratio
            size_height = int(size_width * aspect_ratio)
            
            # Standard resolution (1x)
            output_path = f"{base_path}-{size_name}.jpg"
            if not os.path.exists(output_path) or force:
                resized_image = original_image.resize((size_width, size_height), Image.LANCZOS)
                resized_image = resized_image.convert('RGB')  # Convert to RGB for JPEG
                resized_image.save(output_path, "JPEG", quality=85, optimize=True)
                print(f"Generated {output_path}")
            
            # High resolution (2x)
            output_path_2x = f"{base_path}-{size_name}@2x.jpg"
            if not os.path.exists(output_path_2x) or force:
                # Double the resolution for 2x
                resized_image_2x = original_image.resize((size_width * 2, size_height * 2), Image.LANCZOS)
                resized_image_2x = resized_image_2x.convert('RGB')  # Convert to RGB for JPEG
                resized_image_2x.save(output_path_2x, "JPEG", quality=85, optimize=True)
                print(f"Generated {output_path_2x}")
        
        # Create a large version to serve as the default
        output_path = f"{base_path}-large.jpg"
        if not os.path.exists(output_path) or force:
            if width > IMAGE_SIZES["large"]:
                # If original is larger than our "large" size, resize it
                large_height = int(IMAGE_SIZES["large"] * aspect_ratio)
                resized_image = original_image.resize((IMAGE_SIZES["large"], large_height), Image.LANCZOS)
            else:
                # Otherwise use the original
                resized_image = original_image
            
            resized_image = resized_image.convert('RGB')  # Convert to RGB for JPEG
            resized_image.save(output_path, "JPEG", quality=90, optimize=True)
            print(f"Generated {output_path}")
        
        return True
    
    except UnidentifiedImageError:
        print(f"Error: {image_path} is not a valid image file")
        return False
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return False

def process_directory(directory, force=False):
    """Process all image files in a directory recursively."""
    directory_path = Path(directory)
    if not directory_path.exists():
        print(f"Error: Directory {directory} does not exist")
        return
    
    count = 0
    for path in directory_path.glob('**/*'):
        if path.is_file() and path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            # Skip already processed files (those with size suffixes)
            if any(suffix in path.name for suffix in ['-small', '-medium', '-large']):
                continue
            
            print(f"Processing {path}...")
            if generate_responsive_images(str(path), force):
                count += 1
    
    print(f"Processed {count} images")

def main():
    parser = argparse.ArgumentParser(description='Generate responsive images for the Proletto website')
    parser.add_argument('--directory', default='static/img', help='Directory to process')
    parser.add_argument('--force', action='store_true', help='Regenerate existing images')
    
    args = parser.parse_args()
    process_directory(args.directory, args.force)

if __name__ == '__main__':
    main()