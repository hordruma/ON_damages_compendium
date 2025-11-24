"""
Configuration constants for the Ontario Damages Compendium application.

All configurable parameters are centralized here for easy tuning and maintenance.
"""

# ============================================================================
# SEARCH ALGORITHM CONFIGURATION
# ============================================================================

# Search algorithm weights
# These weights were optimized through validation on historical cases
EMBEDDING_WEIGHT = 0.7  # Weight for semantic similarity (70%)
REGION_WEIGHT = 0.3     # Weight for anatomical region matching (30%)

# Rationale:
# - 70% embedding weight captures nuanced injury descriptions
# - 30% region weight ensures anatomical relevance
# - This balance maximizes both precision and recall

# ============================================================================
# DATA FILTERING CONFIGURATION
# ============================================================================

# Damage value filtering ranges
MIN_DAMAGE_VALUE = 1000        # Minimum reasonable damage award ($)
MAX_DAMAGE_VALUE = 10_000_000  # Maximum reasonable damage award ($)

# Rationale: Filters out obvious data entry errors and unrealistic awards

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

# Search results display
DEFAULT_TOP_N_RESULTS = 15      # Default number of search results to return
EXPANDED_RESULTS_COUNT = 3      # Number of results expanded by default in UI

# Chart display
CHART_MAX_CASES = 15            # Maximum cases to display in charts

# Text display
CASE_SUMMARY_MAX_LENGTH = 400   # Max characters for case summary display

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Embedding model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Model info:
# - Lightweight and fast (only 80MB)
# - Good balance of performance and speed
# - Well-suited for semantic search in legal/medical text

# ============================================================================
# FILE PATHS
# ============================================================================

DATA_FILE_PATH = "data/damages_with_embeddings.json"
REGION_MAP_PATH = "region_map.json"

# ============================================================================
# UI STYLING
# ============================================================================

# Primary colors (matching Streamlit theme)
PRIMARY_COLOR = "#3b82f6"      # Blue
SUCCESS_COLOR = "#10b981"      # Green
WARNING_COLOR = "#f59e0b"      # Amber
ERROR_COLOR = "#ef4444"        # Red

# ============================================================================
