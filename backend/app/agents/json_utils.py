from __future__ import annotations

import json
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_agent_json(response: str) -> dict[str, Any] | None:
    """Parse JSON response from agent with robust cleaning and error handling.
    
    Args:
        response: Raw response string from agent
        
    Returns:
        Parsed JSON dict or None if parsing fails
    """
    if not response:
        return None
    
    # Log first 500 characters for debugging
    logger.debug(f"Parsing agent response (first 500 chars): {str(response)[:500]}")
    
    try:
        # Step 1: Clean the response
        cleaned = str(response).strip()
        
        # Remove code fences
        cleaned = re.sub(r'^```(?:json)?\\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'\\s*```$', '', cleaned, flags=re.MULTILINE)
        
        # Step 2: Extract JSON if not starting with {
        if not cleaned.startswith('{'):
            # Find the first { and matching }
            start_idx = cleaned.find('{')
            if start_idx == -1:
                logger.warning("No JSON object found in response")
                return None
            
            # Find the matching closing brace by counting braces
            brace_count = 0
            end_idx = -1
            
            for i in range(start_idx, len(cleaned)):
                if cleaned[i] == '{':
                    brace_count += 1
                elif cleaned[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx == -1:
                logger.warning("No matching closing brace found")
                return None
                
            cleaned = cleaned[start_idx:end_idx]
        
        # Step 3: Parse JSON
        return json.loads(cleaned)
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}. Response: {response[:200]}...")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}. Response: {response[:200]}...")
        return None