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
        """Optional Azure agent parsing (imported lazily)."""
        try:
            # Lazy imports to avoid hard dependency at import time
            from azure.identity.aio import DefaultAzureCredential  # type: ignore
            from semantic_kernel.agents import (  # type: ignore
                AzureAIAgent,
                AzureAIAgentSettings,
                AzureAIAgentThread,
            )
        except Exception as e:
            raise RuntimeError(f"Azure dependencies unavailable: {e}")

        settings = self.settings
        deployment = model_override or settings.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME
        if not (settings.AZURE_AI_AGENT_ENDPOINT and deployment):
            raise RuntimeError("Azure endpoint or deployment not configured")

        # Build prompt
        prompt = self._build_parsing_prompt(page_text, custom_requirements)

        # Initialize agent client
        credential = DefaultAzureCredential()
        agent = AzureAIAgent(
            AzureAIAgentSettings(
                endpoint=settings.AZURE_AI_AGENT_ENDPOINT,
                model=deployment,
                grounding_connection=settings.bing_connection_name,
            ),
            credentials=credential,
        )
        thread: Any | None = None
        try:
            thread = await agent.create_thread()
            await thread.add_message("user", prompt)
            response_messages = await agent.get_response(thread)

            # Extract text content from response
            response_text = ""
            if response_messages:
                for msg in response_messages:
                    content = getattr(msg, "content", None)
                    if content:
                        response_text += str(content)
                    else:
                        items = getattr(msg, "items", None)
                        if items:
                            for it in items:
                                t = getattr(it, "text", None)
                                if t:
                                    response_text += t
                        else:
                            response_text += str(msg)
            if not response_text:
                response_text = str(response_messages)

            # Parse JSON text from agent
            parsed = self._parse_agent_response(response_text, custom_requirements)
            return parsed
        finally:
            try:
                if thread:
                    await thread.delete()
            except Exception:
                pass
            try:
                await agent.delete()
            except Exception:
                pass

    def _build_parsing_prompt(self, page_text: str, custom_requirements: list[str] | None = None) -> str:
        max_text_length = 15000
        if len(page_text) > max_text_length:
            page_text = page_text[:max_text_length] + "\n...[TEXT TRUNCATED]"
        return (
            "Analyze the following UCL programme webpage content and extract admission requirements into agent-specific checklists.\n\n"
            f"Programme Webpage Content:\n{page_text}\n\n"
            f"Custom Requirements to Include: {custom_requirements or []}\n\n"
            "IMPORTANT: Return ONLY a valid JSON object in this exact format. Do not include any text before or after the JSON. Do not use code fences.\n\n"
            "Required JSON structure:\n{\n  \"checklists\": {\n    \"english_agent\": [\"requirement 1\"],\n    \"degree_agent\": [\"requirement 1\"],\n    \"experience_agent\": [],\n    \"ps_rl_agent\": [],\n    \"academic_agent\": []\n  },\n  \"english_level\": \"string or null\",\n  \"degree_requirement_class\": \"FIRST or UPPER_SECOND or LOWER_SECOND or null\"\n}\n"
        )

    def _parse_agent_response(self, response_text: str, custom_requirements: list[str] | None = None) -> dict[str, Any]:
        cleaned = self._clean_json_response(response_text)
        try:
            parsed = json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Agent JSON parse failed, falling back. Error: {e}")
            return self._get_fallback_rules(custom_requirements)
        return self._validate_and_structure_rules(parsed, custom_requirements)

    def _clean_json_response(self, response: str) -> str:
        # Remove markdown code fences and trim to JSON object bounds
        cleaned = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        if not cleaned.strip().startswith("{"):
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                cleaned = cleaned[start : end + 1]
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

