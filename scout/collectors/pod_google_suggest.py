"""
PodGoogleSuggest - Get Google Suggest queries for POD keywords.
Deep recursive mining with alphabetical expansion.
"""
import requests
from typing import List, Dict, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_suggestions(keyword: str, prefix_with_product: bool = True, depth: int = 2) -> List[Dict[str, Any]]:
    """
    Get Google Suggest suggestions for a keyword with recursive expansion.
    
    Args:
        keyword: Base keyword
        prefix_with_product: If True, also get suggestions with product prefixes
        depth: Recursion depth for expansion (1 = base only, 2 = base + first expansion)
    
    Returns:
        List of suggestion dicts with 'suggestion' key
    """
    results = []
    seen: Set[str] = set()
    
    # Base suggestions
    base_sugs = _fetch_google_suggest(keyword)
    for sug in base_sugs:
        if sug not in seen and len(sug) >= 3:
            seen.add(sug)
            results.append({"suggestion": sug, "source": "google_suggest"})
    
    # With product prefixes
    if prefix_with_product:
        products = ["t-shirt", "mug", "sticker", "gift for", "design", "funny"]
        for product in products:
            query = f"{product} {keyword}"
            product_sugs = _fetch_google_suggest(query)
            for sug in product_sugs:
                if sug not in seen and len(sug) >= 3:
                    seen.add(sug)
                    results.append({"suggestion": sug, "source": "google_suggest"})
    
    # Recursive expansion if depth > 1
    if depth > 1:
        new_seeds = list(seen)[:15]  # Limit to top 15 to avoid explosion
        expanded = _expand_recursively(new_seeds, seen, depth - 1)
        for exp in expanded:
            if exp not in seen:
                seen.add(exp)
                results.append({"suggestion": exp, "source": "google_suggest"})
    
    # Alphabetical expansion (a-z suffixes)
    alpha_expansions = _expand_alphabetically(keyword, seen)
    for exp in alpha_expansions:
        if exp not in seen:
            seen.add(exp)
            results.append({"suggestion": exp, "source": "google_suggest"})
    
    return results


def _expand_recursively(seeds: List[str], seen: Set[str], remaining_depth: int) -> List[str]:
    """Recursively expand seeds."""
    if remaining_depth <= 0 or not seeds:
        return []
    
    expanded = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        fut_map = {pool.submit(_fetch_google_suggest, seed): seed for seed in seeds}
        for f in as_completed(fut_map):
            try:
                results = f.result()
                for r in results:
                    if r not in seen and len(r) >= 3:
                        expanded.append(r)
                        seen.add(r)
            except Exception:
                pass
    
    # One more level if needed
    if remaining_depth > 1 and expanded:
        more = _expand_recursively(expanded[:10], seen, remaining_depth - 1)
        expanded.extend(more)
    
    return expanded


def _expand_alphabetically(base_keyword: str, seen: Set[str]) -> List[str]:
    """Expand with alphabetical suffixes (base + a, base + b, etc.)."""
    expanded = []
    letters = "abcdefghijklmnopqrstuvwxyz"
    
    def fetch_and_collect(query: str) -> List[str]:
        results = _fetch_google_suggest(query)
        return [r for r in results if r not in seen and len(r) >= 3]
    
    with ThreadPoolExecutor(max_workers=15) as pool:
        fut_map = {}
        # Suffixes: "cat a", "cat b", ...
        for letter in letters:
            query = f"{base_keyword} {letter}"
            fut_map[pool.submit(fetch_and_collect, query)] = query
        
        # Prefixes: "a cat", "b cat", ...
        for letter in letters:
            query = f"{letter} {base_keyword}"
            fut_map[pool.submit(fetch_and_collect, query)] = query
        
        for f in as_completed(fut_map):
            try:
                results = f.result()
                expanded.extend(results)
            except Exception:
                pass
    
    return expanded


def _fetch_google_suggest(query: str) -> List[str]:
    """Fetch suggestions from Google Suggest API with HTTPS, fallback, and robust parsing."""
    urls = [
        "https://suggestqueries.google.com/complete/search",
        "https://clients1.google.com/complete/search",
        "http://suggestqueries.google.com/complete/search",
    ]
    params = {
        "client": "firefox",
        "q": query,
        "hl": "en",
    }
    headers_list = [
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"},
        {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"},
    ]
    
    import random
    for attempt in range(3):
        url = urls[attempt % len(urls)]
        headers = random.choice(headers_list)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) >= 2:
                    suggestions = data[1]
                    if isinstance(suggestions, list):
                        return [str(s).strip() for s in suggestions if s and isinstance(s, str)]
                return []
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException as e:
            print(f"Request error (attempt {attempt+1}): {e}")
            continue
        except ValueError as e:
            print(f"JSON parse error (attempt {attempt+1}): {e}")
            continue
        except Exception as e:
            print(f"Unexpected error (attempt {attempt+1}): {e}")
            continue
    return []


if __name__ == "__main__":
    # Test deep mining
    sugs = get_suggestions("cat", depth=2)
    print(f"Found {len(sugs)} suggestions")
    for sug in sugs[:20]:
        print(f"  {sug['suggestion']}")
