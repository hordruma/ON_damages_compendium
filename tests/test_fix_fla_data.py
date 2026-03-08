"""Tests for FLA data fixing module."""

import pytest
from fix_fla_data import (
    fix_relationship_from_description,
    fix_invalid_relationships,
    extract_fla_from_comments,
    deduplicate_fla_claims,
    fix_fla_data,
)


class TestFixRelationshipFromDescription:
    def test_son_genericized_to_child(self):
        claim = {"relationship": "son", "description": "Son: $5,000.00"}
        assert fix_relationship_from_description(claim) == "child"

    def test_daughter_genericized_to_child(self):
        claim = {"relationship": "daughter", "description": "Daughter: $10,000.00"}
        assert fix_relationship_from_description(claim) == "child"

    def test_child_stays_child(self):
        claim = {"relationship": "child", "description": "Children: $30,000.00"}
        assert fix_relationship_from_description(claim) == "child"

    def test_brother_genericized_to_sibling(self):
        claim = {"relationship": "brother", "description": "Brother: $3,000.00"}
        assert fix_relationship_from_description(claim) == "sibling"

    def test_sister_genericized_to_sibling(self):
        claim = {"relationship": "sister", "description": "Sister: $3,000.00"}
        assert fix_relationship_from_description(claim) == "sibling"

    def test_father_genericized_to_parent(self):
        claim = {"relationship": "father", "description": "Father: $50,000.00"}
        assert fix_relationship_from_description(claim) == "parent"

    def test_mother_genericized_to_parent(self):
        claim = {"relationship": "mother", "description": "Mother: $25,000.00"}
        assert fix_relationship_from_description(claim) == "parent"

    def test_grandfather_genericized_to_grandparent(self):
        claim = {"relationship": "grandfather", "description": "Grandfather: $5,000.00"}
        assert fix_relationship_from_description(claim) == "grandparent"

    def test_spouse_stays(self):
        claim = {"relationship": "spouse", "description": "Wife: $5,000.00"}
        assert fix_relationship_from_description(claim) == "spouse"


class TestFixInvalidRelationships:
    def test_grandchildren_to_grandchild(self):
        claim = {"relationship": "grandchildren"}
        assert fix_invalid_relationships(claim) == "grandchild"

    def test_grandparents_to_grandparent(self):
        claim = {"relationship": "grandparents"}
        assert fix_invalid_relationships(claim) == "grandparent"

    def test_grandson_to_grandchild(self):
        claim = {"relationship": "grandson"}
        assert fix_invalid_relationships(claim) == "grandchild"

    def test_son_to_child(self):
        claim = {"relationship": "son"}
        assert fix_invalid_relationships(claim) == "child"

    def test_daughter_to_child(self):
        claim = {"relationship": "daughter"}
        assert fix_invalid_relationships(claim) == "child"

    def test_father_to_parent(self):
        claim = {"relationship": "father"}
        assert fix_invalid_relationships(claim) == "parent"

    def test_mother_to_parent(self):
        claim = {"relationship": "mother"}
        assert fix_invalid_relationships(claim) == "parent"

    def test_brother_to_sibling(self):
        claim = {"relationship": "brother"}
        assert fix_invalid_relationships(claim) == "sibling"

    def test_sister_to_sibling(self):
        claim = {"relationship": "sister"}
        assert fix_invalid_relationships(claim) == "sibling"

    def test_valid_unchanged(self):
        claim = {"relationship": "spouse"}
        assert fix_invalid_relationships(claim) == "spouse"

    def test_unknown_fallback(self):
        claim = {"relationship": "cousin"}
        assert fix_invalid_relationships(claim) == "unknown"


class TestExtractFlaFromComments:
    def test_extracts_wife_amount(self):
        comments = "Wife: $5,000.00 for loss of care"
        claims = extract_fla_from_comments(comments, ["Wife"])
        assert len(claims) == 1
        assert claims[0]["relationship"] == "spouse"
        assert claims[0]["amount"] == 5000.0

    def test_extracts_son_as_child(self):
        comments = "Son - $15,000.00"
        claims = extract_fla_from_comments(comments, ["Son/Daughter"])
        assert len(claims) == 1
        assert claims[0]["relationship"] == "child"
        assert claims[0]["amount"] == 15000.0

    def test_empty_comments(self):
        claims = extract_fla_from_comments("", ["Wife"])
        assert claims == []

    def test_no_amounts(self):
        comments = "Close relationship with family"
        claims = extract_fla_from_comments(comments, ["Son/Daughter"])
        assert claims == []


class TestDeduplicateFLAClaims:
    def test_removes_exact_duplicates(self):
        claims = [
            {"relationship": "spouse", "amount": 5000.0, "is_fla_award": True},
            {"relationship": "spouse", "amount": 5000.0, "is_fla_award": True},
        ]
        result = deduplicate_fla_claims(claims)
        assert len(result) == 1

    def test_keeps_different_amounts(self):
        claims = [
            {"relationship": "spouse", "amount": 5000.0, "is_fla_award": True},
            {"relationship": "spouse", "amount": 10000.0, "is_fla_award": True},
        ]
        result = deduplicate_fla_claims(claims)
        assert len(result) == 2


class TestFixFlaData:
    def test_full_pipeline(self):
        cases = [
            {
                "case_name": "Test v. Test",
                "non_pecuniary_damages": 100000,
                "extended_data": {
                    "categories": ["General"],
                    "family_law_act_claims": [
                        {"relationship": "son", "amount": 5000.0,
                         "description": "Son: $5,000.00", "is_fla_award": True},
                        {"relationship": "grandchildren", "amount": 3000.0,
                         "description": "Grandchildren: $3,000.00", "is_fla_award": True},
                    ]
                }
            }
        ]
        fixed, stats = fix_fla_data(cases, verbose=False)
        claims = fixed[0]["extended_data"]["family_law_act_claims"]
        assert claims[0]["relationship"] == "child"
        assert claims[1]["relationship"] == "grandchild"

    def test_creates_fla_from_category_and_npd(self):
        cases = [
            {
                "case_name": "Test v. Test",
                "non_pecuniary_damages": 15000.0,
                "extended_data": {
                    "categories": ["Son/Daughter"],
                    "family_law_act_claims": [],
                    "comments": "Close relationship with deceased son.",
                }
            }
        ]
        fixed, stats = fix_fla_data(cases, verbose=False)
        claims = fixed[0]["extended_data"]["family_law_act_claims"]
        assert len(claims) >= 1
        assert claims[0]["amount"] == 15000.0
        assert claims[0]["relationship"] == "child"
