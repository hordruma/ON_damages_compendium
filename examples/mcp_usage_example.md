# MCP Server Usage Examples

This document provides example prompts and workflows for using the Ontario Damages Compendium MCP server.

## Setup

First, configure your MCP client (e.g., Claude Desktop) with the server:

```json
{
  "mcpServers": {
    "ontario-damages-compendium": {
      "command": "python",
      "args": ["/path/to/ON_damages_compendium/mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

## Example Workflows

### Example 1: Simple Case Search

**User Prompt:**
```
Search the Ontario Damages Compendium for cases involving cervical spine
injuries with chronic radicular pain in a 45-year-old male plaintiff.
```

**What Happens:**
1. AI uses `search_damages_cases` tool
2. Returns top 10 comparable cases
3. Shows damage award statistics
4. Displays inflation-adjusted values

**Expected Output:**
```json
{
  "summary": {
    "total_matches": 10,
    "damages_statistics": {
      "median": 75000,
      "min": 35000,
      "max": 150000
    }
  },
  "cases": [...]
}
```

### Example 2: Expert Report Analysis + Search

**User Prompt:**
```
I have a medical report. Please analyze it and find comparable cases.

[Attach PDF file or provide base64-encoded content]
```

**What Happens:**
1. AI uses `analyze_expert_report` tool to extract injuries
2. Identifies body regions, limitations, and chronicity
3. Uses `search_damages_cases` with extracted information
4. Returns analysis + comparable cases

**Workflow:**
```
analyze_expert_report(pdf)
  → extracts: cervical_spine, chronic, radicular pain
  → search_damages_cases(regions=["cervical_spine"], injury_desc="...")
  → returns: top cases
```

### Example 3: Inflation Adjustment

**User Prompt:**
```
A damage award of $50,000 was made in 2010. What would that be worth
in 2024 dollars?
```

**What Happens:**
1. AI uses `adjust_for_inflation` tool
2. Calculates inflation-adjusted value using CPI data

**Expected Output:**
```json
{
  "original_amount": 50000,
  "original_year": 2010,
  "adjusted_amount": 65432,
  "target_year": 2024,
  "inflation_rate_percent": 30.86
}
```

### Example 4: Upload CPI Data

**User Prompt:**
```
I have the latest Bank of Canada CPI data. Please update the system.

[Attach CSV file]
```

**What Happens:**
1. AI reads CSV content
2. Uses `upload_cpi_data` tool
3. System reloads CPI data
4. Confirms update with year range

### Example 5: Generate PDF Report

**User Prompt:**
```
Generate a professional PDF report for lumbar spine injuries in a
35-year-old female with chronic low back pain. Include the top 15
comparable cases.
```

**What Happens:**
1. AI searches for cases
2. Uses `generate_damages_report` tool
3. Returns base64-encoded PDF
4. User can download the PDF

### Example 6: Configure API Key

**User Prompt:**
```
Set my OpenAI API key to sk-proj-abc123...
```

**What Happens:**
1. AI uses `set_llm_api_key` tool
2. Stores key for expert report analysis
3. Confirms configuration

### Example 7: Multi-Region Search

**User Prompt:**
```
Search for cases involving injuries to the cervical spine, right shoulder,
and right arm in a 38-year-old male from a motor vehicle accident.
```

**What Happens:**
1. AI identifies multiple regions
2. Uses `search_damages_cases` with:
   - regions: ["cervical_spine", "shoulder_right", "arm_right"]
   - age: 38
   - gender: "Male"
3. Returns cases matching multiple regions

### Example 8: Explore Available Regions

**User Prompt:**
```
What body regions can I search for in the damages compendium?
```

**What Happens:**
1. AI uses `get_available_regions` tool
2. Returns all 32+ anatomical regions
3. Shows clinical labels and terminology

**Expected Output:**
```json
{
  "total_regions": 32,
  "regions": [
    {
      "id": "cervical_spine",
      "label": "Cervical Spine (Neck)",
      "compendium_terms": ["cervical spine", "neck", "C1-C7"]
    },
    ...
  ]
}
```

### Example 9: Access Resources

**User Prompt:**
```
Show me the current CPI data being used for inflation adjustments.
```

**What Happens:**
1. AI accesses `damages://cpi-data` resource
2. Returns CPI data with year range and source

**User Prompt:**
```
What are the statistics for the damages database?
```

**What Happens:**
1. AI accesses `damages://statistics` resource
2. Returns total cases, damage ranges, year coverage

## Advanced Workflows

### Workflow 1: Complete Case Analysis

```
1. User uploads expert medical report
2. AI analyzes report → extracts injuries
3. AI searches for comparable cases
4. AI generates inflation-adjusted analysis
5. AI creates PDF report with findings
6. User downloads report
```

### Workflow 2: Historical Comparison

```
1. User asks about historical trends for specific injury
2. AI searches cases across multiple years
3. AI adjusts all awards to current dollars
4. AI provides statistical analysis
5. AI highlights how awards have changed over time
```

### Workflow 3: Multi-Injury Complex Case

```
1. User describes complex multi-region injury
2. AI breaks down into individual regions
3. AI searches for each region separately
4. AI searches for combined injuries
5. AI compares single vs. multi-region awards
6. AI provides comprehensive analysis
```

## Tips for Best Results

### For Case Searches:
- Use clinical terminology (e.g., "C5-C6 disc herniation" not "neck pain")
- Specify chronicity (acute, chronic, permanent)
- Include mechanism if relevant (MVA, slip & fall, etc.)
- Mention functional limitations
- Be specific about anatomical structures

### For Expert Report Analysis:
- Ensure PDF contains clear injury descriptions
- Better results with structured medical reports
- LLM analysis (OpenAI/Anthropic) more accurate than regex
- Review and edit extracted information before searching

### For Inflation Adjustments:
- Ensure case years are accurate
- Keep CPI data updated
- Consider downloading latest BOC data periodically
- Note that adjustments use annual averages

## Common Scenarios

### Scenario: "I need comparable cases for a settlement negotiation"
1. Describe injury in detail
2. Search for top 20 cases
3. Generate PDF report for documentation
4. Use inflation-adjusted values for current settlement

### Scenario: "I'm preparing a claim and have medical reports"
1. Upload all medical/expert reports
2. Extract injuries from each
3. Combine information
4. Search for comparable cases
5. Generate comprehensive PDF

### Scenario: "I want to track damage award trends over time"
1. Search for specific injury type
2. Request cases from last 20 years
3. Adjust all to current dollars
4. Analyze trends in median awards

## Error Handling

The MCP server handles common errors gracefully:

- **Missing API Key**: Falls back to regex-based extraction
- **Invalid PDF**: Returns error with helpful message
- **No CPI Data**: Uses built-in fallback data
- **Invalid Region IDs**: Filters out unknown regions
- **Network Issues**: Uses local data when possible

## Performance Notes

- First search may take 2-3 seconds (model loading)
- Subsequent searches are fast (<1 second)
- PDF analysis with LLM: 3-5 seconds
- PDF report generation: 1-2 seconds
- Large searches (50+ cases) may take longer

## Support

For issues or questions:
- See [MCP_GUIDE.md](../MCP_GUIDE.md) for detailed documentation
- Check [README.md](../README.md) for general usage
- Report issues on GitHub
