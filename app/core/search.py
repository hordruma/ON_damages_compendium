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


def _parse_comma_separated_injuries(text: str) -> List[str]:
    """
    Parse comma-separated injury phrases from query text.

    Args:
        text: Input text with comma-separated injuries

    Returns:
        List of normalized injury phrases (stripped, lowercased)
    """
    if not text:
        return []
    # Split by comma and normalize each phrase
    phrases = [phrase.strip().lower() for phrase in text.split(',') if phrase.strip()]
    return phrases


def _injury_list_match_score(query_injuries: List[str], case: Dict[str, Any]) -> float:
    """
    Compute direct match score against case's injury list.

    This checks for exact phrase matches (or substring matches) between
    query injuries and the case's injury list. This score should predominate
    when injuries are found in the list.

    Args:
        query_injuries: List of normalized injury phrases from query
        case: Case dictionary

    Returns:
        Match score (0-1), higher when query injuries match case injuries
    """
    if not query_injuries:
        return 0.0

    # Get case injuries
    ext = case.get('extended_data', {})
    case_injuries = ext.get('injuries', [])
    if not case_injuries:
        return 0.0

    # Normalize case injuries
    normalized_case_injuries = [inj.strip().lower() for inj in case_injuries]

    # Count matches: check both exact match and substring match
    matches = 0
    for query_inj in query_injuries:
        # Check for exact match first
        if query_inj in normalized_case_injuries:
            matches += 1
        else:
            # Check for substring match (query injury contains or is contained in case injury)
            for case_inj in normalized_case_injuries:
                if query_inj in case_inj or case_inj in query_inj:
                    matches += 1
                    break

    # Return proportion of query injuries that matched
    return matches / len(query_injuries)


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


def filter_outliers(
    cases: List[Dict[str, Any]],
    threshold: float = 1.5
) -> List[Dict[str, Any]]:
    """
    Filter out statistical outliers from cases based on damages awards.

    Uses the IQR (Interquartile Range) method:
    - Outliers are values below Q1 - threshold*IQR or above Q3 + threshold*IQR
    - Standard threshold is 1.5 (moderate outliers)

    Args:
        cases: List of case dictionaries
        threshold: IQR multiplier for outlier detection (default 1.5)

    Returns:
        List of cases with outliers removed
    """
    if not cases:
        return []

    # Extract damages values
    damages_values = []
    cases_with_damages = []

    for case in cases:
        damage_val = extract_damages_value(case)
        if damage_val is not None and damage_val > 0:
            damages_values.append(damage_val)
            cases_with_damages.append(case)

    # Need at least 4 values for meaningful quartile calculation
    if len(damages_values) < 4:
        return cases

    # Calculate quartiles and IQR
    damages_array = np.array(damages_values)
    q1 = np.percentile(damages_array, 25)
    q3 = np.percentile(damages_array, 75)
    iqr = q3 - q1

    # Define outlier bounds
    lower_bound = q1 - threshold * iqr
    upper_bound = q3 + threshold * iqr

    # Filter cases
    filtered_cases = []
    for case in cases_with_damages:
        damage_val = extract_damages_value(case)
        if damage_val is not None and lower_bound <= damage_val <= upper_bound:
            filtered_cases.append(case)

    # Also include cases without damages (they're not outliers, just missing data)
    for case in cases:
        damage_val = extract_damages_value(case)
        if damage_val is None or damage_val <= 0:
            filtered_cases.append(case)

    return filtered_cases


def search_cases(
    query_text: str,
    selected_regions: List[str],
    cases: List[Dict[str, Any]],
    region_map: Dict[str, Any],
    model: Any,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    top_n: int = 25,
    semantic_weight: float = 0.15,
    keyword_weight: float = 0.55,
    meta_weight: float = 0.3,
    injury_list_weight: float = 0.4
) -> List[Tuple[Dict[str, Any], float, float]]:
    """
    Search cases using hybrid search (semantic + keyword + metadata + injury list match).

    Algorithm:
    1. Apply exclusive category filter: only include cases matching selected categories
    2. Parse comma-separated injuries from query
    3. Compute semantic similarity on embeddings (injuries + category + comments)
    4. Compute keyword match score using BM25
    5. Compute injury list match score (direct matching of query injuries to case injury list)
    6. Compute metadata score from injury overlap, gender match, age proximity
    7. Combine scores with weights
    8. If no categories selected, adjust weight distribution
    9. Return top N sorted by combined_score descending

    Weight Distribution:
    - Default (with injury categories):
      Injury List: 0.4, Keyword: 0.35, Semantic: 0.15, Metadata: 0.1
    - Without categories (metadata weight redistributed):
      Injury List: 0.5, Keyword: 0.35, Semantic: 0.15

    Args:
        query_text: Free-text injury description from user (comma-separated)
        selected_regions: List of category IDs/labels (exclusive filter) - kept as 'regions' for API compat
        cases: List of case dictionaries
        region_map: Category ID -> label mapping (kept as 'region_map' for API compat)
        model: Embedding model with .encode(text) method
        gender: Optional gender filter ("Male", "Female", etc.)
        age: Optional age filter
        top_n: Number of results to return
        semantic_weight: Weight for semantic similarity (default 0.15)
        keyword_weight: Weight for keyword matching (default 0.55, adjusted to 0.35 internally)
        meta_weight: Weight for metadata score (default 0.3, adjusted to 0.1 internally)
        injury_list_weight: Weight for injury list matching (default 0.4)

    Returns:
        List of (case, semantic_sim, combined_score) sorted by combined_score desc
    """
    _ensure_embs_loaded()

    # Parse comma-separated injuries from query
    query_injuries = _parse_comma_separated_injuries(query_text)

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

    # Adjust weights for new 4-component system
    # Default weights (with categories): injury_list=0.4, keyword=0.35, semantic=0.15, meta=0.1
    adjusted_injury_list_weight = injury_list_weight
    adjusted_keyword_weight = 0.35  # Reduced from 0.55 to accommodate injury list weight
    adjusted_semantic_weight = semantic_weight
    adjusted_meta_weight = 0.1  # Reduced from 0.3 to accommodate injury list weight

    if not selected_regions:
        # No category filter: redistribute metadata weight to injury list matching
        # Adjusted weights: injury_list=0.5, keyword=0.35, semantic=0.15, meta=0.0
        adjusted_injury_list_weight = injury_list_weight + 0.1  # 0.4 + 0.1 = 0.5
        adjusted_keyword_weight = 0.35
        adjusted_semantic_weight = 0.15
        adjusted_meta_weight = 0.0

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

        # Injury list match score (predominates when injuries match)
        injury_list_score = _injury_list_match_score(query_injuries, case)

        # Metadata score
        meta_score = compute_meta_score(case, query_injuries, gender, age)

        # Combine all four scores with adjusted weights
        combined = float(
            adjusted_semantic_weight * semantic_sim +
            adjusted_keyword_weight * keyword_score +
            adjusted_injury_list_weight * injury_list_score +
            adjusted_meta_weight * meta_score
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


def boolean_search(
    query: str,
    cases: List[Dict[str, Any]],
    selected_regions: Optional[List[str]] = None,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    age_range: int = 5,
    search_fields: Optional[List[str]] = None,
    min_damages: Optional[float] = None,
    max_damages: Optional[float] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Perform Boolean search on cases using AND, OR, NOT operators.

    Supports:
    - AND: All terms must be present (e.g., "whiplash AND herniation")
    - OR: At least one term must be present (e.g., "fracture OR break")
    - NOT: Term must not be present (e.g., "spine NOT surgery")
    - Parentheses: Grouping (e.g., "(neck OR spine) AND herniation")
    - Quoted phrases: Exact phrase matching (e.g., "disc herniation")
    - Field-specific search: Search in specific fields only
    - Damages filters: Filter by award amounts
    - Year range filters: Filter by case year

    Args:
        query: Boolean query string
        cases: List of case dictionaries
        selected_regions: Optional list of category IDs to filter by
        gender: Optional gender filter
        age: Optional age filter
        age_range: Age range tolerance for age filtering (default 5 years)
        search_fields: List of fields to search in (default: all fields)
                      Options: 'case_name', 'injuries', 'comments', 'summary'
        min_damages: Minimum damages amount filter
        max_damages: Maximum damages amount filter
        min_year: Minimum case year filter
        max_year: Maximum case year filter

    Returns:
        List of matching cases
    """
    if not query.strip():
        return []

    # Default to searching all fields if not specified
    if search_fields is None:
        search_fields = ['case_name', 'injuries', 'comments', 'summary']

    # Parse and evaluate the Boolean expression
    matching_cases = []

    for case in cases:
        # Apply year filter
        if min_year is not None or max_year is not None:
            case_year = case.get('year')
            if case_year is None:
                continue
            if min_year is not None and case_year < min_year:
                continue
            if max_year is not None and case_year > max_year:
                continue

        # Apply damages filter
        if min_damages is not None or max_damages is not None:
            damage_val = extract_damages_value(case)
            if damage_val is None:
                continue
            if min_damages is not None and damage_val < min_damages:
                continue
            if max_damages is not None and damage_val > max_damages:
                continue

        # Apply category filter if specified
        if selected_regions:
            case_categories = case.get("regions") or case.get("extended_data", {}).get("regions") or []
            if not case_categories:
                continue

            lower_case_categories = {str(c).strip().lower() for c in case_categories}
            lower_sel = {str(c).strip().lower() for c in selected_regions}

            if not (lower_case_categories & lower_sel):
                continue

        # Apply gender filter
        if gender:
            ext = case.get("extended_data", {})
            case_gender = ext.get("sex") or case.get("sex")
            if case_gender and case_gender.upper() != gender.upper()[0]:
                continue

        # Apply age filter
        if age is not None:
            ext = case.get("extended_data", {})
            case_age = ext.get("age") or case.get("age")
            if case_age is not None:
                age_diff = abs(case_age - age)
                if age_diff > age_range:
                    continue

        # Get searchable text from case based on selected fields
        text_parts = []
        ext = case.get('extended_data', {})

        if 'case_name' in search_fields:
            case_name = case.get('case_name', '')
            if case_name:
                text_parts.append(case_name)

        if 'injuries' in search_fields:
            injuries = ext.get('injuries', [])
            if injuries:
                text_parts.extend([str(inj) for inj in injuries])

        if 'comments' in search_fields:
            comments = ext.get('comments') or case.get('comments')
            if comments:
                text_parts.append(str(comments))

        if 'summary' in search_fields:
            summary = case.get('summary_text', '')
            if summary:
                text_parts.append(summary)

        # Combine all text
        case_text = ' '.join(text_parts).lower()

        # Evaluate Boolean expression
        if _evaluate_boolean_query(query, case_text):
            matching_cases.append(case)

    return matching_cases


def _evaluate_boolean_query(query: str, text: str) -> bool:
    """
    Evaluate a Boolean query against text.

    Args:
        query: Boolean query string
        text: Text to search in (should be lowercase)

    Returns:
        True if query matches text, False otherwise
    """
    # Handle quoted phrases
    phrase_pattern = r'"([^"]+)"'
    phrases = re.findall(phrase_pattern, query)
    phrase_map = {}

    # Replace phrases with placeholders
    modified_query = query
    for i, phrase in enumerate(phrases):
        placeholder = f"__PHRASE_{i}__"
        phrase_map[placeholder] = phrase.lower()
        modified_query = modified_query.replace(f'"{phrase}"', placeholder)

    # Normalize query
    modified_query = modified_query.upper()
    text_lower = text.lower()

    # Split by OR first (lowest precedence)
    or_parts = re.split(r'\s+OR\s+', modified_query)

    for or_part in or_parts:
        # Split by AND (higher precedence), but keep NOT as part of the next term
        # Treat consecutive terms without operators as implicitly ANDed
        and_parts = []
        tokens = or_part.split()

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == "AND":
                # Skip the AND operator itself
                i += 1
                continue
            elif token == "NOT" and i + 1 < len(tokens):
                # NOT term is treated as a single unit
                and_parts.append(f"NOT {tokens[i + 1]}")
                i += 2
            else:
                # Regular term
                and_parts.append(token)
                i += 1

        all_and_matched = True
        for and_part in and_parts:
            and_part = and_part.strip()

            # Handle NOT
            if and_part.startswith('NOT '):
                term = and_part[4:].strip()

                # Check if it's a phrase placeholder
                if term in phrase_map:
                    if phrase_map[term] in text_lower:
                        all_and_matched = False
                        break
                else:
                    if term.lower() in text_lower:
                        all_and_matched = False
                        break
            else:
                # Regular term or phrase
                if and_part in phrase_map:
                    if phrase_map[and_part] not in text_lower:
                        all_and_matched = False
                        break
                else:
                    if and_part.lower() not in text_lower:
                        all_and_matched = False
                        break

        # If all AND conditions matched in this OR branch, return True
        if all_and_matched:
            return True

    # None of the OR branches matched
    return False
