# Quick Reference Guide

Quick commands and tips for using the Ontario Damages Compendium.

## Installation & Setup

```bash
# Clone repository
git clone https://github.com/hordruma/ON_damages_compendium.git
cd ON_damages_compendium

# Install dependencies
pip install -r requirements.txt

# Validate environment
python validate_environment.py

# Generate embeddings (first time only)
jupyter notebook 01_extract_and_embed.ipynb
```

## Running the Application

### Web Interface (Streamlit)
```bash
streamlit run streamlit_app.py
```
Access at: http://localhost:8501

### MCP Server
Configure in Claude Desktop (see [MCP_GUIDE.md](MCP_GUIDE.md)):
```json
{
  "mcpServers": {
    "ontario-damages-compendium": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

## Common Tasks

### Search for Cases
**Web UI:**
1. Select body regions in sidebar
2. Enter injury description
3. Click "Find Comparable Cases"

**MCP:**
```
Search the damages compendium for cervical spine injuries
with chronic radicular pain in a 45-year-old male.
```

### Analyze Expert Report
**Web UI:**
1. Expand "Upload Expert/Medical Report"
2. Upload PDF file
3. Click "Analyze Expert Report"
4. Review and edit extracted information

**MCP:**
```
Analyze the medical report at /path/to/report.pdf and
search for comparable cases.
```

### Generate PDF Report
**Web UI:**
1. Run a search
2. Scroll to "Download Report" section
3. Select number of cases
4. Click "Generate PDF Report"

**MCP:**
```
Generate a PDF report for lumbar spine injuries with
the top 15 comparable cases.
```

### Upload CPI Data
**Web UI:**
1. Expand "Update CPI Data" in sidebar
2. Upload Bank of Canada CSV
3. System automatically reloads data

**MCP:**
```
Upload the latest CPI data from the Bank of Canada CSV file.
```

### Set API Keys
**Via Environment:**
```bash
# Create .env file
cp .env.example .env
# Edit .env and add your keys
nano .env
```

**Via MCP:**
```
Set my OpenAI API key to sk-...
```

## Keyboard Shortcuts

### Streamlit App
- `Ctrl+R` - Rerun app
- `Ctrl+C` - Stop server (in terminal)
- `?` - Show keyboard shortcuts

## File Locations

### Data Files
- **Case Database**: `data/damages_with_embeddings.json` (generated)
- **Region Map**: `region_map.json`
- **CPI Data**: `data/boc_cpi.csv` (optional)
- **Source PDF**: `2024damagescompendium.pdf` (not included)

### Configuration
- **Environment Variables**: `.env`
- **MCP Config**: `mcp_config.json` (template)
- **Streamlit Config**: `.streamlit/config.toml`

### Assets
- **Body Diagrams**: `assets/body_front.svg`, `assets/body_back.svg`

## Anatomical Regions

### Head & Spine (5)
- head
- cervical_spine (neck)
- thoracic_spine (mid-back)
- lumbar_spine (low back)
- sacroiliac (sacrum)

### Torso (3)
- chest
- abdomen
- pelvis

### Upper Limbs (12)
- shoulder_left/right
- arm_left/right
- elbow_left/right
- forearm_left/right
- wrist_left/right
- hand_left/right

### Lower Limbs (12)
- hip_left/right
- thigh_left/right
- knee_left/right
- lower_leg_left/right
- ankle_left/right
- foot_left/right

## Data Sources

### CPI Data
- **Source**: Bank of Canada
- **URL**: https://www.bankofcanada.ca/valet/observations/group/CPI_MONTHLY/csv
- **Format**: CSV with Year, CPI columns
- **Update Frequency**: Monthly

### Damages Compendium
- **Source**: CCLA Damages Compendium 2024
- **Format**: PDF → Extracted → JSON with embeddings
- **Update**: Annual (when new compendium released)

## API Keys

### OpenAI
- **Get Key**: https://platform.openai.com/api-keys
- **Used For**: Expert report analysis (GPT-4)
- **Format**: `sk-...`

### Anthropic
- **Get Key**: https://console.anthropic.com/
- **Used For**: Expert report analysis (Claude)
- **Format**: `sk-ant-...`

**Note**: Only ONE key needed. System falls back to regex if no key provided.

## Troubleshooting

### "Data file not found"
```bash
# Generate embeddings
jupyter notebook 01_extract_and_embed.ipynb
# Run all cells
```

### "ModuleNotFoundError"
```bash
# Install dependencies
pip install -r requirements.txt
```

### MCP Server Not Connecting
1. Check Python path is absolute in config
2. Verify data files exist
3. Restart MCP client
4. Check logs for errors

### Slow First Search
- Normal - model loads on first use
- Subsequent searches are fast (<1 second)

### Out of Memory
- Close other applications
- Use smaller batch size in config
- Upgrade RAM if persistent

## Performance Tips

1. **Cache Warming**: First search loads models (2-3 seconds)
2. **Batch Searches**: Multiple searches reuse loaded models
3. **Region Filtering**: Select specific regions for faster/more relevant results
4. **Clinical Terms**: Use medical terminology for better matches
5. **CPI Updates**: Update CPI data monthly for accurate inflation adjustments

## Best Practices

### Writing Injury Descriptions
✅ **Good:**
```
C5-C6 disc herniation with chronic radicular pain radiating
to right upper extremity. Failed conservative management.
MRI shows central disc protrusion with nerve root impingement.
```

❌ **Poor:**
```
neck pain
```

### Selecting Regions
- Select all affected regions
- Include adjacent regions for better coverage
- Use spine regions for nerve-related injuries

### Analyzing Reports
- Upload complete medical reports (not summaries)
- Review extracted information before searching
- Edit auto-filled fields for accuracy

## Command Cheat Sheet

```bash
# Setup
pip install -r requirements.txt
python validate_environment.py

# Run applications
streamlit run streamlit_app.py
python mcp_server.py  # (via MCP client)

# Testing
pytest tests/
pytest tests/test_mcp_server.py

# Update data
jupyter notebook 01_extract_and_embed.ipynb

# Validation
python validate_environment.py

# Git operations
git status
git add .
git commit -m "message"
git push origin main
```

## Environment Variables

```bash
# Required: NONE (works with built-in fallbacks)

# Optional:
OPENAI_API_KEY=sk-...           # For AI report analysis
ANTHROPIC_API_KEY=sk-ant-...    # Alternative to OpenAI
STREAMLIT_SERVER_PORT=8501      # Custom port
STREAMLIT_SERVER_ADDRESS=0.0.0.0  # Custom bind address
```

## Port Numbers

- **Streamlit**: 8501 (default)
- **Jupyter**: 8888 (default)
- **MCP Server**: stdio (no port)

## Documentation Links

- **README**: [README.md](README.md) - Overview and features
- **MCP Guide**: [MCP_GUIDE.md](MCP_GUIDE.md) - MCP server setup
- **Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment
- **Expert Reports**: [EXPERT_REPORT_GUIDE.md](EXPERT_REPORT_GUIDE.md) - Report analysis
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md) - Getting started
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide

## Support

- **Issues**: https://github.com/hordruma/ON_damages_compendium/issues
- **Discussions**: GitHub Discussions
- **Documentation**: Project MD files

## Version Info

Run this to check versions:
```bash
python --version
pip show streamlit sentence-transformers mcp
```

## License

MIT License - See [LICENSE](LICENSE) file

---

**Tip**: Run `python validate_environment.py` after setup to verify everything works!
