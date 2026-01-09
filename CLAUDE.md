# CLAUDE.md - AI Assistant Guide for Ontario Damages Compendium

## Project Overview

This is a specialized legal technology application for searching comparable personal injury damages awards in Ontario. It combines AI-powered semantic search with domain-specific legal and medical knowledge to help lawyers find relevant case precedents.

**Key Technologies:**
- Python 3 with Streamlit for the web UI
- Sentence-Transformers (all-mpnet-base-v2) for semantic embeddings
- Optional LLM integration (OpenAI GPT-4o, Anthropic Claude) for expert report analysis
- NumPy/Pandas for data processing
- ReportLab for PDF generation
- Plotly for visualizations

**Purpose:** Enable lawyers to search ~1000+ Ontario personal injury cases using natural language queries, anatomical filters, and demographic criteria to find comparable damages awards.

---

## Repository Structure

### Core Application Files

```
streamlit_app.py (1254 lines)
├── Main Streamlit application entry point
├── Contains 4 main tabs: Search, Judge Analytics, Category Analytics, FLA Analytics
├── Expert report upload and PDF report generation features
└── Uses @st.cache_resource and @st.cache_data for performance

app/
├── core/
│   ├── search.py (961 lines)          # Hybrid semantic search engine
│   ├── data_loader.py (251 lines)     # Data loading with format detection
│   ├── config.py (102 lines)          # Centralized configuration constants
│   └── medical_terms.py (320 lines)   # Medical synonym expansion dictionary
└── ui/
    ├── visualizations.py (266 lines)      # Chart generation utilities
    ├── judge_analytics.py (653 lines)     # Judge-specific award analytics
    ├── category_analytics.py (714 lines)  # Anatomical category analytics
    └── fla_analytics.py (380 lines)       # Family Law Act claims analytics
```

### Data Processing Files

```
build_embeddings.py
├── GPU-accelerated embedding generation
├── Converts AI-parsed format to dashboard format
└── Creates injury-focused search indices

damages_parser_table.py (1375 lines)
├── Hybrid PDF table extraction (Camelot stream + lattice modes)
├── LLM-based row parsing with Azure OpenAI
└── Outputs damages_table_based.json

data_transformer.py
├── Converts between AI-parsed and dashboard formats
└── Handles plaintiff consolidation and data normalization
```

### Utility Files

```
expert_report_analyzer.py       # PDF report analysis with LLM or regex fallback
pdf_report_generator.py         # Professional PDF report generation
inflation_adjuster.py           # CPI-based inflation adjustment (BOC data)
anatomical_mappings.py          # Comprehensive anatomical structure mappings
region_map.json                 # Clinical anatomy region definitions (~30 regions)
```

### Data Files (Generated)

```
data/
├── damages_with_embeddings.json    # Main searchable dataset (~49MB)
├── compendium_inj.json             # Injury-focused case data
├── embeddings_inj.npy              # Pre-computed embedding matrix
├── ids.json                        # Case ID to embedding index mapping
├── boc_cpi.csv                     # Bank of Canada CPI data (1914-2025)
└── damages_raw.csv                 # Raw damages data
```

---

## Key Architecture Patterns

### 1. Hybrid Search System

The search engine uses a 4-component weighted scoring system:

```python
# Weight configuration (app/core/config.py)
SEMANTIC_WEIGHT = 0.15           # Full-text semantic similarity
INJURY_EMBEDDING_WEIGHT = 0.40   # Injury-specific embeddings
KEYWORD_WEIGHT = 0.35            # BM25 keyword matching
META_WEIGHT = 0.10               # Metadata (age, gender, severity)
```

**Search Pipeline:**
1. Medical term expansion (e.g., "TBI" → "traumatic brain injury", "brain damage")
2. Injury extraction from comma-separated input
3. Category filtering (exclusive anatomical region filter)
4. Cosine similarity against case embeddings
5. BM25 keyword scoring with medical synonyms
6. Metadata scoring (severity proximity, gender match, age proximity)
7. Outlier filtering (IQR method)
8. Case deduplication by name
9. Top-N results ranked by combined score

### 2. Dual Embedding System

**Why Two Embeddings?**
- Full-text embeddings: Encode entire case description (injuries + context)
- Injury-specific embeddings: Encode only the injury list for focused matching
- Injury embeddings are weighted heavily (0.40) for relevant results

**Implementation:**
- `damages_with_embeddings.json` contains full-text embeddings
- `embeddings_inj.npy` is a NumPy matrix for fast injury-focused search
- `ids.json` maps case IDs to embedding matrix row indices

### 3. Medical Term Expansion

Located in `app/core/medical_terms.py` with 240+ term mappings:

```python
MEDICAL_TERM_EXPANSIONS = {
    "tbi": ["traumatic brain injury", "brain damage", "head trauma"],
    "whiplash": ["cervical strain", "neck injury", "cervical sprain"],
    # ... 240+ more mappings
}
```

Used in both semantic search and keyword matching to improve medical terminology recall.

### 4. Anatomical Region Mapping

30+ anatomical regions defined in `region_map.json`:

```json
{
  "cervical_spine": {
    "label": "Cervical Spine (Neck)",
    "compendium_terms": ["cervical", "neck", "C1", "C2", ...]
  },
  "shoulder_left": {
    "label": "Left Shoulder",
    "compendium_terms": ["left shoulder", "L shoulder", ...]
  }
}
```

Used for exclusive filtering in search (only return cases matching selected regions).

### 5. Data Format Evolution

**Two formats exist:**

1. **AI-Parsed Format** (output from damages_parser_table.py):
   - Contains `plaintiffs[]` array with per-plaintiff data
   - Raw LLM extraction format

2. **Dashboard Format** (used by streamlit_app.py):
   - Consolidated `extended_data` object
   - Pre-computed embeddings
   - Normalized judges, injuries, FLA claims

**Auto-Detection:**
`app/core/data_loader.py` automatically detects format and converts as needed.

---

## Configuration Management

### Centralized Config

All configuration is in `app/core/config.py`:

```python
# Search weights
EMBEDDING_WEIGHT = 0.7
REGION_WEIGHT = 0.3
SEMANTIC_WEIGHT = 0.15
INJURY_EMBEDDING_WEIGHT = 0.40
KEYWORD_WEIGHT = 0.35
META_WEIGHT = 0.10

# Model
EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"

# Results display
DEFAULT_TOP_N_RESULTS = 15
MIN_RESULTS = 5
MAX_RESULTS = 50
CHART_MAX_CASES = 15

# Damage filtering
MIN_DAMAGE_VALUE = 1000
MAX_DAMAGE_VALUE = 10_000_000

# Data paths
DATA_FILE_PATH = "data/damages_with_embeddings.json"
REGION_MAP_PATH = "region_map.json"
```

**IMPORTANT:** When changing search behavior, modify weights in config.py, not hardcoded values.

### Environment Variables

Optional API keys for expert report analysis:

```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Use `.env` file for development (never commit to git).

---

## Code Conventions

### Naming Conventions

- **Python functions/variables:** snake_case
- **Classes:** PascalCase (e.g., `ExpertReportAnalyzer`, `DamagesReportGenerator`)
- **Region IDs:** lowercase_with_underscores (e.g., `cervical_spine`, `shoulder_left`)
- **Judge names:** Title case, hyphenated surnames preserved (e.g., "Smith", "Jones-Brown")
- **Medical terms:** Lowercase in expansion dictionary

### File Organization

- **Business logic:** `app/core/`
- **UI components:** `app/ui/`
- **Utilities:** Root directory (inflation_adjuster.py, expert_report_analyzer.py, etc.)
- **Tests:** `tests/` directory

### Documentation Style

- **Docstrings:** Google-style with Args/Returns/Raises sections
- **Module docstrings:** Describe purpose and key features
- **Inline comments:** For complex algorithms (e.g., BM25, severity scoring)
- **Type hints:** Encouraged but not required

### Error Handling

- **Graceful fallbacks:** Regex extraction if LLM unavailable, hardcoded CPI if CSV missing
- **User feedback:** Streamlit error/warning/info messages for all failure cases
- **Retry logic:** Rate limiting and exponential backoff in PDF parser
- **Validation:** Input validation for damage ranges, year ranges, age ranges

---

## Development Workflows

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/hordruma/ON_damages_compendium.git
cd ON_damages_compendium

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate embeddings (GPU recommended, 10-20 min)
python build_embeddings.py

# 4. Run app
streamlit run streamlit_app.py
```

### Common Development Tasks

#### 1. Adding a New Search Filter

**Example: Adding a "Court Level" filter**

1. Add configuration to `app/core/config.py`:
   ```python
   COURT_LEVELS = ["Superior Court", "Court of Appeal", "Divisional Court"]
   ```

2. Update search function in `app/core/search.py`:
   ```python
   def search_cases(..., court_level=None):
       # Add court_level to metadata scoring
       if court_level and case.get('court') == court_level:
           meta_score += 0.1
   ```

3. Add UI control in `streamlit_app.py`:
   ```python
   court_level = st.selectbox("Court Level", ["All"] + COURT_LEVELS)
   ```

4. Update tests in `tests/test_search.py`

#### 2. Adding a New Anatomical Region

1. Edit `region_map.json`:
   ```json
   {
     "new_region_id": {
       "label": "Display Name",
       "compendium_terms": ["term1", "term2", "synonym1"]
     }
   }
   ```

2. Update `anatomical_mappings.py` with clinical structures:
   ```python
   ANATOMICAL_MAPPINGS = {
       "specific structure": "new_region_id",
       # ... existing mappings
   }
   ```

3. Re-run `build_embeddings.py` to update indices

4. Update tests in `tests/test_anatomical_mappings.py`

#### 3. Modifying Search Weights

**IMPORTANT:** Search weights must sum to 1.0

1. Edit `app/core/config.py`:
   ```python
   SEMANTIC_WEIGHT = 0.20           # Increased from 0.15
   INJURY_EMBEDDING_WEIGHT = 0.35   # Decreased from 0.40
   KEYWORD_WEIGHT = 0.35            # No change
   META_WEIGHT = 0.10               # No change
   ```

2. Test with various queries to verify improvement

3. Document reasoning in commit message

#### 4. Adding Medical Term Synonyms

1. Edit `app/core/medical_terms.py`:
   ```python
   MEDICAL_TERM_EXPANSIONS = {
       # ... existing terms
       "new_abbreviation": ["full term", "synonym1", "synonym2"],
   }
   ```

2. No need to re-generate embeddings (used at query time)

3. Test with search queries using the new term

#### 5. Updating LLM Prompts

For expert report analysis, edit `expert_report_analyzer.py`:

```python
# Around line 85-90
prompt = f"""Analyze this medical/expert report and extract:

1. Injured body regions (e.g., head, neck, shoulders, back, legs)
2. Specific injuries and diagnoses
3. Functional limitations and restrictions
4. Chronicity (acute, chronic, permanent)
5. Severity (mild, moderate, severe)
6. Demographics (age, gender if mentioned)

[Your custom instructions here]

Report text:
{text}
"""
```

Test with sample reports before deploying.

### Data Pipeline Workflow

**When to regenerate embeddings:**

1. After modifying case data in `damages_with_embeddings.json`
2. After updating `region_map.json` (if regions changed)
3. After changing embedding model
4. After parsing a new version of the compendium PDF

**Steps:**

```bash
# Full pipeline from PDF
jupyter notebook parse_and_embed.ipynb

# Or if you have damages_table_based.json:
python build_embeddings.py

# Verify output
ls -lh data/
# Should see: damages_with_embeddings.json, compendium_inj.json, embeddings_inj.npy, ids.json
```

### Testing Workflow

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_expert_report_analyzer.py

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run with verbose output
pytest tests/ -v
```

**Test files:**
- `test_expert_report_analyzer.py` - LLM and regex extraction
- `test_pdf_report_generator.py` - PDF generation
- `test_inflation_adjuster.py` - CPI calculations
- `test_anatomical_mappings.py` - Region mapping validation

### Deployment Workflow

**Local Development:**

```bash
streamlit run streamlit_app.py
```

**Streamlit Cloud Deployment:**

1. Generate embeddings locally (GPU recommended)
2. Commit `data/` directory to repository
3. Push to GitHub
4. Deploy from Streamlit Cloud dashboard
5. Add API keys to Streamlit secrets (if using expert report features)

**Important:** `app/core/data_loader.py` forces CPU mode for Streamlit Cloud compatibility.

---

## Key Files Deep Dive

### streamlit_app.py

**Purpose:** Main Streamlit application with 4 tabs and expert report features

**Key Sections:**
- Lines 1-50: Imports and version management
- Lines 51-150: Data loading and model initialization
- Lines 151-400: Main search tab
- Lines 401-600: Expert report upload section
- Lines 601-800: Results display and statistics
- Lines 801-900: PDF report generation
- Lines 901-1000: Judge analytics tab
- Lines 1001-1100: Category analytics tab
- Lines 1101-1254: FLA analytics tab

**Cache Management:**
```python
APP_VERSION = "2.1.0"  # Increment to force cache refresh

@st.cache_resource
def load_model():
    # Cached across all users
    pass

@st.cache_data
def load_cases():
    # Cached per user session
    pass
```

**IMPORTANT:** Increment `APP_VERSION` when deploying data format changes to invalidate caches.

### app/core/search.py

**Purpose:** Hybrid semantic search engine with 4-component scoring

**Key Functions:**

```python
def search_cases(
    query_text: str,
    selected_regions: List[str],
    cases: List[dict],
    region_map: dict,
    model,
    gender: str = None,
    age: int = None,
    top_n: int = 15,
    semantic_weight: float = 0.15,
    keyword_weight: float = 0.35,
    meta_weight: float = 0.10,
    injury_embedding_weight: float = 0.40
) -> List[Tuple[dict, float, float]]:
    """
    Main search function combining semantic, keyword, and metadata scoring.

    Returns: List of (case, embedding_similarity, combined_score) tuples
    """
```

**Search Algorithm:**
1. Expand query with medical synonyms (lines 50-100)
2. Filter cases by selected regions (lines 101-150)
3. Compute semantic similarity (lines 151-200)
4. Compute BM25 keyword score (lines 201-250)
5. Compute metadata score (lines 251-300)
6. Combine scores with weights (lines 301-350)
7. Sort and return top-N (lines 351-400)

**Severity Scoring:**
```python
def calculate_severity_score(injury: str) -> float:
    """
    0.0 = mild (bruise, strain, sprain)
    0.5 = moderate (fracture, tear, herniation)
    1.0 = catastrophic (amputation, paralysis, brain injury)
    """
```

**IMPORTANT:** Severity matching uses exponential decay penalty for mismatches.

### app/core/data_loader.py

**Purpose:** Data loading with format auto-detection and CPU-only mode

**Key Features:**
- Detects AI-parsed vs dashboard format
- Converts AI-parsed to dashboard format on the fly
- Forces CPU mode for Streamlit Cloud compatibility
- Handles missing files gracefully

**Format Detection:**
```python
def is_ai_parsed_format(data: dict) -> bool:
    """
    AI-parsed: Has 'plaintiffs' array
    Dashboard: Has 'extended_data' object with consolidated data
    """
    if isinstance(data, dict):
        return 'plaintiffs' in data
    return False
```

**IMPORTANT:** Never remove CPU-only forcing (`device='cpu'`) - breaks Streamlit Cloud deployment.

### app/core/medical_terms.py

**Purpose:** Domain-specific medical synonym expansion

**Structure:**
```python
MEDICAL_TERM_EXPANSIONS = {
    "abbreviation": ["full term", "synonym1", "synonym2"],
    "common term": ["medical term", "related term"],
}
```

**Usage:**
- Query expansion in search
- BM25 keyword matching
- Expert report analysis

**Best Practices:**
- Add synonyms in lowercase
- Include common abbreviations (TBI, ACL, MTBI, etc.)
- Include clinical and lay terminology
- Group related conditions

### damages_parser_table.py

**Purpose:** Hybrid PDF table extraction with LLM-based row parsing

**Architecture:**
1. Camelot extraction (stream + lattice modes)
2. Table structure detection
3. Row-by-row LLM parsing with Azure OpenAI
4. Checkpoint support for resumable parsing
5. Rate limiting and retry logic

**IMPORTANT:**
- Requires Azure OpenAI API key
- Temperature set to 0.1 for deterministic parsing
- Max retries: 3 per row
- Outputs to `damages_table_based.json` (AI-parsed format)

**Configuration:**
```python
AZURE_MODEL = "gpt-4o"
PARSER_TEMPERATURE = 0.1
PARSER_MAX_RETRIES = 3
```

### build_embeddings.py

**Purpose:** GPU-accelerated embedding generation

**Process:**
1. Load damages_table_based.json (AI-parsed format)
2. Convert to dashboard format
3. Generate full-text embeddings
4. Generate injury-specific embeddings
5. Create embedding matrix and ID mapping
6. Save to data/ directory

**GPU Usage:**
```python
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = SentenceTransformer(MODEL_NAME, device=device)
```

**Performance:**
- GPU: 10-20 minutes for ~1000 cases
- CPU: 1-2 hours for ~1000 cases

**Output Files:**
- `data/damages_with_embeddings.json` - Full dataset with embeddings
- `data/compendium_inj.json` - Injury-focused data
- `data/embeddings_inj.npy` - NumPy embedding matrix
- `data/ids.json` - Case ID mapping

### expert_report_analyzer.py

**Purpose:** Extract injuries from medical/expert reports

**Two Modes:**

1. **LLM-based (OpenAI or Anthropic):**
   - High accuracy
   - Understands medical context
   - Requires API key
   - ~$0.001-0.005 per report

2. **Regex-based (fallback):**
   - Pattern matching
   - No API key needed
   - Lower accuracy
   - Free

**LLM Prompt Structure:**
```python
prompt = f"""Analyze this medical/expert report and extract:

1. Injured body regions
2. Specific injuries and diagnoses
3. Functional limitations
4. Chronicity (acute, chronic, permanent)
5. Severity (mild, moderate, severe)
6. Demographics (age, gender)

Return as JSON.

Report text:
{text}
"""
```

**IMPORTANT:** Always validate LLM extraction - models can hallucinate.

### pdf_report_generator.py

**Purpose:** Generate professional PDF reports with ReportLab

**Report Structure:**
1. Title and metadata
2. Search parameters
3. Damage statistics (median, min, max)
4. Top N comparable cases
5. Legal disclaimer

**Styling:**
- Professional legal document formatting
- Blue headers
- Tables for case details
- Page numbers
- Legal disclaimer on last page

**Usage:**
```python
from pdf_report_generator import DamagesReportGenerator

generator = DamagesReportGenerator()
pdf_bytes = generator.generate_report(
    search_params=params,
    results=cases,
    statistics=stats,
    num_cases=10
)
```

### inflation_adjuster.py

**Purpose:** CPI-based inflation adjustment using Bank of Canada data

**Data Source:**
- Primary: `data/boc_cpi.csv` (1914-2025)
- Fallback: Hardcoded CPI values

**Usage:**
```python
from inflation_adjuster import InflationAdjuster

adjuster = InflationAdjuster()
adjusted = adjuster.adjust_to_year(
    amount=100000,
    from_year=2010,
    to_year=2024
)
```

**IMPORTANT:** All charts and comparisons use inflation-adjusted values by default.

---

## Common Pitfalls and How to Avoid Them

### 1. Breaking Streamlit Cloud Deployment

**Problem:** App works locally but fails on Streamlit Cloud

**Common Causes:**
- Hardcoded GPU usage
- Missing data files
- Large file sizes exceeding GitHub limits
- Incorrect file paths

**Solutions:**
- Always use `device='cpu'` in data_loader.py
- Commit `data/` directory or generate on first run
- Keep embedding files under 100MB (use Git LFS if needed)
- Use relative paths, not absolute paths

### 2. Cache Invalidation Issues

**Problem:** Changes not reflected in deployed app

**Solution:**
```python
# In streamlit_app.py
APP_VERSION = "2.1.0"  # Increment this

# Use in cache key
@st.cache_data
def load_cases():
    version = APP_VERSION  # Forces cache refresh
    # ... load data
```

### 3. Search Weight Misconfiguration

**Problem:** Search results don't make sense

**Common Causes:**
- Weights don't sum to 1.0
- One weight is too dominant
- Metadata weight too high

**Solutions:**
- Verify: `SEMANTIC_WEIGHT + INJURY_EMBEDDING_WEIGHT + KEYWORD_WEIGHT + META_WEIGHT = 1.0`
- Test with various queries
- Start with recommended weights and adjust incrementally

### 4. Medical Term Expansion Conflicts

**Problem:** Query expansion returns irrelevant results

**Common Causes:**
- Overly broad synonyms
- Duplicate expansions
- Case sensitivity issues

**Solutions:**
- Keep synonyms specific and clinically relevant
- Use lowercase consistently
- Test expansion with sample queries
- Review `medical_terms.py` for conflicts

### 5. Embedding Regeneration Mistakes

**Problem:** Embeddings out of sync with data

**Common Causes:**
- Modified JSON without regenerating embeddings
- Using wrong source file
- Incomplete embedding generation

**Solutions:**
- Always regenerate after JSON changes
- Use `build_embeddings.py` for production
- Verify all output files exist and have recent timestamps
- Check file sizes (embeddings should be ~49MB)

### 6. Data Format Confusion

**Problem:** App crashes with format-related errors

**Common Causes:**
- Mixing AI-parsed and dashboard formats
- Missing extended_data fields
- Incorrect data structure

**Solutions:**
- Use `data_loader.py` for auto-detection
- Don't manually edit JSON files
- Use `data_transformer.py` for conversions
- Validate JSON structure before deployment

### 7. LLM API Cost Overruns

**Problem:** Unexpected API costs

**Common Causes:**
- Processing large reports
- Using expensive models
- No rate limiting

**Solutions:**
- Truncate reports to first 4000 characters
- Use efficient models (GPT-4o-mini, Claude Haiku)
- Set API spending limits
- Implement caching for repeated analyses
- Offer regex fallback for cost-conscious users

### 8. PDF Parsing Failures

**Problem:** PDF extraction returns empty or incorrect data

**Common Causes:**
- Scanned PDFs without OCR
- Password-protected PDFs
- Complex table layouts
- Image-only PDFs

**Solutions:**
- Use text-based PDFs
- Apply OCR to scans before processing
- Remove password protection
- Use hybrid Camelot modes (stream + lattice)
- Implement fallback extraction strategies

---

## Testing Best Practices

### Unit Test Structure

```python
# tests/test_search.py
import pytest
from app.core.search import search_cases

def test_search_with_single_region():
    """Test search with one anatomical region selected"""
    # Arrange
    query = "cervical spine injury"
    regions = ["cervical_spine"]

    # Act
    results = search_cases(query, regions, cases, region_map, model)

    # Assert
    assert len(results) > 0
    assert all('cervical' in r[0]['injuries'] for r in results)

def test_search_weights_sum_to_one():
    """Verify search weights sum to 1.0"""
    from app.core.config import (
        SEMANTIC_WEIGHT, INJURY_EMBEDDING_WEIGHT,
        KEYWORD_WEIGHT, META_WEIGHT
    )

    total = SEMANTIC_WEIGHT + INJURY_EMBEDDING_WEIGHT + KEYWORD_WEIGHT + META_WEIGHT
    assert abs(total - 1.0) < 0.001, "Weights must sum to 1.0"
```

### Integration Test Examples

```python
# tests/test_integration.py
def test_end_to_end_search():
    """Test complete search workflow"""
    # Load data
    cases = load_cases()
    model = load_model()
    region_map = load_region_map()

    # Execute search
    results = search_cases(
        query_text="traumatic brain injury",
        selected_regions=["head"],
        cases=cases,
        region_map=region_map,
        model=model
    )

    # Verify results
    assert len(results) > 0
    assert all(r[2] > 0 for r in results)  # All scores positive
```

### Test Data Management

```python
# tests/fixtures/sample_cases.json
[
    {
        "id": "test-001",
        "case_name": "Test v. Defendant",
        "year": 2023,
        "non_pecuniary_damages": 100000,
        "extended_data": {
            "injuries": ["cervical strain", "whiplash"],
            "sex": "M",
            "age": 35,
            "regions": ["cervical_spine"]
        },
        "embedding": [0.1, 0.2, ...] # 384 dimensions
    }
]
```

**IMPORTANT:** Use small fixture files (5-10 cases) for fast test execution.

---

## AI Assistant Best Practices

### When Making Code Changes

1. **Read Before Editing:**
   - Always read the full file before making changes
   - Understand context and existing patterns
   - Check for dependencies on modified code

2. **Maintain Consistency:**
   - Follow existing naming conventions
   - Match code style and formatting
   - Use same design patterns as existing code

3. **Preserve Configuration:**
   - Don't hardcode values that belong in config.py
   - Don't modify CPU-only forcing in data_loader.py
   - Don't change search weights without user request

4. **Test Impact:**
   - Consider how changes affect search quality
   - Verify embedding compatibility
   - Check cache invalidation requirements

5. **Document Changes:**
   - Update docstrings for modified functions
   - Add comments for complex logic
   - Update CLAUDE.md if architecture changes

### When Adding Features

1. **Check Existing Functionality:**
   - Search for similar features first
   - Reuse existing utilities and helpers
   - Follow established patterns

2. **Consider Performance:**
   - Will this slow down search queries?
   - Does it require embedding regeneration?
   - Should it be cached?

3. **Plan Data Changes:**
   - Modify data format only if necessary
   - Update data_transformer.py for format changes
   - Document migration path

4. **Add Tests:**
   - Unit tests for new functions
   - Integration tests for features
   - Test with realistic data

### When Debugging Issues

1. **Reproduce First:**
   - Get exact steps to reproduce
   - Check if it's environment-specific
   - Verify with sample data

2. **Check Common Issues:**
   - Cache invalidation (increment APP_VERSION)
   - Data format mismatch (use data_loader.py)
   - Search weight configuration
   - GPU/CPU mode conflicts

3. **Isolate Root Cause:**
   - Test components individually
   - Check logs and error messages
   - Use print debugging sparingly (Streamlit shows output)

4. **Fix Systematically:**
   - Fix root cause, not symptoms
   - Verify fix doesn't break other features
   - Add test to prevent regression

### When Answering Questions

1. **Reference Specific Files:**
   - Cite exact file paths and line numbers
   - Quote relevant code sections
   - Link to related documentation

2. **Explain Context:**
   - Why does this code exist?
   - What problem does it solve?
   - What are the tradeoffs?

3. **Provide Examples:**
   - Show usage examples
   - Demonstrate with sample data
   - Include expected outputs

4. **Consider Skill Level:**
   - Adjust technical depth as needed
   - Explain domain concepts (legal, medical)
   - Link to external resources when helpful

---

## Git Workflow

### Branch Naming

```bash
# Feature branches
claude/add-new-filter-[SESSION_ID]
claude/fix-search-bug-[SESSION_ID]
claude/update-documentation-[SESSION_ID]

# IMPORTANT: Branch must start with 'claude/' and end with session ID
# Otherwise git push will fail with 403 error
```

### Commit Message Format

```bash
# Good commit messages
fix: Correct BM25 scoring in keyword search
feat: Add court level filter to search
docs: Update CLAUDE.md with deployment instructions
refactor: Extract embedding generation into separate module

# Bad commit messages
fix bug
update code
changes
```

**Format:** `type: Brief description`

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code restructuring
- `test:` Adding or updating tests
- `perf:` Performance improvement
- `style:` Formatting, no code change

### Push Workflow

```bash
# Always push with -u flag
git push -u origin claude/feature-name-[SESSION_ID]

# Retry on network errors (up to 4 times with exponential backoff)
# 2s, 4s, 8s, 16s delays
```

**IMPORTANT:** Only retry on network errors, not authentication errors.

### Pull Request Guidelines

1. **PR Title:** Clear, descriptive summary of changes
2. **PR Description:**
   - Summary of changes (2-3 bullet points)
   - Test plan (how to verify changes)
   - Any breaking changes
   - Related issues

3. **Before Submitting:**
   - Run tests: `pytest tests/`
   - Verify app starts: `streamlit run streamlit_app.py`
   - Check no hardcoded API keys or secrets
   - Update CLAUDE.md if needed

---

## Performance Optimization

### Search Query Performance

**Current Performance:**
- Model loading: 30-60s (first run, cached thereafter)
- Search query: ~100ms
- PDF report generation: ~2-5s

**Optimization Opportunities:**

1. **Embedding Precomputation:**
   - Already done - embeddings stored in files
   - Don't recompute at query time

2. **Caching:**
   - Use `@st.cache_resource` for models
   - Use `@st.cache_data` for case data
   - Cache query results if same query repeated

3. **Filtering:**
   - Apply region filter before computing similarities
   - Use NumPy boolean indexing for fast filtering
   - Filter by damage range before scoring

4. **Batching:**
   - Compute embeddings in batches during generation
   - Use NumPy vectorized operations
   - Avoid Python loops for similarity calculations

### Memory Management

**Current Usage:**
- Embedding model: ~420MB
- Case data: ~50MB
- Embedding matrix: ~49MB
- **Total:** ~520MB

**Optimization:**
- Force CPU mode on Streamlit Cloud (no GPU memory)
- Use float32 for embeddings (not float64)
- Load embeddings as memory-mapped NumPy arrays
- Clear unused variables in long-running operations

### Data File Sizes

**Current Sizes:**
- damages_with_embeddings.json: ~49MB
- embeddings_inj.npy: ~3MB
- compendium_inj.json: ~2MB

**If Exceeding GitHub Limits:**
1. Use Git LFS for large files
2. Compress embeddings (float16 instead of float32)
3. Generate embeddings on first deployment
4. Use external storage (S3, GCS)

---

## Security Considerations

### API Key Management

**NEVER:**
- Commit API keys to git
- Hardcode API keys in code
- Share .env files
- Log API keys

**ALWAYS:**
- Use environment variables
- Add .env to .gitignore
- Use Streamlit secrets for deployment
- Rotate keys periodically

### Data Privacy

**Expert Report Analysis:**
- Only first ~4000 characters sent to API
- No data retention by default (check API provider terms)
- Consider HIPAA/PIPEDA compliance if handling PHI
- Offer regex fallback for maximum privacy

**Case Law Data:**
- Public court records (no privacy issues)
- No personally identifiable information
- Safe to deploy publicly

### Input Validation

**Required for:**
- Damage range inputs (prevent injection)
- Year range inputs (prevent invalid dates)
- File uploads (check file type, size)
- Search queries (sanitize for display)

**Example:**
```python
def validate_damage_range(min_val, max_val):
    """Validate damage range inputs"""
    if not (0 <= min_val < max_val <= 10_000_000):
        raise ValueError("Invalid damage range")
    return min_val, max_val
```

---

## Troubleshooting Guide

### App Won't Start

**Symptoms:** Streamlit crashes on startup

**Checks:**
1. Are data files present in `data/` directory?
2. Is `region_map.json` in root directory?
3. Are all dependencies installed? `pip install -r requirements.txt`
4. Is Python version 3.8+?
5. Check error message in terminal

**Solutions:**
- Run `python build_embeddings.py` to generate data files
- Verify all required files exist
- Update dependencies: `pip install --upgrade -r requirements.txt`

### Search Returns No Results

**Symptoms:** All searches return 0 results

**Checks:**
1. Are regions selected? (If yes, only cases with those regions return)
2. Is damage range too restrictive?
3. Is year range too narrow?
4. Are embeddings loaded? Check terminal for errors

**Solutions:**
- Deselect all regions for broader search
- Expand damage range
- Check data file integrity: `python -c "import json; json.load(open('data/damages_with_embeddings.json'))"`

### Slow Search Performance

**Symptoms:** Queries take >5 seconds

**Checks:**
1. How many cases in dataset? (Should be ~1000)
2. Is model loaded? (First query always slower)
3. Is CPU pegged at 100%?
4. Are embeddings loaded as NumPy arrays?

**Solutions:**
- Wait for initial model load (30-60s)
- Verify NumPy embeddings being used: `os.path.exists('data/embeddings_inj.npy')`
- Check data_loader.py forces CPU mode
- Profile with `cProfile` if still slow

### Expert Report Analysis Fails

**Symptoms:** Error when analyzing PDF

**Checks:**
1. Is API key configured?
2. Is PDF text-based or image-only?
3. Is PDF password-protected?
4. Check error message details

**Solutions:**
- Verify API key: `echo $OPENAI_API_KEY`
- Test PDF text extraction: `pdfplumber` can extract text?
- Remove password protection
- Try regex fallback mode
- Check API provider status page

### Embedding Generation Fails

**Symptoms:** build_embeddings.py crashes

**Checks:**
1. Is source JSON file present?
2. Is format correct (AI-parsed or dashboard)?
3. Is GPU driver installed (if using GPU)?
4. Enough RAM? (Need ~2GB)
5. Enough disk space? (Need ~100MB)

**Solutions:**
- Verify source file: `ls -lh damages_table_based.json`
- Check JSON format with data_loader.py
- Force CPU mode if GPU issues: `device='cpu'`
- Close other applications to free RAM
- Clean up disk space

### Charts Not Displaying

**Symptoms:** Blank charts or errors

**Checks:**
1. Are there results to chart?
2. Is Plotly installed?
3. Browser console errors?
4. Streamlit version up to date?

**Solutions:**
- Verify results exist before charting
- Reinstall Plotly: `pip install --upgrade plotly`
- Try different browser
- Update Streamlit: `pip install --upgrade streamlit`

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing: `pytest tests/`
- [ ] App starts locally: `streamlit run streamlit_app.py`
- [ ] Sample searches work correctly
- [ ] No hardcoded API keys or secrets
- [ ] No debug print statements
- [ ] APP_VERSION incremented if data format changed
- [ ] requirements.txt up to date
- [ ] CLAUDE.md updated if architecture changed
- [ ] Git branch follows naming convention
- [ ] Commit messages are clear and descriptive

### Data Files

- [ ] data/damages_with_embeddings.json exists
- [ ] data/compendium_inj.json exists
- [ ] data/embeddings_inj.npy exists
- [ ] data/ids.json exists
- [ ] data/boc_cpi.csv exists (or fallback hardcoded CPI)
- [ ] region_map.json in root directory
- [ ] All files under GitHub size limits (100MB) or using Git LFS

### Configuration

- [ ] app/core/config.py has correct settings
- [ ] Search weights sum to 1.0
- [ ] CPU-only mode enabled in data_loader.py
- [ ] .env not committed to git
- [ ] .gitignore includes .env and __pycache__

### Streamlit Cloud

- [ ] Repository connected to Streamlit Cloud
- [ ] Secrets configured (if using expert reports)
  - [ ] OPENAI_API_KEY or ANTHROPIC_API_KEY
- [ ] Python version specified (3.8+)
- [ ] App URL tested and accessible

### Post-Deployment

- [ ] Test search functionality
- [ ] Test all 4 tabs
- [ ] Test expert report upload (if configured)
- [ ] Test PDF report generation
- [ ] Verify charts display correctly
- [ ] Check performance (queries <1s)
- [ ] Monitor error logs for issues

---

## Additional Resources

### External Documentation

- **Streamlit:** https://docs.streamlit.io/
- **Sentence-Transformers:** https://www.sbert.net/
- **ReportLab:** https://www.reportlab.com/docs/
- **Plotly:** https://plotly.com/python/
- **OpenAI API:** https://platform.openai.com/docs/
- **Anthropic API:** https://docs.anthropic.com/

### Project-Specific Guides

- **README.md** - Installation and basic usage
- **EXPERT_REPORT_GUIDE.md** - Expert report analysis feature
- **requirements.txt** - Complete dependency list
- **.env.example** - API key configuration template

### Code Examples

**Search Query:**
```python
from app.core.search import search_cases
from app.core.data_loader import load_model, load_cases

model = load_model()
cases = load_cases()
region_map = load_region_map()

results = search_cases(
    query_text="cervical spine whiplash injury",
    selected_regions=["cervical_spine"],
    cases=cases,
    region_map=region_map,
    model=model,
    gender="M",
    age=35,
    top_n=10
)

for case, sim, score in results:
    print(f"{case['case_name']}: {score:.3f}")
```

**Inflation Adjustment:**
```python
from inflation_adjuster import InflationAdjuster

adjuster = InflationAdjuster()
adjusted = adjuster.adjust_to_year(
    amount=75000,
    from_year=2015,
    to_year=2024
)
print(f"2015 $75,000 = 2024 ${adjusted:,.0f}")
```

**Expert Report Analysis:**
```python
from expert_report_analyzer import ExpertReportAnalyzer

analyzer = ExpertReportAnalyzer(
    provider="openai",  # or "anthropic"
    api_key=os.getenv("OPENAI_API_KEY")
)

results = analyzer.analyze_report("path/to/report.pdf")
print(f"Injuries: {results['injuries']}")
print(f"Regions: {results['regions']}")
```

---

## Version History

### Version 2.1.0 (Current)
- Added expert report analysis with LLM and regex fallback
- Added PDF report generation
- Improved search with 4-component hybrid scoring
- Added judge analytics, category analytics, FLA analytics
- Modular architecture with app/core and app/ui packages

### Version 2.0.0
- Dual embedding system (full-text + injury-specific)
- Medical term expansion dictionary
- Streamlit Cloud deployment support
- Inflation adjustment with BOC CPI data

### Version 1.0.0
- Initial release with basic semantic search
- Single embedding system
- Local deployment only

---

## Contact and Support

For issues, questions, or contributions:

1. **GitHub Issues:** https://github.com/hordruma/ON_damages_compendium/issues
2. **Pull Requests:** Follow PR guidelines in this document
3. **Documentation:** Check README.md, EXPERT_REPORT_GUIDE.md, and this file

---

## Summary for AI Assistants

**When working on this codebase:**

1. **Always read files before editing** - Understand existing patterns
2. **Use centralized configuration** - Don't hardcode values
3. **Preserve CPU-only mode** - Critical for Streamlit Cloud
4. **Increment APP_VERSION** - When changing data formats
5. **Test search quality** - After modifying weights or algorithms
6. **Follow naming conventions** - snake_case, PascalCase, lowercase regions
7. **Document changes** - Update docstrings and CLAUDE.md
8. **Consider performance** - Embedding regeneration is slow
9. **Validate LLM outputs** - Models can hallucinate
10. **Commit meaningful messages** - Use conventional commit format

**Key files to remember:**
- `app/core/config.py` - All configuration
- `app/core/search.py` - Search algorithm
- `streamlit_app.py` - Main application
- `build_embeddings.py` - Embedding generation
- `region_map.json` - Anatomical regions

**Common tasks:**
- Adding search filter: Edit search.py, config.py, streamlit_app.py
- Adding region: Edit region_map.json, anatomical_mappings.py, regenerate embeddings
- Modifying weights: Edit config.py, test thoroughly
- Adding medical terms: Edit medical_terms.py (no regeneration needed)
- Updating LLM prompts: Edit expert_report_analyzer.py

**Things to never do:**
- Remove CPU-only forcing in data_loader.py
- Commit API keys or .env files
- Change search weights without testing
- Modify embeddings manually
- Deploy without data files
- Skip tests before deployment

This is a sophisticated legal tech application that requires careful attention to search quality, performance, and deployment constraints. Always test changes thoroughly and consider the impact on end users (lawyers searching for case precedents).
