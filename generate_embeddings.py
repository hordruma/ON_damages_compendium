#!/usr/bin/env python3
"""
Generate injury-focused embeddings for the Ontario Damages Compendium.

This script creates embeddings from injuries and sequelae only (not full case text),
which are used for semantic search in the Streamlit app.

Output files:
- data/compendium_inj.json: Cases with search_text and injury embeddings
- data/embeddings_inj.npy: Embedding matrix for fast similarity search
- data/ids.json: Case IDs for mapping embeddings to cases
"""

from sentence_transformers import SentenceTransformer
import numpy as np
import json
import re
from pathlib import Path
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
    # Load the dashboard cases with existing data
    DASHBOARD_JSON = "data/damages_with_embeddings.json"

    print(f"📂 Loading cases from {DASHBOARD_JSON}...")
    with open(DASHBOARD_JSON, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"   Loaded {len(cases):,} cases")

    # Load embedding model - upgraded to MPNet for better semantic understanding
    print("🔄 Loading sentence-transformers model (all-mpnet-base-v2)...")
    print("   This model is significantly better at understanding medical terminology")
    emb_model = SentenceTransformer("all-mpnet-base-v2")
    print("   Model loaded successfully")

    # Build injury-focused search_text and embeddings
    ids = []
    inj_embs = []
    out_cases = []

    print("🔄 Generating injury-focused embeddings...")
    cases_without_injuries = 0
    cases_with_extracted_injuries = 0

    for c in tqdm(cases, desc="Processing cases"):
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
        emb = emb_model.encode(search_text).astype("float32")
        c['inj_emb'] = emb.tolist()

        ids.append(c['id'])
        inj_embs.append(emb)
        out_cases.append(c)

    # Save artifacts
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    print("\n💾 Saving artifacts...")

    # Save cases with search_text and embeddings
    with open(data_dir / "compendium_inj.json", "w", encoding="utf-8") as f:
        json.dump(out_cases, f, ensure_ascii=False, indent=2)

    # Save embedding matrix for fast load
    emb_matrix = np.vstack(inj_embs)
    np.save(data_dir / "embeddings_inj.npy", emb_matrix)

    # Save case IDs for mapping
    with open(data_dir / "ids.json", "w", encoding="utf-8") as f:
        json.dump(ids, f)

    # Print summary
    print(f"\n✅ Created {len(out_cases):,} injury-focused embeddings")
    print(f"\n📊 Data Quality Summary:")
    print(f"   - Cases without injury lists: {cases_without_injuries} ({cases_without_injuries/len(out_cases)*100:.1f}%)")
    print(f"   - Cases with extracted injuries from comments: {cases_with_extracted_injuries}")
    print(f"   - Remaining cases without injuries: {cases_without_injuries - cases_with_extracted_injuries}")
    print(f"\n📁 Output files:")
    print(f"   - compendium_inj.json: {(data_dir / 'compendium_inj.json').stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   - embeddings_inj.npy: {(data_dir / 'embeddings_inj.npy').stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   - ids.json: {(data_dir / 'ids.json').stat().st_size / 1024:.1f} KB")
    print(f"\n✅ Done! The Streamlit app can now use these embeddings for search.")

if __name__ == "__main__":
    main()
