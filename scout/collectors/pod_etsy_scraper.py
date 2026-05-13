"""
PodEtsyScraper - Scrape Etsy for POD keywords and competition data.
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import re


def scrape_etsy_search(keyword: str) -> Dict[str, Any]:
    """
    Scrape Etsy search results for a keyword.

    Tries the browser extension bridge first (renders JS properly).
    Falls back to direct HTTP scraping if bridge unavailable.

    Returns:
        Dict with competition_count, top_listings, suggestions, avg_price
    """
    try:
        from scout.bridge_client import bridge_search_etsy
        bridge_result = bridge_search_etsy(keyword)
        if bridge_result is not None:
            return bridge_result
    except Exception:
        pass

    result = {
        "competition_count": 0,
        "top_listings": [],
        "suggestions": [],
        "avg_price": 0.0,
    }
    
    # Search page
    search_url = "https://www.etsy.com/search"
    params = {
        "q": keyword,
        "ref": "search_bar",
        "is_personalizable": "true",
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
            count_elem = soup.find('meta', {'name': 'description'})
            if count_elem:
                content = count_elem.get('content', '')
                match = re.search(r'([,\d]+)\s+results', content)
                if match:
                    result["competition_count"] = int(match.group(1).replace(',', ''))
            
            # Get top listings
            listings = soup.find_all('div', {'data-listing-id': True})[:10]
            prices = []
            for listing in listings:
                title_elem = listing.find('h3')
                title = title_elem.text.strip() if title_elem else ''
                
                price_elem = listing.find('span', class_='currency-value')
                price = 0.0
                if price_elem:
                    try:
                        price = float(price_elem.text.strip())
                        prices.append(price)
                    except ValueError:
                        pass
                
                result["top_listings"].append({
                    "title": title,
                    "price": price,
                })
            
            if prices:
                result["avg_price"] = sum(prices) / len(prices)
        
    except Exception as e:
        print(f"Error scraping Etsy: {e}")
    
    # Get autocomplete suggestions
    try:
        suggest_url = "https://www.etsy.com/api/v3/ajax/bespoke/public/neu/specs/search_bar_autosuggest"
        suggest_params = {
            "q": keyword,
            "language": "en",
            "limit": 10,
        }
        resp = requests.get(suggest_url, params=suggest_params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            suggestions = data.get('results', [])
            result["suggestions"] = [{"suggestion": s.get('phrase', '')} for s in suggestions if s.get('phrase')]
    except Exception:
        pass
    
    return result


if __name__ == "__main__":
    # Test
    result = scrape_etsy_search("cat lover")
    print(f"Competition: {result['competition_count']}")
    print(f"Avg Price: ${result['avg_price']:.2f}")
    print(f"Suggestions: {len(result['suggestions'])}")
