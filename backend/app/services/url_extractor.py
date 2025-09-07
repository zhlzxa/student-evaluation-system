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
        # Look for common programme title patterns in first few lines
        lines = page_text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for Master's or MSc programmes
            if any(keyword in line.lower() for keyword in ['msc', 'master', 'ma ', 'mres', 'programme', 'degree']):
                # Clean up the line
                title = line.replace('|', ' ').replace(' - UCL', '').replace(' | UCL', '').strip()
                if len(title) > 10 and len(title) < 200:  # Reasonable length
                    return title
        
        # Fallback: try to extract from URL
        if 'programmes' in url.lower() or 'courses' in url.lower():
            url_parts = url.split('/')
            for part in reversed(url_parts):
                if part and not part.isdigit() and len(part) > 3:
                    # Clean up URL part
                    title = part.replace('-', ' ').replace('_', ' ').title()
                    if len(title) > 5:
                        return f"{title} Programme"
        
        # Final fallback
        from datetime import datetime
        return f"Programme Rules {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
    except Exception as e:
        logger.warning(f"Could not extract programme title: {e}")
        from datetime import datetime
        return f"Programme Rules {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"