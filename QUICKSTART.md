# Quick Start Guide

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- 2024 Damages Compendium PDF file

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/hordruma/ON_damages_compendium.git
cd ON_damages_compendium
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

## Data Extraction

### 1. Place the PDF

Put your `2024damagescompendium.pdf` file in the project root directory.

### 2. Run the extraction notebook

```bash
jupyter notebook 01_extract_and_embed.ipynb
```

Execute all cells in order. This will:
- Extract tables from the PDF
- Clean and normalize the data
- Generate embeddings for each case
- Save to `data/damages_with_embeddings.json`

**Expected time:** 2-5 minutes depending on PDF size and your hardware.

## Running the App

### Local Development

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

### Deploy to Streamlit Cloud (Free)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Select `streamlit_app.py` as the main file
5. Click Deploy

**Note:** You'll need to upload the generated `data/damages_with_embeddings.json` file to your repository (or use Git LFS for large files).

## Using the Tool

1. **Select Demographics**: Choose gender and age in the sidebar
2. **Select Regions**: Expand region groups and check injured body areas
3. **Describe Injury**: Enter detailed clinical description of the injury
4. **Search**: Click "Find Comparable Cases"
5. **Review Results**: Examine matched cases and damage ranges

## Customization

### Update Body Diagrams

Replace the SVG files in `assets/` with your own:
- `body_front.svg` - Front view
- `body_back.svg` - Back view

Make sure region IDs match those in `region_map.json`.

### Adjust Region Mappings

Edit `region_map.json` to:
- Add new regions
- Modify clinical labels
- Update compendium term mappings

### Tune Search Algorithm

In `streamlit_app.py`, adjust the scoring weights:

```python
# Line ~165
combined_scores = 0.7 * embedding_sims + 0.3 * region_scores
#                 ^^^                      ^^^
#                 embedding weight         region weight
```

## Troubleshooting

### "Data file not found" error

Run the extraction notebook first to generate `data/damages_with_embeddings.json`.

### PDF extraction issues

- Ensure you're using the correct PDF (2024 Damages Compendium)
- Try different Camelot flavors: `flavor="stream"` instead of `"lattice"`
- Check PDF isn't password protected or corrupted

### Slow embedding generation

- Normal for large datasets (1000+ cases)
- Consider using a GPU-enabled machine
- Or use a smaller embedding model (though less accurate)

### No search results

- Check that regions are correctly mapped
- Try broader search terms
- Verify embeddings were generated successfully

## Support

For issues, visit: https://github.com/hordruma/ON_damages_compendium/issues
