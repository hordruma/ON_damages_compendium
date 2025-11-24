# Ontario Damages Compendium - Visual Search Tool

A professional legal tool for searching comparable personal injury awards in Ontario using visual body mapping and AI-powered similarity search.

## Features

- **Visual Body Mapping**: Click on anatomical regions to select injury locations
- **Multi-Region Selection**: Support for cases with multiple injuries
- **Clinical Anatomy Labels**: Professional medical terminology for PI and insurance lawyers
- **AI-Powered Search**: Embedding-based similarity matching for finding comparable cases
- **Damage Award Analysis**: Automatic calculation of median, min, and max damage ranges
- **Gender & Age Filters**: Adjust search based on plaintiff demographics

## Installation

1. Clone the repository:
```bash
git clone https://github.com/hordruma/ON_damages_compendium.git
cd ON_damages_compendium
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Extract and process the compendium data:
```bash
jupyter notebook 01_extract_and_embed.ipynb
```

4. Run the Streamlit app:
```bash
streamlit run streamlit_app.py
```

## Project Structure

```
ON_damages_compendium/
├── 01_extract_and_embed.ipynb   # Data extraction and embedding generation
├── streamlit_app.py              # Main Streamlit application
├── region_map.json               # Clinical anatomy region mappings
├── assets/
│   ├── body_front.svg            # Front body diagram
│   └── body_back.svg             # Back body diagram
├── data/
│   └── damages_with_embeddings.json  # Processed case data (generated)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Usage

1. **Prepare Data**: Place `2024damagescompendium.pdf` in the project root
2. **Extract Cases**: Run the Jupyter notebook to generate embeddings
3. **Launch App**: Run the Streamlit application
4. **Search Cases**:
   - Select gender and age
   - Click body regions to highlight injuries
   - Describe the injury in detail
   - Click "Find Comparable Cases"
   - Review matched cases and damage ranges

## Technology Stack

- **PDF Extraction**: Camelot-py
- **Embeddings**: Sentence-Transformers (all-MiniLM-L6-v2)
- **UI**: Streamlit
- **Data Format**: JSON
- **Similarity Search**: Scikit-learn cosine similarity

## License

MIT License - See LICENSE file for details

## Credits

Built for the legal community to improve access to damages precedent data.
