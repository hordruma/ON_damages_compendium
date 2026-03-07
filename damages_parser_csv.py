"""
Ontario Damages Compendium — Deterministic CSV Parser

Parses the raw Camelot-extracted CSV without requiring an LLM.
Uses regex patterns for structured field extraction (names, citations,
damages amounts, demographics, injuries, FLA claims).

Key features:
- Cleans corrupted case names (Appeal/Action text bleeding into plaintiff names)
- Deduplicates cases that appear across multiple PDF pages/sections
- Consolidates multiple body-region appearances into single case records
- Maps citations to PDF section headers for accurate category assignment
"""

import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


# ─── Known section headers from the PDF ─────────────────────────────────────

VALID_SECTIONS = {
    # Head/Brain
    "General", "Brain & Skull", "Brain Damage – Very Severe",
    "Head", "Head - General",
    # Spine
    "Back", "Neck", "Whiplash", "Spine Below Neck",
    "Cervical Spine", "Thoracic Spine", "Lumbar Spine",
    # Arms
    "Shoulder & Collar Bone", "Whole Arm", "Elbow",
    "Forearm", "Wrist", "Hand",
    # Body
    "Internal Organs", "Ribs", "Reproductive Organs",
    "Buttock and Thigh",
    # Legs
    "Hip", "Thigh", "Knee", "Leg/Whole Leg",
    "Leg/Lower Leg", "Leg/Loss of Leg", "Ankle", "Foot",
    # Skin
    "Scars and Lacerations", "Burns",
    # Sensory
    "Eye/Sight", "Ears/Hearing", "Teeth",
    # Severe
    "Quadriplegia", "Paraplegia",
    # Psychological/other
    "Traumatic Neurosis", "Sexual Assault/Abuse",
    "Pain and Suffering – Minor Cases",
    "Pre-existing Disability or Condition",
    # FLA/Fatal
    "Loss of Guidance, Care and Companionship",
    "Fatal Injuries",
    "Husband and Father", "Wife & Mother",
    "Son/Daughter", "Brother/Sister",
    "Father", "Mother", "Husband", "Wife",
    "Grandparent", "Grandchild",
}

# Lowercase lookup for fuzzy matching
_VALID_SECTIONS_LOWER = {s.lower(): s for s in VALID_SECTIONS}


# ─── Regex patterns ─────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r'\b(19\d{2}|20[0-2]\d)\b')
_CITATION_RE = re.compile(r'\[\d{4}\]\s*O\.J\.')
_MONEY_RE = re.compile(r'\$[\d,]+(?:\.\d{2})?')
_AGE_RE = re.compile(r'(\d{1,3})\s*(?:years?|yrs?|year)', re.IGNORECASE)
_SEX_RE = re.compile(r'\b(Male|Female|M|F)\b', re.IGNORECASE)
_COURT_SCJ_RE = re.compile(r'\bS\.?C\.?J\.?\b', re.IGNORECASE)
_COURT_CA_RE = re.compile(r'\b(?:Ont\.?\s*)?C\.?A\.?\b|Court of Appeal', re.IGNORECASE)
_JUDGE_RE = re.compile(
    r'([A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+)*)\s+'
    r'(?:J\.|J\.A\.|J\.J\.A\.|C\.J\.|C\.J\.O\.)',
)
_PROVISIONAL_RE = re.compile(r'provisionally|provisional', re.IGNORECASE)

# Patterns for legal status text that bleeds into case names from Camelot
_LEGAL_STATUS_FRAGMENTS = re.compile(
    r'(?:^[A-Z]?\s*)?'  # Optional eaten first char
    r'(?:'
    r'ppeal(?:ed)?\s+(?:allowed|dismissed|by)|'
    r'ction\s+dismissed|'
    r'laintiff[\u2019\']?s?\s+appeal|'
    r'efendant[\u2019\']?s?\s+appeal|'
    r'o\s+liability|'
    r'ew\s+trial\s+ordered|'
    r'ppealed\s+by|'
    r'dditional\s+reasons?|'
    r'upplementary\s+[Rr]easons?|'
    r'otion\s+to\s+set|'
    r'amages\s+assessed|'
    r'osts\s+assessed'
    r')',
    re.IGNORECASE,
)

# FLA relationship patterns
_FLA_PATTERNS = [
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*(?:Wife|Spouse\s*\(F\))\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'spouse'),
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*Husband\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'spouse'),
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*(?:Son|Daughter|Child(?:ren)?)\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'child'),
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*(?:Father|Dad)\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'father'),
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*(?:Mother|Mom)\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'mother'),
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*(?:Brother|Sister|Sibling)\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'sibling'),
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*(?:Grand(?:parent|father|mother|child))\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'grandparent'),
    (re.compile(r'(?:Family\s+Law\s+Act|FLA)\s*(?:Claim)?[:\s]*(?:Parent)\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'parent'),
]

# Other damages patterns
_OTHER_DAMAGES_PATTERNS = [
    (re.compile(r'(?:Past\s+)?(?:Loss\s+of\s+)?(?:Income|Earnings?|Wages?)\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'past_loss_of_income'),
    (re.compile(r'(?:Future\s+)?(?:Loss\s+of\s+)?(?:Income|Earning\s+Capacity|Wages?)\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'future_loss_of_income'),
    (re.compile(r'(?:Future\s+)?(?:Cost\s+of\s+)?(?:Care|Attendant|Nursing)\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'cost_of_future_care'),
    (re.compile(r'(?:Housekeep(?:ing|er)|Household\s+Services?)\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'housekeeping_capacity'),
    (re.compile(r'(?:Special\s+Damages?|Out\s+of\s+Pocket)\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'other'),
    (re.compile(r'(?:Punitive|Exemplary)\s+Damages?\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'other'),
    (re.compile(r'(?:Aggravated)\s+Damages?\s*[:\-]\s*\$?([\d,]+(?:\.\d{2})?)', re.IGNORECASE), 'other'),
]


def _parse_money(text: str) -> Optional[float]:
    """Parse a dollar amount string to float."""
    if not text:
        return None
    cleaned = text.replace('$', '').replace(',', '').strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_year(text: str) -> Optional[int]:
    """Extract the most likely case year from text."""
    m = _YEAR_RE.search(text)
    return int(m.group(1)) if m else None


def _extract_court(text: str) -> str:
    """Determine court from text."""
    if _COURT_CA_RE.search(text):
        return "CA"
    if _COURT_SCJ_RE.search(text):
        return "SCJ"
    return ""


def _extract_judges(text: str) -> List[str]:
    """Extract judge last names from text."""
    judges = []
    for m in _JUDGE_RE.finditer(text):
        name = m.group(1).strip()
        # Take last word as surname
        parts = name.split()
        surname = parts[-1].rstrip('.')
        if surname and len(surname) > 1:
            judges.append(surname.title())
    return judges


def _extract_sex_age(text: str) -> Tuple[Optional[str], Optional[int]]:
    """Extract sex and age from the Sex/Age column."""
    sex = None
    age = None

    sm = _SEX_RE.search(text)
    if sm:
        s = sm.group(1).upper()
        sex = "M" if s in ("M", "MALE") else "F"

    am = _AGE_RE.search(text)
    if am:
        a = int(am.group(1))
        if 0 < a <= 110:
            age = a

    # Handle "2 Male" pattern (num_plaintiffs, not age)
    m2 = re.match(r'^(\d+)\s+(Male|Female)', text, re.IGNORECASE)
    if m2:
        sex = "M" if m2.group(2).upper() in ("MALE", "M") else "F"
        # The number is plaintiff count, not age
        age = None

    return sex, age


def _extract_non_pecuniary(text: str) -> Tuple[Optional[float], bool, List[Dict]]:
    """
    Extract non-pecuniary damages from the damages column.

    Returns: (total_amount, is_provisional, plaintiffs_list)
    """
    is_provisional = bool(_PROVISIONAL_RE.search(text))

    # Check for multi-plaintiff pattern: "Plaintiff 1: $X  Plaintiff 2: $Y"
    multi_pattern = re.findall(
        r'(?:Plaintiff\s*\d+|P\d+)\s*[:]\s*\$?([\d,]+(?:\.\d{2})?)',
        text, re.IGNORECASE,
    )
    if multi_pattern:
        plaintiffs = []
        total = 0
        for i, amt_str in enumerate(multi_pattern, 1):
            amt = _parse_money(amt_str)
            if amt:
                total += amt
                plaintiffs.append({
                    'plaintiff_id': f'P{i}',
                    'plaintiff_name': f'Plaintiff {i}',
                    'non_pecuniary_damages': amt,
                })
        return total if total else None, is_provisional, plaintiffs

    # Single amount
    amounts = _MONEY_RE.findall(text)
    if amounts:
        # Take the first/largest amount as non-pecuniary
        vals = [_parse_money(a) for a in amounts]
        vals = [v for v in vals if v is not None]
        if vals:
            return max(vals), is_provisional, []

    return None, is_provisional, []


def _extract_fla_claims(text: str) -> List[Dict[str, Any]]:
    """Extract Family Law Act claims from Other Damages or Comments columns."""
    claims = []

    # Try each FLA pattern
    for pattern, relationship in _FLA_PATTERNS:
        for m in pattern.finditer(text):
            amt = _parse_money(m.group(1))
            if amt and amt > 0:
                claims.append({
                    'relationship': relationship,
                    'amount': amt,
                    'description': m.group(0).strip(),
                    'is_fla_award': True,
                })

    # Broader catch: "Wife: $X", "Son- $X" etc. in FLA context
    if 'family law' in text.lower() or 'fla' in text.lower():
        broader = re.findall(
            r'((?:Wife|Husband|Son|Daughter|Father|Mother|Brother|Sister|'
            r'Child(?:ren)?|Spouse|Parent|Grand\w+))\s*[-:]\s*\$?([\d,]+(?:\.\d{2})?)',
            text, re.IGNORECASE,
        )
        for rel_raw, amt_str in broader:
            amt = _parse_money(amt_str)
            if amt and amt > 0:
                rel = rel_raw.strip().lower()
                # Normalize relationship
                if rel in ('wife', 'husband', 'spouse'):
                    rel_norm = 'spouse'
                elif rel in ('son', 'daughter', 'child', 'children'):
                    rel_norm = 'child'
                elif rel in ('father', 'dad'):
                    rel_norm = 'father'
                elif rel in ('mother', 'mom'):
                    rel_norm = 'mother'
                elif rel in ('brother', 'sister', 'sibling'):
                    rel_norm = 'sibling'
                else:
                    rel_norm = rel

                # Avoid duplicates
                exists = any(
                    c['relationship'] == rel_norm and abs(c['amount'] - amt) < 1
                    for c in claims
                )
                if not exists:
                    claims.append({
                        'relationship': rel_norm,
                        'amount': amt,
                        'description': f"{rel_raw}: ${amt:,.2f}",
                        'is_fla_award': True,
                    })

    return claims


def _extract_other_damages(text: str) -> List[Dict[str, Any]]:
    """Extract pecuniary/other damages from the Other Damages column."""
    damages = []

    for pattern, dtype in _OTHER_DAMAGES_PATTERNS:
        for m in pattern.finditer(text):
            amt = _parse_money(m.group(1))
            if amt and amt > 0:
                damages.append({
                    'type': dtype,
                    'amount': amt,
                    'description': m.group(0).strip(),
                })

    return damages


def _extract_injuries(comments: str) -> List[str]:
    """
    Extract individual injury descriptions from comments text.

    Splits on sentence boundaries and extracts injury-like phrases.
    """
    if not comments or len(comments) < 5:
        return []

    injuries = []
    # Split on periods, but preserve abbreviations
    sentences = re.split(r'(?<!\b[A-Z])(?<!\b[a-z])\.\s+', comments)

    # Injury-indicating keywords
    injury_keywords = re.compile(
        r'fractur|injur|tear|strain|sprain|hernia|contusion|lacerat|'
        r'disloc|break|broken|damage|loss|pain|scar|burn|'
        r'syndrome|disorder|impair|deficit|paralys|pleg|'
        r'concuss|whiplash|trauma|degenerat|ruptur|compress|'
        r'anxiety|depress|ptsd|stress|phobia|nightmar|'
        r'numbness|tingling|stiff|swell|inflam|'
        r'surgery|amputa|remov',
        re.IGNORECASE,
    )

    for sentence in sentences:
        s = sentence.strip()
        if not s or len(s) < 5:
            continue
        # Only include sentences that describe injuries
        if injury_keywords.search(s):
            # Clean up the sentence
            s = re.sub(r'^(The\s+)?(plaintiff|victim|patient)\s+', '', s, flags=re.IGNORECASE)
            s = s.strip().rstrip('.')
            if len(s) > 3:
                injuries.append(s)

    # If no keyword matches but comments exist, take the whole thing
    # as a description (many comments are just injury lists)
    if not injuries and len(comments) > 10:
        # Split on ". " for individual injury phrases
        parts = [p.strip().rstrip('.') for p in comments.split('. ') if p.strip()]
        injuries = [p for p in parts if len(p) > 3]

    return injuries[:20]  # Cap at 20


def _clean_plaintiff_name(name: str) -> str:
    """
    Clean plaintiff name by removing legal status text that Camelot
    concatenated from continuation lines.

    Examples:
        "AMomand ppeal allowed in part." -> "Momand"
        "AGeorge ction dismissed." -> "George"
        "PElmardy laintiff's appeal" -> "Elmardy"
        "ACrawford (Litigation Guardian) ppeal affirmed" -> "Crawford (Litigation Guardian)"
    """
    original = name

    # Strip leading junk: single uppercase chars separated by spaces
    # e.g., "A          AMustapha..." -> "AMustapha..."
    # These are eaten first chars from multiple legal status lines
    name = re.sub(r'^(?:[A-Z]\s+)+', '', name).strip()

    # Known truncated legal words that bleed from continuation rows.
    # The first char gets eaten by Camelot and prepended to the name.
    # Pattern: [eaten char][RealName] [truncated legal word]...
    # e.g., "AMomand ppeal" = A(ppeal) eaten, real name = Momand
    #        "PElmardy laintiff" = P(laintiff) eaten, real name = Elmardy
    #        "AK.K. ppeal" = A(ppeal) eaten, real name = K.K.
    #        "D  PCalin efendant..." = D(efendant) + P(laintiff), real name = Calin

    # First: detect if legal fragments are present
    # These are truncated words where the first letter was eaten by Camelot
    # e.g., "Appeal" -> "ppeal", "Plaintiff" -> "laintiff"
    # Use negative lookbehind to avoid matching complete words like "plaintiffs"
    legal_fragments = re.compile(
        r'(?<![Aa])ppeal|(?<![Aa])ction\s+dismiss|(?<![Pp])laintiff|(?<![Dd])efendant|'
        r'(?<![Nn])o\s+liab|(?<![Nn])ew\s+trial|'
        r'(?<![Aa])ppealed|(?<![Aa])dditional|(?<![Ss])upplementary|(?<![Mm])otion\s+to|'
        r'(?<![Dd])amages\s+assess|(?<![Cc])osts\s+assess|'
        r'(?<![Oo])n\s+appeal|(?<![Ll])eave\s+to|(?<![Jj])ury\s+trial',
        re.IGNORECASE,
    )

    if legal_fragments.search(name):
        # Strategy: find the real name by looking for a name-like token
        # before the first legal fragment. The eaten char is at position 0.

        # Remove everything after (and including) the legal fragment
        # But first, handle the eaten first character

        # Strategy: find where the legal fragment starts and take everything before it
        # as the (possibly corrupted) name, then clean the eaten first char.

        # Find the position of the first truncated legal word
        frag_match = legal_fragments.search(name)
        if frag_match:
            before_frag = name[:frag_match.start()].strip()

            # The text before the fragment is the name (possibly with eaten char)
            # e.g., "AMustapha " or "ACrawford (Litigation Guardian) "
            # or "PKingston Road Animal Hospital Professional Corp. "

            if before_frag:
                # Remove eaten first char: if first char is uppercase and
                # removing it still leaves a valid name start
                real_name = before_frag
                if len(real_name) > 1 and real_name[0].isupper():
                    without_first = real_name[1:].strip()
                    if without_first and (without_first[0].isupper() or re.match(r'^[A-Z]\.', without_first)):
                        real_name = without_first

                # Clean trailing punctuation and whitespace
                # But preserve trailing dots on initials (e.g., "K.K.")
                real_name = real_name.rstrip(':;, ')
                # Only strip trailing dot if it's not part of an initial
                if real_name.endswith('.') and not re.search(r'[A-Z]\.$', real_name):
                    real_name = real_name.rstrip('.')

                # Remove any "(by Hospital)" style annotations that aren't part of the name
                real_name = re.sub(r'\s*\(by\s+\w+\)', '', real_name)
                # Remove "(father)", "(mother)" etc. legal context annotations
                real_name = re.sub(r'\s*\((?:father|mother|daughter|son|husband|wife)\)', '', real_name, flags=re.IGNORECASE)

                if real_name and len(real_name) > 1:
                    return real_name
        if m:
            real_name = m.group(1).strip()
            # The first char might be an eaten letter prepended to the name
            # e.g., "AMikolik" -> the A is from "Appeal", real name is "Mikolik"
            # Check if removing first char still leaves a valid name
            if len(real_name) > 2 and real_name[0].isupper():
                without_first = real_name[1:].strip()
                if without_first and without_first[0].isupper():
                    real_name = without_first
                # Handle initials: "AK.K." -> remove A, keep "K.K."
                elif without_first and re.match(r'^[A-Z]\.', without_first):
                    real_name = without_first
            return real_name

        # Fallback: more aggressive cleanup for really messy names
        # Just take the first capitalized word(s) before any legal text
        tokens = re.split(r'\s+', name)
        clean_tokens = []
        for t in tokens:
            # Stop at legal fragment tokens
            if re.match(r'^(?:ppeal|ction|laintiff|efendant|ppealed|dditional|'
                        r'upplementary|otion|amages|osts|eave|ury|affirm|dismiss)',
                        t, re.IGNORECASE):
                break
            # Skip single eaten chars unless they're initials
            if len(t) == 1 and not t.endswith('.'):
                continue
            # Skip noise
            if t.strip() in ('', 'A', 'P', 'D', 'S', 'N', 'O', 'L', 'M'):
                continue
            clean_tokens.append(t)

        if clean_tokens:
            result = ' '.join(clean_tokens).strip()
            # Remove leading eaten char if present
            if len(result) > 2 and result[0].isupper() and result[1:2].isupper():
                # Like "AMikolik" -> could be eaten A
                pass  # already handled above
            if result:
                return result

    # Clean up "(two plaintiffs)" and similar annotations — always apply
    name = re.sub(r'\s*\(two\s+plaintiffs?\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(three\s+plaintiffs?\)', '', name, flags=re.IGNORECASE)

    # Clean up trailing legal fragments (full words, not truncated)
    name = re.sub(
        r'\s+(?:Appeal\s+(?:allowed|dismissed)|Action\s+dismissed|'
        r'No\s+liability|New\s+trial|Appealed\s+by|'
        r'Additional\s+reasons?|Supplementary\s+[Rr]easons?|'
        r'Motion\s+to\s+set|Damages\s+assessed|Costs\s+assessed).*$',
        '', name, flags=re.IGNORECASE
    ).strip()

    return name if name else original


def _extract_oj_number(citation: str) -> Optional[str]:
    """Extract first O.J. number from citation for deduplication."""
    m = re.search(r'\[\d{4}\]\s*O\.?J\.?\s*No\.?\s*(\d+)', citation)
    return m.group(1) if m else None


def _is_section_header(row: List[str]) -> Optional[str]:
    """Check if a CSV row is a section header. Returns section name or None."""
    non_empty = [c.strip() for c in row if c.strip()]
    if len(non_empty) != 1:
        return None

    candidate = non_empty[0].strip()

    # Direct match
    if candidate in VALID_SECTIONS:
        return candidate

    # Case-insensitive match
    lower = candidate.lower()
    if lower in _VALID_SECTIONS_LOWER:
        return _VALID_SECTIONS_LOWER[lower]

    return None


def _is_column_header(row: List[str]) -> bool:
    """Check if a CSV row is a column header row."""
    text = ' '.join(c.strip() for c in row)
    return 'Plaintiff' in text and ('Defendant' in text or 'Citation' in text)


def _is_data_row(row: List[str]) -> bool:
    """Check if a CSV row contains case data (has plaintiff name)."""
    if len(row) < 2:
        return False
    col0 = row[0].strip()
    col1 = row[1].strip()
    if not col0 or not col1:
        return False
    # Reject if col0 starts with $ or is a number
    if col0.startswith('$') or col0.startswith('(') or col0[0].isdigit():
        return False
    # Reject if it looks like a continuation fragment
    if col0.startswith('and ') or col0.startswith('or ') or col0.startswith('the '):
        return False
    return True


def parse_csv(csv_path: str = "data/damages_raw.csv") -> List[Dict[str, Any]]:
    """
    Parse the raw Camelot-extracted CSV into structured case data.

    Args:
        csv_path: Path to the raw CSV file

    Returns:
        List of parsed case dictionaries (raw records, not yet deduplicated)
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

    cases = []
    current_section = "General"
    current_case = None

    for i, row in enumerate(rows):
        # Skip header row (row 0 is numeric indices)
        if i == 0:
            continue

        # Skip empty rows
        if not any(c.strip() for c in row):
            continue

        # Check for section header
        section = _is_section_header(row)
        if section:
            current_section = section
            continue

        # Skip column headers
        if _is_column_header(row):
            continue

        # Check if this is a data row with plaintiff/defendant
        if _is_data_row(row):
            # Save previous case
            if current_case:
                cases.append(current_case)

            # Parse new case
            current_case = _parse_data_row(row, current_section)
        elif current_case:
            # This might be a continuation row — merge extra data
            _merge_continuation(current_case, row)

    # Don't forget the last case
    if current_case:
        cases.append(current_case)

    return cases


def _parse_data_row(row: List[str], section: str) -> Dict[str, Any]:
    """Parse a data row into a case dictionary."""
    # Column mapping (from the CSV structure):
    # 0: Plaintiff
    # 1: Defendant
    # 2: Year
    # 3: Citation
    # 4: Court
    # 5: Judge
    # 6: Sex/Age
    # 7: Non-Pecuniary General Damages
    # 8: Other Damages
    # 9: Comments
    # (some rows have data in cols 10-12 as overflow)

    def get(idx):
        return row[idx].strip() if idx < len(row) and row[idx].strip() else ""

    plaintiff_raw = get(0)
    defendant = get(1)
    year_text = get(2)
    citation = get(3)
    court_text = get(4)
    judge_text = get(5)
    sex_age_text = get(6)
    damages_text = get(7)
    other_damages_text = get(8)
    comments_text = get(9)

    # Collect overflow columns as additional comments
    overflow = []
    for ci in range(10, min(len(row), 13)):
        val = get(ci)
        if val:
            overflow.append(val)
    if overflow:
        comments_text = comments_text + " " + " ".join(overflow) if comments_text else " ".join(overflow)

    # Clean plaintiff name (remove legal status fragments)
    plaintiff = _clean_plaintiff_name(plaintiff_raw)

    # Parse structured fields
    case_name = f"{plaintiff} v. {defendant}" if defendant else plaintiff
    year = _extract_year(year_text)
    court = _extract_court(court_text) or _extract_court(citation)
    judges = _extract_judges(judge_text)
    sex, age = _extract_sex_age(sex_age_text)

    # Parse damages
    non_pec, is_provisional, multi_plaintiffs = _extract_non_pecuniary(damages_text)

    # Parse FLA claims from other_damages AND comments
    fla_from_other = _extract_fla_claims(other_damages_text)
    fla_from_comments = _extract_fla_claims(comments_text)

    # Combine and deduplicate
    all_fla = fla_from_other + fla_from_comments
    seen_fla = set()
    unique_fla = []
    for claim in all_fla:
        key = (claim['relationship'], claim['amount'])
        if key not in seen_fla:
            seen_fla.add(key)
            unique_fla.append(claim)

    # Parse other (pecuniary) damages
    other_damages = _extract_other_damages(other_damages_text)

    # Extract injuries from comments
    injuries = _extract_injuries(comments_text)

    # Build case
    case = {
        'case_name': case_name,
        'plaintiff_name': plaintiff,
        'defendant_name': defendant,
        'year': year,
        'citation': citation,
        'court': court,
        'judge': judges if judges else None,
        'sex': sex,
        'age': age,
        'non_pecuniary_damages': non_pec,
        'is_provisional': is_provisional,
        'injuries': injuries,
        'other_damages': other_damages,
        'family_law_act_claims': unique_fla,
        'comments': comments_text,
        'category': section,
        'region': [section],
        'source_page': None,
        'is_continuation': False,
    }

    # Handle multi-plaintiff cases
    if multi_plaintiffs:
        case['plaintiffs'] = multi_plaintiffs
        # Copy sex/age to first plaintiff
        if multi_plaintiffs and sex:
            multi_plaintiffs[0]['sex'] = sex
        if multi_plaintiffs and age:
            multi_plaintiffs[0]['age'] = age

    return case


def _merge_continuation(case: Dict[str, Any], row: List[str]) -> None:
    """Merge a continuation row's data into the current case."""
    # Continuation rows can have data in various columns
    text = ' '.join(c.strip() for c in row if c.strip())
    if not text or len(text) < 3:
        return

    # Check for FLA claims
    fla = _extract_fla_claims(text)
    if fla:
        existing_fla = case.get('family_law_act_claims', [])
        for claim in fla:
            key = (claim['relationship'], claim['amount'])
            exists = any(
                (c['relationship'], c['amount']) == key
                for c in existing_fla
            )
            if not exists:
                existing_fla.append(claim)
        case['family_law_act_claims'] = existing_fla

    # Check for other damages
    other = _extract_other_damages(text)
    if other:
        existing_other = case.get('other_damages', [])
        existing_other.extend(other)
        case['other_damages'] = existing_other

    # Check for additional non-pecuniary amount
    if '$' in text and not fla and not other:
        # Might be additional damages info
        amounts = _MONEY_RE.findall(text)
        for amt_str in amounts:
            amt = _parse_money(amt_str)
            if amt and amt > 0:
                # Add to other damages as unclassified
                od = case.get('other_damages', [])
                od.append({
                    'type': 'other',
                    'amount': amt,
                    'description': text[:100],
                })
                case['other_damages'] = od

    # Append to comments
    if case.get('comments'):
        case['comments'] = case['comments'] + ' ' + text
    else:
        case['comments'] = text

    # Re-extract injuries from updated comments
    case['injuries'] = _extract_injuries(case['comments'])


def deduplicate_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate cases that appear multiple times across PDF pages/sections.

    The same case often appears under multiple body-region sections
    (e.g., a patient with knee AND back injuries appears under both).
    Camelot also splits multi-page cases into separate rows.

    Strategy:
    1. Primary key: O.J. citation number (most reliable)
    2. Fallback key: case_name + year
    3. Merge: collect all regions/categories, keep best data from each record
    """
    # Group by O.J. number first
    oj_groups: Dict[str, List[Dict]] = defaultdict(list)
    no_oj: List[Dict] = []

    for case in cases:
        oj = _extract_oj_number(case.get('citation', ''))
        if oj:
            oj_groups[oj].append(case)
        else:
            no_oj.append(case)

    # Group no-OJ cases by case_name + year
    name_groups: Dict[Tuple, List[Dict]] = defaultdict(list)
    truly_unique: List[Dict] = []

    for case in no_oj:
        name = case.get('case_name', '').strip()
        year = case.get('year')
        if name and year:
            name_groups[(name, year)].append(case)
        elif name:
            # No year, try name alone but be conservative
            name_groups[(name, None)].append(case)
        else:
            truly_unique.append(case)

    # Merge each group into a single consolidated case
    result = []

    for oj_num, group in oj_groups.items():
        merged = _merge_case_group(group)
        result.append(merged)

    for key, group in name_groups.items():
        merged = _merge_case_group(group)
        result.append(merged)

    result.extend(truly_unique)

    return result


def _merge_case_group(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge a group of duplicate case records into one consolidated record."""
    if len(group) == 1:
        return group[0]

    # Use the record with the most data as base
    # Score by: has damages + has injuries + has comments + has citation
    def score(c):
        s = 0
        if c.get('non_pecuniary_damages'):
            s += 10
        if c.get('injuries'):
            s += len(c['injuries'])
        if c.get('comments'):
            s += min(len(c['comments']) // 50, 5)
        if c.get('citation'):
            s += 3
        if c.get('judge'):
            s += 2
        if c.get('sex'):
            s += 1
        if c.get('age'):
            s += 1
        return s

    group.sort(key=score, reverse=True)
    base = group[0].copy()

    # Collect all regions/categories across all records
    all_regions = set()
    all_categories = set()
    all_injuries = set()
    all_fla = []
    seen_fla_keys = set()
    all_other_damages = []
    all_citations = set()

    for case in group:
        # Regions
        regions = case.get('region', [])
        if isinstance(regions, list):
            all_regions.update(r for r in regions if r)
        elif regions:
            all_regions.add(regions)

        # Categories
        cat = case.get('category')
        if cat:
            all_categories.add(cat)

        # Injuries
        inj = case.get('injuries', [])
        if isinstance(inj, list):
            all_injuries.update(inj)

        # FLA claims (deduplicate by relationship + amount)
        for claim in case.get('family_law_act_claims', []):
            key = (claim.get('relationship'), claim.get('amount'))
            if key not in seen_fla_keys:
                seen_fla_keys.add(key)
                all_fla.append(claim)

        # Other damages (deduplicate by type + amount)
        for dam in case.get('other_damages', []):
            all_other_damages.append(dam)

        # Citations
        cit = case.get('citation', '')
        if cit:
            all_citations.add(cit)

        # Fill in missing fields from other records
        if not base.get('year') and case.get('year'):
            base['year'] = case['year']
        if not base.get('sex') and case.get('sex'):
            base['sex'] = case['sex']
        if not base.get('age') and case.get('age'):
            base['age'] = case['age']
        if not base.get('judge') and case.get('judge'):
            base['judge'] = case['judge']
        if not base.get('court') and case.get('court'):
            base['court'] = case['court']

        # Keep longest comments
        if len(case.get('comments', '')) > len(base.get('comments', '')):
            base['comments'] = case['comments']

    # NON-PECUNIARY DAMAGES: use the base record's value only (don't sum across dupes)
    # The base is already the best-scored record

    # Merge multi-plaintiff data — keep from the record that has them
    for case in group:
        if case.get('plaintiffs') and not base.get('plaintiffs'):
            base['plaintiffs'] = case['plaintiffs']
            break

    # Update merged fields
    base['region'] = sorted(all_regions) if all_regions else base.get('region', [])
    base['categories'] = sorted(all_categories) if all_categories else [base.get('category', 'General')]
    base['injuries'] = sorted(all_injuries) if all_injuries else base.get('injuries', [])
    base['family_law_act_claims'] = all_fla
    if all_other_damages:
        # Deduplicate other damages by (type, amount)
        seen = set()
        unique_od = []
        for d in all_other_damages:
            key = (d.get('type'), d.get('amount'))
            if key not in seen:
                seen.add(key)
                unique_od.append(d)
        base['other_damages'] = unique_od

    # Merge citations
    if len(all_citations) > 1:
        base['citation'] = '; '.join(sorted(all_citations))

    # Re-extract injuries from merged comments
    if base.get('comments') and not base.get('injuries'):
        base['injuries'] = _extract_injuries(base['comments'])

    return base


def fix_categories_from_pdf(
    cases: List[Dict[str, Any]],
    pdf_path: str = "2024damagescompendium.pdf",
) -> int:
    """
    Fix category/region assignments using section headers from the PDF.

    The raw CSV loses many section headers during Camelot extraction.
    This reads the PDF directly to map citations to their correct sections.

    Args:
        cases: Parsed case list (modified in place)
        pdf_path: Path to the source PDF

    Returns:
        Number of cases with improved category assignments
    """
    try:
        import PyPDF2
    except ImportError:
        print("PyPDF2 not available -- skipping PDF section mapping")
        return 0

    reader = PyPDF2.PdfReader(pdf_path)

    # Build page -> section mapping from "Page N SECTION" headers
    PARENT_ONLY = {
        "HEAD", "ARMS", "SPINE", "BODY", "LEGS", "SKIN",
        "FATAL INJURIES", "MOST SEVERE INJURIES", "MISCELLANEOUS",
    }
    NOISE_FRAGMENTS = ("$", "v.", "Meady", "Millar", "Pelletier", "El-Kodhr")

    page_sections: Dict[int, str] = {}
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        for line in text.split("\n")[:6]:
            m = re.match(r"Page\s+\d+\s+(.+)", line.strip())
            if m:
                section = m.group(1).strip()
                if any(frag in section for frag in NOISE_FRAGMENTS):
                    continue
                page_sections[i + 1] = section
                break

    # Forward-fill section assignments (skip parent-only headers)
    prev_section = "General"
    all_page_sections: Dict[int, str] = {}
    for pg in range(1, len(reader.pages) + 1):
        if pg in page_sections:
            s = page_sections[pg]
            if s not in PARENT_ONLY:
                prev_section = s
        all_page_sections[pg] = prev_section

    # Build citation O.J. number -> set of sections lookup
    # A case can appear in multiple sections (e.g., Knee AND Back)
    citation_sections: Dict[str, set] = defaultdict(set)
    for pg_num in range(4, len(reader.pages) + 1):
        text = reader.pages[pg_num - 1].extract_text() or ""
        section = all_page_sections.get(pg_num, "General")
        for m in re.finditer(r"\[\d{4}\]\s*O\.J\.\s*No\.\s*(\d+)", text):
            oj_num = m.group(1)
            citation_sections[oj_num].add(section)

    # Apply to parsed cases
    improved = 0
    for case in cases:
        cit = case.get("citation", "")
        oj_num = _extract_oj_number(cit)
        if oj_num and oj_num in citation_sections:
            sections = citation_sections[oj_num]
            # Normalize section names
            normalized = set()
            for s in sections:
                if s == "PAIN AND SUFFERING \u2013 MINOR CASES":
                    s = "Pain and Suffering \u2013 Minor Cases"
                normalized.add(s)

            primary = sorted(normalized)[0]
            if case.get("category") != primary:
                improved += 1
            case["category"] = primary
            case["region"] = sorted(normalized)
            case["categories"] = sorted(normalized)

        # Recover missing years from citation
        if not case.get("year"):
            ym = re.search(r"\[(\d{4})\]", cit)
            if ym:
                case["year"] = int(ym.group(1))

    return improved


def save_parsed_cases(cases: List[Dict[str, Any]], output_path: str = "damages_parsed.json") -> None:
    """Save parsed cases to JSON."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(cases)} cases to {output_path}")


if __name__ == "__main__":
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/damages_raw.csv"
    pdf_path = sys.argv[2] if len(sys.argv) > 2 else "2024damagescompendium.pdf"
    output_path = sys.argv[3] if len(sys.argv) > 3 else "damages_parsed.json"

    print(f"Parsing {csv_path}...")
    raw_cases = parse_csv(csv_path)
    print(f"  Raw records from CSV: {len(raw_cases)}")

    # Deduplicate cases that appear across multiple pages/sections
    print(f"\nDeduplicating...")
    cases = deduplicate_cases(raw_cases)
    print(f"  Unique cases after dedup: {len(cases)}")

    # Fix categories using PDF section headers
    if Path(pdf_path).exists():
        print(f"\nFixing categories from {pdf_path}...")
        improved = fix_categories_from_pdf(cases, pdf_path)
        print(f"  Improved {improved} category assignments")
    else:
        print(f"\nPDF not found at {pdf_path} -- skipping section mapping")

    # Statistics
    with_damages = sum(1 for c in cases if c.get('non_pecuniary_damages'))
    with_injuries = sum(1 for c in cases if c.get('injuries'))
    with_fla = sum(1 for c in cases if c.get('family_law_act_claims'))
    with_judges = sum(1 for c in cases if c.get('judge'))
    with_citation = sum(1 for c in cases if c.get('citation'))
    with_year = sum(1 for c in cases if c.get('year'))
    with_multi_region = sum(1 for c in cases if len(c.get('region', [])) > 1)

    print(f"\nParsed {len(cases)} unique cases:")
    print(f"  With damages:      {with_damages} ({with_damages/len(cases)*100:.0f}%)")
    print(f"  With injuries:     {with_injuries} ({with_injuries/len(cases)*100:.0f}%)")
    print(f"  With FLA claims:   {with_fla} ({with_fla/len(cases)*100:.0f}%)")
    print(f"  With judges:       {with_judges} ({with_judges/len(cases)*100:.0f}%)")
    print(f"  With citations:    {with_citation} ({with_citation/len(cases)*100:.0f}%)")
    print(f"  With year:         {with_year} ({with_year/len(cases)*100:.0f}%)")
    print(f"  Multi-region:      {with_multi_region} ({with_multi_region/len(cases)*100:.0f}%)")

    from collections import Counter
    cats = Counter(c.get('category', 'UNKNOWN') for c in cases)
    print(f"\nCategories ({len(cats)}):")
    for cat, cnt in cats.most_common():
        print(f"  {cat}: {cnt}")

    save_parsed_cases(cases, output_path)
