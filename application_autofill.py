"""
Proletto Application Auto-Fill System
This module provides AI-powered application form detection and auto-fill capabilities
for artists applying to opportunities.
"""

import os
import json
import logging
import requests
from datetime import datetime
from openai import OpenAI
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('application_autofill')

# Initialize OpenAI client with proper error handling
api_key = os.environ.get("OPENAI_API_KEY")
OPENAI_AVAILABLE = True
client = None  # Initialize to None

def check_openai_availability():
    """
    Check if OpenAI API is available and working.
    Updates the global OPENAI_AVAILABLE flag and client variable.
    
    Returns:
        bool: True if OpenAI API is available, False otherwise
    """
    global OPENAI_AVAILABLE, client
    
    try:
        if not api_key:
            OPENAI_AVAILABLE = False
            logger.warning("OpenAI API key not found in environment. AI features will be limited.")
            return False
            
        if client is None:
            client = OpenAI(api_key=api_key)
            
        # Test the client with a simple query to ensure it's working
        client.models.list()
        OPENAI_AVAILABLE = True
        return True
    except Exception as e:
        OPENAI_AVAILABLE = False
        logger.warning(f"Error connecting to OpenAI API: {e}. AI features will be limited.")
        return False

# Initial API check
try:
    check_openai_availability()
except Exception as e:
    OPENAI_AVAILABLE = False
    logger.warning(f"Error initializing OpenAI client: {e}. AI features will be limited.")
    client = None

class ApplicationFormDetector:
    """
    Detects and analyzes application forms from opportunity websites.
    Uses pattern recognition and AI to identify form fields and required information.
    """
    
    def __init__(self):
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    
    def detect_form(self, url):
        """
        Detects application form on a given URL
        
        Args:
            url (str): URL of the opportunity application page
            
        Returns:
            dict: Detected form fields and metadata
        """
        try:
            # Fetch the page content
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            html_content = response.text
            
            # Use BeautifulSoup to parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract all form elements
            forms = soup.find_all('form')
            if not forms:
                logger.warning(f"No forms detected on {url}")
                # Try to find div elements that might contain form-like structures
                form_classes = ['form', 'application', 'submit']
                possible_form_containers = []
                for tag in ['div', 'section']:
                    elements = soup.find_all(tag)
                    for element in elements:
                        if element.has_attr('class') and any(term in ' '.join(element['class']).lower() for term in form_classes):
                            possible_form_containers.append(element)
                if not possible_form_containers:
                    return {
                        'success': False,
                        'message': 'No application form detected on this page',
                        'form_fields': []
                    }
                
                # Use the first potential form container
                form_container = possible_form_containers[0]
            else:
                # Use the largest form (likely the main application form)
                form_container = max(forms, key=lambda f: len(str(f)))
            
            # Extract input fields, textareas, and selects
            input_fields = form_container.find_all('input')
            textareas = form_container.find_all('textarea')
            selects = form_container.find_all('select')
            
            # Process all field types
            form_fields = []
            
            # Process input fields
            for input_field in input_fields:
                field_type = input_field.get('type', 'text')
                if field_type in ['submit', 'button', 'reset', 'hidden']:
                    continue
                
                field = {
                    'name': input_field.get('name', ''),
                    'id': input_field.get('id', ''),
                    'type': field_type,
                    'label': self._find_label(input_field, soup),
                    'placeholder': input_field.get('placeholder', ''),
                    'required': input_field.has_attr('required'),
                    'value': input_field.get('value', '')
                }
                form_fields.append(field)
            
            # Process textareas
            for textarea in textareas:
                field = {
                    'name': textarea.get('name', ''),
                    'id': textarea.get('id', ''),
                    'type': 'textarea',
                    'label': self._find_label(textarea, soup),
                    'placeholder': textarea.get('placeholder', ''),
                    'required': textarea.has_attr('required'),
                    'value': textarea.text.strip()
                }
                form_fields.append(field)
            
            # Process select dropdowns
            for select in selects:
                options = []
                for option in select.find_all('option'):
                    options.append({
                        'value': option.get('value', ''),
                        'text': option.text.strip()
                    })
                
                field = {
                    'name': select.get('name', ''),
                    'id': select.get('id', ''),
                    'type': 'select',
                    'label': self._find_label(select, soup),
                    'required': select.has_attr('required'),
                    'options': options,
                    'value': ''
                }
                form_fields.append(field)
            
            # Use AI to analyze the form structure if needed
            if not form_fields:
                form_fields = self._analyze_with_ai(html_content)
            
            # Categorize fields using AI
            categorized_fields = self._categorize_fields(form_fields)
            
            return {
                'success': True,
                'url': url,
                'form_detected': True,
                'form_fields': categorized_fields,
                'detected_at': datetime.utcnow().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Error fetching the URL {url}: {e}")
            return {
                'success': False,
                'message': f"Error accessing the URL: {str(e)}",
                'form_fields': []
            }
        except Exception as e:
            logger.error(f"Error analyzing form on {url}: {e}")
            return {
                'success': False,
                'message': f"Error analyzing form: {str(e)}",
                'form_fields': []
            }
    
    def _find_label(self, field, soup):
        """Find the label text for a form field"""
        field_id = field.get('id')
        if field_id:
            label = soup.find('label', attrs={'for': field_id})
            if label:
                return label.text.strip()
        
        # Look for parent label
        parent_label = field.find_parent('label')
        if parent_label:
            # Remove the text of any inputs/selects within the label
            for element in parent_label.find_all(['input', 'select', 'textarea']):
                element.extract()
            return parent_label.text.strip()
        
        return ""
    
    def _analyze_with_ai(self, html_content):
        """Use AI to extract form fields from complex HTML"""
        try:
            # Prepare a simplified HTML version
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Create a simplified version focusing on form-related elements
            form_elements = soup.find_all(['form', 'input', 'textarea', 'select', 'label', 'button'])
            simplified_html = "\n".join([str(el) for el in form_elements])
            
            # Make sure it's not too long for the API call
            if len(simplified_html) > 50000:
                simplified_html = simplified_html[:50000]
            
            try:
                # Check if OpenAI is available
                if not OPENAI_AVAILABLE or client is None:
                    raise Exception("OpenAI API is not available")
                
                prompt = f"""
                Extract all form fields from this HTML. The HTML represents an application form on a website.
                Identify each input field, textarea, or select dropdown, along with:
                1. The field name/ID
                2. The field label or description
                3. The field type (text, email, dropdown, etc.)
                4. Whether it appears to be required
                
                Format your response as a JSON array of form fields with the properties:
                - name: the name or id attribute of the field
                - label: the text label associated with the field
                - type: the type of field (text, email, textarea, select, etc.)
                - required: boolean indicating if the field appears to be required
                
                HTML:
                {simplified_html}
                """
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert HTML parser specialized in extracting form structures from websites."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                # Parse the result
                result = json.loads(response.choices[0].message.content)
                
                if 'form_fields' in result:
                    return result['form_fields']
                return result
                
            except Exception as ai_error:
                # If AI analysis fails, fall back to basic form field extraction
                logger.warning(f"AI analysis failed: {ai_error}. Falling back to basic extraction.")
                
                # Extract form fields without AI
                form_fields = []
                
                # Process all input fields
                for input_field in soup.find_all('input'):
                    field_type = input_field.get('type', 'text')
                    if field_type in ['submit', 'button', 'reset', 'hidden']:
                        continue
                    
                    name = input_field.get('name', '')
                    id_attr = input_field.get('id', '')
                    
                    # Skip fields without name or id
                    if not name and not id_attr:
                        continue
                    
                    # Look for labels
                    label_text = ""
                    if id_attr:
                        label = soup.find('label', attrs={'for': id_attr})
                        if label:
                            label_text = label.text.strip()
                    
                    # Add to form fields
                    form_fields.append({
                        'name': name or id_attr,
                        'id': id_attr,
                        'type': field_type,
                        'label': label_text,
                        'placeholder': input_field.get('placeholder', ''),
                        'required': input_field.has_attr('required'),
                        'value': input_field.get('value', '')
                    })
                
                # Process textareas
                for textarea in soup.find_all('textarea'):
                    name = textarea.get('name', '')
                    id_attr = textarea.get('id', '')
                    
                    # Skip fields without name or id
                    if not name and not id_attr:
                        continue
                    
                    # Look for labels
                    label_text = ""
                    if id_attr:
                        label = soup.find('label', attrs={'for': id_attr})
                        if label:
                            label_text = label.text.strip()
                    
                    # Add to form fields
                    form_fields.append({
                        'name': name or id_attr,
                        'id': id_attr,
                        'type': 'textarea',
                        'label': label_text,
                        'placeholder': textarea.get('placeholder', ''),
                        'required': textarea.has_attr('required'),
                        'value': textarea.text.strip()
                    })
                
                # Process selects
                for select in soup.find_all('select'):
                    name = select.get('name', '')
                    id_attr = select.get('id', '')
                    
                    # Skip fields without name or id
                    if not name and not id_attr:
                        continue
                    
                    # Look for labels
                    label_text = ""
                    if id_attr:
                        label = soup.find('label', attrs={'for': id_attr})
                        if label:
                            label_text = label.text.strip()
                    
                    # Get options
                    options = []
                    for option in select.find_all('option'):
                        options.append({
                            'value': option.get('value', ''),
                            'text': option.text.strip()
                        })
                    
                    # Add to form fields
                    form_fields.append({
                        'name': name or id_attr,
                        'id': id_attr,
                        'type': 'select',
                        'label': label_text,
                        'required': select.has_attr('required'),
                        'options': options,
                        'value': ''
                    })
                
                return form_fields
            
        except Exception as e:
            logger.error(f"Error using AI to analyze form: {e}")
            return []
    
    def _categorize_fields(self, form_fields):
        """Categorize form fields into standard categories using AI"""
        if not form_fields:
            return []
            
        try:
            try:
                # Check if OpenAI is available
                if not OPENAI_AVAILABLE or client is None:
                    raise Exception("OpenAI API is not available")
                
                # Convert form fields to JSON for the prompt
                fields_json = json.dumps(form_fields, indent=2)
                
                prompt = f"""
                Categorize these form fields into standard categories for an artist application.
                For each field, determine what artist information category it belongs to.
                
                Common categories include:
                - PERSONAL_INFO (name, email, phone, address, etc.)
                - ARTIST_STATEMENT
                - BIOGRAPHY
                - PROJECT_PROPOSAL
                - PORTFOLIO
                - EDUCATION
                - EXHIBITION_HISTORY
                - REFERENCES
                - ADMINISTRATIVE (terms, consent, etc.)
                
                Form fields:
                {fields_json}
                
                For each field, add a 'category' property with one of the standard categories above.
                Return the enhanced fields list as JSON.
                """
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert in analyzing artist application forms and categorizing fields."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                # Parse the result
                result = json.loads(response.choices[0].message.content)
                
                if 'fields' in result:
                    return result['fields']
                return result
                
            except Exception as ai_error:
                # If AI categorization fails, fall back to basic categorization
                logger.warning(f"AI categorization failed: {ai_error}. Using simple heuristic categorization.")
                
                # Apply simple categorization rules
                categorized_fields = []
                
                # Common keywords for each category
                category_keywords = {
                    'PERSONAL_INFO': ['name', 'email', 'phone', 'address', 'city', 'state', 'zip', 'postal', 'country', 'contact'],
                    'ARTIST_STATEMENT': ['statement', 'artistic', 'practice', 'work', 'philosophy'],
                    'BIOGRAPHY': ['bio', 'biography', 'about', 'yourself'],
                    'PROJECT_PROPOSAL': ['proposal', 'project', 'plan', 'concept', 'idea'],
                    'PORTFOLIO': ['portfolio', 'images', 'works', 'gallery', 'artwork', 'samples'],
                    'EDUCATION': ['education', 'degree', 'university', 'school', 'college', 'academic'],
                    'EXHIBITION_HISTORY': ['exhibition', 'shows', 'display', 'history', 'gallery', 'museum'],
                    'REFERENCES': ['reference', 'referral', 'recommend', 'recommendation'],
                    'ADMINISTRATIVE': ['terms', 'conditions', 'agree', 'consent', 'privacy', 'policy', 'accept']
                }
                
                for field in form_fields:
                    # Get field properties to check
                    name = (field.get('name', '') or '').lower()
                    label = (field.get('label', '') or '').lower()
                    placeholder = (field.get('placeholder', '') or '').lower()
                    field_type = (field.get('type', '') or '').lower()
                    
                    # Text to check for keywords
                    text_to_check = f"{name} {label} {placeholder}"
                    
                    # Default category
                    category = 'UNKNOWN'
                    
                    # Check each category's keywords
                    for cat, keywords in category_keywords.items():
                        if any(keyword in text_to_check for keyword in keywords):
                            category = cat
                            break
                    
                    # Special cases based on field type
                    if category == 'UNKNOWN':
                        if field_type == 'email':
                            category = 'PERSONAL_INFO'
                        elif field_type == 'tel':
                            category = 'PERSONAL_INFO'
                        elif field_type == 'textarea' and label:
                            # Long text fields are likely statements/proposals
                            if 'statement' in label:
                                category = 'ARTIST_STATEMENT'
                            elif 'proposal' in label:
                                category = 'PROJECT_PROPOSAL'
                            elif 'bio' in label or 'about' in label:
                                category = 'BIOGRAPHY'
                    
                    # Add category to field
                    field_copy = field.copy()
                    field_copy['category'] = category
                    categorized_fields.append(field_copy)
                
                return categorized_fields
            
        except Exception as e:
            logger.error(f"Error categorizing form fields: {e}")
            # Return original fields if categorization fails
            return form_fields


class ApplicationAutoFiller:
    """
    Automatically fills application forms based on artist profile and portfolio data.
    """
    
    def __init__(self):
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
        self.detector = ApplicationFormDetector()
    
    def generate_application_content(self, artist_data, opportunity_data, form_fields):
        """
        Generate content for an application form based on artist data and opportunity.
        
        Args:
            artist_data (dict): Artist profile and portfolio data
            opportunity_data (dict): Information about the opportunity
            form_fields (list): List of detected form fields
            
        Returns:
            dict: Generated content for each field
        """
        try:
            # Group fields by category
            fields_by_category = {}
            for field in form_fields:
                category = field.get('category', 'UNKNOWN')
                if category not in fields_by_category:
                    fields_by_category[category] = []
                fields_by_category[category].append(field)
            
            # Generate content for each category
            filled_fields = {}
            
            # Handle personal information fields directly
            if 'PERSONAL_INFO' in fields_by_category:
                personal_info_fields = fields_by_category['PERSONAL_INFO']
                for field in personal_info_fields:
                    field_name = field.get('name') or field.get('id')
                    if not field_name:
                        continue
                        
                    # Match common personal info fields
                    field_label = field.get('label', '').lower()
                    field_placeholder = field.get('placeholder', '').lower()
                    
                    # Try to match field with artist data
                    if any(term in field_label or term in field_placeholder for term in ['name', 'full name']):
                        filled_fields[field_name] = artist_data.get('name', '')
                    elif any(term in field_label or term in field_placeholder for term in ['email']):
                        filled_fields[field_name] = artist_data.get('email', '')
                    elif any(term in field_label or term in field_placeholder for term in ['phone']):
                        filled_fields[field_name] = artist_data.get('phone', '')
                    elif any(term in field_label or term in field_placeholder for term in ['address']):
                        filled_fields[field_name] = artist_data.get('address', '')
                    elif any(term in field_label or term in field_placeholder for term in ['city']):
                        filled_fields[field_name] = artist_data.get('city', '')
                    elif any(term in field_label or term in field_placeholder for term in ['state']):
                        filled_fields[field_name] = artist_data.get('state', '')
                    elif any(term in field_label or term in field_placeholder for term in ['zip', 'postal']):
                        filled_fields[field_name] = artist_data.get('zip_code', '')
                    elif any(term in field_label or term in field_placeholder for term in ['country']):
                        filled_fields[field_name] = artist_data.get('country', '')
                    elif any(term in field_label or term in field_placeholder for term in ['website']):
                        filled_fields[field_name] = artist_data.get('website', '')
            
            # Use AI to generate content for more complex fields
            for category, fields in fields_by_category.items():
                # Skip personal info which we handled above
                if category == 'PERSONAL_INFO':
                    continue
                
                # Skip administrative fields
                if category == 'ADMINISTRATIVE':
                    continue
                
                # Generate content for this category
                category_content = self._generate_category_content(
                    category, 
                    fields, 
                    artist_data, 
                    opportunity_data
                )
                
                # Add to filled fields
                filled_fields.update(category_content)
            
            return {
                'success': True,
                'filled_fields': filled_fields
            }
            
        except Exception as e:
            logger.error(f"Error generating application content: {e}")
            return {
                'success': False,
                'message': f"Error generating content: {str(e)}",
                'filled_fields': {}
            }
    
    def _generate_category_content(self, category, fields, artist_data, opportunity_data):
        """Generate content for fields in a specific category"""
        try:
            # Prepare the field information for the prompt
            fields_json = json.dumps([{
                'name': f.get('name') or f.get('id'),
                'label': f.get('label', ''),
                'placeholder': f.get('placeholder', ''),
                'type': f.get('type', ''),
                'max_length': f.get('maxlength', 0)
            } for f in fields], indent=2)
            
            try:
                # Check if OpenAI is available
                if not OPENAI_AVAILABLE or client is None:
                    raise Exception("OpenAI API is not available")
                    
                # Create a prompt based on the category
                if category == 'ARTIST_STATEMENT':
                    prompt = f"""
                    Generate an artist statement for an application to this opportunity:
                    
                    Opportunity: {opportunity_data.get('title', '')}
                    Description: {opportunity_data.get('description', '')}
                    
                    Artist: {artist_data.get('name', '')}
                    Artist Medium/Style: {artist_data.get('art_type', '')}
                    Artist Background: {artist_data.get('biography', '')}
                    
                    The statement should be tailored to these form fields:
                    {fields_json}
                    
                    Create a compelling artist statement that connects the artist's work with this specific opportunity.
                    Make sure the content is appropriate for the length and nature of each field.
                    Return a JSON object with field names as keys and the generated content as values.
                    """
                    
                elif category == 'PROJECT_PROPOSAL':
                    prompt = f"""
                    Generate a project proposal for an application to this opportunity:
                    
                    Opportunity: {opportunity_data.get('title', '')}
                    Description: {opportunity_data.get('description', '')}
                    
                    Artist: {artist_data.get('name', '')}
                    Artist Medium/Style: {artist_data.get('art_type', '')}
                    Artist Background: {artist_data.get('biography', '')}
                    Portfolio highlights: {json.dumps(artist_data.get('portfolio_highlights', []), indent=2)}
                    
                    The proposal should be tailored to these form fields:
                    {fields_json}
                    
                    Create a thoughtful project proposal that aligns with the opportunity and showcases the artist's strengths.
                    Include specific details about execution, timeline, and expected outcomes when appropriate.
                    Return a JSON object with field names as keys and the generated content as values.
                    """
                    
                elif category == 'BIOGRAPHY':
                    prompt = f"""
                    Generate an artist biography for an application to this opportunity:
                    
                    Opportunity: {opportunity_data.get('title', '')}
                    
                    Artist: {artist_data.get('name', '')}
                    Artist Medium/Style: {artist_data.get('art_type', '')}
                    Artist Background: {artist_data.get('biography', '')}
                    Education: {artist_data.get('education', '')}
                    Exhibition History: {json.dumps(artist_data.get('exhibition_history', []), indent=2)}
                    
                    The biography should be tailored to these form fields:
                    {fields_json}
                    
                    Create a professional artist biography that emphasizes relevant experience for this opportunity.
                    Make sure the content is appropriate for the length and nature of each field.
                    Return a JSON object with field names as keys and the generated content as values.
                    """
                    
                else:
                    # General prompt for other categories
                    prompt = f"""
                    Generate content for the form fields in the {category} category:
                    
                    Opportunity: {opportunity_data.get('title', '')}
                    Description: {opportunity_data.get('description', '')}
                    
                    Artist information: {json.dumps(artist_data, indent=2)}
                    
                    Fields to fill: {fields_json}
                    
                    Create appropriate content for each field based on the artist information and the opportunity.
                    Make sure the content is appropriate for the length and nature of each field.
                    Return a JSON object with field names as keys and the generated content as values.
                    """
                
                # Generate content with AI
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert in generating professional content for artist applications."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                # Parse the result
                result = json.loads(response.choices[0].message.content)
                
                # Clean up the result to ensure it's a simple key-value mapping
                field_content = {}
                for field in fields:
                    field_name = field.get('name') or field.get('id')
                    if not field_name:
                        continue
                    
                    if field_name in result:
                        field_content[field_name] = result[field_name]
                
                return field_content
                
            except Exception as ai_error:
                # If AI generation fails, fall back to template-based content
                logger.warning(f"AI content generation failed: {ai_error}. Using template-based content.")
                
                # Generate simple content based on templates
                field_content = {}
                
                for field in fields:
                    field_name = field.get('name') or field.get('id')
                    if not field_name:
                        continue
                    
                    # Get field properties
                    field_label = field.get('label', '').lower()
                    field_type = field.get('type', '')
                    
                    # Generate content based on category
                    if category == 'ARTIST_STATEMENT':
                        field_content[field_name] = (
                            f"As a {artist_data.get('art_type', 'visual artist')}, my work explores the relationship "
                            f"between form and content. {artist_data.get('biography', '').split('.')[0] if artist_data.get('biography') else ''} "
                            f"This opportunity aligns with my artistic goals by providing a platform to further develop "
                            f"my exploration of {opportunity_data.get('title', 'contemporary art')}."
                        )
                    
                    elif category == 'PROJECT_PROPOSAL':
                        field_content[field_name] = (
                            f"For this {opportunity_data.get('title', 'opportunity')}, I propose to create "
                            f"a series based on {artist_data.get('art_type', 'visual art')}. "
                            f"The project will explore themes of identity and environment, "
                            f"building on my previous work with {artist_data.get('portfolio_highlights', ['mixed media'])[0] if artist_data.get('portfolio_highlights') else 'various materials'}. "
                            f"The timeline includes research (2 weeks), creation (4 weeks), and refinement (2 weeks)."
                        )
                    
                    elif category == 'BIOGRAPHY':
                        # Create a biography from available information
                        bio_parts = []
                        
                        if artist_data.get('name'):
                            bio_parts.append(f"{artist_data.get('name')} is a {artist_data.get('art_type', 'visual artist')}.")
                        
                        if artist_data.get('education'):
                            bio_parts.append(f"Education includes {artist_data.get('education')}.")
                        
                        if artist_data.get('exhibition_history') and len(artist_data.get('exhibition_history')) > 0:
                            recent_shows = artist_data.get('exhibition_history')[:2]
                            shows_text = ", ".join([f"{show.get('title')} at {show.get('venue')} ({show.get('year')})" for show in recent_shows])
                            bio_parts.append(f"Recent exhibitions include {shows_text}.")
                        
                        if artist_data.get('biography'):
                            first_sentence = artist_data.get('biography').split('.')[0] + '.'
                            bio_parts.append(first_sentence)
                        
                        field_content[field_name] = " ".join(bio_parts)
                    
                    elif category == 'PORTFOLIO':
                        field_content[field_name] = (
                            f"My portfolio showcases my work in {artist_data.get('art_type', 'visual art')}, "
                            f"highlighting my technical skills and conceptual approach. "
                            f"Key works include {', '.join(artist_data.get('portfolio_highlights', ['recent projects'])[:2] if artist_data.get('portfolio_highlights') else ['recent projects'])}."
                        )
                    
                    elif category == 'EDUCATION':
                        field_content[field_name] = artist_data.get('education', 'Education details available upon request.')
                    
                    else:
                        # Default content for unknown categories
                        field_content[field_name] = (
                            f"Information related to {field_label or category.lower()} for {artist_data.get('name', 'the artist')}. "
                            f"Please contact for more specific details."
                        )
                    
                    # Adjust content length based on field type
                    if field_type == 'text' and len(field_content[field_name]) > 100:
                        field_content[field_name] = field_content[field_name].split('.')[0] + '.'
                
                return field_content
            
        except Exception as e:
            logger.error(f"Error generating content for {category}: {e}")
            return {}


class ApplicationSubmitter:
    """
    Submits application forms and tracks application status.
    """
    
    def __init__(self):
        self.session = requests.Session()
    
    def submit_application(self, url, form_data, artist_data):
        """
        Submit an application form with the provided data.
        
        Args:
            url (str): URL of the application form
            form_data (dict): Form data to submit
            artist_data (dict): Artist information for tracking
            
        Returns:
            dict: Submission result and tracking information
        """
        try:
            # This is a placeholder for actual form submission logic
            # In a production environment, this would use more sophisticated techniques
            # such as browser automation (Selenium) to handle various form types
            
            # For now, return a simulated successful submission
            submission_id = f"sub_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            return {
                'success': True,
                'message': 'Application prepared for submission',
                'submission_id': submission_id,
                'submission_url': url,
                'submission_date': datetime.utcnow().isoformat(),
                'status': 'prepared',
                'tracking_info': {
                    'artist_id': artist_data.get('id'),
                    'artist_name': artist_data.get('name'),
                    'opportunity_title': form_data.get('opportunity_title', 'Unknown Opportunity'),
                    'form_fields_count': len(form_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error submitting application to {url}: {e}")
            return {
                'success': False,
                'message': f"Error submitting application: {str(e)}",
                'status': 'failed'
            }


class ApplicationTracker:
    """
    Tracks the status of submitted applications.
    """
    
    def __init__(self):
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
    
    def track_application(self, application_data, check_url=None):
        """
        Track the status of a submitted application.
        
        Args:
            application_data (dict): Data about the application
            check_url (str, optional): URL to check for status updates
            
        Returns:
            dict: Updated application status
        """
        # This is a placeholder for actual tracking logic
        # In a production environment, this would check emails, status pages, etc.
        
        # For now, return the current status with timestamp
        return {
            'success': True,
            'application_id': application_data.get('submission_id'),
            'status': application_data.get('status', 'unknown'),
            'last_checked': datetime.utcnow().isoformat(),
            'status_message': 'Application is being processed'
        }


# Example usage
def test_form_detection(url):
    """Test the form detection with a sample URL"""
    detector = ApplicationFormDetector()
    result = detector.detect_form(url)
    print(json.dumps(result, indent=2))
    return result

def test_auto_fill(artist_data, opportunity_data, form_fields):
    """Test the auto-fill with sample data"""
    filler = ApplicationAutoFiller()
    result = filler.generate_application_content(artist_data, opportunity_data, form_fields)
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    # This code runs when the script is executed directly
    print("Proletto Application Auto-Fill System")
    
    # Replace with an actual opportunity URL
    test_url = "https://www.callforentry.org/festivals_unique_info.php?ID=7003"
    
    # Run a test detection
    detected_form = test_form_detection(test_url)
    
    # If form was detected, run a test auto-fill
    if detected_form.get('success') and detected_form.get('form_fields'):
        test_artist = {
            "id": 123,
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
        
        test_opportunity = {
            "title": "Digital Art Residency 2025",
            "description": "A three-month residency program for artists exploring digital media and technology."
        }
        
        test_auto_fill(test_artist, test_opportunity, detected_form['form_fields'])