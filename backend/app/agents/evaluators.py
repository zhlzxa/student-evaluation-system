from __future__ import annotations

from typing import Any, Optional

from app.agents.azure_client import run_single_turn
from app.agents.plugins.english_score import EnglishScorePlugin
from app.agents.plugins.degree_score import DegreeScorePlugin
from app.agents.plugins.degree_policy import DegreePolicyPlugin
from app.agents.plugins.doc_store import DocStorePlugin
from app.agents.plugins.china_india_eligibility import ChinaIndiaEligibilityPlugin
from app.agents.json_utils import parse_agent_json


async def _ask_agent(name: str, instructions: str, content: str, with_bing: bool = False, plugins: Optional[list[object]] = None) -> str:
    return await run_single_turn(
        name=name,
        instructions=instructions,
        message=content,
        with_bing_grounding=with_bing,
        plugins=plugins,
    )


async def english_agent(applicant_id: int, run_id: int, level_hint: str | None = None, policy: dict | None = None) -> dict[str, Any]:
    instructions = (
        "You evaluate English language requirements for UCL admission using document access tools. Follow these steps:\n"
        "\n"
        "STEP 1 - Survey Documents:\n"
        "- Call list_documents() to see available materials\n"
        "- Prioritize: Personal Statement, CV, Transcripts, Test Certificates\n"
        "- Use search_documents() to find 'IELTS', 'TOEFL', 'nationality', 'citizenship'\n"
        "\n"
        "STEP 2 - Check Exemptions:\n"
        "- Look for nationality mentions (British, American, Canadian, etc.)\n"
        "- Look for degree countries (University of Cambridge, Harvard, etc.)\n"
        "- If nationality OR degree country is in policy exemption lists, set exemption=true\n"
        "\n"
        "STEP 3 - Extract Test Scores:\n"
        "- Read documents likely to contain test scores (certificates, CV, PS)\n"
        "- Extract ALL numeric scores: overall, reading, writing, speaking, listening\n"
        "- Common formats: 'Overall: 7.5', 'Band Score: 7.5', 'Total: 100'\n"
        "- Set test_type (e.g., 'IELTS') and test_overall (e.g., 7.5)\n"
        "\n"
        "STEP 4 - Evaluate Against Requirements:\n"
        "- Use provided level hint to find policy.levels[level].tests requirements\n"
        "- Call meets_thresholds() function to compare scores vs. requirements\n"
        "- For IELTS, call score_ielts_level2() to get 0-10 score\n"
        "\n"
        "Return JSON: {exemption:boolean, test_type:string|null, test_overall:number|null, level:string|null, score:number|null, evidence:string[]}\n"
        "Use minimal tokens - be strategic about which documents to read fully."
    )
    import json
    policy_json = json.dumps(policy or {})
    prompt = (
        f"Level hint: {level_hint or ''}\n"
        f"Policy JSON:\n{policy_json}\n"
        "IMPORTANT: Use meets_thresholds(...) for deterministic numeric comparisons.\n"
        "IMPORTANT: Use document access functions to find English test information strategically."
    )
    ans = await _ask_agent("EnglishAgent", instructions, prompt, plugins=[EnglishScorePlugin(), DocStorePlugin(applicant_id, run_id)])
    result = parse_agent_json(ans)
    if result is None:
        return {"exemption": False, "test_type": None, "test_overall": None, "level": level_hint, "score": None, "evidence": []}
    return result


async def degree_agent(
    applicant_id: int,
    run_id: int,
    target_class: str = "UPPER_SECOND",
    checklists: list[str] | None = None,
    special_context: str | None = None,
    detected_country_iso3: str | None = None,
) -> dict[str, Any]:
    instructions = (
        "You verify degree equivalency and academic background fit for UCL using document access and specialized policy tools. "
        "PRIORITY: For China/India applicants, use the new specialized evaluation functions first. "
        "\n"
        "Steps: "
        "(1) Survey available documents with list_documents(); "
        "(2) Read transcripts, degree certificates, and CV strategically; "
        "(3) Infer the applicant's degree-awarding country and institution; "
        "(4) CRITICAL - For China/India applicants: "
        "   - If China (CHN): Call ChinaIndiaEligibilityPlugin-evaluate_china_applicant(institution_name, major_field, weighted_average_mark, target_uk_class) "
        "   - If India (IND): Call ChinaIndiaEligibilityPlugin-evaluate_india_applicant(institution_name, mark_value, mark_scale, target_uk_class) "
        "   - These functions handle UCL's official requirements with precise thresholds and institution classifications "
        "   - Use ChinaIndiaEligibilityPlugin-is_country_supported(country) to check if specialized evaluation is available "
        "(5) For other countries: Call DegreePolicyPlugin-get_policy_for_country(country, target_class) to retrieve general policy requirements; "
        "(6) Extract degree result (percent/CGPA) from transcripts; "
        "(7) Verify subject/field relevance against programme requirements from checklist; "
        "(8) Check prerequisite courses and academic background fit; "
        "(9) If using general policy with percent threshold, call DegreeScorePlugin-meets_percent_threshold(observed_percent, min_required_percent); "
        "(10) Compute score: use specialized plugin results OR call DegreeScorePlugin-percent_to_score(observed_percent) or estimate 0-10 from policy; "
        "(11) MANDATORY: Search for and include the institution's current QS World University Ranking via web search. "
        "IMPORTANT: The China/India plugins provide authoritative eligibility determinations - trust their results over general rules. "
        "Use minimal tokens - focus on transcripts and certificates for degree info. "
        "Return strict JSON: {country:string|null, institution:string|null, meets_requirement:boolean|null, qs_rank:int|null, score:number|null, subject_fit:boolean|null, missing_prerequisites:string[], evidence:string[], policy_source:string|null}."
    )
    prompt = "\n".join([
        f"Target UK class: {target_class}",
        f"Checklist: {checklists or []}",
        (f"Special Context (use only if relevant to country {detected_country_iso3}):\n{(special_context or '')[:6000]}" if special_context else ""),
        "Use document access functions to find degree and academic information strategically.",
    ])
    ans = await _ask_agent(
        "DegreeAgent",
        instructions,
        prompt,
        with_bing=True,
        plugins=[DegreeScorePlugin(), DegreePolicyPlugin(), ChinaIndiaEligibilityPlugin(), DocStorePlugin(applicant_id, run_id)],
    )
    result = parse_agent_json(ans)
    if result is None:
        return {"country": None, "institution": None, "meets_requirement": None, "qs_rank": None, "score": None, "subject_fit": None, "missing_prerequisites": [], "evidence": [], "policy_source": None}
    return result



async def experience_agent(applicant_id: int, run_id: int, checklist: list[str] | None = None) -> dict[str, Any]:
    instructions = (
        "You assess internships/work/projects vs requirements using document access tools. "
        "First call list_documents() then prioritize: CV, Personal Statement, Experience Letters, Portfolio. "
        "Use Bing to gauge company reputation when found. "
        "Score (0-10): top companies >2 months -> 10; Tencent/Huawei -> 8; general IT -> 4; other work -> 2; school projects based on relevance. "
        "Use minimal tokens - focus on CV and experience-related documents. "
        "Return JSON: score (0-10), highlights (array), evidence (array)."
    )
    prompt = f"Checklist: {checklist or []}\nUse document access functions to find work experience and project information."
    ans = await _ask_agent("ExperienceAgent", instructions, prompt, with_bing=True, plugins=[DocStorePlugin(applicant_id, run_id)])
    result = parse_agent_json(ans)
    if result is None:
        return {"score": None, "highlights": [], "evidence": []}
    return result


async def ps_rl_agent(applicant_id: int, run_id: int, checklist: list[str] | None = None) -> dict[str, Any]:
    instructions = (
        "Evaluate personal statement motivation and detail; verify alignment to checklist using document access tools. "
        "First call list_documents() then prioritize: Personal Statement, Reference Letters, Motivation Letter. "
        "For reference letters, validate recommender standing with Bing. "
        "Use minimal tokens - focus on PS and reference letter documents specifically. "
        "\n"
        "MANDATORY: Return ONLY valid JSON format, no markdown or additional text: "
        "{\"score\": <number 0-10>, \"strengths\": [\"strength1\", \"strength2\"], \"weaknesses\": [\"weakness1\"], \"evidence\": [\"evidence1\"]}"
    )
    prompt = f"Checklist: {checklist or []}\nUse document access functions to find personal statement and reference letter content."
    ans = await _ask_agent("PsRlAgent", instructions, prompt, with_bing=False, plugins=[DocStorePlugin(applicant_id, run_id)])
    result = parse_agent_json(ans)
    if result is None:
        return {"score": None, "strengths": [], "weaknesses": [], "evidence": []}
    return result


async def academic_agent(applicant_id: int, run_id: int) -> dict[str, Any]:
    instructions = (
        "Evaluate publications using document access tools: verify authenticity via Bing, venue tier (conference/journal), and coauthorship with faculty. "
        "First call list_documents() then prioritize: CV, Publications List, Research Statement, Portfolio. "
        "Use search_documents() to find 'publication', 'paper', 'conference', 'journal'. "
        "Score: top-tier 10; general conference 5; only unpublished 0. "
        "Use minimal tokens - focus on academic documents and publications. "
        "Return JSON: score (0-10), papers (array of {title, venue, tier}), evidence (array)."
    )
    prompt = "Use document access functions to find academic publications and research work."
    ans = await _ask_agent("AcademicAgent", instructions, prompt, with_bing=True, plugins=[DocStorePlugin(applicant_id, run_id)])
    result = parse_agent_json(ans)
    if result is None:
        return {"score": None, "papers": [], "evidence": []}
    return result


async def compare_agent(app_a: dict[str, Any], app_b: dict[str, Any]) -> dict[str, Any]:
    """Pairwise comparison for Bradley–Terry adjustment.

    Returns JSON: {winner: "A"|"B"|"tie", reason: string}
    """
    instructions = (
        "You compare two applicants using structured scores and evidence from multiple agents (english, degree, academic, experience, ps_rl). "
        "Choose which applicant is better overall for UCL admissions based on the provided weights (english 10%, degree 50%, academic 15%, experience 15%, ps_rl 10%). "
        "Return strict JSON: {winner: 'A'|'B'|'tie', reason: string}."
    )
    import json
    content = json.dumps({"A": app_a, "B": app_b})
    ans = await _ask_agent("PairwiseAgent", instructions, content, with_bing=True)
    result = parse_agent_json(ans)
    if result is not None and result.get("winner") in {"A", "B", "tie"}:
        return result
    return {"winner": "tie", "reason": "undecided"}
