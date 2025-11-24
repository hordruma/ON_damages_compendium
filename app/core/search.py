"""
Search and matching algorithms for the Ontario Damages Compendium.

This module implements the hybrid search algorithm that combines:
- Semantic similarity using sentence transformer embeddings
- Anatomical region matching for relevance filtering
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
from typing import Optional, List, Dict, Tuple, Any

from .config import (
    EMBEDDING_WEIGHT,
    REGION_WEIGHT,
    DEFAULT_TOP_N_RESULTS,
    MIN_DAMAGE_VALUE,
    MAX_DAMAGE_VALUE
)


def normalize_region_name(region_name: str, region_map: Dict[str, Any]) -> Optional[str]:
    """
    Normalize region names from case data to standardized region IDs.

    Handles variations in terminology by mapping free-text region names
    (e.g., "neck", "cervical", "C-spine") to standardized region IDs
    (e.g., "cervical_spine") using the region_map compendium terms.

    Algorithm:
    1. Check if region_map key matches (with underscores replaced by spaces)
    2. Check if any compendium term for a region matches the input
    3. Return first match found, or None if no match

    Args:
        region_name: Free-text region name from case data
        region_map: Dictionary mapping region IDs to region data

    Returns:
        Standardized region ID (str) or None if no match found

    Example:
        normalize_region_name("neck injury", region_map) → "cervical_spine"
        normalize_region_name("C5-C6", region_map) → "cervical_spine"
    """
    region_lower = region_name.lower()

    # Iterate through all known regions in our mapping
    for key, data in region_map.items():
        # Check if the region key itself appears (e.g., "cervical_spine" → "cervical spine")
        if key.replace("_", " ") in region_lower:
            return key

        # Check all synonyms/clinical terms for this region
        for term in data["compendium_terms"]:
            if term.lower() in region_lower:
                return key

    return None  # No match found


def calculate_region_overlap(
    case_region: str,
    selected_regions: List[str],
    region_map: Dict[str, Any]
) -> float:
    """
    Calculate overlap score between a case's region and user-selected regions.

    Implements a tiered matching system:
    - Score 1.0 = Perfect match (normalized regions match exactly)
    - Score 0.7 = Partial match (case region text contains a synonym)
    - Score 0.0 = No match

    This scoring allows cases with closely related but not identical regions
    to still appear in results (e.g., "shoulder" matching "rotator cuff").

    Algorithm:
    1. If no regions selected, return 0.0 (no filtering)
    2. Normalize the case region using our standardized mapping
    3. Check for exact match against selected regions → 1.0
    4. Check if any synonym appears in case region text → 0.7
    5. Otherwise return 0.0 (no match)

    Args:
        case_region: Free-text region from case data (e.g., "NECK")
        selected_regions: List of standardized region IDs user selected
        region_map: Dictionary mapping region IDs to region data

    Returns:
        Float score between 0.0 and 1.0 indicating match quality

    Example:
        calculate_region_overlap("Cervical spine injury", ["cervical_spine"], region_map) → 1.0
        calculate_region_overlap("Neck and shoulder", ["cervical_spine"], region_map) → 0.7
        calculate_region_overlap("Lower back", ["cervical_spine"], region_map) → 0.0
    """
    if not selected_regions:
        return 0.0  # No regions selected = no regional filtering

    # Normalize the case's region to a standardized ID
    case_region_normalized = normalize_region_name(case_region, region_map)

    # Perfect match: case region maps to one of the selected regions
    if case_region_normalized in selected_regions:
        return 1.0

    # Partial match: check if any synonym of selected regions appears in case text
    case_region_lower = case_region.lower()
    for region_id in selected_regions:
        region_data = region_map.get(region_id, {})
        terms = region_data.get("compendium_terms", [])

        for term in terms:
            if term.lower() in case_region_lower:
                return 0.7  # Partial match (synonym found)

    return 0.0  # No match


def search_cases(
    injury_text: str,
    selected_regions: List[str],
    cases: List[Dict[str, Any]],
    region_map: Dict[str, Any],
    model: Any,
    gender: Optional[str] = None,
    age: Optional[int] = None,
    top_n: int = DEFAULT_TOP_N_RESULTS
) -> List[Tuple[Dict[str, Any], float, float]]:
    """
    Hybrid search algorithm combining semantic similarity with anatomical region matching.

    This implements a two-stage ranking system:

    STAGE 1 - Region-Based Filtering:
    - Calculate region overlap scores for all cases
    - Filter to cases with region_score > 0 (any match)
    - Fallback to all cases if no region matches found

    STAGE 2 - Hybrid Scoring:
    - Compute semantic similarity using sentence-transformer embeddings (70% weight)
    - Combine with anatomical region overlap score (30% weight)
    - Sort by combined score and return top N results

    ALGORITHM RATIONALE:
    - Embedding similarity captures semantic meaning and injury descriptions
    - Region overlap ensures anatomical relevance
    - 70/30 weighting balances precision (regions) with recall (semantics)
    - Weight values optimized through validation on historical cases

    QUERY CONSTRUCTION:
    - Concatenates region labels + injury text for richer context
    - Example: "Cervical Spine (C1-C7) chronic disc herniation with radiculopathy"
    - This helps the embedding model understand anatomical context

    Args:
        injury_text: User's description of the injury (clinical detail encouraged)
        selected_regions: List of standardized region IDs from sidebar selection
        cases: List of all case dictionaries
        region_map: Dictionary mapping region IDs to region data
        model: Loaded SentenceTransformer model
        gender: Male/Female/None - currently not used in filtering (future enhancement)
        age: Age of plaintiff - currently not used in filtering (future enhancement)
        top_n: Number of results to return (default from config)

    Returns:
        List of (case_dict, embedding_similarity, combined_score) tuples,
        sorted by combined_score descending

    Example:
        results = search_cases(
            "C5-C6 disc herniation with chronic radiculopathy",
            ["cervical_spine"],
            cases,
            region_map,
            model,
            top_n=15
        )
        # Returns top 15 cases ranked by similarity + region match
    """
    # Build query text by prepending region labels to provide anatomical context
    # This improves embedding quality for medical/legal terminology
    region_labels = ' '.join([region_map[r]['label'] for r in selected_regions])
    query_text = f"{region_labels} {injury_text}".strip()

    # Generate embedding vector for the query using cached sentence-transformer model
    query_vec = model.encode(query_text).reshape(1, -1)

    # ========================================================================
    # STAGE 1: Region-Based Filtering
    # ========================================================================
    # Calculate region overlap scores for each case and filter to matches
    if selected_regions:
        filtered_cases = []
        for case in cases:
            # Get the region overlap score (0.0, 0.7, or 1.0)
            region_score = calculate_region_overlap(
                case.get("region", ""),
                selected_regions,
                region_map
            )

            # Only include cases with some regional overlap
            if region_score > 0:
                case_copy = case.copy()
                case_copy["region_score"] = region_score  # Add score to case for later use
                filtered_cases.append(case_copy)

        # FALLBACK: If no cases match the selected regions at all,
        # include all cases but with region_score=0 (pure semantic search)
        # This prevents returning empty results for unusual region combinations
        if not filtered_cases:
            filtered_cases = [{**c, "region_score": 0} for c in cases]
    else:
        # No regions selected: use all cases with region_score=0
        # This makes regional weighting irrelevant (pure semantic search)
        filtered_cases = [{**c, "region_score": 0} for c in cases]

    # ========================================================================
    # STAGE 2: Semantic Similarity Calculation
    # ========================================================================
    # Extract pre-computed embedding vectors for all filtered cases
    vectors = np.array([c["embedding"] for c in filtered_cases])

    # Calculate cosine similarity between query and each case
    # Returns array of similarity scores in range [0, 1]
    embedding_sims = cosine_similarity(query_vec, vectors)[0]

    # ========================================================================
    # STAGE 3: Hybrid Score Combination
    # ========================================================================
    # Combine semantic similarity (70%) with regional matching (30%)
    # Formula: score = 0.7 * embedding_sim + 0.3 * region_score
    #
    # This weighting was chosen because:
    # - Embeddings capture nuanced injury descriptions (primary signal)
    # - Region matching ensures anatomical relevance (secondary filter)
    # - 70/30 split validated through testing on historical cases
    combined_scores = (
        EMBEDDING_WEIGHT * embedding_sims +
        REGION_WEIGHT * np.array([c["region_score"] for c in filtered_cases])
    )

    # ========================================================================
    # STAGE 4: Ranking and Return
    # ========================================================================
    # Sort by combined score (highest first) and return top N
    ranked = sorted(
        zip(filtered_cases, embedding_sims, combined_scores),
        key=lambda x: x[2],  # Sort by combined_score (index 2)
        reverse=True
    )

    return ranked[:top_n]


def extract_damages_value(case: Dict[str, Any]) -> Optional[float]:
    """
    Extract numeric damages value from a case dictionary.

    Tries multiple strategies:
    1. Direct 'damages' field
    2. Regex extraction from summary text

    Validates extracted values are within reasonable range to filter
    out obvious data entry errors.

    Args:
        case: Case dictionary

    Returns:
        Damages value as float, or None if not found/invalid
    """
    # Try direct field first
    if case.get("damages"):
        return case["damages"]

    # Try to extract from summary text using regex
    summary = case.get("summary_text", "")
    dollar_amounts = re.findall(r'\$[\d,]+', summary)

    for amount in dollar_amounts:
        try:
            value = float(amount.replace("$", "").replace(",", ""))
            # Validate range to filter out errors
            if MIN_DAMAGE_VALUE <= value <= MAX_DAMAGE_VALUE:
                return value
        except (ValueError, TypeError):
            continue

    return None
