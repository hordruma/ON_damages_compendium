"""
Ontario Damages Compendium Parser using Azure AI Foundry.

This module provides tools to parse the Ontario Damages Compendium PDF
using Azure OpenAI (GPT-4o, GPT-4) or Claude models via Azure AI Foundry.

Features:
- PDF text extraction with pdfplumber
- Structured data extraction using Azure OpenAI or Claude
- Checkpoint/resume functionality for long-running parses
- Multi-plaintiff support
- Family Law Act claims extraction
- Comprehensive error handling

Usage:
    from damages_parser_azure import parse_compendium

    cases = parse_compendium(
        "2024damagescompendium.pdf",
        endpoint="https://your-resource.openai.azure.com/",
        api_key="your-api-key",
        model="gpt-4o"
    )

    # Resume from interruption
    cases = parse_compendium(
        "2024damagescompendium.pdf",
        endpoint="https://your-resource.openai.azure.com/",
        api_key="your-api-key",
        model="gpt-4o",
        resume=True
    )
"""

import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import pdfplumber
import requests


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
    Parses the Ontario Damages Compendium using Azure AI Foundry.

    Supports both Azure OpenAI (GPT-4o, GPT-4) and Claude models
    via Azure AI Foundry.
    """

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

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        api_version: str = "2024-02-15-preview",
        verbose: bool = True
    ):
        """
        Initialize the parser.

        Args:
            endpoint: Azure OpenAI endpoint (e.g., "https://your-resource.openai.azure.com/")
            api_key: Azure API key
            model: Model deployment name (e.g., "gpt-4o", "claude-3-5-sonnet")
            api_version: Azure OpenAI API version
            verbose: Whether to print progress messages
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.api_version = api_version
        self.verbose = verbose
        self.errors: List[Dict[str, Any]] = []

        # Detect if using Azure OpenAI or Azure AI Foundry (Claude)
        self.is_claude = 'claude' in model.lower()

    def _call_azure_openai(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call Azure OpenAI API with retry logic.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retries on failure

        Returns:
            Response text or None if all retries failed
        """
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        # Azure OpenAI endpoint format
        url = f"{self.endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # Low temperature for consistent extraction
            "max_tokens": 8192,
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
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

    def _call_azure_claude(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call Azure AI Foundry Claude API with retry logic.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retries on failure

        Returns:
            Response text or None if all retries failed
        """
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        # Azure AI Foundry endpoint format for Claude
        url = f"{self.endpoint}/models/{self.model}/chat/completions"

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 8192,
        }

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    return None

                elif response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
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

    def _call_api(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call the appropriate API based on model type.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retries on failure

        Returns:
            Response text or None if all retries failed
        """
        if self.is_claude:
            return self._call_azure_claude(prompt, max_retries)
        else:
            return self._call_azure_openai(prompt, max_retries)

    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Parse API JSON response.

        Args:
            response_text: Raw response text from API

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
        response = self._call_api(prompt)

        if response:
            cases = self._parse_response(response)
            # Add source page to each case
            for case in cases:
                case['source_page'] = page_number
            return cases
        else:
            self.errors.append({
                "page": page_number,
                "error": "Failed to get valid response from API"
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
            print(f"Using model: {self.model}")

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
                "last_page_processed": page_num,
                "cases_count": len(all_cases),
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
    endpoint: str,
    api_key: str,
    model: str,
    output_json: str = "damages_full.json",
    checkpoint_file: str = "parsing_checkpoint.json",
    resume: bool = False,
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    Parse the Ontario Damages Compendium PDF using Azure AI.

    This is the main entry point for parsing. It supports automatic
    checkpointing and resume functionality.

    Args:
        pdf_path: Path to the PDF file
        endpoint: Azure endpoint URL
        api_key: Azure API key
        model: Model deployment name
        output_json: Path to save parsed cases
        checkpoint_file: Path to checkpoint file
        resume: If True, resume from last checkpoint
        start_page: Starting page (overrides resume)
        end_page: Ending page
        verbose: Whether to print progress

    Returns:
        List of parsed case dictionaries

    Example:
        # Fresh parse with Azure OpenAI
        cases = parse_compendium(
            "2024damagescompendium.pdf",
            endpoint="https://your-resource.openai.azure.com/",
            api_key="your-key",
            model="gpt-4o"
        )

        # Resume after interruption
        cases = parse_compendium(
            "2024damagescompendium.pdf",
            endpoint="https://your-resource.openai.azure.com/",
            api_key="your-key",
            model="gpt-4o",
            resume=True
        )

        # Parse specific page range
        cases = parse_compendium(
            "2024damagescompendium.pdf",
            endpoint="https://your-resource.openai.azure.com/",
            api_key="your-key",
            model="gpt-4o",
            start_page=100,
            end_page=200
        )
    """
    parser = DamagesCompendiumParser(endpoint, api_key, model, verbose=verbose)

    actual_start_page = start_page if start_page else 1
    existing_cases = []

    # Check for resume
    if resume and not start_page:
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
            actual_start_page = max(1, checkpoint["last_page_processed"] - 1)

            if verbose:
                print(f"Resuming from page {actual_start_page}")
                print(f"Loaded {len(existing_cases)} existing cases")
        else:
            if verbose:
                print("No checkpoint found, starting fresh")

    # Parse
    new_cases = parser.parse_pdf(
        pdf_path,
        start_page=actual_start_page,
        end_page=end_page,
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


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("Usage: python damages_parser_azure.py <pdf_path> <endpoint> <api_key> <model> [output_json]")
        print("\nExample:")
        print('  python damages_parser_azure.py 2024damagescompendium.pdf \\')
        print('    "https://your-resource.openai.azure.com/" \\')
        print('    "your-api-key" \\')
        print('    "gpt-4o" \\')
        print('    "damages_full.json"')
        sys.exit(1)

    pdf_path = sys.argv[1]
    endpoint = sys.argv[2]
    api_key = sys.argv[3]
    model = sys.argv[4]
    output_json = sys.argv[5] if len(sys.argv) > 5 else "damages_full.json"

    print(f"Parsing {pdf_path}...")
    cases = parse_compendium(pdf_path, endpoint, api_key, model, output_json)
    print(f"\nDone! Parsed {len(cases)} cases")
    print(f"Saved to {output_json}")
