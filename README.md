# Ontario Damages Compendium - Visual Search Tool

A professional legal tool for searching comparable personal injury awards in Ontario using visual body mapping and AI-powered similarity search.

## Features

- **Visual Body Mapping**: Click on anatomical regions to select injury locations
- **Multi-Region Selection**: Support for cases with multiple injuries
- **Clinical Anatomy Labels**: Professional medical terminology for PI and insurance lawyers
- **AI-Powered Search**: Embedding-based similarity matching for finding comparable cases
- **Damage Award Analysis**: Automatic calculation of median, min, and max damage ranges
- **Gender & Age Filters**: Adjust search based on plaintiff demographics
- **🆕 Expert Report Analysis**: Upload medical/expert reports for automatic injury extraction
- **🆕 PDF Report Generation**: Download professional formatted reports with search results
- **🆕 MCP Server Support**: Access via Model Context Protocol for integration with AI assistants

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

**Or use as an MCP Server:**

See [MCP_GUIDE.md](MCP_GUIDE.md) for complete MCP server setup instructions.

## Project Structure

```
ON_damages_compendium/
├── 01_extract_and_embed.ipynb    # Data extraction and embedding generation
├── streamlit_app.py               # Main Streamlit application
├── mcp_server.py                  # MCP server for AI assistant integration
├── expert_report_analyzer.py     # Expert report PDF analysis
├── pdf_report_generator.py       # PDF report generation
├── region_map.json                # Clinical anatomy region mappings
├── .env.example                   # API key configuration template
├── mcp_config.json                # MCP server configuration template
├── assets/
│   ├── body_front.svg             # Front body diagram
│   └── body_back.svg              # Back body diagram
├── data/
│   └── damages_with_embeddings.json  # Processed case data (generated)
├── requirements.txt               # Python dependencies
├── README.md                      # This file
├── MCP_GUIDE.md                   # MCP server usage guide
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

### 🆕 Using via MCP Server

The Ontario Damages Compendium can be accessed through any MCP-compatible client (Claude Desktop, Cline, etc.):

1. **Configure MCP Client**: Add server configuration to your MCP client
2. **Access via Natural Language**: Ask your AI assistant to search cases, analyze reports, etc.
3. **Automated Workflows**: Combine multiple operations (analyze report → search cases → generate PDF)

**Quick Setup:**

```json
{
  "mcpServers": {
    "ontario-damages-compendium": {
      "command": "python",
      "args": ["/absolute/path/to/ON_damages_compendium/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "your-key-here"
      }
    }
  }
}
```

**Available MCP Features:**
- 🔍 Search for comparable cases
- 📄 Analyze expert/medical reports
- 💰 Adjust awards for inflation
- 📊 Upload custom CPI data
- 🔑 Configure LLM API keys
- 📥 Generate PDF reports
- 📚 Access resources (CPI data, statistics, regions)

See **[MCP_GUIDE.md](MCP_GUIDE.md)** for complete documentation.

## Technology Stack

- **PDF Extraction**: Camelot-py, PDFPlumber
- **Embeddings**: Sentence-Transformers (all-MiniLM-L6-v2)
- **UI**: Streamlit
- **MCP Server**: Model Context Protocol (MCP SDK)
- **Data Format**: JSON
- **Similarity Search**: Scikit-learn cosine similarity
- **LLM Integration**: OpenAI GPT-4, Anthropic Claude

## License

MIT License - See LICENSE file for details

## Credits

Built for the legal community to improve access to damages precedent data.
