"""
PodPinterestScraper - Scrape Pinterest for POD trends and niche discovery.
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import re
import json


def scrape_pinterest_search(keyword: str, mode: str = "all") -> Dict[str, Any]:
    """
    Scrape Pinterest for a keyword.
    
    Args:
        keyword: The keyword to search
        mode: 'suggest', 'boards', 'trending', 'all'
    
    Returns:
        Dict with suggestions, top_pins, top_boards, trending
    """
    result = {
        "suggestions": [],
        "top_pins": [],
        "top_boards": [],
        "trending": [],
        "pin_count_estimate": 0,
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    # Get autocomplete suggestions
    if mode in ["suggest", "all"]:
        try:
            suggest_url = "https://www.pinterest.com/api/v3/search/typeahead/"
            params = {
                "q": keyword,
                "scope": "boards",
                "count": 10,
            }
            resp = requests.get(suggest_url, params=params, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                suggestions = data.get('results', [])
                result["suggestions"] = [
                    {"suggestion": s.get('term', ''), "source": "pinterest_suggest"}
                    for s in suggestions if s.get('term')
                ]
        except Exception:
            pass
        
        # Fallback: try another endpoint
        if not result["suggestions"]:
            try:
                suggest_url2 = "https://www.pinterest.com/autocomplete/pins/"
                params2 = {"q": keyword}
                resp2 = requests.get(suggest_url2, params=params2, headers=headers, timeout=5)
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    suggestions2 = data2.get('suggestions', [])
                    result["suggestions"] = [
                        {"suggestion": s.get('phrase', ''), "source": "pinterest_suggest"}
                        for s in suggestions2 if s.get('phrase')
                    ]
            except Exception:
                pass
    
    # Search Pinterest
    if mode in ["boards", "all"]:
        try:
            search_url = f"https://www.pinterest.com/search/boards/?q={keyword}"
            resp = requests.get(search_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Try to extract boards
                board_elements = soup.find_all('div', {'data-test-id': 'board-card'})[:10]
                for board_elem in board_elements:
                    name_elem = board_elem.find('h3')
                    name = name_elem.text.strip() if name_elem else ''
                    
                    followers_elem = board_elem.find('span', class_='follower-count')
                    followers = 0
                    if followers_elem:
                        followers_text = followers_elem.text.strip()
                        # Parse "1.2K" -> 1200
                        if 'K' in followers_text:
                            followers = int(float(followers_text.replace('K', '')) * 1000)
                        elif 'M' in followers_text:
                            followers = int(float(followers_text.replace('M', '')) * 1000000)
                        else:
                            try:
                                followers = int(followers_text.replace(',', ''))
                            except ValueError:
                                pass
                    
                    result["top_boards"].append({
                        "board_name": name,
                        "followers": followers,
                        "pin_count": 0,  # Hard to extract from search
                    })
                
                # Estimate total pins
                count_elem = soup.find('meta', {'name': 'description'})
                if count_elem:
                    content = count_elem.get('content', '')
                    match = re.search(r'([,\d]+)\s+results', content)
                    if match:
                        result["pin_count_estimate"] = int(match.group(1).replace(',', ''))
        
        except Exception as e:
            print(f"Error scraping Pinterest search: {e}")
    
    # Get trending (simplified)
    if mode in ["trending", "all"]:
        try:
            trending_url = "https://www.pinterest.com/today/"
            resp = requests.get(trending_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                # Placeholder - real implementation would parse trending categories
                result["trending"] = [
                    {"trend": "Whimsical Art", "category": "Art"},
                    {"trend": "Quote Typography", "category": "Typography"},
                    {"trend": "Cute Animal Stickers", "category": "Stickers"},
                ]
        except Exception:
            pass
    
    return result


def get_pinterest_boards(keyword: str) -> List[Dict[str, Any]]:
    """Get Pinterest boards related to a keyword."""
    result = scrape_pinterest_search(keyword, mode="boards")
    return result.get("top_boards", [])


if __name__ == "__main__":
    # Test
    result = scrape_pinterest_search("cat lover", mode="all")
    print(f"Suggestions: {len(result['suggestions'])}")
    print(f"Boards: {len(result['top_boards'])}")
    print(f"Pin estimate: {result['pin_count_estimate']}")
