"""
Inflation Adjustment Utility
Adjusts historical damage awards to current dollars using Canadian CPI data
"""

from datetime import datetime
from typing import Optional

# Canadian Consumer Price Index (CPI) data
# Source: Statistics Canada, Annual average CPI (2002=100)
# Updated to 2024
CANADIAN_CPI_DATA = {
    2000: 95.4,
    2001: 97.8,
    2002: 100.0,
    2003: 102.8,
    2004: 104.7,
    2005: 107.0,
    2006: 109.1,
    2007: 111.5,
    2008: 114.1,
    2009: 114.4,
    2010: 116.5,
    2011: 119.9,
    2012: 121.7,
    2013: 122.8,
    2014: 125.2,
    2015: 126.6,
    2016: 128.4,
    2017: 130.4,
    2018: 133.4,
    2019: 136.0,
    2020: 137.0,
    2021: 141.6,
    2022: 151.2,
    2023: 156.0,
    2024: 160.5,  # Estimated based on trend
    2025: 164.0,  # Projected
}

# Default reference year for adjustments
DEFAULT_REFERENCE_YEAR = 2024


def get_cpi_for_year(year: int) -> Optional[float]:
    """
    Get CPI value for a specific year

    Args:
        year: The year to look up

    Returns:
        CPI value or None if year not in data
    """
    return CANADIAN_CPI_DATA.get(year)


def adjust_for_inflation(
    amount: float,
    original_year: int,
    target_year: int = DEFAULT_REFERENCE_YEAR
) -> Optional[float]:
    """
    Adjust a dollar amount for inflation

    Args:
        amount: Original dollar amount
        original_year: Year the amount is from
        target_year: Year to adjust to (default: current year)

    Returns:
        Inflation-adjusted amount or None if CPI data unavailable
    """
    original_cpi = get_cpi_for_year(original_year)
    target_cpi = get_cpi_for_year(target_year)

    if original_cpi is None or target_cpi is None:
        return None

    # Adjustment formula: amount * (target_cpi / original_cpi)
    adjusted = amount * (target_cpi / original_cpi)

    return round(adjusted, 2)


def get_inflation_rate(start_year: int, end_year: int) -> Optional[float]:
    """
    Calculate inflation rate between two years

    Args:
        start_year: Starting year
        end_year: Ending year

    Returns:
        Inflation rate as percentage or None if data unavailable
    """
    start_cpi = get_cpi_for_year(start_year)
    end_cpi = get_cpi_for_year(end_year)

    if start_cpi is None or end_cpi is None:
        return None

    rate = ((end_cpi - start_cpi) / start_cpi) * 100

    return round(rate, 2)


def format_inflation_info(
    original_amount: float,
    original_year: int,
    adjusted_amount: float,
    target_year: int = DEFAULT_REFERENCE_YEAR
) -> str:
    """
    Format inflation adjustment information as readable text

    Args:
        original_amount: Original award amount
        original_year: Year of original award
        adjusted_amount: Inflation-adjusted amount
        target_year: Target year for adjustment

    Returns:
        Formatted string describing the adjustment
    """
    inflation_rate = get_inflation_rate(original_year, target_year)

    if inflation_rate is None:
        return f"${original_amount:,.0f} ({original_year})"

    return (
        f"${original_amount:,.0f} ({original_year}) → "
        f"${adjusted_amount:,.0f} ({target_year}) "
        f"[+{inflation_rate:.1f}% inflation]"
    )


def get_available_years() -> list:
    """Get list of years with available CPI data"""
    return sorted(CANADIAN_CPI_DATA.keys())


def get_earliest_year() -> int:
    """Get earliest year with CPI data"""
    return min(CANADIAN_CPI_DATA.keys())


def get_latest_year() -> int:
    """Get latest year with CPI data"""
    return max(CANADIAN_CPI_DATA.keys())


# Example usage
if __name__ == "__main__":
    # Test inflation adjustment
    test_cases = [
        (75000, 2010),
        (95000, 2015),
        (125000, 2020),
        (85000, 2023),
    ]

    print("Inflation Adjustment Examples")
    print("=" * 60)

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
