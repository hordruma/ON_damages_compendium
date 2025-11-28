"""
Inflation Adjustment Utility
Adjusts historical damage awards to current dollars using Bank of Canada CPI data
"""

from datetime import datetime
from typing import Optional, Dict, List
import csv
from pathlib import Path
import re
import requests
from io import StringIO

# Default reference year for adjustments
DEFAULT_REFERENCE_YEAR = 2025

# Path to Bank of Canada CPI CSV file
BOC_CPI_CSV = Path(__file__).parent / "data" / "boc_cpi.csv"

# Fallback CPI data (if CSV not available)
# Comprehensive Bank of Canada CPI data (1914-2025)
# Annual averages calculated from monthly BOC Total CPI values
FALLBACK_CPI_DATA = {
    1914: 6.01, 1915: 6.13, 1916: 6.68, 1917: 7.88, 1918: 8.92, 1919: 9.77, 1920: 11.36, 1921: 9.98, 1922: 9.2, 1923: 9.2,
    1924: 9.02, 1925: 9.13, 1926: 9.2, 1927: 9.06, 1928: 9.13, 1929: 9.22, 1930: 9.13, 1931: 8.23, 1932: 7.45, 1933: 7.13,
    1934: 7.22, 1935: 7.25, 1936: 7.4, 1937: 7.67, 1938: 7.71, 1939: 7.65, 1940: 7.97, 1941: 8.45, 1942: 8.84, 1943: 9.03,
    1944: 9.09, 1945: 9.15, 1946: 9.43, 1947: 10.28, 1948: 11.75, 1949: 12.16, 1950: 12.48, 1951: 13.8, 1952: 14.16, 1953: 14.02,
    1954: 14.11, 1955: 14.13, 1956: 14.32, 1957: 14.8, 1958: 15.15, 1959: 15.33, 1960: 15.54, 1961: 15.7, 1962: 15.87, 1963: 16.12,
    1964: 16.43, 1965: 16.82, 1966: 17.46, 1967: 18.08, 1968: 18.82, 1969: 19.68, 1970: 20.33, 1971: 20.88, 1972: 21.93, 1973: 23.57,
    1974: 26.16, 1975: 28.95, 1976: 31.13, 1977: 33.62, 1978: 36.63, 1979: 39.98, 1980: 44.03, 1981: 49.52, 1982: 54.86, 1983: 58.08,
    1984: 60.57, 1985: 62.98, 1986: 65.62, 1987: 68.48, 1988: 71.23, 1989: 74.78, 1990: 78.36, 1991: 82.77, 1992: 84.0, 1993: 85.57,
    1994: 85.71, 1995: 87.55, 1996: 88.92, 1997: 90.37, 1998: 91.27, 1999: 92.85, 2000: 95.38, 2001: 97.78, 2002: 99.99, 2003: 102.75,
    2004: 104.66, 2005: 106.98, 2006: 109.12, 2007: 111.45, 2008: 114.09, 2009: 114.43, 2010: 116.47, 2011: 119.86, 2012: 121.68, 2013: 122.82,
    2014: 125.16, 2015: 126.57, 2016: 128.37, 2017: 130.42, 2018: 133.38, 2019: 135.98, 2020: 136.96, 2021: 141.61, 2022: 151.24, 2023: 157.11,
    2024: 160.85, 2025: 163.98,
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
    url: str = "https://www.bankofcanada.ca/valet/observations/V41690973/csv",
    save_path: Path = BOC_CPI_CSV,
    timeout: int = 30
) -> Dict[int, float]:
    """
    Download CPI data directly from Bank of Canada website

    NOTE: The Bank of Canada Valet API may block automated requests with 403 errors.
    To manually download CPI data:

    1. Visit the Bank of Canada Inflation Calculator page:
       https://www.bankofcanada.ca/rates/related/inflation-calculator/
    2. Look for the link to download the CPI CSV data on that page
    3. Download the CSV file
    4. Save it as: data/boc_cpi.csv
    5. The system will automatically use the local file

    Expected CSV format:
        CANSIM,v41690973
        2025-10,165.30000000
        2025-09,164.90000000
        ...

    Args:
        url: Bank of Canada Valet API URL for CPI data (series V41690973)
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


def reload_cpi_data(download_fresh: bool = False) -> Dict[int, float]:
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


def update_cpi_data() -> Optional[Dict[int, float]]:
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


def get_available_years() -> List[int]:
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
