# Proletto Brand Assets Management

This folder contains scripts for managing Proletto brand assets across the application.

## Assets Overview

The primary brand assets include:

- Logo (SVG and PNG versions)
- Icon (SVG and PNG versions)
- Favicon

## Scripts

### generate_png_from_svg.py

This script converts SVG files to PNG format for use in email templates and other contexts where SVG may not be supported.

**Features:**
- Multiple conversion methods with fallbacks:
  1. CairoSVG (primary method)
  2. Inkscape (fallback)
  3. ImageMagick (fallback)
  4. rsvg-convert (fallback)
  5. Placeholder image (last resort)
- Error handling and logging
- Configurable image dimensions

**Usage:**
```bash
python scripts/generate_png_from_svg.py
```

### update_assets.py

This script manages the entire asset workflow, including:

1. Copying SVG files from static/img to assets directory
2. Generating PNG versions using the generate_png_from_svg.py script
3. Creating favicon.ico from the icon SVG (if ImageMagick is available)

**Usage:**
```bash
python scripts/update_assets.py
```

## Asset Directory Structure

- `static/img/` - Main location for SVG assets used in the web application
- `assets/` - Storage for both SVG and PNG versions used in emails and other contexts
- `static/favicon.ico` - Favicon for the website

## Updating Brand Assets

When updating brand assets, follow these steps:

1. Place updated SVG files in the `static/img/` directory
2. Run `python scripts/update_assets.py` to propagate changes across the application
3. Verify that PNG versions and favicon have been generated correctly
4. Check the application to ensure the new assets display properly

## Dependencies

- **CairoSVG**: Primary method for SVG-to-PNG conversion (Python library)
- **ImageMagick**: Used for creating favicon.ico (System dependency)
- **Inkscape/rsvg-convert**: Alternative conversion methods (System dependencies)

To install the required Python dependencies:
```bash
pip install cairosvg Pillow
```

To install system dependencies (on Debian/Ubuntu):
```bash
apt-get install imagemagick librsvg2-bin
```