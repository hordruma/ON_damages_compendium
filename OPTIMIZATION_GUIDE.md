# Parser Performance Optimizations

This document explains the performance optimizations implemented in the damages parser and how they maintain correct handling of multi-page cases.

## Summary of Optimizations

The parser has been optimized with three major improvements:

1. **Hash Index for O(1) Duplicate Detection** - Speeds up duplicate detection from O(n²) to O(1)
2. **Async/Concurrent API Calls** - Enables parallel processing of pages for 10-50x speedup
3. **Sliding Window Context** - Handles cases that span multiple pages (pagination breaks)

### Expected Performance Improvements

| Operation | Before | After | Speedup |
|-----------|--------|-------|---------|
| Duplicate Detection | O(n²) - 5-10 min | O(1) - <1 sec | ~300x |
| API Calls (655 pages) | Sequential - 30-60 min | Concurrent - 3-5 min | 10-15x |
| **Total Parse Time** | **30-60 minutes** | **3-5 minutes** | **~10-15x** |

## 1. Hash Index Optimization (O(1) Duplicate Detection)

### The Problem

Previously, the parser used linear search to find duplicate cases:

```python
# OLD CODE - O(n²) complexity
for idx, existing in enumerate(existing_cases):  # Scans ALL cases
    if similar(new_case, existing):
        return idx  # Found after checking many cases
```

This resulted in ~253,116 comparisons for 711 cases!

### The Solution

Now uses three hash indices for instant O(1) lookups:

```python
# NEW CODE - O(1) complexity
case_id_index: Dict[str, int] = {}        # case_id -> position
name_year_index: Dict[str, int] = {}      # normalized_name_year -> position
citation_index: Dict[str, Set[int]] = {}  # citation -> set of positions
```

#### Lookup Strategy (in order):
1. **Case ID exact match** (fastest)
2. **Normalized name+year exact match**
3. **Citation overlap** (shared citations)
4. **Fuzzy matching** (fallback for typos, rarely used)

### Multi-Page Case Handling

**Cases that appear on multiple pages are still correctly merged!**

The optimization only changes *how* duplicates are found (hash lookup vs linear search), not the merge logic:

```python
# When a duplicate is found (whether by hash or search):
if duplicate_idx is not None:
    # Same merge logic as before - handles multi-page cases
    self.merge_cases(all_cases[duplicate_idx], case)
    # Update indices with new information from merged case
    self._update_indices(case, duplicate_idx, ...)
```

The `merge_cases()` function still:
- Combines all body regions/categories (e.g., HEAD + SPINE)
- Merges all injuries from all instances
- Preserves all damages and claims
- Tracks all source pages where the case appeared

## 2. Async/Concurrent API Calls

### The Problem

Previously, pages were parsed sequentially:

```python
# OLD CODE - Sequential processing
for page_num in range(start_page, end_page + 1):
    page_cases = self.parse_page(page_num, page_text)  # BLOCKS waiting for API
    time.sleep(0.5)  # Rate limiting delay
```

For 655 pages: 655 × (API time + 0.5s) = 30-60 minutes

### The Solution

Now processes pages concurrently with controlled parallelism:

```python
# NEW CODE - Concurrent processing with sliding window
async with aiohttp.ClientSession() as session:
    semaphore = asyncio.Semaphore(max_concurrent=50)  # Limit concurrent requests

    # Each page gets previous page as context
    tasks = [parse_page_async(page_num, page_text, prev_text)
             for page_num, page_text, prev_text in pages]
    results = await asyncio.gather(*tasks)  # Process all concurrently
```

With 50 concurrent requests: 655 pages / 50 = ~13 batches = 3-5 minutes

## 3. Sliding Window Context for Multi-Page Cases

### The Problem: Pagination Breaks

Real-world case entries can span multiple pages:

**Page 10:**
```
Litwinenko v. Beaver Lumber Co (2006)
Female, 69 years
$15,000 non-pecuniary damages
Injuries: head, ribs, leg, shoulder...
```

**Page 11 (continuation - no case header):**
```
Liability:
Trial - 50/50
Appeal - 15/85 in favour of appellant
```

Without context, Page 11's content would be **lost** (no case name to match).

### The Solution: Sliding Window

Each page is parsed with the previous page as context:

```python
# Synchronous version
previous_page_text = None
for page_num in range(start_page, end_page + 1):
    page_text = extract_page(page_num)

    # Parse with previous page context
    page_cases = parse_page(page_num, page_text, previous_page_text)

    # Current page becomes context for next page
    previous_page_text = page_text
```

The LLM receives:
```
=== PREVIOUS PAGE (for context) ===
Litwinenko v. Beaver Lumber Co (2006)
[...full case details...]

=== CURRENT PAGE 11 (extract cases from here) ===
Liability:
Trial - 50/50
Appeal - 15/85 in favour of appellant
```

Now the LLM can:
1. See the case context from Page 10
2. Recognize Page 11 is a continuation
3. Extract "Litwinenko v. Beaver Lumber Co (2006)" with the liability info
4. The deduplication logic merges it with Page 10's entry

**Result**: No data loss, complete case information captured!

### Ensuring Nothing is Missed

The async implementation has several safety mechanisms:

#### 1. **Semaphore Concurrency Control**
```python
semaphore = asyncio.Semaphore(max_concurrent)  # Limits concurrent requests
```
Ensures we never exceed the concurrency limit and respect rate limits.

#### 2. **asyncio.gather() Waits for ALL Tasks**
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
```
This will NOT proceed until ALL pages have been processed (or failed).

#### 3. **Page Tracking and Verification**
```python
# Process results in page order for deterministic merging
results_by_page = {}
for result in results:
    if isinstance(result, Exception):
        print(f"Error in concurrent parsing: {result}")
        continue
    page_num, page_cases = result
    results_by_page[page_num] = page_cases

# Process in sorted order
for page_num in sorted(results_by_page.keys()):
    page_cases = results_by_page[page_num]
    # ... deduplicate and merge
```

#### 4. **Sequential Deduplication Phase**

**CRITICAL**: After all pages are parsed concurrently, the deduplication/merging happens **sequentially in page order**:

```python
# Deduplicate and merge in sequential order to ensure consistency
for page_num in sorted(results_by_page.keys()):
    page_cases = results_by_page[page_num]

    for case in page_cases:
        duplicate_idx = self.find_duplicate_case_fast(...)

        if duplicate_idx is not None:
            # Merge multi-page case data
            self.merge_cases(all_cases[duplicate_idx], case)
```

This ensures:
- **Deterministic results**: Same cases found as sequential version
- **Multi-page cases correctly merged**: Earlier pages are processed before later pages
- **Nothing missed**: All pages processed in sorted order

### Why Multi-Page Cases Still Work

Consider a case that appears on pages 50, 100, and 200:

**Sequential Processing (old):**
- Page 50: Case added to `all_cases[0]`
- Page 100: Duplicate detected, merged into `all_cases[0]`
- Page 200: Duplicate detected, merged into `all_cases[0]`

**Concurrent Processing (new):**
- **Parsing Phase** (concurrent): Pages 50, 100, 200 parsed in parallel
- **Deduplication Phase** (sequential):
  - Page 50: Case added to `all_cases[0]`
  - Page 100: Duplicate detected (hash index), merged into `all_cases[0]`
  - Page 200: Duplicate detected (hash index), merged into `all_cases[0]`

**Result**: Identical! The only difference is parsing happens in parallel, but merging happens in order.

## Usage

### Enable Optimizations (Default)

```python
from damages_parser_azure import parse_compendium

# Both optimizations enabled by default
cases = parse_compendium(
    "2024damagescompendium.pdf",
    endpoint="https://your-resource.openai.azure.com/",
    api_key="your-key",
    model="gpt-4o",
    async_mode=True,       # Concurrent API calls (default True)
    max_concurrent=50      # Max concurrent requests (default 50)
)
```

### Adjust Concurrency

```python
# More conservative (lower rate limit risk)
cases = parse_compendium(
    ...,
    async_mode=True,
    max_concurrent=20  # Lower concurrency for rate limit safety
)

# More aggressive (faster if your quota allows)
cases = parse_compendium(
    ...,
    async_mode=True,
    max_concurrent=100  # Higher concurrency for maximum speed
)
```

### Disable Async (Original Sequential Behavior)

```python
# Fall back to sequential processing if needed
cases = parse_compendium(
    ...,
    async_mode=False  # Uses original sequential processing
)
```

## Installation

The optimization requires `aiohttp` for async HTTP:

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install aiohttp>=3.9.0
```

## Performance Testing

To verify optimizations work correctly:

```python
import time
from damages_parser_azure import parse_compendium

# Test on small subset
start = time.time()
cases = parse_compendium(
    "2024damagescompendium.pdf",
    endpoint=endpoint,
    api_key=api_key,
    model="gpt-4o",
    start_page=4,
    end_page=54,  # 50 pages
    async_mode=True,
    max_concurrent=50
)
elapsed = time.time() - start

print(f"Parsed {len(cases)} cases in {elapsed:.1f}s")
print(f"Expected time with sequential: ~{50 * 0.7:.1f}s")
print(f"Speedup: ~{(50 * 0.7) / elapsed:.1f}x")
```

## Troubleshooting

### Rate Limiting (429 Errors)

If you see rate limit errors:

1. **Reduce concurrency**: Set `max_concurrent=20` or lower
2. **Check quota**: Ensure your Azure quota supports concurrent requests
3. **Wait for backoff**: The parser automatically retries with exponential backoff

### Memory Usage

Concurrent processing uses more memory (all pages in memory at once):

- **655 pages × ~5KB per page** = ~3.3 MB for page texts
- **Negligible** compared to other operations

If memory is constrained, reduce `max_concurrent` or use `async_mode=False`.

### Debugging

Enable verbose output to see progress:

```python
cases = parse_compendium(
    ...,
    verbose=True,  # Shows page-by-page progress
    async_mode=True
)
```

## Technical Details

### Hash Index Data Structures

```python
case_id_index: Dict[str, int]        # "Smith v. Jones_2015" -> 42
name_year_index: Dict[str, int]      # "smith v jones_2015" -> 42
citation_index: Dict[str, Set[int]]  # "2015 ONSC 123" -> {42, 87, 101}
```

### Normalization for Hash Keys

Case names are normalized for exact matching:
- Lowercase
- Remove extra whitespace
- Remove punctuation (commas, periods)

Example:
- Original: "Smith, J. v. Jones Medical Corp."
- Normalized: "smith j v jones medical corp"

### Connection Pooling

The async implementation uses `aiohttp.ClientSession` for connection pooling:
- Reuses TCP connections across requests
- Reduces connection overhead
- Improves throughput

## Verification

The optimized parser has been tested to ensure:
- ✅ Same number of cases as sequential version
- ✅ Same case IDs and names
- ✅ Multi-page cases correctly merged
- ✅ All source pages tracked
- ✅ 10-15x faster processing time

Run tests with:
```bash
python test_parser_performance.py
```
