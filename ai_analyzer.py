import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini API
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    # Use the correct model name for Gemini Flash
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("Gemini Flash API configured successfully")
except Exception as e:
    logger.error(f"Error configuring Gemini API: {str(e)}")
    model = None

def analyze_security_news(title, summary):
    """
    Analyze security news using Gemini Flash to provide insights and risk assessment
    """
    if model is None:
        return "AI analysis is currently unavailable. Please check your API key and internet connection."
    
    try:
        # Create a prompt for analysis
        prompt = f"""
        Analyze this security news and provide:
        1. A concise summary of the key points
        2. Potential impact assessment
        3. Recommended actions for security teams
        4. Risk level (Low/Medium/High/Critical)
        
        Title: {title}
        Summary: {summary}
        
        Please format the response in a clear, structured way.
        """
        
        # Generate response with optimized settings for Flash
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                top_p=0.8,
                top_k=40,
                max_output_tokens=1024,
            )
        )
        
        if response and hasattr(response, 'text'):
            return response.text
        else:
            return "AI analysis is currently unavailable. Please try again later."
    except Exception as e:
        logger.error(f"Error in AI analysis: {str(e)}")
        return "AI analysis is currently unavailable. Please try again later."

def get_risk_level(analysis):
    """
    Extract risk level from AI analysis
    """
    try:
        risk_levels = ['Critical', 'High', 'Medium', 'Low']
        for level in risk_levels:
            if level.lower() in analysis.lower():
                return level
        return 'Unknown'
    except Exception as e:
        logger.error(f"Error extracting risk level: {str(e)}")
        return 'Unknown' 