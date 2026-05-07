"""
POD_SEEDS - Predefined seed keywords by category for POD niche discovery.
"""
POD_SEEDS = {
    "professions": [
        "nurse", "teacher", "firefighter", "police", "doctor",
        "engineer", "accountant", "lawyer", "chef", "electrician",
        "plumber", "carpenter", "veterinarian", "pharmacist",
        "dentist", "pilot", "soldier", "farmer",
    ],
    "animals": [
        "cat", "dog", "golden retriever", "french bulldog", "labrador",
        "dachshund", "pug", "beagle", "husky", "corgi", "australian shepherd",
        "siamese cat", "black cat", "bunny", "horse", "bird lover",
    ],
    "family": [
        "mama", "dad", "grandma", "grandpa", "sister", "brother",
        "aunt", "uncle", "new mom", "dog mom", "cat mom",
    ],
    "hobbies": [
        "hiking", "camping", "fishing", "gardening", "knitting", "reading",
        "gaming", "yoga", "cycling", "running", "baking", "painting",
        "photography", "woodworking", "sewing",
    ],
    "humor": [
        "sarcastic", "introverted", "coffee addict", "wine lover",
        "nap queen", "monday hater",
    ],
    "holidays": [
        "christmas", "halloween", "valentines day", "thanksgiving",
        "easter", "fourth of july", "st patricks day", "new year",
        "mothers day", "fathers day",
    ],
    "sports": [
        "football", "basketball", "baseball", "soccer", "tennis",
        "golf", "swimming", "volleyball", "rugby", "hockey",
    ],
    "geographic": [
        "texas", "california", "florida", "new york", "colorado",
        "french", "italian", "german", "irish", "puerto rico",
    ],
    "lifestyle": [
        "vegan", "vegetarian", "organic", "zero waste", "minimalist",
        "boho", "cottagecore", "dark academia",
    ],
}


def expand_seed(seed: str, depth: int = 2) -> list:
    """
    Expand a seed by adding product prefixes.
    Returns list of expanded keywords.
    """
    prefixes = ["t-shirt", "mug", "sticker", "poster", "hoodie", "gift for"]
    results = [seed]
    if depth >= 2:
        for prefix in prefixes:
            if prefix in ["t-shirt", "mug", "sticker", "poster", "hoodie"]:
                results.append(f"{seed} {prefix}")
            else:
                results.append(f"{prefix} {seed}")
    return results


def get_all_seeds(category: str = "all", limit_per_category: int = 10) -> list:
    """
    Get seeds from POD_SEEDS.
    If category='all', return seeds from all categories.
    """
    if category == "all":
        all_seeds = []
        for seeds in POD_SEEDS.values():
            all_seeds.extend(seeds[:limit_per_category])
        return all_seeds
    elif category in POD_SEEDS:
        return POD_SEEDS[category][:limit_per_category]
    else:
        return []


if __name__ == "__main__":
    # Test
    print("Professions:", POD_SEEDS["professions"][:3])
    print("\nExpanded 'nurse':", expand_seed("nurse", depth=2)[:5])
    print("\nAll seeds (2 per category):", len(get_all_seeds(limit_per_category=2)))
