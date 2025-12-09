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

### 1. Clone the repository
```bash
git clone https://github.com/hordruma/ON_damages_compendium.git
cd ON_damages_compendium
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Prepare your data

Place your source data file (e.g., `damages_table_based.json`) in the project root. This should contain the parsed case data from the Ontario Damages Compendium.

### 4. Generate embeddings

Run the embedding generation script to create the searchable database:

```bash
python build_embeddings.py
```

**Hardware Requirements:**
- **GPU recommended** for faster embedding generation (~10-20 minutes with GPU vs 1-2 hours on CPU)
- Supports CUDA GPUs (NVIDIA) - automatically detected
- Falls back to CPU if no GPU available
- Requires ~2GB RAM during processing

**What this does:**
1. Loads the source case data
2. Converts to dashboard format
3. Generates semantic embeddings for all cases using `all-mpnet-base-v2` model
4. Creates injury-focused search indices
5. Outputs to `data/` directory

**Output files:**
- `data/damages_with_embeddings.json` - Main dashboard data with full embeddings
- `data/compendium_inj.json` - Injury-focused case data
- `data/embeddings_inj.npy` - Pre-computed embedding matrix for fast search
- `data/ids.json` - Case ID mapping

**Alternative (for development/debugging):**
If you prefer using Jupyter notebooks:
```bash
jupyter notebook parse_and_embed.ipynb
```

### 5. Run the Streamlit app

```bash
streamlit run streamlit_app.py
```

The app will automatically load the generated data files.

## Project Structure

```
ON_damages_compendium/
├── streamlit_app.py               # Main Streamlit application
├── build_embeddings.py            # Embedding generation script (GPU-accelerated)
├── data_transformer.py            # Data format conversion utilities
├── parse_and_embed.ipynb          # Alternative notebook for embedding generation
├── expert_report_analyzer.py      # Expert report PDF analysis
├── pdf_report_generator.py        # PDF report generation
├── region_map.json                # Clinical anatomy region mappings
├── .env.example                   # API key configuration template
├── app/
│   ├── core/
│   │   ├── search.py             # Injury-focused semantic search
│   │   ├── data_loader.py        # Data loading (CPU-only for Streamlit Cloud)
│   │   └── config.py             # Configuration constants
│   └── ui/
│       ├── visualizations.py     # Chart generation
│       ├── fla_analytics.py      # Family Law Act analytics
│       └── judge_analytics.py    # Judge statistics
├── data/                          # Generated data (create via build_embeddings.py)
│   ├── damages_with_embeddings.json  # Main dashboard data with embeddings
│   ├── compendium_inj.json           # Injury-focused case data
│   ├── embeddings_inj.npy            # Pre-computed embedding matrix
│   └── ids.json                      # Case ID mapping
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── EXPERT_REPORT_GUIDE.md         # Guide for expert report analysis
```

## Usage

### Using the Web Interface (Streamlit)

#### Basic Workflow

1. **Ensure Data is Generated**: Run `python build_embeddings.py` if you haven't already (see Installation step 4)
2. **Launch App**:
   ```bash
   streamlit run streamlit_app.py
   ```
3. **Search for Comparable Cases**:
   - Select gender and age filters (optional)
   - Click body regions on the anatomical diagram to highlight injury areas
   - Enter a detailed injury description in the search box
   - Adjust the number of results (default: 15)
   - Click "Find Comparable Cases"
   - Review matched cases with similarity scores
   - Analyze damage award statistics (median, min, max)

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
- **Embeddings**: Sentence-Transformers (`all-mpnet-base-v2`)
  - 420MB model with excellent medical terminology understanding
  - GPU-accelerated during embedding generation (optional)
  - CPU-only during app runtime (for Streamlit Cloud compatibility)
- **Semantic Search**: NumPy cosine similarity with injury-focused embeddings
- **UI**: Streamlit
- **Data Format**: JSON
- **LLM Integration**: OpenAI GPT-4, Anthropic Claude (optional for expert report analysis)

## Deployment

### Local Development

Run the app locally with full features:

```bash
streamlit run streamlit_app.py
```

**Performance Tips:**
- Use GPU for initial embedding generation (`build_embeddings.py`)
- The app itself runs fine on CPU
- First launch may take 30-60 seconds to load the embedding model into memory
- Subsequent searches are fast (~100ms)

### Streamlit Cloud Deployment

The app is configured to run on Streamlit Cloud (CPU-only environment):

1. **Data Preparation**:
   - Generate embeddings locally using `build_embeddings.py` (with GPU if available)
   - Commit the `data/` directory to your repository
   - Or generate embeddings on first cloud startup (slower, ~1-2 hours)

2. **Deploy to Streamlit Cloud**:
   - Connect your GitHub repository
   - Set secrets for API keys (if using expert report analysis)
   - The app automatically detects CPU-only environment and configures accordingly

3. **Environment Variables** (if using expert report features):
   - `OPENAI_API_KEY` - For GPT-based report analysis
   - `ANTHROPIC_API_KEY` - For Claude-based report analysis

**Note**: The data loader (`app/core/data_loader.py`) is configured to force CPU usage for model inference, ensuring compatibility with Streamlit Cloud's CPU-only containers.

## License

MIT License - See LICENSE file for details

## Credits

Built for the legal community to improve access to damages precedent data.
