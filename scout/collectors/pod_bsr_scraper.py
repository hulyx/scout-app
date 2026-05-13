"""BSR scraper for Amazon Merch (POD) products.

Parses server-rendered Amazon product pages to extract the
Best Sellers Rank for POD-relevant categories (Clothing,
Home & Kitchen, etc.). Falls back to multiple selectors
since Amazon frequently changes its DOM.
"""

import re
import logging
from typing import Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

from scout.http_client import create_session

logger = logging.getLogger(__name__)

POD_BSR_PRODUCT_URL = "https://www.amazon.com/dp/{asin}"

# POD-relevant BSR categories we care about (keywords in the BSR text)
POD_BSR_CATEGORIES = [
    "clothing", "shoes", "jewelry", "accessories", "apparel",
    "home", "kitchen", "dining", "bedding", "bath",
    "office", "wall art", "poster", "print", "calendar",
    "novelty", "collectible", "gift", "toy", "game",
    "sports", "outdoor", "fitness", "luggage", "travel",
]


def _is_pod_relevant_bsr(bsr_text: str) -> bool:
    """Check if a BSR line is for a POD-relevant category."""
    lower = bsr_text.lower()
    if any(cat in lower for cat in POD_BSR_CATEGORIES):
        return True
    # Generic "Best Sellers Rank" without specific category is also relevant
    # (it usually defaults to the product's main category)
    if "best sellers rank" in lower:
        return True
    return False


def _extract_bsr_from_soup(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Try multiple strategies to extract BSR from parsed HTML.

    Amazon serves BSR in several possible locations depending on
    page layout version. Returns the FIRST POD-relevant BSR found.
    """

    # Strategy 1: #detailBullets_feature_div (modern layout)
    detail_bullets = soup.select_one("#detailBullets_feature_div")
    if detail_bullets:
        for li in detail_bullets.select("li"):
            text = li.get_text(" ", strip=True)
            if _is_pod_relevant_bsr(text):
                m = re.search(r"#(\d[\d,]*)", text)
                if m:
                    bsr = int(m.group(1).replace(",", ""))
                    return {"bsr": bsr, "source": "detailBullets", "text": text[:200]}

    # Strategy 2: #productDetails_detailBullets (classic layout)
    prod_details = soup.select_one("#productDetails_detailBullets")
    if prod_details:
        for tr in prod_details.select("tr"):
            text = tr.get_text(" ", strip=True)
            if _is_pod_relevant_bsr(text):
                m = re.search(r"#(\d[\d,]*)", text)
                if m:
                    bsr = int(m.group(1).replace(",", ""))
                    return {"bsr": bsr, "source": "productDetails", "text": text[:200]}

    # Strategy 3: .a-section .a-spacing-small (ASIN page sometimes)
    for section in soup.select(".a-section.a-spacing-small"):
        text = section.get_text(" ", strip=True)
        if "best sellers rank" in text.lower():
            m = re.search(r"#(\d[\d,]*)", text)
            if m:
                bsr = int(m.group(1).replace(",", ""))
                return {"bsr": bsr, "source": "a-section", "text": text[:200]}

    # Strategy 4: Any span/div with BSR pattern
    for tag in soup.find_all(["span", "div", "li"]):
        text = tag.get_text(" ", strip=True)
        if "best sellers rank" in text.lower() and _is_pod_relevant_bsr(text):
            m = re.search(r"#(\d[\d,]*)", text)
            if m:
                bsr = int(m.group(1).replace(",", ""))
                return {"bsr": bsr, "source": "generic", "text": text[:200]}

    return None


def scrape_pod_bsr(asin: str) -> Dict[str, Any]:
    """Scrape BSR for an Amazon Merch product by ASIN.

    Args:
        asin: Amazon ASIN (e.g. B09XYZ1234).

    Returns:
        Dict with:
            - bsr: int or None
            - category: str or None
            - title: str (product title)
            - price: float or None
            - estimated_sales: float (daily sales estimate)
        Returns {"bsr": None, ...} on failure.
    """
    url = POD_BSR_PRODUCT_URL.format(asin=asin)
    try:
        session = create_session()
        resp = session.get(url, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Product title
        title = None
        for sel in ["#productTitle", "#title", "h1.a-size-large"]:
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                break

        # Price
        price = None
        price_el = soup.select_one(".a-price .a-offscreen")
        if price_el:
            m = re.search(r"[\d.]+", price_el.get_text(strip=True))
            if m:
                price = float(m.group())

        # BSR
        bsr_data = _extract_bsr_from_soup(soup)

        if bsr_data:
            daily = estimate_pod_daily_sales(bsr_data["bsr"])
        else:
            daily = 0.0

        return {
            "asin": asin,
            "title": title or "Unknown",
            "price": price,
            "bsr": bsr_data["bsr"] if bsr_data else None,
            "bsr_category": bsr_data["text"] if bsr_data else None,
            "estimated_daily_sales": round(daily, 1),
            "estimated_monthly_sales": round(daily * 30, 0),
        }

    except requests.RequestException as e:
        logger.warning(f"Failed to scrape {asin}: {e}")
        return {"asin": asin, "title": None, "price": None, "bsr": None,
                "bsr_category": None, "estimated_daily_sales": 0.0,
                "estimated_monthly_sales": 0}

    except Exception as e:
        logger.error(f"Error scraping {asin}: {e}", exc_info=True)
        return {"asin": asin, "title": None, "price": None, "bsr": None,
                "bsr_category": None, "estimated_daily_sales": 0.0,
                "estimated_monthly_sales": 0}


# ── POD BSR → Sales estimation ────────────────────────────────
# Calibrated for Clothing / Home & Kitchen categories (not books).
# Sources: JungleScout, Helium10 public data, seller forum reports.
POD_BSR_MODELS = {
    "clothing":       {"k": 35000,  "a": 0.72},
    "home_kitchen":   {"k": 45000,  "a": 0.74},
    "accessories":    {"k": 30000,  "a": 0.70},
    "default":        {"k": 25000,  "a": 0.70},
}


def _detect_pod_category(bsr_text: str) -> str:
    lower = bsr_text.lower()
    if any(c in lower for c in ["clothing", "shoes", "apparel", "fashion"]):
        return "clothing"
    if any(c in lower for c in ["home", "kitchen", "dining", "bedding"]):
        return "home_kitchen"
    if any(c in lower for c in ["accessories", "jewelry", "watch", "bag"]):
        return "accessories"
    return "default"


def estimate_pod_daily_sales(bsr: int, category: str = "default") -> float:
    """Estimate daily sales for a POD product from its BSR.

    Uses a power-law model: daily_sales = k * bsr^(-a)
    Calibrated for Amazon Merch / POD categories.

    Args:
        bsr: Best Sellers Rank (>= 1).
        category: One of "clothing", "home_kitchen", "accessories", "default".

    Returns:
        Estimated daily sales as a float.
    """
    if bsr is None or bsr < 1:
        return 0.0
    model = POD_BSR_MODELS.get(category, POD_BSR_MODELS["default"])
    daily = model["k"] * (bsr ** -model["a"])
    return round(daily, 2)


def estimate_pod_monthly_revenue(bsr: int, price: float,
                                  category: str = "default",
                                  royalty: float = 0.15) -> float:
    """Estimate monthly royalty revenue for a POD product.

    Amazon Merch royalty is ~15% of sale price (varies by product type).
    """
    if bsr is None or bsr < 1 or not price:
        return 0.0
    daily = estimate_pod_daily_sales(bsr, category)
    return round(daily * 30 * price * royalty, 2)


SCRAPE_RATE_LIMIT = 1.0  # seconds between requests
