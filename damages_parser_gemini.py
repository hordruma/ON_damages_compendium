"""
Ontario Damages Compendium Parser using Google Gemini API.

This module provides tools to parse the Ontario Damages Compendium PDF
using Google's Gemini API for intelligent extraction of case data.

Features:
- PDF text extraction with pdfplumber
- Structured data extraction using Gemini 2.0 Flash
- Checkpoint/resume functionality for long-running parses
- Multi-plaintiff support
- Family Law Act claims extraction
- Comprehensive error handling

Usage:
    from damages_parser_gemini import parse_compendium

    cases = parse_compendium(
        "2024damagescompendium.pdf",
        api_key="your-api-key",
        output_json="damages_full.json"
    )

    # Resume from interruption
    cases = parse_compendium(
        "2024damagescompendium.pdf",
        api_key="your-api-key",
        output_json="damages_full.json",
        resume=True
    )
"""

import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import pdfplumber
import requests


@dataclass
class Plaintiff:
    """Represents a plaintiff in a damages case."""
    plaintiff_id: str
    sex: Optional[str] = None
    age: Optional[int] = None
    non_pecuniary_damages: Optional[float] = None
    is_provisional: bool = False
    injuries: List[str] = None
    other_damages: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.injuries is None:
            self.injuries = []
        if self.other_damages is None:
            self.other_damages = []


@dataclass
class FamilyLawActClaim:
    """Represents a Family Law Act claim."""
    description: str
    amount: Optional[float] = None


@dataclass
class DamagesCase:
    """Represents a complete damages case."""
    case_id: str
    case_name: str
    plaintiff_name: Optional[str] = None
    defendant_name: Optional[str] = None
    year: Optional[int] = None
    category: Optional[str] = None
    court: Optional[str] = None
    citations: List[str] = None
    judges: List[str] = None
    plaintiffs: List[Plaintiff] = None
    family_law_act_claims: List[FamilyLawActClaim] = None
    comments: Optional[str] = None

    def __post_init__(self):
        if self.citations is None:
            self.citations = []
        if self.judges is None:
            self.judges = []
        if self.plaintiffs is None:
            self.plaintiffs = []
        if self.family_law_act_claims is None:
            self.family_law_act_claims = []


class PDFTextExtractor:
    """Extracts text from PDF files using pdfplumber."""

    def __init__(self, pdf_path: str):
        """
        Initialize the PDF extractor.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = pdf_path

    def extract_page(self, page_number: int) -> Optional[str]:
        """
        Extract text from a specific page.

        Args:
            page_number: Page number (1-indexed)

        Returns:
            Extracted text or None if error
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                if page_number < 1 or page_number > len(pdf.pages):
                    return None

                page = pdf.pages[page_number - 1]  # pdfplumber uses 0-indexed
                return page.extract_text()
        except Exception as e:
            print(f"Error extracting page {page_number}: {e}")
            return None

    def get_page_count(self) -> int:
        """
        Get the total number of pages in the PDF.

        Returns:
            Number of pages
        """
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                return len(pdf.pages)
        except Exception as e:
            print(f"Error getting page count: {e}")
            return 0


class DamagesCompendiumParser:
    """
    Parses the Ontario Damages Compendium using Google Gemini API.

    This parser uses Gemini 2.0 Flash to intelligently extract structured
    case data from the PDF, including support for multi-plaintiff cases
    and Family Law Act claims.
    """

    # Gemini API endpoint
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"

    # Extraction prompt template
    EXTRACTION_PROMPT = """You are parsing a legal damages compendium. Extract all case information from this page.

Return a JSON array of cases. Each case should have:
- case_name: Full case name
- plaintiff_name: Plaintiff name (if different from case_name)
- defendant_name: Defendant name
- year: Year of decision (integer)
- category: Category/type of injury (e.g., "CERVICAL SPINE", "HEAD INJURY")
- court: Court name
- citations: Array of citation strings
- judges: Array of judge names
- plaintiffs: Array of plaintiff objects, each with:
  - plaintiff_id: "P1", "P2", etc. for multiple plaintiffs
  - sex: "M" or "F"
  - age: Age in years (integer)
  - non_pecuniary_damages: Amount in dollars (float)
  - is_provisional: true/false if damages are provisional
  - injuries: Array of injury descriptions
  - other_damages: Array of {type, amount, description} objects
- family_law_act_claims: Array of {description, amount} objects
- comments: Any additional notes or comments

Important:
- If only one plaintiff, still use array with plaintiff_id "P1"
- Parse all monetary amounts as numbers (no $ or commas)
- If information is not present, use null
- Return empty array [] if no cases on this page
- Be precise with numbers and dates

Page text:
{page_text}

Return only the JSON array, no other text."""

    def __init__(self, api_key: str, verbose: bool = True):
        """
        Initialize the parser.

        Args:
            api_key: Google Gemini API key
            verbose: Whether to print progress messages
        """
        self.api_key = api_key
        self.verbose = verbose
        self.errors: List[Dict[str, Any]] = []

    def _call_gemini(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call Gemini API with retry logic.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retries on failure

        Returns:
            Response text or None if all retries failed
        """
        headers = {
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for consistent extraction
                "maxOutputTokens": 8192,
            }
        }

        url = f"{self.GEMINI_API_URL}?key={self.api_key}"

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=60)

                if response.status_code == 200:
                    result = response.json()
                    if "candidates" in result and len(result["candidates"]) > 0:
                        content = result["candidates"][0].get("content", {})
                        parts = content.get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return None

                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt  # Exponential backoff
                    if self.verbose:
                        print(f"Rate limit hit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                else:
                    if self.verbose:
                        print(f"API error {response.status_code}: {response.text}")
                    return None

            except Exception as e:
                if self.verbose:
                    print(f"Request error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None

        return None

    def _parse_gemini_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse Gemini's JSON response.

        Args:
            response_text: Raw response text from Gemini

        Returns:
            List of case dictionaries
        """
        if not response_text:
            return []

        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)

        try:
            cases = json.loads(response_text)
            if isinstance(cases, list):
                return cases
            elif isinstance(cases, dict):
                return [cases]
            else:
                return []
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"JSON parse error: {e}")
            return []

    def parse_page(self, page_number: int, page_text: str) -> List[Dict[str, Any]]:
        """
        Parse a single page to extract case data.

        Args:
            page_number: Page number (for logging)
            page_text: Extracted text from the page

        Returns:
            List of case dictionaries
        """
        if not page_text or len(page_text.strip()) < 50:
            return []

        prompt = self.EXTRACTION_PROMPT.format(page_text=page_text)
        response = self._call_gemini(prompt)

        if response:
            return self._parse_gemini_response(response)
        else:
            self.errors.append({
                "page": page_number,
                "error": "Failed to get valid response from Gemini"
            })
            return []

    def parse_pdf(
        self,
        pdf_path: str,
        start_page: int = 1,
        end_page: Optional[int] = None,
        checkpoint_file: str = "parsing_checkpoint.json",
        output_json: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse the entire PDF or a range of pages.

        Args:
            pdf_path: Path to PDF file
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (None = all pages)
            checkpoint_file: Path to save checkpoints
            output_json: Path to save results incrementally

        Returns:
            List of all parsed cases
        """
        extractor = PDFTextExtractor(pdf_path)
        total_pages = extractor.get_page_count()

        if end_page is None:
            end_page = total_pages

        all_cases = []
        case_ids_seen = set()

        if self.verbose:
            print(f"Parsing pages {start_page} to {end_page} of {total_pages}")

        for page_num in range(start_page, end_page + 1):
            if self.verbose:
                print(f"\nPage {page_num}/{end_page}...", end=" ")

            # Extract text
            page_text = extractor.extract_page(page_num)
            if not page_text:
                if self.verbose:
                    print("(empty)")
                continue

            # Parse page
            page_cases = self.parse_page(page_num, page_text)

            # Deduplicate and add
            new_cases = 0
            for case in page_cases:
                # Generate unique ID if not present
                if "case_id" not in case or not case["case_id"]:
                    case["case_id"] = f"{case.get('case_name', 'UNKNOWN')}_{case.get('year', 0)}"

                if case["case_id"] not in case_ids_seen:
                    all_cases.append(case)
                    case_ids_seen.add(case["case_id"])
                    new_cases += 1

            if self.verbose:
                print(f"found {new_cases} new cases (total: {len(all_cases)})")

            # Save checkpoint
            checkpoint = {
                "last_page": page_num,
                "total_cases": len(all_cases),
                "timestamp": time.time()
            }
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint, f, indent=2)

            # Save incremental results
            if output_json:
                with open(output_json, "w") as f:
                    json.dump(all_cases, f, indent=2)

            # Rate limiting - small delay between pages
            time.sleep(0.5)

        if self.verbose:
            print(f"\n✓ Parsing complete: {len(all_cases)} cases")
            if self.errors:
                print(f"⚠ {len(self.errors)} errors occurred")

        return all_cases


def parse_compendium(
    pdf_path: str,
    api_key: str,
    output_json: str = "damages_full.json",
    checkpoint_file: str = "parsing_checkpoint.json",
    resume: bool = False,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Parse the Ontario Damages Compendium PDF.

    This is the main entry point for parsing. It supports automatic
    checkpointing and resume functionality.

    Args:
        pdf_path: Path to the PDF file
        api_key: Google Gemini API key
        output_json: Path to save parsed cases
        checkpoint_file: Path to checkpoint file
        resume: If True, resume from last checkpoint
        verbose: Whether to print progress

    Returns:
        List of parsed case dictionaries

    Example:
        # Fresh parse
        cases = parse_compendium(
            "2024damagescompendium.pdf",
            api_key="your-key",
            output_json="damages.json"
        )

        # Resume after interruption
        cases = parse_compendium(
            "2024damagescompendium.pdf",
            api_key="your-key",
            output_json="damages.json",
            resume=True
        )
    """
    parser = DamagesCompendiumParser(api_key, verbose=verbose)

    start_page = 1
    existing_cases = []

    # Check for resume
    if resume:
        checkpoint_path = Path(checkpoint_file)
        output_path = Path(output_json)

        if checkpoint_path.exists() and output_path.exists():
            # Load checkpoint
            with open(checkpoint_path) as f:
                checkpoint = json.load(f)

            # Load existing cases
            with open(output_path) as f:
                existing_cases = json.load(f)

            # Resume from 1 page back for safety
            start_page = max(1, checkpoint["last_page"] - 1)

            if verbose:
                print(f"Resuming from page {start_page}")
                print(f"Loaded {len(existing_cases)} existing cases")
        else:
            if verbose:
                print("No checkpoint found, starting fresh")

    # Parse
    new_cases = parser.parse_pdf(
        pdf_path,
        start_page=start_page,
        checkpoint_file=checkpoint_file,
        output_json=output_json
    )

    # Merge with existing cases if resuming
    if resume and existing_cases:
        # Create a set of existing case IDs
        existing_ids = {c["case_id"] for c in existing_cases}

        # Add only new cases
        for case in new_cases:
            if case["case_id"] not in existing_ids:
                existing_cases.append(case)

        # Save merged results
        with open(output_json, "w") as f:
            json.dump(existing_cases, f, indent=2)

        if verbose:
            print(f"Merged: {len(existing_cases)} total cases")

        return existing_cases

    return new_cases


def flatten_cases_to_records(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten nested case structure to one row per plaintiff.

    This is useful for creating DataFrames for analysis or ML.

    Args:
        cases: List of case dictionaries from parser

    Returns:
        List of flattened records (one per plaintiff)

    Example:
        import pandas as pd

        cases = parse_compendium(...)
        records = flatten_cases_to_records(cases)
        df = pd.DataFrame(records)
    """
    rows = []

    for case in cases:
        base = {
            'case_id': case.get('case_id'),
            'case_name': case.get('case_name'),
            'plaintiff_name': case.get('plaintiff_name'),
            'defendant_name': case.get('defendant_name'),
            'year': case.get('year'),
            'category': case.get('category'),
            'court': case.get('court'),
            'citations': ', '.join(case.get('citations', [])) if case.get('citations') else None,
            'judges': ', '.join(case.get('judges', [])) if case.get('judges') else None,
            'comments': case.get('comments'),
            'num_plaintiffs': len(case.get('plaintiffs', [])),
            'has_fla_claims': bool(case.get('family_law_act_claims')),
            'total_fla_amount': sum(
                c.get('amount', 0) or 0
                for c in case.get('family_law_act_claims', [])
            )
        }

        plaintiffs = case.get('plaintiffs', [])
        if not plaintiffs:
            # No plaintiffs, add base row
            rows.append(base)
        else:
            # One row per plaintiff
            for p in plaintiffs:
                row = base.copy()
                row.update({
                    'plaintiff_id': p.get('plaintiff_id'),
                    'sex': p.get('sex'),
                    'age': p.get('age'),
                    'non_pecuniary_damages': p.get('non_pecuniary_damages'),
                    'is_provisional': p.get('is_provisional'),
                    'injuries': ', '.join(p.get('injuries', [])) if p.get('injuries') else None,
                    'num_injuries': len(p.get('injuries', [])),
                    'other_damages_total': sum(
                        d.get('amount', 0) or 0
                        for d in p.get('other_damages', [])
                    )
                })
                rows.append(row)

    return rows


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python damages_parser_gemini.py <pdf_path> <api_key> [output_json]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    api_key = sys.argv[2]
    output_json = sys.argv[3] if len(sys.argv) > 3 else "damages_full.json"

    print(f"Parsing {pdf_path}...")
    cases = parse_compendium(pdf_path, api_key, output_json)
    print(f"\nDone! Parsed {len(cases)} cases")
    print(f"Saved to {output_json}")
