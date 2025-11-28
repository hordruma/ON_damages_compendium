"""Test core app functionality without Streamlit"""

import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def test_search_simulation():
    """Simulate the search functionality"""
    print("Loading data...")
    with open('data/damages_with_embeddings.json') as f:
        cases = json.load(f)

    print(f"✓ Loaded {len(cases)} cases")

    # Try to extract embeddings
    print("\nExtracting embeddings...")
    try:
        vectors = np.array([c["embedding"] for c in cases])
        print(f"✓ Created embedding matrix: {vectors.shape}")
    except Exception as e:
        print(f"❌ Failed to create embedding matrix: {e}")
        return False

    # Try a simple search
    print("\nSimulating search...")
    try:
        # Use first case as query
        query_vec = vectors[0:1]

        # Calculate cosine similarity
        embedding_sims = cosine_similarity(query_vec, vectors)[0]
        print(f"✓ Calculated similarities: {len(embedding_sims)} values")
        print(f"  Min similarity: {embedding_sims.min():.4f}")
        print(f"  Max similarity: {embedding_sims.max():.4f}")
        print(f"  Mean similarity: {embedding_sims.mean():.4f}")

        # Try sorting
        top_indices = np.argsort(embedding_sims)[::-1][:10]
        print(f"✓ Found top 10 matches")

        # Print top matches
        print("\nTop 3 matches:")
        for i, idx in enumerate(top_indices[:3]):
            case = cases[idx]
            print(f"  {i+1}. {case.get('case_name')} ({case.get('year')}) - {embedding_sims[idx]:.4f}")

    except Exception as e:
        print(f"❌ Search simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Try region filtering
    print("\nTesting region filtering...")
    try:
        regions = set(c.get('region') for c in cases if c.get('region'))
        print(f"✓ Found {len(regions)} unique regions")
        print(f"  Regions: {sorted(list(regions))[:10]}")
    except Exception as e:
        print(f"❌ Region filtering failed: {e}")
        return False

    # Try damages extraction
    print("\nTesting damages extraction...")
    try:
        damages = [c.get('damages') for c in cases if c.get('damages')]
        print(f"✓ Found {len(damages)} cases with damages")
        print(f"  Min: ${min(damages):,.2f}")
        print(f"  Max: ${max(damages):,.2f}")
        print(f"  Mean: ${np.mean(damages):,.2f}")
    except Exception as e:
        print(f"❌ Damages extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Try inflation adjustment simulation
    print("\nTesting inflation_adjuster import...")
    try:
        from inflation_adjuster import adjust_for_inflation, DEFAULT_REFERENCE_YEAR
        print(f"✓ Imported inflation_adjuster")
        print(f"  Default reference year: {DEFAULT_REFERENCE_YEAR}")

        # Try adjusting a value
        test_amount = 50000
        test_year = 2000
        adjusted = adjust_for_inflation(test_amount, test_year, DEFAULT_REFERENCE_YEAR)
        if adjusted:
            print(f"  Test: ${test_amount:,} in {test_year} = ${adjusted:,.2f} in {DEFAULT_REFERENCE_YEAR}")
        else:
            print(f"  ⚠️  Inflation adjustment returned None (might not have CPI data)")
    except Exception as e:
        print(f"❌ Inflation adjuster failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✅ All tests passed!")
    return True

if __name__ == '__main__':
    import sys
    success = test_search_simulation()
    sys.exit(0 if success else 1)
