"""Collector for NicheBloom — scrapes 100 curated POD niches + detail pages.

All pages are server-rendered (Next.js), no JS required for static data.
The AI idea generator requires auth, so we don't attempt to scrape it.
"""

import logging
import re
from typing import Dict, List, Optional, Any

import requests
from bs4 import BeautifulSoup

from scout.http_client import create_session

logger = logging.getLogger(__name__)

NICHEBLOOM_URL = "https://www.nichebloom.pro"
LIST_URL = NICHEBLOOM_URL + "/"
DETAIL_URL = NICHEBLOOM_URL + "/trend/{niche_id}"

# Bloom score level names — extracted from the site's class patterns
BLOOM_LEVELS = {
    "Peak Demand": 5,
    "Thriving": 4,
    "Blooming": 3,
    "Growing": 2,
    "Sprouting": 1,
}


def _soup(url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
    try:
        session = create_session()
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def scrape_niche_list() -> List[Dict[str, Any]]:
    """Scrape the 100 curated niches from the NicheBloom homepage.

    Returns a list of dicts with keys:
        id, name, category, bloom_level, bloom_score, description, url
    """
    soup = _soup(LIST_URL)
    if soup is None:
        return []

    niches = []
    # Each niche card is an <a> with href="/trend/{id}"
    for a_tag in soup.select("a[href^='/trend/']"):
        href = a_tag.get("href", "")
        m = re.search(r"/trend/(\d+)", href)
        if not m:
            continue
        niche_id = int(m.group(1))

        # Category pill
        cat_el = a_tag.select_one(
            "span.inline-flex.items-center.rounded-full.bg-indigo-500\\/10"
        )
        category = cat_el.get_text(strip=True) if cat_el else ""

        # Bloom score pill
        bloom_el = a_tag.select_one(
            "div.inline-flex.items-center.gap-1\\.5.rounded-full.border"
        )
        bloom_text = bloom_el.get_text(" ", strip=True) if bloom_el else ""
        bloom_level = ""
        bloom_score = 0
        for level_name, score in BLOOM_LEVELS.items():
            if level_name in bloom_text:
                bloom_level = level_name
                bloom_score = score
                break

        # Title
        title_el = a_tag.select_one("h3")
        title = title_el.get_text(strip=True) if title_el else ""

        # Description
        desc_el = a_tag.select_one("p.text-slate-400")
        desc = desc_el.get_text(strip=True) if desc_el else ""

        if title:
            niches.append({
                "id": niche_id,
                "name": title,
                "category": category,
                "bloom_level": bloom_level,
                "bloom_score": bloom_score,
                "description": desc,
                "url": f"{NICHEBLOOM_URL}/trend/{niche_id}",
            })

    return niches


def _extract_str(soup: BeautifulSoup, selector: str) -> str:
    el = soup.select_one(selector)
    return el.get_text(strip=True) if el else ""


def scrape_niche_detail(niche_id: int) -> Dict[str, Any]:
    """Scrape a single niche detail page for enriched data.

    Returns a dict with keys:
        id, name, description, category, bloom_level, bloom_score,
        starter_ideas (list), strategy (dict with category, best_use,
        design_angle, monetization_note)
    """
    url = DETAIL_URL.format(niche_id=niche_id)
    soup = _soup(url)
    if soup is None:
        return {"id": niche_id, "error": "Failed to fetch"}

    result: Dict[str, Any] = {"id": niche_id}

    # Name
    result["name"] = _extract_str(soup, "h1")

    # Description
    desc_el = soup.select_one("p.text-slate-300.text-lg")
    result["description"] = desc_el.get_text(strip=True) if desc_el else ""

    # Category pill
    cat_el = soup.select_one(
        "span.inline-flex.items-center.rounded-full.bg-indigo-500\\/15"
    )
    result["category"] = cat_el.get_text(strip=True) if cat_el else ""

    # Bloom score
    bloom_el = soup.select_one(
        "div.inline-flex.items-center.gap-1\\.5.rounded-full.border"
    )
    if bloom_el:
        bloom_text = bloom_el.get_text(" ", strip=True)
        for level_name, score in BLOOM_LEVELS.items():
            if level_name in bloom_text:
                result["bloom_level"] = level_name
                result["bloom_score"] = score
                break

    # Starter Ideas — divs inside the "Starter Ideas" section
    starter_section = soup.find("h2", string=re.compile(r"Starter Ideas", re.I))
    if starter_section:
        parent = starter_section.find_parent("div", class_="rounded-2xl")
        if parent:
            idea_divs = parent.select("div.rounded-2xl.border")
            result["starter_ideas"] = [
                d.get_text(strip=True) for d in idea_divs if d.get_text(strip=True)
            ]
        else:
            result["starter_ideas"] = []
    else:
        result["starter_ideas"] = []

    # Strategy section — "Why this niche works"
    strategy_blocks = soup.select(
        "div.rounded-2xl.border.border-white\\/5.bg-\\[\\#060d1a\\].p-4"
    )
    if strategy_blocks:
        strategy = {}
        for block in strategy_blocks:
            label_el = block.select_one("p.text-sm.uppercase")
            value = block.get_text(separator="\n", strip=True)
            if label_el:
                label = label_el.get_text(strip=True).lower().replace(" ", "_")
                # Remove the label from the text to get just the value
                val = value[len(label_el.get_text(strip=True)):].strip()
                strategy[label] = val if val else block.get_text(separator=" ", strip=True)
            else:
                strategy["note"] = block.get_text(separator=" ", strip=True)
        result["strategy"] = strategy
    else:
        result["strategy"] = {}

    result["url"] = f"{NICHEBLOOM_URL}/trend/{niche_id}"
    return result
