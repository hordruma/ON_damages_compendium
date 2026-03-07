#!/usr/bin/env python3
"""
Fix FLA (Family Law Act) data quality issues in the damages dataset.

This script fixes several known parsing issues:
1. Relationship mapping: "child" -> "son"/"daughter" when description specifies gender
2. Invalid relationship values: "grandchildren" -> "grandchild", "grandparents" -> "grandparent", etc.
3. FLA section cases: Cases categorized under FLA sections (e.g., "Son/Daughter") that
   are missing family_law_act_claims objects get them reconstructed from category + comments
4. Duplicate cases: Cases appearing multiple times get deduplicated

Run this after build_embeddings.py to clean up data quality issues.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter


# Mapping of invalid/non-standard relationship values to valid enum values
RELATIONSHIP_FIXES = {
    "grandchildren": "grandchild",
    "grandparents": "grandparent",
    "grandson": "grandchild",
    "granddaughter": "grandchild",
    "husband": "spouse",
    "wife": "spouse",
    "kids": "child",
    "children": "child",
    "mom": "mother",
    "dad": "father",
    "bro": "brother",
    "sis": "sister",
}

# Valid relationship values per the schema enum
VALID_RELATIONSHIPS = {
    "father", "mother", "parent", "spouse", "son", "daughter", "child",
    "brother", "sister", "sibling", "grandfather", "grandmother",
    "grandparent", "grandchild", "unknown"
}

# FLA category to relationship mapping
# These are the section headers in the compendium PDF
FLA_CATEGORY_TO_RELATIONSHIP = {
    "Son/Daughter": ["son", "daughter"],
    "Husband and Father": ["spouse", "father"],
    "Husband": ["spouse"],
    "Wife": ["spouse"],
    "Wife & Mother": ["spouse", "mother"],
    "Brother/Sister": ["brother", "sister"],
    "Mother": ["mother"],
    "Father": ["father"],
    "Grandparent": ["grandparent"],
    "Grandchild": ["grandchild"],
}


def fix_relationship_from_description(claim: Dict[str, Any]) -> str:
    """
    Fix the relationship field using the description text.

    When the LLM maps "Son: $5,000" to relationship="child" instead of "son",
    this function corrects it by parsing the description.

    Args:
        claim: FLA claim dict with 'relationship' and 'description' fields

    Returns:
        Corrected relationship string
    """
    relationship = claim.get("relationship", "unknown")
    description = (claim.get("description") or "").lower()

    # If relationship is already gender-specific, no fix needed
    if relationship in ("son", "daughter", "father", "mother",
                        "brother", "sister", "grandfather", "grandmother"):
        return relationship

    # Fix "child" -> "son" or "daughter" based on description
    if relationship == "child":
        if re.search(r'\bson\b', description):
            return "son"
        if re.search(r'\bdaughter\b', description):
            return "daughter"

    # Fix "sibling" -> "brother" or "sister" based on description
    if relationship == "sibling":
        if re.search(r'\bbrother\b', description):
            return "brother"
        if re.search(r'\bsister\b', description):
            return "sister"

    # Fix "parent" -> "father" or "mother" based on description
    if relationship == "parent":
        if re.search(r'\bfather\b', description):
            return "father"
        if re.search(r'\bmother\b', description):
            return "mother"

    # Fix "grandparent" -> "grandfather" or "grandmother" based on description
    if relationship == "grandparent":
        if re.search(r'\bgrandfather\b', description):
            return "grandfather"
        if re.search(r'\bgrandmother\b', description):
            return "grandmother"

    # Fix "spouse" -> keep as spouse (we can't infer husband vs wife reliably)
    return relationship


def fix_invalid_relationships(claim: Dict[str, Any]) -> str:
    """
    Fix non-standard relationship values to valid enum values.

    Args:
        claim: FLA claim dict

    Returns:
        Valid relationship string
    """
    relationship = claim.get("relationship", "unknown")

    # Normalize to lowercase
    rel_lower = relationship.lower().strip()

    # Check if it's already valid
    if rel_lower in VALID_RELATIONSHIPS:
        return rel_lower

    # Check our fixes mapping
    if rel_lower in RELATIONSHIP_FIXES:
        return RELATIONSHIP_FIXES[rel_lower]

    # Unknown - return as unknown
    return "unknown"


def extract_fla_from_comments(comments: str, categories: List[str]) -> List[Dict[str, Any]]:
    """
    Extract FLA claim information from comments text for cases in FLA sections.

    For cases that are in an FLA category section (e.g., "Son/Daughter") but
    don't have FLA claims extracted, try to reconstruct claims from the comments.

    Args:
        comments: Case comments text
        categories: Case categories (from the compendium sections)

    Returns:
        List of extracted FLA claim dicts
    """
    if not comments:
        return []

    claims = []

    # Look for common FLA amount patterns in comments
    # Patterns like: "Wife: $5,000.00", "Son - $15,000", "Mother: $25,000.00"
    # Also: "Loss of care, guidance and companionship: $250,000.00"
    fla_patterns = [
        # "Relationship: $amount" or "Relationship - $amount"
        r'(?:^|\s)((?:Wife|Husband|Mother|Father|Son|Daughter|Brother|Sister|'
        r'Child(?:ren)?|Grandchild(?:ren)?|Grandparent|Grandmother|Grandfather|'
        r'Spouse|Sibling)\s*(?:(?:and|&|/)\s*(?:Mother|Father))?\s*)'
        r'[-:]\s*\$\s*([\d,]+(?:\.\d{2})?)',
    ]

    for pattern in fla_patterns:
        for match in re.finditer(pattern, comments, re.IGNORECASE):
            rel_text = match.group(1).strip().lower()
            amount_str = match.group(2).replace(",", "")
            try:
                amount = float(amount_str)
            except ValueError:
                continue

            # Map relationship text to valid enum
            relationship = _map_text_to_relationship(rel_text)
            if relationship:
                claims.append({
                    "relationship": relationship,
                    "amount": amount,
                    "description": match.group(0).strip(),
                    "is_fla_award": True,
                })

    # Also look for "Loss of care, guidance and companionship" patterns
    loc_pattern = r'Loss of (?:care|guidance|companionship)[^:$]*[:]\s*\$\s*([\d,]+(?:\.\d{2})?)'
    for match in re.finditer(loc_pattern, comments, re.IGNORECASE):
        amount_str = match.group(1).replace(",", "")
        try:
            amount = float(amount_str)
        except ValueError:
            continue

        # Determine relationship from categories
        fla_cats = [c for c in categories if c in FLA_CATEGORY_TO_RELATIONSHIP]
        if fla_cats:
            rels = FLA_CATEGORY_TO_RELATIONSHIP[fla_cats[0]]
            relationship = rels[0] if rels else "unknown"
        else:
            relationship = "unknown"

        claims.append({
            "relationship": relationship,
            "amount": amount,
            "description": match.group(0).strip(),
            "is_fla_award": True,
        })

    return claims


def _map_text_to_relationship(text: str) -> Optional[str]:
    """Map free-text relationship description to valid enum value."""
    text = text.lower().strip()

    # Remove compound relationships like "wife and mother"
    # Take the first one
    for sep in [" and ", " & ", "/"]:
        if sep in text:
            text = text.split(sep)[0].strip()

    mapping = {
        "wife": "spouse",
        "husband": "spouse",
        "spouse": "spouse",
        "mother": "mother",
        "father": "father",
        "son": "son",
        "daughter": "daughter",
        "child": "child",
        "children": "child",
        "brother": "brother",
        "sister": "sister",
        "sibling": "sibling",
        "grandchild": "grandchild",
        "grandchildren": "grandchild",
        "grandparent": "grandparent",
        "grandparents": "grandparent",
        "grandmother": "grandmother",
        "grandfather": "grandfather",
        "grandson": "grandchild",
        "granddaughter": "grandchild",
    }

    return mapping.get(text)


def deduplicate_fla_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate FLA claims (same relationship + amount).

    Args:
        claims: List of FLA claim dicts

    Returns:
        Deduplicated list
    """
    seen = set()
    unique = []
    for claim in claims:
        key = (claim.get("relationship"), claim.get("amount"))
        if key not in seen:
            seen.add(key)
            unique.append(claim)
    return unique


def fix_fla_data(cases: List[Dict[str, Any]], verbose: bool = True) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Fix all FLA data quality issues in the dataset.

    Args:
        cases: List of case dicts (dashboard format)
        verbose: Print progress

    Returns:
        Tuple of (fixed cases list, stats dict)
    """
    stats = {
        "total_cases": len(cases),
        "relationships_fixed_from_description": 0,
        "invalid_relationships_fixed": 0,
        "fla_claims_extracted_from_comments": 0,
        "fla_claims_deduplicated": 0,
        "cases_with_fla_category_fixed": 0,
    }

    for case in cases:
        ed = case.get("extended_data", {})
        fla_claims = ed.get("family_law_act_claims", [])

        # Fix 1: Fix relationship from description (child -> son/daughter)
        for claim in fla_claims:
            old_rel = claim.get("relationship")
            new_rel = fix_relationship_from_description(claim)
            if new_rel != old_rel:
                claim["relationship"] = new_rel
                stats["relationships_fixed_from_description"] += 1

        # Fix 2: Fix invalid relationship values
        for claim in fla_claims:
            old_rel = claim.get("relationship", "")
            if old_rel.lower() not in VALID_RELATIONSHIPS:
                new_rel = fix_invalid_relationships(claim)
                claim["relationship"] = new_rel
                stats["invalid_relationships_fixed"] += 1

        # Fix 3: Extract FLA claims from comments for FLA-category cases
        categories = ed.get("categories", [])
        fla_cats = [c for c in categories if c in FLA_CATEGORY_TO_RELATIONSHIP]

        if fla_cats and not fla_claims:
            # This case is in an FLA section but has no FLA claims
            comments = ed.get("comments") or case.get("comments", "")

            # First try to extract from comments text
            extracted = extract_fla_from_comments(comments, categories)

            # If no claims found in comments, create from category + non_pecuniary_damages
            # Cases in FLA sections (e.g., "Son/Daughter") where the non_pecuniary_damages
            # IS the FLA award amount
            if not extracted:
                npd = case.get("non_pecuniary_damages", 0) or 0
                if npd > 0:
                    for fla_cat in fla_cats:
                        rels = FLA_CATEGORY_TO_RELATIONSHIP.get(fla_cat, [])
                        for rel in rels:
                            extracted.append({
                                "relationship": rel,
                                "amount": npd,
                                "description": f"{fla_cat}: ${npd:,.2f}",
                                "is_fla_award": True,
                            })
                        # Only use first FLA category for the amount
                        break

            if extracted:
                fla_claims.extend(extracted)
                ed["family_law_act_claims"] = fla_claims
                stats["fla_claims_extracted_from_comments"] += len(extracted)
                stats["cases_with_fla_category_fixed"] += 1

        # Fix 4: Deduplicate FLA claims
        if fla_claims:
            original_count = len(fla_claims)
            deduped = deduplicate_fla_claims(fla_claims)
            if len(deduped) < original_count:
                ed["family_law_act_claims"] = deduped
                stats["fla_claims_deduplicated"] += original_count - len(deduped)

    if verbose:
        print("FLA Data Fixes Applied:")
        print(f"  Relationships fixed from description: {stats['relationships_fixed_from_description']}")
        print(f"  Invalid relationships normalized: {stats['invalid_relationships_fixed']}")
        print(f"  FLA claims extracted from comments: {stats['fla_claims_extracted_from_comments']}")
        print(f"  Cases with FLA category fixed: {stats['cases_with_fla_category_fixed']}")
        print(f"  Duplicate FLA claims removed: {stats['fla_claims_deduplicated']}")

    return cases, stats


def fix_data_file(input_path: str = "data/damages_with_embeddings.json",
                  output_path: Optional[str] = None,
                  verbose: bool = True) -> Dict[str, int]:
    """
    Load, fix, and save the damages data file.

    Args:
        input_path: Path to input JSON
        output_path: Path to output JSON (defaults to same as input)
        verbose: Print progress

    Returns:
        Stats dict
    """
    if output_path is None:
        output_path = input_path

    if verbose:
        print(f"Loading {input_path}...")

    with open(input_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    if verbose:
        print(f"Loaded {len(cases)} cases")

    cases, stats = fix_fla_data(cases, verbose=verbose)

    if verbose:
        print(f"\nSaving to {output_path}...")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"Done!")

    return stats


if __name__ == "__main__":
    # Fix main data file
    fix_data_file()

    # Also fix compendium_inj.json if it exists
    inj_path = Path("data/compendium_inj.json")
    if inj_path.exists():
        print()
        fix_data_file(str(inj_path))
