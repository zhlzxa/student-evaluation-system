"""
Custom Requirements Classifier Agent

This agent intelligently classifies user-defined custom requirements
into appropriate agent categories before the concurrent evaluation phase.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging

from app.agents.azure_client import run_single_turn
from app.agents.json_utils import parse_agent_json
from app.services.logging_service import log_agent_event

logger = logging.getLogger(__name__)


CLASSIFIER_INSTRUCTIONS = (
    "You are a requirements classification specialist for university admissions. "
    "Your role is to analyze custom requirements provided by users and classify them "
    "into appropriate evaluation agent categories.\n"
    "\n"
    "AGENT CATEGORIES:\n"
    "- english_agent: English language requirements (IELTS, TOEFL, language proficiency, exemptions)\n"
    "- degree_agent: Academic degree requirements (GPA, classification, subject prerequisites, academic background)\n"
    "- experience_agent: Work experience, internships, professional projects, industry experience\n"
    "- ps_rl_agent: Personal statement, reference letters, motivation letters, recommendation requirements\n"
    "- academic_agent: Research publications, academic achievements, scholarly work\n"
    "\n"
    "CLASSIFICATION RULES:\n"
    "1. Assign each requirement to the MOST appropriate single category\n"
    "2. If a requirement spans multiple categories, choose the primary/dominant one\n"
    "3. Mark requirements as 'high_priority' if they are mandatory/critical\n"
    "4. Provide clear reasoning for each classification decision\n"
    "\n"
    "OUTPUT FORMAT: Return ONLY valid JSON with no additional text.\n"
    "Return JSON: {\n"
    "  \"classifications\": [\n"
    "    {\n"
    "      \"requirement\": \"original requirement text\",\n"
    "      \"agent\": \"target_agent_name\",\n"
    "      \"priority\": \"high|normal\",\n"
    "      \"reasoning\": \"explanation for classification\"\n"
    "    }\n"
    "  ],\n"
    "  \"summary\": {\n"
    "    \"total_requirements\": number,\n"
    "    \"english_agent\": number,\n"
    "    \"degree_agent\": number,\n"
    "    \"experience_agent\": number,\n"
    "    \"ps_rl_agent\": number,\n"
    "    \"academic_agent\": number\n"
    "  }\n"
    "}"
)


async def classify_custom_requirements(
    custom_requirements: List[str],
    run_id: int,
    model_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify custom requirements into appropriate agent categories.

    Args:
        custom_requirements: List of user-defined requirements
        run_id: Assessment run ID for logging
        model_override: Optional model override for the agent

    Returns:
        Dictionary containing classified requirements and distribution
    """
    if not custom_requirements:
        logger.info(f"No custom requirements to classify for run {run_id}")
        return {
            "classified_checklists": {},
            "classification_details": [],
            "total_classified": 0
        }

    log_agent_event(
        run_id=run_id,
        agent_name="custom_requirements_classifier",
        phase="start",
        message=f"Starting classification of {len(custom_requirements)} custom requirements"
    )

    try:
        # Prepare prompt for the classifier agent
        requirements_text = "\n".join([f"- {req}" for req in custom_requirements])

        prompt = (
            f"Please classify the following {len(custom_requirements)} custom requirements "
            f"into appropriate agent categories:\n\n"
            f"Custom Requirements:\n{requirements_text}\n\n"
            f"Analyze each requirement and determine which evaluation agent should handle it. "
            f"Consider the nature of each requirement and match it to the most suitable agent type. "
            f"Mark critical/mandatory requirements as high priority."
        )

        # Call the classifier agent
        raw_result = await run_single_turn(
            name="CustomRequirementsClassifier",
            instructions=CLASSIFIER_INSTRUCTIONS,
            message=prompt,
            model=model_override
        )

        # Parse the agent response
        result = parse_agent_json(str(raw_result))

        if not isinstance(result, dict) or "classifications" not in result:
            raise ValueError("Invalid classifier response format")

        # Transform result into checklist format
        classified_checklists = {
            "english_agent": [],
            "degree_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": []
        }

        classification_details = []

        for classification in result.get("classifications", []):
            requirement = classification.get("requirement", "")
            agent = classification.get("agent", "")
            priority = classification.get("priority", "normal")
            reasoning = classification.get("reasoning", "")

            if agent in classified_checklists:
                # Add user-defined marker for all custom requirements
                requirement_text = f"[USER DEFINED] {requirement}"

                classified_checklists[agent].append(requirement_text)

                classification_details.append({
                    "original_requirement": requirement,
                    "assigned_agent": agent,
                    "priority": priority,
                    "reasoning": reasoning,
                    "final_text": requirement_text
                })
            else:
                logger.warning(f"Unknown agent category: {agent} for requirement: {requirement}")

        # Log classification results
        summary = result.get("summary", {})
        log_message = f"Classification completed. Distribution: " + ", ".join([
            f"{agent}={summary.get(agent, 0)}"
            for agent in classified_checklists.keys()
        ])

        log_agent_event(
            run_id=run_id,
            agent_name="custom_requirements_classifier",
            phase="completed",
            message=log_message
        )

        logger.info(f"Successfully classified {len(custom_requirements)} requirements for run {run_id}")

        return {
            "classified_checklists": classified_checklists,
            "classification_details": classification_details,
            "total_classified": len(classification_details),
            "summary": summary
        }

    except Exception as e:
        error_msg = f"Failed to classify custom requirements: {str(e)}"
        logger.error(error_msg)

        log_agent_event(
            run_id=run_id,
            agent_name="custom_requirements_classifier",
            phase="error",
            message=error_msg
        )

        # Fallback: assign all to degree_agent (current behavior)
        fallback_checklists = {
            "english_agent": [],
            "degree_agent": [f"[USER DEFINED] {req}" for req in custom_requirements],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": []
        }

        return {
            "classified_checklists": fallback_checklists,
            "classification_details": [],
            "total_classified": 0,
            "fallback_used": True
        }


def merge_classified_requirements_with_checklists(
    original_checklists: Dict[str, List[str]],
    classified_checklists: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """
    Merge classified custom requirements with original rule-based checklists.
    Custom requirements are added at the beginning to indicate higher priority.

    Args:
        original_checklists: Checklists from rule parsing
        classified_checklists: Classified custom requirements

    Returns:
        Merged checklists with custom requirements prioritized
    """
    merged = {}

    # Ensure all agent types are present
    all_agents = {"english_agent", "degree_agent", "experience_agent", "ps_rl_agent", "academic_agent"}

    for agent in all_agents:
        # Start with custom requirements (higher priority)
        agent_checklist = classified_checklists.get(agent, []).copy()

        # Add original requirements after custom ones
        original_items = original_checklists.get(agent, [])
        agent_checklist.extend(original_items)

        merged[agent] = agent_checklist

    return merged