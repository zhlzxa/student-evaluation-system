"""URL content extraction service using BeautifulSoup4."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def extract_full_page_text(url: str, timeout: int = 60) -> dict[str, Any]:
    """
    Extract complete text content from a webpage using BeautifulSoup4.
    
    Args:
        url: The webpage URL to extract text from
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary containing:
        - text: Full page text content
        - title: Page title if available
        - status: 'success' or 'error'
        - error: Error message if extraction failed
        - url: Original URL
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout, 
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        ) as client:
            logger.info(f"Fetching URL: {url}")
            response = await client.get(url)
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else "No title"
            
            # Extract all text content
            # Get text with newlines preserved for structure
            full_text = soup.get_text(separator='\n', strip=True)
            
            # Clean up excessive whitespace
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            cleaned_text = '\n'.join(lines)
            
            logger.info(f"Successfully extracted {len(cleaned_text)} characters from {url}")
            
            return {
                'text': cleaned_text,
                'title': title,
                'status': 'success',
                'url': url,
                'length': len(cleaned_text)
            }
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error {e.response.status_code} for URL {url}: {str(e)}"
        logger.error(error_msg)
        return {
            'text': '',
            'title': '',
            'status': 'error',
            'error': error_msg,
            'url': url
        }
    except httpx.TimeoutException:
        error_msg = f"Timeout error for URL {url}"
        logger.error(error_msg)
        return {
            'text': '',
            'title': '',
            'status': 'error', 
            'error': error_msg,
            'url': url
        }
    except Exception as e:
        error_msg = f"Unexpected error extracting text from {url}: {str(e)}"
        logger.error(error_msg)
        return {
            'text': '',
            'title': '',
            'status': 'error',
            'error': error_msg,
            'url': url
        }


def extract_programme_title_from_text(page_text: str, url: str) -> str:
    """
    Extract a meaningful programme title from page text and URL.
    
    Args:
        page_text: Full page text content
        url: Original URL
        
    Returns:
        Extracted programme title or auto-generated name
    """
    try:
        import re
        from urllib.parse import urlparse

        def clean_candidate(text: str) -> str:
            # Remove segments that are clearly site-wide labels
            junk_markers = [
                'university college london', 'ucl', 'prospective students', 'graduate',
                'taught degrees', 'research degrees', 'home', 'study', 'programmes'
            ]
            # Split by common separators and keep the most specific left part
            separators = ['|', '—', '–', '-', '·']
            candidate = text
            for sep in separators:
                if sep in candidate:
                    parts = [p.strip() for p in candidate.split(sep) if p.strip()]
                    # Prefer the first part containing a degree suffix
                    preferred = None
                    degree_re = re.compile(r"\b(MSc|MA|MRes|MPhil|PhD|MBA|LLM|MEng)\b", re.IGNORECASE)
                    for p in parts:
                        if degree_re.search(p):
                            preferred = p
                            break
                    candidate = preferred or parts[0]
                    break

            # Drop junk tails like ": UCL" etc.
            lowered = candidate.lower()
            for marker in junk_markers:
                idx = lowered.find(marker)
                if idx != -1:
                    candidate = candidate[:idx].strip()
                    break

            # Normalize whitespace
            candidate = re.sub(r"\s+", " ", candidate).strip()
            return candidate

        # 1) Scan the first few lines for a concise "Title + Degree" pattern
        degree_pattern = re.compile(r"^(?P<title>.+?)\s+(?P<deg>MSc|MA|MRes|MPhil|PhD|MBA|LLM|MEng)\b", re.IGNORECASE)
        for raw in page_text.split('\n')[:12]:
            line = raw.strip()
            if not line:
                continue
            m = degree_pattern.search(line)
            if m:
                candidate = f"{m.group('title').strip()} {m.group('deg').upper()}"
                candidate = clean_candidate(candidate)
                if 5 <= len(candidate) <= 120:
                    return candidate
            # If not matched, still try to clean a line that obviously contains degree keywords
            if any(k in line.lower() for k in ['msc', 'mres', 'mphil', 'phd', 'mba', 'llm', 'meng']):
                candidate = clean_candidate(line)
                if 5 <= len(candidate) <= 120:
                    return candidate

        # 2) Fallback: derive from URL slug
        try:
            parsed = urlparse(url)
            segments = [s for s in parsed.path.split('/') if s and not s.isdigit()]
            if segments:
                slug = segments[-1]
                m = re.match(r"(?P<title>.+?)(?:-(?P<deg>msc|ma|mres|mphil|phd|mba|llm|meng))?$", slug, re.IGNORECASE)
                if m:
                    title_part = m.group('title').replace('-', ' ').replace('_', ' ').strip()
                    deg = m.group('deg')
                    # Title case with small words preserved
                    small = {'and','or','of','in','the','a','an','with','for','to'}
                    words = [w.lower() for w in title_part.split()]
                    tc = ' '.join(w.upper() if w.upper() in {'UCL'} else (w if w in small else w.capitalize()) for w in words)
                    candidate = tc
                    if deg:
                        candidate = f"{candidate} {deg.upper()}"
                    candidate = clean_candidate(candidate)
                    if 5 <= len(candidate) <= 120:
                        return candidate
        except Exception:
            pass

        # 3) Final fallback
        from datetime import datetime
        return f"Programme Rules {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    except Exception as e:
        logger.warning(f"Could not extract programme title: {e}")
        from datetime import datetime
        return f"Programme Rules {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"