# Dual Embedding System for Injury Matching

## Overview

The search system now implements a **dual embedding approach** for injury matching, where two separate embedding computations compete alongside string-based matching. This provides more nuanced and accurate injury matching.

## Architecture

### 5-Component Hybrid Search System

1. **Semantic Similarity (Full Text)** - `semantic_weight` (default: 0.15)
   - Embeds the full query text
   - Matches against case injury embeddings
   - Captures overall context and narrative

2. **Injury Embedding Matching** - `injury_embedding_weight` (default: 0.20)
   - Embeds only the extracted injury terms from query
   - Matches against case injury embeddings
   - Provides semantic similarity for injury-specific terms
   - Example: "TBI" will match "traumatic brain injury", "head injury", etc.

3. **Injury String Matching** - `injury_list_weight` (default: 0.20)
   - Direct string matching (exact/substring)
   - Fast and precise for known injury names
   - Example: "TBI" matches "TBI" or "mild TBI"

4. **Keyword/Text Matching** - `keyword_weight` (default: 0.35)
   - BM25 keyword matching
   - Searches comments, case names, summaries
   - Good for narrative descriptions

5. **Demographics/Metadata** - `meta_weight` (default: 0.10)
   - Age proximity, gender match, injury overlap
   - Redistributed to injury embeddings when no category filter applied

## How It Works

### Query Processing

```python
# Input query: "traumatic brain injury, C5-C6 disc herniation"

# Step 1: Parse comma-separated injuries
query_injuries = ["traumatic brain injury", "C5-C6 disc herniation"]

# Step 2: Create dual embeddings
qv_full = model.encode("traumatic brain injury, C5-C6 disc herniation")
qv_injury = model.encode("traumatic brain injury, C5-C6 disc herniation")  # Same in this case

# Step 3: Compute similarities
semantic_sim_full = cosine_similarity(qv_full, case_embeddings)      # Full text
semantic_sim_injury = cosine_similarity(qv_injury, case_embeddings)  # Injury-focused

# Step 4: Combine with other scores
combined_score = (
    0.15 * semantic_sim_full +
    0.20 * semantic_sim_injury +
    0.20 * string_match_score +
    0.35 * keyword_score +
    0.10 * meta_score
)
```

### Competition Between Methods

The system creates healthy competition between three injury matching approaches:

| Method | Type | Strengths | Use Case |
|--------|------|-----------|----------|
| **Injury String Matching** | Exact/Substring | Fast, precise | Known injury terms |
| **Injury Embedding Matching** | Semantic | Finds similar concepts | Synonyms, related injuries |
| **Semantic (Full Text)** | Contextual | Understands narrative | Complex descriptions |

### Example: Query = "head injury"

**Injury String Matching (0.20):**
- ✅ "head injury" → 1.0 (exact match)
- ❌ "traumatic brain injury" → 0.0 (no substring)
- ❌ "skull fracture" → 0.0 (no match)

**Injury Embedding Matching (0.20):**
- ✅ "head injury" → 0.95 (very similar)
- ✅ "traumatic brain injury" → 0.88 (semantic match)
- ✅ "skull fracture" → 0.72 (related injury)

**Semantic Full Text (0.15):**
- Captures overall context
- May match "plaintiff suffered severe head trauma" even without exact injury name

## UI Configuration

### Presets

Four presets are available with optimized weight distributions:

1. **Balanced (Default)**
   - Injury String: 20%, Injury Embedding: 20%, Keyword: 35%, Semantic: 15%, Meta: 10%
   - Good for general use

2. **Story/Narrative Focus**
   - Injury String: 15%, Injury Embedding: 15%, Keyword: 50%, Semantic: 10%, Meta: 10%
   - Best for detailed narrative descriptions

3. **Injury Name Focus**
   - Injury String: 30%, Injury Embedding: 30%, Keyword: 20%, Semantic: 10%, Meta: 10%
   - Best for searches with specific injury terms

4. **Similar Cases (Semantic)**
   - Injury String: 20%, Injury Embedding: 25%, Keyword: 20%, Semantic: 25%, Meta: 10%
   - Best for finding conceptually similar cases

### Custom Weights

Users can adjust each weight individually:

```python
injury_list_weight = 0.20          # String matching
injury_embedding_weight = 0.20     # Injury-specific embeddings
keyword_weight = 0.35              # BM25 keyword matching
semantic_weight = 0.15             # Full-text embeddings
meta_weight = 0.10                 # Demographics/metadata
```

Weights are automatically normalized to sum to 1.0.

## Technical Implementation

### Files Modified

1. **app/core/search.py**
   - Added `injury_embedding_weight` parameter to `search_cases()`
   - Implemented dual embedding computation
   - Updated scoring algorithm

2. **streamlit_app.py**
   - Updated presets with new weight distributions
   - Added injury embedding weight slider
   - Updated UI descriptions

### Key Functions

```python
def search_cases(
    query_text: str,
    ...,
    semantic_weight: float = 0.15,
    injury_embedding_weight: float = 0.20,
    injury_list_weight: float = 0.20,
    ...
)
```

### Embedding Generation

Both embeddings use the same model (all-MiniLM-L6-v2) and compare against the same case embeddings (generated from case injuries). The difference is in what gets embedded:

- **Full text embedding**: Entire query as-is
- **Injury embedding**: Extracted comma-separated injury terms only

## Benefits

1. **Better Semantic Matching**: Injury embeddings catch synonyms and related terms
2. **Preserves Precision**: String matching still available for exact matches
3. **Flexible Tuning**: Users can adjust weights to their preference
4. **Context Awareness**: Full-text embeddings capture narrative context

## Performance

- **Minimal Overhead**: Only adds one additional embedding computation per query (~50ms)
- **Same Embedding Matrix**: Uses existing case injury embeddings
- **Configurable Weights**: Can be adjusted based on use case

## Future Enhancements

Possible improvements:
- Multi-embedding caching for repeat queries
- Dynamic weight adjustment based on query characteristics
- Ensemble learning to optimize weight combinations
- Injury-specific embedding models trained on medical corpora

## Notes

- Injuries are already displayed in the UI (lines 162-185 of streamlit_app.py)
- The display_enhanced_data() function shows injuries in a 2-column layout
- All plaintiffs' injuries are properly extracted and deduplicated
- FLA claims remain separate from injury categories as intended
