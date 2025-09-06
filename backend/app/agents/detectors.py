from __future__ import annotations

import json
from typing import Optional, Dict, Any

from app.agents.azure_client import run_single_turn_blocking


INSTRUCTIONS_DEGREE_COUNTRY = (
    "You are given applicant materials. Determine the degree-awarding country for the highest completed degree. "
    "Return strict JSON: {country_name: string|null, country_code_iso3: string|null}. "
    "Do not include prose or backticks."
)


def detect_degree_country(text: str) -> Dict[str, Optional[str]]:
    payload = {"text": text[:20000]}
    result = run_single_turn_blocking(
        name="DegreeCountryDetector",
        instructions=INSTRUCTIONS_DEGREE_COUNTRY,
        message=json.dumps(payload),
        with_bing_grounding=False,
    )
    try:
        data = json.loads(result)
        if isinstance(data, dict):
            return {
                "country_name": data.get("country_name"),
                "country_code_iso3": data.get("country_code_iso3"),
            }
    except Exception:
        pass
    return {"country_name": None, "country_code_iso3": None}

