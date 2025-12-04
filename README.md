# Ontario Damages Compendium - AI Search Tool

A professional legal tool for searching comparable personal injury awards in Ontario using AI-powered similarity search.

## Features

- **Visual Body Mapping**: Click on anatomical regions to select injury locations
- **Multi-Region Selection**: Support for cases with multiple injuries
- **Clinical Anatomy Labels**: Professional medical terminology for PI and insurance lawyers
- **Injury-Focused Search**: Semantic search based on injury descriptions with metadata filtering
- **Damage Award Analysis**: Automatic calculation of median, min, and max damage ranges
- **Gender & Age Filters**: Adjust search based on plaintiff demographics
- **🆕 Expert Report Analysis**: Upload medical/expert reports for automatic injury extraction
- **🆕 PDF Report Generation**: Download professional formatted reports with search results

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
├── parse_and_embed.ipynb          # Data extraction and embedding generation
├── streamlit_app.py               # Main Streamlit application
├── expert_report_analyzer.py      # Expert report PDF analysis
├── pdf_report_generator.py        # PDF report generation
├── region_map.json                # Clinical anatomy region mappings
├── .env.example                   # API key configuration template
├── app/
│   ├── core/
│   │   ├── search.py             # Injury-focused semantic search
│   │   ├── data_loader.py        # Data loading and initialization
│   │   └── config.py             # Configuration constants
│   └── ui/
│       ├── visualizations.py     # Chart generation
│       ├── fla_analytics.py      # Family Law Act analytics
│       └── judge_analytics.py    # Judge statistics
├── data/
│   ├── damages_with_embeddings.json  # Processed case data (generated)
│   ├── compendium_inj.json           # Injury-focused case data (generated)
│   ├── embeddings_inj.npy            # Injury embeddings matrix (generated)
│   └── ids.json                      # Embedding ID mapping (generated)
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── EXPERT_REPORT_GUIDE.md         # Guide for expert report analysis
└── [Additional documentation...]
```

## Usage

### Using the Web Interface (Streamlit)

#### Basic Workflow

1. **Prepare Data**: Place `2024damagescompendium.pdf` in the project root
2. **Extract Cases**: Run the Jupyter notebook to generate embeddings
3. **Launch App**: Run the Streamlit application
4. **Search Cases**:
   - Select gender and age
   - Click body regions to highlight injuries
   - Describe the injury in detail
   - Click "Find Comparable Cases"
   - Review matched cases and damage ranges

### 🆕 Expert Report Analysis (Optional)

Upload a medical/expert report PDF to automatically extract injuries:

1. **Configure API Key** (optional, for AI analysis):
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI or Anthropic API key
   ```

2. **Upload Report**:
   - Expand "Upload Expert/Medical Report" section
   - Choose PDF file (IME, medical report, expert opinion, etc.)
   - Click "Analyze Expert Report"
   - Review extracted information
   - Edit auto-populated fields if needed

3. **Run Search** as normal

See [EXPERT_REPORT_GUIDE.md](EXPERT_REPORT_GUIDE.md) for detailed instructions.

### 🆕 PDF Report Generation

Download professional formatted reports with your search results:

1. **Run a search** and review results
2. **Click "Generate PDF Report"**
3. **Choose number of cases** to include
4. **Download PDF** - Includes:
   - Search parameters
   - Damage award statistics
   - Top comparable cases with details
   - Legal disclaimer


## Technology Stack

- **PDF Extraction**: Camelot-py, PDFPlumber
- **Embeddings**: Sentence-Transformers (all-MiniLM-L6-v2)
- **Semantic Search**: NumPy cosine similarity with injury-focused embeddings
- **UI**: Streamlit
- **Data Format**: JSON
- **LLM Integration**: OpenAI GPT-4, Anthropic Claude (optional for expert report analysis)

## License

MIT License - See LICENSE file for details

## Credits

Built for the legal community to improve access to damages precedent data.
