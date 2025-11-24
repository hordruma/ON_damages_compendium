"""
Data loading and caching functions for the Ontario Damages Compendium.

This module handles loading case data, embeddings, and region mappings
with appropriate caching for performance.
"""

import streamlit as st
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import Optional, List, Dict, Any

from .config import EMBEDDING_MODEL_NAME, DATA_FILE_PATH, REGION_MAP_PATH


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


def initialize_data() -> tuple:
    """
    Initialize all required data for the application.

    Loads:
    1. Embedding model
    2. Case data
    3. Region mapping

    Returns:
        Tuple of (model, cases, region_map)

    Raises:
        SystemExit: If case data cannot be loaded (via st.stop())
    """
    model = load_embedding_model()
    cases = load_cases()
    region_map = load_region_map()

    if cases is None:
        st.stop()

    return model, cases, region_map
