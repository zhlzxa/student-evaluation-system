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
        "You are an English language assessment specialist for UCL admissions. Your role is to evaluate whether applicants meet the English language requirements. "
        "Write your findings in clear, professional language that admissions staff can easily understand.\n"
        "\n"
        "EVALUATION PROCESS:\n"
        "1. Document Review: Call list_documents() and search_documents() to find relevant materials (certificates, personal statements, CVs, transcripts)\n"
        "2. Table Data Analysis: For documents with has_tables=true, use read_document_tables() or search_tables() to extract structured test scores\n"
        "3. Exemption Check: Use check_comprehensive_exemption() to determine if the applicant is exempt based on nationality or degree country\n"
        "4. Test Score Analysis: If not exempt, extract and evaluate English test scores (IELTS, TOEFL, etc.)\n"
        "5. Requirements Assessment: Compare findings against UCL's requirements using the appropriate scoring functions\n"
        "\n"
        "EVIDENCE WRITING GUIDELINES:\n"
        "Write evidence entries as complete, professional sentences that explain your findings clearly. Examples:\n"
        "- 'The applicant is a British citizen and therefore exempt from English language requirements.'\n"
        "- 'IELTS Academic score of 7.5 overall (with 6.5 in each component) meets the Level 2 requirements for this programme.'\n"
        "- 'No English language test certificates were found in the submitted documents.'\n"
        "- 'The applicant completed their undergraduate degree at University of Toronto, Canada, which qualifies for English language exemption.'\n"
        "\n"
        "TECHNICAL REQUIREMENTS:\n"
        "- Use exemption plugins for accurate country checking (don't guess)\n"
        "- Call appropriate scoring functions (score_exemption(), score_ielts_level2(), etc.)\n"
        "- If exempt, set score=10 and exemption=true\n"
        "- Include all supporting details in the evidence array\n"
        "\n"
        "CUSTOM REQUIREMENTS HANDLING:\n"
        "- Some requirements in the input checklist may be marked with [USER DEFINED] - these are custom user requirements with HIGHER priority than standard rules\n"
        "- When evaluating, prioritize user-defined requirements over standard criteria if they conflict\n"
        "- In your evidence, reference the exact requirement text as provided (including [USER DEFINED] prefix if present)\n"
        "- IMPORTANT: Do NOT add [USER DEFINED] prefix to your output - only reference existing prefixes when quoting requirements\n"
        "\n"
        "OUTPUT FORMAT: Return ONLY valid JSON with no additional text.\n"
        "Return JSON: {exemption:boolean, test_type:string|null, test_overall:number|null, level:string|null, score:number|null, evidence:string[]}\n"
        "Make evidence entries readable and informative for admissions staff review."
    )
    prompt = (
        f"Required English level: {level_hint or 'level2'}\n\n"
        "Please evaluate this applicant's English language qualifications and write a clear assessment.\n"
        "Focus on providing helpful information for admissions staff who will review this application.\n\n"
        "Remember to:\n"
        "- Use the exemption checking functions to verify nationality and degree country exemptions\n"
        "- Extract test scores accurately and compare them against requirements\n"
        "- Write evidence in complete sentences that explain your findings\n"
        "- Include specific details about test scores, exemption reasons, or missing documentation"
    )
    # First attempt
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
    
    # Retry if parsing failed
    if result is None:
        retry_instructions = instructions + "\n\nCRITICAL RETRY: Previous response failed JSON parsing. Return ONLY valid JSON object starting with { and ending with }. No additional text."
        ans2 = await _ask_agent(
            "EnglishAgentRetry",
            retry_instructions,
            prompt,
            plugins=[EnglishScorePlugin(), EnglishExemptionPlugin(), DocStorePlugin(applicant_id, run_id)],
            agent_type="english",
            model_override=model_override,
            run_id=run_id,
            applicant_id=applicant_id,
        )
        result = parse_agent_json(ans2)
    
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
        "You are an academic credentials evaluator for UCL admissions. Your role is to assess whether applicants' degrees and academic backgrounds meet the entry requirements. "
        "Write your findings in clear, informative language that helps admissions staff understand the applicant's academic profile.\n"
        "\n"
        "EVALUATION PROCESS:\n"
        "1. Document Review: Examine transcripts, degree certificates, and CVs to understand the applicant's academic background\n"
        "2. Table Data Analysis: For transcripts with has_tables=true, use read_document_tables() to extract structured grade data, course lists, and GPA information\n"
        "3. Institution Analysis: Identify the degree-awarding institution, its reputation, and QS World Ranking\n"
        "4. Academic Achievement: Extract grades, GPA, or percentage marks and assess against UCL requirements\n"
        "5. Subject Relevance: Evaluate how well the applicant's field of study aligns with the target programme\n"
        "6. Country-Specific Assessment: Use appropriate evaluation frameworks for different countries\n"
        "\n"
        "EVIDENCE WRITING GUIDELINES:\n"
        "Write evidence as complete, informative sentences that provide clear context. Include specific details:\n"
        "- 'The applicant holds a Bachelor of Computer Science degree from Beijing University of Technology, China.'\n"
        "- 'Academic performance shows a weighted average of 87.5%, which exceeds the 85% requirement for upper second-class equivalency.'\n"
        "- 'Beijing University of Technology is ranked #801-1000 in the latest QS World University Rankings.'\n"
        "- 'The Computer Science degree provides strong subject alignment with the target MSc programme requirements.'\n"
        "- 'Transcript review confirms completion of prerequisite courses in mathematics and programming fundamentals.'\n"
        "\n"
        "TECHNICAL REQUIREMENTS:\n"
        "- Use specialized evaluation plugins for China/India when applicable\n"
        "- Include specific degree details: type (Bachelor/Master), field of study, institution name\n"
        "- Provide exact academic results with context (e.g., '87.5% weighted average')\n"
        "- Research and include the most recent QS World University Ranking (search for latest available year, be precise about ranking numbers)\n"
        "- Assess subject fit and identify any missing prerequisites\n"
        "- CRITICAL: The 'score' field MUST be an evaluation score from 0-10 rating the overall degree qualification strength, NOT the student's percentage grade\n"
        "- Scoring scale: Strong degrees from top institutions (9-10), good degrees meeting requirements (7-8), marginal cases (5-6), below requirements (1-4), insufficient information (0)\n"
        "- DO NOT use the student's academic percentage (e.g., 86.8%) as the score - that goes in evidence and degree details\n"
        "\n"
        "CUSTOM REQUIREMENTS HANDLING:\n"
        "- Some requirements in the input checklist may be marked with [USER DEFINED] - these are custom user requirements with HIGHER priority than standard rules\n"
        "- When evaluating, prioritize user-defined requirements over standard criteria if they conflict\n"
        "- In your evidence, reference the exact requirement text as provided (including [USER DEFINED] prefix if present)\n"
        "- IMPORTANT: Do NOT add [USER DEFINED] prefix to your output - only reference existing prefixes when quoting requirements\n"
        "\n"
        "OUTPUT FORMAT: Return ONLY valid JSON with no additional text.\n"
        "Return JSON: {country:string|null, institution:string|null, meets_requirement:boolean|null, qs_rank:int|null, score:number, subject_fit:boolean|null, missing_prerequisites:string[], evidence:string[], policy_source:string|null, degrees:object[]}\n"
        "The score field must be a number from 0 to 10 representing the evaluation strength of the degree qualification, NOT the student's academic percentage.\n"
        "The degrees field should contain an array of degree objects, each with: {degree_type:string, field_of_study:string, institution:string, country:string, grade:string|null, duration:string|null}\n"
        "Include all identified degrees. If no degrees found, use empty array.\n"
        "Make evidence entries detailed and informative for comprehensive degree evaluation review."
    )
    prompt = "\n".join([
        f"Target requirement: {target_class} UK class equivalent",
        f"Programme requirements checklist: {checklists or []}",
        (f"Country-specific context for {detected_country_iso3}:\n{(special_context or '')[:6000]}" if special_context else ""),
        "",
        "Please evaluate this applicant's academic credentials comprehensively.",
        "Focus on providing clear, detailed information about their educational background.",
        "",
        "In your evidence, please include:",
        "- Complete degree information (type, field of study, institution name and country)",
        "- Specific academic results with percentage/GPA and any honors received",
        "- Institution reputation and latest QS World University Ranking",
        "- Assessment of subject relevance to the target programme",
        "- Any missing prerequisites or areas of concern",
        "",
        "IMPORTANT: For each degree you identify, populate the degrees array with objects containing:",
        "- degree_type: e.g., 'Bachelor of Science', 'Master of Arts', 'PhD'",
        "- field_of_study: e.g., 'Computer Science', 'Mathematics', 'Engineering'",
        "- institution: Full institution name",
        "- country: Country where degree was awarded",
        "- grade: Final grade/result if available (e.g., 'Upper Second Class Honours', '87.5%', '3.8 GPA')",
        "- duration: Program duration if mentioned (e.g., '3 years', '2021-2024')",
        "",
        "Include ALL degrees found in the documents, not just the highest or most relevant one.",
        "",
        "Use the appropriate evaluation plugins and provide thorough documentation.",
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
    required_keys = {"country", "institution", "meets_requirement", "qs_rank", "score", "subject_fit", "missing_prerequisites", "evidence", "policy_source", "degrees"}
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
        return {"country": None, "institution": None, "meets_requirement": None, "qs_rank": None, "score": None, "subject_fit": None, "missing_prerequisites": [], "evidence": [], "policy_source": None, "degrees": []}
    return result



async def experience_agent(applicant_id: int, run_id: int, checklist: list[str] | None = None, model_override: Optional[str] = None) -> dict[str, Any]:
    instructions = (
        "You assess internships/work/projects vs requirements using document access tools. "
        "First call list_documents() then prioritize: CV, Personal Statement, Experience Letters, Portfolio. "
        "Use Bing to gauge company reputation when found. "
        "For documents with has_tables=true, use read_document_tables() or search_tables() to extract structured employment dates, durations, and project lists. "
        "Score (0-10): top companies >2 months -> 10; Tencent/Huawei -> 8; general IT -> 4; other work -> 2; school projects based on relevance. "
        "Use minimal tokens - focus on CV and experience-related documents. "
        "\n"
        "CUSTOM REQUIREMENTS HANDLING:\n"
        "- Some requirements in the input checklist may be marked with [USER DEFINED] - these are custom user requirements with HIGHER priority than standard rules\n"
        "- When evaluating, prioritize user-defined requirements over standard criteria if they conflict\n"
        "- In your evidence, reference the exact requirement text as provided (including [USER DEFINED] prefix if present)\n"
        "- IMPORTANT: Do NOT add [USER DEFINED] prefix to your output - only reference existing prefixes when quoting requirements\n"
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
        "For documents with has_tables=true, use read_document_tables() or search_tables() to extract structured achievements, publications, or activity lists. "
        "Use minimal tokens - focus on PS and reference letter documents specifically. \n\n"
        "CUSTOM REQUIREMENTS HANDLING:\n"
        "- Some requirements in the input checklist may be marked with [USER DEFINED] - these are custom user requirements with HIGHER priority than standard rules\n"
        "- When evaluating, prioritize user-defined requirements over standard criteria if they conflict\n"
        "- In your evidence, reference the exact requirement text as provided (including [USER DEFINED] prefix if present)\n"
        "- IMPORTANT: Do NOT add [USER DEFINED] prefix to your output - only reference existing prefixes when quoting requirements\n"
        "\n"
        "MANDATORY OUTPUT FORMAT: Return ONLY valid JSON with no additional text, explanations, or formatting.\n"
        "Do not use markdown code fences or backticks. Start with { and end with }.\n"
        "Each strength and weakness MUST have corresponding evidence. Structure as: "
        "{\"score\": <number 0-10>, \"strengths\": [{\"point\": \"strength description\", \"evidence\": \"specific evidence from documents\"}], \"weaknesses\": [{\"point\": \"weakness description\", \"evidence\": \"specific evidence from documents\"}]}"
    )
    prompt = f"Checklist: {checklist or []}\nUse document access functions to find personal statement and reference letter content."
    # First attempt
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
    
    # Retry if parsing failed
    if result is None:
        retry_instructions = instructions + "\n\nCRITICAL RETRY: Previous response failed JSON parsing. Return ONLY valid JSON object starting with { and ending with }. No additional text."
        ans2 = await _ask_agent(
            "PsRlAgentRetry",
            retry_instructions,
            prompt,
            with_bing=False,
            plugins=[DocStorePlugin(applicant_id, run_id)],
            agent_type="ps_rl",
            model_override=model_override,
            run_id=run_id,
            applicant_id=applicant_id,
        )
        result = parse_agent_json(ans2)
    
    if result is None:
        return {"score": None, "strengths": [], "weaknesses": []}
    return result


async def academic_agent(applicant_id: int, run_id: int, checklist: Optional[list[str]] = None, model_override: Optional[str] = None) -> dict[str, Any]:
    # Build checklist context
    checklist_text = ""
    if checklist:
        checklist_text = f"\n\nSpecific academic requirements to evaluate:\n" + "\n".join(f"- {req}" for req in checklist)
    
    instructions = (
        "You are an academic publications evaluator for UCL admissions. Your role is to assess applicants' research experience and academic contributions. "
        "Write your findings in clear, detailed language that helps admissions staff understand the quality and scope of the applicant's academic work.\n"
        "\n"
        "EVALUATION PROCESS:\n"
        "1. Document Review: Examine CVs, publication lists, research statements, and portfolios\n"
        "2. Table Data Analysis: For documents with has_tables=true, use read_document_tables() or search_tables() to extract structured publication lists, awards, and metrics\n"
        "3. Publication Discovery: Search for academic papers, conference presentations, thesis work, and research projects\n"
        "4. Venue Assessment: Research the quality and reputation of publication venues (journals, conferences)\n"
        "5. Impact Evaluation: Consider factors like citation count, venue ranking, and collaboration with faculty\n"
        "\n"
        "EVIDENCE WRITING GUIDELINES:\n"
        "Write evidence as complete, informative sentences that provide comprehensive publication details:\n"
        "- 'The applicant has published \"Deep Learning Approaches to Natural Language Processing\" in the IEEE Transactions on Neural Networks and Learning Systems (Impact Factor: 14.255).'\n"
        "- 'Co-authored research paper \"Blockchain Security Analysis\" presented at the 2023 ACM Conference on Computer and Communications Security, a top-tier venue in cybersecurity research.'\n"
        "- 'Completed undergraduate thesis titled \"Machine Learning Applications in Healthcare\" under supervision of Prof. Zhang at Beijing University of Technology.'\n"
        "- 'First-authored paper demonstrates independent research capability in the target field of study.'\n"
        "- 'No academic publications were found in the submitted documents, which is typical for undergraduate applicants.'\n"
        "\n"
        "PUBLICATION DETAILS TO INCLUDE:\n"
        "- Complete paper titles and full venue names\n"
        "- Publication year and authorship position (first author, co-author, etc.)\n"
        "- Venue quality assessment (impact factor, conference ranking, tier classification)\n"
        "- Research field relevance to the target programme\n"
        "- Any notable achievements (awards, high citations, etc.)\n"
        "\n"
        "CUSTOM REQUIREMENTS HANDLING:\n"
        "- Some requirements in the input checklist may be marked with [USER DEFINED] - these are custom user requirements with HIGHER priority than standard rules\n"
        "- When evaluating, prioritize user-defined requirements over standard criteria if they conflict\n"
        "- In your evidence, reference the exact requirement text as provided (including [USER DEFINED] prefix if present)\n"
        "- IMPORTANT: Do NOT add [USER DEFINED] prefix to your output - only reference existing prefixes when quoting requirements\n"
        "\n"
        "OUTPUT FORMAT: Return ONLY valid JSON with no additional text.\n"
        "Required JSON format: {\"score\": number(0-10), \"papers\": [{\"title\": \"string\", \"venue\": \"string\", \"tier\": \"string\", \"year\": \"string|null\", \"authors\": \"string|null\"}], \"evidence\": [\"string\"]}\n"
        "Each paper object should include:\n"
        "- title: Complete paper title\n"
        "- venue: Full venue name (journal/conference)\n"
        "- tier: Quality assessment (e.g., 'Top-tier', 'High-impact', 'Regional conference')\n"
        "- year: Publication year if available\n"
        "- authors: Author list or authorship position if available\n"
        "Make evidence entries comprehensive and informative for academic merit assessment."
        f"{checklist_text}"
    )
    prompt = (
        "Please evaluate this applicant's academic publications and research experience comprehensively.\n"
        "Focus on providing detailed information about their scholarly contributions.\n\n"
        "In your evidence, please include specific details about:\n"
        "- Complete titles of published papers, conference presentations, or thesis work\n"
        "- Full names of publication venues (journals, conferences, workshops)\n"
        "- Quality indicators (impact factors, conference rankings, venue reputation)\n"
        "- Authorship details and collaboration information\n"
        "- Relevance of research topics to the target programme\n\n"
        "If no publications are found, provide a clear explanation and context for the applicant's academic level."
    )
    # First attempt
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
    
    # Retry if parsing failed
    if result is None:
        retry_instructions = instructions + "\n\nCRITICAL RETRY: Previous response failed JSON parsing. Return ONLY valid JSON object starting with { and ending with }. No additional text."
        ans2 = await _ask_agent(
            "AcademicAgentRetry",
            retry_instructions,
            prompt,
            with_bing=True,
            plugins=[DocStorePlugin(applicant_id, run_id)],
            agent_type="academic",
            model_override=model_override,
            run_id=run_id,
            applicant_id=applicant_id,
        )
        result = parse_agent_json(ans2)
    
    if result is None:
        return {"score": None, "papers": [], "evidence": []}
    return result


async def compare_agent(app_a: dict[str, Any], app_b: dict[str, Any], model_override: Optional[str] = None) -> dict[str, Any]:
    """Pairwise comparison for Bradley–Terry adjustment.

    Returns JSON: {winner: "A"|"B"|"tie", reason: string}
    """
    instructions = (
        "You compare two applicants using structured scores and evidence from multiple agents (english, degree, academic, experience, ps_rl). "
        "Choose which applicant is better overall for UCL admissions based on the provided weights (english 10%, degree 50%, academic 15%, experience 15%, ps_rl 10%). \n\n"
        "MANDATORY OUTPUT FORMAT: Return ONLY valid JSON with no additional text, explanations, or formatting.\n"
        "Do not use markdown code fences or backticks. Start with { and end with }.\n"
        "Return strict JSON: {winner: 'A'|'B'|'tie', reason: string}."
    )
    import json
    content = json.dumps({"A": app_a, "B": app_b})
    # First attempt
    ans = await _ask_agent(
        "PairwiseAgent",
        instructions,
        content,
        with_bing=True,
        agent_type="compare",
        model_override=model_override,
    )
    result = parse_agent_json(ans)
    
    # Retry if parsing failed or invalid winner
    if result is None or result.get("winner") not in {"A", "B", "tie"}:
        retry_instructions = instructions + "\n\nCRITICAL RETRY: Previous response failed. Return ONLY valid JSON object starting with { and ending with }. Winner must be 'A', 'B', or 'tie'."
        ans2 = await _ask_agent(
            "PairwiseAgentRetry",
            retry_instructions,
            content,
            with_bing=True,
            agent_type="compare",
            model_override=model_override,
        )
        result = parse_agent_json(ans2)
    
    if result is not None and result.get("winner") in {"A", "B", "tie"}:
        return result
    return {"winner": "tie", "reason": "undecided"}
