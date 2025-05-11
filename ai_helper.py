import os
import json
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
MODEL = "gpt-4o"

def generate_artist_opportunities(artist_interests=None):
    """Generate personalized artist opportunities based on interests."""
    try:
        prompt = "Generate 3 potential opportunities for visual artists"
        
        if artist_interests:
            prompt += f" interested in {artist_interests}"
        
        prompt += """. For each opportunity, include:
        1. Title
        2. Type (grant, residency, exhibition, etc.)
        3. Brief description (2-3 sentences)
        4. Estimated deadline
        5. Award amount or benefit
        
        Format as a JSON array with the following structure:
        [
            {
                "title": "Opportunity name",
                "type": "Type of opportunity",
                "description": "Brief description",
                "deadline": "Estimated deadline date",
                "award": "Award amount or benefit description"
            },
            ...
        ]
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "You are an expert in artist opportunities and grants."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating opportunities: {error_msg}")
        
        # Check if it's a quota error
        if "insufficient_quota" in error_msg:
            return [
                {
                    "title": "OpenAI API Quota Exceeded",
                    "type": "API Error",
                    "description": "The OpenAI API quota has been exceeded. This is a demo application and the API key has limited usage. In a production environment, this would use a paid API key with higher limits.",
                    "deadline": "N/A",
                    "award": "N/A"
                }
            ]
        
        return {"error": error_msg}

def analyze_artist_portfolio(portfolio_description):
    """Analyze an artist's portfolio and provide feedback."""
    try:
        prompt = f"""Analyze this artist's portfolio description and provide constructive feedback:
        
        Portfolio: {portfolio_description}
        
        Provide feedback on:
        1. Strengths of their work
        2. Areas that could be improved
        3. Potential opportunities that might suit their work
        4. Suggestions to enhance their artistic statement
        
        Format your response as JSON with the following structure:
        {{
            "strengths": ["strength 1", "strength 2", ...],
            "areas_for_improvement": ["area 1", "area 2", ...],
            "recommended_opportunities": ["opportunity 1", "opportunity 2", ...],
            "statement_suggestions": "Suggestions for improving their artist statement"
        }}
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "You are an expert art critic and mentor."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"Error analyzing portfolio: {error_msg}")
        
        # Check if it's a quota error
        if "insufficient_quota" in error_msg:
            return {
                "strengths": ["Demo Mode: OpenAI API quota exceeded. In a production environment, this would provide real analysis."],
                "areas_for_improvement": ["Get a production API key with sufficient quota to enable full functionality."],
                "recommended_opportunities": ["Sign up for OpenAI API access at platform.openai.com"],
                "statement_suggestions": "This is a demo application using the OpenAI API. The API quota has been exceeded. In a production environment, this would provide detailed feedback on your artist statement."
            }
        
        return {"error": error_msg}

def generate_application_tips(opportunity_type):
    """Generate tips for applying to specific types of art opportunities."""
    try:
        prompt = f"""Provide 5 practical tips for visual artists applying to {opportunity_type} opportunities.
        
        Format your response as a JSON array with the following structure:
        {{
            "tips": [
                {{
                    "title": "Tip title",
                    "description": "Detailed explanation of the tip"
                }},
                ...
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "You are an expert in artist grants and applications."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating application tips: {error_msg}")
        
        # Check if it's a quota error
        if "insufficient_quota" in error_msg:
            return {
                "tips": [
                    {
                        "title": "Demo Mode: API Quota Exceeded",
                        "description": "This is a demo application using the OpenAI API. The API quota has been exceeded. In a production environment with a paid API key, this would provide real tips for applying to art opportunities."
                    },
                    {
                        "title": "Consider Upgrading API Access",
                        "description": "To use this feature, a production API key with sufficient quota would be needed. You can sign up for OpenAI API access at platform.openai.com."
                    }
                ]
            }
        
        return {"error": error_msg}

def generate_personalized_suggestions(user_profile):
    """Generate personalized artist opportunity suggestions based on user profile data"""
    try:
        # Extract relevant information from user profile
        interests = user_profile.get('interests', [])
        portfolio_items = user_profile.get('portfolio_items', [])
        past_applications = user_profile.get('past_applications', [])
        location = user_profile.get('location', '')
        
        interests_text = ", ".join(interests) if interests else "various art forms"
        portfolio_text = ", ".join([item.get('title', '') for item in portfolio_items[:5]]) if portfolio_items else "their portfolio work"
        
        prompt = f"""Generate 3 personalized opportunity suggestions for a visual artist with the following profile:

        - Interests: {interests_text}
        - Portfolio includes: {portfolio_text}
        - Location: {location}
        
        For each suggestion, provide:
        1. Type of opportunity (grant, residency, exhibition, commission, etc.)
        2. A specific organization or program name that offers this
        3. Why it's a good fit for this artist specifically
        4. Estimated application timeline
        5. A specific tip for how this artist could improve their chances
        
        Format the response as a JSON object with the following structure:
        {{
            "suggestions": [
                {{
                    "title": "Opportunity name",
                    "type": "Type of opportunity",
                    "organization": "Organization name",
                    "fit_reason": "Why it's a good fit for this artist",
                    "timeline": "Application timeline",
                    "success_tip": "Tip for improving chances"
                }},
                ...
            ]
        }}
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "You are an expert in artist opportunities and career development with deep knowledge of grants, residencies, and exhibitions for visual artists."},
                      {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        error_msg = str(e)
        print(f"Error generating personalized suggestions: {error_msg}")
        
        # Check if it's a quota error
        if "insufficient_quota" in error_msg:
            return {
                "suggestions": [
                    {
                        "title": "Demo Mode: API Quota Exceeded",
                        "type": "API Error",
                        "organization": "OpenAI",
                        "fit_reason": "This is a demo application with limited API quota. In a production environment, you would receive personalized suggestions based on your profile.",
                        "timeline": "N/A",
                        "success_tip": "Consider using a production API key with sufficient quota to enable full functionality."
                    }
                ]
            }
        
        return {"error": error_msg}

def track_user_activity(user, activity_type, details=None):
    """Track user activity for badge awards and AI suggestions"""
    if not user:
        return
    
    # Update activity counts based on type
    if activity_type == "view_opportunity":
        user.opportunity_views += 1
    elif activity_type == "apply_opportunity":
        user.application_count += 1
    elif activity_type == "use_ai":
        user.ai_uses += 1
    elif activity_type == "upload_portfolio":
        user.portfolio_count += 1
    
    # Check for new badges
    new_badges = user.check_and_award_badges()
    
    # Return any new badges that were awarded
    return new_badges