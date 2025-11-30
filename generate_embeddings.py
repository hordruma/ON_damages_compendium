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
from pathlib import Path
from tqdm import tqdm

def main():
    # Load the dashboard cases with existing data
    DASHBOARD_JSON = "data/damages_with_embeddings.json"

    print(f"📂 Loading cases from {DASHBOARD_JSON}...")
    with open(DASHBOARD_JSON, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"   Loaded {len(cases):,} cases")

    # Load embedding model
    print("🔄 Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    emb_model = SentenceTransformer("all-MiniLM-L6-v2")
    print("   Model loaded successfully")

    # Build injury-focused search_text and embeddings
    ids = []
    inj_embs = []
    out_cases = []

    print("🔄 Generating injury-focused embeddings...")
    for c in tqdm(cases, desc="Processing cases"):
        # Build search_text from injuries only
        ext = c.get("extended_data", {}) or {}
        injuries = ext.get("injuries") or []

        # Join injuries into search text
        search_text = "; ".join(injuries) if injuries else ""

        # Fallback if no injuries found
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
    print(f"\n📁 Output files:")
    print(f"   - compendium_inj.json: {(data_dir / 'compendium_inj.json').stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   - embeddings_inj.npy: {(data_dir / 'embeddings_inj.npy').stat().st_size / 1024 / 1024:.1f} MB")
    print(f"   - ids.json: {(data_dir / 'ids.json').stat().st_size / 1024:.1f} KB")
    print(f"\n✅ Done! The Streamlit app can now use these embeddings for search.")

if __name__ == "__main__":
    main()
