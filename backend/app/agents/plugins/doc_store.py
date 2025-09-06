from __future__ import annotations

from typing import Annotated, List, Dict, Any, Optional
from pathlib import Path

from semantic_kernel.functions import kernel_function
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.assessment import ApplicantDocument
from app.services.storage import ensure_storage_dir


class DocStorePlugin:
    """Provides agents with intelligent access to applicant documents.
    
    Instead of receiving a pre-concatenated text blob, agents can:
    1. List available documents for an applicant
    2. Read specific documents (full text or page-by-page)
    3. Make strategic decisions about which documents to examine first
    
    This mimics human evaluator behavior - reviewing PS first, then transcripts, etc.
    """

    def __init__(self, applicant_id: int, run_id: int):
        self.applicant_id = applicant_id
        self.run_id = run_id
        self._storage_base = Path(ensure_storage_dir()) / "runs" / f"run_{run_id}"

    @kernel_function(description="List all documents available for this applicant with metadata.")
    def list_documents(self) -> Annotated[str, "JSON array of documents with id, filename, type, size, and brief description"]:
        """List all documents for the applicant."""
        db = SessionLocal()
        try:
            docs = db.query(ApplicantDocument).filter_by(applicant_id=self.applicant_id).all()
            
            doc_list = []
            for doc in docs:
                doc_info = {
                    "id": doc.id,
                    "filename": doc.original_filename,
                    "type": doc.doc_type or "unknown",
                    "content_type": doc.content_type,
                    "size_bytes": doc.size_bytes,
                    "rel_path": doc.rel_path,
                    "preview": (doc.text_preview or "")[:200] + "..." if doc.text_preview and len(doc.text_preview) > 200 else doc.text_preview or ""
                }
                doc_list.append(doc_info)
            
            import json
            return json.dumps(doc_list, indent=2)
        finally:
            db.close()

    @kernel_function(description="Read the full text content of a specific document.")
    def read_document(
        self,
        doc_id: Annotated[int, "Document ID from list_documents()"],
    ) -> Annotated[str, "Full text content of the document"]:
        """Read complete text content of a document."""
        db = SessionLocal()
        try:
            doc = db.query(ApplicantDocument).filter_by(
                id=doc_id, 
                applicant_id=self.applicant_id
            ).first()
            
            if not doc:
                return "Document not found or access denied."
            
            # Return cached text_preview if available
            if doc.text_preview:
                return doc.text_preview
            
            # Try to read from file if no preview cached
            file_path = self._storage_base / doc.rel_path
            if not file_path.exists():
                return "Document file not found on disk."
            
            try:
                # For text files, read directly
                if doc.content_type and doc.content_type.startswith("text/"):
                    return file_path.read_text(encoding="utf-8", errors="ignore")
                
                # For other files, return preview or indication that it needs processing
                return doc.text_preview or f"Binary file {doc.original_filename} - text extraction needed."
            except Exception as e:
                return f"Error reading document: {str(e)}"
        finally:
            db.close()

    @kernel_function(description="Read a specific page or section of a document (for large documents).")
    def read_document_window(
        self,
        doc_id: Annotated[int, "Document ID from list_documents()"],
        start_char: Annotated[int, "Starting character position (0-based)"] = 0,
        length: Annotated[int, "Number of characters to read (max 5000)"] = 5000,
    ) -> Annotated[str, "Text content window with position info"]:
        """Read a specific window of text from a document."""
        db = SessionLocal()
        try:
            doc = db.query(ApplicantDocument).filter_by(
                id=doc_id, 
                applicant_id=self.applicant_id
            ).first()
            
            if not doc:
                return "Document not found or access denied."
            
            # Get full text (from cache or file)
            full_text = ""
            if doc.text_preview:
                full_text = doc.text_preview
            else:
                file_path = self._storage_base / doc.rel_path
                if file_path.exists() and doc.content_type and doc.content_type.startswith("text/"):
                    try:
                        full_text = file_path.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        return "Error reading document file."
            
            if not full_text:
                return "No text content available for this document."
            
            # Limit window size to prevent context overflow
            max_length = min(length, 5000)
            start_pos = max(0, start_char)
            end_pos = min(len(full_text), start_pos + max_length)
            
            window_text = full_text[start_pos:end_pos]
            
            return f"Document: {doc.original_filename}\nPosition: {start_pos}-{end_pos} of {len(full_text)} chars\n\n{window_text}"
        finally:
            db.close()

    @kernel_function(description="Search for specific keywords or patterns within all applicant documents.")
    def search_documents(
        self,
        query: Annotated[str, "Search terms or keywords"],
        max_results: Annotated[int, "Maximum number of results to return"] = 10,
    ) -> Annotated[str, "Search results with document context"]:
        """Search for specific content across all documents."""
        db = SessionLocal()
        try:
            docs = db.query(ApplicantDocument).filter_by(applicant_id=self.applicant_id).all()
            
            results = []
            query_lower = query.lower()
            
            for doc in docs:
                text = doc.text_preview or ""
                if query_lower in text.lower():
                    # Find context around the match
                    start_idx = text.lower().find(query_lower)
                    context_start = max(0, start_idx - 100)
                    context_end = min(len(text), start_idx + len(query) + 100)
                    context = text[context_start:context_end]
                    
                    results.append({
                        "doc_id": doc.id,
                        "filename": doc.original_filename,
                        "doc_type": doc.doc_type,
                        "context": context,
                        "match_position": start_idx
                    })
                    
                    if len(results) >= max_results:
                        break
            
            import json
            return json.dumps(results, indent=2)
        finally:
            db.close()