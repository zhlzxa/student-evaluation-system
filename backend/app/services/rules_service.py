from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models import DegreeEquivalencySource, EnglishRule
import re


async def fetch_text_from_url(url: str, timeout: int = 30) -> str:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text


async def preview_page_text(url: str) -> str:
    html = await fetch_text_from_url(url)
    soup = BeautifulSoup(html, "html.parser")
    # Keep simple text extraction; semantic interpretation will be done by agents later
    text = soup.get_text("\n", strip=True)
    # Return full text for complete analysis
    return text


def extract_programme_basics(text: str) -> dict[str, str | None]:
    """Heuristic extraction of english_level and degree_requirement_class from programme text.

    - english_level: match 'English language level' followed by 'Level X' (1-5)
    - degree_requirement_class: look for phrases indicating FIRST / UPPER_SECOND / LOWER_SECOND
    """
    t = text or ""
    level = None
    m = re.search(r"English\s+language\s+level[^\n]*Level\s*([1-5])", t, re.IGNORECASE)
    if not m:
        m = re.search(r"\bLevel\s*([1-5])\b", t)
    if m:
        level = f"Level {m.group(1)}"

    cls = None
    tl = t.lower()
    if re.search(r"\bfirst[-\s]?class\b", tl):
        cls = "FIRST"
    if re.search(r"\bupper\s+second[-\s]?class\b|\b2[:\.]?1\b|\b2-1\b|\bsecond\s+higher\b", tl):
        cls = cls or "UPPER_SECOND"
    if re.search(r"\blower\s+second[-\s]?class\b|\b2[:\.]?2\b|\b2-2\b|\bsecond\s+lower\b", tl):
        # Prefer explicit lower second if present
        cls = "LOWER_SECOND"

    return {"english_level": level, "degree_requirement_class": cls}


def extract_programme_name_from_url_and_text(url: str, text: str) -> str:
    """Extract a meaningful program name from URL and page text.
    
    Args:
        url: The UCL programme URL
        text: Extracted page text content
        
    Returns:
        A clean, readable program name
    """
    # First try to extract from URL path
    program_name = None
    
    if url:
        # UCL URLs typically follow: /graduate/taught-degrees/program-name-msc
        # or /graduate/research-degrees/program-name-phd
        url_parts = url.split('/')
        for part in reversed(url_parts):
            if part and not part.isdigit():
                # Clean up the URL slug
                candidate = part.replace('-', ' ').replace('_', ' ')
                # Skip common non-program parts
                if candidate.lower() not in ['graduate', 'taught-degrees', 'research-degrees', 
                                           'prospective-students', 'www.ucl.ac.uk', 'ucl.ac.uk']:
                    program_name = candidate
                    break
    
    # If URL extraction didn't work or gave poor results, try text extraction
    if not program_name or len(program_name.strip()) < 3:
        # Look for common UCL program title patterns in text
        text_lines = text.split('\n')[:10]  # Check first 10 lines where title usually appears
        
        for line in text_lines:
            line = line.strip()
            
            # Pattern 1: "Program Name MSc/MA/PhD | UCL" or similar
            if ('|' in line and any(degree in line.upper() for degree in ['MSC', 'MA', 'PHD', 'MPHIL', 'MBA'])):
                program_part = line.split('|')[0].strip()
                if len(program_part) > 5:  # Reasonable length
                    program_name = program_part
                    break
            
            # Pattern 2: Lines ending with degree abbreviations
            for degree in ['MSc', 'MA', 'PhD', 'MPhil', 'MBA', 'MEng', 'LLM']:
                if line.endswith(degree) and len(line) > len(degree) + 3:
                    program_name = line
                    break
            
            if program_name:
                break
            
            # Pattern 3: Look for lines with degree words
            if any(word in line.upper() for word in ['MASTER', 'MASTERS', 'DOCTORATE', 'BACHELOR']) and len(line.strip()) > 10:
                # Take the line but clean it up
                program_name = line.strip()
                break
    
    # Clean up and format the extracted name
    if program_name:
        # Remove common prefixes/suffixes that don't add value
        program_name = program_name.strip()
        
        # Remove leading/trailing non-letter characters
        program_name = re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', program_name)
        
        # Capitalize properly
        words = program_name.split()
        capitalized_words = []
        
        for word in words:
            word = word.strip()
            if not word:
                continue
                
            # Keep certain abbreviations uppercase
            if word.upper() in ['MSC', 'MA', 'PHD', 'MPHIL', 'MBA', 'MEng', 'LLM', 'UCL', 'BSC', 'BA']:
                capitalized_words.append(word.upper())
            # Keep certain words lowercase (articles, prepositions)
            elif word.lower() in ['and', 'or', 'of', 'in', 'the', 'a', 'an', 'with', 'for', 'to']:
                capitalized_words.append(word.lower())
            else:
                # Standard title case
                capitalized_words.append(word.capitalize())
        
        program_name = ' '.join(capitalized_words)
        
        # Final validation - ensure it's reasonable
        if len(program_name.strip()) >= 5 and not program_name.lower().startswith('skip to'):
            return program_name.strip()
    
    # Fallback: extract a reasonable name from URL
    if url:
        # Last resort: use the domain + a cleaned path
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p and p not in ['graduate', 'taught-degrees']]
            if path_parts:
                fallback = path_parts[-1].replace('-', ' ').title()
                if len(fallback) >= 5:
                    return fallback
        except:
            pass
    
    # Ultimate fallback
    from datetime import datetime
    return f"Programme {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"


def ensure_degree_sources(db: Session, sources: list[tuple[str, str, str | None]]):
    """Upsert degree equivalency sources.

    sources: list of (uk_class, url, notes)
    """
    for uk_class, url, notes in sources:
        existing = db.query(DegreeEquivalencySource).filter_by(uk_class=uk_class).one_or_none()
        if existing:
            existing.source_url = url
            existing.notes = notes
        else:
            db.add(DegreeEquivalencySource(uk_class=uk_class, source_url=url, notes=notes))
    db.commit()


def create_or_update_english_rule(
    db: Session,
    nationality_exempt: list[str] | None,
    degree_country_exempt: list[str] | None,
    levels: dict[str, Any] | None,
    source_url: str | None,
) -> EnglishRule:
    obj = EnglishRule(
        nationality_exempt_countries=nationality_exempt,
        degree_obtained_exempt_countries=degree_country_exempt,
        levels=levels,
        source_url=source_url,
        last_verified_at=datetime.utcnow(),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
