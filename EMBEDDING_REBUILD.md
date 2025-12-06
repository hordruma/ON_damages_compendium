# Rebuilding Embeddings - Quick Guide

## One-Step Process

Run this single script to rebuild all embeddings:

```bash
python3 build_embeddings.py
```

This script:
1. ✅ Loads `damages_table_based.json` (authoritative source)
2. ✅ Converts to dashboard format with full case embeddings
3. ✅ Saves to `data/damages_with_embeddings.json`
4. ✅ Generates injury-focused embeddings for search
5. ✅ Saves to `data/compendium_inj.json`, `embeddings_inj.npy`, `ids.json`

## Requirements

```bash
pip install sentence-transformers numpy tqdm
```

## First Run

The first time you run it, it will download a ~400MB model file (`all-mpnet-base-v2`). This is cached for future runs.

## Expected Runtime

- First run: ~5-10 minutes (model download + processing)
- Subsequent runs: ~2-3 minutes (processing only)

## Output Files

| File | Purpose | Size |
|------|---------|------|
| `data/damages_with_embeddings.json` | Dashboard format with full case embeddings | ~1.7 MB |
| `data/compendium_inj.json` | Cases with injury search text | ~30 MB |
| `data/embeddings_inj.npy` | Embedding matrix for fast search | ~4 MB |
| `data/ids.json` | Case ID mapping | ~18 KB |

## After Rebuilding

Restart the Streamlit app to load fresh data:

```bash
streamlit run streamlit_app.py
```

The app will automatically detect and use the new embeddings.

## What Gets Preserved

The rebuild ensures all data is preserved:
- ✅ Injuries (from parser)
- ✅ FLA claims (Family Law Act relationships)
- ✅ Comments (case details)
- ✅ Demographics (age, sex)
- ✅ Judges, citations, court info
- ✅ Other damages (pecuniary, future loss, etc.)

## Troubleshooting

**"ModuleNotFoundError: No module named 'sentence_transformers'"**
```bash
pip install sentence-transformers
```

**"FileNotFoundError: damages_table_based.json"**

Make sure you're running from the project root directory where `damages_table_based.json` exists.

**Script runs but FLA count mismatch warning**

Check that `data_transformer.py` includes FLA claims in `extended_data`. The script will show:
```
⚠️  WARNING: FLA count mismatch! Source: 1000, Dashboard: 950
```

This means some FLA claims were lost during transformation.
