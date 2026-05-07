"""
PodScorer - Weighted scoring engine for POD keywords.
"""
from typing import Dict, Any, List


POD_DEFAULT_WEIGHTS = {
    'merch_autocomplete': 0.14,    # Position in Amazon Merch AC
    'etsy_competition': 0.11,     # Competition on Etsy (inversed: lower = better)
    'redbubble_competition': 0.09, # Competition on Redbubble (inversed)
    'spreadshirt_presence': 0.05, # Presence on Spreadshirt
    'pinterest_demand': 0.12,   # Demand signal from Pinterest (boards + repins)
    'reddit_demand': 0.13,       # Demand signal from Reddit
    'google_trends_score': 0.11, # Google Trends score (interest + trend)
    'google_suggest': 0.07,        # Google Suggest position
    'avg_price_score': 0.10,     # Average price (too low = bad signal)
    'niche_specificity': 0.05,   # Specificity of niche (long-tail = better)
    'seasonal_risk': 0.03,        # Seasonal risk (pics = risk)
}


def normalize_merch_position(position: int) -> float:
    """Normalize Merch autocomplete position (1 = best, higher = worse)."""
    if not position:
        return 0.5
    return max(0.0, 1.0 - (position - 1) / 20.0)


def normalize_etsy_competition(count: int) -> float:
    """Normalize Etsy competition count (lower = better)."""
    if not count:
        return 1.0
    return 1.0 / (1.0 + count / 5000.0)


def normalize_redbubble_competition(count: int) -> float:
    """Normalize Redbubble competition (lower = better)."""
    if not count:
        return 1.0
    return 1.0 / (1.0 + count / 10000.0)


def normalize_spreadshirt_presence(has_presence: bool) -> float:
    """Normalize Spreadshirt presence."""
    return 1.0 if has_presence else 0.5


def normalize_pinterest_demand(board_followers: int, pin_count_estimate: int) -> float:
    """Normalize Pinterest demand (combined score)."""
    followers_score = min(1.0, (board_followers or 0) / 10000.0)
    pin_score = min(1.0, (pin_count_estimate or 0) / 10000.0)
    return followers_score * 0.6 + pin_score * 0.4


def normalize_reddit_demand(score: float) -> float:
    """Normalize Reddit demand score."""
    return min(1.0, max(0.0, (score or 0) / 100.0))


def normalize_google_trends(score: float) -> float:
    """Normalize Google Trends score (0-100 scale)."""
    return min(1.0, max(0.0, (score or 0) / 100.0))


def normalize_google_suggest(position: int) -> float:
    """Normalize Google Suggest position."""
    if not position:
        return 0.5
    return max(0.0, 1.0 - (position - 1) / 10.0)


def normalize_avg_price(price: float) -> float:
    """Normalize average price (optimal: $20-35, too low = bad)."""
    if not price:
        return 0.5
    if 20 <= price <= 35:
        return 1.0
    elif price < 15:
        return 0.3  # Too cheap = low quality signal
    elif price > 50:
        return 0.7  # Too expensive = smaller market
    return 0.9


def normalize_niche_specificity(keyword: str) -> float:
    """Favor longer, more specific keywords (2-4 words ideal)."""
    if not keyword:
        return 0.5
    word_count = len(keyword.split())
    if word_count >= 3:
        return 1.0
    elif word_count == 2:
        return 0.8
    return 0.5  # Generic single words are risky


def normalize_seasonal_risk(keyword: str) -> float:
    """Penalize seasonal keywords (Christmas, Halloween, etc.)."""
    seasonal_words = [
        'christmas', 'halloween', 'valentine', 'thanksgiving',
        'easter', 'new year', 'fourth of july', 'st patricks',
    ]
    keyword_lower = (keyword or '').lower()
    for word in seasonal_words:
        if word in keyword_lower:
            return 0.3  # High seasonal risk
    return 1.0  # No seasonal risk


def score_pod_keyword(keyword_data: Dict[str, Any], weights: Dict[str, float] = None) -> float:
    """
    Score a POD keyword using weighted components.
    
    Args:
        keyword_data: Dict with keys like merch_ac_position, etsy_competition, etc.
        weights: Optional custom weights (defaults to POD_DEFAULT_WEIGHTS)
    
    Returns:
        Float score between 0.0 and 1.0
    """
    if weights is None:
        weights = POD_DEFAULT_WEIGHTS
    
    total_score = 0.0
    total_weight = 0.0
    
    keyword = keyword_data.get('keyword', '')
    
    # Merch autocomplete position
    if 'merch_autocomplete' in weights and 'merch_ac_position' in keyword_data:
        score = normalize_merch_position(keyword_data['merch_ac_position'])
        total_score += score * weights['merch_autocomplete']
        total_weight += weights['merch_autocomplete']
    
    # Etsy competition
    if 'etsy_competition' in weights and 'etsy_competition' in keyword_data:
        score = normalize_etsy_competition(keyword_data['etsy_competition'])
        total_score += score * weights['etsy_competition']
        total_weight += weights['etsy_competition']
    
    # Redbubble competition
    if 'redbubble_competition' in weights and 'redbubble_competition' in keyword_data:
        score = normalize_redbubble_competition(keyword_data['redbubble_competition'])
        total_score += score * weights['redbubble_competition']
        total_weight += weights['redbubble_competition']
    
    # Spreadshirt presence
    if 'spreadshirt_presence' in weights:
        has_presence = keyword_data.get('spreadshirt_presence', False)
        score = normalize_spreadshirt_presence(has_presence)
        total_score += score * weights['spreadshirt_presence']
        total_weight += weights['spreadshirt_presence']
    
    # Pinterest demand
    if 'pinterest_demand' in weights:
        board_followers = keyword_data.get('pinterest_board_followers', 0)
        pin_count = keyword_data.get('pinterest_pin_count', 0)
        score = normalize_pinterest_demand(board_followers, pin_count)
        total_score += score * weights['pinterest_demand']
        total_weight += weights['pinterest_demand']
    
    # Reddit demand
    if 'reddit_demand' in weights and 'reddit_score' in keyword_data:
        score = normalize_reddit_demand(keyword_data['reddit_score'])
        total_score += score * weights['reddit_demand']
        total_weight += weights['reddit_demand']
    
    # Google Trends
    if 'google_trends_score' in weights and 'google_trends_score' in keyword_data:
        score = normalize_google_trends(keyword_data['google_trends_score'])
        total_score += score * weights['google_trends_score']
        total_weight += weights['google_trends_score']
    
    # Google Suggest
    if 'google_suggest' in weights and 'google_suggest_position' in keyword_data:
        score = normalize_google_suggest(keyword_data['google_suggest_position'])
        total_score += score * weights['google_suggest']
        total_weight += weights['google_suggest']
    
    # Average price
    if 'avg_price_score' in weights and 'avg_price' in keyword_data:
        score = normalize_avg_price(keyword_data['avg_price'])
        total_score += score * weights['avg_price_score']
        total_weight += weights['avg_price_score']
    
    # Niche specificity
    if 'niche_specificity' in weights:
        score = normalize_niche_specificity(keyword)
        total_score += score * weights['niche_specificity']
        total_weight += weights['niche_specificity']
    
    # Seasonal risk
    if 'seasonal_risk' in weights:
        score = normalize_seasonal_risk(keyword)
        total_score += score * weights['seasonal_risk']
        total_weight += weights['seasonal_risk']
    
    # Normalize by total weight used
    if total_weight > 0:
        return total_score / total_weight
    return 0.5  # Neutral score if no data


if __name__ == '__main__':
    # Test
    test_keyword = {
        'keyword': 'funny cat mug',
        'merch_ac_position': 3,
        'etsy_competition': 2500,
        'redbubble_competition': 5000,
        'pinterest_board_followers': 3000,
        'pinterest_pin_count': 8000,
        'reddit_score': 45.0,
        'google_trends_score': 65.0,
        'avg_price': 22.99,
    }
    
    score = score_pod_keyword(test_keyword)
    print(f"Score for '{test_keyword['keyword']}': {score:.3f}")
