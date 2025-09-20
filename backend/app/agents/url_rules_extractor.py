"""URL-based rules extraction.

This module was repaired to fix prior syntax issues and to avoid
import-time failures when Azure-related libraries are unavailable.

Behavior:
- If Azure AI Agent settings are present, it attempts agent parsing.
- Otherwise, it uses a heuristic parser to extract useful data.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.services.url_extractor import extract_full_page_text, extract_programme_title_from_text
from app.config import get_settings

logger = logging.getLogger(__name__)


class URLRulesExtractor:
    """Extract admission rules from URL with optional Azure agent support."""

    def __init__(self):
        self.settings = get_settings()

    async def extract_rules_from_url(
        self,
        url: str,
        custom_requirements: list[str] | None = None,
        model_override: Optional[str] = None,
    ) -> dict[str, Any]:
        try:
            logger.info(f"Extracting text from URL: {url}")
            page_data = await extract_full_page_text(url)
            if page_data.get("status") != "success":
                logger.error(f"Failed to fetch URL text: {page_data}")
                return self._get_fallback_rules(custom_requirements)

            page_text: str = page_data.get("text") or ""
            if len(page_text) < 100:
                logger.warning(f"Extracted text too short: {len(page_text)} chars")
                return self._get_fallback_rules(custom_requirements)

            # Prefer Azure agent when endpoint + deployment are configured
            use_azure = bool(
                self.settings.AZURE_AI_AGENT_ENDPOINT and self.settings.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME
            )
            if use_azure:
                try:
                    rules = await self._parse_rules_with_azure_agent(page_text, custom_requirements, model_override)
                except Exception as agent_err:
                    logger.warning(f"Azure agent parsing failed, falling back to heuristics: {agent_err}")
                    rules = self._parse_rules_heuristic(page_text, custom_requirements)
            else:
                rules = self._parse_rules_heuristic(page_text, custom_requirements)

            if "programme_title" not in rules:
                rules["programme_title"] = extract_programme_title_from_text(page_text, url)
            rules["rule_set_url"] = url
            rules["text_length"] = len(page_text)
            return rules
        except Exception as e:
            logger.exception(f"Error extracting rules from URL {url}: {e}")
            return self._get_fallback_rules(custom_requirements)

    async def _parse_rules_with_azure_agent(
        self,
        page_text: str,
        custom_requirements: list[str] | None = None,
        model_override: Optional[str] = None,
    ) -> dict[str, Any]:
        """Optional Azure agent parsing using proper Azure AI client."""
        try:
            # Use the azure_client helper instead of direct agent management
            from app.agents.azure_client import run_single_turn
        except Exception as e:
            raise RuntimeError(f"Azure client unavailable: {e}")

        settings = self.settings
        deployment = model_override or settings.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME
        if not (settings.AZURE_AI_AGENT_ENDPOINT and deployment):
            raise RuntimeError("Azure endpoint or deployment not configured")

        # Build prompt
        prompt = self._build_parsing_prompt(page_text, custom_requirements)

        # Retry logic for JSON parsing
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Use single-turn conversation with Azure AI agent
                response_text = await run_single_turn(
                    name="URL-Rules-Extractor",
                    instructions="You are a JSON extraction specialist. You must return ONLY valid JSON with no additional text, explanations, or formatting. Follow the user's format requirements exactly.",
                    message=prompt,
                    with_bing_grounding=False,  # Disable for o3-mini compatibility
                    model=deployment,
                )

                # Parse JSON text from agent
                parsed = self._parse_agent_response(response_text, custom_requirements)
                logger.info(f"Successfully parsed JSON on attempt {attempt + 1}")
                return parsed
                
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON parsing failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    # Modify prompt for retry to be more explicit
                    prompt = self._build_retry_prompt(page_text, custom_requirements, response_text if 'response_text' in locals() else None)
                    continue
            except Exception as e:
                logger.error(f"Azure agent parsing failed on attempt {attempt + 1}: {e}")
                raise e
        
        logger.error(f"Failed to get valid JSON after {max_retries} attempts, last error: {last_error}")
        raise RuntimeError(f"Failed to parse JSON after {max_retries} attempts: {last_error}")

    def _build_parsing_prompt(self, page_text: str, custom_requirements: list[str] | None = None) -> str:
        return (
            "You are a JSON extraction specialist. Your task is to analyze UCL programme webpage content and extract admission requirements "
            "into appropriate evaluation agent categories.\n\n"
            f"Programme Webpage Content:\n{page_text}\n\n"
            f"Custom Requirements to Include: {custom_requirements or []}\n\n"
            "AGENT CATEGORIES:\n"
            "- english_agent: English language requirements (IELTS, TOEFL, language proficiency, exemptions)\n"
            "- degree_agent: Academic degree requirements (GPA, classification, subject prerequisites, academic background)\n"
            "- experience_agent: Work experience, internships, professional projects, industry experience\n"
            "- ps_rl_agent: Personal statement, reference letters, motivation letters, recommendation requirements\n"
            "- academic_agent: Research publications, academic achievements, scholarly work\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- You MUST return ONLY valid JSON, nothing else\n"
            "- NO explanatory text before or after the JSON\n"
            "- NO markdown code fences or backticks\n"
            "- NO comments or additional formatting\n"
            "- The response must start with { and end with }\n"
            "- Assign each requirement to the MOST appropriate single category\n"
            "- If a requirement spans multiple categories, choose the primary/dominant one\n\n"
            "Required JSON structure (return exactly this format):\n"
            "{\n"
            '  "checklists": {\n'
            '    "english_agent": ["requirement 1", "requirement 2"],\n'
            '    "degree_agent": ["requirement 1", "requirement 2"],\n'
            '    "experience_agent": ["requirement if any"],\n'
            '    "ps_rl_agent": ["requirement if any"],\n'
            '    "academic_agent": ["requirement if any"]\n'
            '  },\n'
            '  "english_level": "level1/level2/level3/level4/level5 or null",\n'
            '  "degree_requirement_class": "FIRST/UPPER_SECOND/LOWER_SECOND or null"\n'
            "}\n\n"
            "START YOUR RESPONSE WITH THE JSON OBJECT NOW:"
        )
    
    def _build_retry_prompt(self, page_text: str, custom_requirements: list[str] | None = None, failed_response: str | None = None) -> str:
        retry_instruction = ""
        if failed_response:
            retry_instruction = f"\n\nPREVIOUS FAILED RESPONSE:\n{failed_response[:200]}...\n\nThe above response was invalid JSON. Please correct this and return ONLY valid JSON.\n\n"
        
        return (
            "RETRY: You previously failed to return valid JSON. This is your second chance.\n\n"
            "You are a JSON extraction specialist. Your ONLY job is to return valid JSON.\n\n"
            f"Programme Webpage Content:\n{page_text}\n\n"
            f"Custom Requirements to Include: {custom_requirements or []}\n\n"
            f"{retry_instruction}"
            "MANDATORY REQUIREMENTS:\n"
            "1. Return ONLY JSON - no text before or after\n"
            "2. No markdown, no backticks, no code fences\n"
            "3. Start with { and end with }\n"
            "4. Use this exact structure:\n\n"
            "{\n"
            '  "checklists": {\n'
            '    "english_agent": [],\n'
            '    "degree_agent": [],\n'
            '    "experience_agent": [],\n'
            '    "ps_rl_agent": [],\n'
            '    "academic_agent": []\n'
            '  },\n'
            '  "english_level": null,\n'
            '  "degree_requirement_class": null\n'
            "}\n\n"
            "RESPOND WITH JSON NOW (no other text):"
        )

    def _parse_agent_response(self, response_text: str, custom_requirements: list[str] | None = None) -> dict[str, Any]:
        cleaned = self._clean_json_response(response_text)
        logger.debug(f"Attempting to parse JSON: {cleaned[:200]}...")
        
        try:
            parsed = json.loads(cleaned)
            logger.info("Successfully parsed JSON response")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed. Raw response: {response_text[:500]}...")
            logger.error(f"Cleaned response: {cleaned[:500]}...")
            logger.error(f"JSON error: {e}")
            raise e  # Re-raise to trigger retry logic
        except Exception as e:
            logger.warning(f"Agent JSON parse failed, falling back. Error: {e}")
            return self._get_fallback_rules(custom_requirements)
        return self._validate_and_structure_rules(parsed, custom_requirements)

    def _clean_json_response(self, response: str) -> str:
        # Remove markdown code fences and trim to JSON object bounds
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        
        # Remove any leading/trailing explanatory text
        cleaned = cleaned.strip()
        
        # Find JSON object boundaries more aggressively
        if not cleaned.startswith("{"):
            start = cleaned.find("{")
            if start == -1:
                logger.warning(f"No JSON object found in response: {cleaned[:200]}...")
                return "{}"
            cleaned = cleaned[start:]
        
        if not cleaned.endswith("}"):
            end = cleaned.rfind("}")
            if end == -1:
                logger.warning(f"No closing brace found in response: {cleaned[:200]}...")
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

    def _parse_rules_heuristic(self, page_text: str, custom_requirements: list[str] | None = None) -> dict[str, Any]:
        text_lower = page_text.lower()

        # English level heuristics (UCL pages often show "Level X")
        english_level_match = re.search(r"english language (?:level|requirements)[:\s]*level\s*(\d)", text_lower)
        english_level = None
        if english_level_match:
            english_level = f"level{english_level_match.group(1)}"

        # Degree class heuristics
        degree_class = None
        if re.search(r"first[-\s]class", text_lower):
            degree_class = "FIRST"
        if re.search(r"upper\s*second[-\s]class|2:?1|2-1", text_lower):
            degree_class = degree_class or "UPPER_SECOND"
        if re.search(r"lower\s*second[-\s]class|2:?2|2-2", text_lower):
            degree_class = "LOWER_SECOND"

        # Build checklists with simple phrases if present
        def present(phrase: str) -> bool:
            return phrase.lower() in text_lower

        english_items: list[str] = []
        if english_level:
            english_items.append(f"Meet UCL English language {english_level} requirements")
        if present("ielts"):
            english_items.append("IELTS test scores as required")
        if present("toefl"):
            english_items.append("TOEFL test scores as required")

        degree_items: list[str] = []
        if degree_class == "FIRST":
            degree_items.append("First-class UK Bachelor's degree or equivalent")
        elif degree_class == "UPPER_SECOND":
            degree_items.append("Upper second-class (2:1) UK Bachelor's degree or equivalent")
        elif degree_class == "LOWER_SECOND":
            degree_items.append("Lower second-class (2:2) UK Bachelor's degree or equivalent")

        # Common requirements on UCL programme pages
        ps_items: list[str] = []
        if present("personal statement"):
            ps_items.append("Personal statement required")
        if present("reference"):
            ps_items.append("Reference letter(s) required")
        if present("interview"):
            ps_items.append("Interview may be required")

        experience_items: list[str] = []
        if present("portfolio"):
            experience_items.append("Portfolio may be required")
        if present("work experience"):
            experience_items.append("Relevant work experience considered")

        academic_items: list[str] = []
        if present("research"):
            academic_items.append("Research experience considered")

        if custom_requirements:
            degree_items.extend(custom_requirements)

        return {
            "checklists": {
                "english_agent": english_items,
                "degree_agent": degree_items,
                "experience_agent": experience_items,
                "ps_rl_agent": ps_items,
                "academic_agent": academic_items,
            },
            "english_level": english_level,
            "degree_requirement_class": degree_class,
        }

    def _validate_and_structure_rules(self, parsed: dict, custom_requirements: list[str] | None = None) -> dict[str, Any]:
        checklists = parsed.get("checklists", {}) or {}
        required_agents = [
            "english_agent",
            "degree_agent",
            "experience_agent",
            "ps_rl_agent",
            "academic_agent",
        ]
        for agent in required_agents:
            lst = checklists.get(agent)
            if not isinstance(lst, list):
                checklists[agent] = []
        if custom_requirements:
            checklists.setdefault("degree_agent", []).extend(custom_requirements)
        return {
            "checklists": checklists,
            "english_level": parsed.get("english_level"),
            "degree_requirement_class": parsed.get("degree_requirement_class"),
        }

    def _get_fallback_rules(self, custom_requirements: list[str] | None = None) -> dict[str, Any]:
        return {
            "checklists": {
                "english_agent": [],
                "degree_agent": list(custom_requirements or []),
                "experience_agent": [],
                "ps_rl_agent": [],
                "academic_agent": [],
            },
            "english_level": None,
            "degree_requirement_class": None,
        }


# Convenience function for direct usage
async def extract_rules_from_url(
    url: str,
    custom_requirements: list[str] | None = None,
    model_override: Optional[str] = None,
) -> dict[str, Any]:
    extractor = URLRulesExtractor()
    return await extractor.extract_rules_from_url(url, custom_requirements, model_override)

