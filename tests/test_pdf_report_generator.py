"""
Tests for PDF Report Generator
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_report_generator import generate_damages_report


def test_generate_report():
    """Test PDF report generation with sample data"""
    # Sample data for testing
    sample_results = [
        (
            {
                'case_name': 'Smith v. Jones',
                'year': 2023,
                'region': 'NECK',
                'court': 'ONSC',
                'damages': 75000,
                'summary_text': 'C5-C6 disc herniation with chronic radicular pain...'
            },
            0.85,
            0.92
        )
    ]

    output = "test_report.pdf"

    generate_damages_report(
        output,
        selected_regions=["cervical_spine", "shoulder_right"],
        region_labels={
            "cervical_spine": "Cervical Spine (C1-C7)",
            "shoulder_right": "Right Glenohumeral / AC Complex"
        },
        injury_description="C5-C6 disc herniation with chronic pain and radiculopathy",
        results=sample_results,
        damages_values=[75000, 80000, 65000],
        gender="Male",
        age=45,
        max_cases=5
    )

    print(f"✅ Report generated: {output}")

    # Clean up
    if Path(output).exists():
        Path(output).unlink()
        print(f"✅ Test file cleaned up: {output}")


if __name__ == "__main__":
    test_generate_report()
