from __future__ import annotations

from typing import Any, Tuple
import logging
import re

from app.agents.azure_client import run_single_turn
from app.config import get_settings


INSTRUCTIONS = (
    "You analyze a UCL graduate programme page and extract factual admission requirements into agent-specific checklists. "
    "Extract ONLY what is explicitly stated on the page - do not fabricate implementation details. "
    "\n"
    "Agent purposes:\n"
    "- english_agent: Extract English language requirements (tests, scores, exemptions mentioned)\n"
    "- degree_agent: Extract degree classification requirements, subject requirements, academic prerequisites\n" 
    "- experience_agent: Extract work experience, internship, or project requirements\n"
    "- ps_rl_agent: Extract personal statement and reference letter requirements\n"
    "- academic_agent: Extract research publication, academic achievement requirements\n"
    "\n"
    "For english_level: Extract ONLY the specific Level number (1-5) if explicitly mentioned on the page.\n"
    "For degree_requirement_class: Extract ONLY the UK classification mentioned (FIRST, UPPER_SECOND, LOWER_SECOND).\n"
    "\n"
    "Output strict JSON: {'checklists': {'english_agent': string[], 'degree_agent': string[], 'experience_agent': string[], 'ps_rl_agent': string[], 'academic_agent': string[]}, 'english_level': string|null, 'degree_requirement_class': string|null}.\n"
    "Use only information explicitly present in the programme text."
)


async def generate_checklists(page_text: str, custom_requirements: list[str] | None = None) -> dict:
    settings = get_settings()

    prompt = (
        "Derive agent checklists, english_level, and degree_requirement_class from the programme text below.\n"
        "Return STRICT JSON that can be parsed by json.loads in Python.\n"
        "Rules: use DOUBLE QUOTES for all keys and strings; output ONLY a JSON object (no prose, no code fences).\n"
        "Schema (keys must exist): {\"checklists\": {\"english_agent\": string[], \"degree_agent\": string[], \"experience_agent\": string[], \"ps_rl_agent\": string[], \"academic_agent\": string[]}, \"english_level\": string|null, \"degree_requirement_class\": string|null}.\n\n"
        f"Programme Text:\n{page_text}\n\n"
        f"Custom Requirements: {custom_requirements or []}\n"
    )
    try:
        result = await run_single_turn(name="RuleParser", instructions=INSTRUCTIONS, message=prompt)
    except Exception:
        # Agent not available or failed: fallback
        logging.exception("RuleParser agent invocation failed")
        base = {
            "checklists": {
                "english_agent": [],
                "degree_agent": [],
                "experience_agent": [],
                "ps_rl_agent": [],
                "academic_agent": [],
            },
            "english_level": None,
            "degree_requirement_class": None,
        }
        if custom_requirements:
            base["checklists"]["custom"] = custom_requirements
            base["checklists"]["degree_agent"] += custom_requirements
        return base
    logging.debug("RuleParser raw output (first 500 chars): %s", str(result)[:500])
    # Return raw JSON if well-formed; otherwise wrap into a dict
    try:
        import json

        # Try to unwrap common wrappers and coerce into valid JSON
        candidate = str(result).strip()
        # strip code fences
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
        # extract first JSON object if text is wrapped
        if not candidate.startswith("{"):
            i = candidate.find("{")
            j = candidate.rfind("}")
            if i != -1 and j != -1 and j > i:
                candidate = candidate[i : j + 1]
        # normalize fancy quotes
        candidate = candidate.replace("“", '"').replace("”", '"').replace("’", "'")

        try:
            parsed = json.loads(candidate)
        except Exception:
            # naive single-quote to double-quote replacement
            candidate2 = re.sub(r"(?<!\\)'", '"', candidate)
            parsed = json.loads(candidate2)
        if isinstance(parsed, dict):
            # Ensure structure exists
            parsed.setdefault("checklists", {
                "english_agent": [],
                "degree_agent": [],
                "experience_agent": [],
                "ps_rl_agent": [],
                "academic_agent": [],
            })
            if custom_requirements:
                # push customs into degree/background by default and also expose a custom bucket
                cj = parsed["checklists"]
                cj.setdefault("degree_agent", [])
                cj.setdefault("custom", [])
                cj["degree_agent"] += custom_requirements
                cj["custom"] += custom_requirements
            return parsed
    except Exception:
        logging.exception("Failed to parse RuleParser output as JSON")
        pass

    # Fallback structure if parsing fails
    base = {
        "checklists": {
            "english_agent": [],
            "degree_agent": [],
            "background_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": [],
        },
        "english_level": None,
        "degree_requirement_class": None,
    }
    if custom_requirements:
        base["checklists"]["custom"] = custom_requirements
        base["checklists"]["degree_agent"] += custom_requirements
    return base


async def generate_checklists_debug(
    page_text: str, custom_requirements: list[str] | None = None
) -> Tuple[dict, str, str]:
    """Run the agent and also return raw output and candidate string used for parsing.

    Returns: (parsed_dict, raw_output, candidate_used)
    """
    settings = get_settings()
    # Always attempt to call the agent; rely on azure_client to resolve settings or raise

    prompt = (
        "Derive agent checklists, english_level, and degree_requirement_class from the programme text below.\n"
        "Return STRICT JSON that can be parsed by json.loads in Python.\n"
        "Rules: use DOUBLE QUOTES for all keys and strings; output ONLY a JSON object (no prose, no code fences).\n"
        "Schema (keys must exist): {\"checklists\": {\"english_agent\": string[], \"degree_agent\": string[], \"experience_agent\": string[], \"ps_rl_agent\": string[], \"academic_agent\": string[]}, \"english_level\": string|null, \"degree_requirement_class\": string|null}.\n\n"
        f"Programme Text:\n{page_text}\n\n"
        f"Custom Requirements: {custom_requirements or []}\n"
    )
    try:
        raw = await run_single_turn(name="RuleParser", instructions=INSTRUCTIONS, message=prompt)
    except Exception:
        logging.exception("RuleParser agent invocation failed (debug)")
        base = {
            "checklists": {
                "english_agent": [],
                "degree_agent": [],
                "experience_agent": [],
                "ps_rl_agent": [],
                "academic_agent": [],
            },
            "english_level": None,
            "degree_requirement_class": None,
        }
        if custom_requirements:
            base["checklists"]["custom"] = custom_requirements
            base["checklists"]["degree_agent"] += custom_requirements
        return base, "", ""
    logging.debug("RuleParser raw output (first 500 chars): %s", str(raw)[:500])

    # Build candidate string similar to generate_checklists
    candidate = str(raw).strip()
    candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
    candidate = re.sub(r"\s*```$", "", candidate)
    if not candidate.startswith("{"):
        i = candidate.find("{")
        j = candidate.rfind("}")
        if i != -1 and j != -1 and j > i:
            candidate = candidate[i : j + 1]
    # Normalize curly quotes via Unicode escapes to keep source ASCII-only
    candidate = re.sub("\u201C|\u201D", '"', candidate)
    candidate = re.sub("\u2019", "'", candidate)

    try:
        import json

        try:
            parsed = json.loads(candidate)
        except Exception:
            candidate2 = re.sub(r"(?<!\\)'", '"', candidate)
            parsed = json.loads(candidate2)

        if isinstance(parsed, dict):
            parsed.setdefault("checklists", {
                "english_agent": [],
                "degree_agent": [],
                "experience_agent": [],
                "ps_rl_agent": [],
                "academic_agent": [],
            })
            if custom_requirements:
                cj = parsed["checklists"]
                cj.setdefault("degree_agent", [])
                cj.setdefault("custom", [])
                cj["degree_agent"] += custom_requirements
                cj["custom"] += custom_requirements
            return parsed, str(raw), candidate
    except Exception:
        logging.exception("Failed to parse RuleParser output as JSON (debug)")

    # Fallback
    base = {
        "checklists": {
            "english_agent": [],
            "degree_agent": [],
            "background_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": [],
        },
        "english_level": None,
        "degree_requirement_class": None,
    }
    if custom_requirements:
        base["checklists"]["custom"] = custom_requirements
        base["checklists"]["degree_agent"] += custom_requirements
    return base, str(raw), candidate

