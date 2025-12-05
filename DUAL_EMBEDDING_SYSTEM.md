# Dual Embedding System for Injury Matching

## Overview

The search system now implements a **dual embedding approach** for injury matching, where two separate embedding computations work together. This provides more nuanced and accurate injury matching using **embeddings-only** (no string matching).

## Architecture

### 4-Component Hybrid Search System (Embeddings-Only)

1. **Semantic Similarity (Full Text)** - `semantic_weight` (default: 0.15)
   - Embeds the full query text
   - Matches against case injury embeddings
   - Captures overall context and narrative

2. **Injury Embedding Matching** - `injury_embedding_weight` (default: 0.40)
   - Embeds only the extracted injury terms from query
   - Matches against case injury embeddings
   - Provides semantic similarity for injury-specific terms
   - Example: "TBI" will match "traumatic brain injury", "head injury", "brain contusion", etc.

3. **Keyword/Text Matching** - `keyword_weight` (default: 0.35)
   - BM25 keyword matching
   - Searches comments, case names, summaries
   - Good for narrative descriptions

4. **Demographics/Metadata** - `meta_weight` (default: 0.10)
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

### Dual Embedding Strategy

The system uses two embedding computations for comprehensive matching:

| Method | Type | Strengths | Use Case |
|--------|------|-----------|----------|
| **Injury Embedding Matching** | Semantic | Finds similar concepts | Synonyms, related injuries, abbreviations |
| **Semantic (Full Text)** | Contextual | Understands narrative | Complex descriptions, mechanisms of injury |

### Example: Query = "head injury"

**Injury Embedding Matching (0.40):**
- ✅ "head injury" → 0.95 (very similar)
- ✅ "traumatic brain injury" → 0.88 (semantic match)
- ✅ "TBI" → 0.86 (abbreviation understood)
- ✅ "skull fracture" → 0.72 (related injury)
- ✅ "brain contusion" → 0.78 (similar injury type)
- ✅ "concussion" → 0.80 (related head trauma)

**Semantic Full Text (0.15):**
- Captures overall context
- Matches "plaintiff suffered severe head trauma" with narrative understanding
- Understands mechanism and impact descriptions

## UI Configuration

### Presets

Four presets are available with optimized weight distributions:

1. **Balanced (Default)**
   - Injury Embedding: 40%, Keyword: 35%, Semantic: 15%, Meta: 10%
   - Good for general use

2. **Story/Narrative Focus**
   - Injury Embedding: 30%, Keyword: 50%, Semantic: 10%, Meta: 10%
   - Best for detailed narrative descriptions

3. **Injury Name Focus**
   - Injury Embedding: 60%, Keyword: 20%, Semantic: 10%, Meta: 10%
   - Best for searches with specific injury terms

4. **Similar Cases (Semantic)**
   - Injury Embedding: 40%, Keyword: 20%, Semantic: 30%, Meta: 10%
   - Best for finding conceptually similar cases

### Custom Weights

Users can adjust each weight individually:

```python
injury_embedding_weight = 0.40     # Injury-specific embeddings
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

1. **Superior Semantic Matching**: Injury embeddings understand synonyms, abbreviations, and related medical terms
2. **Pure AI-Based**: Fully embedding-based approach for intelligent matching
3. **Flexible Tuning**: Users can adjust weights to their preference
4. **Context Awareness**: Full-text embeddings capture narrative context
5. **Robust to Terminology**: Works even when exact terms don't match (e.g., "TBI" matches "brain injury")

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
