# PDF Parser Integration Guide

This document explains how to parse the Ontario Damages Compendium PDF using Azure OpenAI to generate enhanced case data for the dashboard.

## Overview

The Azure parser uses GPT-5 or GPT-4o to intelligently extract structured case data from the PDF, providing:

- **Multi-Plaintiff Support**: Properly handles cases with multiple plaintiffs
- **Family Law Act Claims**: Extracts FLA claims and amounts
- **Detailed Injury Information**: Captures specific injuries and descriptions
- **Other Damages**: Tracks additional damage awards
- **Checkpoint/Resume**: Automatic checkpointing for long-running parses
- **Smart Deduplication**: Prevents duplicate cases across page boundaries
- **Source Page Tracking**: Records which PDF page each case was found on

### Cost & Performance

- **Model**: GPT-5 or GPT-4o via Azure OpenAI
- **Cost**: $4-6 for full PDF (655 pages)
- **Speed**: 30-60 minutes
- **Quality**: Excellent

## Quick Start

### 1. Get Azure Credentials

1. Create an Azure OpenAI resource
2. Deploy GPT-5 or GPT-4o
3. Copy your endpoint and API key

### 2. Configure and Parse

**Using the Notebook** (recommended):

1. Open `02_azure_parse_and_embed.ipynb`
2. Update cell 4 with your credentials:
   ```python
   ENDPOINT = "https://your-resource.openai.azure.com/"
   API_KEY = "your-api-key"
   MODEL = "gpt-5-chat"  # or "gpt-4o"
   ```
3. Run the cells to parse

**Using Python**:

```python
from damages_parser_azure import parse_compendium

cases = parse_compendium(
    "2024damagescompendium.pdf",
    endpoint="https://your-resource.openai.azure.com/",
    api_key="your-api-key",
    model="gpt-5-chat"  # or "gpt-4o"
)
```

### 3. Generate Embeddings

```python
from data_transformer import add_embeddings_to_cases

add_embeddings_to_cases(
    "damages_full.json",
    "data/damages_with_embeddings.json"
)
```

### 4. Launch Dashboard

```bash
streamlit run streamlit_app.py
```

The dashboard will automatically detect and use the AI-parsed data!

## Detailed Usage

### Resume from Checkpoint

If parsing is interrupted:

```python
cases = parse_compendium(
    "2024damagescompendium.pdf",
    endpoint="...",
    api_key="...",
    model="gpt-5-chat",
    resume=True  # <-- Resume from checkpoint
)
```

### Parse Specific Pages

Useful for testing:

```python
cases = parse_compendium(
    "2024damagescompendium.pdf",
    endpoint="...",
    api_key="...",
    model="gpt-5-chat",
    start_page=100,
    end_page=200
)
```

### Command Line Usage

```bash
python damages_parser_azure.py \
  2024damagescompendium.pdf \
  "https://your-resource.openai.azure.com/" \
  "your-api-key" \
  "gpt-5-chat" \
  damages_full.json
```

## Data Format

The parser produces structured JSON:

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
  "source_page": 145,
  "plaintiffs": [
    {
      "plaintiff_id": "P1",
      "sex": "M",
      "age": 45,
      "non_pecuniary_damages": 125000.0,
      "is_provisional": false,
      "injuries": [
        "C5-C6 disc herniation",
        "Chronic neck pain"
      ],
      "other_damages": [
        {
          "type": "Loss of income",
          "amount": 250000.0,
          "description": "Past and future"
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

## Dashboard Integration

The dashboard automatically:
- Detects the AI-parsed format
- Converts to dashboard format with embeddings
- Displays enhanced case information
- Saves converted data for future use

Enhanced display includes:
- Multi-plaintiff indicators `[P1]`, `[P2]`
- Demographics (sex, age)
- Detailed injury lists
- Other damage awards
- FLA claims and amounts
- Full citations and judges
- Source page numbers

## Troubleshooting

### Azure Errors

**Problem**: `401 Unauthorized`
- **Solution**: Check your API key is correct

**Problem**: `404 Model not found`
- **Solution**: Verify deployment name matches your Azure deployment (gpt-5-chat or gpt-4o)

**Problem**: `429 Too Many Requests`
- **Solution**: The parser auto-retries. Use `resume=True` if needed

### General Issues

**Parsing Stopped Mid-Way**
```python
# Check checkpoint
with open("parsing_checkpoint.json") as f:
    checkpoint = json.load(f)
print(f"Last page: {checkpoint['last_page_processed']}")

# Resume
cases = parse_compendium(..., resume=True)
```

**Missing Embeddings**
```python
# Regenerate embeddings
from data_transformer import add_embeddings_to_cases

add_embeddings_to_cases(
    "damages_full.json",
    "data/damages_with_embeddings.json"
)
```

**Format Not Recognized**
```python
# Check format
from app.core.data_loader import detect_json_format

with open("damages_full.json") as f:
    data = json.load(f)

format_type = detect_json_format(data)
print(f"Format: {format_type}")  # Should be "ai_parsed"
```

## Best Practices

1. **Test First**: Parse a few pages (e.g., 1-10) to verify setup
2. **Monitor Progress**: Check checkpoint file periodically
3. **Use Resume**: Always use `resume=True` if restarting
4. **Backup Original**: Keep original data before replacing
5. **Verify Output**: Spot-check a few cases manually
6. **Track Costs**: Monitor API usage in Azure Portal

## File Reference

### Parser Files

| File | Purpose |
|------|---------|
| `damages_parser_azure.py` | Azure OpenAI parser |
| `data_transformer.py` | Data transformation utilities |
| `02_azure_parse_and_embed.ipynb` | Azure parsing notebook |

### Generated Files

| File | Purpose |
|------|---------|
| `damages_full.json` | Raw parsed output |
| `parsing_checkpoint.json` | Checkpoint state |
| `data/damages_with_embeddings.json` | Dashboard-ready format |
| `damages_flattened.csv` | Flattened DataFrame export |

## Advanced Features

### Custom Prompts

The parser uses a customizable extraction prompt:

```python
from damages_parser_azure import DamagesCompendiumParser

parser = DamagesCompendiumParser(
    endpoint="...",
    api_key="...",
    model="gpt-5-chat"
)

# Modify prompt if needed
parser.EXTRACTION_PROMPT = """Your custom prompt here..."""

# Parse with custom prompt
cases = parser.parse_pdf("2024damagescompendium.pdf")
```

### Data Analysis

Flatten and analyze with pandas:

```python
import pandas as pd
from data_transformer import extract_statistics

# Get statistics
stats = extract_statistics(cases)
print(f"Multi-plaintiff cases: {stats['multi_plaintiff_count']}")

# Create DataFrame
def flatten_cases(cases):
    rows = []
    for case in cases:
        for p in case.get('plaintiffs', []):
            rows.append({
                'case_name': case.get('case_name'),
                'year': case.get('year'),
                'category': case.get('category'),
                'plaintiff_id': p.get('plaintiff_id'),
                'sex': p.get('sex'),
                'age': p.get('age'),
                'non_pecuniary_damages': p.get('non_pecuniary_damages'),
            })
    return pd.DataFrame(rows)

df = flatten_cases(cases)
df.groupby('category')['non_pecuniary_damages'].agg(['count', 'mean', 'median'])
```

## Support

For issues:
1. Check this documentation
2. Review the notebook for examples
3. Examine parser source code documentation
4. Check the troubleshooting section above

## Cost Details

Using Azure OpenAI GPT-5 or GPT-4o:
- Input: ~$2.50 per 1M tokens
- Output: ~$10 per 1M tokens

For the full 655-page PDF:
- ~500 tokens input per page
- ~1000 tokens output per page
- Total: ~325K input + ~650K output tokens
- **Total cost: ~$4-6**

This is cost-effective for the value provided: accurate multi-plaintiff support, FLA claims extraction, and detailed injury information that would be difficult to extract with traditional table-based methods.
