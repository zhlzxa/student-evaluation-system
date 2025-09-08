from __future__ import annotations

from typing import Any, Optional

from app.agents.azure_client import run_single_turn
from app.agents.plugins.english_score import EnglishScorePlugin
from app.agents.plugins.english_exemption import EnglishExemptionPlugin
from app.agents.plugins.degree_score import DegreeScorePlugin
from app.agents.plugins.degree_policy import DegreePolicyPlugin
from app.agents.plugins.doc_store import DocStorePlugin
from app.agents.plugins.china_india_eligibility import ChinaIndiaEligibilityPlugin
from app.agents.json_utils import parse_agent_json
from app.agents.model_config import get_model_for_agent
from app.services.logging_service import log_agent_event


async def _ask_agent(
    name: str,
    instructions: str,
    content: str,
    with_bing: bool = False,
    plugins: Optional[list[object]] = None,
    agent_type: Optional[str] = None,
    model_override: Optional[str] = None,
    run_id: Optional[int] = None,
    applicant_id: Optional[int] = None,
) -> str:
    # Resolve model: per-call override > per-agent configured model
    model = model_override
    if model is None and agent_type:
        model = get_model_for_agent(agent_type)

    # Persist request log if context provided
    try:
        if run_id is not None and agent_type is not None:
            plugin_names = [type(p).__name__ for p in (plugins or [])]
            req_msg = (
                f"instructions:\n{instructions}\n\n"
                f"content:\n{content}\n\n"
                f"plugins: {plugin_names}"
            )
            log_agent_event(run_id=run_id, applicant_id=applicant_id, agent_name=agent_type, phase="request", message=req_msg)
    except Exception:
        pass

    result = await run_single_turn(
        name=name,
        instructions=instructions,
        message=content,
        with_bing_grounding=with_bing,
        plugins=plugins,
        model=model,
    )
    # Persist response log if context provided
    try:
        if run_id is not None and agent_type is not None:
            log_agent_event(run_id=run_id, applicant_id=applicant_id, agent_name=agent_type, phase="response", message=str(result)[:16000])
    except Exception:
        pass
    return result


async def english_agent(applicant_id: int, run_id: int, level_hint: str | None = None, policy: dict | None = None, model_override: Optional[str] = None) -> dict[str, Any]:
    instructions = (
        "You evaluate English language requirements for UCL admission using document access and exemption checking tools. Follow these steps:\n"
        "\n"
        "STEP 1 - Survey Documents:\n"
        "- Call list_documents() to see available materials\n"
        "- Prioritize: Personal Statement, CV, Transcripts, Test Certificates\n"
        "- Use search_documents() to find 'IELTS', 'TOEFL', 'nationality', 'citizenship', 'passport', degree location info\n"
        "\n"
        "STEP 2 - Check Exemptions (STANDARDIZED LOGIC):\n"
        "- Extract nationality/citizenship and degree country from documents\n"
        "- CRITICAL: Call check_comprehensive_exemption(nationality=X, degree_country=Y, institution_name=Z)\n"
        "- This plugin uses standardized country lists for deterministic exemption checking\n"
        "- If result.is_exempt=true: Call score_exemption() and set score=10\n"
        "- FALLBACK: If exemption check fails unexpectedly, you can call get_nationality_exempt_countries() and get_degree_exempt_countries() to see the full lists for manual verification\n"
        "\n"
        "STEP 3 - Extract Test Scores (if not exempt):\n"
        "- Read documents likely to contain test scores (certificates, CV, PS)\n"
        "- Extract ALL numeric scores: overall, reading, writing, speaking, listening\n"
        "- Common formats: 'Overall: 7.5', 'Band Score: 7.5', 'Total: 100'\n"
        "- Set test_type (e.g., 'IELTS') and test_overall (e.g., 7.5)\n"
        "\n"
        "STEP 4 - Evaluate Against Requirements (if not exempt):\n"
        "- Use level hint (e.g., 'level2') to determine required thresholds\n"
        "- Call meets_thresholds() function to compare observed vs. required scores\n"
        "- For IELTS Level 2, call score_ielts_level2() to get 0-10 score\n"
        "\n"
        "STEP 5 - Prepare Evidence:\n"
        "- Include exemption check results and reasoning in evidence array\n"
        "- For test scores: include score details and policy evaluation\n"
        "- All analysis must go in evidence array, not as markdown text\n"
        "\n"
        "Return JSON: {exemption:boolean, test_type:string|null, test_overall:number|null, level:string|null, score:number|null, evidence:string[]}\n"
        "CRITICAL: Use exemption plugin for standardized country checking. Don't guess or use semantic understanding for countries.\n"
        "FALLBACK: If the automated exemption check seems incorrect, you can call get_nationality_exempt_countries() and get_degree_exempt_countries() to get the full exemption lists for manual verification.\n"
        "Use minimal tokens - be strategic about which documents to read fully."
    )
    prompt = (
        f"Level hint: {level_hint or 'level2'}\n"
        "IMPORTANT: Use exemption plugin functions for standardized country checking - don't rely on semantic understanding.\n"
        "IMPORTANT: Use meets_thresholds(...) for deterministic numeric comparisons.\n"
        "IMPORTANT: Use document access functions to find English test and nationality information strategically.\n"
        "CRITICAL: If exemption=true, MUST call score_exemption() and set score=10. Include exemption reasoning in evidence.\n"
        "CRITICAL: All reasoning and analysis must be included in the evidence array, not as markdown text."
    )
    ans = await _ask_agent(
        "EnglishAgent",
        instructions,
        prompt,
        plugins=[EnglishScorePlugin(), EnglishExemptionPlugin(), DocStorePlugin(applicant_id, run_id)],
        agent_type="english",
        model_override=model_override,
        run_id=run_id,
        applicant_id=applicant_id,
    )
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
    model_override: Optional[str] = None,
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
        "   - These functions provide authoritative eligibility determinations with precise thresholds and institution classifications "
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
        "\n"
        "MANDATORY OUTPUT FORMAT: Return ONLY valid JSON (no markdown, bullets, or prose). "
        "All reasoning and analysis must be included in the evidence array, not as free text. "
        "Do not ask questions or request confirmation. "
        "The score field MUST be a number from 0 to 10 (never null). "
        "Return JSON exactly with keys: {country:string|null, institution:string|null, meets_requirement:boolean|null, qs_rank:int|null, score:number, subject_fit:boolean|null, missing_prerequisites:string[], evidence:string[], policy_source:string|null}."
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
        agent_type="degree",
        model_override=model_override,
        run_id=run_id,
        applicant_id=applicant_id,
    )
    result = parse_agent_json(ans)
    required_keys = {"country", "institution", "meets_requirement", "qs_rank", "score", "subject_fit", "missing_prerequisites", "evidence", "policy_source"}
    needs_retry = (
        result is None
        or not isinstance(result, dict)
        or not required_keys.issubset(set(result.keys()))
        or result.get("score") is None
    )
    if needs_retry:
        strict_instructions = instructions + "\nCRITICAL: Output must be ONLY the JSON object with the required keys and score 0-10."
        ans2 = await _ask_agent(
            "DegreeAgentStrict",
            strict_instructions,
            prompt,
            with_bing=True,
            plugins=[DegreeScorePlugin(), DegreePolicyPlugin(), ChinaIndiaEligibilityPlugin(), DocStorePlugin(applicant_id, run_id)],
            agent_type="degree",
            model_override=model_override,
            run_id=run_id,
            applicant_id=applicant_id,
        )
        result2 = parse_agent_json(ans2)
        if result2 is not None and isinstance(result2, dict) and required_keys.issubset(set(result2.keys())) and result2.get("score") is not None:
            return result2
        return {"country": None, "institution": None, "meets_requirement": None, "qs_rank": None, "score": None, "subject_fit": None, "missing_prerequisites": [], "evidence": [], "policy_source": None}
    return result



async def experience_agent(applicant_id: int, run_id: int, checklist: list[str] | None = None, model_override: Optional[str] = None) -> dict[str, Any]:
    instructions = (
        "You assess internships/work/projects vs requirements using document access tools. "
        "First call list_documents() then prioritize: CV, Personal Statement, Experience Letters, Portfolio. "
        "Use Bing to gauge company reputation when found. "
        "Score (0-10): top companies >2 months -> 10; Tencent/Huawei -> 8; general IT -> 4; other work -> 2; school projects based on relevance. "
        "Use minimal tokens - focus on CV and experience-related documents. "
        "\n"
        "MANDATORY OUTPUT FORMAT: Return ONLY valid JSON (no markdown, bullets, prose, or code fences). "
        "All reasoning and analysis must be included in the evidence array, not as free text. "
        "Do not ask questions or request confirmation. "
        "The score field MUST be a number from 0 to 10 (never null). "
        "Return JSON exactly with keys: {score:number, highlights:string[], evidence:string[]}."
    )
    prompt = f"Checklist: {checklist or []}\nUse document access functions to find work experience and project information."
    ans = await _ask_agent(
        "ExperienceAgent",
        instructions,
        prompt,
        with_bing=True,
        plugins=[DocStorePlugin(applicant_id, run_id)],
        agent_type="experience",
        model_override=model_override,
        run_id=run_id,
        applicant_id=applicant_id,
    )
    result = parse_agent_json(ans)
    required_keys = {"score", "highlights", "evidence"}
    needs_retry = (
        result is None
        or not isinstance(result, dict)
        or not required_keys.issubset(set(result.keys()))
        or not isinstance(result.get("score"), (int, float))
    )
    if needs_retry:
        strict_instructions = instructions + "\nCRITICAL: Output must be ONLY the JSON object with the required keys and score 0-10."
        ans2 = await _ask_agent(
            "ExperienceAgentStrict",
            strict_instructions,
            prompt,
            with_bing=True,
            plugins=[DocStorePlugin(applicant_id, run_id)],
            agent_type="experience",
            model_override=model_override,
            run_id=run_id,
            applicant_id=applicant_id,
        )
        result2 = parse_agent_json(ans2)
        if (
            result2 is not None
            and isinstance(result2, dict)
            and required_keys.issubset(set(result2.keys()))
            and isinstance(result2.get("score"), (int, float))
        ):
            return result2
        return {"score": None, "highlights": [], "evidence": []}
    return result


async def ps_rl_agent(applicant_id: int, run_id: int, checklist: list[str] | None = None, model_override: Optional[str] = None) -> dict[str, Any]:
    instructions = (
        "Evaluate personal statement motivation and detail; verify alignment to checklist using document access tools. "
        "First call list_documents() then prioritize: Personal Statement, Reference Letters, Motivation Letter. "
        "For reference letters, validate recommender standing with Bing. "
        "Use minimal tokens - focus on PS and reference letter documents specifically. "
        "\n"
        "MANDATORY: Return ONLY valid JSON format, no markdown or additional text. "
        "Each strength and weakness MUST have corresponding evidence. Structure as: "
        "{\"score\": <number 0-10>, \"strengths\": [{\"point\": \"strength description\", \"evidence\": \"specific evidence from documents\"}], \"weaknesses\": [{\"point\": \"weakness description\", \"evidence\": \"specific evidence from documents\"}]}"
    )
    prompt = f"Checklist: {checklist or []}\nUse document access functions to find personal statement and reference letter content."
    ans = await _ask_agent(
        "PsRlAgent",
        instructions,
        prompt,
        with_bing=False,
        plugins=[DocStorePlugin(applicant_id, run_id)],
        agent_type="ps_rl",
        model_override=model_override,
        run_id=run_id,
        applicant_id=applicant_id,
    )
    result = parse_agent_json(ans)
    if result is None:
        return {"score": None, "strengths": [], "weaknesses": []}
    return result


async def academic_agent(applicant_id: int, run_id: int, checklist: Optional[list[str]] = None, model_override: Optional[str] = None) -> dict[str, Any]:
    # Build checklist context
    checklist_text = ""
    if checklist:
        checklist_text = f"\n\nSpecific academic requirements to evaluate:\n" + "\n".join(f"- {req}" for req in checklist)
    
    instructions = (
        "Evaluate publications using document access tools: verify authenticity via Bing, venue tier (conference/journal), and coauthorship with faculty. "
        "First call list_documents() then prioritize: CV, Publications List, Research Statement, Portfolio. "
        "Use search_documents() to find 'publication', 'paper', 'conference', 'journal'. "
        "Score: top-tier 10; general conference 5; only unpublished 0. "
        "Use minimal tokens - focus on academic documents and publications. "
        "Return JSON: score (0-10), papers (array of {title, venue, tier}), evidence (array)."
        f"{checklist_text}"
    )
    prompt = "Use document access functions to find academic publications and research work."
    ans = await _ask_agent(
        "AcademicAgent",
        instructions,
        prompt,
        with_bing=True,
        plugins=[DocStorePlugin(applicant_id, run_id)],
        agent_type="academic",
        model_override=model_override,
        run_id=run_id,
        applicant_id=applicant_id,
    )
    result = parse_agent_json(ans)
    if result is None:
        return {"score": None, "papers": [], "evidence": []}
    return result


async def compare_agent(app_a: dict[str, Any], app_b: dict[str, Any], model_override: Optional[str] = None) -> dict[str, Any]:
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
    ans = await _ask_agent(
        "PairwiseAgent",
        instructions,
        content,
        with_bing=True,
        agent_type="compare",
        model_override=model_override,
    )
    result = parse_agent_json(ans)
    if result is not None and result.get("winner") in {"A", "B", "tie"}:
        return result
    return {"winner": "tie", "reason": "undecided"}
