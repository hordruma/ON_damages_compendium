# Comprehensive Testing Guide

This guide documents testing the injury-focused RAG search architecture.

## Test Scenarios

### 1. Injury-Focused Embedding Quality

Test that embeddings capture injury semantics correctly.

```python
from sentence_transformers import SentenceTransformer
import json

model = SentenceTransformer("all-MiniLM-L6-v2")

# Load sample cases
with open("data/compendium_inj.json") as f:
    cases = json.load(f)

# Test embedding quality
test_injury = "cervical disc herniation with radiculopathy"
test_emb = model.encode(test_injury)

# Find similar injuries
import numpy as np
injuries = np.load("data/embeddings_inj.npy")
norms = np.linalg.norm(injuries, axis=1, keepdims=True)
norm_injuries = injuries / norms

q_norm = test_emb / np.linalg.norm(test_emb)
sims = norm_injuries.dot(q_norm)

# Check top matches
top_idx = np.argsort(-sims)[:5]
for idx in top_idx:
    print(f"Similarity: {sims[idx]:.3f}, Search text: {cases[idx]['search_text'][:80]}")
```

### 2. Exclusive Region Filtering

Test that region filters correctly limit candidate set.

```python
from app.core.search import search_cases
from app.core.data_loader import initialize_data

model, cases, region_map = initialize_data()

# Test with different region selections
test_query = "neck pain and stiffness"
selected_regions = ["cervical_spine"]  # exclusive filter

results = search_cases(
    test_query,
    selected_regions,
    cases,
    region_map,
    model,
    top_n=10
)

print(f"Found {len(results)} cases with cervical spine region")
for case, inj_sim, combined_score in results[:3]:
    regions = case.get('regions', [])
    print(f"  {case['case_name']}: {regions}")
```

### 3. Meta-Score Computation

Test injury overlap and demographic scoring.

```python
from app.core.search import compute_meta_score

# Create test case
test_case = {
    "extended_data": {
        "injuries": ["cervical disc herniation", "radiculopathy"],
        "sex": "male",
        "age": 45
    }
}

# Test scoring
meta_score = compute_meta_score(
    test_case,
    query_injuries=["cervical disc herniation"],  # would be empty in real usage
    query_gender="Male",
    query_age=45
)

print(f"Meta score: {meta_score:.3f}")  # Should be high (injury + gender + age match)
```

### 4. Search with No Minimum Threshold

Test that all results are returned sorted by relevance.

```python
# Run search
results = search_cases(
    "traumatic brain injury",
    [],  # no region filter
    cases,
    region_map,
    model,
    top_n=25
)

print(f"Returned {len(results)} results (all sorted by relevance, no cutoff)")

# Check score distribution
scores = [combined_score for _, _, combined_score in results]
print(f"Min score: {min(scores):.3f}, Max score: {max(scores):.3f}")
print(f"Score distribution: {scores[:5]}")  # First 5 scores
```

### 5. Camelot Table Extraction Validation

Test that camelot correctly extracts tables from PDF.

```python
import camelot

# Test on sample page
tables = camelot.read_pdf("2024damagescompendium.pdf", pages="1-5")

print(f"Extracted {len(tables)} tables from pages 1-5")

for i, table in enumerate(tables):
    print(f"\nTable {i}: {table.shape[0]} rows x {table.shape[1]} columns")
    print("Sample rows:")
    print(table.df.iloc[:2].to_string())
```

### 6. End-to-End Pipeline

Test complete search pipeline from query to results.

```python
import streamlit as st
from app.core.data_loader import initialize_data
from app.core.search import search_cases, extract_damages_value

# Initialize
model, cases, region_map = initialize_data()

# Test query
injury_description = "Motor vehicle accident: significant cervical and lumbar strain with chronic pain and functional limitations"
selected_regions = ["cervical_spine", "lumbar_spine"]
gender = "Male"
age = 42

# Search
results = search_cases(
    injury_description,
    selected_regions,
    cases,
    region_map,
    model,
    gender=gender,
    age=age,
    top_n=15
)

print(f"Found {len(results)} comparable cases")

# Display results
for idx, (case, inj_sim, combined_score) in enumerate(results[:5], 1):
    damages = extract_damages_value(case)
    print(f"\n{idx}. {case['case_name']}")
    print(f"   Injury similarity: {inj_sim:.3f}")
    print(f"   Combined score: {combined_score:.3f}")
    print(f"   Damages: ${damages:,.0f}" if damages else "   Damages: N/A")
    print(f"   Regions: {case.get('regions', 'N/A')}")
```

## Test Cases to Validate

1. **Cervical Spine Injuries**: Search for "C5-C6 disc herniation with radiculopathy"
   - Should return cervical spine cases
   - Should not return lumbar spine cases

2. **Multiple Regions**: Filter on multiple regions simultaneously
   - Should only return cases with at least one selected region

3. **Age/Gender Filtering**: Test with same injury but different demographics
   - Meta-score should adjust based on age/gender proximity

4. **No Minimum Threshold**: Verify all results shown
   - Even low-scoring results should be displayed
   - Results should be sorted by relevance

5. **Expert Report Analysis**: Upload a sample medical report
   - Should extract injuries and sequelae correctly
   - Should populate search field with extracted info

6. **Inflation Adjustment**: Test damages inflation adjustment
   - Awards from different years should be normalized to reference year

## Performance Benchmarks

Track performance metrics:

```python
import time

# Measure search latency
start = time.time()
results = search_cases(query_text, selected_regions, cases, region_map, model)
latency = time.time() - start
print(f"Search latency: {latency:.3f}s for {len(results)} results")

# Measure memory usage
import sys
emb_size = sys.getsizeof(emb_matrix)
print(f"Embedding matrix size: {emb_size / 1024 / 1024:.1f} MB")
```

## Known Limitations

1. **Scalability**: Current implementation loads full embedding matrix in memory
   - Works well for ~5000 cases
   - For >10k cases consider FAISS indexing

2. **Camelot Dependency**: Requires graphical backend for table detection
   - May need configuration on headless systems
   - Consider PDFPlumber as fallback for simple tables

3. **Expert Report**: LLM extraction requires API key
   - Fallback to regex extraction without API key
   - Accuracy depends on report format consistency

## Improvement Opportunities

1. Implement FAISS index for large-scale retrieval
2. Add BM25 keyword search as fallback for low-confidence results
3. Implement streaming/pagination for large result sets
4. Add result explanation (why this case matched)
5. Create evaluation set and measure precision@k metrics
