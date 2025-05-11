#!/usr/bin/env python3
"""
Test script for the Application Auto-Fill System
This script tests the functionality of the application_autofill.py module
"""

import json
import requests
from application_autofill import ApplicationFormDetector, ApplicationAutoFiller

def test_detect_form():
    """Test the form detection functionality"""
    print("Testing form detection...")
    
    # Test URLs (replace with actual opportunity application URLs)
    test_urls = [
        "https://www.callforentry.org/festivals_unique_info.php?ID=7003",
        "https://www.nyfa.org/opportunities/",
        "https://www.submittable.com/submit/123456/test-opportunity"
    ]
    
    detector = ApplicationFormDetector()
    
    # Test each URL
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        try:
            result = detector.detect_form(url)
            print(f"Success: {result['success']}")
            print(f"Form fields detected: {len(result.get('form_fields', []))}")
            
            # Print some details of detected fields
            if result.get('form_fields'):
                print("\nSample detected fields:")
                for i, field in enumerate(result['form_fields'][:3]):  # Show first 3 fields
                    print(f"{i+1}. {field.get('label', 'No label')} - Type: {field.get('type', 'unknown')}")
        except Exception as e:
            print(f"Error: {e}")

def test_autofill_content(form_fields=None):
    """Test the auto-fill content generation"""
    print("\nTesting auto-fill content generation...")
    
    # Sample artist data
    artist_data = {
        "id": 123,
        "user_id": 123,
        "name": "Alex Rivera",
        "email": "alex@example.com",
        "phone": "555-123-4567",
        "address": "123 Art St",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "country": "USA",
        "website": "https://alexrivera.art",
        "art_type": "Mixed media installation and digital art",
        "biography": "Alex Rivera is a mixed media artist working at the intersection of technology and nature, with over 10 years of experience creating interactive installations that challenge viewers to reconsider their relationship with the environment. Based in New York City, Rivera's work has been exhibited nationally and internationally.",
        "education": "MFA in Fine Arts, School of Visual Arts, 2018\nBFA in Digital Arts, Pratt Institute, 2015",
        "exhibition_history": [
            {"year": 2023, "venue": "Gallery X", "title": "Digital Erosion"},
            {"year": 2022, "venue": "Museum Y", "title": "Memory Cache"},
            {"year": 2021, "venue": "International Art Biennial", "title": "Networked Ecologies"}
        ],
        "portfolio_highlights": [
            "Large-scale interactive installations",
            "Digital projections on physical objects",
            "Sound art exploring human-technology interaction"
        ]
    }
    
    # Sample opportunity data
    opportunity_data = {
        "title": "Digital Art Residency 2025",
        "description": "A three-month residency program for artists exploring digital media and technology. Artists will have access to cutting-edge equipment and technical support while developing new work that engages with themes of digital culture, environmental sustainability, and social justice.",
        "deadline": "2025-06-15",
        "location": "New York, NY",
        "url": "https://example.com/digital-art-residency-2025"
    }
    
    # Use detected form fields or create sample ones
    if not form_fields:
        form_fields = [
            {
                "name": "artist_name",
                "label": "Full Name",
                "type": "text",
                "required": True,
                "category": "PERSONAL_INFO"
            },
            {
                "name": "artist_email",
                "label": "Email Address",
                "type": "email",
                "required": True,
                "category": "PERSONAL_INFO"
            },
            {
                "name": "artist_statement",
                "label": "Artist Statement (max 500 words)",
                "type": "textarea",
                "required": True,
                "category": "ARTIST_STATEMENT"
            },
            {
                "name": "project_proposal",
                "label": "Project Proposal for Residency",
                "type": "textarea",
                "required": True,
                "category": "PROJECT_PROPOSAL"
            },
            {
                "name": "artist_bio",
                "label": "Short Biography (max 250 words)",
                "type": "textarea",
                "required": True,
                "category": "BIOGRAPHY"
            }
        ]
    
    # Create auto-filler
    auto_filler = ApplicationAutoFiller()
    
    # Generate content
    try:
        result = auto_filler.generate_application_content(artist_data, opportunity_data, form_fields)
        print(f"Success: {result['success']}")
        
        # Print generated content
        if result.get('filled_fields'):
            print("\nGenerated content:")
            for field_name, content in result['filled_fields'].items():
                # Print truncated content for readability
                if len(content) > 100:
                    content_preview = content[:97] + "..."
                else:
                    content_preview = content
                
                print(f"\n{field_name}:\n{content_preview}")
    except Exception as e:
        print(f"Error: {e}")

def test_api_detect_endpoint():
    """Test the API endpoint for form detection"""
    print("\nTesting API form detection endpoint...")
    
    # Test URL
    test_url = "https://www.callforentry.org/festivals_unique_info.php?ID=7003"
    
    # API endpoint (update with the correct URL)
    api_url = "http://localhost:5001/api/application/detect"
    
    # Request payload
    payload = {
        "url": test_url,
        "user_id": 1  # Change to an existing user ID if available
    }
    
    # Send request
    try:
        response = requests.post(api_url, json=payload)
        
        print(f"Status code: {response.status_code}")
        result = response.json()
        
        print(f"Success: {result.get('success', False)}")
        print(f"Form fields detected: {len(result.get('form_fields', []))}")
        
        # Save result for autofill test
        if result.get('success') and result.get('form_fields'):
            print("\nSaving detected form for autofill test")
            with open("detected_form.json", "w") as f:
                json.dump(result, f, indent=2)
                
            return result.get('form_fields')
    except Exception as e:
        print(f"Error: {e}")
        
    return None

def test_api_autofill_endpoint(form_fields=None):
    """Test the API endpoint for auto-fill"""
    print("\nTesting API auto-fill endpoint...")
    
    # API endpoint (update with the correct URL)
    api_url = "http://localhost:5001/api/application/autofill"
    
    # Load form fields from file if not provided
    if not form_fields:
        try:
            with open("detected_form.json", "r") as f:
                result = json.load(f)
                form_fields = result.get('form_fields', [])
        except (FileNotFoundError, json.JSONDecodeError):
            print("No detected form found, using sample fields")
            form_fields = []
    
    # Sample artist data
    artist_data = {
        "id": 123,
        "user_id": 1,  # Change to an existing user ID if available
        "name": "Alex Rivera",
        "email": "alex@example.com",
        "phone": "555-123-4567",
        "address": "123 Art St",
        "city": "New York",
        "state": "NY",
        "zip_code": "10001",
        "country": "USA",
        "website": "https://alexrivera.art",
        "art_type": "Mixed media installation and digital art",
        "biography": "Alex Rivera is a mixed media artist working at the intersection of technology and nature.",
        "education": "MFA in Fine Arts, School of Visual Arts, 2018",
        "exhibition_history": [
            {"year": 2023, "venue": "Gallery X", "title": "Digital Erosion"},
            {"year": 2022, "venue": "Museum Y", "title": "Memory Cache"}
        ],
        "portfolio_highlights": [
            "Large-scale interactive installations",
            "Digital projections on physical objects",
            "Sound art exploring human-technology interaction"
        ]
    }
    
    # Sample opportunity data
    opportunity_data = {
        "title": "Digital Art Residency 2025",
        "description": "A three-month residency program for artists exploring digital media and technology.",
        "deadline": "2025-06-15",
        "location": "New York, NY",
        "url": "https://example.com/digital-art-residency-2025"
    }
    
    # Request payload
    payload = {
        "artist_data": artist_data,
        "opportunity_data": opportunity_data,
        "form_fields": form_fields
    }
    
    # Send request
    try:
        response = requests.post(api_url, json=payload)
        
        print(f"Status code: {response.status_code}")
        result = response.json()
        
        print(f"Success: {result.get('success', False)}")
        
        # Print filled fields
        if result.get('success') and result.get('filled_fields'):
            print(f"Fields filled: {len(result.get('filled_fields', {}))}")
            print("\nSample filled fields:")
            
            for field_name, content in list(result['filled_fields'].items())[:2]:  # Show first 2 fields
                # Print truncated content for readability
                if len(content) > 100:
                    content_preview = content[:97] + "..."
                else:
                    content_preview = content
                
                print(f"\n{field_name}:\n{content_preview}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Application Auto-Fill System Test\n" + "-" * 35)
    
    # Test form detection (local)
    test_detect_form()
    
    # Test auto-fill content generation (local)
    test_autofill_content()
    
    # Test API endpoints
    form_fields = test_api_detect_endpoint()
    test_api_autofill_endpoint(form_fields)