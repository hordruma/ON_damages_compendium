#!/usr/bin/env python3
"""
Simple test script to verify case merging logic works correctly.

This test doesn't import the full module to avoid dependency issues.
Instead, it copies the merge logic and tests it directly.
"""

import json
from typing import Dict, Any


def merge_cases(existing_case: Dict[str, Any], new_case: Dict[str, Any]) -> None:
    """
    Merge information from a duplicate case into an existing case.

    This is a copy of the merge_cases method from DamagesCompendiumParser
    for testing purposes.
    """
    # Track all source pages
    if 'source_pages' not in existing_case:
        # Convert old single source_page to list if needed
        if 'source_page' in existing_case:
            existing_case['source_pages'] = [existing_case['source_page']]
            del existing_case['source_page']
        else:
            existing_case['source_pages'] = []

    # Add new source page
    new_page = new_case.get('source_page')
    if new_page and new_page not in existing_case['source_pages']:
        existing_case['source_pages'].append(new_page)

    # Merge categories (body regions) - this is crucial for multi-table cases
    existing_categories = set(filter(None, [existing_case.get('category')]))
    new_category = new_case.get('category')
    if new_category:
        existing_categories.add(new_category)
    if existing_categories:
        existing_case['category'] = list(existing_categories)

    # Merge regions
    existing_regions = set(filter(None, [existing_case.get('region')] if isinstance(existing_case.get('region'), str) else existing_case.get('region', [])))
    new_region = new_case.get('region')
    if new_region:
        if isinstance(new_region, str):
            existing_regions.add(new_region)
        elif isinstance(new_region, list):
            existing_regions.update(new_region)
    if existing_regions:
        existing_case['region'] = list(existing_regions)

    # Merge citations
    existing_citations = set(existing_case.get('citations', []))
    new_citations = set(new_case.get('citations', []))
    merged_citations = existing_citations | new_citations
    if merged_citations:
        existing_case['citations'] = list(merged_citations)

    # Merge judges
    existing_judges = set(existing_case.get('judges', []))
    new_judges = set(new_case.get('judges', []))
    merged_judges = existing_judges | new_judges
    if merged_judges:
        existing_case['judges'] = list(merged_judges)

    # Merge plaintiffs - match by plaintiff_id or merge all
    existing_plaintiffs = existing_case.get('plaintiffs', [])
    new_plaintiffs = new_case.get('plaintiffs', [])

    if existing_plaintiffs and new_plaintiffs:
        # Create a mapping of existing plaintiffs by ID
        existing_by_id = {p.get('plaintiff_id'): p for p in existing_plaintiffs if p.get('plaintiff_id')}

        for new_plaintiff in new_plaintiffs:
            plaintiff_id = new_plaintiff.get('plaintiff_id')

            if plaintiff_id and plaintiff_id in existing_by_id:
                # Merge plaintiff data
                existing_plaintiff = existing_by_id[plaintiff_id]

                # Merge injuries
                existing_injuries = set(existing_plaintiff.get('injuries', []))
                new_injuries = set(new_plaintiff.get('injuries', []))
                merged_injuries = existing_injuries | new_injuries
                if merged_injuries:
                    existing_plaintiff['injuries'] = list(merged_injuries)

                # Merge other_damages
                existing_damages = existing_plaintiff.get('other_damages', [])
                new_damages = new_plaintiff.get('other_damages', [])

                # Create a set of existing damage types to avoid true duplicates
                existing_damage_keys = {(d.get('type'), d.get('amount')) for d in existing_damages}

                for new_damage in new_damages:
                    damage_key = (new_damage.get('type'), new_damage.get('amount'))
                    if damage_key not in existing_damage_keys:
                        existing_damages.append(new_damage)
                        existing_damage_keys.add(damage_key)

                # Update non-pecuniary damages if higher (take max)
                existing_npd = existing_plaintiff.get('non_pecuniary_damages')
                new_npd = new_plaintiff.get('non_pecuniary_damages')
                if new_npd and (not existing_npd or new_npd > existing_npd):
                    existing_plaintiff['non_pecuniary_damages'] = new_npd
                    # Also update provisional flag if present
                    if 'is_provisional' in new_plaintiff:
                        existing_plaintiff['is_provisional'] = new_plaintiff['is_provisional']
            else:
                # New plaintiff - add them
                existing_plaintiffs.append(new_plaintiff)
    elif new_plaintiffs and not existing_plaintiffs:
        # No existing plaintiffs, use new ones
        existing_case['plaintiffs'] = new_plaintiffs

    # Merge Family Law Act claims
    existing_fla = existing_case.get('family_law_act_claims', [])
    new_fla = new_case.get('family_law_act_claims', [])

    # Create a set of existing FLA claim keys to avoid duplicates
    existing_fla_keys = {(f.get('category'), f.get('amount'), f.get('description')) for f in existing_fla}

    for new_claim in new_fla:
        claim_key = (new_claim.get('category'), new_claim.get('amount'), new_claim.get('description'))
        if claim_key not in existing_fla_keys:
            existing_fla.append(new_claim)
            existing_fla_keys.add(claim_key)

    if existing_fla:
        existing_case['family_law_act_claims'] = existing_fla

    # Merge comments
    existing_comments = existing_case.get('comments', '')
    new_comments = new_case.get('comments', '')

    if new_comments and new_comments not in existing_comments:
        if existing_comments:
            existing_case['comments'] = f"{existing_comments} | {new_comments}"
        else:
            existing_case['comments'] = new_comments

    # Update metadata fields if they're missing
    for field in ['court', 'plaintiff_name', 'defendant_name']:
        if not existing_case.get(field) and new_case.get(field):
            existing_case[field] = new_case[field]


def test_case_merging():
    """Test that duplicate cases are merged correctly."""

    print("Testing case merging logic...\n")

    # Simulate a case appearing first in the CERVICAL SPINE table
    case1 = {
        "case_id": "Smith v. Jones_2020",
        "case_name": "Smith v. Jones",
        "plaintiff_name": "Smith",
        "defendant_name": "Jones",
        "year": 2020,
        "category": "SPINE",
        "region": "CERVICAL SPINE",
        "source_page": 100,
        "court": "Ontario Superior Court",
        "citations": ["2020 ONSC 1234"],
        "judges": ["Brown"],
        "plaintiffs": [{
            "plaintiff_id": "P1",
            "sex": "M",
            "age": 35,
            "non_pecuniary_damages": 250000.0,
            "is_provisional": False,
            "injuries": ["Cervical spine injury", "Whiplash"],
            "other_damages": [
                {"type": "past_loss_of_income", "amount": 50000.0, "description": "Past income loss"}
            ]
        }],
        "family_law_act_claims": [],
        "comments": "Initial assessment"
    }

    # Simulate the same case appearing later in the LUMBAR SPINE table
    case2 = {
        "case_id": "Smith v. Jones_2020",
        "case_name": "Smith v. Jones",
        "plaintiff_name": "Smith",
        "defendant_name": "Jones",
        "year": 2020,
        "category": "SPINE",
        "region": "LUMBAR SPINE",
        "source_page": 150,
        "court": "Ontario Superior Court",
        "citations": ["2020 ONSC 1234", "2020 CarswellOnt 5678"],
        "judges": ["Brown"],
        "plaintiffs": [{
            "plaintiff_id": "P1",
            "sex": "M",
            "age": 35,
            "non_pecuniary_damages": 250000.0,
            "is_provisional": False,
            "injuries": ["Lumbar spine injury", "Disc herniation"],
            "other_damages": [
                {"type": "cost_of_future_care", "amount": 75000.0, "description": "Future care costs"}
            ]
        }],
        "family_law_act_claims": [
            {"category": "spouse", "amount": 25000.0, "description": "Loss of care, guidance and companionship"}
        ],
        "comments": "Additional findings"
    }

    print("BEFORE MERGING:")
    print("=" * 80)
    print("\nCase 1 (from page 100 - CERVICAL SPINE table):")
    print(json.dumps(case1, indent=2))
    print("\nCase 2 (from page 150 - LUMBAR SPINE table):")
    print(json.dumps(case2, indent=2))

    # Merge case2 into case1
    merge_cases(case1, case2)

    print("\n\nAFTER MERGING:")
    print("=" * 80)
    print("\nMerged case (all information combined):")
    print(json.dumps(case1, indent=2))

    # Verify the merge worked correctly
    print("\n\nVERIFICATION:")
    print("=" * 80)

    assertions = []

    # Check source pages
    if 'source_pages' in case1 and 100 in case1['source_pages'] and 150 in case1['source_pages']:
        assertions.append("✓ Both source pages tracked: [100, 150]")
    else:
        assertions.append(f"✗ Source pages incorrect: {case1.get('source_pages')}")

    # Check regions merged
    regions = case1.get('region', [])
    if isinstance(regions, list) and 'CERVICAL SPINE' in regions and 'LUMBAR SPINE' in regions:
        assertions.append(f"✓ Both regions preserved: {regions}")
    else:
        assertions.append(f"✗ Regions not merged properly: {regions}")

    # Check injuries merged
    injuries = case1['plaintiffs'][0].get('injuries', [])
    expected_injuries = {'Cervical spine injury', 'Whiplash', 'Lumbar spine injury', 'Disc herniation'}
    if set(injuries) == expected_injuries:
        assertions.append(f"✓ All 4 injuries preserved: {injuries}")
    else:
        assertions.append(f"✗ Injuries not merged: {injuries}")

    # Check other_damages merged
    damages = case1['plaintiffs'][0].get('other_damages', [])
    if len(damages) == 2:
        types = {d['type'] for d in damages}
        if 'past_loss_of_income' in types and 'cost_of_future_care' in types:
            assertions.append(f"✓ Both damage types preserved: {types}")
        else:
            assertions.append(f"✗ Damage types incorrect: {types}")
    else:
        assertions.append(f"✗ Should have 2 damage entries, got {len(damages)}")

    # Check FLA claims
    fla = case1.get('family_law_act_claims', [])
    if len(fla) == 1 and fla[0]['amount'] == 25000.0:
        assertions.append("✓ FLA claim preserved")
    else:
        assertions.append(f"✗ FLA claims incorrect: {fla}")

    # Check citations merged
    citations = case1.get('citations', [])
    if len(citations) == 2:
        assertions.append(f"✓ Both citations preserved: {citations}")
    else:
        assertions.append(f"✗ Citations not merged: {citations}")

    # Check comments merged
    comments = case1.get('comments', '')
    if 'Initial assessment' in comments and 'Additional findings' in comments:
        assertions.append(f"✓ Comments merged: {comments}")
    else:
        assertions.append(f"✗ Comments not merged: {comments}")

    # Print all assertions
    for assertion in assertions:
        print(assertion)

    # Overall result
    passed = all('✓' in a for a in assertions)
    print("\n" + "=" * 80)
    if passed:
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nThe merging logic correctly preserves ALL information from duplicate cases,")
        print("ensuring that cases appearing in multiple body region tables are complete.")
        return 0
    else:
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        return 1


if __name__ == "__main__":
    exit(test_case_merging())
