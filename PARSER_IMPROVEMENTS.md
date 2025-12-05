# Parser Improvements - Plaintiff & Injury Extraction

## Issues Identified

### 1. Incomplete Plaintiff Data (167 cases affected)
- Plaintiffs appearing with no name, injuries, or comments
- "Phantom plaintiffs" with only damage amounts but no other data
- Example: Dusk v. Malone had a p2 plaintiff with $40,000 damages but no name/injuries/comments

### 2. Missing Injuries (82 cases affected)
- Cases with NO injuries extracted despite having injury descriptions in comments
- LLM not extracting injuries from narrative text in comments field
- Example: "plaintiff's head bounced off the pavement twice" not being extracted as injuries

### 3. Continuation Row Issues
- Continuation rows not properly merging plaintiff and FLA claim data
- Some continuation rows being treated as new cases with null case_name

### 4. FLA Relationship Confusion
- User concern about distinguishing Family Law Act claims from injury categories
- FLA claims are relationship-based awards (spouse, child, parent making claims)
- These should not be confused with injury types

## Fixes Implemented

### 1. Enhanced LLM Prompt (`damages_parser_table.py` lines 87-182)

**Critical Rules Added:**

#### Injury Extraction (Most Important)
- **ALWAYS** extract injuries from Comments field, even if described narratively
- Look for injury descriptions in ALL text fields
- Extract specific medical conditions, body parts, symptoms, diagnoses
- Examples added to prompt:
  - "plaintiff's head bounced off the pavement twice" → ["head injury", "head trauma"]
  - "soft tissue injuries to neck and back" → ["soft tissue injury to neck", "soft tissue injury to back"]
- DO NOT leave injuries array empty if ANY injury description exists in comments
- For mass casualty cases, copy injury descriptions to all affected plaintiffs if individual details not specified

#### Multi-Plaintiff Cases
- Use "plaintiffs" array ONLY when there are truly MULTIPLE distinct plaintiffs
- Each plaintiff entry MUST have a name (even if generic like "Plaintiff 2" or "Son")
- **NEVER** create a plaintiff entry without plaintiff_name - omit entirely if no name found
- Extract plaintiff-specific injuries by analyzing comments:
  - Look for patterns like "P1 suffered X", "plaintiff Mary had Y", "the son injured his Z"
  - If comments mention "one plaintiff had leg injury, another had arm injury", create separate plaintiffs with respective injuries
  - If generic description applies to all, copy to all plaintiff entries
- Include ALL plaintiffs mentioned in row with their specific details
- The plaintiffs array should contain p1, p2, p3... for ALL plaintiffs (including primary)

#### Continuation Rows
- Set "is_continuation": true ONLY if BOTH case name AND citation are missing/null
- If there's a case name OR citation, it's a NEW case (is_continuation: false)
- Continuation rows usually contain additional damages, injuries, or comments

#### FLA Claims - Separate from Injuries
- FLA claims represent awards to FAMILY MEMBERS for loss of care/companionship
- DO NOT confuse these with injury types - they are relationship-based claims
- Use gender-specific terms when clear: "son"/"daughter", "father"/"mother", etc.
- Use gender-neutral ONLY when unspecified
- Handle plurals by creating separate entries

#### Data Quality
- DO NOT create incomplete plaintiff entries (missing name AND injuries AND damages)
- If cannot extract complete plaintiff information, use top-level fields only (no plaintiffs array)

### 2. Improved Continuation Row Merging (`damages_parser_table.py` lines 668-739)

**New Features:**
- Merge `family_law_act_claims` from continuation rows
- Merge `plaintiffs` array properly:
  - Match plaintiffs by `plaintiff_id`
  - Merge injuries for matching plaintiffs
  - Append comments for matching plaintiffs
  - Update damages if higher
  - Add new plaintiffs if not already present

**Example:**
```python
# Before: FLA claims and plaintiffs from continuation rows were lost
# After: Properly merged into existing case
```

### 3. Post-Processing Cleanup (`damages_parser_table.py` lines 741-800)

**New `clean_up_plaintiff_data()` function:**

**Rules:**
1. Remove plaintiffs with no name AND no injuries AND no damages
2. If all plaintiffs are removed, remove the plaintiffs array entirely
3. Remove cases with no case_name (likely failed continuation rows)
4. Ensure top-level injuries include all plaintiff injuries

**Logic:**
- Keep plaintiff if they have: name OR (injuries OR damages OR comments)
- This allows plaintiffs with damages but generic names like "Plaintiff 2"
- Aggregates all plaintiff injuries to top-level injuries array
- Removes phantom entries that provide no useful information

## Expected Results

### Before Improvements:
- 167 cases with incomplete plaintiff data
- 82 cases with NO injuries extracted
- Cases with null case_name appearing in results
- Phantom plaintiffs with only damage amounts

### After Improvements:
- Plaintiffs only created when meaningful data exists
- Injuries extracted from narrative comments
- Proper merging of continuation rows including plaintiffs and FLA claims
- Clean data hierarchy: Case → Plaintiff → Details per plaintiff
- Better handling of:
  - Mass casualties (copy descriptions when appropriate)
  - Individual stories (extract separately when available)
  - Multiple plaintiffs with different injuries (distinguish properly)

## Data Hierarchy

The improved parser ensures the correct hierarchy:

```
Case
├── case_name (required)
├── year, citation, court, judge
├── injuries (aggregated from all plaintiffs)
├── comments (case-level comments)
├── family_law_act_claims (relationship-based awards)
└── plaintiffs (array, only if multiple distinct plaintiffs)
    ├── p1
    │   ├── plaintiff_name (required)
    │   ├── injuries (plaintiff-specific)
    │   ├── non_pecuniary_damages
    │   └── comments (plaintiff-specific)
    ├── p2
    │   └── ... (same structure)
    └── p3
        └── ... (same structure)
```

## Testing Recommendations

1. Re-parse the PDF with the improved parser
2. Check statistics:
   - Count cases with null case_name (should be 0)
   - Count plaintiffs with no name AND no injuries (should be 0)
   - Count cases with no injuries but comments describing injuries (should be much lower)
3. Manually review a few multi-plaintiff cases to ensure proper extraction
4. Verify FLA claims are properly categorized

## Notes

- The prompt is now ~2x longer but provides critical guidance for accurate extraction
- The cleanup function removes ~10-15 incomplete entries (estimated)
- Top-level injuries now include all plaintiff injuries for better searchability
- FLA claims remain separate from injury categories as they represent different concepts
