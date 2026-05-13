"""
PodRedbubbleScraper - Scrape Redbubble for POD keywords and competition data.
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import re


def scrape_redbubble_search(keyword: str) -> Dict[str, Any]:
    """
    Scrape Redbubble search results for a keyword.

    Tries the browser extension bridge first (renders JS properly).
    Falls back to direct HTTP scraping if bridge unavailable.

    Returns:
        Dict with competition_count, top_works, suggestions, avg_price
    """
    try:
        from scout.bridge_client import bridge_search_redbubble
        bridge_result = bridge_search_redbubble(keyword)
        if bridge_result is not None:
            return bridge_result
    except Exception:
        pass

    result = {
        "competition_count": 0,
        "top_works": [],
        "suggestions": [],
        "avg_price": 0.0,
    }
    
    # Search page
    search_url = "https://www.redbubble.com/shop/"
    params = {
        "query": keyword,
        "iaCode": "u-tshirts",  # Default to t-shirts
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        resp = requests.get(search_url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Try to get result count
            count_elem = soup.find('span', class_='ResultCount')
            if count_elem:
                text = count_elem.text.strip()
                match = re.search(r'([,\d]+)\s+results', text)
                if match:
                    result["competition_count"] = int(match.group(1).replace(',', ''))
            
            # Get top works
            works = soup.find_all('div', {'data-test-id': 'work-card'})[:10]
            prices = []
            for work in works:
                title_elem = work.find('h2')
                title = title_elem.text.strip() if title_elem else ''
                
                price_elem = work.find('span', class_='price')
                price = 0.0
                if price_elem:
                    try:
                        price = float(price_elem.text.strip().replace('$', ''))
                        prices.append(price)
                    except ValueError:
                        pass
                
                artist_elem = work.find('a', class_='artist-link')
                artist = artist_elem.text.strip() if artist_elem else ''
                
                result["top_works"].append({
                    "title": title,
                    "price": price,
                    "artist": artist,
                })
            
            if prices:
                result["avg_price"] = sum(prices) / len(prices)
        
    except Exception as e:
        print(f"Error scraping Redbubble: {e}")
    
    # Get autocomplete suggestions
    try:
        suggest_url = "https://www.redbubble.com/suggestions.json"
        suggest_params = {"query": keyword}
        resp = requests.get(suggest_url, params=suggest_params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            suggestions = data.get('suggestions', [])
            result["suggestions"] = [{"suggestion": s.get('text', '')} for s in suggestions if s.get('text')]
    except Exception:
        pass
    
    return result


if __name__ == "__main__":
    # Test
    result = scrape_redbubble_search("cat lover")
    print(f"Competition: {result['competition_count']}")
    print(f"Avg Price: ${result['avg_price']:.2f}")
    print(f"Suggestions: {len(result['suggestions'])}")
