"""
PodMerchAutocomplete - Mine keywords from Amazon Merch autocomplete.
Uses a dedicated event loop per call to avoid conflicts with Qt's event loop.
"""
import asyncio
import threading
import aiohttp
from typing import List, Dict, Any


async def fetch_merch_suggestions(session, seed: str, marketplace: str = "us", product_type: str = "t-shirts") -> List[Dict[str, Any]]:
    """Fetch autocomplete suggestions from Amazon Merch."""
    domain_map = {
        "us": "amazon.com", "uk": "amazon.co.uk", "de": "amazon.de",
        "fr": "amazon.fr", "ca": "amazon.ca", "au": "amazon.com.au",
        "jp": "amazon.co.jp", "it": "amazon.it", "es": "amazon.es",
    }
    domain = domain_map.get(marketplace, "amazon.com")

    aliases = ["merch-shirts", "merch-hoodies", "merch-pop"]
    if product_type == "t-shirt":
        aliases = ["merch-t-shirts", "merch-shirts"]
    elif product_type == "mug":
        aliases = ["merch-mugs"]
    elif product_type == "sticker":
        aliases = ["merch-stickers"]
    elif product_type == "poster":
        aliases = ["merch-posters"]

    results = []
    for alias in aliases[:1]:
        url = f"https://completion.{domain}/api/2017/suggestions"
        params = {
            "mid": "ATVPDKIKX0DER",
            "alias": alias,
            "search-alias": alias,
            "mkt": "1",
            "q": seed,
        }
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    suggestions = data.get("suggestions", [])
                    for i, sug in enumerate(suggestions, 1):
                        keyword = sug.get("value", "").strip()
                        if keyword:
                            results.append({
                                "keyword": keyword,
                                "position": i,
                                "source": "merch_autocomplete",
                                "marketplace": marketplace,
                                "product_type": product_type,
                            })
        except Exception as e:
            print(f"Error fetching Merch suggestions for '{seed}': {e}")
    return results


async def expand_keyword(session, seed: str, marketplace: str, product_type: str, depth: int) -> List[Dict[str, Any]]:
    """Recursively expand keywords up to given depth."""
    if depth <= 0:
        return []
    direct = await fetch_merch_suggestions(session, seed, marketplace, product_type)
    all_keywords = list(direct)
    if depth > 1:
        tasks = [
            expand_keyword(session, kw["keyword"], marketplace, product_type, depth - 1)
            for kw in direct[:5]
        ]
        if tasks:
            expanded = await asyncio.gather(*tasks)
            for exp in expanded:
                all_keywords.extend(exp)
    return all_keywords


async def _mine_async(seed: str, marketplace: str, product_type: str, depth: int) -> List[Dict[str, Any]]:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        if product_type == "all":
            types = ["t-shirts", "mugs", "stickers"]
        else:
            types = [product_type]

        all_results = []
        for ptype in types:
            results = await expand_keyword(session, seed, marketplace, ptype, depth)
            all_results.extend(results)

        # Remove duplicates
        seen = set()
        unique = []
        for kw in all_results:
            if kw["keyword"] not in seen:
                seen.add(kw["keyword"])
                unique.append(kw)
        return unique


def mine_merch_autocomplete(seed: str, marketplace: str = "us", product_type: str = "all", depth: int = 2) -> List[Dict[str, Any]]:
    """
    Mine keywords from Amazon Merch autocomplete.
    Uses a dedicated thread-local event loop to avoid conflicts with Qt.
    """
    result_holder = []
    error_holder = []

    def _run_in_thread():
        # Create a brand-new event loop in this thread — never touch Qt's loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                _mine_async(seed, marketplace, product_type, depth)
            )
            result_holder.extend(result)
        except Exception as e:
            error_holder.append(e)
        finally:
            loop.close()

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join(timeout=60)

    if error_holder:
        print(f"mine_merch_autocomplete error: {error_holder[0]}")
        return []
    return result_holder


if __name__ == "__main__":
    results = mine_merch_autocomplete("cat", marketplace="us", depth=2)
    print(f"Found {len(results)} keywords")
    for kw in results[:10]:
        print(f"  {kw['keyword']} (pos: {kw['position']})")
