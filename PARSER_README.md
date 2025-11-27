# PDF Parser Integration Guide

This document explains how to parse the Ontario Damages Compendium PDF using AI models to generate enhanced case data for the dashboard.

## Supported Parsers

### 1. Azure AI Foundry (Recommended)
- **Models**: Azure OpenAI (GPT-4o, GPT-4) or Claude via Azure
- **Cost**: $4-20 for full PDF (655 pages)
- **Speed**: 30-60 minutes
- **File**: `damages_parser_azure.py`
- **Notebook**: `02_azure_parse_and_embed.ipynb`

### 2. Google Gemini
- **Models**: Gemini 2.0 Flash
- **Cost**: $0.20-$0.50 for full PDF
- **Speed**: 30-60 minutes
- **File**: `damages_parser_gemini.py`
- **Notebook**: `02_gemini_parse_and_embed.ipynb`

## Features

All parsers provide:

- **Multi-Plaintiff Support**: Properly handles cases with multiple plaintiffs
- **Family Law Act Claims**: Extracts FLA claims and amounts
- **Detailed Injury Information**: Captures specific injuries and descriptions
- **Other Damages**: Tracks additional damage awards
- **Checkpoint/Resume**: Automatic checkpointing for long-running parses
- **Smart Deduplication**: Prevents duplicate cases across page boundaries
- **Source Page Tracking**: Records which PDF page each case was found on
- **Automatic Embedding Generation**: Creates semantic embeddings for search

## Quick Start

### Option A: Azure AI Foundry (Recommended)

1. **Get Azure Credentials**
   - Create an Azure OpenAI resource
   - Deploy a model (GPT-4o recommended)
   - Copy your endpoint and API key

2. **Configure and Run**
   ```python
   from damages_parser_azure import parse_compendium

   cases = parse_compendium(
       "2024damagescompendium.pdf",
       endpoint="https://your-resource.openai.azure.com/",
       api_key="your-api-key",
       model="gpt-4o"  # Your deployment name
   )
   ```

3. **Generate Embeddings**
   ```python
   from gemini_data_transformer import add_embeddings_to_gemini_cases

   add_embeddings_to_gemini_cases(
       "damages_full.json",
       "data/damages_with_embeddings.json"
   )
   ```

4. **Launch Dashboard**
   ```bash
   streamlit run streamlit_app.py
   ```

### Option B: Google Gemini

1. **Get Gemini API Key**
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key

2. **Parse PDF**
   ```python
   from damages_parser_gemini import parse_compendium

   cases = parse_compendium(
       "2024damagescompendium.pdf",
       api_key="your-gemini-api-key",
       output_json="damages_full.json"
   )
   ```

3. **Generate Embeddings** (same as Azure)

4. **Launch Dashboard** (same as Azure)

## Detailed Usage

### Resume from Checkpoint

Both parsers support resuming:

```python
# Azure
cases = parse_compendium(
    "2024damagescompendium.pdf",
    endpoint="...",
    api_key="...",
    model="gpt-4o",
    resume=True  # <-- Resume from checkpoint
)

# Gemini
cases = parse_compendium(
    "2024damagescompendium.pdf",
    api_key="...",
    resume=True
)
```

### Parse Specific Pages

```python
# Parse pages 100-200
cases = parse_compendium(
    "2024damagescompendium.pdf",
    endpoint="...",
    api_key="...",
    model="gpt-4o",
    start_page=100,
    end_page=200
)
```

### Command Line Usage

```bash
# Azure
python damages_parser_azure.py \
  2024damagescompendium.pdf \
  "https://your-resource.openai.azure.com/" \
  "your-api-key" \
  "gpt-4o" \
  damages_full.json

# Gemini
python damages_parser_gemini.py \
  2024damagescompendium.pdf \
  "your-gemini-api-key" \
  damages_full.json
```

## Data Format

Both parsers produce the same JSON format:

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
- Detects the parsed format
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

## Cost Comparison

| Parser | Model | Input Cost | Output Cost | Total (655 pages) |
|--------|-------|------------|-------------|-------------------|
| Azure | GPT-4o | $2.50/1M | $10/1M | **$4-6** |
| Azure | GPT-4 Turbo | $10/1M | $30/1M | $15-20 |
| Gemini | 2.0 Flash | $0.075/1M | $0.30/1M | **$0.20-0.50** |

**Recommendation**:
- For best quality: Azure GPT-4o
- For lowest cost: Google Gemini 2.0 Flash
- Both produce excellent results

## Troubleshooting

### Azure Errors

**Problem**: `401 Unauthorized`
- **Solution**: Check your API key is correct

**Problem**: `404 Model not found`
- **Solution**: Verify deployment name matches your Azure deployment

**Problem**: `429 Too Many Requests`
- **Solution**: The parser auto-retries. Use `resume=True` if needed

### Gemini Errors

**Problem**: `403 Forbidden`
- **Solution**: Check API key is valid and enabled

**Problem**: `429 Quota exceeded`
- **Solution**: Wait and resume with `resume=True`

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
from gemini_data_transformer import add_embeddings_to_gemini_cases

add_embeddings_to_gemini_cases(
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
print(f"Format: {format_type}")
```

## Best Practices

1. **Test First**: Parse a few pages (e.g., 1-10) to verify setup
2. **Monitor Progress**: Check checkpoint file periodically
3. **Use Resume**: Always use `resume=True` if restarting
4. **Backup Original**: Keep original data before replacing
5. **Verify Output**: Spot-check a few cases manually
6. **Track Costs**: Monitor API usage in respective consoles

## File Reference

### Parser Files

| File | Purpose |
|------|---------|
| `damages_parser_azure.py` | Azure OpenAI/Claude parser |
| `damages_parser_gemini.py` | Google Gemini parser |
| `gemini_data_transformer.py` | Data transformation utilities (works with both) |
| `02_azure_parse_and_embed.ipynb` | Azure parsing notebook |
| `02_gemini_parse_and_embed.ipynb` | Gemini parsing notebook |

### Generated Files

| File | Purpose |
|------|---------|
| `damages_full.json` | Raw parsed output |
| `parsing_checkpoint.json` | Checkpoint state |
| `data/damages_with_embeddings.json` | Dashboard-ready format |
| `damages_flattened.csv` | Flattened DataFrame export |

## Advanced Features

### Custom Prompts

Both parsers use customizable extraction prompts:

```python
from damages_parser_azure import DamagesCompendiumParser

parser = DamagesCompendiumParser(
    endpoint="...",
    api_key="...",
    model="gpt-4o"
)

# Modify prompt if needed
parser.EXTRACTION_PROMPT = """Your custom prompt here..."""

# Parse with custom prompt
cases = parser.parse_pdf("2024damagescompendium.pdf")
```

### Batch Processing

Parse multiple PDFs:

```python
pdfs = [
    "2024damagescompendium.pdf",
    "2023damagescompendium.pdf",
    "2022damagescompendium.pdf"
]

all_cases = []
for pdf in pdfs:
    cases = parse_compendium(
        pdf,
        endpoint="...",
        api_key="...",
        model="gpt-4o",
        output_json=f"{pdf}.json"
    )
    all_cases.extend(cases)
```

### Data Analysis

Flatten and analyze with pandas:

```python
from damages_parser_gemini import flatten_cases_to_records
import pandas as pd

records = flatten_cases_to_records(cases)
df = pd.DataFrame(records)

# Analysis
df.groupby('category')['non_pecuniary_damages'].agg(['count', 'mean', 'median'])
df[df['has_fla_claims']].describe()
df.groupby('year')['non_pecuniary_damages'].mean().plot()
```

## Support

For issues:
1. Check this documentation
2. Review the notebooks for examples
3. Examine parser source code documentation
4. Check the troubleshooting section above

## Migration Notes

### From Legacy Extraction

If you have existing data from the Camelot-based extraction (`01_extract_and_embed.ipynb`):

1. **Keep Original**: Backup `data/damages_with_embeddings.json`
2. **Parse with AI**: Use Azure or Gemini parser
3. **Generate Embeddings**: Run transformation
4. **Test Dashboard**: Verify everything works
5. **Compare**: Spot-check cases between old and new

The AI parsers typically provide:
- More accurate plaintiff data
- Better injury descriptions
- Additional damage categories
- Multi-plaintiff support
- FLA claims extraction

### Merge Strategies

```python
from gemini_data_transformer import merge_gemini_with_existing

# Merge new AI-parsed data with existing
merged = merge_gemini_with_existing(
    gemini_json_path="damages_full.json",
    existing_json_path="data/damages_with_embeddings.json",
    output_path="data/damages_merged.json"
)
```

## Future Enhancements

Planned improvements:
- Parallel processing for faster parsing
- Validation against test cases
- Incremental updates (parse only new cases)
- Multi-language support
- Enhanced error recovery
- Quality scoring per case
