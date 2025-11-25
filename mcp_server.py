"""
Ontario Damages Compendium - MCP Server
Exposes the damages compendium functionality via Model Context Protocol (MCP)
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import base64

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    Resource,
    ResourceTemplate,
    INTERNAL_ERROR,
)

# Import application modules
from app.core.config import *
from app.core.data_loader import initialize_data
from app.core.search import search_cases, extract_damages_value
from expert_report_analyzer import analyze_expert_report
from inflation_adjuster import (
    adjust_for_inflation,
    get_cpi_data,
    reload_cpi_data,
    get_data_source,
    DEFAULT_REFERENCE_YEAR,
    BOC_CPI_CSV
)
from pdf_report_generator import generate_damages_report
import numpy as np

# ============================================================================
# SERVER INITIALIZATION
# ============================================================================

# Initialize the MCP server
app = Server("ontario-damages-compendium")

# Global state for application data
model = None
cases = None
region_map = None
llm_api_keys = {
    "openai": os.getenv("OPENAI_API_KEY"),
    "anthropic": os.getenv("ANTHROPIC_API_KEY")
}

def initialize_app():
    """Initialize the application data"""
    global model, cases, region_map
    if model is None:
        model, cases, region_map = initialize_data()

# ============================================================================
# RESOURCES
# ============================================================================

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources"""
    initialize_app()

    return [
        Resource(
            uri="damages://cpi-data",
            name="Current CPI Data",
            mimeType="application/json",
            description="Current Consumer Price Index data used for inflation adjustments"
        ),
        Resource(
            uri="damages://statistics",
            name="Database Statistics",
            mimeType="application/json",
            description="Statistics about the damages compendium database"
        ),
        Resource(
            uri="damages://regions",
            name="Body Regions Map",
            mimeType="application/json",
            description="Available anatomical regions for injury mapping"
        ),
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI"""
    initialize_app()

    if uri == "damages://cpi-data":
        cpi_data = get_cpi_data()
        return json.dumps({
            "source": get_data_source(),
            "data": {str(year): value for year, value in cpi_data.items()},
            "reference_year": DEFAULT_REFERENCE_YEAR
        }, indent=2)

    elif uri == "damages://statistics":
        # Calculate database statistics
        total_cases = len(cases)

        # Extract damages values
        damages_values = []
        years = []
        for case in cases:
            damage_val = extract_damages_value(case)
            if damage_val:
                damages_values.append(damage_val)
            if case.get('year'):
                years.append(case['year'])

        stats = {
            "total_cases": total_cases,
            "cases_with_damages": len(damages_values),
            "damages_range": {
                "min": float(np.min(damages_values)) if damages_values else 0,
                "max": float(np.max(damages_values)) if damages_values else 0,
                "median": float(np.median(damages_values)) if damages_values else 0,
                "mean": float(np.mean(damages_values)) if damages_values else 0
            },
            "year_range": {
                "earliest": int(min(years)) if years else None,
                "latest": int(max(years)) if years else None
            }
        }

        return json.dumps(stats, indent=2)

    elif uri == "damages://regions":
        return json.dumps(region_map, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")

# ============================================================================
# TOOLS
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="search_damages_cases",
            description="Search for comparable personal injury damage awards based on injury description and body regions",
            inputSchema={
                "type": "object",
                "properties": {
                    "injury_description": {
                        "type": "string",
                        "description": "Detailed description of the injury (include anatomical structures, severity, chronicity)"
                    },
                    "body_regions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of injured body region IDs (e.g., ['cervical_spine', 'shoulder_right'])",
                        "default": []
                    },
                    "gender": {
                        "type": "string",
                        "enum": ["Male", "Female", "Not Specified"],
                        "description": "Gender of plaintiff",
                        "default": "Not Specified"
                    },
                    "age": {
                        "type": "integer",
                        "description": "Age of plaintiff at time of injury",
                        "default": 35,
                        "minimum": 5,
                        "maximum": 100
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": ["injury_description"]
            }
        ),
        Tool(
            name="analyze_expert_report",
            description="Analyze a medical/expert report PDF to extract injury information",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_base64": {
                        "type": "string",
                        "description": "Base64-encoded PDF file content"
                    },
                    "use_llm": {
                        "type": "boolean",
                        "description": "Use LLM for analysis (requires API key)",
                        "default": True
                    }
                },
                "required": ["pdf_base64"]
            }
        ),
        Tool(
            name="upload_cpi_data",
            description="Upload Bank of Canada CPI data to update inflation adjustments",
            inputSchema={
                "type": "object",
                "properties": {
                    "csv_content": {
                        "type": "string",
                        "description": "CSV file content with Bank of Canada CPI data"
                    }
                },
                "required": ["csv_content"]
            }
        ),
        Tool(
            name="set_llm_api_key",
            description="Set API key for LLM provider (OpenAI or Anthropic) for expert report analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "anthropic"],
                        "description": "LLM provider"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "API key for the provider"
                    }
                },
                "required": ["provider", "api_key"]
            }
        ),
        Tool(
            name="generate_damages_report",
            description="Generate a professional PDF report with search results",
            inputSchema={
                "type": "object",
                "properties": {
                    "injury_description": {
                        "type": "string",
                        "description": "Description of the injury used in search"
                    },
                    "body_regions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of injured body region IDs",
                        "default": []
                    },
                    "gender": {
                        "type": "string",
                        "enum": ["Male", "Female", "Not Specified"],
                        "default": "Not Specified"
                    },
                    "age": {
                        "type": "integer",
                        "default": 35
                    },
                    "max_cases": {
                        "type": "integer",
                        "description": "Number of cases to include in report",
                        "default": 10
                    }
                },
                "required": ["injury_description"]
            }
        ),
        Tool(
            name="adjust_for_inflation",
            description="Adjust a damage award amount for inflation to current dollars",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Original dollar amount"
                    },
                    "original_year": {
                        "type": "integer",
                        "description": "Year the award was made"
                    },
                    "target_year": {
                        "type": "integer",
                        "description": "Year to adjust to (default: 2024)",
                        "default": DEFAULT_REFERENCE_YEAR
                    }
                },
                "required": ["amount", "original_year"]
            }
        ),
        Tool(
            name="get_available_regions",
            description="Get list of available body regions for injury selection",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    initialize_app()

    try:
        if name == "search_damages_cases":
            injury_description = arguments["injury_description"]
            body_regions = arguments.get("body_regions", [])
            gender = arguments.get("gender", "Not Specified")
            age = arguments.get("age", 35)
            max_results = arguments.get("max_results", 10)

            # Perform search
            results = search_cases(
                injury_description,
                body_regions,
                cases,
                region_map,
                model,
                gender=gender if gender != "Not Specified" else None,
                age=age
            )

            # Limit results
            results = results[:max_results]

            # Extract damages for summary
            damages_values = []
            for case, emb_sim, combined_score in results:
                damage_val = extract_damages_value(case)
                if damage_val:
                    damages_values.append(damage_val)

            # Format results
            result_data = {
                "summary": {
                    "total_matches": len(results),
                    "cases_with_damages": len(damages_values),
                    "damages_statistics": {
                        "median": float(np.median(damages_values)) if damages_values else None,
                        "min": float(np.min(damages_values)) if damages_values else None,
                        "max": float(np.max(damages_values)) if damages_values else None,
                        "mean": float(np.mean(damages_values)) if damages_values else None
                    }
                },
                "cases": []
            }

            for idx, (case, emb_sim, combined_score) in enumerate(results, 1):
                damage_val = extract_damages_value(case)

                case_info = {
                    "rank": idx,
                    "case_name": case.get("case_name", "Unknown"),
                    "region": case.get("region", "Unknown"),
                    "year": case.get("year"),
                    "court": case.get("court"),
                    "damages": damage_val,
                    "similarity_score": float(emb_sim),
                    "combined_score": float(combined_score),
                    "summary": case.get("summary_text", "")[:500]
                }

                # Add inflation-adjusted amount if year available
                if damage_val and case.get("year"):
                    adjusted = adjust_for_inflation(
                        damage_val,
                        case["year"],
                        DEFAULT_REFERENCE_YEAR
                    )
                    if adjusted:
                        case_info["damages_adjusted"] = adjusted
                        case_info["adjusted_to_year"] = DEFAULT_REFERENCE_YEAR

                result_data["cases"].append(case_info)

            return [TextContent(
                type="text",
                text=json.dumps(result_data, indent=2)
            )]

        elif name == "analyze_expert_report":
            pdf_base64 = arguments["pdf_base64"]
            use_llm = arguments.get("use_llm", True)

            # Decode PDF
            pdf_data = base64.b64decode(pdf_base64)

            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_data)
                tmp_path = tmp_file.name

            try:
                # Analyze report
                api_key = llm_api_keys.get("openai") or llm_api_keys.get("anthropic")
                provider = "openai" if llm_api_keys.get("openai") else "anthropic"

                analysis = analyze_expert_report(
                    tmp_path,
                    api_key=api_key,
                    provider=provider,
                    use_llm=use_llm and api_key is not None
                )

                return [TextContent(
                    type="text",
                    text=json.dumps(analysis, indent=2)
                )]

            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        elif name == "upload_cpi_data":
            csv_content = arguments["csv_content"]

            # Save CSV content
            BOC_CPI_CSV.parent.mkdir(parents=True, exist_ok=True)
            with open(BOC_CPI_CSV, 'w', encoding='utf-8') as f:
                f.write(csv_content)

            # Reload data
            new_data = reload_cpi_data()

            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": f"CPI data updated successfully! Now have {len(new_data)} years of data.",
                    "source": get_data_source()
                }, indent=2)
            )]

        elif name == "set_llm_api_key":
            provider = arguments["provider"]
            api_key = arguments["api_key"]

            # Store API key
            llm_api_keys[provider] = api_key

            # Also set environment variable
            env_var = f"{provider.upper()}_API_KEY"
            os.environ[env_var] = api_key

            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": f"API key for {provider} has been set successfully",
                    "provider": provider
                }, indent=2)
            )]

        elif name == "generate_damages_report":
            injury_description = arguments["injury_description"]
            body_regions = arguments.get("body_regions", [])
            gender = arguments.get("gender", "Not Specified")
            age = arguments.get("age", 35)
            max_cases = arguments.get("max_cases", 10)

            # Perform search first
            results = search_cases(
                injury_description,
                body_regions,
                cases,
                region_map,
                model,
                gender=gender if gender != "Not Specified" else None,
                age=age
            )

            # Extract damages
            damages_values = []
            for case, emb_sim, combined_score in results:
                damage_val = extract_damages_value(case)
                if damage_val:
                    damages_values.append(damage_val)

            # Prepare region labels
            region_labels = {
                rid: region_map[rid]["label"]
                for rid in body_regions
                if rid in region_map
            }

            # Generate PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                pdf_path = tmp_file.name

            try:
                generate_damages_report(
                    output_path=pdf_path,
                    selected_regions=body_regions,
                    region_labels=region_labels,
                    injury_description=injury_description,
                    results=results,
                    damages_values=damages_values,
                    gender=gender if gender != "Not Specified" else None,
                    age=age,
                    max_cases=max_cases
                )

                # Read PDF and encode
                with open(pdf_path, 'rb') as f:
                    pdf_data = f.read()

                pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "success",
                        "message": "PDF report generated successfully",
                        "pdf_base64": pdf_base64,
                        "cases_included": min(len(results), max_cases)
                    }, indent=2)
                )]

            finally:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)

        elif name == "adjust_for_inflation":
            amount = arguments["amount"]
            original_year = arguments["original_year"]
            target_year = arguments.get("target_year", DEFAULT_REFERENCE_YEAR)

            adjusted = adjust_for_inflation(amount, original_year, target_year)

            if adjusted is None:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "message": f"CPI data not available for years {original_year} or {target_year}"
                    }, indent=2)
                )]

            inflation_rate = ((adjusted - amount) / amount) * 100

            return [TextContent(
                type="text",
                text=json.dumps({
                    "original_amount": amount,
                    "original_year": original_year,
                    "adjusted_amount": adjusted,
                    "target_year": target_year,
                    "inflation_rate_percent": round(inflation_rate, 2)
                }, indent=2)
            )]

        elif name == "get_available_regions":
            regions_list = []

            for region_id, region_data in region_map.items():
                regions_list.append({
                    "id": region_id,
                    "label": region_data["label"],
                    "compendium_terms": region_data.get("compendium_terms", [])
                })

            return [TextContent(
                type="text",
                text=json.dumps({
                    "total_regions": len(regions_list),
                    "regions": regions_list
                }, indent=2)
            )]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "error",
                "message": str(e)
            }, indent=2)
        )]

# ============================================================================
# PROMPTS
# ============================================================================

@app.list_prompts()
async def list_prompts() -> list[Any]:
    """List available prompt templates"""
    from mcp.types import Prompt, PromptArgument

    return [
        Prompt(
            name="search_injuries",
            description="Search for comparable cases based on injury description",
            arguments=[
                PromptArgument(
                    name="injury",
                    description="Description of the injury",
                    required=True
                ),
                PromptArgument(
                    name="regions",
                    description="Comma-separated body regions (optional)",
                    required=False
                )
            ]
        ),
        Prompt(
            name="analyze_report",
            description="Analyze an expert medical report",
            arguments=[
                PromptArgument(
                    name="report_path",
                    description="Path to the PDF report",
                    required=True
                )
            ]
        )
    ]

@app.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> Any:
    """Get a prompt template"""
    from mcp.types import PromptMessage, TextContent as PromptTextContent

    if name == "search_injuries":
        injury = arguments.get("injury", "") if arguments else ""
        regions = arguments.get("regions", "").split(",") if arguments and arguments.get("regions") else []

        prompt_text = f"""Search the Ontario Damages Compendium for cases similar to this injury:

Injury Description: {injury}
Body Regions: {', '.join(regions) if regions else 'Not specified'}

Please use the search_damages_cases tool to find comparable cases and provide:
1. Summary statistics of damage awards
2. Top 5-10 most similar cases
3. Key factors that make these cases comparable
4. Inflation-adjusted values where applicable
"""

        return PromptMessage(
            role="user",
            content=PromptTextContent(type="text", text=prompt_text)
        )

    elif name == "analyze_report":
        report_path = arguments.get("report_path", "") if arguments else ""

        prompt_text = f"""Analyze the medical/expert report at: {report_path}

Please:
1. Extract all injuries and affected body regions
2. Identify functional limitations
3. Determine injury chronicity (acute/chronic/permanent)
4. Extract mechanism of injury
5. Use the extracted information to search for comparable cases
"""

        return PromptMessage(
            role="user",
            content=PromptTextContent(type="text", text=prompt_text)
        )

    raise ValueError(f"Unknown prompt: {name}")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
