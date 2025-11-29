"""
Ontario Damages Compendium Parser using Azure AI Foundry.

This module provides tools to parse the Ontario Damages Compendium PDF
using Azure OpenAI (GPT-4o, GPT-4) or Claude models via Azure AI Foundry.

Features:
- PDF text extraction with pdfplumber
- Structured data extraction using Azure OpenAI or Claude
- Intelligent case merging for duplicates across multiple pages/sections
- Sliding window context for multi-page cases
- Checkpoint/resume functionality for long-running parses
- Multi-plaintiff support
- Family Law Act claims extraction
- Comprehensive error handling and retry logic
- Rate limiting to stay within Azure API limits

Case Merging Behavior:
When a case appears in multiple locations (e.g., different body region tables),
the parser automatically merges all instances to create a complete record:
- Combines all body regions/categories (e.g., HEAD + SPINE)
- Merges all injuries from all instances
- Preserves all damages and claims
- Tracks all source pages where the case appeared

Usage:
    from damages_parser_azure import parse_compendium

    cases = parse_compendium(
        "2024damagescompendium.pdf",
        endpoint="https://your-resource.openai.azure.com/",
        api_key="your-api-key",
        model="gpt-4o"
    )

    # Parse with custom rate limit (Azure default is 200 req/min)
    cases = parse_compendium(
        "2024damagescompendium.pdf",
        endpoint="https://your-resource.openai.azure.com/",
        api_key="your-api-key",
        model="gpt-4o",
        requests_per_minute=188  # Stay under Azure's 200 req/min limit
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
from typing import List, Dict, Any, Optional, Set
import pdfplumber
import requests
from difflib import SequenceMatcher
from collections import deque


class RateLimiter:
    """
    Rate limiter to control API requests per minute.

    Uses a sliding window approach to track requests and ensure
    we don't exceed the specified rate limit.
    """

    def __init__(self, requests_per_minute: int = 200):
        """
        Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.request_times: deque = deque()
        self.window_seconds = 60.0

    def wait_if_needed(self):
        """
        Wait if necessary to stay within rate limits.

        This method should be called before making each API request.
        It will automatically sleep if we're approaching the rate limit.
        """
        now = time.time()

        # Remove requests older than our window
        while self.request_times and self.request_times[0] < now - self.window_seconds:
            self.request_times.popleft()

        # If we're at the limit, wait until the oldest request falls out of the window
        if len(self.request_times) >= self.requests_per_minute:
            oldest_request = self.request_times[0]
            sleep_time = (oldest_request + self.window_seconds) - now
            if sleep_time > 0:
                time.sleep(sleep_time)
                # Clean up old requests after sleeping
                now = time.time()
                while self.request_times and self.request_times[0] < now - self.window_seconds:
                    self.request_times.popleft()

        # Record this request
        self.request_times.append(time.time())


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

CRITICAL INSTRUCTIONS:
1. Look for section headings at the top of the page (like "HEAD", "SPINE", "ARMS", etc.) - this tells you the region/category
2. In case names, plaintiff comes BEFORE "v." and defendant comes AFTER "v."
   - Example: "Smith v. Jones" means Smith is plaintiff, Jones is defendant
   - NEVER list the defendant as the plaintiff
3. For multiple plaintiffs in the same case, create ONE case with multiple plaintiff objects
4. Normalize judge names by removing titles like "J.", "J.A.", etc. at the end
   - Example: "Abella J.", "Abella J.A.", "Abella" should all be normalized to "Abella"
5. Properly categorize "other damages" by type:
   - "future_loss_of_income" for future income loss
   - "past_loss_of_income" for past income loss
   - "cost_of_future_care" for future care costs
   - "housekeeping_capacity" for loss of housekeeping
   - "other" only if it doesn't fit above categories

Return a JSON array of cases. Each case should have:
- case_name: Full case name (plaintiff v. defendant)
- plaintiff_name: Plaintiff name only (before "v.")
- defendant_name: Defendant name only (after "v.")
- year: Year of decision (integer)
- category: Category from page heading (e.g., "HEAD", "SPINE", "ARMS") - extract from the page section title
- region: More specific region if mentioned (e.g., "CERVICAL SPINE", "BRAIN & SKULL")
- court: Court name
- citations: Array of citation strings
- judges: Array of judge names (normalized, without titles like J., J.A.)
- plaintiffs: Array of plaintiff objects, each with:
  - plaintiff_id: "P1", "P2", etc. for multiple plaintiffs in same case
  - sex: "M" or "F"
  - age: Age in years (integer)
  - non_pecuniary_damages: Amount in dollars (float)
  - is_provisional: true/false if damages are provisional
  - injuries: Array of injury descriptions
  - other_damages: Array of {{type, amount, description}} objects where type is one of: future_loss_of_income, past_loss_of_income, cost_of_future_care, housekeeping_capacity, other
  - comments: Any additional notes or comments specific to this plaintiff
- family_law_act_claims: Array of {{description, amount, category}} objects

Important:
- If multiple plaintiffs exist in ONE case, create ONE case object with multiple items in the plaintiffs array
- DO NOT create duplicate cases for the same legal matter
- Parse all monetary amounts as numbers (no $ or commas)
- If information is not present, use null
- Return empty array [] if no cases on this page
- Normalize all judge names by removing trailing titles

Page text:
{page_text}

Return only the JSON array, no other text."""

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
        Initialize the parser.

        Args:
            endpoint: Azure OpenAI endpoint (e.g., "https://your-resource.openai.azure.com/")
            api_key: Azure API key
            model: Model deployment name (e.g., "gpt-4o", "claude-3-5-sonnet")
            api_version: Azure OpenAI API version
            verbose: Whether to print progress messages
            rate_limiter: Optional rate limiter to control API request rate
        """
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.api_version = api_version
        self.verbose = verbose
        self.rate_limiter = rate_limiter
        self.errors: List[Dict[str, Any]] = []

        # Detect if using Azure OpenAI or Azure AI Foundry (Claude)
        self.is_claude = 'claude' in model.lower()

        # Detect if model uses max_completion_tokens (newer models) vs max_tokens (older models)
        # Newer models (GPT-4o, GPT-5, o1, o3 series) use max_completion_tokens
        model_lower = model.lower()
        self.uses_max_completion_tokens = any([
            'gpt-4o' in model_lower,
            'gpt-5' in model_lower,
            'o1-' in model_lower,
            'o3-' in model_lower,
            'chatgpt-4o' in model_lower
        ])

        # Set appropriate temperature based on model
        # Some models like Claude 3.5 Sonnet only support temperature=1.0
        if any(x in model_lower for x in ['claude-3-5', '3.5-sonnet', '5-sonnet', 'sonnet-3-5', 'nano']):
            self.temperature = 1.0
        else:
            self.temperature = 0.1  # Low temperature for consistent extraction

    def _call_azure_openai(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """
        Call Azure OpenAI API with retry logic.

        Args:
            prompt: The prompt to send
            max_retries: Maximum number of retries on failure

        Returns:
            Response text or None if all retries failed
        """
        # Apply rate limiting before making the request
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

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
            "temperature": self.temperature,
        }

        # Use correct token parameter based on model
        if self.uses_max_completion_tokens:
            payload["max_completion_tokens"] = 8192
        else:
            payload["max_tokens"] = 8192

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    return None

                elif response.status_code == 429:  # Rate limit
                    # Check for Retry-After header, otherwise wait 1 second
                    retry_after = response.headers.get('Retry-After')
                    if retry_after and retry_after.isdigit():
                        wait_time = int(retry_after)
                    else:
                        wait_time = 1  # Fixed wait time instead of exponential backoff
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
        # Apply rate limiting before making the request
        if self.rate_limiter:
            self.rate_limiter.wait_if_needed()

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
            "temperature": self.temperature,
        }

        # Use correct token parameter based on model
        if self.uses_max_completion_tokens:
            payload["max_completion_tokens"] = 8192
        else:
            payload["max_tokens"] = 8192

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=120)

                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        return result["choices"][0]["message"]["content"]
                    return None

                elif response.status_code == 429:  # Rate limit
                    # Check for Retry-After header, otherwise wait 1 second
                    retry_after = response.headers.get('Retry-After')
                    if retry_after and retry_after.isdigit():
                        wait_time = int(retry_after)
                    else:
                        wait_time = 1  # Fixed wait time instead of exponential backoff
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

    @staticmethod
    def normalize_judge_name(judge_name: str) -> str:
        """
        Normalize judge names by removing titles and standardizing format.

        Args:
            judge_name: Raw judge name

        Returns:
            Normalized judge name
        """
        if not judge_name:
            return ""

        # Remove common titles and suffixes
        name = judge_name.strip()

        # Remove trailing titles (J., J.A., C.J., etc.)
        name = re.sub(r',?\s*(J\.A\.|J\.|C\.J\.|C\.J\.O\.|C\.J\.C\.)$', '', name, flags=re.IGNORECASE)

        # Remove "The Honourable", "Hon.", etc. at start
        name = re.sub(r'^(The\s+)?(Hon\.?|Honourable)\s+', '', name, flags=re.IGNORECASE)

        # Standardize spacing
        name = re.sub(r'\s+', ' ', name).strip()

        return name

    @staticmethod
    def similar_strings(s1: str, s2: str, threshold: float = 0.85) -> bool:
        """
        Check if two strings are similar (for deduplication).

        Args:
            s1: First string
            s2: Second string
            threshold: Similarity threshold (0-1)

        Returns:
            True if strings are similar enough
        """
        if not s1 or not s2:
            return False
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio() >= threshold

    @staticmethod
    def _normalize_case_key(case_name: str, year: Optional[int]) -> str:
        """
        Create a normalized key for case lookup.

        Args:
            case_name: The case name
            year: The case year

        Returns:
            Normalized key for hash index lookup
        """
        if not case_name:
            return ""
        # Normalize: lowercase, remove extra spaces, strip
        normalized = re.sub(r'\s+', ' ', case_name.lower().strip())
        # Remove common punctuation variations
        normalized = normalized.replace(',', '').replace('.', '')
        year_str = str(year) if year else ""
        return f"{normalized}_{year_str}"

    def _update_indices(
        self,
        case: Dict[str, Any],
        case_index: int,
        case_id_index: Dict[str, int],
        name_year_index: Dict[str, int],
        citation_index: Dict[str, Set[int]]
    ) -> None:
        """
        Update all hash indices when adding a new case.

        Args:
            case: The case to index
            case_index: The index position of the case in all_cases list
            case_id_index: Index mapping case_id to position
            name_year_index: Index mapping normalized name+year to position
            citation_index: Index mapping citations to set of case positions
        """
        # Index by case_id
        case_id = case.get("case_id")
        if case_id:
            case_id_index[case_id] = case_index

        # Index by normalized name+year
        case_name = case.get("case_name", "")
        year = case.get("year")
        key = self._normalize_case_key(case_name, year)
        if key:
            name_year_index[key] = case_index

        # Index by citations
        citations = case.get("citations", [])
        for citation in citations:
            if citation:
                if citation not in citation_index:
                    citation_index[citation] = set()
                citation_index[citation].add(case_index)

    def find_duplicate_case_fast(
        self,
        new_case: Dict[str, Any],
        all_cases: List[Dict[str, Any]],
        case_id_index: Dict[str, int],
        name_year_index: Dict[str, int],
        citation_index: Dict[str, Set[int]]
    ) -> Optional[int]:
        """
        Fast O(1) duplicate detection using hash indices.

        Args:
            new_case: New case to check
            all_cases: List of existing cases
            case_id_index: Hash index for case IDs
            name_year_index: Hash index for case name+year
            citation_index: Hash index for citations

        Returns:
            Index of matching case, or None if no duplicate found
        """
        # 1. Check by case_id (fastest)
        case_id = new_case.get("case_id")
        if case_id and case_id in case_id_index:
            return case_id_index[case_id]

        # 2. Check by exact normalized name+year match
        case_name = new_case.get("case_name", "")
        year = new_case.get("year")
        key = self._normalize_case_key(case_name, year)
        if key and key in name_year_index:
            return name_year_index[key]

        # 3. Check by citation overlap
        new_citations = set(new_case.get("citations", []))
        if new_citations:
            for citation in new_citations:
                if citation in citation_index:
                    # Return first matching case with overlapping citation
                    case_indices = citation_index[citation]
                    if case_indices:
                        return min(case_indices)  # Return earliest match

        # 4. Fall back to fuzzy matching (rare, only for edge cases)
        # This handles typos or slight variations not caught by normalization
        new_name = new_case.get('case_name', '')
        new_year = new_case.get('year')

        if new_name and new_year:
            # Only check cases with same year for efficiency
            for idx, existing in enumerate(all_cases):
                existing_year = existing.get('year')
                if new_year == existing_year:
                    existing_name = existing.get('case_name', '')
                    if self.similar_strings(new_name, existing_name):
                        return idx

        return None

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
                # Post-process each case
                for case in cases:
                    self._post_process_case(case)
                return cases
            elif isinstance(cases, dict):
                self._post_process_case(cases)
                return [cases]
            else:
                return []
        except json.JSONDecodeError as e:
            if self.verbose:
                print(f"JSON parse error: {e}")
            return []

    def _post_process_case(self, case: Dict[str, Any]) -> None:
        """
        Post-process a case to normalize data.

        Args:
            case: Case dictionary to modify in-place
        """
        # Normalize judge names
        if 'judges' in case and case['judges']:
            case['judges'] = [self.normalize_judge_name(j) for j in case['judges'] if j]
            # Remove empty strings
            case['judges'] = [j for j in case['judges'] if j]

        # Ensure plaintiff/defendant are properly separated
        if 'case_name' in case and case['case_name']:
            case_name = case['case_name']
            # Look for " v. " or " v " pattern
            if ' v. ' in case_name or ' v ' in case_name:
                parts = re.split(r'\s+v\.?\s+', case_name, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) == 2:
                    if not case.get('plaintiff_name'):
                        case['plaintiff_name'] = parts[0].strip()
                    if not case.get('defendant_name'):
                        case['defendant_name'] = parts[1].strip()

        # Ensure "other_damages" have proper types
        if 'plaintiffs' in case:
            for plaintiff in case['plaintiffs']:
                if 'other_damages' in plaintiff and plaintiff['other_damages']:
                    for damage in plaintiff['other_damages']:
                        if 'type' not in damage or not damage['type']:
                            damage['type'] = 'other'

    def parse_page(self, page_number: int, page_text: str, previous_page_text: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse a single page to extract case data with optional context from previous page.

        Uses a sliding window approach to handle cases that span multiple pages.
        When previous_page_text is provided, the LLM can see continuations and
        properly associate orphaned content (like comments, liability info) with
        cases from the previous page.

        Args:
            page_number: Page number (for logging)
            page_text: Extracted text from the current page
            previous_page_text: Optional text from previous page for context

        Returns:
            List of case dictionaries
        """
        if not page_text or len(page_text.strip()) < 50:
            return []

        # Build context window if previous page provided
        if previous_page_text:
            # Combine previous and current page with clear separator
            combined_text = (
                f"=== PREVIOUS PAGE (for context) ===\n"
                f"{previous_page_text}\n\n"
                f"=== CURRENT PAGE {page_number} (extract cases from here) ===\n"
                f"{page_text}"
            )
            prompt = self.EXTRACTION_PROMPT.format(page_text=combined_text)
        else:
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

    def find_duplicate_case(self, new_case: Dict[str, Any], existing_cases: List[Dict[str, Any]]) -> Optional[int]:
        """
        Find if a case is a duplicate and return its index.

        Args:
            new_case: New case to check
            existing_cases: List of existing cases

        Returns:
            Index of matching case, or None if no duplicate found
        """
        new_name = new_case.get('case_name', '')
        new_year = new_case.get('year')

        for idx, existing in enumerate(existing_cases):
            existing_name = existing.get('case_name', '')
            existing_year = existing.get('year')

            # Same year and similar case name
            if new_year == existing_year and self.similar_strings(new_name, existing_name):
                return idx

            # Check citation overlap
            new_citations = set(new_case.get('citations', []))
            existing_citations = set(existing.get('citations', []))
            if new_citations and existing_citations and new_citations & existing_citations:
                return idx

        return None

    def merge_cases(self, existing_case: Dict[str, Any], new_case: Dict[str, Any]) -> None:
        """
        Merge information from a duplicate case into an existing case.

        This is critical for cases appearing in multiple body region tables,
        ensuring all injuries, regions, and damages are captured.

        Args:
            existing_case: The case to merge into (modified in-place)
            new_case: The duplicate case with potentially new information
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
        existing_category = existing_case.get('category')
        if existing_category is None:
            existing_categories = set()
        elif isinstance(existing_category, str):
            existing_categories = set(filter(None, [existing_category]))
        else:  # list or other iterable
            existing_categories = set(filter(None, existing_category))

        new_category = new_case.get('category')
        if new_category:
            if isinstance(new_category, str):
                existing_categories.add(new_category)
            elif isinstance(new_category, list):
                existing_categories.update(new_category)
        if existing_categories:
            existing_case['category'] = list(existing_categories)

        # Merge regions
        existing_region = existing_case.get('region')
        if existing_region is None:
            existing_regions = set()
        elif isinstance(existing_region, str):
            existing_regions = set(filter(None, [existing_region]))
        else:  # list or other iterable
            existing_regions = set(filter(None, existing_region))

        new_region = new_case.get('region')
        if new_region:
            if isinstance(new_region, str):
                existing_regions.add(new_region)
            elif isinstance(new_region, list):
                existing_regions.update(new_region)
        if existing_regions:
            existing_case['region'] = list(existing_regions)

        # Merge citations
        existing_citations = set(existing_case.get('citations') or [])
        new_citations = set(new_case.get('citations') or [])
        merged_citations = existing_citations | new_citations
        if merged_citations:
            existing_case['citations'] = list(merged_citations)

        # Merge judges
        existing_judges = set(existing_case.get('judges') or [])
        new_judges = set(new_case.get('judges') or [])
        merged_judges = existing_judges | new_judges
        if merged_judges:
            existing_case['judges'] = list(merged_judges)

        # Merge plaintiffs - match by plaintiff_id or merge all
        existing_plaintiffs = existing_case.get('plaintiffs') or []
        new_plaintiffs = new_case.get('plaintiffs') or []

        if existing_plaintiffs and new_plaintiffs:
            # Create a mapping of existing plaintiffs by ID
            existing_by_id = {p.get('plaintiff_id'): p for p in existing_plaintiffs if p.get('plaintiff_id')}

            for new_plaintiff in new_plaintiffs:
                plaintiff_id = new_plaintiff.get('plaintiff_id')

                if plaintiff_id and plaintiff_id in existing_by_id:
                    # Merge plaintiff data
                    existing_plaintiff = existing_by_id[plaintiff_id]

                    # Merge injuries
                    existing_injuries = set(existing_plaintiff.get('injuries') or [])
                    new_injuries = set(new_plaintiff.get('injuries') or [])
                    merged_injuries = existing_injuries | new_injuries
                    if merged_injuries:
                        existing_plaintiff['injuries'] = list(merged_injuries)

                    # Merge other_damages
                    existing_damages = existing_plaintiff.get('other_damages') or []
                    new_damages = new_plaintiff.get('other_damages') or []

                    # Create a set of existing damage types to avoid true duplicates
                    # Use tuple keys with None handling for safe comparison
                    existing_damage_keys = {(d.get('type') if isinstance(d, dict) else None,
                                            d.get('amount') if isinstance(d, dict) else None)
                                           for d in existing_damages if d}

                    for new_damage in new_damages:
                        if not new_damage or not isinstance(new_damage, dict):
                            continue
                        damage_key = (new_damage.get('type'), new_damage.get('amount'))
                        if damage_key not in existing_damage_keys:
                            existing_damages.append(new_damage)
                            existing_damage_keys.add(damage_key)

                    # Update non-pecuniary damages if higher (take max)
                    existing_npd = existing_plaintiff.get('non_pecuniary_damages')
                    new_npd = new_plaintiff.get('non_pecuniary_damages')
                    # Safely handle None values and ensure numeric comparison
                    try:
                        if new_npd is not None and (existing_npd is None or (isinstance(new_npd, (int, float)) and isinstance(existing_npd, (int, float)) and new_npd > existing_npd)):
                            existing_plaintiff['non_pecuniary_damages'] = new_npd
                            # Also update provisional flag if present
                            if 'is_provisional' in new_plaintiff:
                                existing_plaintiff['is_provisional'] = new_plaintiff['is_provisional']
                    except (TypeError, ValueError):
                        # If comparison fails, prefer the new value if it exists and existing doesn't
                        if new_npd is not None and existing_npd is None:
                            existing_plaintiff['non_pecuniary_damages'] = new_npd

                    # Merge comments for this plaintiff
                    existing_comments = existing_plaintiff.get('comments') or ''
                    new_comments = new_plaintiff.get('comments') or ''

                    if new_comments and new_comments not in existing_comments:
                        if existing_comments:
                            existing_plaintiff['comments'] = f"{existing_comments} | {new_comments}"
                        else:
                            existing_plaintiff['comments'] = new_comments
                else:
                    # New plaintiff - add them
                    existing_plaintiffs.append(new_plaintiff)
        elif new_plaintiffs and not existing_plaintiffs:
            # No existing plaintiffs, use new ones
            existing_case['plaintiffs'] = new_plaintiffs

        # Merge Family Law Act claims
        existing_fla = existing_case.get('family_law_act_claims') or []
        new_fla = new_case.get('family_law_act_claims') or []

        # Create a set of existing FLA claim keys to avoid duplicates
        # Use tuple keys with None handling for safe comparison
        existing_fla_keys = {(f.get('category') if isinstance(f, dict) else None,
                             f.get('amount') if isinstance(f, dict) else None,
                             f.get('description') if isinstance(f, dict) else None)
                            for f in existing_fla if f}

        for new_claim in new_fla:
            if not new_claim or not isinstance(new_claim, dict):
                continue
            claim_key = (new_claim.get('category'), new_claim.get('amount'), new_claim.get('description'))
            if claim_key not in existing_fla_keys:
                existing_fla.append(new_claim)
                existing_fla_keys.add(claim_key)

        if existing_fla:
            existing_case['family_law_act_claims'] = existing_fla

        # Update metadata fields if they're missing
        for field in ['court', 'plaintiff_name', 'defendant_name']:
            if not existing_case.get(field) and new_case.get(field):
                existing_case[field] = new_case[field]

    def parse_pdf(
        self,
        pdf_path: str,
        start_page: int = 1,
        end_page: Optional[int] = None,
        checkpoint_file: str = "parsing_checkpoint.json",
        output_json: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse the entire PDF or a range of pages with deduplication.

        Args:
            pdf_path: Path to PDF file
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (None = all pages)
            checkpoint_file: Path to save checkpoints
            output_json: Path to save results incrementally

        Returns:
            List of all parsed cases (deduplicated)
        """
        extractor = PDFTextExtractor(pdf_path)
        total_pages = extractor.get_page_count()

        if end_page is None:
            end_page = total_pages

        all_cases = []
        # Initialize hash indices for O(1) duplicate detection
        case_id_index: Dict[str, int] = {}  # case_id -> index
        name_year_index: Dict[str, int] = {}  # normalized_name_year -> index
        citation_index: Dict[str, Set[int]] = {}  # citation -> set of indices
        duplicates_found = 0

        if self.verbose:
            print(f"Parsing pages {start_page} to {end_page} of {total_pages}")
            print(f"Using model: {self.model}")
            print(f"Using sliding window for multi-page case handling")

        previous_page_text = None
        for page_num in range(start_page, end_page + 1):
            if self.verbose:
                print(f"\nPage {page_num}/{end_page}...", end=" ")

            # Extract text
            page_text = extractor.extract_page(page_num)
            if not page_text:
                if self.verbose:
                    print("(empty)")
                previous_page_text = None  # Reset context on empty page
                continue

            # Parse page with sliding window context
            page_cases = self.parse_page(page_num, page_text, previous_page_text)

            # Update sliding window - current page becomes previous for next iteration
            previous_page_text = page_text

            # Deduplicate and merge
            new_cases = 0
            merged_cases = 0
            for case in page_cases:
                # Generate unique ID if not present
                if "case_id" not in case or not case["case_id"]:
                    case_name = case.get('case_name', 'UNKNOWN')
                    year = case.get('year', 0)
                    case["case_id"] = f"{case_name}_{year}"

                # Check for duplicates using fast O(1) hash index lookup
                duplicate_idx = self.find_duplicate_case_fast(
                    case,
                    all_cases,
                    case_id_index,
                    name_year_index,
                    citation_index
                )

                if duplicate_idx is not None:
                    # Merge the duplicate case data (handles multi-page cases)
                    self.merge_cases(all_cases[duplicate_idx], case)
                    merged_cases += 1
                    duplicates_found += 1
                    # Update indices with any new information from merged case
                    self._update_indices(case, duplicate_idx, case_id_index, name_year_index, citation_index)
                else:
                    # New case - add it and update all indices
                    case_index = len(all_cases)
                    all_cases.append(case)
                    self._update_indices(case, case_index, case_id_index, name_year_index, citation_index)
                    new_cases += 1

            if self.verbose:
                msg = f"found {new_cases} new"
                if merged_cases > 0:
                    msg += f", merged {merged_cases}"
                msg += f" (total: {len(all_cases)}, {duplicates_found} duplicates processed)"
                print(msg)

            # Save checkpoint
            checkpoint = {
                "last_page_processed": page_num,
                "cases_count": len(all_cases),
                "duplicates_found": duplicates_found,
                "timestamp": time.time()
            }
            with open(checkpoint_file, "w") as f:
                json.dump(checkpoint, f, indent=2)

            # Save incremental results
            if output_json:
                with open(output_json, "w") as f:
                    json.dump(all_cases, f, indent=2)

        if self.verbose:
            print(f"\n✓ Parsing complete: {len(all_cases)} unique cases")
            print(f"  Duplicates merged: {duplicates_found}")
            if self.errors:
                print(f"  ⚠ {len(self.errors)} errors occurred")

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
    verbose: bool = True,
    requests_per_minute: int = 200
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
        requests_per_minute: Maximum API requests per minute (default: 200 for Azure)

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

        # Parse with custom rate limit
        cases = parse_compendium(
            "2024damagescompendium.pdf",
            endpoint="https://your-resource.openai.azure.com/",
            api_key="your-key",
            model="gpt-4o",
            requests_per_minute=188  # Stay under Azure's 200 req/min limit
        )
    """
    # Create rate limiter if requests_per_minute is specified
    rate_limiter = RateLimiter(requests_per_minute) if requests_per_minute > 0 else None

    if verbose and rate_limiter:
        print(f"Rate limiting enabled: {requests_per_minute} requests/minute")

    parser = DamagesCompendiumParser(endpoint, api_key, model, verbose=verbose, rate_limiter=rate_limiter)

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

    # Parse sequentially with sliding window context
    new_cases = parser.parse_pdf(
        pdf_path,
        start_page=actual_start_page,
        end_page=end_page,
        checkpoint_file=checkpoint_file,
        output_json=output_json
    )

    # Merge with existing cases if resuming
    if resume and existing_cases:
        # Create a mapping of existing cases by case_id for efficient lookup
        existing_by_id = {c["case_id"]: i for i, c in enumerate(existing_cases)}

        new_added = 0
        merged_on_resume = 0

        # Merge or add each new case
        for case in new_cases:
            case_id = case["case_id"]
            if case_id in existing_by_id:
                # Merge with existing case
                idx = existing_by_id[case_id]
                parser.merge_cases(existing_cases[idx], case)
                merged_on_resume += 1
            else:
                # New case - add it
                existing_cases.append(case)
                new_added += 1

        # Save merged results
        with open(output_json, "w") as f:
            json.dump(existing_cases, f, indent=2)

        if verbose:
            print(f"Resume merge: {new_added} new cases added, {merged_on_resume} cases merged")
            print(f"Total: {len(existing_cases)} cases")

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
