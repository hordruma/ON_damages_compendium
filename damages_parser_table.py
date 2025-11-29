"""
Ontario Damages Compendium Parser - Table-Based Extraction

This is a more efficient alternative to damages_parser_azure.py that:
- Extracts tables directly from PDF using pdfplumber
- Processes rows one at a time (cheaper, faster)
- Uses column headers to pre-label data
- Deterministically merges rows without citations into previous case
- Tracks body region from section headers

Advantages over full-page extraction:
- 10-50x cheaper (sends only row text, not full pages)
- Faster processing (smaller prompts)
- More reliable (structured input)
- Works better with lighter models (5-nano, 4o-mini)
- Simpler merging logic (no fuzzy matching needed)
- Pre-labeled columns (plaintiff, defendant, year, etc.)

Usage:
    from damages_parser_table import parse_compendium_tables

    cases = parse_compendium_tables(
        "2024damagescompendium.pdf",
        endpoint="https://your-resource.openai.azure.com/",
        api_key="your-api-key",
        model="gpt-5-nano"  # Cheaper models work fine!
    )
"""

import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import pdfplumber
import requests
from collections import deque


class RateLimiter:
    """Rate limiter to control API requests per minute."""

    def __init__(self, requests_per_minute: int = 200):
        self.requests_per_minute = requests_per_minute
        self.request_times: deque = deque()
        self.window_seconds = 60.0

    def wait_if_needed(self):
        """Wait if necessary to stay within rate limits."""
        now = time.time()

        # Remove requests older than our window
        while self.request_times and self.request_times[0] < now - self.window_seconds:
            self.request_times.popleft()

        # If we're at the limit, wait
        if len(self.request_times) >= self.requests_per_minute:
            oldest_request = self.request_times[0]
            sleep_time = (oldest_request + self.window_seconds) - now
            if sleep_time > 0:
                time.sleep(sleep_time)
                now = time.time()
                while self.request_times and self.request_times[0] < now - self.window_seconds:
                    self.request_times.popleft()

        # Record this request
        self.request_times.append(time.time())


class TableBasedParser:
    """
    Parses damages compendium using table extraction.

    Much more efficient than full-page text extraction:
    - Processes one row at a time
    - Pre-labeled columns
    - Deterministic merging
    """

    # Row parsing prompt - much simpler and cheaper than full-page
    ROW_PROMPT = """Parse this table row from a legal damages compendium.

Body Region/Category: {section}
Table Columns: {columns}
Row Data: {row_data}

Extract the following information and return as JSON:
{{
  "case_name": "Full case name (plaintiff v. defendant)" or null,
  "plaintiff_name": "Plaintiff name only" or null,
  "defendant_name": "Defendant name only" or null,
  "year": year as integer or null,
  "citation": "Citation string" or null,
  "court": "Court name" or null,
  "judge": "Judge name (normalized, without J./J.A.)" or null,
  "sex": "M" or "F" or null,
  "age": age as integer or null,
  "non_pecuniary_damages": amount in dollars (number, no $ or commas) or null,
  "is_provisional": true/false or null,
  "injuries": ["injury1", "injury2"] or [],
  "other_damages": [{{"type": "future_loss_of_income|past_loss_of_income|cost_of_future_care|housekeeping_capacity|other", "amount": number, "description": "text"}}] or [],
  "comments": "Additional notes" or null,
  "is_continuation": true if this row lacks case_name/citation (continuation of previous case), false otherwise
}}

IMPORTANT:
- Set "is_continuation": true if this row has no case name or citation (it's continuing the previous case)
- Normalize judge names: remove "J.", "J.A.", "C.J." suffixes
- Parse monetary amounts as numbers only (no $ or commas)
- Return only valid JSON, no other text

Return the JSON object:"""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str,
        api_version: str = "2024-02-15-preview",
        verbose: bool = True,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize the table-based parser.

        Args:
            endpoint: Azure endpoint URL
            api_key: Azure API key
            model: Model deployment name
            api_version: Azure API version
            verbose: Whether to print progress
            rate_limiter: Optional rate limiter
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.api_version = api_version
        self.verbose = verbose
        self.rate_limiter = rate_limiter
        self.errors: List[Dict[str, Any]] = []

        # Detect model type
        self.is_claude = 'claude' in model.lower()
        model_lower = model.lower()
        self.uses_max_completion_tokens = any([
            'gpt-4o' in model_lower,
            'gpt-5' in model_lower,
            'o1-' in model_lower,
            'o3-' in model_lower,
            'chatgpt-4o' in model_lower
        ])

        # Temperature settings
        if any(x in model_lower for x in ['claude-3-5', '3.5-sonnet', '5-sonnet', 'sonnet-3-5', 'nano']):
            self.temperature = 1.0
        else:
            self.temperature = 0.1

    def _call_api(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Call Azure API with retry logic."""
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        # Determine URL based on model type
        if self.is_claude:
            url = f"{self.endpoint}/models/{self.model}/chat/completions"
        else:
            url = f"{self.endpoint}/openai/deployments/{self.model}/chat/completions?api-version={self.api_version}"

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
        }

        if self.uses_max_completion_tokens:
            payload["max_completion_tokens"] = 2048  # Rows are small, don't need much
        else:
            payload["max_tokens"] = 2048

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=60)

                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    return None

                elif response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    wait_time = int(retry_after) if retry_after and retry_after.isdigit() else 1
                    if self.verbose:
                        print(f"  Rate limit, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                else:
                    if self.verbose:
                        print(f"  API error {response.status_code}: {response.text}")
                    return None

            except Exception as e:
                if self.verbose:
                    print(f"  Request error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None

        return None

    def detect_section_header(self, page_text: str) -> str:
        """
        Detect body region section from page text.

        Looks for common section headers like:
        - HEAD
        - BRAIN & SKULL
        - SPINE
        - CERVICAL SPINE
        - etc.
        """
        if not page_text:
            return "UNKNOWN"

        # Common section patterns (uppercase headings)
        sections = [
            "BRAIN & SKULL", "BRAIN AND SKULL",
            "HEAD",
            "CERVICAL SPINE",
            "THORACIC SPINE",
            "LUMBAR SPINE",
            "SPINE",
            "NECK",
            "SHOULDER",
            "ARM", "ARMS",
            "ELBOW",
            "WRIST", "HAND",
            "CHEST", "THORAX",
            "ABDOMEN",
            "PELVIS",
            "HIP",
            "KNEE",
            "LEG", "LEGS",
            "ANKLE", "FOOT",
            "PSYCHOLOGICAL", "PSYCHIATRIC",
            "MULTIPLE INJURIES",
            "SOFT TISSUE",
        ]

        # Look for section header in first 500 chars
        text_upper = page_text[:500].upper()

        for section in sections:
            # Look for standalone section name (not part of another word)
            pattern = r'\b' + re.escape(section) + r'\b'
            if re.search(pattern, text_upper):
                return section

        return "UNKNOWN"

    def extract_tables_from_page(self, page) -> List[List[List[str]]]:
        """
        Extract tables from a pdfplumber page object.

        Returns list of tables, where each table is a list of rows,
        and each row is a list of cell values.
        """
        try:
            tables = page.extract_tables()
            return tables if tables else []
        except Exception as e:
            if self.verbose:
                print(f"  Table extraction error: {e}")
            return []

    def parse_row(
        self,
        row: List[str],
        columns: List[str],
        section: str,
        page_number: int
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single table row.

        Args:
            row: List of cell values
            columns: List of column headers
            section: Body region/section name
            page_number: Page number (for logging)

        Returns:
            Parsed row data or None if parsing fails
        """
        # Format row data for prompt
        row_data = []
        for i, (col, val) in enumerate(zip(columns, row)):
            if val and val.strip():
                row_data.append(f"{col}: {val.strip()}")

        if not row_data:
            return None

        row_data_str = "\n".join(row_data)
        columns_str = ", ".join(columns)

        prompt = self.ROW_PROMPT.format(
            section=section,
            columns=columns_str,
            row_data=row_data_str
        )

        response = self._call_api(prompt)

        if response:
            # Extract JSON from response
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                response = json_match.group(1)

            try:
                data = json.loads(response)
                data['source_page'] = page_number
                data['category'] = section
                return data
            except json.JSONDecodeError as e:
                if self.verbose:
                    print(f"  JSON parse error: {e}")
                return None

        return None

    def merge_continuation_row(self, case: Dict[str, Any], row_data: Dict[str, Any]) -> None:
        """
        Merge a continuation row into an existing case.

        Continuation rows lack case name/citation but have additional
        damages, injuries, or comments.
        """
        # Merge injuries
        if row_data.get('injuries'):
            existing_injuries = set(case.get('injuries', []))
            existing_injuries.update(row_data['injuries'])
            case['injuries'] = list(existing_injuries)

        # Merge other_damages
        if row_data.get('other_damages'):
            case.setdefault('other_damages', []).extend(row_data['other_damages'])

        # Append comments
        if row_data.get('comments'):
            existing_comments = case.get('comments', '')
            if existing_comments:
                case['comments'] = f"{existing_comments} | {row_data['comments']}"
            else:
                case['comments'] = row_data['comments']

        # Update damages if higher
        new_npd = row_data.get('non_pecuniary_damages')
        if new_npd is not None:
            existing_npd = case.get('non_pecuniary_damages')
            if existing_npd is None or new_npd > existing_npd:
                case['non_pecuniary_damages'] = new_npd

    def parse_pdf(
        self,
        pdf_path: str,
        start_page: int = 1,
        end_page: Optional[int] = None,
        output_json: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse PDF using table extraction.

        Args:
            pdf_path: Path to PDF
            start_page: Starting page (1-indexed)
            end_page: Ending page (None = all)
            output_json: Optional path to save results

        Returns:
            List of parsed cases
        """
        all_cases = []
        current_case = None
        total_rows = 0
        continuation_rows = 0

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            if end_page is None:
                end_page = total_pages

            if self.verbose:
                print(f"Parsing pages {start_page} to {end_page} of {total_pages}")
                print(f"Using table-based extraction (row-by-row)")
                print(f"Model: {self.model}")

            for page_num in range(start_page - 1, end_page):  # 0-indexed
                page = pdf.pages[page_num]
                page_number = page_num + 1  # 1-indexed for display

                if self.verbose:
                    print(f"\nPage {page_number}/{end_page}...", end=" ")

                # Detect section
                page_text = page.extract_text() or ""
                section = self.detect_section_header(page_text)

                # Extract tables
                tables = self.extract_tables_from_page(page)

                if not tables:
                    if self.verbose:
                        print("no tables")
                    continue

                page_rows = 0
                page_new = 0
                page_merged = 0

                # Process each table
                for table_idx, table in enumerate(tables):
                    if len(table) < 2:  # Need header + at least 1 row
                        continue

                    # First row is usually header
                    header = [str(cell).strip() if cell else "" for cell in table[0]]

                    # Skip if header looks wrong
                    if not any(h.lower() in ['plaintiff', 'case', 'year'] for h in header):
                        continue

                    # Process data rows
                    for row in table[1:]:
                        row_cells = [str(cell).strip() if cell else "" for cell in row]

                        # Skip empty rows
                        if not any(row_cells):
                            continue

                        page_rows += 1
                        total_rows += 1

                        # Parse row
                        row_data = self.parse_row(row_cells, header, section, page_number)

                        if not row_data:
                            continue

                        # Check if continuation row
                        if row_data.get('is_continuation') and current_case:
                            # Merge into current case
                            self.merge_continuation_row(current_case, row_data)
                            page_merged += 1
                            continuation_rows += 1
                        else:
                            # New case
                            if current_case:
                                all_cases.append(current_case)

                            current_case = row_data
                            page_new += 1

                if self.verbose:
                    print(f"{page_rows} rows, {page_new} new cases, {page_merged} merged (total: {len(all_cases)})")

                # Save incremental results
                if output_json and page_number % 10 == 0:
                    with open(output_json, 'w') as f:
                        json.dump(all_cases, f, indent=2)

            # Add final case
            if current_case:
                all_cases.append(current_case)

        if self.verbose:
            print(f"\n✓ Parsing complete")
            print(f"  Total rows processed: {total_rows}")
            print(f"  Continuation rows merged: {continuation_rows}")
            print(f"  Unique cases: {len(all_cases)}")

        # Save final results
        if output_json:
            with open(output_json, 'w') as f:
                json.dump(all_cases, f, indent=2)

        return all_cases


def parse_compendium_tables(
    pdf_path: str,
    endpoint: str,
    api_key: str,
    model: str,
    output_json: str = "damages_table_based.json",
    start_page: Optional[int] = None,
    end_page: Optional[int] = None,
    verbose: bool = True,
    requests_per_minute: int = 200
) -> List[Dict[str, Any]]:
    """
    Parse Ontario Damages Compendium using table extraction.

    This is more efficient than full-page parsing:
    - 10-50x cheaper (processes rows instead of full pages)
    - Faster (smaller prompts)
    - More reliable (structured input)
    - Works well with lighter models

    Args:
        pdf_path: Path to PDF
        endpoint: Azure endpoint
        api_key: Azure API key
        model: Model deployment name (gpt-5-nano works great!)
        output_json: Path to save results
        start_page: Starting page
        end_page: Ending page
        verbose: Print progress
        requests_per_minute: Rate limit

    Returns:
        List of parsed cases

    Example:
        cases = parse_compendium_tables(
            "2024damagescompendium.pdf",
            endpoint="https://your-resource.openai.azure.com/",
            api_key="your-key",
            model="gpt-5-nano"  # Cheaper model works fine!
        )
    """
    rate_limiter = RateLimiter(requests_per_minute) if requests_per_minute > 0 else None

    if verbose and rate_limiter:
        print(f"Rate limiting: {requests_per_minute} requests/minute")

    parser = TableBasedParser(
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        verbose=verbose,
        rate_limiter=rate_limiter
    )

    return parser.parse_pdf(
        pdf_path=pdf_path,
        start_page=start_page or 1,
        end_page=end_page,
        output_json=output_json
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print("Usage: python damages_parser_table.py <pdf_path> <endpoint> <api_key> <model> [output_json]")
        print("\nExample:")
        print('  python damages_parser_table.py 2024damagescompendium.pdf \\')
        print('    "https://your-resource.openai.azure.com/" \\')
        print('    "your-api-key" \\')
        print('    "gpt-5-nano" \\')  # Note: cheaper model!
        print('    "damages_table_based.json"')
        sys.exit(1)

    pdf_path = sys.argv[1]
    endpoint = sys.argv[2]
    api_key = sys.argv[3]
    model = sys.argv[4]
    output_json = sys.argv[5] if len(sys.argv) > 5 else "damages_table_based.json"

    print(f"Parsing {pdf_path} using table extraction...")
    cases = parse_compendium_tables(pdf_path, endpoint, api_key, model, output_json)
    print(f"\nDone! Parsed {len(cases)} cases")
    print(f"Saved to {output_json}")
