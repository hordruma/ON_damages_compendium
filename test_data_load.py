"""Test script to diagnose data loading issues"""

import json
import sys

def test_data_structure():
    """Test if the data structure is compatible"""
    print("Loading data...")

    try:
        with open('data/damages_with_embeddings.json') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        return False

    print(f"✓ Loaded {len(data)} cases")

    # Check first case structure
    if not data:
        print("❌ No data in file")
        return False

    first_case = data[0]
    print(f"\n✓ First case keys: {list(first_case.keys())}")

    # Check required fields
    required_fields = ['embedding', 'summary_text', 'region', 'damages']
    missing_fields = []

    for field in required_fields:
        if field not in first_case:
            missing_fields.append(field)

    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        return False
    else:
        print(f"✓ All required fields present: {required_fields}")

    # Check embedding structure
    embedding = first_case.get('embedding')
    if not isinstance(embedding, list):
        print(f"❌ Embedding is not a list: {type(embedding)}")
        return False

    if len(embedding) == 0:
        print(f"❌ Embedding is empty")
        return False

    print(f"✓ Embedding is a list with {len(embedding)} dimensions")

    # Check if all values are numeric
    try:
        first_val = embedding[0]
        if not isinstance(first_val, (int, float)):
            print(f"❌ Embedding values are not numeric: {type(first_val)}")
            return False
    except Exception as e:
        print(f"❌ Error checking embedding values: {e}")
        return False

    print(f"✓ Embedding values are numeric")

    # Check for any None embeddings
    cases_with_none_embeddings = 0
    for i, case in enumerate(data[:100]):  # Check first 100
        if case.get('embedding') is None:
            cases_with_none_embeddings += 1

    if cases_with_none_embeddings > 0:
        print(f"⚠️  Found {cases_with_none_embeddings} cases with None embeddings (in first 100)")
    else:
        print(f"✓ No None embeddings in first 100 cases")

    print("\n✅ Data structure appears valid!")
    return True

if __name__ == '__main__':
    success = test_data_structure()
    sys.exit(0 if success else 1)
