"""
Expert Report Analyzer

Extracts injuries and sequelae from medical/expert reports using LLM analysis.
Focus: injury and functional outcome data only, not procedural information.
"""

import pdfplumber
import re
from typing import Dict, List, Optional
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# LLM settings
DEFAULT_LLM_MODEL_OPENAI = "gpt-4o-mini"
DEFAULT_LLM_MODEL_ANTHROPIC = "claude-3-haiku-20240307"
MAX_REPORT_CHARS_FOR_LLM = 4000
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 1000

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
    """Analyzes medical/expert reports to extract injuries and sequelae."""

    def __init__(self, api_key: Optional[str] = None, provider: str = "openai"):
        """
        Initialize the analyzer.

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

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        text = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return "\n\n".join(text)

    def analyze_with_llm(self, report_text: str) -> Dict:
        """
        Analyze report text with LLM to extract injuries and sequelae only.

        Returns:
            {
                "injuries": ["cervical radiculopathy", "brachial plexus injury", ...],
                "sequelae": ["chronic pain", "paresthesia", ...],
                "severity": "mild|moderate|severe"
            }
        """
        if not self.api_key:
            return self._analyze_with_regex(report_text)

        # Truncate if needed
        if len(report_text) > MAX_REPORT_CHARS_FOR_LLM:
            logger.warning(
                f"Report text truncated from {len(report_text)} to {MAX_REPORT_CHARS_FOR_LLM}."
            )
            report_text_truncated = report_text[:MAX_REPORT_CHARS_FOR_LLM]
        else:
            report_text_truncated = report_text

        prompt = f"""Analyze this medical/expert report and extract ONLY injuries and sequelae.

REPORT TEXT:
{report_text_truncated}

Please extract and return ONLY a JSON object with this exact structure (no other text):
{{
    "injuries": ["injury1", "injury2", ...],
    "sequelae": ["functional limitation1", "limitation2", ...],
    "severity": "mild|moderate|severe"
}}

IMPORTANT:
- injuries: List of diagnosed or described injuries (e.g., "C5-C6 disc herniation", "rotator cuff tear")
- sequelae: List of functional consequences (e.g., "chronic pain", "reduced ROM", "paresthesia")
- severity: Overall severity assessment from the report
- Do NOT include case information, judge names, or procedural details
- Be specific and clinical
"""

        try:
            if self.provider == "openai" and OPENAI_AVAILABLE:
                response = openai.chat.completions.create(
                    model=DEFAULT_LLM_MODEL_OPENAI,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a medical report analyzer. Return ONLY valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=LLM_TEMPERATURE,
                    max_tokens=LLM_MAX_TOKENS
                )

                result_text = response.choices[0].message.content.strip()

                # Extract JSON from response
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
                    messages=[{"role": "user", "content": prompt}]
                )

                result_text = message.content[0].text.strip()

                # Extract JSON from response
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()

                return json.loads(result_text)

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return self._analyze_with_regex(report_text)

        return self._analyze_with_regex(report_text)

    def _analyze_with_regex(self, report_text: str) -> Dict:
        """Fallback regex-based analysis for injuries and sequelae."""
        text_lower = report_text.lower()

        # Extract injuries using patterns
        injuries = []
        injury_patterns = [
            r"(?:diagnosed|presents with|history of|suffer[s]? from|sustained)\s+([^.]{10,80}?(?:injury|herniation|tear|fracture|strain|sprain|syndrome))",
            r"([^.]{10,80}?(?:disc|ligament|meniscus|tendon)\s+(?:herniation|tear|strain|rupture))",
        ]

        for pattern in injury_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            injuries.extend([m.strip()[:80] for m in matches])

        injuries = list(set(injuries))

        # Extract sequelae using patterns
        sequelae = []
        sequelae_patterns = [
            r"(?:results in|leading to|causes|symptom[s]?:?)\s+([^.]{5,60})",
            r"(?:pain|limitation|difficulty|unable)\s+(?:with|to)\s+([^.]{5,60})",
            r"([^.]{5,60}?(?:pain|limitation|difficulty|dysfunction|weakness))",
        ]

        for pattern in sequelae_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            sequelae.extend([m.strip()[:80] for m in matches])

        sequelae = list(set(sequelae))

        # Detect severity
        severity = "moderate"
        if any(word in text_lower for word in ["severe", "significant", "major", "profound"]):
            severity = "severe"
        elif any(word in text_lower for word in ["mild", "minor", "slight"]):
            severity = "mild"

        return {
            "injuries": injuries[:10],
            "sequelae": sequelae[:10],
            "severity": severity
        }

    def analyze_report(self, pdf_path: str, use_llm: bool = True) -> Dict:
        """
        Main method to analyze an expert report.

        Args:
            pdf_path: Path to the PDF file
            use_llm: Whether to use LLM analysis (requires API key)

        Returns:
            Structured injury/sequelae data
        """
        text = self.extract_text_from_pdf(pdf_path)

        if not text.strip():
            raise ValueError("Could not extract text from PDF")

        if use_llm and self.api_key:
            result = self.analyze_with_llm(text)
        else:
            result = self._analyze_with_regex(text)

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
    Convenience function to analyze an expert report.

    Returns only injuries and sequelae data for search use.
    """
    analyzer = ExpertReportAnalyzer(api_key=api_key, provider=provider)
    return analyzer.analyze_report(pdf_path, use_llm=use_llm)
