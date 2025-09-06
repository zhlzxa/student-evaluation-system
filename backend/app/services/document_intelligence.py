from __future__ import annotations

from pathlib import Path
from typing import Any

from app.config import get_settings


def available() -> bool:
    s = get_settings()
    return bool(s.AZURE_DI_ENDPOINT and s.AZURE_DI_KEY)


def analyze_layout_file(path: Path) -> dict[str, Any]:
    """Analyze document layout via Azure Document Intelligence prebuilt layout model.

    Returns a compact dict with paragraphs and tables (as strings for now).
    If configuration is missing, returns a placeholder result.
    """
    if not available():
        return {"status": "skipped", "reason": "missing_config"}

    try:
        # Lazy import so environments without the package still run other paths
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential
    except Exception as e:  # pragma: no cover
        return {"status": "skipped", "reason": f"import_error: {e}"}

    s = get_settings()
    client = DocumentIntelligenceClient(endpoint=s.AZURE_DI_ENDPOINT, credential=AzureKeyCredential(s.AZURE_DI_KEY))

    with open(path, "rb") as f:
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=f
        )
        result = poller.result()

    paras: list[str] = []
    try:
        if result.paragraphs:
            paras = [p.content for p in result.paragraphs if getattr(p, "content", None)]
    except Exception:
        pass

    tables: list[list[list[str]] | str] = []
    try:
        if result.tables:
            for t in result.tables:
                rows = max([c.row_index for c in t.cells] + [0]) + 1 if t.cells else 0
                cols = max([c.column_index for c in t.cells] + [0]) + 1 if t.cells else 0
                grid = [["" for _ in range(cols)] for _ in range(rows)]
                for c in t.cells:
                    grid[c.row_index][c.column_index] = c.content or ""
                tables.append(grid)
    except Exception:
        pass

    return {
        "status": "ok",
        "paragraphs": paras[:2000],  # guard size
        "tables": tables[:50],
    }

