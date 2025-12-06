#!/usr/bin/env python3
"""
Regenerate embeddings from damages_table_based.json with complete FLA data.

This script:
1. Loads damages_table_based.json (the authoritative source with all data)
2. Converts to dashboard format using data_transformer (preserving FLA claims)
3. Generates embeddings using sentence-transformers
4. Saves to data/damages_with_embeddings.json

This ensures all data (injuries, FLA claims, comments, etc.) is preserved.
"""

import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
from data_transformer import convert_to_dashboard_format

def main():
    print("=" * 70)
    print("REGENERATING DAMAGES COMPENDIUM WITH COMPLETE DATA")
    print("=" * 70)

    # Load source data
    source_file = "damages_table_based.json"
    print(f"\n📂 Loading source data from {source_file}...")

    with open(source_file, 'r', encoding='utf-8') as f:
        source_cases = json.load(f)

    print(f"   ✓ Loaded {len(source_cases):,} cases")

    # Check FLA coverage in source
    fla_cases = [c for c in source_cases if c.get('family_law_act_claims')]
    fla_count = sum(len(c.get('family_law_act_claims', [])) for c in fla_cases)
    print(f"   ✓ Source has {len(fla_cases)} cases with {fla_count} FLA claims")

    # Load embedding model
    print(f"\n🔄 Loading embedding model (all-mpnet-base-v2)...")
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
    print(f"   ✓ Model loaded")

    # Convert to dashboard format
    print(f"\n🔄 Converting to dashboard format...")
    print(f"   This preserves: injuries, FLA claims, comments, demographics")
    dashboard_cases = convert_to_dashboard_format(source_cases, model)
    print(f"   ✓ Converted {len(dashboard_cases):,} cases")

    # Verify FLA preservation
    fla_dashboard = [c for c in dashboard_cases
                     if c.get('extended_data', {}).get('family_law_act_claims')]
    fla_dashboard_count = sum(
        len(c.get('extended_data', {}).get('family_law_act_claims', []))
        for c in fla_dashboard
    )
    print(f"   ✓ Dashboard has {len(fla_dashboard)} cases with {fla_dashboard_count} FLA claims")

    if fla_dashboard_count != fla_count:
        print(f"   ⚠️  WARNING: FLA count mismatch! Source: {fla_count}, Dashboard: {fla_dashboard_count}")
    else:
        print(f"   ✅ FLA claims successfully preserved!")

    # Verify injury preservation
    injury_cases = [c for c in dashboard_cases
                    if c.get('extended_data', {}).get('injuries')]
    print(f"   ✓ Dashboard has {len(injury_cases)} cases with injuries")

    # Save to dashboard JSON
    output_path = Path("data/damages_with_embeddings.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Saving to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_cases, f, indent=2, ensure_ascii=False)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"   ✓ Saved {size_mb:.1f} MB")

    # Summary
    print(f"\n" + "=" * 70)
    print(f"✅ REGENERATION COMPLETE")
    print(f"=" * 70)
    print(f"\n📊 Summary:")
    print(f"   • Total cases: {len(dashboard_cases):,}")
    print(f"   • Cases with injuries: {len(injury_cases):,}")
    print(f"   • Cases with FLA claims: {len(fla_dashboard):,}")
    print(f"   • Total FLA relationships: {fla_dashboard_count:,}")
    print(f"\n📁 Output: {output_path}")
    print(f"\n💡 Next steps:")
    print(f"   1. Run generate_embeddings.py to create injury embeddings")
    print(f"   2. Restart Streamlit app to load new data")
    print()

if __name__ == "__main__":
    main()
