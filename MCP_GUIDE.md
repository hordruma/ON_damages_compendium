# Ontario Damages Compendium - MCP Server Guide

The Ontario Damages Compendium is now available as an MCP (Model Context Protocol) server, allowing you to interact with the damages database through any MCP-compatible client.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the MCP Client

Add this configuration to your MCP client settings (e.g., Claude Desktop, Cline, etc.):

**For Claude Desktop** - Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ontario-damages-compendium": {
      "command": "python",
      "args": [
        "/absolute/path/to/ON_damages_compendium/mcp_server.py"
      ],
      "env": {
        "OPENAI_API_KEY": "your-openai-key-here",
        "ANTHROPIC_API_KEY": "your-anthropic-key-here"
      }
    }
  }
}
```

**For Other MCP Clients** - Use the provided `mcp_config.json` as a template.

### 3. Run the Server

The server starts automatically when your MCP client connects to it. No manual startup required!

## Available Features

### 🔍 Tools

The MCP server exposes the following tools:

#### 1. `search_damages_cases`
Search for comparable personal injury damage awards.

**Parameters:**
- `injury_description` (required): Detailed injury description
- `body_regions` (optional): Array of region IDs (e.g., `["cervical_spine", "shoulder_right"]`)
- `gender` (optional): "Male", "Female", or "Not Specified"
- `age` (optional): Age of plaintiff (5-100)
- `max_results` (optional): Maximum results to return (1-50, default: 10)

**Example:**
```json
{
  "injury_description": "C5-C6 disc herniation with chronic radicular pain radiating to right upper extremity",
  "body_regions": ["cervical_spine"],
  "gender": "Male",
  "age": 42,
  "max_results": 10
}
```

#### 2. `analyze_expert_report`
Extract injury information from medical/expert reports.

**Parameters:**
- `pdf_base64` (required): Base64-encoded PDF file
- `use_llm` (optional): Use LLM for analysis (default: true)

**Example:**
```json
{
  "pdf_base64": "JVBERi0xLjQKJeLjz9MKMy...",
  "use_llm": true
}
```

#### 3. `upload_cpi_data`
Upload Bank of Canada CPI data for inflation adjustments.

**Parameters:**
- `csv_content` (required): CSV file content with CPI data

**Example:**
```json
{
  "csv_content": "Year,CPI\n2024,160.85\n2023,157.11\n..."
}
```

#### 4. `set_llm_api_key`
Configure API keys for LLM providers.

**Parameters:**
- `provider` (required): "openai" or "anthropic"
- `api_key` (required): Your API key

**Example:**
```json
{
  "provider": "openai",
  "api_key": "sk-..."
}
```

#### 5. `generate_damages_report`
Generate a professional PDF report with search results.

**Parameters:**
- `injury_description` (required): Description used in search
- `body_regions` (optional): Array of region IDs
- `gender` (optional): Plaintiff gender
- `age` (optional): Plaintiff age
- `max_cases` (optional): Number of cases in report (default: 10)

**Returns:** Base64-encoded PDF report

#### 6. `adjust_for_inflation`
Adjust damage awards for inflation.

**Parameters:**
- `amount` (required): Original dollar amount
- `original_year` (required): Year of award
- `target_year` (optional): Target year (default: 2024)

**Example:**
```json
{
  "amount": 50000,
  "original_year": 2010,
  "target_year": 2024
}
```

#### 7. `get_available_regions`
Get list of available anatomical regions.

**Parameters:** None

### 📚 Resources

The server provides these resources:

1. **damages://cpi-data** - Current CPI data for inflation adjustments
2. **damages://statistics** - Database statistics (total cases, damage ranges, etc.)
3. **damages://regions** - Available body regions mapping

### 💬 Prompts

Pre-configured prompts for common workflows:

1. **search_injuries** - Search for comparable cases
   - Arguments: `injury`, `regions` (optional)

2. **analyze_report** - Analyze a medical report
   - Arguments: `report_path`

## Usage Examples

### Example 1: Search for Comparable Cases

Ask your MCP client:

```
Search the damages compendium for cases involving cervical spine injuries
with chronic radicular pain in a 45-year-old male plaintiff.
```

The client will use the `search_damages_cases` tool automatically.

### Example 2: Analyze an Expert Report

```
I have a medical report at /path/to/report.pdf. Please analyze it and
search for comparable cases.
```

The client will:
1. Read the PDF file
2. Use `analyze_expert_report` to extract injuries
3. Use `search_damages_cases` to find comparable cases

### Example 3: Set API Key and Upload CPI Data

```
Set my OpenAI API key to sk-... and upload the latest CPI data from
the Bank of Canada CSV file.
```

The client will:
1. Use `set_llm_api_key` to configure the API key
2. Use `upload_cpi_data` to update inflation data

### Example 4: Generate a Report

```
Generate a PDF report for lumbar spine injuries in a 35-year-old female
with chronic low back pain. Include the top 15 comparable cases.
```

The client will:
1. Search for cases
2. Generate a PDF report
3. Return the base64-encoded PDF

## Configuration Options

### API Keys

Set API keys either:

1. **Via Environment Variables** (in MCP config):
   ```json
   "env": {
     "OPENAI_API_KEY": "sk-...",
     "ANTHROPIC_API_KEY": "sk-ant-..."
   }
   ```

2. **Via the `set_llm_api_key` tool** (during runtime)

3. **Via .env file** (for development):
   ```bash
   cp .env.example .env
   # Edit .env and add your keys
   ```

### CPI Data

The server uses Bank of Canada CPI data for inflation adjustments:

1. **Default**: Built-in fallback data (1914-2025)
2. **Custom**: Upload via `upload_cpi_data` tool
3. **Auto-download**: Download from Bank of Canada website (requires network access)

## Troubleshooting

### Server Not Starting

1. Ensure Python dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Check that the path in your MCP config is absolute

3. Verify that `data/damages_with_embeddings.json` exists:
   ```bash
   # If missing, generate it:
   jupyter notebook 01_extract_and_embed.ipynb
   ```

### LLM Analysis Not Working

1. Check API key is set correctly
2. Verify API key has credits/quota available
3. Check network connectivity
4. Falls back to regex-based extraction if LLM unavailable

### CPI Data Issues

1. Verify CSV format matches Bank of Canada format
2. Check file permissions on `data/boc_cpi.csv`
3. Server uses fallback data if custom data unavailable

## Architecture

The MCP server wraps the existing Streamlit application functionality:

```
MCP Client (Claude Desktop, etc.)
    ↓
MCP Server (mcp_server.py)
    ↓
Application Modules
    ├── app/core/search.py - Case search engine
    ├── expert_report_analyzer.py - PDF analysis
    ├── inflation_adjuster.py - CPI calculations
    └── pdf_report_generator.py - Report generation
```

## Security Notes

1. **API Keys**: Never commit API keys to version control
2. **PDF Upload**: PDFs are processed in temporary files and deleted after analysis
3. **Data Access**: Server only accesses local database files
4. **Network**: Only outbound connections for LLM APIs and CPI downloads

## Support

For issues or questions:
- GitHub Issues: https://github.com/hordruma/ON_damages_compendium/issues
- Documentation: See README.md and EXPERT_REPORT_GUIDE.md

## License

MIT License - See LICENSE file for details
