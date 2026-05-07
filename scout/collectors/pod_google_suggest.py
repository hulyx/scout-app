"""
PodGoogleSuggest - Get Google Suggest queries for POD keywords.
"""
import requests
from typing import List, Dict, Any


def get_suggestions(keyword: str, prefix_with_product: bool = True) -> List[Dict[str, Any]]:
    """
    Get Google Suggest suggestions for a keyword.
    Optionally prefix with product types (t-shirt, mug, etc.).
    
    Args:
        keyword: Base keyword
        prefix_with_product: If True, also get suggestions with product prefixes
    
    Returns:
        List of suggestion dicts with 'suggestion' key
    """
    results = []
    seen = set()
    
    # Base suggestions
    base_sugs = _fetch_google_suggest(keyword)
    for sug in base_sugs:
        if sug not in seen:
            seen.add(sug)
            results.append({"suggestion": sug, "source": "google_suggest"})
    
    # With product prefixes
    if prefix_with_product:
        products = ["t-shirt", "mug", "sticker", "gift for", "design"]
        for product in products:
            query = f"{product} {keyword}"
            product_sugs = _fetch_google_suggest(query)
            for sug in product_sugs:
                if sug not in seen:
                    seen.add(sug)
                    results.append({"suggestion": sug, "source": "google_suggest"})
    
    return results


def _fetch_google_suggest(query: str) -> List[str]:
    """Fetch suggestions from Google Suggest API."""
    url = "http://suggestqueries.google.com/complete/search"
    params = {
        "client": "firefox",
        "q": query,
        "hl": "en",
    }
    
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            suggestions = data[1] if len(data) > 1 else []
            return suggestions
    except Exception as e:
        print(f"Error fetching Google Suggest: {e}")
    return []


if __name__ == "__main__":
    # Test
    sugs = get_suggestions("nurse")
    print(f"Found {len(sugs)} suggestions")
    for sug in sugs[:10]:
        print(f"  {sug['suggestion']}")
