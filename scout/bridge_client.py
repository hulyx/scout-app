"""Bridge client — adapter between collectors and the browser extension.

Each function tries the extension bridge first, falls back to
direct Python scraping if the bridge is unavailable.

Bridge execute() blocks the calling thread waiting for the
extension to open a tab, render JS, extract data, and post back.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_BRIDGE_ACTIONS = {
    "etsy":        "search_etsy",
    "redbubble":   "search_redbubble",
    "spreadshirt": "search_spreadshirt",
    "amazon_bsr":  "get_bsr",
    "amazon_search": "search_amazon",
    "pinterest":   "search_pinterest",
    "google_suggest": "get_google_suggest",
}


def _try_bridge(action: str, params: dict, timeout: int = 45) -> Optional[dict]:
    """Try to execute via extension bridge. Returns None if unavailable."""
    try:
        from scout.extension_bridge import get_bridge
        bridge = get_bridge()
        if bridge is None:
            return None
        return bridge.execute(action, params, timeout=timeout)
    except ImportError:
        return None
    except Exception:
        logger.debug("Bridge execution failed", exc_info=True)
        return None


# ── Etsy ──────────────────────────────────────────────────────


def _unwrap(raw: Optional[dict]) -> dict:
    """Unwrap extension response: raw = {status, data: {...}} → data dict."""
    if raw is None:
        return {}
    data = raw.get("data") or {}
    return data if isinstance(data, dict) else {}


def bridge_search_etsy(keyword: str) -> Optional[Dict[str, Any]]:
    """Search Etsy via extension bridge.

    Returns data in the same format as pod_etsy_scraper.scrape_etsy_search():
        {competition_count, top_listings, suggestions, avg_price}
    """
    raw = _try_bridge("search_etsy", {"query": keyword})
    if raw is None:
        return None
    data = _unwrap(raw)

    listings = data.get("listings") or []
    total = data.get("total_results") or 0
    prices = [l.get("price", 0) or 0 for l in listings if l.get("price")]
    avg_price = sum(prices) / len(prices) if prices else 0.0

    return {
        "competition_count": total,
        "top_listings": [
            {"title": l.get("title", ""), "price": l.get("price", 0)}
            for l in listings[:10]
        ],
        "suggestions": [],
        "avg_price": round(avg_price, 2),
    }


# ── Redbubble ─────────────────────────────────────────────────


def bridge_search_redbubble(keyword: str) -> Optional[Dict[str, Any]]:
    """Search Redbubble via extension bridge.

    Returns data in the same format as pod_redbubble_scraper.scrape_redbubble_search():
        {competition_count, top_works, suggestions, avg_price}
    """
    raw = _try_bridge("search_redbubble", {"query": keyword})
    if raw is None:
        return None
    data = _unwrap(raw)

    works = data.get("works") or data.get("listings") or []
    total = data.get("total_results") or 0
    prices = [w.get("price", 0) or 0 for w in works if w.get("price")]
    avg_price = sum(prices) / len(prices) if prices else 0.0

    return {
        "competition_count": total,
        "top_works": [
            {
                "title": w.get("title", ""),
                "price": w.get("price", 0),
                "artist": w.get("artist", ""),
            }
            for w in works[:10]
        ],
        "suggestions": [],
        "avg_price": round(avg_price, 2),
    }


# ── Spreadshirt ───────────────────────────────────────────────


def bridge_search_spreadshirt(keyword: str) -> Optional[Dict[str, Any]]:
    """Search Spreadshirt via extension bridge.

    Returns data in the same format as pod_spreadshirt_scraper.scrape_spreadshirt_search():
        {competition_count, top_designs, suggestions, spreadshirt_present}
    """
    raw = _try_bridge("search_spreadshirt", {"query": keyword})
    if raw is None:
        return None
    data = _unwrap(raw)

    designs = data.get("designs") or []
    total = data.get("total_results") or 0
    present = total > 0 or len(designs) > 0

    return {
        "competition_count": total,
        "top_designs": [
            {"title": d.get("title", ""), "price": d.get("price", 0)}
            for d in designs[:10]
        ],
        "suggestions": [],
        "spreadshirt_present": present,
    }


# ── Google Suggest (no tab needed, extension fetches API directly) ─


def bridge_google_suggest(keyword: str) -> list:
    """Get Google Suggest completions for a keyword via extension bridge.

    Falls back to direct Python HTTP if the bridge is unavailable.
    Returns a list of suggestion strings (empty list on total failure).
    """
    raw = _try_bridge("get_google_suggest", {"query": keyword}, timeout=10)
    if raw is not None:
        data = _unwrap(raw)
        sugs = data.get("suggestions") or []
        if sugs:
            return sugs
    # Fallback: direct Python HTTP
    try:
        from scout.collectors.pod_google_suggest import _fetch_google_suggest
        sugs = _fetch_google_suggest(keyword)
        return sugs if sugs else []
    except Exception:
        return []


# ── Trending pages (no keyword needed) ──────────────────────────


def bridge_trending_etsy() -> Optional[Dict[str, Any]]:
    """Scrape Etsy homepage trending/featured items."""
    raw = _try_bridge("etsy_trending", {}, timeout=30)
    if raw is None:
        return None
    data = _unwrap(raw)
    listings = data.get("listings") or []
    return {
        "platform": "etsy",
        "items": [{"title": l.get("title", ""), "price": l.get("price", 0)} for l in listings],
    }


def bridge_trending_redbubble() -> Optional[Dict[str, Any]]:
    """Scrape Redbubble popular page."""
    raw = _try_bridge("redbubble_popular", {}, timeout=30)
    if raw is None:
        return None
    data = _unwrap(raw)
    works = data.get("works") or data.get("listings") or []
    return {
        "platform": "redbubble",
        "items": [{"title": w.get("title", ""), "price": w.get("price", 0), "artist": w.get("artist", "")} for w in works],
    }


def bridge_trending_spreadshirt() -> Optional[Dict[str, Any]]:
    """Scrape Spreadshirt trending designs."""
    raw = _try_bridge("spreadshirt_trending", {}, timeout=30)
    if raw is None:
        return None
    data = _unwrap(raw)
    designs = data.get("designs") or []
    return {
        "platform": "spreadshirt",
        "items": [{"title": d.get("title", ""), "price": d.get("price", 0)} for d in designs],
    }


def bridge_trending_pinterest() -> Optional[Dict[str, Any]]:
    """Scrape Pinterest trending/ideas page."""
    raw = _try_bridge("pinterest_trending", {}, timeout=30)
    if raw is None:
        return None
    data = _unwrap(raw)
    pins = data.get("pins") or data.get("listings") or []
    return {
        "platform": "pinterest",
        "items": [{"title": p.get("title", ""), "source": "pinterest_trending"} for p in pins],
    }


def bridge_amazon_bestsellers() -> Optional[Dict[str, Any]]:
    """Scrape Amazon Best Sellers in Fashion."""
    raw = _try_bridge("amazon_bestsellers", {}, timeout=20)
    if raw is None:
        return None
    data = _unwrap(raw)
    listings = data.get("listings") or []
    return {
        "platform": "amazon",
        "items": [{"title": l.get("title", ""), "source": "amazon_bestseller"} for l in listings],
    }


def bridge_amazon_movers() -> Optional[Dict[str, Any]]:
    """Scrape Amazon Movers & Shakers in Fashion."""
    raw = _try_bridge("amazon_movers", {}, timeout=20)
    if raw is None:
        return None
    data = _unwrap(raw)
    listings = data.get("listings") or []
    return {
        "platform": "amazon",
        "items": [{"title": l.get("title", ""), "source": "amazon_mover"} for l in listings],
    }
