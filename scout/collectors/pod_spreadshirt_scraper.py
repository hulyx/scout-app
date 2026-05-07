"""
PodSpreadshirtScraper - Scrape Spreadshirt for POD competition data.
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import re


def scrape_spreadshirt_search(keyword: str, market: str = "com") -> Dict[str, Any]:
    """
    Scrape Spreadshirt search results for a keyword.
    market: 'com' for US, 'fr' for France, 'de' for Germany.
    Returns: {"competition_count": int, "top_designs": list, "suggestions": list}
    """
    result = {
        "competition_count": 0,
        "top_designs": [],
        "suggestions": [],
        "spreadshirt_present": False,
    }

    base = "spreadshirt.fr" if market == "fr" else ("spreadshirt.de" if market == "de" else "spreadshirt.com")
    url = f"https://www.{base}/shop/designs?q={requests.utils.quote(keyword)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Try to get result count
            count_selectors = [
                {"data-testid": "result-count"},
                {"class": re.compile(r"result.?count", re.I)},
            ]
            for sel in count_selectors:
                elem = soup.find(attrs=sel)
                if elem:
                    m = re.search(r"[\d,]+", elem.get_text())
                    if m:
                        result["competition_count"] = int(m.group().replace(",", ""))
                        break

            # Get top designs
            design_cards = soup.find_all("div", {"data-testid": re.compile(r"product.?card|design.?card", re.I)})[:10]
            if not design_cards:
                design_cards = soup.find_all("article")[:10]
            for card in design_cards:
                title_elem = card.find(["h2", "h3", "span"], {"data-testid": re.compile(r"title|name", re.I)})
                title = title_elem.get_text(strip=True) if title_elem else ""
                price_elem = card.find(string=re.compile(r"\d+[.,]\d+"))
                price = 0.0
                if price_elem:
                    m = re.search(r"(\d+)[.,](\d+)", price_elem)
                    if m:
                        try:
                            price = float(f"{m.group(1)}.{m.group(2)}")
                        except ValueError:
                            pass
                if title:
                    result["top_designs"].append({"title": title, "price": price})

            result["spreadshirt_present"] = result["competition_count"] > 0 or len(result["top_designs"]) > 0

    except Exception as e:
        print(f"Spreadshirt scrape error for '{keyword}': {e}")

    return result


if __name__ == "__main__":
    r = scrape_spreadshirt_search("cat lover")
    print(f"Competition: {r['competition_count']}, Designs: {len(r['top_designs'])}, Present: {r['spreadshirt_present']}")
