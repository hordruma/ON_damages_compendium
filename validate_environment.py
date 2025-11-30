#!/usr/bin/env python3
"""
Environment Validation Script
Checks that all dependencies and data files are properly configured
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def check_python_version() -> bool:
    """Check Python version is 3.9+"""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python version {version.major}.{version.minor}.{version.micro} (3.9+ required)")
        return False

def check_dependencies() -> Tuple[List[str], List[str]]:
    """Check required Python dependencies"""
    required_packages = [
        'streamlit',
        'pandas',
        'numpy',
        'sentence_transformers',
        'sklearn',
        'torch',
        'pdfplumber',
        'reportlab',
        'plotly',
        'anthropic',
        'openai',
        'dotenv'
    ]

    installed = []
    missing = []

    for package in required_packages:
        try:
            # Try alternative names
            if package == 'sklearn':
                __import__('sklearn')
            elif package == 'dotenv':
                __import__('dotenv')
            else:
                __import__(package)
            installed.append(package)
            print_success(f"{package}")
        except ImportError:
            missing.append(package)
            if package in ['anthropic', 'openai']:
                print_warning(f"{package} (optional - for LLM features)")
            else:
                print_error(f"{package} (required)")

    return installed, missing

def check_data_files() -> Tuple[List[str], List[str]]:
    """Check required data files exist"""
    base_path = Path(__file__).parent

    required_files = {
        'region_map.json': 'Required - Region mapping data',
        'data/damages_with_embeddings.json': 'Required - Case database (run 01_extract_and_embed.ipynb to generate)',
        'assets/body_front.svg': 'Optional - Front body diagram',
        'assets/body_back.svg': 'Optional - Back body diagram',
        'data/boc_cpi.csv': 'Optional - CPI inflation data (uses fallback if missing)'
    }

    found = []
    missing = []

    for file_path, description in required_files.items():
        full_path = base_path / file_path
        if full_path.exists():
            size = full_path.stat().st_size
            size_str = f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB"
            print_success(f"{file_path} ({size_str})")
            found.append(file_path)
        else:
            if 'Optional' in description:
                print_warning(f"{file_path} - {description}")
            else:
                print_error(f"{file_path} - {description}")
            missing.append(file_path)

    return found, missing

def check_environment_variables() -> Tuple[List[str], List[str]]:
    """Check optional environment variables"""
    optional_vars = {
        'OPENAI_API_KEY': 'OpenAI API key for LLM-based report analysis',
        'ANTHROPIC_API_KEY': 'Anthropic API key for LLM-based report analysis'
    }

    configured = []
    unconfigured = []

    # Check for .env file
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        print_success(f".env file found")
        # Load .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            print_warning("python-dotenv not installed, cannot load .env file")

    for var, description in optional_vars.items():
        if os.getenv(var):
            masked_value = os.getenv(var)[:8] + '...'
            print_success(f"{var} = {masked_value}")
            configured.append(var)
        else:
            print_info(f"{var} not set - {description}")
            unconfigured.append(var)

    return configured, unconfigured

def check_streamlit_app() -> bool:
    """Check Streamlit app can be imported"""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import streamlit_app
        print_success("Streamlit app module can be imported")
        return True
    except ImportError as e:
        print_error(f"Cannot import Streamlit app: {e}")
        return False
    except Exception as e:
        print_warning(f"Streamlit app import succeeded but may fail at runtime: {e}")
        return True

def print_summary(
    python_ok: bool,
    installed_packages: List[str],
    missing_packages: List[str],
    found_files: List[str],
    missing_files: List[str],
    configured_vars: List[str],
    streamlit_ok: bool
):
    """Print validation summary"""
    print_header("VALIDATION SUMMARY")

    # Calculate status
    critical_missing = [p for p in missing_packages if p not in ['anthropic', 'openai']]
    critical_files_missing = [f for f in missing_files if 'Optional' not in f and 'damages_with_embeddings' in f]

    if python_ok and not critical_missing and not critical_files_missing:
        print_success(f"{Colors.BOLD}✓ Environment validation PASSED{Colors.END}")
        print()
        print("Your environment is ready!")
        print()
        print("Next steps:")
        print("  • Run Streamlit app: streamlit run streamlit_app.py")
        print("  • Upload expert reports for analysis")
        print("  • Search for comparable cases")
    else:
        print_error(f"{Colors.BOLD}✗ Environment validation FAILED{Colors.END}")
        print()
        print("Issues found:")

        if not python_ok:
            print_error("  • Python 3.9+ required")

        if critical_missing:
            print_error(f"  • Missing critical packages: {', '.join(critical_missing)}")
            print()
            print("Install missing packages:")
            print(f"  pip install -r requirements.txt")

        if critical_files_missing:
            print_error("  • Missing case data file")
            print()
            print("Generate data file:")
            print("  1. Place 2024damagescompendium.pdf in project root")
            print("  2. Run: jupyter notebook 01_extract_and_embed.ipynb")
            print("  3. Execute all cells to generate embeddings")

    # Optional features
    print()
    print(f"{Colors.BOLD}Optional Features:{Colors.END}")

    if not configured_vars:
        print_warning("  • No LLM API keys configured (regex-based report analysis only)")
        print_info("    Configure API keys in .env file for AI-powered analysis")

    if missing_packages and 'mcp' in missing_packages:
        print_warning("  • MCP SDK not installed (MCP server unavailable)")
        print_info("    Install: pip install mcp>=0.9.0")

    if 'assets/body_front.svg' in missing_files:
        print_warning("  • Body diagram SVGs missing (visual reference unavailable)")

    print()

def main():
    """Run all validation checks"""
    print()
    print(f"{Colors.BOLD}Ontario Damages Compendium - Environment Validation{Colors.END}")

    # Python version
    print_header("Python Version")
    python_ok = check_python_version()

    # Dependencies
    print_header("Python Dependencies")
    installed, missing = check_dependencies()

    # Data files
    print_header("Data Files")
    found_files, missing_files = check_data_files()

    # Environment variables
    print_header("Environment Variables")
    configured_vars, unconfigured_vars = check_environment_variables()

    # Streamlit app
    print_header("Streamlit App")
    streamlit_ok = check_streamlit_app()

    # Summary
    print_summary(
        python_ok,
        installed,
        missing,
        found_files,
        missing_files,
        configured_vars,
        streamlit_ok
    )

    # Exit code
    critical_missing = [p for p in missing if p not in ['anthropic', 'openai']]
    critical_files_missing = [f for f in missing_files if 'Optional' not in f and 'damages_with_embeddings' in f]

    if not python_ok or critical_missing or critical_files_missing:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
