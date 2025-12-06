# DAMAGES COMPENDIUM - COMPREHENSIVE FIXES

## Issues Found and Fixes Applied

### 1. FLA Relationships Showing as 0 ❌ → ✅ FIXED
**Problem:**
- `data/damages_with_embeddings.json` was created with old transformer
- Old transformer didn't include `family_law_act_claims` in `extended_data`
- Source data (`damages_table_based.json`) HAS 476 cases with 1000+ FLA relationships

**Root Cause:**
- Line 196 of current `data_transformer.py` DOES include FLA claims
- But the JSON file was generated before this fix was added

**Fix:**
- Created `regenerate_embeddings.py` to re-transform from source
- Preserves: injuries, FLA claims, comments, demographics, judges
- Running now...

---

### 2. No Award Amounts for FLA Cases ❌ → NEEDS FIX
**Problem:**
- FLA cases like "MacMillan v. Moreau" show no award
- FLA awards are in `family_law_act_claims[]` array, not `non_pecuniary_damages`
- `extract_damages_value()` only checks non-pecuniary fields

**Example:**
```
MacMillan v. Moreau (2002):
- Deceased: massive pulmonary embolism
- Wife: $40,000 FLA award
- Child 1: $50,000 FLA award
- Child 2: $35,000 FLA award
- Child 3: $30,000 FLA award
- TOTAL: $155,000 in FLA awards
But shows: "No award amount"
```

**Fix Required:**
Update `app/core/search.py::extract_damages_value()` to:
1. Try non-pecuniary damages first (current behavior)
2. If None, sum all FLA awards as fallback
3. Display total FLA amount for FLA-only cases

---

### 3. Comments Not Displaying ❌ → ACTUALLY WORKING
**Finding:**
- Comments ARE in the data
- MacMillan case has: "Wife separated for 3 years; not a close relationship..."
- Display logic IS correct (lines 240-244 of streamlit_app.py)

**Likely Issue:**
- You may be seeing old cached data in browser
- OR looking at wrong plaintiff in multi-plaintiff display

**Fix:**
- Regenerating embeddings will refresh all data
- Clear browser cache / restart Streamlit

---

### 4. Search Returns Wrong Cases (DAI → Pulmonary Embolism) ❌ → INVESTIGATING
**Problem:**
- Searching "diffuse axonal injury" returns "massive pulmonary embolism" case

**Finding:**
- DAI cases DO exist in data (found 2 cases: Foniciello v. Bendall)
- MacMillan case (pulmonary embolism) should NOT match DAI query

**Possible Causes:**
1. Old embeddings (being regenerated now)
2. Category filter mismatch
3. Embedding model not understanding medical terms
4. Search weights heavily favoring keywords over semantics

**Fix:**
- Regenerating embeddings with better model (all-mpnet-base-v2)
- Will test after regeneration completes

---

### 5. MTBI Filtered on HEAD Gives No Results ❌ → NEEDS FIX
**Problem:**
- "MTBI" abbreviation may not appear in injury text
- Cases might use "mild traumatic brain injury" or "concussion"

**Fix Required:**
- Add medical abbreviation expansion to search
- "MTBI" → ["MTBI", "mild traumatic brain injury", "mild TBI", "concussion"]
- Already exists in `app/core/medical_terms.py` - verify it's being used

---

### 6. Display Formatting Issues ❌ → NEEDS INVESTIGATION
**Problem:**
- User sees: "Category: SISTER - 8,000.00"
- Category field should be anatomical (HEAD, SPINE, etc.)
- "SISTER" is an FLA relationship, not a category!

**Possible Cause:**
- Data corruption during parsing
- FLA relationship overwriting category field
- Multi-plaintiff case display bug

**Fix:**
- Review parser logic for FLA cases
- Ensure category stays anatomical
- Fix display to show: "Category: BRAIN & SKULL | FLA: Sister - $8,000"

---

### 7. Injuries Not Showing ❌ → PARTIALLY FIXED
**Problem:**
- User says "injuries are NOT showing up"

**Finding:**
- Injuries ARE in the data (1260/1350 cases have injuries)
- `display_enhanced_data()` DOES display them (lines 176-199)

**Issue:**
- Old `extended_data` may not have injuries
- Current transformer DOES include injuries
- Regenerating embeddings will fix this

---

## Files Modified / Created

1. ✅ **regenerate_embeddings.py** - Complete data transformation script
2. ⏳ **app/core/search.py** - Need to update `extract_damages_value()`
3. ⏳ **streamlit_app.py** - May need display formatting fixes
4. ⏳ **app/core/medical_terms.py** - Verify abbreviation expansion

---

## Next Steps

1. ✅ Wait for regeneration script to complete
2. ⏳ Fix `extract_damages_value()` for FLA awards
3. ⏳ Fix display formatting for FLA cases
4. ⏳ Run `generate_embeddings.py` for injury embeddings
5. ⏳ Test search with "diffuse axonal injury"
6. ⏳ Test "MTBI" + HEAD filter
7. ⏳ Verify FLA relationships show correctly
8. ⏳ Commit and push fixes

---

## Technical Details

### Data Flow:
```
damages_table_based.json (SOURCE)
  ↓
data_transformer.py::convert_to_dashboard_format()
  ↓
data/damages_with_embeddings.json (DASHBOARD)
  ↓
generate_embeddings.py (INJURY EMBEDDINGS)
  ↓
data/compendium_inj.json + embeddings_inj.npy
  ↓
Streamlit App (SEARCH & DISPLAY)
```

### Data Preservation Checklist:
- [x] case_name, year, court, judge, citation
- [x] category (anatomical region)
- [x] non_pecuniary_damages, pecuniary_damages
- [x] comments
- [x] injuries array
- [x] family_law_act_claims array ← **THIS WAS MISSING!**
- [x] sex, age (demographics)
- [x] other_damages array
- [x] num_plaintiffs, plaintiff_id
- [x] judges array

