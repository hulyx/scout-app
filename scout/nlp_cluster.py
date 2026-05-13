"""Pure-Python NLP keyword clustering using TF-IDF + cosine similarity.

No external dependencies beyond math and re. Uses a greedy clustering
algorithm: build similarity matrix, then group keywords with
cosine similarity above a threshold.
"""

import math
import re
from typing import List, Dict, Tuple, Set


_COMMON_WORDS = {
    "shirt", "tshirt", "t-shirt", "hoodie", "sweatshirt",
    "mug", "cup", "glass",
    "sticker", "decal",
    "poster", "print", "canvas",
    "gift", "present", "ideas",
    "gifts", "ideas",
    "lover", "lovers", "mom", "dad", "grandma", "grandpa",
    "men", "women", "kids", "boys", "girls",
    "birthday", "christmas",
}


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())
    return [t for t in tokens if len(t) > 1 and t not in _COMMON_WORDS]


def _idf(corpus: List[List[str]]) -> Dict[str, float]:
    N = len(corpus)
    df: Dict[str, int] = {}
    for doc in corpus:
        for t in set(doc):
            df[t] = df.get(t, 0) + 1
    return {t: math.log((N + 1) / (c + 1)) + 1 for t, c in df.items()}


def _tfidf_vector(tokens: List[str], idf: Dict[str, float]) -> List[float]:
    if not tokens:
        return []
    terms = sorted(idf.keys())
    return [idf.get(t, 1.0) for t in terms if t in tokens]


def _overlap_sim(a_tokens: List[str], b_tokens: List[str]) -> float:
    """Overlap coefficient: |intersection| / min(|A|, |B|)."""
    if not a_tokens or not b_tokens:
        return 0.0
    set_a, set_b = set(a_tokens), set(b_tokens)
    inter = set_a & set_b
    if not inter:
        return 0.0
    return len(inter) / min(len(set_a), len(set_b))


def cluster_keywords(
    keywords: List[str],
    threshold: float = 0.4,
    min_cluster_size: int = 2,
) -> List[Dict]:
    """Group keywords into clusters by word overlap similarity.

    Args:
        keywords: List of keyword strings.
        threshold: Overlap similarity threshold (0-1). Higher = tighter groups.
        min_cluster_size: Minimum keywords per cluster.

    Returns:
        List of dicts::
            {"cluster": int or -1, "label": str, "size": int,
             "keywords": [str, ...], "avg_score": float}
        - ``cluster`` is -1 for unclustered (singleton) keywords.
        - ``label`` is the most representative keyword (highest avg similarity).
    """
    if not keywords:
        return []

    corpus = [_tokenize(kw) for kw in keywords]

    # Overlap similarity matrix
    n = len(keywords)
    sim = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            s = _overlap_sim(corpus[i], corpus[j])
            sim[i][j] = sim[j][i] = s

    # Greedy clustering: pick keyword with most neighbors above threshold
    assigned = [False] * n
    clusters: List[List[int]] = []
    for _ in range(n):
        # Find best unassigned seed (most neighbors not yet assigned)
        best_idx = -1
        best_count = -1
        for i in range(n):
            if assigned[i]:
                continue
            count = sum(1 for j in range(n) if not assigned[j] and sim[i][j] >= threshold)
            if count > best_count:
                best_count = count
                best_idx = i

        if best_idx == -1 or best_count < min_cluster_size:
            break

        # Form cluster from best_idx + all neighbors above threshold
        cluster = [best_idx]
        assigned[best_idx] = True
        for j in range(n):
            if not assigned[j] and sim[best_idx][j] >= threshold:
                cluster.append(j)
                assigned[j] = True

        if len(cluster) >= min_cluster_size:
            clusters.append(cluster)

    # Anything left unassigned goes as singletons
    singletons = [i for i in range(n) if not assigned[i]]

    # Build result
    result: List[Dict] = []
    cluster_id = 0
    for cluster in clusters:
        kw_list = [keywords[i] for i in cluster]
        # Label: keyword with highest avg similarity to rest of cluster
        best_lbl = kw_list[0]
        best_avg = -1.0
        for i in cluster:
            others = [j for j in cluster if j != i]
            if not others:
                continue
            avg_s = sum(sim[i][j] for j in others) / len(others)
            if avg_s > best_avg:
                best_avg = avg_s
                best_lbl = keywords[i]
        result.append({
            "cluster": cluster_id,
            "label": best_lbl,
            "size": len(kw_list),
            "keywords": kw_list,
            "avg_score": round(best_avg, 3) if best_avg >= 0 else 0,
        })
        cluster_id += 1

    for i in singletons:
        result.append({
            "cluster": -1,
            "label": keywords[i],
            "size": 1,
            "keywords": [keywords[i]],
            "avg_score": 0.0,
        })

    return result


def cluster_keywords_flat(
    keywords: List[str],
    threshold: float = 0.4,
) -> List[int]:
    """Assign cluster IDs to each keyword without building full metadata.

    Returns a list of ints (cluster_id per keyword, -1 for singletons).
    """
    clusters = cluster_keywords(keywords, threshold=threshold, min_cluster_size=2)
    mapping: Dict[str, int] = {}
    for cl in clusters:
        for kw in cl["keywords"]:
            mapping[kw] = cl["cluster"]
    return [mapping.get(kw, -1) for kw in keywords]
