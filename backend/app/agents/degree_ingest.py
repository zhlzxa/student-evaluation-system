from __future__ import annotations

import json
from typing import Any

from app.agents.azure_client import run_single_turn_blocking


INGEST_TEXT_INSTRUCTIONS = (
    "You are parsing plain text from UCL's Graduate Equivalent International Qualifications page. "
    "Do not browse the web. Only use the provided text. "
    "Extract a structured summary per country of the equivalence to UK classes: FIRST, UPPER_SECOND (2:1), LOWER_SECOND (2:2). \n\n"
    "MANDATORY OUTPUT FORMAT: Return ONLY valid JSON with no additional text, explanations, or formatting.\n"
    "Do not use markdown code fences or backticks. Start with { and end with }.\n\n"
    "Return strict JSON with keys: countries (array) and special_institutions (array). "
    "countries items: {country_name, country_code_iso3, classes}. classes has up to three keys (FIRST, UPPER_SECOND, LOWER_SECOND). Each contains a 'requirement' object with the best-effort interpretation (e.g., percentage >= X, CGPA >= Y on scale Z, narrative text if numeric unknown) and 'source_url' set to the provided base URL. "
    "special_institutions items only when the text clearly specifies institution-dependent thresholds (e.g., China, India). Use ISO 3166-1 alpha-3 codes for country_code_iso3. If country code cannot be determined, omit the item. "
    "If numeric data is not present in the text for a country, include a requirement with a 'text' field summarizing what is stated. Do not invent numbers."
)


def _clean_json_response(response: str) -> str:
    """Clean and extract JSON from agent response."""
    import re
    
    # Remove markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
    
    # Find JSON object boundaries
    cleaned = cleaned.strip()
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        if start == -1:
            return "{}"
        cleaned = cleaned[start:]
    
    if not cleaned.endswith("}"):
        end = cleaned.rfind("}")
        if end == -1:
            return "{}"
        cleaned = cleaned[:end + 1]
    
    # Remove any text after the JSON object
    brace_count = 0
    json_end = -1
    for i, char in enumerate(cleaned):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_end = i
                break
    
    if json_end != -1 and json_end < len(cleaned) - 1:
        cleaned = cleaned[:json_end + 1]
    
    return cleaned

def ingest_equivalency_from_text(page_text: str, base_url: str) -> dict[str, Any]:
    payload = {
        "base_url": base_url,
        "text": page_text,
    }
    
    # First attempt
    result = run_single_turn_blocking(
        name="DegreeIngestorText",
        instructions=INGEST_TEXT_INSTRUCTIONS,
        message=json.dumps(payload),
        with_bing_grounding=False,
    )
    
    cleaned = _clean_json_response(result)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            data.setdefault("countries", [])
            data.setdefault("special_institutions", [])
            return data
    except json.JSONDecodeError:
        # Retry with more explicit instructions
        retry_instructions = INGEST_TEXT_INSTRUCTIONS + "\n\nCRITICAL RETRY: Previous response failed JSON parsing. Return ONLY valid JSON object starting with { and ending with }. No additional text."
        result2 = run_single_turn_blocking(
            name="DegreeIngestorTextRetry",
            instructions=retry_instructions,
            message=json.dumps(payload),
            with_bing_grounding=False,
        )
        
        cleaned2 = _clean_json_response(result2)
        try:
            data = json.loads(cleaned2)
            if isinstance(data, dict):
                data.setdefault("countries", [])
                data.setdefault("special_institutions", [])
                return data
        except Exception:
            pass
    except Exception:
        pass
    
    return {"countries": [], "special_institutions": []}
