"""
Inflation Adjustment Utility
Adjusts historical damage awards to current dollars using Bank of Canada CPI data
"""

from datetime import datetime
from typing import Optional, Dict
import csv
from pathlib import Path
import re
import requests
from io import StringIO

# Default reference year for adjustments
DEFAULT_REFERENCE_YEAR = 2024

# Path to Bank of Canada CPI CSV file
BOC_CPI_CSV = Path(__file__).parent / "data" / "boc_cpi.csv"

# Fallback CPI data (if CSV not available)
FALLBACK_CPI_DATA = {
    2000: 95.4, 2001: 97.8, 2002: 100.0, 2003: 102.8, 2004: 104.7,
    2005: 107.0, 2006: 109.1, 2007: 111.5, 2008: 114.1, 2009: 114.4,
    2010: 116.5, 2011: 119.9, 2012: 121.7, 2013: 122.8, 2014: 125.2,
    2015: 126.6, 2016: 128.4, 2017: 130.4, 2018: 133.4, 2019: 136.0,
    2020: 137.0, 2021: 141.6, 2022: 151.2, 2023: 156.0, 2024: 160.5,
}

# Cache for loaded CPI data
_cpi_cache: Optional[Dict[int, float]] = None


def load_boc_cpi_data(csv_path: Path = BOC_CPI_CSV) -> Dict[int, float]:
    """
    Load CPI data from Bank of Canada CSV file

    CSV Format:
    CANSIM,v41690973,v41690914,...
    2025-10,165.3,165.2,...
    2025-09,164.9,165.0,...

    Args:
        csv_path: Path to the Bank of Canada CPI CSV file

    Returns:
        Dictionary mapping year -> average annual CPI
    """
    if not csv_path.exists():
        return None

    try:
        monthly_data = {}

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header

            for row in reader:
                if not row or len(row) < 2:
                    continue

                # Parse date (format: YYYY-MM)
                date_str = row[0].strip()
                if not re.match(r'^\d{4}-\d{2}$', date_str):
                    continue

                year, month = date_str.split('-')
                year = int(year)

                # Get CPI value (second column - v41690973 "All-items")
                try:
                    cpi_str = row[1].strip().rstrip('R').strip()  # Remove 'R' revision indicator
                    cpi = float(cpi_str)
                except (ValueError, IndexError):
                    continue

                # Store monthly data
                if year not in monthly_data:
                    monthly_data[year] = []
                monthly_data[year].append(cpi)

        # Calculate annual averages
        annual_data = {}
        for year, values in monthly_data.items():
            if values:
                annual_data[year] = sum(values) / len(values)

        return annual_data

    except Exception as e:
        print(f"Warning: Failed to load Bank of Canada CPI data: {e}")
        return None


def download_boc_cpi_data(
    url: str = "https://www.bankofcanada.ca/valet/observations/group/CPI_MONTHLY/csv",
    save_path: Path = BOC_CPI_CSV,
    timeout: int = 30
) -> Dict[int, float]:
    """
    Download CPI data directly from Bank of Canada website

    NOTE: The Bank of Canada Valet API may require authentication or may block
    automated requests. If this function fails, you can:
    1. Manually download the CSV from the Bank of Canada website
    2. Save it to data/boc_cpi.csv
    3. The system will use the local file automatically

    Args:
        url: Bank of Canada Valet API URL for CPI data
        save_path: Path to save the downloaded CSV file
        timeout: Request timeout in seconds

    Returns:
        Dictionary mapping year -> average annual CPI, or None on failure
    """
    try:
        print(f"Downloading CPI data from Bank of Canada...")

        # Set headers with honest application identifier
        headers = {
            'User-Agent': 'Ontario-Damages-Compendium/1.0 (+https://github.com/yourrepo/ON_damages_compendium)',
            'Accept': 'text/csv,application/csv,text/plain,*/*'
        }

        # Download the CSV
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()  # Raise exception for HTTP errors

        # Ensure data directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)

        # Save the raw CSV
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        print(f"✓ CPI data downloaded and saved to {save_path}")

        # Parse and return the data
        return load_boc_cpi_data(save_path)

    except requests.exceptions.Timeout:
        print(f"Warning: Request timed out after {timeout} seconds")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Warning: Could not connect to Bank of Canada website")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"Warning: HTTP error downloading CPI data: {e}")
        return None
    except Exception as e:
        print(f"Warning: Failed to download Bank of Canada CPI data: {e}")
        return None


def get_cpi_data(auto_download: bool = False) -> Dict[int, float]:
    """
    Get CPI data, using cached version or loading from CSV

    Args:
        auto_download: If True and local CSV doesn't exist, download from Bank of Canada

    Returns:
        Dictionary mapping year -> CPI value
    """
    global _cpi_cache

    if _cpi_cache is not None:
        return _cpi_cache

    # Try to load from Bank of Canada CSV
    boc_data = load_boc_cpi_data()

    # If no local data and auto_download enabled, try downloading
    if (boc_data is None or len(boc_data) < 10) and auto_download:
        boc_data = download_boc_cpi_data()

    if boc_data and len(boc_data) > 10:  # Ensure we got reasonable data
        _cpi_cache = boc_data
        return _cpi_cache

    # Fallback to hardcoded data
    _cpi_cache = FALLBACK_CPI_DATA.copy()
    return _cpi_cache


def reload_cpi_data(download_fresh: bool = False):
    """
    Force reload of CPI data from CSV (useful after updating the file)

    Args:
        download_fresh: If True, download fresh data from Bank of Canada before reloading

    Returns:
        Dictionary of CPI data
    """
    global _cpi_cache
    _cpi_cache = None

    if download_fresh:
        download_boc_cpi_data()

    return get_cpi_data()


def update_cpi_data():
    """
    Convenience function to download and update CPI data from Bank of Canada

    Returns:
        Dictionary of CPI data if successful, None otherwise
    """
    return download_boc_cpi_data()


def get_cpi_for_year(year: int) -> Optional[float]:
    """
    Get CPI value for a specific year

    Args:
        year: The year to look up

    Returns:
        CPI value or None if year not in data
    """
    cpi_data = get_cpi_data()
    return cpi_data.get(year)


def adjust_for_inflation(
    amount: float,
    original_year: int,
    target_year: int = DEFAULT_REFERENCE_YEAR
) -> Optional[float]:
    """
    Adjust a dollar amount for inflation using Bank of Canada CPI data

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
    cpi_data = get_cpi_data()
    return sorted(cpi_data.keys())


def get_earliest_year() -> int:
    """Get earliest year with CPI data"""
    years = get_available_years()
    return min(years) if years else 2000


def get_latest_year() -> int:
    """Get latest year with CPI data"""
    years = get_available_years()
    return max(years) if years else DEFAULT_REFERENCE_YEAR


def get_data_source() -> str:
    """Get information about the CPI data source being used"""
    cpi_data = get_cpi_data()

    if BOC_CPI_CSV.exists():
        num_years = len(cpi_data)
        year_range = f"{get_earliest_year()}-{get_latest_year()}"
        return f"Bank of Canada CSV ({num_years} years: {year_range})"
    else:
        num_years = len(cpi_data)
        year_range = f"{get_earliest_year()}-{get_latest_year()}"
        return f"Fallback data ({num_years} years: {year_range})"


# Example usage and testing
if __name__ == "__main__":
    print("=" * 70)
    print("Bank of Canada CPI Inflation Adjuster")
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
