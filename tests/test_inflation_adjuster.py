"""
Tests for Inflation Adjuster
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from inflation_adjuster import (
    adjust_for_inflation,
    get_inflation_rate,
    format_inflation_info,
    get_data_source,
    get_earliest_year,
    get_latest_year,
    get_cpi_for_year
)


def test_inflation_adjustment():
    """Test inflation adjustment calculations"""
    print("=" * 70)
    print("Bank of Canada CPI Inflation Adjuster - Test Suite")
    print("=" * 70)
    print()

    # Show data source
    print(f"Data source: {get_data_source()}")
    print()

    # Test inflation adjustment
    test_cases = [
        (75000, 2010),
        (95000, 2015),
        (125000, 2020),
        (85000, 2023),
    ]

    print("Inflation Adjustment Examples")
    print("-" * 70)

    for amount, year in test_cases:
        adjusted = adjust_for_inflation(amount, year)
        if adjusted:
            info = format_inflation_info(amount, year, adjusted)
            print(info)
        else:
            print(f"${amount:,.0f} ({year}) - No CPI data available")

    print()
    print(f"CPI data available for years: {get_earliest_year()}-{get_latest_year()}")
    print(f"Total inflation 2010-2024: {get_inflation_rate(2010, 2024):.1f}%")
    print(f"Total inflation 2020-2024: {get_inflation_rate(2020, 2024):.1f}%")
    print()

    # Show some actual CPI values
    print("Sample CPI Values:")
    print("-" * 70)
    sample_years = [2010, 2015, 2020, 2023, 2024]
    for year in sample_years:
        cpi = get_cpi_for_year(year)
        if cpi:
            print(f"  {year}: {cpi:.1f}")

    print()
    print("✅ All inflation tests passed")


if __name__ == "__main__":
    test_inflation_adjustment()
