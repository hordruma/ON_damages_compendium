#!/usr/bin/env python3
"""
Build all embeddings for the Ontario Damages Compendium.

This script combines the full workflow:
1. Loads damages_table_based.json (authoritative source)
2. Converts to dashboard format with full case embeddings
3. Saves to data/damages_with_embeddings.json
4. Generates injury-focused embeddings for semantic search
5. Saves to data/compendium_inj.json, embeddings_inj.npy, ids.json

One script to rule them all!
"""

import json
import re
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from data_transformer import convert_to_dashboard_format
from tqdm import tqdm


def extract_injuries_from_comments(comments: str) -> list:
    """
    Extract injury-related terms from comments text as a fallback.

    This helps cases with empty injury arrays by extracting injury
    descriptions from narrative comments.

    Args:
        comments: Comment text from case

    Returns:
        List of extracted injury terms
    """
    if not comments:
        return []

    # Common injury-related patterns
    injury_patterns = [
        r'\b(?:suffered?|sustained?|experienced?|diagnosed with)\s+([^.;,]+(?:injury|injuries|fracture|damage|trauma|pain|syndrome|disorder|impairment|loss|tear|rupture|herniation|sprain|strain|contusion|hemorrhage|bleeding|concussion))',
        r'\b(brain (?:damage|injury|trauma|hemorrhage))',
        r'\b(spinal cord (?:injury|damage))',
        r'\b(traumatic brain injury|tbi)',
        r'\b(post[- ]traumatic stress|ptsd)',
        r'\b(complex regional pain syndrome|crps)',
        r'\b(diffuse axonal injury)',
        r'\b(herniated (?:disc|disk))',
        r'\b(fractured? \w+)',
        r'\b(torn \w+)',
        r'\b(ruptured \w+)',
        r'\b(\w+ fracture)',
        r'\b(whiplash)',
        r'\b(chronic pain)',
        r'\b(paralysis|paraplegia|quadriplegia)',
        r'\b(amputation)',
        r'\b(vision loss|blindness|hearing loss)',
        r'\b(internal (?:injuries|bleeding))',
    ]

    extracted = []
    comments_lower = comments.lower()

    for pattern in injury_patterns:
        matches = re.finditer(pattern, comments_lower, re.IGNORECASE)
        for match in matches:
            injury = match.group(1) if match.lastindex else match.group(0)
            injury = injury.strip()
            if injury and len(injury) > 3:
                extracted.append(injury)

    # Remove duplicates while preserving order
    seen = set()
    unique_injuries = []
    for inj in extracted:
        inj_lower = inj.lower()
        if inj_lower not in seen:
            seen.add(inj_lower)
            unique_injuries.append(inj)

    return unique_injuries[:10]  # Limit to top 10 extracted terms


def main():
    print("=" * 70)
    print("BUILDING ALL EMBEDDINGS FOR DAMAGES COMPENDIUM")
    print("=" * 70)

    # STEP 1: Load source data
    source_file = "damages_table_based.json"
    print(f"\n📂 Step 1: Loading source data from {source_file}...")

    with open(source_file, 'r', encoding='utf-8') as f:
        source_cases = json.load(f)

    print(f"   ✓ Loaded {len(source_cases):,} cases")

    # Check FLA coverage in source
    fla_cases = [c for c in source_cases if c.get('family_law_act_claims')]
    fla_count = sum(len(c.get('family_law_act_claims', [])) for c in fla_cases)
    print(f"   ✓ Source has {len(fla_cases)} cases with {fla_count} FLA claims")

    # STEP 2: Load embedding model (only once!)
    print(f"\n🔄 Step 2: Loading embedding model (all-mpnet-base-v2)...")
    print(f"   This model provides excellent medical terminology understanding")
    print(f"   (First run will download ~400MB model)")
    model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2", device='cpu')
    print(f"   ✓ Model loaded")

    # STEP 3: Convert to dashboard format
    print(f"\n🔄 Step 3: Converting to dashboard format with full case embeddings...")
    print(f"   Preserves: injuries, FLA claims, comments, demographics")
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

    # STEP 4: Save dashboard JSON
    output_path = Path("data/damages_with_embeddings.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n💾 Step 4: Saving dashboard data to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_cases, f, indent=2, ensure_ascii=False)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"   ✓ Saved {size_mb:.1f} MB")

    # STEP 5: Generate injury-focused embeddings
    print(f"\n🔄 Step 5: Generating injury-focused embeddings for semantic search...")

    ids = []
    inj_embs = []
    out_cases = []
    cases_without_injuries = 0
    cases_with_extracted_injuries = 0

    for c in tqdm(dashboard_cases, desc="Processing cases"):
        # Build search_text from injuries only
        ext = c.get("extended_data", {}) or {}
        injuries = ext.get("injuries") or []

        # Fallback: Extract injuries from comments if empty
        if not injuries:
            cases_without_injuries += 1
            comments = ext.get("comments") or c.get("comments", "")
            extracted = extract_injuries_from_comments(comments)
            if extracted:
                injuries = extracted
                cases_with_extracted_injuries += 1

        # Join injuries into search text
        search_text = "; ".join(injuries) if injuries else ""

        # Final fallback if no injuries found
        if not search_text:
            case_name = c.get("case_name", "")
            search_text = case_name if case_name else "case"

        c['search_text'] = search_text

        # Compute embedding
        emb = model.encode(search_text).astype("float32")
        c['inj_emb'] = emb.tolist()

        ids.append(c['id'])
        inj_embs.append(emb)
        out_cases.append(c)

    # STEP 6: Save injury embeddings
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    print("\n💾 Step 6: Saving injury-focused embeddings...")

    # Save cases with search_text and embeddings
    with open(data_dir / "compendium_inj.json", "w", encoding="utf-8") as f:
        json.dump(out_cases, f, ensure_ascii=False, indent=2)

    # Save embedding matrix for fast load
    emb_matrix = np.vstack(inj_embs)
    np.save(data_dir / "embeddings_inj.npy", emb_matrix)

    # Save case IDs for mapping
    with open(data_dir / "ids.json", "w", encoding="utf-8") as f:
        json.dump(ids, f)

    print(f"   ✓ compendium_inj.json: {(data_dir / 'compendium_inj.json').stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   ✓ embeddings_inj.npy: {(data_dir / 'embeddings_inj.npy').stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   ✓ ids.json: {(data_dir / 'ids.json').stat().st_size / 1024:.1f} KB")

    # FINAL SUMMARY
    print(f"\n" + "=" * 70)
    print(f"✅ ALL EMBEDDINGS BUILT SUCCESSFULLY")
    print(f"=" * 70)
    print(f"\n📊 Summary:")
    print(f"   • Total cases: {len(dashboard_cases):,}")
    print(f"   • Cases with injuries: {len(injury_cases):,}")
    print(f"   • Cases with FLA claims: {len(fla_dashboard):,}")
    print(f"   • Total FLA relationships: {fla_dashboard_count:,}")
    print(f"\n📊 Injury Extraction:")
    print(f"   • Cases without injury lists: {cases_without_injuries} ({cases_without_injuries/len(out_cases)*100:.1f}%)")
    print(f"   • Extracted from comments: {cases_with_extracted_injuries}")
    print(f"   • Still missing: {cases_without_injuries - cases_with_extracted_injuries}")
    print(f"\n📁 Output Files:")
    print(f"   • data/damages_with_embeddings.json (dashboard format)")
    print(f"   • data/compendium_inj.json (injury-focused)")
    print(f"   • data/embeddings_inj.npy (embedding matrix)")
    print(f"   • data/ids.json (case ID mapping)")
    print(f"\n💡 Next step: Restart Streamlit app to load new data")
    print(f"   streamlit run streamlit_app.py")
    print()


if __name__ == "__main__":
    main()
