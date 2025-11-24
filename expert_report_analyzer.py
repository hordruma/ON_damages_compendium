"""
Expert Report Analyzer
Extracts injuries and limitations from medical/expert reports using LLM analysis
"""

import pdfplumber
import re
from typing import Dict, List, Optional, Tuple
import json
import os
import logging
from pathlib import Path
from anatomical_mappings import enhance_region_detection, ANATOMICAL_MAPPINGS

# Setup logging
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# LLM settings
DEFAULT_LLM_MODEL_OPENAI = "gpt-4o-mini"  # Fast and cost-effective
DEFAULT_LLM_MODEL_ANTHROPIC = "claude-3-haiku-20240307"  # Fast and cost-effective
MAX_REPORT_CHARS_FOR_LLM = 4000  # Maximum characters to send to LLM (token limit)
LLM_TEMPERATURE = 0.1  # Low temperature for consistent extraction
LLM_MAX_TOKENS = 1000  # Maximum tokens in LLM response

# Regex extraction settings
MAX_LIMITATIONS_EXTRACTED = 10  # Maximum number of limitations to extract
MAX_REGIONS_DETECTED = 5  # Maximum number of regions to detect
SUMMARY_CHARS = 500  # Characters for fallback summary

# ============================================================================

# Optional LLM imports
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class ExpertReportAnalyzer:
    """Analyzes medical/expert reports to extract injuries and limitations"""

    def __init__(self, api_key: Optional[str] = None, provider: str = "openai"):
        """
        Initialize the analyzer

        Args:
            api_key: API key for LLM provider (or set via env var)
            provider: "openai" or "anthropic"
        """
        self.provider = provider

        if provider == "openai" and OPENAI_AVAILABLE:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if self.api_key:
                openai.api_key = self.api_key
        elif provider == "anthropic" and ANTHROPIC_AVAILABLE:
            self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if self.api_key:
                self.client = anthropic.Anthropic(api_key=self.api_key)

        # Load region mappings
        region_map_path = Path(__file__).parent / "region_map.json"
        with open(region_map_path) as f:
            self.region_map = json.load(f)

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        text = []

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)

        return "\n\n".join(text)

    def analyze_with_llm(self, report_text: str) -> Dict:
        """
        Analyze report text with LLM to extract structured injury information

        Returns:
            {
                "injured_regions": ["cervical_spine", "shoulder_right", ...],
                "injury_description": "Detailed clinical description...",
                "limitations": ["Reduced ROM", "Chronic pain", ...],
                "chronicity": "acute|chronic|permanent",
                "mechanism": "MVA|slip and fall|...",
                "severity": "mild|moderate|severe"
            }
        """
        if not self.api_key:
            # Fallback to regex-based analysis if no LLM available
            return self._analyze_with_regex(report_text)

        # Build region list for prompt
        region_list = "\n".join([
            f"- {rid}: {data['label']}"
            for rid, data in self.region_map.items()
        ])

        # Truncate if needed and warn user
        if len(report_text) > MAX_REPORT_CHARS_FOR_LLM:
            logger.warning(
                f"Report text truncated from {len(report_text)} to {MAX_REPORT_CHARS_FOR_LLM} characters. "
                f"This may result in missing information from later sections of the report."
            )
            print(f"⚠️  Warning: Report text truncated ({len(report_text)} → {MAX_REPORT_CHARS_FOR_LLM} chars)")
            report_text_truncated = report_text[:MAX_REPORT_CHARS_FOR_LLM]
        else:
            report_text_truncated = report_text

        prompt = f"""Analyze this medical/expert report and extract structured injury information.

REPORT TEXT:
{report_text_truncated}

AVAILABLE BODY REGIONS:
{region_list}

Please extract and return ONLY a JSON object with this exact structure (no other text):
{{
    "injured_regions": ["region_id1", "region_id2"],
    "injury_description": "Detailed clinical description of injuries including anatomical structures, severity, and symptoms",
    "limitations": ["Limitation 1", "Limitation 2"],
    "chronicity": "acute|chronic|permanent",
    "mechanism": "Description of how injury occurred",
    "severity": "mild|moderate|severe",
    "age": 35,
    "gender": "male|female|unspecified"
}}

IMPORTANT:
- Use ONLY region IDs from the list above
- Be specific and clinical in the injury_description
- Extract all functional limitations mentioned
- Determine chronicity from permanence/prognosis language
- Extract age and gender if mentioned
"""

        try:
            if self.provider == "openai" and OPENAI_AVAILABLE:
                response = openai.chat.completions.create(
                    model=DEFAULT_LLM_MODEL_OPENAI,
                    messages=[
                        {"role": "system", "content": "You are a medical report analyzer. Return ONLY valid JSON, no other text."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=LLM_MAX_TOKENS
                )

                result_text = response.choices[0].message.content.strip()

                # Extract JSON from response (sometimes LLM wraps it in markdown)
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                return json.loads(result_text)

            elif self.provider == "anthropic" and ANTHROPIC_AVAILABLE:
                message = self.client.messages.create(
                    model=DEFAULT_LLM_MODEL_ANTHROPIC,
                    max_tokens=LLM_MAX_TOKENS,
                    temperature=LLM_TEMPERATURE,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                result_text = message.content[0].text.strip()

                # Extract JSON from response
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                return json.loads(result_text)

        except Exception as e:
            print(f"LLM analysis failed: {e}")
            # Fallback to regex
            return self._analyze_with_regex(report_text)

        # Final fallback
        return self._analyze_with_regex(report_text)

    def _analyze_with_regex(self, report_text: str) -> Dict:
        """
        Fallback regex-based analysis when LLM is not available
        Now enhanced with anatomical structure mapping
        """
        text_lower = report_text.lower()

        # Detect regions based on keywords
        detected_regions = []

        for region_id, region_data in self.region_map.items():
            # Check if any compendium terms appear in the text
            for term in region_data["compendium_terms"]:
                if term.lower() in text_lower:
                    detected_regions.append(region_id)
                    break

        # Enhanced detection using anatomical structure mapping
        # This catches terms like "tibia", "femur", "humerus", etc.
        anatomical_regions = enhance_region_detection(report_text, detected_regions)
        detected_regions.extend(anatomical_regions)

        # Remove duplicates
        detected_regions = list(set(detected_regions))

        # Detect chronicity
        chronicity = "unspecified"
        if any(word in text_lower for word in ["chronic", "permanent", "ongoing", "persistent"]):
            chronicity = "chronic"
        elif any(word in text_lower for word in ["acute", "recent", "new"]):
            chronicity = "acute"

        # Detect severity
        severity = "moderate"
        if any(word in text_lower for word in ["severe", "significant", "major", "profound"]):
            severity = "severe"
        elif any(word in text_lower for word in ["mild", "minor", "slight"]):
            severity = "mild"

        # Extract limitations (common phrases)
        limitations = []
        limitation_patterns = [
            r"unable to ([\w\s]+)",
            r"difficulty ([\w\s]+)",
            r"reduced ([\w\s]+)",
            r"limited ([\w\s]+)",
            r"impaired ([\w\s]+)",
        ]

        for pattern in limitation_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            limitations.extend([m.strip()[:50] for m in matches[:5]])

        # Detect mechanism
        mechanism = "unspecified"
        if "motor vehicle" in text_lower or "mva" in text_lower or "car accident" in text_lower:
            mechanism = "Motor vehicle accident"
        elif "slip" in text_lower and "fall" in text_lower:
            mechanism = "Slip and fall"
        elif "work" in text_lower and ("accident" in text_lower or "injury" in text_lower):
            mechanism = "Workplace accident"

        return {
            "injured_regions": detected_regions[:MAX_REGIONS_DETECTED],
            "injury_description": report_text[:SUMMARY_CHARS],
            "limitations": list(set(limitations))[:MAX_LIMITATIONS_EXTRACTED],
            "chronicity": chronicity,
            "mechanism": mechanism,
            "severity": severity,
            "age": None,
            "gender": "unspecified"
        }

    def analyze_report(self, pdf_path: str, use_llm: bool = True) -> Dict:
        """
        Main method to analyze an expert report

        Args:
            pdf_path: Path to the PDF file
            use_llm: Whether to use LLM analysis (requires API key)

        Returns:
            Structured injury data
        """
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            raise ValueError("Could not extract text from PDF")

        # Analyze with LLM or regex
        if use_llm and self.api_key:
            result = self.analyze_with_llm(text)
        else:
            result = self._analyze_with_regex(text)

        # Add source metadata
        result["source_file"] = Path(pdf_path).name
        result["extraction_method"] = "llm" if (use_llm and self.api_key) else "regex"

        return result


def analyze_expert_report(
    pdf_path: str,
    api_key: Optional[str] = None,
    provider: str = "openai",
    use_llm: bool = True
) -> Dict:
    """
    Convenience function to analyze an expert report

    Args:
        pdf_path: Path to PDF file
        api_key: API key for LLM (optional, uses env var if not provided)
        provider: "openai" or "anthropic"
        use_llm: Whether to use LLM (falls back to regex if False or no API key)

    Returns:
        Structured injury data
    """
    analyzer = ExpertReportAnalyzer(api_key=api_key, provider=provider)
    return analyzer.analyze_report(pdf_path, use_llm=use_llm)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python expert_report_analyzer.py <pdf_path> [--no-llm]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    use_llm = "--no-llm" not in sys.argv

    result = analyze_expert_report(pdf_path, use_llm=use_llm)

    print("\n=== Expert Report Analysis ===\n")
    print(json.dumps(result, indent=2))
