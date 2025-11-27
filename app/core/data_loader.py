"""
Data loading and caching functions for the Ontario Damages Compendium.

This module handles loading case data, embeddings, and region mappings
with appropriate caching for performance.

Supports both:
- Legacy dashboard format (pre-computed embeddings)
- Gemini-parsed format (with auto-conversion)
"""

import streamlit as st
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import Optional, List, Dict, Any

from .config import (
    EMBEDDING_MODEL_NAME,
    DATA_FILE_PATH,
    REGION_MAP_PATH,
    GEMINI_FULL_JSON_PATH
)


@st.cache_resource
def load_embedding_model() -> SentenceTransformer:
    """
    Load the sentence transformer model for semantic search.

    Uses Streamlit's cache_resource to avoid reloading the model
    on every interaction. The model persists across reruns.

    Returns:
        Loaded SentenceTransformer model
    """
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


@st.cache_data
def load_cases() -> Optional[List[Dict[str, Any]]]:
    """
    Load case data with pre-computed embeddings.

    Expects a JSON file with case data including:
    - case_name: Name of the case
    - year: Year of the decision
    - region: Anatomical region involved
    - damages: Award amount
    - summary_text: Case summary
    - embedding: Pre-computed vector embedding

    Returns:
        List of case dictionaries, or None if file not found
    """
    data_path = Path(DATA_FILE_PATH)

    if not data_path.exists():
        st.error(f"❌ Data file not found: {data_path}")
        st.info(
            "Please run the `01_extract_and_embed.ipynb` notebook first "
            "to generate the data with embeddings."
        )
        return None

    with open(data_path) as f:
        return json.load(f)


@st.cache_data
def load_region_map() -> Dict[str, Any]:
    """
    Load anatomical region mapping data.

    The region map contains standardized region IDs mapped to:
    - label: Clinical terminology (e.g., "Cervical Spine (C1-C7)")
    - compendium_terms: List of synonyms for matching

    Returns:
        Dictionary mapping region IDs to region data
    """
    with open(REGION_MAP_PATH) as f:
        return json.load(f)


def detect_json_format(data: List[Dict[str, Any]]) -> str:
    """
    Detect whether JSON data is in Gemini or dashboard format.

    Args:
        data: List of case dictionaries

    Returns:
        "gemini" or "dashboard"
    """
    if not data:
        return "unknown"

    sample = data[0]

    # Gemini format has 'plaintiffs' array and 'case_id'
    if 'plaintiffs' in sample and isinstance(sample.get('plaintiffs'), list):
        return "gemini"

    # Dashboard format has 'embedding' and 'summary_text'
    if 'embedding' in sample and 'summary_text' in sample:
        return "dashboard"

    return "unknown"


def convert_gemini_to_dashboard_inline(
    gemini_cases: List[Dict[str, Any]],
    model: SentenceTransformer
) -> List[Dict[str, Any]]:
    """
    Convert Gemini format to dashboard format inline.

    This is a lightweight version that imports the transformer
    on-demand to avoid circular dependencies.

    Args:
        gemini_cases: Cases in Gemini format
        model: SentenceTransformer model for embeddings

    Returns:
        Cases in dashboard format
    """
    try:
        from gemini_data_transformer import convert_gemini_to_dashboard_format
        return convert_gemini_to_dashboard_format(gemini_cases, model)
    except ImportError:
        st.error("⚠️ gemini_data_transformer module not found")
        return []


@st.cache_data
def load_cases_auto() -> Optional[List[Dict[str, Any]]]:
    """
    Auto-detect and load case data in either format.

    Tries to load from:
    1. Standard dashboard JSON (pre-computed embeddings)
    2. Gemini-parsed JSON (with auto-conversion)

    Returns:
        List of case dictionaries in dashboard format, or None if not found
    """
    data_path = Path(DATA_FILE_PATH)
    gemini_path = Path(GEMINI_FULL_JSON_PATH)

    # Try standard dashboard format first
    if data_path.exists():
        with open(data_path) as f:
            data = json.load(f)

        format_type = detect_json_format(data)

        if format_type == "dashboard":
            return data
        elif format_type == "gemini":
            # Auto-convert
            st.info("🔄 Detected Gemini format, converting to dashboard format...")
            model = load_embedding_model()
            return convert_gemini_to_dashboard_inline(data, model)

    # Try Gemini format
    if gemini_path.exists():
        st.info(f"📂 Loading from Gemini format: {gemini_path}")
        with open(gemini_path) as f:
            data = json.load(f)

        format_type = detect_json_format(data)

        if format_type == "gemini":
            st.info("🔄 Converting Gemini format to dashboard format...")
            model = load_embedding_model()
            converted = convert_gemini_to_dashboard_inline(data, model)

            # Save for future use
            st.info(f"💾 Saving converted data to {DATA_FILE_PATH}...")
            data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(data_path, 'w') as f:
                json.dump(converted, f, indent=2)

            return converted

    # Not found
    st.error(f"❌ Data file not found: {data_path}")
    st.info(
        "Please either:\n"
        "1. Run `01_extract_and_embed.ipynb` to generate the data, or\n"
        "2. Place Gemini-parsed `damages_full.json` in the project root"
    )
    return None


def initialize_data() -> tuple:
    """
    Initialize all required data for the application.

    Loads:
    1. Embedding model
    2. Case data (auto-detecting format)
    3. Region mapping

    Returns:
        Tuple of (model, cases, region_map)

    Raises:
        SystemExit: If case data cannot be loaded (via st.stop())
    """
    model = load_embedding_model()
    cases = load_cases_auto()  # Use auto-detection
    region_map = load_region_map()

    if cases is None:
        st.stop()

    return model, cases, region_map
