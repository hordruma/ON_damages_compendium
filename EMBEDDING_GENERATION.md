# Generating Injury-Focused Embeddings

## Overview

The injury-focused semantic search requires precomputed embeddings. These embeddings are generated from the injuries and sequelae fields only (not the full case text).

## Prerequisites

Install the required packages:

```bash
pip install sentence-transformers tqdm
```

**Note**: This installation may take 10-15 minutes due to large packages (~1.5GB for PyTorch and CUDA libraries).

## Generate Embeddings

Once the packages are installed, run:

```bash
python3 generate_embeddings.py
```

This will:
1. Load existing case data from `data/damages_with_embeddings.json`
2. Extract injuries/sequelae from each case's `extended_data.injuries`
3. Generate embeddings using the `all-MiniLM-L6-v2` model
4. Save three files:
   - `data/compendium_inj.json` (~10 MB) - Cases with search_text and embeddings
   - `data/embeddings_inj.npy` (~1 MB) - Embedding matrix for fast similarity search
   - `data/ids.json` (~10 KB) - Case IDs for mapping

## Expected Output

```
📂 Loading cases from data/damages_with_embeddings.json...
   Loaded 1,234 cases
🔄 Loading sentence-transformers model (all-MiniLM-L6-v2)...
   Model loaded successfully
🔄 Generating injury-focused embeddings...
Processing cases: 100%|████████████| 1234/1234 [00:15<00:00, 82.27it/s]

💾 Saving artifacts...

✅ Created 1,234 injury-focused embeddings

📁 Output files:
   - compendium_inj.json: 10.2 MB
   - embeddings_inj.npy: 0.9 MB
   - ids.json: 12.5 KB

✅ Done! The Streamlit app can now use these embeddings for search.
```

## Verification

After generation, verify the files exist:

```bash
ls -lh data/compendium_inj.json data/embeddings_inj.npy data/ids.json
```

## Integration with Streamlit

The Streamlit app (`streamlit_app.py`) loads these files automatically:

```python
# app/core/search.py
embeddings = np.load("data/embeddings_inj.npy")
with open("data/compendium_inj.json") as f:
    cases = json.load(f)
```

## Regenerating Embeddings

If you update the case data or want to regenerate embeddings:

1. Delete existing embeddings: `rm data/*_inj.*`
2. Run the script again: `python3 generate_embeddings.py`

## Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'sentence_transformers'`
- **Solution**: Run `pip install sentence-transformers tqdm`

**Issue**: Model download fails
- **Solution**: Ensure you have internet access. The model (~90MB) is downloaded on first use.

**Issue**: Out of memory
- **Solution**: The script uses CPU-only inference and should work with 2GB+ RAM. Close other applications if needed.
