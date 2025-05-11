"""
Proletto AI Portfolio Optimizer
This module provides AI-powered portfolio optimization for artists.
It analyzes portfolio content, suggests improvements, and recommends
opportunities that match the artist's strengths.
"""

import os
import json
import logging
from openai import OpenAI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the OpenAI client
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

class PortfolioOptimizer:
    """
    AI-powered portfolio optimizer for artists.
    Uses OpenAI's GPT-4o model to analyze portfolios and provide
    personalized recommendations to improve application success rates.
    """
    
    def __init__(self):
        """Initialize the portfolio optimizer."""
        self.model = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
        
    def analyze_portfolio(self, portfolio_data):
        """
        Analyze an artist's portfolio and provide feedback.
        
        Args:
            portfolio_data (dict): A dictionary containing portfolio information
                {
                    "artist_name": str,
                    "art_type": str,
                    "portfolio_description": str,
                    "portfolio_items": list,
                    "past_exhibitions": list,
                    "target_opportunities": list (optional)
                }
                
        Returns:
            dict: Analysis results including strengths, weaknesses, and recommendations
        """
        try:
            # Construct the prompt for the AI
            prompt = self._build_analysis_prompt(portfolio_data)
            
            # Get analysis from OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert art curator and gallery owner with decades of experience reviewing artist portfolios. Provide detailed, constructive feedback on the artist's portfolio to help them improve and match with ideal opportunities."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            # Parse the response
            analysis = json.loads(response.choices[0].message.content)
            
            # Enhance the analysis with opportunity matching if targets provided
            if "target_opportunities" in portfolio_data and portfolio_data["target_opportunities"]:
                analysis["opportunity_matches"] = self.match_opportunities(
                    portfolio_data, 
                    portfolio_data["target_opportunities"]
                )
            
            return {
                "success": True,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def optimize_portfolio(self, portfolio_data, optimization_goals=None):
        """
        Provide specific recommendations to optimize a portfolio for success.
        
        Args:
            portfolio_data (dict): Artist portfolio information
            optimization_goals (list): Specific goals for the optimization
                
        Returns:
            dict: Optimization plan with actionable steps
        """
        try:
            # First get portfolio analysis as foundation
            analysis_result = self.analyze_portfolio(portfolio_data)
            
            if not analysis_result["success"]:
                return analysis_result
            
            # Build optimization prompt based on analysis and goals
            optimization_prompt = self._build_optimization_prompt(
                portfolio_data, 
                analysis_result["analysis"],
                optimization_goals
            )
            
            # Get optimization recommendations from OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI-powered portfolio optimization assistant with expertise in helping artists win grants, residencies, and exhibitions. Provide detailed, actionable recommendations to improve portfolio success rates."},
                    {"role": "user", "content": optimization_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            # Parse the response
            optimization_plan = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "optimization_plan": optimization_plan
            }
            
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def match_opportunities(self, portfolio_data, opportunities):
        """
        Match portfolio to relevant opportunities and rank by fit.
        
        Args:
            portfolio_data (dict): Artist portfolio information
            opportunities (list): Available opportunities to match against
                
        Returns:
            list: Ranked opportunities with match confidence scores
        """
        try:
            # Build the matching prompt
            matching_prompt = self._build_matching_prompt(portfolio_data, opportunities)
            
            # Get matching results from OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI-powered opportunity matching system that helps artists find the most relevant opportunities for their work. Rank opportunities by relevance and explain why they're a good fit."},
                    {"role": "user", "content": matching_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.5
            )
            
            # Parse the response
            matches = json.loads(response.choices[0].message.content)
            
            return matches
            
        except Exception as e:
            logger.error(f"Error matching opportunities: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_application_materials(self, portfolio_data, opportunity, material_type):
        """
        Generate application materials for a specific opportunity.
        
        Args:
            portfolio_data (dict): Artist portfolio information
            opportunity (dict): The opportunity to apply for
            material_type (str): Type of material to generate (artist_statement, 
                                 cover_letter, project_proposal)
                
        Returns:
            dict: Generated application material
        """
        try:
            # Build the prompt for generating application materials
            application_prompt = self._build_application_prompt(
                portfolio_data, 
                opportunity, 
                material_type
            )
            
            # Get generated material from OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an AI-powered application writer with expertise in helping artists craft compelling application materials for grants, residencies, and exhibitions. Write in the artist's authentic voice while highlighting their unique strengths."},
                    {"role": "user", "content": application_prompt}
                ],
                temperature=0.8
            )
            
            # Format the response
            generated_content = response.choices[0].message.content
            
            return {
                "success": True,
                "material_type": material_type,
                "content": generated_content
            }
            
        except Exception as e:
            logger.error(f"Error generating application materials: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_analysis_prompt(self, portfolio_data):
        """Build prompt for portfolio analysis."""
        prompt = f"""
        Please analyze the following artist portfolio in detail:
        
        Artist Name: {portfolio_data.get('artist_name', 'Not provided')}
        Art Type/Medium: {portfolio_data.get('art_type', 'Not provided')}
        
        Portfolio Description:
        {portfolio_data.get('portfolio_description', 'Not provided')}
        
        Portfolio Items:
        {json.dumps(portfolio_data.get('portfolio_items', []), indent=2)}
        
        Past Exhibitions/Shows:
        {json.dumps(portfolio_data.get('past_exhibitions', []), indent=2)}
        
        Provide a detailed analysis of this portfolio in JSON format with the following sections:
        1. Overview and first impressions
        2. Portfolio strengths
        3. Areas for improvement
        4. Coherence and narrative
        5. Technical skill assessment
        6. Market positioning
        7. Recommended next steps
        
        Include specific actionable recommendations that will help this artist increase their chances of being accepted for grants, residencies, and exhibitions.
        """
        return prompt
    
    def _build_optimization_prompt(self, portfolio_data, analysis, optimization_goals=None):
        """Build prompt for portfolio optimization."""
        goals_text = ""
        if optimization_goals:
            goals_text = f"""
            The artist has specified the following optimization goals:
            {json.dumps(optimization_goals, indent=2)}
            
            Please ensure your recommendations address these specific goals.
            """
        
        prompt = f"""
        Based on the following portfolio analysis:
        {json.dumps(analysis, indent=2)}
        
        For this artist:
        Artist Name: {portfolio_data.get('artist_name', 'Not provided')}
        Art Type/Medium: {portfolio_data.get('art_type', 'Not provided')}
        
        {goals_text}
        
        Create a detailed portfolio optimization plan in JSON format that includes:
        1. "executive_summary": A brief summary of the optimization strategy
        2. "priority_changes": Top 3-5 highest-impact changes to make immediately
        3. "content_recommendations": Specific suggestions for what to add, remove, or modify in the portfolio
        4. "presentation_improvements": How to better present the existing work
        5. "narrative_development": How to strengthen the portfolio's story and artist's unique voice
        6. "technical_skill_focus": Areas to improve technically
        7. "strategic_additions": New work or projects to consider creating
        8. "implementation_timeline": Suggested timeline for making these changes
        9. "expected_outcomes": What results the artist can expect after optimization
        
        Make all recommendations specific, actionable, and tailored to this particular artist's work and goals.
        """
        return prompt
    
    def _build_matching_prompt(self, portfolio_data, opportunities):
        """Build prompt for opportunity matching."""
        prompt = f"""
        Match the following artist portfolio:
        
        Artist Name: {portfolio_data.get('artist_name', 'Not provided')}
        Art Type/Medium: {portfolio_data.get('art_type', 'Not provided')}
        
        Portfolio Description:
        {portfolio_data.get('portfolio_description', 'Not provided')}
        
        With these opportunities:
        {json.dumps(opportunities, indent=2)}
        
        Provide a ranked list of the top matches in JSON format with the following structure:
        {{
            "matches": [
                {{
                    "opportunity_id": "id of the opportunity",
                    "title": "title of the opportunity",
                    "match_score": 0-100 (a numerical score indicating fit),
                    "match_rationale": "detailed explanation of why this is a good match",
                    "application_strategy": "specific suggestions for applying to this opportunity"
                }}
            ]
        }}
        
        Only include opportunities with a match score of 60 or higher. Rank them in descending order by match score.
        """
        return prompt
    
    def _build_application_prompt(self, portfolio_data, opportunity, material_type):
        """Build prompt for generating application materials."""
        content_type_instructions = {
            "artist_statement": "Create a compelling artist statement that describes the artist's work, approach, philosophy, and vision. Keep it authentic, specific, and aligned with the opportunity's focus.",
            "cover_letter": "Write a persuasive cover letter for this specific opportunity that highlights relevant experience and explains why the artist is a perfect fit.",
            "project_proposal": "Develop a detailed project proposal tailored to this opportunity that outlines the concept, execution plan, timeline, and expected impact."
        }
        
        instructions = content_type_instructions.get(
            material_type, 
            "Create application content for this opportunity."
        )
        
        prompt = f"""
        Based on this artist portfolio:
        
        Artist Name: {portfolio_data.get('artist_name', 'Not provided')}
        Art Type/Medium: {portfolio_data.get('art_type', 'Not provided')}
        
        Portfolio Description:
        {portfolio_data.get('portfolio_description', 'Not provided')}
        
        For this opportunity:
        {json.dumps(opportunity, indent=2)}
        
        {instructions}
        
        Ensure the writing captures the artist's unique voice while meeting all the requirements of the opportunity.
        """
        return prompt


# Testing function (for development purposes only)
def test_portfolio_optimizer():
    """Test the portfolio optimizer with sample data."""
    # Create sample portfolio data
    sample_portfolio = {
        "artist_name": "Alex Rivera",
        "art_type": "Mixed media installation and digital art",
        "portfolio_description": "My work explores the intersection of technology, nature, and human experience through immersive installations and digital compositions. I combine natural materials with electronic elements to create experiences that question our relationship with the digital world.",
        "portfolio_items": [
            {
                "title": "Digital Erosion",
                "year": 2023,
                "medium": "Interactive projection on sculpted sand",
                "description": "An installation where viewers' movements cause digital projections to erode virtual landscapes mapped onto physical sand formations."
            },
            {
                "title": "Memory Cache",
                "year": 2022,
                "medium": "Video installation with found objects",
                "description": "A room-sized installation exploring digital memory through projected video onto arranged personal artifacts."
            },
            {
                "title": "Biometric Resonance",
                "year": 2021,
                "medium": "Sound installation with heart rate sensors",
                "description": "An audio experience where visitors' heartbeats influence an evolving soundscape."
            }
        ],
        "past_exhibitions": [
            {
                "title": "Emergent Technologies Biennial",
                "venue": "Contemporary Arts Center",
                "location": "Chicago, IL",
                "year": 2023
            },
            {
                "title": "Digital Frontiers",
                "venue": "New Media Gallery",
                "location": "Seattle, WA",
                "year": 2022
            }
        ]
    }
    
    # Create sample opportunities
    sample_opportunities = [
        {
            "id": "opp1",
            "title": "Tech Arts Residency",
            "organization": "Digital Arts Foundation",
            "location": "San Francisco, CA",
            "description": "A 3-month residency for artists working at the intersection of technology and traditional art forms.",
            "deadline": "2023-06-30"
        },
        {
            "id": "opp2",
            "title": "Environmental Art Grant",
            "organization": "EcoCreative Initiative",
            "location": "Portland, OR",
            "description": "Funding for projects that address environmental issues through innovative art practices.",
            "deadline": "2023-07-15"
        },
        {
            "id": "opp3",
            "title": "Immersive Installations Exhibition",
            "organization": "Modern Art Museum",
            "location": "Boston, MA",
            "description": "A group exhibition focused on immersive, experiential art installations.",
            "deadline": "2023-08-01"
        }
    ]
    
    # Initialize the optimizer
    optimizer = PortfolioOptimizer()
    
    # Test portfolio analysis
    analysis_result = optimizer.analyze_portfolio(sample_portfolio)
    print("\n--- Portfolio Analysis ---")
    print(json.dumps(analysis_result, indent=2))
    
    # Test portfolio optimization
    optimization_goals = ["Emphasize technological innovation", "Prepare for museum exhibition applications", "Develop more cohesive narrative across works"]
    optimization_result = optimizer.optimize_portfolio(sample_portfolio, optimization_goals)
    print("\n--- Portfolio Optimization Plan ---")
    print(json.dumps(optimization_result, indent=2))
    
    # Test opportunity matching
    sample_portfolio["target_opportunities"] = sample_opportunities
    matching_result = optimizer.match_opportunities(sample_portfolio, sample_opportunities)
    print("\n--- Opportunity Matches ---")
    print(json.dumps(matching_result, indent=2))
    
    # Test application material generation
    material_result = optimizer.generate_application_materials(
        sample_portfolio, 
        sample_opportunities[0],
        "project_proposal"
    )
    print("\n--- Generated Project Proposal ---")
    print(json.dumps(material_result, indent=2))


if __name__ == "__main__":
    # Only run test if explicitly called as a script
    # test_portfolio_optimizer()
    pass