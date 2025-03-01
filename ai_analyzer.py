
import os
import json
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ollama configuration
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")

def analyze_document(text, is_summary=False):
    """Analyze document content using Ollama"""
    try:
        # Format the prompt based on whether this is a summary request or full analysis
        if is_summary:
            prompt = """
            Summarize this research paper's title and abstract concisely. 
            Focus on the main contributions and findings.

            Respond with JSON in this format:
            {
                "summary": "brief overall summary of the paper (2-3 sentences)",
                "key_points": ["key point 1", "key point 2", "key point 3"]
            }

            Here's the paper to summarize:
            """ + text
        else:
            prompt = """
            Analyze this research document and provide a detailed analysis including:
            - summary
            - key points
            - methodology
            - findings
            - suggested citations

            Respond with JSON in this format:
            {
                "summary": "brief summary",
                "key_points": ["point 1", "point 2", ...],
                "methodology": "methodology description",
                "findings": ["finding 1", "finding 2", ...],
                "citations": ["citation 1", "citation 2", ...]
            }

            Here's the document to analyze:
            """ + text

        system_prompt = "You are a research paper analysis assistant. Always respond with valid JSON."
        
        # Make request to Ollama API
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False
        }
        
        logger.debug(f"Sending request to Ollama API at {OLLAMA_BASE_URL}/api/generate")
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", 
                                json=payload, 
                                headers=headers)
        
        if response.status_code != 200:
            raise ConnectionError(f"Failed to connect to Ollama: {response.status_code} - {response.text}")
        
        # Parse the response
        try:
            result = response.json()
            # Extract the content from the response
            content = result.get("response", "")
            
            # Try to extract JSON from the content
            # Look for JSON block between triple backticks or just try to parse the whole thing
            json_text = content
            if "```json" in content and "```" in content.split("```json", 1)[1]:
                json_text = content.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in content and "```" in content.split("```", 1)[1]:
                json_text = content.split("```", 1)[1].split("```", 1)[0]
            
            # Try to parse it as JSON
            analysis = json.loads(json_text)
            return analysis
        except json.JSONDecodeError:
            # If the model didn't return valid JSON, try to parse it in a more forgiving way
            logger.warning("Failed to parse JSON response, attempting fallback parsing")
            text_response = content

            # Basic fallback response
            return {
                "summary": text_response[:500],  # First 500 chars as summary
                "key_points": ["Analysis format error - please try again"],
                "methodology": "Unable to parse methodology",
                "findings": ["Analysis format error - please try again"],
                "citations": []
            }

    except ConnectionError as e:
        logger.error(f"Failed to connect to Ollama: {str(e)}")
        raise ConnectionError(f"Failed to connect to Ollama. Make sure Ollama is running at {OLLAMA_BASE_URL}")
    except Exception as e:
        logger.error(f"Failed to analyze document: {str(e)}")
        raise Exception(f"Failed to analyze document: {str(e)}")
