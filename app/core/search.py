"""
Hybrid search for the Ontario Damages Compendium.

This module implements hybrid search combining:
- Semantic search: Embeddings from injuries, category, and comments
- Keyword search: BM25-style keyword matching on case text
- Metadata scoring: Injury overlap, gender match, age proximity
- Exclusive category filtering: Cases must match selected anatomical categories
- Results sorted by combined relevance score
"""

import numpy as np
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from collections import Counter
import math


DATA_DIR = Path("data")
EMB_PATH = DATA_DIR / "embeddings_inj.npy"
IDS_PATH = DATA_DIR / "ids.json"

# Cache embeddings in memory for fast lookup
_emb_matrix = None
_ids = None
_emb_norm = None


def _ensure_embs_loaded():
    """Load embedding matrix and IDs once at module scope."""
    global _emb_matrix, _ids, _emb_norm
    if _emb_matrix is None:
        _emb_matrix = np.load(str(EMB_PATH))
        with open(IDS_PATH, "r", encoding="utf-8") as f:
            _ids = json.load(f)
        # Normalize rows for cosine similarity
        norms = np.linalg.norm(_emb_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        _emb_norm = _emb_matrix / norms


def _cosine_sim_batch(query_vec: np.ndarray, indices: Optional[List[int]]) -> np.ndarray:
    """
    Compute cosine similarity between query vector and candidate embeddings.

    Args:
        query_vec: Query embedding vector (D,), float32
        indices: List of row indices to compare against, or None for all

    Returns:
        Array of cosine similarities aligned with indices
    """
    q = query_vec.astype("float32")
    q_norm = q / (np.linalg.norm(q) or 1.0)

    if indices is None:
        return _emb_norm.dot(q_norm)
    else:
        sub = _emb_norm[indices]
        return sub.dot(q_norm)


def _age_proximity_score(case_age: Optional[int], query_age: Optional[int]) -> float:
    """
    Score age proximity: 1.0 exact, 0.85 within 5 years, 0.7 within 10, etc.
    If either is None, return 0.5 (neutral).
    """
    if query_age is None or case_age is None:
        return 0.5
    diff = abs(case_age - query_age)
    if diff == 0:
        return 1.0
    if diff <= 5:
        return 0.85
    if diff <= 10:
        return 0.7
    if diff <= 20:
        return 0.5
    return 0.3


def _gender_match_score(case_gender: Optional[str], query_gender: Optional[str]) -> float:
    """
    Score gender match: 1.0 if exact match, 0.0 if no match, 0.5 if either None.
    """
    if query_gender is None or not case_gender:
        return 0.5
    return 1.0 if case_gender.strip().lower() == query_gender.strip().lower() else 0.0


def _injury_overlap_score(case_injuries: List[str], query_injuries: List[str]) -> float:
    """
    Compute fraction of query injuries that overlap with case injuries.
    If no query_injuries, return 0.5 (neutral).
    If no case_injuries, return 0.0.
    """
    if not query_injuries:
        return 0.5
    if not case_injuries:
        return 0.0

    s_case = {s.strip().lower() for s in case_injuries if s}
    s_q = {s.strip().lower() for s in query_injuries if s}

    if not s_case or not s_q:
        return 0.0

    overlap = s_case & s_q
    return len(overlap) / max(1, len(s_q))


def _tokenize(text: str) -> List[str]:
    """
    Tokenize text into normalized keywords.

    Args:
        text: Input text

    Returns:
        List of lowercase tokens
    """
    if not text:
        return []
    # Convert to lowercase, split on non-alphanumeric, filter short tokens
    tokens = re.findall(r'\b[a-z]{2,}\b', text.lower())
    return tokens


def _bm25_score(query_tokens: List[str], doc_tokens: List[str], avg_doc_len: float = 100.0) -> float:
    """
    Compute BM25 score for keyword matching.

    BM25 is a ranking function used by search engines to estimate
    relevance of documents to a given search query.

    Args:
        query_tokens: Tokenized query
        doc_tokens: Tokenized document
        avg_doc_len: Average document length (for normalization)

    Returns:
        BM25 score (higher = better match)
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    # BM25 parameters
    k1 = 1.5  # Term frequency saturation parameter
    b = 0.75  # Length normalization parameter

    # Count term frequencies
    doc_tf = Counter(doc_tokens)
    doc_len = len(doc_tokens)

    score = 0.0
    for term in query_tokens:
        if term in doc_tf:
            tf = doc_tf[term]
            # Simplified BM25 (without IDF since we're scoring one doc at a time)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_len / avg_doc_len))
            score += numerator / denominator

    # Normalize by query length
    return score / max(1, len(set(query_tokens)))


def _keyword_search_score(query_text: str, case: Dict[str, Any]) -> float:
    """
    Compute keyword match score for a case.

    Searches in: injuries, comments, case name, summary text

    Args:
        query_text: User's search query
        case: Case dictionary

    Returns:
        Keyword match score (0-1)
    """
    # Tokenize query
    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return 0.0

    # Gather searchable text from case
    text_parts = []

    # Add injuries (weighted heavily)
    ext = case.get('extended_data', {})
    injuries = ext.get('injuries', [])
    if injuries:
        text_parts.extend(injuries * 2)  # Double weight for injuries

    # Add comments (also important)
    comments = ext.get('comments') or case.get('comments')
    if comments:
        text_parts.append(comments)

    # Add case name
    case_name = case.get('case_name', '')
    if case_name:
        text_parts.append(case_name)

    # Add summary text if available
    summary = case.get('summary_text', '')
    if summary:
        text_parts.append(summary)

    # Combine and tokenize document
    doc_text = ' '.join(str(p) for p in text_parts if p)
    doc_tokens = _tokenize(doc_text)

    if not doc_tokens:
        return 0.0

    # Compute BM25 score
    bm25_raw = _bm25_score(query_tokens, doc_tokens)

    # Normalize to 0-1 range (typical BM25 scores are 0-10)
    normalized = min(bm25_raw / 10.0, 1.0)

    return normalized


def compute_meta_score(
    case: Dict[str, Any],
    query_injuries: List[str],
    query_gender: Optional[str],
    query_age: Optional[int]
) -> float:
    """
    Compute meta_score from injury overlap, gender match, and age proximity.

    Weights:
    - Injury overlap: 0.7
    - Gender match: 0.15
    - Age proximity: 0.15
    """
    inj_score = _injury_overlap_score(
        case.get("extended_data", {}).get("injuries", []) or [],
        query_injuries
    )
    gender_score = _gender_match_score(
        case.get("extended_data", {}).get("sex") or case.get("extended_data", {}).get("gender"),
        query_gender
    )
    age_score = _age_proximity_score(
        case.get("extended_data", {}).get("age"),
        query_age
    )

    combined = (0.7 * inj_score) + (0.15 * gender_score) + (0.15 * age_score)
    return min(max(combined, 0.0), 1.0)


def search_cases(
    query_text: str,
    selected_regions: List[str],
    cases: List[Dict[str, Any]],
    region_map: Dict[str, Any],
    model: Any,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    top_n: int = 25,
    semantic_weight: float = 0.5,
    keyword_weight: float = 0.3,
    meta_weight: float = 0.2
) -> List[Tuple[Dict[str, Any], float, float]]:
    """
    Search cases using hybrid search (semantic + keyword + metadata).

    Algorithm:
    1. Apply exclusive category filter: only include cases matching selected categories
    2. Compute semantic similarity on embeddings (injuries + category + comments)
    3. Compute keyword match score using BM25
    4. Compute metadata score from injury overlap, gender match, age proximity
    5. Combine scores: combined = sem_weight*semantic + kw_weight*keyword + meta_weight*meta
    6. Return top N sorted by combined_score descending

    Args:
        query_text: Free-text injury description from user
        selected_regions: List of category IDs/labels (exclusive filter) - kept as 'regions' for API compat
        cases: List of case dictionaries
        region_map: Category ID -> label mapping (kept as 'region_map' for API compat)
        model: Embedding model with .encode(text) method
        gender: Optional gender filter ("Male", "Female", etc.)
        age: Optional age filter
        top_n: Number of results to return
        semantic_weight: Weight for semantic similarity (default 0.5)
        keyword_weight: Weight for keyword matching (default 0.3)
        meta_weight: Weight for metadata score (default 0.2)

    Returns:
        List of (case, semantic_sim, combined_score) sorted by combined_score desc
    """
    _ensure_embs_loaded()

    # Encode query using same model as embeddings
    qv = model.encode(query_text).astype("float32")

    # Stage 1: Exclusive category filtering
    candidate_indices = []
    case_index_map = {}

    for i, case in enumerate(cases):
        cid = case.get("id")
        try:
            row_idx = _ids.index(cid)
        except ValueError:
            # Case ID not found in embedding matrix, skip
            continue

        # Apply exclusive category filter if categories selected
        if selected_regions:  # kept as 'selected_regions' for API compat
            # Check both 'regions' field (legacy) and category-based fields
            case_categories = case.get("regions") or case.get("extended_data", {}).get("regions") or []
            if not case_categories:
                continue

            # Case-insensitive category overlap check
            lower_case_categories = {str(c).strip().lower() for c in case_categories}
            lower_sel = {str(c).strip().lower() for c in selected_regions}

            if lower_case_categories & lower_sel:
                candidate_indices.append(row_idx)
                case_index_map[row_idx] = case
        else:
            # No category filter: include all
            candidate_indices.append(row_idx)
            case_index_map[row_idx] = case

    if not candidate_indices:
        return []

    # Stage 2: Compute semantic similarity
    semantic_sims = _cosine_sim_batch(qv, candidate_indices)

    # Stage 3: Hybrid scoring
    results = []
    for idx_pos, row_idx in enumerate(candidate_indices):
        case = case_index_map[row_idx]

        # Semantic score from embeddings
        semantic_sim = float(semantic_sims[idx_pos])

        # Keyword score from BM25
        keyword_score = _keyword_search_score(query_text, case)

        # Metadata score
        query_injuries = []
        meta_score = compute_meta_score(case, query_injuries, gender, age)

        # Combine all three scores
        combined = float(
            semantic_weight * semantic_sim +
            keyword_weight * keyword_score +
            meta_weight * meta_score
        )

        results.append((case, semantic_sim, combined))

    # Stage 4: Sort and return top N
    results.sort(key=lambda t: t[2], reverse=True)
    return results[:top_n]


def extract_damages_value(case: Dict[str, Any]) -> Optional[float]:
    """
    Extract numeric damages value from case.

    Tries multiple fields to support both old and new data formats:
    1. Direct 'damages' field (new format)
    2. Top-level 'non_pecuniary_damages' field
    3. extended_data.non_pecuniary_damages
    4. Non-pecuniary damages from plaintiffs array

    Returns:
        Damages value as float, or None if not found
    """
    # Try direct damages field first (new format)
    if case.get("damages"):
        try:
            return float(case["damages"])
        except (ValueError, TypeError):
            pass

    # Try top-level non_pecuniary_damages (current format)
    if case.get("non_pecuniary_damages"):
        try:
            return float(case["non_pecuniary_damages"])
        except (ValueError, TypeError):
            pass

    # Try extended_data
    ext = case.get("extended_data", {})
    if ext.get("non_pecuniary_damages"):
        try:
            return float(ext["non_pecuniary_damages"])
        except (ValueError, TypeError):
            pass

    # Try plaintiffs array
    plaintiffs = case.get("plaintiffs", [])
    if plaintiffs:
        for p in plaintiffs:
            damages = p.get("non_pecuniary_damages")
            if damages:
                try:
                    return float(damages)
                except (ValueError, TypeError):
                    pass

    return None
