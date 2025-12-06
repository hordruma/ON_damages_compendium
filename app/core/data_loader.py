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
    AI_PARSED_JSON_PATH
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
    Detect whether JSON data is in AI-parsed or dashboard format.

    Args:
        data: List of case dictionaries

    Returns:
        "ai_parsed" or "dashboard"
    """
    if not data:
        return "unknown"

    sample = data[0]

    # AI-parsed format has 'plaintiffs' array and 'case_id'
    if 'plaintiffs' in sample and isinstance(sample.get('plaintiffs'), list):
        return "ai_parsed"

    # Dashboard format has 'embedding' and 'summary_text'
    if 'embedding' in sample and 'summary_text' in sample:
        return "dashboard"

    return "unknown"


def convert_ai_to_dashboard_inline(
    ai_cases: List[Dict[str, Any]],
    model: SentenceTransformer
) -> List[Dict[str, Any]]:
    """
    Convert AI-parsed format to dashboard format inline.

    This is a lightweight version that imports the transformer
    on-demand to avoid circular dependencies.

    Args:
        ai_cases: Cases in AI-parsed format
        model: SentenceTransformer model for embeddings

    Returns:
        Cases in dashboard format
    """
    try:
        from data_transformer import convert_to_dashboard_format
        return convert_to_dashboard_format(ai_cases, model)
    except ImportError:
        st.error("⚠️ data_transformer module not found")
        return []


def load_cases_auto() -> Optional[List[Dict[str, Any]]]:
    """
    Auto-detect and load case data in either format.

    Tries to load from:
    1. Standard dashboard JSON (pre-computed embeddings)
    2. AI-parsed JSON (with auto-conversion)

    Returns:
        List of case dictionaries in dashboard format, or None if not found
    """
    data_path = Path(DATA_FILE_PATH)
    ai_parsed_path = Path(AI_PARSED_JSON_PATH)

    # Try standard dashboard format first
    if data_path.exists():
        try:
            with open(data_path) as f:
                data = json.load(f)

            format_type = detect_json_format(data)

            if format_type == "dashboard":
                return data
            elif format_type == "ai_parsed":
                # Auto-convert with progress indicator
                st.info("📊 Converting AI-parsed data to dashboard format... This may take a moment.")
                model = load_embedding_model()
                return convert_ai_to_dashboard_inline(data, model)
        except Exception as e:
            st.error(f"❌ Error loading data from {data_path}: {str(e)}")
            st.info("Trying alternative data source...")

    # Try AI-parsed format
    if ai_parsed_path.exists():
        try:
            with open(ai_parsed_path) as f:
                data = json.load(f)

            format_type = detect_json_format(data)

            if format_type == "ai_parsed":
                # Convert with progress indicator
                st.info("📊 Converting AI-parsed data to dashboard format... This may take a moment.")
                model = load_embedding_model()
                converted = convert_ai_to_dashboard_inline(data, model)

                # Save for future use
                try:
                    data_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(data_path, 'w') as f:
                        json.dump(converted, f, indent=2)
                    st.success("✅ Converted data saved for faster loading next time!")
                except Exception as e:
                    st.warning(f"⚠️ Could not save converted data: {str(e)}")

                return converted
        except Exception as e:
            st.error(f"❌ Error loading data from {ai_parsed_path}: {str(e)}")

    # Not found
    st.error(f"❌ Data file not found: {data_path}")
    st.info(
        "Please either:\n"
        "1. Run `01_extract_and_embed.ipynb` to generate the data, or\n"
        "2. Place AI-parsed `damages_full.json` in the project root"
    )
    return None


@st.cache_data
def _cached_load_cases() -> Optional[List[Dict[str, Any]]]:
    """Cached wrapper for load_cases_auto() to avoid re-computing on every rerun."""
    return load_cases_auto()


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

    # Check if we have cached data first
    if 'cases_loaded' not in st.session_state:
        with st.spinner("🔄 Loading case data... This may take a moment on first load."):
            cases = _cached_load_cases()
            if cases is not None:
                st.session_state.cases_loaded = True
    else:
        # Use cached version without spinner
        cases = _cached_load_cases()

    region_map = load_region_map()

    if cases is None:
        st.stop()

    return model, cases, region_map
