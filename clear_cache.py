#!/usr/bin/env python3
"""
Clear Streamlit cache to fix data format compatibility issues.

Run this script after updating the data file to ensure the app loads
the new data format correctly without conflicts from cached old data.
"""

import shutil
from pathlib import Path

def clear_streamlit_cache():
    """Clear Streamlit cache directories"""
    cache_dirs = [
        Path.home() / '.streamlit' / 'cache',
        Path('.streamlit'),
        Path('__pycache__'),
        Path('.cache'),
    ]

    cleared = []

    for cache_dir in cache_dirs:
        if cache_dir.exists():
            try:
                if cache_dir.is_dir():
                    shutil.rmtree(cache_dir)
                    cleared.append(str(cache_dir))
                    print(f"✓ Cleared: {cache_dir}")
            except Exception as e:
                print(f"⚠️  Could not clear {cache_dir}: {e}")

    # Also clear Python cache files
    for pycache in Path('.').rglob('__pycache__'):
        try:
            shutil.rmtree(pycache)
            cleared.append(str(pycache))
            print(f"✓ Cleared: {pycache}")
        except Exception as e:
            print(f"⚠️  Could not clear {pycache}: {e}")

    if cleared:
        print(f"\n✅ Cleared {len(cleared)} cache location(s)")
        print("\n💡 Now restart the Streamlit app:")
        print("   streamlit run streamlit_app.py")
    else:
        print("ℹ️  No cache found to clear")

if __name__ == '__main__':
    print("Clearing Streamlit cache...\n")
    clear_streamlit_cache()
