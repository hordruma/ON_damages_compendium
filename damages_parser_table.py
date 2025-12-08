"""
Ontario Damages Compendium Parser - Hybrid Camelot Stream+Lattice + LLM Approach

This parser uses a hybrid approach:
- STREAM mode: Captures section headers (Forearm, General, etc.) from row 0
- LATTICE mode: Extracts clean table structure with bordered cells
- LLM: Parses each row to handle complex cases and multi-plaintiff scenarios

Key features:
- Hybrid section detection: Stream finds sections, lattice parses data
- Row-by-row LLM processing (handles multi-plaintiff cases)
- Pre-labeled columns from table headers
- Deterministic continuation row merging
- Accurate anatomical category tracking

Advantages over full-page extraction:
- 10-50x cheaper (sends only row text, not full pages)
- More accurate section detection (no "General Damages" false positives)
- Better table structure parsing (lattice mode for borders)
- Handles complex cases (multiple plaintiffs in one cell)
- Faster processing (smaller prompts)
- Works with lighter models (gpt-4o-mini, gpt-5-nano)
- Simpler merging logic (no fuzzy matching needed)

Usage:
    from damages_parser_table import parse_compendium_tables

    cases = parse_compendium_tables(
        "2024damagescompendium.pdf",
        endpoint="https://your-resource.openai.azure.com/",
        api_key="your-api-key",
        model="gpt-5-nano"
    )
"""

import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import camelot
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

    # Row parsing prompt - uses structured column:value format for better LLM parsing
    ROW_PROMPT = """Parse this table row from a legal damages compendium.

ANATOMICAL CATEGORY: {section}

DATA FROM TABLE:
{row_data_formatted}

Call the extract_case_row function with the parsed data.

CRITICAL RULES:

1. CONTINUATION ROWS:
   - Set is_continuation: true ONLY if BOTH case name AND citation are missing/null
   - If there's a case name OR citation, it's a NEW case (is_continuation: false)

2. INJURY EXTRACTION (MOST IMPORTANT):
   - ALWAYS extract injuries from Comments, even if described narratively
   - Extract ALL injury descriptions from ANY text field
   - DO NOT leave injuries array empty if ANY injury description exists

3. MULTI-PLAINTIFF CASES:
   - Use plaintiffs array ONLY when truly MULTIPLE distinct plaintiffs
   - Each plaintiff MUST have a name (even if generic like "Plaintiff 2")
   - NEVER create plaintiff without plaintiff_name

4. FLA Claims:
   - FLA = Family Law Act claims for family members
   - Use gender-specific terms when clear (son/daughter, father/mother)
   - Mark is_fla_award: false for insurance/subrogation
   - Mark is_fla_award: true for true FLA claims
   - CRITICAL: Extract Comments field EVEN FOR FLA-ONLY CASES
   - For FLA cases, comments describe the underlying injury/circumstances (e.g., "No liability", "Alleged medical negligence")
   - DO NOT leave comments empty if the Comments column has text

5. DATA QUALITY:
   - Parse monetary amounts as numbers only (no $ or commas)
   - Extract judge LAST NAME ONLY
   - Preserve hyphenated surnames (e.g., 'Harrison-Young')
"""

    # Tool definition for structured extraction
    CASE_EXTRACTION_TOOL = {
        "type": "function",
        "function": {
            "name": "extract_case_row",
            "description": "Extract structured case information from a legal damages compendium table row",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_name": {
                        "type": ["string", "null"],
                        "description": "Full case name (plaintiff v. defendant)"
                    },
                    "plaintiff_name": {
                        "type": ["string", "null"],
                        "description": "Plaintiff name only (primary plaintiff, or null if multiple)"
                    },
                    "defendant_name": {
                        "type": ["string", "null"],
                        "description": "Defendant name only"
                    },
                    "year": {
                        "type": ["integer", "null"],
                        "description": "Year as integer"
                    },
                    "citation": {
                        "type": ["string", "null"],
                        "description": "Citation string"
                    },
                    "court": {
                        "type": ["string", "null"],
                        "enum": ["SCJ", "CA", None],
                        "description": "SCJ for Superior Court of Justice or CA for Court of Appeal"
                    },
                    "judge": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                            {"type": "null"}
                        ],
                        "description": "Judge's LAST NAME ONLY. For appeals with multiple judges, use array"
                    },
                    "sex": {
                        "type": ["string", "null"],
                        "enum": ["M", "F", None]
                    },
                    "age": {
                        "type": ["integer", "null"],
                        "description": "Age as integer"
                    },
                    "non_pecuniary_damages": {
                        "type": ["number", "null"],
                        "description": "Amount in dollars (number only, no $ or commas)"
                    },
                    "is_provisional": {
                        "type": ["boolean", "null"]
                    },
                    "injuries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of injuries extracted from all text fields"
                    },
                    "other_damages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["future_loss_of_income", "past_loss_of_income", "cost_of_future_care", "housekeeping_capacity", "other"]
                                },
                                "amount": {"type": "number"},
                                "description": {"type": "string"}
                            },
                            "required": ["type", "amount"]
                        }
                    },
                    "family_law_act_claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "relationship": {
                                    "type": "string",
                                    "enum": ["father", "mother", "parent", "spouse", "son", "daughter", "child", "brother", "sister", "sibling", "grandfather", "grandmother", "grandparent", "grandchild", "unknown"]
                                },
                                "amount": {"type": "number"},
                                "description": {"type": "string"},
                                "is_fla_award": {
                                    "type": "boolean",
                                    "description": "true for FLA awards, false for subrogation/insurance"
                                }
                            },
                            "required": ["relationship", "amount", "is_fla_award"]
                        }
                    },
                    "comments": {
                        "type": ["string", "null"],
                        "description": "Additional notes from Comments column. Extract EVEN FOR FLA-ONLY CASES (describes injury/circumstances, liability, causation, etc.)"
                    },
                    "plaintiffs": {
                        "type": ["array", "null"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "plaintiff_id": {"type": "string"},
                                "plaintiff_name": {"type": "string"},
                                "sex": {"type": ["string", "null"], "enum": ["M", "F", None]},
                                "age": {"type": ["integer", "null"]},
                                "non_pecuniary_damages": {"type": ["number", "null"]},
                                "injuries": {"type": "array", "items": {"type": "string"}},
                                "comments": {"type": ["string", "null"]}
                            },
                            "required": ["plaintiff_id", "plaintiff_name"]
                        },
                        "description": "Only use if multiple plaintiffs; omit if single plaintiff"
                    },
                    "is_continuation": {
                        "type": "boolean",
                        "description": "true if this row lacks case_name/citation (continuation of previous case)"
                    }
                },
                "required": ["is_continuation"]
            }
        }
    }

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

    def _call_api(self, prompt: str, max_retries: int = 3, use_tools: bool = True) -> Optional[Dict[str, Any]]:
        """
        Call Azure API with tool calling support.

        Args:
            prompt: The prompt text
            max_retries: Number of retry attempts
            use_tools: Whether to use function calling (must be True)

        Returns:
            Dict with 'tool_call' key containing extracted data, or None on error
        """
        if not use_tools:
            raise ValueError("Tool calling is required - old models without tool support are not supported")

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
            "tools": [self.CASE_EXTRACTION_TOOL],
            "tool_choice": {"type": "function", "function": {"name": "extract_case_row"}}
        }

        if self.uses_max_completion_tokens:
            payload["max_completion_tokens"] = 2048
        else:
            payload["max_tokens"] = 2048

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=60)

                if response.status_code == 200:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        choice = result["choices"][0]
                        message = choice.get("message", {})

                        # Extract tool call
                        if "tool_calls" in message and len(message["tool_calls"]) > 0:
                            tool_call = message["tool_calls"][0]
                            if tool_call.get("type") == "function":
                                function_args = tool_call.get("function", {}).get("arguments", "{}")
                                import json
                                return {"tool_call": json.loads(function_args)}

                    if self.verbose:
                        print(f"  No tool call in response")
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

    @staticmethod
    def normalize_judge_name(judge_name):
        """
        Normalize judge names to last name only.
        Preserves list structure for appeals cases with multiple judges.

        Examples:
            "Smith J." -> "Smith"
            "A. Smith J.A." -> "Smith"
            "Hon. John Smith J." -> "Smith"
            "Smith, J." -> "Smith"
            "Brown J.J.A." -> "Brown"
            ["Smith J.", "Jones J.A."] -> ["Smith", "Jones"]
            ["Brown J.J.A."] -> ["Brown"]

        Args:
            judge_name: Raw judge name (string) or list of names (for appeals)

        Returns:
            Normalized last name(s) - string if input is string, list if input is list
        """
        if not judge_name:
            return None

        # Helper function to normalize a single judge name
        def normalize_single(name):
            if not name:
                return ""

            # Convert to string and strip whitespace
            name = str(name).strip()

            if not name:
                return ""

            # Remove trailing titles and suffixes (J., J.A., J.J.A., C.J., etc.)
            name = re.sub(r',?\s*(J\.J\.A\.|J\.A\.|J\.|C\.J\.|C\.J\.O\.|C\.J\.C\.)$', '', name, flags=re.IGNORECASE)

            # Remove "The Honourable", "Hon.", etc. at start
            name = re.sub(r'^(The\s+)?(Hon\.?|Honourable)\s+', '', name, flags=re.IGNORECASE)

            # Remove any remaining commas
            name = name.replace(',', '')

            # Standardize spacing
            name = re.sub(r'\s+', ' ', name).strip()

            # Extract last name (last word after splitting)
            # This handles "A. Smith", "John Smith", "A.B. Smith" -> "Smith"
            if name:
                parts = name.split()
                if parts:
                    # Last part is the last name
                    last_name = parts[-1]
                    # Clean up any remaining periods
                    last_name = last_name.rstrip('.')

                    # Normalize to title case for consistency
                    # Handle special cases like "MacKinnon", "O'Brien", "DiTomaso"
                    last_name = last_name.title()

                    return last_name

            return ""

        # Handle list input (appeals cases with multiple judges)
        if isinstance(judge_name, list):
            normalized = [normalize_single(j) for j in judge_name]
            # Filter out empty strings
            normalized = [j for j in normalized if j]
            return normalized if normalized else None

        # Handle string input (single judge)
        result = normalize_single(judge_name)
        return result if result else None

    @staticmethod
    def _map_headers_to_columns(headers_list: List[str], num_columns: int) -> List[str]:
        """
        Map split headers to actual table columns intelligently.

        The PDF has column headers where some cells contain multiple lines:
        - "Sex" and "Age" are on separate lines in ONE cell (one column)
        - "Non-Pecuniary", "General", and "Damages" are on separate lines in ONE cell (one column)

        When Camelot extracts these as newline-separated text and we split on newlines, we get:
        ['Plaintiff', 'Defendant', ..., 'Sex', 'Non-Pecuniary', 'Other Damages', 'Comments', 'Age', 'General', 'Damages']

        This method intelligently maps these to the actual columns by:
        1. Checking if header count matches column count (if so, use as-is)
        2. If not, combining known multi-line patterns to match column count:
           - "Sex" + "Age" → "Sex/Age" (combined header preserves context for LLM)
           - "Non-Pecuniary" + "General" + "Damages" → "Non-Pecuniary Damages"

        This preserves information for the LLM so it understands:
        - "Sex/Age" column can have values like "2 male", "M, 35", "F 28"
        - LLM can correctly interpret "2 male" as "2 males" (not age=2, sex=M)

        Args:
            headers_list: List of header strings (after splitting on newlines)
            num_columns: Actual number of columns in the table

        Returns:
            List of headers mapped to match column count
        """
        if not headers_list:
            return []

        # If header count matches column count, no grouping needed
        if len(headers_list) == num_columns:
            return headers_list

        # If we have fewer headers than columns, pad with generic names
        if len(headers_list) < num_columns:
            padded = headers_list.copy()
            for i in range(len(headers_list), num_columns):
                padded.append(f"Col_{i}")
            return padded

        # If we have more headers than columns, we need to combine some
        # This is the common case where multi-line headers were split

        # Convert to lowercase for checking
        headers_lower = [h.lower() for h in headers_list]

        # Track which headers to group together
        skip_indices = set()
        combined = []

        i = 0
        while i < len(headers_list):
            if i in skip_indices:
                i += 1
                continue

            header = headers_list[i]
            header_lower = header.lower()

            # Check if this is "Sex" followed by "Age"
            if header_lower == 'sex':
                # Look ahead for "Age"
                age_idx = None
                for j in range(i + 1, len(headers_list)):
                    if headers_list[j].lower() == 'age' and j not in skip_indices:
                        age_idx = j
                        break

                if age_idx is not None:
                    # Combine Sex and Age into one column
                    combined.append("Sex/Age")
                    skip_indices.add(age_idx)
                else:
                    combined.append(header)

            # Check if this is "Non-Pecuniary" followed by "General" and/or "Damages"
            elif 'non-pecuniary' in header_lower or 'non pecuniary' in header_lower:
                # Look ahead for "General" and "Damages"
                general_idx = None
                damages_idx = None

                for j in range(i + 1, len(headers_list)):
                    if headers_list[j].lower() == 'general' and j not in skip_indices and general_idx is None:
                        general_idx = j
                    elif headers_list[j].lower() == 'damages' and j not in skip_indices and damages_idx is None:
                        damages_idx = j

                # Combine them
                if general_idx is not None:
                    skip_indices.add(general_idx)
                if damages_idx is not None:
                    skip_indices.add(damages_idx)

                combined.append("Non-Pecuniary Damages")

            # Skip standalone "Age" if it wasn't already grouped with "Sex"
            elif header_lower == 'age':
                # Check if we already combined it
                if i not in skip_indices:
                    # This is a standalone Age that wasn't grouped - skip it
                    # (It was likely part of a multi-line cell we couldn't detect)
                    pass

            # Skip standalone "General" or "Damages" if not already grouped
            elif header_lower in ['general', 'damages']:
                # Check if we already combined it
                if i not in skip_indices:
                    # This is standalone - skip it
                    pass

            else:
                # Keep all other headers as-is
                combined.append(header)

            i += 1

        # If we still have more headers than columns, take first N
        if len(combined) > num_columns:
            return combined[:num_columns]

        # If we have fewer, pad with generic names
        if len(combined) < num_columns:
            for i in range(len(combined), num_columns):
                combined.append(f"Col_{i}")

        return combined

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

    def _clean_section_header(self, section_text: str) -> str:
        """
        Clean section header text by removing trailing money/numbers and garbage.
        Only accept known anatomical/injury section headers.

        Examples:
            "SISTER - $8,000.00" -> "SISTER"
            "DAUGHTER -" -> "DAUGHTER"
            "BRAIN & SKULL" -> "BRAIN & SKULL" (unchanged)
            "P11: FEMALE" -> "" (invalid, reject)
            "$85,796.00" -> "" (invalid, reject)
            "Defendant's motion for a" -> "" (invalid, reject)
            "non-pecuniary" -> "" (invalid, reject)

        Args:
            section_text: Raw section header text

        Returns:
            Cleaned section text, or empty string if invalid
        """
        if not section_text:
            return ""

        text = section_text.strip()

        # Reject if starts with $ or digits (clearly not a section header)
        if text and (text[0] == '$' or text[0].isdigit()):
            return ""

        # Reject invalid patterns (case-insensitive)
        invalid_patterns = [
            "CONTRIBUTORILY",
            "P11:", "P12:",
            "SPECIAL",
            "DEFENDANT",  # "Defendant's motion for a"
            "PLAINTIFF",  # "Plaintiff was..."
            "MOTION",
            "GENERAL DAMAGES",  # This is a column header, not a section
            "PECUNIARY",  # "pecuniary" or "non-pecuniary" are column headers
            "NON-PECUNIARY",
            "DAMAGES",  # When standalone
            "AWARD",
            "TOTAL",
        ]
        text_upper = text.upper()
        for pattern in invalid_patterns:
            if pattern in text_upper:
                return ""

        # Whitelist: Only accept known anatomical/injury sections or FLA relationships
        # This is the MOST IMPORTANT fix - only allow valid sections
        valid_sections = [
            # General/common subsections
            "GENERAL", "MISCELLANEOUS", "MOST SEVERE", "FATAL",
            # Head/sensory
            "BRAIN", "SKULL", "HEAD",
            "EARS", "HEARING", "EYE", "SIGHT", "TEETH",
            # Spine
            "CERVICAL", "THORACIC", "LUMBAR", "SPINE", "SPINAL",
            "NECK", "BACK", "WHIPLASH",
            # Arms
            "SHOULDER", "ARM", "ELBOW", "FOREARM", "WRIST", "HAND", "FINGER", "WHOLE", "COLLAR",
            # Body/torso
            "CHEST", "THORAX", "ABDOMEN", "PELVIS", "BODY",
            "BUTTOCK", "THIGH", "INTERNAL", "REPRODUCTIVE", "RIBS",
            # Legs
            "HIP", "KNEE", "LEG", "ANKLE", "FOOT", "TOE", "LOWER", "LOSS",
            # Skin
            "SKIN", "BURNS", "SCARS", "LACERATIONS",
            # Severe injuries
            "PARAPLEGIA", "QUADRIPLEGIA",
            # Psychological
            "PSYCHOLOGICAL", "PSYCHIATRIC", "MENTAL", "TRAUMATIC", "NEUROSIS",
            "PAIN", "SUFFERING", "MINOR",
            # Other
            "MULTIPLE", "SOFT TISSUE",
            "PRE-EXISTING", "DISABILITY", "CONDITION",
            "SEXUAL", "ASSAULT", "ABUSE",
            "GUIDANCE", "CARE", "COMPANIONSHIP",
            # FLA relationships
            "FATHER", "MOTHER", "PARENT",
            "SON", "DAUGHTER", "CHILD",
            "BROTHER", "SISTER", "SIBLING",
            "SPOUSE", "HUSBAND", "WIFE",
            "GRANDFATHER", "GRANDMOTHER", "GRANDPARENT", "GRANDCHILD",
        ]

        # Check if text contains any valid section keyword
        found_valid = False
        for valid in valid_sections:
            if valid in text_upper:
                found_valid = True
                break

        if not found_valid:
            return ""  # Reject - not a known section type

        # Clean trailing " - $..." or " - " patterns
        # Examples: "SISTER - $8,000.00" -> "SISTER"
        #           "DAUGHTER -" -> "DAUGHTER"
        import re
        # Remove " - $..." money amounts
        text = re.sub(r'\s*-\s*\$[\d,\.]+', '', text)
        # Remove trailing " -" if no content follows
        text = re.sub(r'\s*-\s*$', '', text)

        return text.strip()

    def extract_section_from_stream(self, pdf_path: str, page_spec: str) -> Dict[int, Optional[str]]:
        """
        Extract section headers from stream mode row 0.

        Uses stream mode to capture section headers that lattice mode misses.
        The PDF is predictably formatted with section headers always in row 0.

        Cleans section headers to remove garbage like "SISTER - $8,000.00" -> "SISTER"

        Args:
            pdf_path: Path to PDF file
            page_spec: Page specification (e.g., "1-10" or "all")

        Returns:
            Dict mapping page number to section header (or None if not found)
        """
        sections_by_page = {}

        try:
            # Use stream mode to capture section headers
            tables_stream = camelot.read_pdf(pdf_path, pages=page_spec, flavor="stream")

            for table in tables_stream:
                page_num = table.page
                df_stream = table.df

                if len(df_stream) > 0:
                    # Extract first non-empty cell from row 0 as section header
                    row0_values = df_stream.iloc[0].tolist()
                    section_found = None

                    for cell in row0_values:
                        cell_str = str(cell).strip()
                        if cell_str and cell_str != 'nan':
                            # Clean the section header
                            cleaned = self._clean_section_header(cell_str)
                            if cleaned:
                                section_found = cleaned
                                break
                            elif self.verbose:
                                print(f"  [Page {page_num}] Rejected/cleaned section header: {cell_str}")

                    sections_by_page[page_num] = section_found
        except Exception as e:
            if self.verbose:
                print(f"  Stream mode section extraction warning: {e}")

        return sections_by_page

    def extract_tables_from_pdf(self, pdf_path: str, page_spec: str) -> List[Any]:
        """
        Extract tables from PDF using Camelot.

        Args:
            pdf_path: Path to PDF file
            page_spec: Page specification (e.g., "1-10" or "all")

        Returns:
            List of Camelot table objects
        """
        try:
            tables = camelot.read_pdf(
                pdf_path,
                pages=page_spec,
                flavor="lattice"
                # Don't strip newlines - we need them for header detection
            )
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

        row_data_formatted = "\n".join(row_data)

        prompt = self.ROW_PROMPT.format(
            section=section,
            row_data_formatted=row_data_formatted
        )

        api_response = self._call_api(prompt, use_tools=True)

        if api_response and "tool_call" in api_response:
            data = api_response["tool_call"]
            data['source_page'] = page_number
            data['category'] = section
            data['region'] = [section] if section else []

            # Normalize judge name to last name only
            if data.get('judge'):
                data['judge'] = self.normalize_judge_name(data['judge'])

            return data

        if self.verbose:
            print(f"  No tool call response received")
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
            if not isinstance(case.get('other_damages'), list):
                case['other_damages'] = []
            case['other_damages'].extend(row_data['other_damages'])

        # Merge family_law_act_claims
        if row_data.get('family_law_act_claims'):
            if not isinstance(case.get('family_law_act_claims'), list):
                case['family_law_act_claims'] = []
            case['family_law_act_claims'].extend(row_data['family_law_act_claims'])

        # Merge plaintiffs array
        if row_data.get('plaintiffs'):
            # If case doesn't have plaintiffs array yet, create it
            if not case.get('plaintiffs'):
                case['plaintiffs'] = []

            # Merge plaintiffs by plaintiff_id
            existing_plaintiff_ids = {p.get('plaintiff_id'): p for p in case['plaintiffs']}

            for new_plaintiff in row_data['plaintiffs']:
                plaintiff_id = new_plaintiff.get('plaintiff_id')
                if plaintiff_id and plaintiff_id in existing_plaintiff_ids:
                    # Merge with existing plaintiff
                    existing = existing_plaintiff_ids[plaintiff_id]

                    # Merge injuries
                    if new_plaintiff.get('injuries'):
                        existing_inj = set(existing.get('injuries', []))
                        existing_inj.update(new_plaintiff['injuries'])
                        existing['injuries'] = list(existing_inj)

                    # Append comments
                    if new_plaintiff.get('comments'):
                        if existing.get('comments'):
                            existing['comments'] = f"{existing['comments']} | {new_plaintiff['comments']}"
                        else:
                            existing['comments'] = new_plaintiff['comments']

                    # Update damages if higher
                    new_damages = new_plaintiff.get('non_pecuniary_damages')
                    if new_damages is not None:
                        if existing.get('non_pecuniary_damages') is None or new_damages > existing['non_pecuniary_damages']:
                            existing['non_pecuniary_damages'] = new_damages
                else:
                    # Add new plaintiff
                    case['plaintiffs'].append(new_plaintiff)

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

    @staticmethod
    def clean_up_plaintiff_data(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean up incomplete plaintiff data and remove phantom entries.

        Rules:
        1. Remove plaintiffs with no name AND no injuries AND no damages
        2. If all plaintiffs are removed, remove the plaintiffs array
        3. Remove cases with no case_name (likely failed continuation rows)
        4. Ensure top-level injuries are populated if they exist in plaintiffs

        Args:
            cases: List of parsed cases

        Returns:
            Cleaned list of cases
        """
        cleaned_cases = []

        for case in cases:
            # Skip cases with no case name (likely failed continuation rows)
            if not case.get('case_name'):
                continue

            # Clean up plaintiffs array
            if case.get('plaintiffs'):
                valid_plaintiffs = []

                for plaintiff in case['plaintiffs']:
                    # Check if plaintiff has meaningful data
                    has_name = bool(plaintiff.get('plaintiff_name'))
                    has_injuries = bool(plaintiff.get('injuries'))
                    has_damages = plaintiff.get('non_pecuniary_damages') is not None
                    has_comments = bool(plaintiff.get('comments'))

                    # Keep plaintiff if they have name OR (injuries OR damages OR comments)
                    # This allows plaintiffs with damages but generic names like "Plaintiff 2"
                    if has_name or has_injuries or has_damages or has_comments:
                        valid_plaintiffs.append(plaintiff)

                # Update or remove plaintiffs array
                if valid_plaintiffs:
                    case['plaintiffs'] = valid_plaintiffs

                    # Ensure top-level injuries include all plaintiff injuries
                    all_plaintiff_injuries = set()
                    for p in valid_plaintiffs:
                        all_plaintiff_injuries.update(p.get('injuries', []))

                    # Merge with top-level injuries
                    top_level_injuries = set(case.get('injuries', []))
                    top_level_injuries.update(all_plaintiff_injuries)
                    case['injuries'] = list(top_level_injuries)
                else:
                    # Remove empty plaintiffs array
                    del case['plaintiffs']

            cleaned_cases.append(case)

        return cleaned_cases

    def parse_pdf(
        self,
        pdf_path: str,
        start_page: int = 4,
        end_page: Optional[int] = None,
        output_json: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Parse PDF using Camelot table extraction + LLM row parsing.

        Args:
            pdf_path: Path to PDF
            start_page: Starting page (1-indexed, default=4 to skip TOC)
            end_page: Ending page (None = all)
            output_json: Optional path to save results

        Returns:
            List of parsed cases
        """
        all_cases = []
        current_case = None
        total_rows = 0
        continuation_rows = 0

        # Build page specification for Camelot
        if end_page is None:
            page_spec = "all"
        else:
            page_spec = f"{start_page}-{end_page}"

        if self.verbose:
            print(f"Parsing pages {page_spec}")
            print(f"Using Camelot table extraction + LLM row parsing")
            print(f"Model: {self.model}")

        # HYBRID APPROACH: Extract sections using stream mode
        if self.verbose:
            print("\n📄 Extracting section headers with stream mode...")

        sections_from_stream = self.extract_section_from_stream(pdf_path, page_spec)

        if self.verbose:
            found_count = sum(1 for s in sections_from_stream.values() if s)
            print(f"✅ Found {found_count} section headers from stream mode")

        # Extract all tables using lattice mode
        if self.verbose:
            print("\n📄 Extracting tables with lattice mode...")

        tables = self.extract_tables_from_pdf(pdf_path, page_spec)

        if self.verbose:
            print(f"✅ Extracted {len(tables)} tables from lattice mode")

        # Track current section per page
        section_by_page = {}

        # Track parent section for hierarchical sections
        # Main sections that can have subsections
        main_sections = [
            "HEAD", "BRAIN", "SKULL",
            "ARMS", "SPINE", "BODY", "LEGS", "SKIN",
            "FATAL INJURIES", "MOST SEVERE INJURIES", "MISCELLANEOUS"
        ]

        # Subsection-only keywords that should be combined with parent
        subsection_keywords = ["GENERAL"]

        current_parent_section = None

        # Process each table
        for table_idx, table in enumerate(tables):
            page_number = table.page  # Camelot table objects have .page attribute

            if self.verbose and (table_idx == 0 or table.page != tables[table_idx-1].page):
                print(f"\nPage {page_number}...", end=" ")

            # Use section from stream mode, fallback to table detection
            if page_number not in section_by_page:
                # Try stream mode section first
                section = sections_from_stream.get(page_number)

                # Fallback to table content detection if stream didn't find it
                if not section:
                    section = self.detect_section_from_table(table)

                if section:
                    section_upper = section.upper()

                    # Check if this is a main section
                    is_main_section = any(main_sec in section_upper for main_sec in main_sections)

                    # Check if this is a subsection-only keyword
                    is_subsection_only = any(sub_kw in section_upper for sub_kw in subsection_keywords)

                    if is_main_section:
                        # This is a main section - update parent
                        current_parent_section = section_upper
                        section_by_page[page_number] = section_upper
                    elif is_subsection_only and current_parent_section:
                        # This is a subsection - combine with parent
                        combined = f"{current_parent_section} - {section_upper}"
                        section_by_page[page_number] = combined
                        if self.verbose:
                            print(f"[Hierarchical: {combined}]", end=" ")
                    else:
                        # Standalone section or subsection under a main category
                        section_by_page[page_number] = section_upper
                else:
                    section_by_page[page_number] = "UNKNOWN"

            section = section_by_page[page_number]

            # Get table data as DataFrame
            df = table.df

            if len(df) < 2:  # Need at least header + data
                continue

            # STRUCTURE DETECTION (from test notebook that worked)
            # Type 1: Headers spread across row 0 (pages 91-95) - data starts row 1
            # Type 2: Newline-separated headers in row 0 - data starts row 1
            # Type 3: Section in row 0, headers in row 1 (pages 21-25) - data starts row 2

            row0_cell0 = str(df.iloc[0, 0]).strip() if len(df) > 0 else ""
            row0_values = [str(cell).strip() for cell in df.iloc[0].tolist()] if len(df) > 0 else []
            num_filled_cells = sum(1 for v in row0_values if v and v != 'nan')

            header = []
            data_start_row = 1

            if num_filled_cells > 1:
                # Type 1: Headers spread across columns (pages 91-95)
                header = [v if v and v != 'nan' else f"Col_{i}" for i, v in enumerate(row0_values)]
                data_start_row = 1

            elif '\n' in row0_cell0 or '\\n' in row0_cell0:
                # Type 2: Newline-separated headers in row 0, col 0
                headers_raw = row0_cell0.replace('\\n', '\n').split('\n')
                headers_split = [h.strip() for h in headers_raw if h.strip()]

                # Map multi-line headers to actual columns (e.g., "Sex \n Age" -> "Sex/Age", "Non-Pecuniary \n General \n Damages" -> "Non-Pecuniary Damages")
                num_columns = len(df.columns)
                header = self._map_headers_to_columns(headers_split, num_columns)
                data_start_row = 1

            else:
                # Type 3: Section in row 0, headers in row 1 (pages 21-25)
                if len(df) > 1:
                    row1_cell0 = str(df.iloc[1, 0]).strip()
                    row1_values = [str(cell).strip() for cell in df.iloc[1].tolist()]
                    num_filled_row1 = sum(1 for v in row1_values if v and v != 'nan')

                    if self.verbose:
                        print(f"\nDEBUG Type 3:")
                        print(f"  row1_cell0: {repr(row1_cell0[:100])}")
                        print(f"  num_filled_row1: {num_filled_row1}")
                        print(f"  row1_values: {row1_values[:3]}")

                    if '\n' in row1_cell0 or '\\n' in row1_cell0:
                        # Headers newline-separated in row 1
                        headers_raw = row1_cell0.replace('\\n', '\n').split('\n')
                        headers_split = [h.strip() for h in headers_raw if h.strip()]

                        # Map multi-line headers to actual columns (e.g., "Sex \n Age" -> "Sex/Age", "Non-Pecuniary \n General \n Damages" -> "Non-Pecuniary Damages")
                        # The PDF has some cells with 2-3 lines that represent a single column
                        num_columns = len(df.columns)
                        if self.verbose:
                            print(f"  headers_split ({len(headers_split)}): {headers_split}")
                            print(f"  num_columns: {num_columns}")
                        header = self._map_headers_to_columns(headers_split, num_columns)
                        if self.verbose:
                            print(f"  mapped_headers ({len(header)}): {header}")
                    elif num_filled_row1 > 1:
                        # Headers spread across row 1
                        header = [v if v and v != 'nan' else f"Col_{i}" for i, v in enumerate(row1_values)]
                    else:
                        header = [str(h).strip() for h in df.iloc[1].tolist() if str(h).strip()]

                    data_start_row = 2
                else:
                    continue  # Not enough rows

            # Validate headers
            if not header or not any(h.lower() in ['plaintiff', 'case', 'year', 'defendant'] for h in header):
                if self.verbose:
                    print(f"SKIP - headers: {header[:5] if header else 'None'}")
                continue

            if self.verbose:
                print(f"Headers: {header[:5] if len(header) > 5 else header}, data_start: {data_start_row}, df_len: {len(df)}")

            page_rows = 0
            page_new = 0
            page_merged = 0

            # Process data rows starting from correct row
            for idx in range(data_start_row, len(df)):
                row = df.iloc[idx]
                row_cells = [str(cell).strip() if cell else "" for cell in row]

                # Skip empty rows
                if not any(row_cells):
                    continue

                page_rows += 1
                total_rows += 1

                # Parse row with LLM
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

            if self.verbose and page_rows > 0:
                print(f"{page_rows} rows, {page_new} new, {page_merged} merged")

            # Save incremental results every 10 tables
            if output_json and table_idx > 0 and table_idx % 10 == 0:
                if current_case:
                    all_cases.append(current_case)
                    current_case = None
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

        # Post-process to clean up incomplete data
        all_cases = self.clean_up_plaintiff_data(all_cases)

        if self.verbose:
            print(f"  After cleanup: {len(all_cases)} cases")

        # Save final results
        if output_json:
            with open(output_json, 'w') as f:
                json.dump(all_cases, f, indent=2)

        return all_cases

    def detect_section_from_table(self, table) -> str:
        """
        Detect body region section from table content.

        Since we're using Camelot, we extract section from table text.
        """
        # Get table text
        df = table.df
        table_text = " ".join([str(cell) for row in df.values for cell in row])

        return self.detect_section_header(table_text)


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
    Parse Ontario Damages Compendium using hybrid Camelot + LLM approach.

    This is more efficient than full-page parsing:
    - Better table detection (Camelot lattice-based)
    - Handles complex cases (multiple plaintiffs per cell)
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
        start_page=start_page or 4,  # Start on page 4 to skip TOC (pages 1-3)
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
