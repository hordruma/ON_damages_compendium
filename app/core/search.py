"""
Search and matching algorithms for the Ontario Damages Compendium.

This module implements injury-focused semantic search that:
- Embeds and searches only on injuries and sequelae (not full text)
- Uses exclusive region filtering via sidebar multi-select
- Computes meta_score from injury-tag overlap and age/gender proximity
- Returns all results sorted by combined_score (no minimum threshold)
"""

import numpy as np
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any


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
    inj_weight: float = 0.8,
    meta_weight: float = 0.2
) -> List[Tuple[Dict[str, Any], float, float]]:
    """
    Search cases using injury-focused embeddings with exclusive region filtering.

    Algorithm:
    1. Apply exclusive region filter: only cases with at least one selected region
    2. Compute semantic similarity on injury embeddings (inj_emb)
    3. Compute meta_score from injury-tag overlap + age/gender
    4. Combine scores: combined = inj_weight * inj_sim + meta_weight * meta_score
    5. Return top N sorted by combined_score (no minimum threshold)

    Args:
        query_text: Free-text injury description from user (no preprocessing)
        selected_regions: List of region IDs/labels (exclusive filter)
        cases: List of case dictionaries
        region_map: Region ID -> label mapping
        model: Embedding model with .encode(text) method
        gender: Optional gender filter ("Male", "Female", etc.)
        age: Optional age filter
        top_n: Number of results to return
        inj_weight: Weight for injury semantic similarity (default 0.8)
        meta_weight: Weight for metadata score (default 0.2)

    Returns:
        List of (case, inj_sim, combined_score) sorted by combined_score desc
    """
    _ensure_embs_loaded()

    # Encode query using same model as embeddings
    qv = model.encode(query_text).astype("float32")

    # Stage 1: Exclusive region filtering
    candidate_indices = []
    case_index_map = {}

    for i, case in enumerate(cases):
        cid = case.get("id")
        try:
            row_idx = _ids.index(cid)
        except ValueError:
            # Case ID not found in embedding matrix, skip
            continue

        # Apply exclusive region filter if regions selected
        if selected_regions:
            case_regions = case.get("regions") or case.get("extended_data", {}).get("regions") or []
            if not case_regions:
                continue

            # Case-insensitive region overlap check
            lower_case_regions = {str(r).strip().lower() for r in case_regions}
            lower_sel = {str(r).strip().lower() for r in selected_regions}

            if lower_case_regions & lower_sel:
                candidate_indices.append(row_idx)
                case_index_map[row_idx] = case
        else:
            # No region filter: include all
            candidate_indices.append(row_idx)
            case_index_map[row_idx] = case

    if not candidate_indices:
        return []

    # Stage 2: Compute injury semantic similarity
    sims = _cosine_sim_batch(qv, candidate_indices)

    # Stage 3: Combine scores
    results = []
    for idx_pos, row_idx in enumerate(candidate_indices):
        case = case_index_map[row_idx]
        inj_sim = float(sims[idx_pos])

        # Meta score: no query preprocessing per user requirement
        # So query_injuries is empty, making injury_overlap neutral (0.5)
        query_injuries = []
        meta_score = compute_meta_score(case, query_injuries, gender, age)

        combined = float(inj_weight * inj_sim + meta_weight * meta_score)
        results.append((case, inj_sim, combined))

    # Stage 4: Sort and return top N
    results.sort(key=lambda t: t[2], reverse=True)
    return results[:top_n]


def extract_damages_value(case: Dict[str, Any]) -> Optional[float]:
    """
    Extract numeric damages value from case.

    Tries:
    1. extended_data.non_pecuniary_damages
    2. Non-pecuniary damages from plaintiffs array
    3. Direct 'damages' field

    Returns:
        Damages value as float, or None if not found
    """
    # Try extended_data first
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

    # Try direct field
    if case.get("damages"):
        try:
            return float(case["damages"])
        except (ValueError, TypeError):
            pass

    return None
