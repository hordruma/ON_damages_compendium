"""
Ontario Damages Compendium — Deterministic CSV Parser

Parses the raw Camelot-extracted CSV without requiring an LLM.
Uses regex patterns for structured field extraction (names, citations,
damages amounts, demographics, injuries, FLA claims).

This parser captures ~1400 cases vs the ~635 from the LLM pipeline,
and runs in seconds instead of hours.
"""

import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


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
        List of parsed case dictionaries in AI-parsed format
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

    plaintiff = get(0)
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
        print("PyPDF2 not available — skipping PDF section mapping")
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

    # Build citation O.J. number -> section lookup
    citation_section: Dict[str, str] = {}
    for pg_num in range(4, len(reader.pages) + 1):
        text = reader.pages[pg_num - 1].extract_text() or ""
        section = all_page_sections.get(pg_num, "General")
        for m in re.finditer(r"\[\d{4}\]\s*O\.J\.\s*No\.\s*(\d+)", text):
            oj_num = m.group(1)
            citation_section[oj_num] = section

    # Apply to parsed cases
    improved = 0
    for case in cases:
        cit = case.get("citation", "")
        m = re.search(r"\[\d{4}\]\s*O\.J\.\s*No\.\s*(\d+)", cit)
        if m:
            oj_num = m.group(1)
            if oj_num in citation_section:
                new_section = citation_section[oj_num]
                # Normalize case
                if new_section == "PAIN AND SUFFERING – MINOR CASES":
                    new_section = "Pain and Suffering – Minor Cases"
                if case.get("category") != new_section:
                    improved += 1
                case["category"] = new_section
                case["region"] = [new_section]

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
    cases = parse_csv(csv_path)

    # Fix categories using PDF section headers
    if Path(pdf_path).exists():
        print(f"\nFixing categories from {pdf_path}...")
        improved = fix_categories_from_pdf(cases, pdf_path)
        print(f"  Improved {improved} category assignments")
    else:
        print(f"\nPDF not found at {pdf_path} — skipping section mapping")

    # Statistics
    with_damages = sum(1 for c in cases if c.get('non_pecuniary_damages'))
    with_injuries = sum(1 for c in cases if c.get('injuries'))
    with_fla = sum(1 for c in cases if c.get('family_law_act_claims'))
    with_judges = sum(1 for c in cases if c.get('judge'))
    with_citation = sum(1 for c in cases if c.get('citation'))
    with_year = sum(1 for c in cases if c.get('year'))

    print(f"\nParsed {len(cases)} cases:")
    print(f"  With damages:    {with_damages} ({with_damages/len(cases)*100:.0f}%)")
    print(f"  With injuries:   {with_injuries} ({with_injuries/len(cases)*100:.0f}%)")
    print(f"  With FLA claims: {with_fla} ({with_fla/len(cases)*100:.0f}%)")
    print(f"  With judges:     {with_judges} ({with_judges/len(cases)*100:.0f}%)")
    print(f"  With citations:  {with_citation} ({with_citation/len(cases)*100:.0f}%)")
    print(f"  With year:       {with_year} ({with_year/len(cases)*100:.0f}%)")

    from collections import Counter
    cats = Counter(c.get('category', 'UNKNOWN') for c in cases)
    print(f"\nCategories ({len(cats)}):")
    for cat, cnt in cats.most_common():
        print(f"  {cat}: {cnt}")

    save_parsed_cases(cases, output_path)
