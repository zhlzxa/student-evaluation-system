from __future__ import annotations

import os
from pathlib import Path
import shutil
from typing import Iterator
import zipfile

from app.config import get_settings


def ensure_storage_dir() -> Path:
    base = Path(get_settings().STORAGE_DIR).resolve()
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_zip(content: bytes, run_id: int) -> Path:
    base = ensure_storage_dir()
    zips_dir = base / "zips"
    zips_dir.mkdir(parents=True, exist_ok=True)
    path = zips_dir / f"run_{run_id}.zip"
    path.write_bytes(content)
    return path


def _is_within_directory(directory: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(directory.resolve())
        return True
    except Exception:
        return False


def extract_zip(zip_path: Path, run_id: int) -> Path:
    base = ensure_storage_dir()
    dest = base / "runs" / f"run_{run_id}"
    # Clean previous extraction to avoid stale applicants/documents on re-upload
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            # Skip directory traversal and absolute paths
            name = Path(member.filename)
            if name.is_absolute() or any(part in ("..", "") for part in name.parts):
                continue
            target = dest / name
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member, "r") as src, open(target, "wb") as out:
                    out.write(src.read())
    return dest


def iter_applicant_folders(root: Path) -> Iterator[Path]:
    for p in root.iterdir():
        if p.is_dir():
            name = p.name
            # Skip common junk/hidden directories from ZIPs
            if name.startswith('.') or name == '__MACOSX':
                continue
            yield p


def guess_content_type(path: Path) -> str | None:
    # Keep simple mapping; detailed parsing delegated to Azure Document Intelligence later
    ext = path.suffix.lower()
    if ext in {".pdf"}:
        return "application/pdf"
    if ext in {".doc", ".docx"}:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in {".txt"}:
        return "text/plain"
    if ext in {".png"}:
        return "image/png"
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return None


def read_text_preview(path: Path, max_chars: int = 4000) -> str | None:
    try:
        if guess_content_type(path) == "text/plain":
            data = path.read_text(errors="ignore")
            return data[:max_chars]
    except Exception:
        return None
    return None
