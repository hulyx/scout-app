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
    """Fetch suggestions using googlesearch-python library to bypass SSL blocks."""
    try:
        from googlesearch import search
        # Use the search library which handles redirects and SSL better
        # We only need a few results to extract suggestions from titles/snippets
        results = []
        try:
            # Search for the query and extract related terms from results
            search_results = list(search(query, num_results=5, lang="en", timeout=5))
            for url in search_results:
                # Extract potential keywords from URL structure
                if "google.com/search" in url or "youtu.be" not in url:
                    # Clean URL to get meaningful phrases
                    parts = url.replace("https://", "").replace("http://", "").split("/")
                    for part in parts:
                        clean = part.replace("-", " ").replace("_", " ").strip()
                        if len(clean) > 3 and query.lower() in clean.lower():
                            results.append(clean.title())
        except Exception as e:
            pass
        
        # Fallback: try direct API with aggressive retry and different client
        if not results:
            results = _fetch_direct_api(query)
        
        return list(set([r.strip() for r in results if len(r) >= 3]))
    except Exception:
        return _fetch_direct_api(query)


def _fetch_direct_api(query: str) -> List[str]:
    """Direct API fetch with multiple clients and aggressive retry logic."""
    # Try different client types that are less blocked
    clients = [
        ("chrome", "firefox"),
        ("chrome", "chrome"),
        ("firefox", "firefox"),
        ("gws", "firefox"),  # Google Web Search
        ("serp", "chrome"),
    ]
    
    urls = [
        "https://www.google.com/complete/search",
        "https://suggestqueries.google.com/complete/search",
    ]
    
    headers_list = [
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"},
        {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"},
        {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:133.0) Gecko/20100101 Firefox/133.0", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"},
        {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", "Accept": "*/*"},
    ]
    
    import random
    import time
    
    for attempt in range(5):  # More retries
        client_name, cb_name = random.choice(clients)
        url = random.choice(urls)
        headers = random.choice(headers_list)
        
        params = {
            "q": query,
            "client": client_name,
            "cp": cb_name,
            "gs_ri": "hp",
            "xhr": "t",
            "xssi": "t",
            "hl": "en",
        }
        
        try:
            session = requests.Session()
            session.headers.update(headers)
            resp = session.get(url, params=params, timeout=8)
            
            if resp.status_code == 200:
                text = resp.text
                # Handle JSONP response (starts with ")]}'\n")
                if text.startswith(")]}'"):
                    text = text[4:]
                elif text.startswith(")]}'\n"):
                    text = text[5:]
                
                import json
                data = json.loads(text)
                if isinstance(data, list) and len(data) >= 2:
                    suggestions = data[1]
                    if isinstance(suggestions, list):
                        extracted = []
                        for s in suggestions:
                            if isinstance(s, str):
                                extracted.append(s.strip())
                            elif isinstance(s, list) and len(s) > 0:
                                extracted.append(str(s[0]).strip())
                        return extracted
                return []
        except Exception as e:
            if attempt < 4:
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
            continue
    
    return []


if __name__ == "__main__":
    # Test deep mining
    sugs = get_suggestions("cat", depth=2)
    print(f"Found {len(sugs)} suggestions")
    for sug in sugs[:20]:
        print(f"  {sug['suggestion']}")
