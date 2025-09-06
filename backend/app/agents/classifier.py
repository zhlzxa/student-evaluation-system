from __future__ import annotations

from typing import Optional

from app.config import get_settings
from app.agents.azure_client import run_single_turn_blocking


ALLOWED_LABELS = [
    "personal_statement",
    "reference_letter",
    "cv_resume",
    "transcript",
    "diploma_certificate",
    "language_test",
    "certificate_award",
    "internship_proof",
    "general_overview",
    "other",
]


def _build_instructions() -> str:
    labels = ", ".join(ALLOWED_LABELS)
    return (
        "You are a classifier for graduate application documents. "
        "Given the fulltext or extracted paragraphs of a single document, classify it into exactly one label from: "
        f"{labels}. "
        "Guidelines: personal_statement is the applicant's essay about motivation; reference_letter is a recommender's letter; "
        "cv_resume is the candidate's resume; transcript lists courses and grades; diploma_certificate certifies a degree; "
        "language_test is IELTS/TOEFL or similar; certificate_award are honors/awards; internship_proof verifies internships/work; "
        "general_overview includes brochures or programme overviews; otherwise choose other. "
        "Respond with only the label, lowercase, no extra words."
    )


def classify_document(text: str) -> Optional[str]:
    """Classify a document text into a canonical label. Returns None if unavailable.

    Uses AzureAIAgent; if configuration is missing or errors occur, returns None.
    """
    settings = get_settings()
    if not (settings.AZURE_AI_AGENT_ENDPOINT or settings.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME):
        return None

    # Limit content size to keep token usage in check
    content = text[:12000]
    instructions = _build_instructions()
    prompt = (
        "Classify this document. Output only the label.\n\n" 
        f"Document:\n{content}\n"
    )

    try:
        result = run_single_turn_blocking(name="DocClassifier", instructions=instructions, message=prompt)
        label = (result or "").strip().strip("`\"'")
        if label in ALLOWED_LABELS:
            return label
        # Try to normalize common variants
        normalized = label.lower()
        if normalized in ALLOWED_LABELS:
            return normalized
        return None
    except Exception:
        return None


def classify_documents_batch(documents: list[dict]) -> dict[str, str]:
    """Classify multiple documents in a single agent call for efficiency.
    
    Args:
        documents: List of dicts with keys 'filename', 'text', 'doc_id'
        
    Returns:
        Dict mapping doc_id to classification label
    """
    settings = get_settings()
    if not (settings.AZURE_AI_AGENT_ENDPOINT or settings.AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME):
        return {}
    
    if not documents:
        return {}
    
    # Build batch instructions
    labels = ", ".join(ALLOWED_LABELS)
    instructions = (
        "You are a classifier for graduate application documents. "
        "You will be given multiple documents to classify in a single request. "
        f"For each document, classify it into exactly one label from: {labels}. "
        "Guidelines: personal_statement is the applicant's essay about motivation; reference_letter is a recommender's letter; "
        "cv_resume is the candidate's resume; transcript lists courses and grades; diploma_certificate certifies a degree; "
        "language_test is IELTS/TOEFL or similar; certificate_award are honors/awards; internship_proof verifies internships/work; "
        "general_overview includes brochures or programme overviews; otherwise choose other. "
        "Return your response as JSON in the format: {\"doc_1\": \"label\", \"doc_2\": \"label\", ...} "
        "Use only lowercase labels with no extra words."
    )
    
    # Build batch prompt
    prompt_parts = ["Classify these documents:\n"]
    for i, doc in enumerate(documents, 1):
        # Limit each document content size
        content = doc['text'][:8000] if doc['text'] else ""
        filename = doc.get('filename', f'document_{i}')
        prompt_parts.append(f"Document doc_{i} (filename: {filename}):")
        prompt_parts.append(content)
        prompt_parts.append("")
    
    prompt = "\n".join(prompt_parts)
    
    try:
        result = run_single_turn_blocking(name="BatchDocClassifier", instructions=instructions, message=prompt)
        
        # Parse JSON response
        import json
        result_clean = (result or "").strip()
        
        # Try to extract JSON from response
        if result_clean.startswith("{") and result_clean.endswith("}"):
            classifications = json.loads(result_clean)
        else:
            # Try to find JSON in response
            import re
            json_match = re.search(r'\{[^}]+\}', result_clean)
            if json_match:
                classifications = json.loads(json_match.group())
            else:
                return {}
        
        # Map back to doc_ids and validate labels
        result_map = {}
        for i, doc in enumerate(documents, 1):
            doc_key = f"doc_{i}"
            if doc_key in classifications:
                label = classifications[doc_key].strip().lower()
                if label in ALLOWED_LABELS:
                    result_map[doc['doc_id']] = label
        
        return result_map
        
    except Exception:
        return {}

