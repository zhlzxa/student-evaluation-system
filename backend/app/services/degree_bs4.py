from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
import pycountry


CLASS_KEYS = {
    "FIRST": ["first-class", "first class", "first-class honours", "first-class degree", "first"],
    "UPPER_SECOND": ["upper second-class", "upper second class", "2:1", "2.1", "second higher", "upper second"],
    "LOWER_SECOND": ["lower second-class", "lower second class", "2:2", "2.2", "second lower", "lower second"],
}


def fetch_html(url: str, timeout: int = 60) -> str:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def parse_country_requirements(url: str, country_name: Optional[str] = None) -> Dict[str, str]:
    """Parse a single country page and extract text snippets per UK class.

    Heuristic: scan paragraphs and list items for keyword patterns associated
    with FIRST, UPPER_SECOND (2:1), LOWER_SECOND (2:2). Collect text snippets.
    If no class-specific text is identified, return an empty dict.
    """
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # If a country name is provided, try to locate a section headed by that name
    container = soup
    if country_name:
        name_lc = country_name.strip().lower()
        # search headings that contain the country name
        for header in soup.find_all(["h1", "h2", "h3", "h4"]):
            if name_lc in header.get_text(" ", strip=True).lower():
                # collect siblings until next heading of same or higher level
                section_nodes: List = []
                for sib in header.next_siblings:
                    if getattr(sib, "name", None) in {"h1", "h2", "h3", "h4"}:
                        break
                    section_nodes.append(sib)
                # build a temporary soup from collected nodes
                tmp_html = "".join(str(n) for n in section_nodes)
                container = BeautifulSoup(tmp_html, "html.parser")
                break

    texts: List[str] = []
    for tag in container.find_all(["p", "li", "dd", "dt"]):
        t = tag.get_text(" ", strip=True)
        if t:
            texts.append(t)

    results: Dict[str, List[str]] = {k: [] for k in CLASS_KEYS.keys()}
    for t in texts:
        lt = t.lower()
        for cls, patterns in CLASS_KEYS.items():
            if any(p in lt for p in patterns):
                results[cls].append(t)

    # Flatten lists to joined text; drop empty
    flattened: Dict[str, str] = {}
    for cls, arr in results.items():
        if arr:
            # de-duplicate while preserving order
            seen = set()
            uniq = []
            for s in arr:
                if s not in seen:
                    uniq.append(s)
                    seen.add(s)
            flattened[cls] = "\n".join(uniq)

    return flattened


def _to_iso3(name: str) -> Optional[str]:
    base = name.split("(")[0].split("/")[0].strip()
    try:
        # Try direct lookup
        c = pycountry.countries.lookup(base)
        return c.alpha_3
    except Exception:
        # Try fuzzy search
        try:
            cand = pycountry.countries.search_fuzzy(base)[0]
            return cand.alpha_3
        except Exception:
            return None


def _find_heading_table(soup: BeautifulSoup, heading_text: str) -> Optional[BeautifulSoup]:
    # Find heading h1-h4 with text contains heading_text (case-insensitive), then next table
    target = None
    ht = heading_text.strip().lower()
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if ht in h.get_text(" ", strip=True).lower():
            target = h
            break
    if not target:
        return None
    table = target.find_next("table")
    return table


def parse_all_tables(url: str) -> List[Dict[str, Dict[str, object]]]:
    """Parse the three main tables and return a list of items:
    [
      {
        country_name,
        country_code_iso3,
        classes: {
          FIRST|UPPER_SECOND|LOWER_SECOND: { "text": str, ["other": str] }
        }
      }
    ]
    """
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    heading_map = {
        "Second Higher": "UPPER_SECOND",
        "Second Lower": "LOWER_SECOND",
        "Above Honours": "FIRST",
    }

    # country_name -> {uk_class: text}
    collected: Dict[str, Dict[str, Dict[str, str]]] = {}

    for heading, uk_class in heading_map.items():
        table = _find_heading_table(soup, heading)
        if not table:
            continue
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            # Skip header rows
            if not tds or len(tds) < 2:
                continue
            # detect header by 'Country' keyword
            first_text = tds[0].get_text(" ", strip=True)
            if first_text.lower() in {"country", "countries"}:
                continue
            country = first_text.strip()
            # Column 2: requirement text
            req_cell = tds[1]
            req_parts: List[str] = []
            for li in req_cell.find_all("li"):
                txt = li.get_text(" ", strip=True)
                if txt:
                    req_parts.append(txt)
            if not req_parts:
                txt = req_cell.get_text(" ", strip=True)
                if txt:
                    req_parts.append(txt)
            if not req_parts:
                continue
            req_block = "\n".join(dict.fromkeys(req_parts))

            # Column 3 (if present): other qualifications
            other_block = None
            if len(tds) >= 3:
                other_cell = tds[2]
                other_parts: List[str] = []
                for li in other_cell.find_all("li"):
                    txt = li.get_text(" ", strip=True)
                    if txt:
                        other_parts.append(txt)
                if not other_parts:
                    txt = other_cell.get_text(" ", strip=True)
                    if txt:
                        other_parts.append(txt)
                if other_parts:
                    other_block = "\n".join(dict.fromkeys(other_parts))

            if country not in collected:
                collected[country] = {}
            requirement: Dict[str, str] = {"text": req_block}
            if other_block:
                requirement["other"] = other_block
            collected[country][uk_class] = requirement

    items: List[Dict[str, Dict[str, object]]] = []
    for country_name, classes in collected.items():
        iso3 = _to_iso3(country_name) or ""
        items.append({
            "country_name": country_name,
            "country_code_iso3": iso3,
            "classes": classes,
        })

    return items
