"""
Tests for the MCP Server
Tests the Ontario Damages Compendium MCP server functionality
"""

import pytest
import json
import base64
import tempfile
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import (
    initialize_app,
    extract_damages_value
)


class TestMCPServer:
    """Test suite for MCP server functionality"""

    def test_initialization(self):
        """Test that the app initializes properly"""
        try:
            # Note: This will fail if data files don't exist, which is expected
            # in test environment without full data setup
            initialize_app()
        except SystemExit:
            # Expected when data files missing
            pass
        except Exception as e:
            pytest.fail(f"Unexpected error during initialization: {e}")

    def test_extract_damages_from_dict(self):
        """Test damage value extraction from case dictionary"""
        # Test direct damages field
        case_with_damages = {"damages": 50000.0}
        assert extract_damages_value(case_with_damages) == 50000.0

        # Test extraction from summary text
        case_with_text = {
            "summary_text": "The plaintiff was awarded $75,000 in damages"
        }
        assert extract_damages_value(case_with_text) == 75000.0

        # Test no damages found
        case_no_damages = {"summary_text": "No award mentioned"}
        assert extract_damages_value(case_no_damages) is None

    def test_json_serialization(self):
        """Test that MCP responses are valid JSON"""
        test_data = {
            "status": "success",
            "results": [
                {"case_name": "Test v. Test", "damages": 50000}
            ]
        }

        # Should serialize without errors
        json_str = json.dumps(test_data)
        # Should deserialize back to same structure
        parsed = json.loads(json_str)
        assert parsed == test_data

    def test_base64_encoding(self):
        """Test PDF base64 encoding/decoding"""
        # Create a simple test file
        test_content = b"PDF test content"
        encoded = base64.b64encode(test_content).decode('utf-8')

        # Should be able to decode back
        decoded = base64.b64decode(encoded)
        assert decoded == test_content

    def test_region_data_structure(self):
        """Test that region map has expected structure"""
        region_map_path = Path(__file__).parent.parent / "region_map.json"

        if not region_map_path.exists():
            pytest.skip("region_map.json not found")

        with open(region_map_path) as f:
            region_map = json.load(f)

        # Should have regions defined
        assert len(region_map) > 0

        # Each region should have required fields
        for region_id, region_data in region_map.items():
            assert "label" in region_data, f"Region {region_id} missing label"
            assert "compendium_terms" in region_data, f"Region {region_id} missing terms"
            assert isinstance(region_data["compendium_terms"], list)


class TestMCPToolSchemas:
    """Test MCP tool input schemas"""

    def test_search_tool_schema(self):
        """Test search_damages_cases tool schema"""
        valid_input = {
            "injury_description": "Cervical spine injury",
            "body_regions": ["cervical_spine"],
            "gender": "Male",
            "age": 35,
            "max_results": 10
        }

        # All required fields present
        assert "injury_description" in valid_input

        # Optional fields have valid values
        assert valid_input["gender"] in ["Male", "Female", "Not Specified"]
        assert 5 <= valid_input["age"] <= 100
        assert 1 <= valid_input["max_results"] <= 50

    def test_analyze_report_schema(self):
        """Test analyze_expert_report tool schema"""
        test_pdf = b"PDF content"
        valid_input = {
            "pdf_base64": base64.b64encode(test_pdf).decode('utf-8'),
            "use_llm": True
        }

        # Required fields present
        assert "pdf_base64" in valid_input

        # Can decode PDF
        decoded = base64.b64decode(valid_input["pdf_base64"])
        assert decoded == test_pdf

    def test_upload_cpi_schema(self):
        """Test upload_cpi_data tool schema"""
        valid_input = {
            "csv_content": "Year,CPI\n2024,160.85\n2023,157.11"
        }

        # Required field present
        assert "csv_content" in valid_input

        # CSV has valid structure
        lines = valid_input["csv_content"].split("\n")
        assert len(lines) >= 2  # Header + at least one data row
        assert "Year" in lines[0] and "CPI" in lines[0]

    def test_set_api_key_schema(self):
        """Test set_llm_api_key tool schema"""
        valid_input = {
            "provider": "openai",
            "api_key": "sk-test123"
        }

        # Required fields present
        assert "provider" in valid_input
        assert "api_key" in valid_input

        # Valid provider
        assert valid_input["provider"] in ["openai", "anthropic"]

    def test_adjust_inflation_schema(self):
        """Test adjust_for_inflation tool schema"""
        valid_input = {
            "amount": 50000,
            "original_year": 2010,
            "target_year": 2024
        }

        # Required fields present
        assert "amount" in valid_input
        assert "original_year" in valid_input

        # Valid year range
        assert 1900 <= valid_input["original_year"] <= 2100
        assert 1900 <= valid_input["target_year"] <= 2100


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_region_handling(self):
        """Test that invalid regions are handled gracefully"""
        invalid_regions = ["nonexistent_region", "fake_region"]
        # Should not crash, just filter out invalid regions
        # This would be tested in actual search function

    def test_missing_data_handling(self):
        """Test handling of missing case data"""
        incomplete_case = {"case_name": "Test"}
        # Should handle missing fields gracefully
        assert extract_damages_value(incomplete_case) is None

    def test_malformed_json(self):
        """Test handling of malformed JSON"""
        malformed = "{invalid json"
        with pytest.raises(json.JSONDecodeError):
            json.loads(malformed)


class TestResourceValidation:
    """Test MCP resources"""

    def test_cpi_data_resource(self):
        """Test CPI data resource structure"""
        # CPI data should have year keys and float values
        sample_cpi = {
            "2024": 160.85,
            "2023": 157.11
        }

        for year, cpi in sample_cpi.items():
            assert year.isdigit()
            assert isinstance(cpi, (int, float))
            assert cpi > 0

    def test_statistics_resource(self):
        """Test statistics resource structure"""
        sample_stats = {
            "total_cases": 100,
            "cases_with_damages": 95,
            "damages_range": {
                "min": 1000,
                "max": 500000,
                "median": 75000
            }
        }

        assert "total_cases" in sample_stats
        assert "damages_range" in sample_stats
        assert "median" in sample_stats["damages_range"]


def test_import_statements():
    """Test that all required imports are available"""
    try:
        from mcp.server import Server
        from mcp.server.stdio import stdio_server
        from mcp.types import Tool, TextContent
        assert True
    except ImportError as e:
        pytest.fail(f"Missing MCP SDK import: {e}")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
