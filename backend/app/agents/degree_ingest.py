from __future__ import annotations

import json
from typing import Any

from app.agents.azure_client import run_single_turn_blocking


INGEST_TEXT_INSTRUCTIONS = (
    "You are parsing plain text from UCL's Graduate Equivalent International Qualifications page. "
    "Do not browse the web. Only use the provided text. "
    "Extract a structured summary per country of the equivalence to UK classes: FIRST, UPPER_SECOND (2:1), LOWER_SECOND (2:2). "
    "Return strict JSON with keys: countries (array) and special_institutions (array). "
    "countries items: {country_name, country_code_iso3, classes}. classes has up to three keys (FIRST, UPPER_SECOND, LOWER_SECOND). Each contains a 'requirement' object with the best-effort interpretation (e.g., percentage >= X, CGPA >= Y on scale Z, narrative text if numeric unknown) and 'source_url' set to the provided base URL. "
    "special_institutions items only when the text clearly specifies institution-dependent thresholds (e.g., China, India). Use ISO 3166-1 alpha-3 codes for country_code_iso3. If country code cannot be determined, omit the item. "
    "If numeric data is not present in the text for a country, include a requirement with a 'text' field summarizing what is stated. Do not invent numbers."
)


def ingest_equivalency_from_text(page_text: str, base_url: str) -> dict[str, Any]:
    payload = {
        "base_url": base_url,
        "text": page_text,
    }
    result = run_single_turn_blocking(
        name="DegreeIngestorText",
        instructions=INGEST_TEXT_INSTRUCTIONS,
        message=json.dumps(payload),
        with_bing_grounding=False,
    )
    try:
        data = json.loads(result)
        if isinstance(data, dict):
            data.setdefault("countries", [])
            data.setdefault("special_institutions", [])
            return data
    except Exception:
        pass
    return {"countries": [], "special_institutions": []}
