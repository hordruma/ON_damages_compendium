# Gemini PDF Parser Integration

This document explains how to use the Google Gemini API to parse the Ontario Damages Compendium PDF and generate enhanced case data for the dashboard.

## Overview

The Gemini parser provides intelligent extraction of case data from the PDF, with several advantages over traditional table-based extraction:

### Features

- **Multi-Plaintiff Support**: Properly handles cases with multiple plaintiffs
- **Family Law Act Claims**: Extracts FLA claims and associates them with cases
- **Detailed Injury Information**: Captures specific injuries and their descriptions
- **Other Damages**: Tracks additional damage awards beyond non-pecuniary damages
- **Checkpoint/Resume**: Automatic checkpointing for long-running parses
- **Smart Deduplication**: Prevents duplicate cases across page boundaries
- **Automatic Embedding Generation**: Creates semantic embeddings for search

### Cost

Using Gemini 2.0 Flash (recommended):
- **Full PDF (655 pages)**: ~$0.20-$0.50
- **Processing time**: 30-60 minutes

## Quick Start

### 1. Get a Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key for use below

### 2. Run the Parsing Notebook

Open `02_gemini_parse_and_embed.ipynb` and follow the steps:

```python
# Set your API key
API_KEY = "your-gemini-api-key-here"

# Parse the PDF
from damages_parser_gemini import parse_compendium

cases = parse_compendium(
    "2024damagescompendium.pdf",
    api_key=API_KEY,
    output_json="damages_full.json"
)
```

### 3. Generate Dashboard Embeddings

```python
from gemini_data_transformer import add_embeddings_to_gemini_cases

# Convert and add embeddings
dashboard_cases = add_embeddings_to_gemini_cases(
    "damages_full.json",
    "data/damages_with_embeddings.json"
)
```

### 4. Launch Dashboard

```bash
streamlit run streamlit_app.py
```

The dashboard will automatically detect and use the Gemini-parsed data!

## Data Format

### Gemini Format (Raw)

```json
{
  "case_id": "Smith v. Jones_2020",
  "case_name": "Smith v. Jones",
  "plaintiff_name": "John Smith",
  "defendant_name": "ABC Corporation",
  "year": 2020,
  "category": "CERVICAL SPINE",
  "court": "Ontario Superior Court of Justice",
  "citations": ["2020 ONSC 12345"],
  "judges": ["Justice Brown"],
  "plaintiffs": [
    {
      "plaintiff_id": "P1",
      "sex": "M",
      "age": 45,
      "non_pecuniary_damages": 125000.0,
      "is_provisional": false,
      "injuries": [
        "C5-C6 disc herniation",
        "Chronic neck pain",
        "Radiculopathy"
      ],
      "other_damages": [
        {
          "type": "Loss of income",
          "amount": 250000.0,
          "description": "Past and future income loss"
        }
      ]
    }
  ],
  "family_law_act_claims": [
    {
      "description": "Spouse's claim",
      "amount": 50000.0
    }
  ],
  "comments": "Liability admitted"
}
```

### Dashboard Format (Converted)

The transformer converts Gemini format to dashboard format:

```json
{
  "region": "CERVICAL SPINE",
  "case_name": "Smith v. Jones",
  "year": 2020,
  "court": "Ontario Superior Court of Justice",
  "damages": 125000.0,
  "summary_text": "Smith v. Jones (2020). Category: CERVICAL SPINE. Plaintiff P1: M, age 45. Injuries: C5-C6 disc herniation, Chronic neck pain, Radiculopathy...",
  "embedding": [0.123, -0.456, ...],  // 384-dimensional vector
  "gemini_data": {
    // All original Gemini fields preserved here
    "case_id": "Smith v. Jones_2020",
    "plaintiff_id": "P1",
    "sex": "M",
    "age": 45,
    "injuries": ["C5-C6 disc herniation", ...],
    "family_law_act_claims": [...],
    ...
  }
}
```

## API Usage

### Parse Compendium

```python
from damages_parser_gemini import parse_compendium

# Full parse
cases = parse_compendium(
    pdf_path="2024damagescompendium.pdf",
    api_key="your-api-key",
    output_json="damages_full.json"
)

# Resume from interruption
cases = parse_compendium(
    pdf_path="2024damagescompendium.pdf",
    api_key="your-api-key",
    output_json="damages_full.json",
    resume=True  # <-- Resume from checkpoint
)
```

### Convert to Dashboard Format

```python
from gemini_data_transformer import convert_gemini_to_dashboard_format
from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# Convert
dashboard_cases = convert_gemini_to_dashboard_format(gemini_cases, model)
```

### Flatten for Analysis

```python
from damages_parser_gemini import flatten_cases_to_records
import pandas as pd

# Flatten to DataFrame (one row per plaintiff)
records = flatten_cases_to_records(gemini_cases)
df = pd.DataFrame(records)

# Now you can analyze with pandas
df.groupby('category')['non_pecuniary_damages'].agg(['count', 'mean', 'median'])
```

### Extract Statistics

```python
from gemini_data_transformer import extract_gemini_statistics

stats = extract_gemini_statistics(gemini_cases)

print(f"Total cases: {stats['total_cases']}")
print(f"Multi-plaintiff cases: {stats['multi_plaintiff_count']}")
print(f"FLA cases: {stats['family_law_act_count']}")
```

## Dashboard Features

When using Gemini-parsed data, the dashboard displays:

### Enhanced Case Information

- **Multi-Plaintiff Indicator**: Cases with multiple plaintiffs show `[P1]`, `[P2]`, etc.
- **Demographics**: Sex and age from Gemini data
- **Detailed Injuries**: Bullet list of specific injuries
- **Other Damages**: Additional damage awards (income loss, etc.)
- **Family Law Act Claims**: FLA claims and amounts
- **Citations**: Full case citations
- **Judges**: Presiding judges
- **Comments**: Additional case notes

### Example Display

```
Case 1 - Smith v. Jones [P1] | Region: CERVICAL SPINE | Match: 95.2%

Region: CERVICAL SPINE
Year: 2020
Court: Ontario Superior Court of Justice
Damages: $125,000

Case Summary:
Smith v. Jones (2020). Category: CERVICAL SPINE. Plaintiff P1: M, age 45...

─────────────────────────

Plaintiff: P1
Demographics: Sex: M, Age: 45

Injuries:
- C5-C6 disc herniation
- Chronic neck pain
- Radiculopathy

Other Damages:
- Loss of income: $250,000 (Past and future income loss)

Family Law Act Claims:
- Spouse's claim: $50,000

Citations: 2020 ONSC 12345
Judges: Justice Brown
```

## Advanced Usage

### Command Line Parsing

```bash
# Parse from command line
python damages_parser_gemini.py 2024damagescompendium.pdf YOUR_API_KEY damages_full.json

# Transform to dashboard format
python gemini_data_transformer.py damages_full.json data/damages_with_embeddings.json
```

### Custom Page Range

```python
from damages_parser_gemini import DamagesCompendiumParser

parser = DamagesCompendiumParser(api_key="your-key")

# Parse specific page range
cases = parser.parse_pdf(
    "2024damagescompendium.pdf",
    start_page=100,
    end_page=200
)
```

### Merge with Existing Data

```python
from gemini_data_transformer import merge_gemini_with_existing

# Merge new Gemini data with existing dashboard data
merged = merge_gemini_with_existing(
    gemini_json_path="damages_full.json",
    existing_json_path="data/damages_with_embeddings.json",
    output_path="data/damages_merged.json"
)
```

## Troubleshooting

### API Rate Limits

**Problem**: `429 Too Many Requests` error

**Solution**: The parser automatically retries with exponential backoff. If you hit quota limits:

1. Wait a few minutes
2. Run with `resume=True` to continue from checkpoint

### Incomplete Parsing

**Problem**: Parser stopped in the middle

**Solution**:
```python
# Check checkpoint
import json
with open("parsing_checkpoint.json") as f:
    checkpoint = json.load(f)
print(f"Last page: {checkpoint['last_page']}")

# Resume
cases = parse_compendium(..., resume=True)
```

### Missing Embeddings

**Problem**: Dashboard shows "No embedding" error

**Solution**: Re-run the embedding generation:
```python
from gemini_data_transformer import add_embeddings_to_gemini_cases

add_embeddings_to_gemini_cases(
    "damages_full.json",
    "data/damages_with_embeddings.json"
)
```

### Format Detection Issues

**Problem**: Dashboard doesn't recognize Gemini data

**Solution**: Check the format:
```python
from app.core.data_loader import detect_json_format

with open("damages_full.json") as f:
    data = json.load(f)

format_type = detect_json_format(data)
print(f"Format: {format_type}")  # Should be "gemini"
```

## File Reference

### Created Files

| File | Purpose |
|------|---------|
| `damages_parser_gemini.py` | Core parser using Gemini API |
| `gemini_data_transformer.py` | Data transformation utilities |
| `02_gemini_parse_and_embed.ipynb` | Interactive parsing notebook |
| `damages_full.json` | Raw Gemini output (created during parsing) |
| `parsing_checkpoint.json` | Checkpoint file (created during parsing) |
| `data/damages_with_embeddings.json` | Dashboard-ready format |

### Modified Files

| File | Changes |
|------|---------|
| `app/core/config.py` | Added Gemini configuration |
| `app/core/data_loader.py` | Added format auto-detection and conversion |
| `streamlit_app.py` | Added Gemini data display function |
| `requirements.txt` | Updated comments |

## Best Practices

1. **Use Checkpoints**: Always enable checkpointing for long parses
2. **Verify Output**: Spot-check a few cases manually
3. **Backup Original**: Keep the original `damages_with_embeddings.json` before replacing
4. **Monitor Costs**: Check API usage in Google Cloud Console
5. **Test Incrementally**: Parse a few pages first to validate

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the notebook examples in `02_gemini_parse_and_embed.ipynb`
- Examine the source code documentation in `damages_parser_gemini.py`

## Future Enhancements

Potential improvements:
- Batch processing for faster parsing
- Validation against known test cases
- Enhanced error recovery
- Incremental updates (parse only new cases)
- Multi-language support
