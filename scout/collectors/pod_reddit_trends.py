"""Reddit demand mining for POD niches."""

import logging
import re
import time
from collections import Counter

logger = logging.getLogger(__name__)

# POD-focused subreddits
POD_SUBREDDITS = [
    "redbubble", "MerchByAmazon", "PodDesign", "Etsy", "EtsySellers",
    "Entrepreneur", "tshritdesigns", "streetwear", "typography",
    "puns", "mugs", "stickers", "hiking", "camping", "doglovers",
    "catlovers", "nurses", "teachers", "funny", " sarcastic",
]

# Keywords to extract from titles
_POD_KEYWORD_PATTERNS = re.compile(
    r'\b('
    r't-shirt|hoodie|mug|sticker|poster|sweatshirt|popsocket|'
    r'design|graphic|funny|sarcastic|cute|vintage|retro|'
    r'nurse|teacher|firefighter|dog|cat|mama|dad|'
    r'christmas|halloween|valentines|thanksgiving|'
    r'gift for|present for|idea for'
    r')\b',
    re.IGNORECASE,
)

def fetch_reddit_posts(subreddit, sort='hot', limit=100):
    """Fetch posts from Reddit public JSON API."""
    url = f'https://www.reddit.com/r/{subreddit}/{sort}.json'
    params = {'limit': limit}
    try:
        import requests
        resp = requests.get(url, params=params, headers={'User-Agent': 'POD-Scout/0.4.6'}, timeout=10)
        data = resp.json()
        return data.get('data', {}).get('children', [])
    except Exception as e:
        logger.warning(f'Reddit fetch failed for r/{subreddit}: {e}')
        return []


def extract_pod_keywords(posts):
    """Extract POD-relevant keywords from post titles."""
    keywords = []
    for post in posts:
        title = post.get('data', {}).get('title', '')
        matches = _POD_KEYWORD_PATTERNS.findall(title)
        keywords.extend([m.lower() for m in matches])
        # Also extract quoted phrases
        quoted = re.findall(r'"([^"]{3,50})"', title)
        keywords.extend([q.lower() for q in quoted])
    return keywords


def score_keywords(keyword_list):
    """Score keywords by frequency and engagement."""
    counter = Counter(keyword_list)
    results = []
    for kw, count in counter.most_common(50):
        results.append({
            'keyword': kw,
            'score': min(1.0, count / 10),
            'posts': count,
            'subreddits': list(set([p.get('data', {}).get('subreddit', '') for p in []])),  # simplified
            'demand': 'high' if count > 5 else 'medium' if count > 2 else 'low',
        })
    return results


def mine_pod_reddit_trends():
    """Main function: mine POD trends from Reddit."""
    all_keywords = []
    for sub in POD_SUBREDDITS[:5]:  # limit to avoid rate limits
        posts = fetch_reddit_posts(sub, limit=50)
        keywords = extract_pod_keywords(posts)
        all_keywords.extend(keywords)
        time.sleep(0.5)  # rate limiting

    return score_keywords(all_keywords)


# Baseline trends if scraping fails
BASELINE_POD_TRENDS = [
    {"keyword": "dog mom t-shirt", "score": 0.95, "subreddits": ["doglovers"], "demand": "high", "posts": 12},
    {"keyword": "sarcastic mug", "score": 0.92, "subreddits": ["sarcastic"], "demand": "high", "posts": 10},
    {"keyword": "nurse life hoodie", "score": 0.88, "subreddits": ["nurses"], "demand": "high", "posts": 9},
    {"keyword": "hiking sticker", "score": 0.85, "subreddits": ["hiking"], "demand": "high", "posts": 8},
    {"keyword": "funny camping mug", "score": 0.82, "subreddits": ["camping"], "demand": "medium", "posts": 7},
    {"keyword": "teacher gift tote", "score": 0.78, "subreddits": ["teachers"], "demand": "medium", "posts": 6},
    {"keyword": "cat lover sweatshirt", "score": 0.75, "subreddits": ["catlovers"], "demand": "medium", "posts": 6},
    {"keyword": "christmas family pajamas", "score": 0.72, "subreddits": ["christmas"], "demand": "medium", "posts": 5},
    {"keyword": "typography poster", "score": 0.68, "subreddits": ["typography"], "demand": "medium", "posts": 5},
    {"keyword": "vintage camera sticker", "score": 0.65, "subreddits": ["vintage"], "demand": "medium", "posts": 4},
]
