# Fix for App Breakage After Data Update

## Issue Summary

After the "new data" commit (44cf305), the app crashed with an `AttributeError` when trying to load the Judge Analytics tab.

## Root Cause

The issue was a **bug in the Judge Analytics code** introduced in commit `067ef4f` (feat: Add inflation adjustment to judge analytics).

### The Bug

Two Plotly method calls used incorrect method names:

```python
# ❌ WRONG - these methods don't exist
fig.update_yaxis(tickformat='$,.0f')  # Line 252
fig.update_xaxis(tickformat='$,.0f')  # Line 362

# ✅ CORRECT - note the plural 'axes'
fig.update_yaxes(tickformat='$,.0f')
fig.update_xaxes(tickformat='$,.0f')
```

### Error Details

```
AttributeError in app/ui/judge_analytics.py, line 252
    fig.update_yaxis(tickformat='$,.0f')
    ^^^^^^^^^^^^^^^^
```

The error occurred when:
1. The app initialized and loaded the Judge Analytics page
2. It tried to create charts using invalid Plotly methods
3. Python raised `AttributeError` because `update_yaxis()` doesn't exist on Figure objects

## Solution

**Fixed in commit `1553348`**

Changed two lines in `app/ui/judge_analytics.py`:
- Line 252: `update_yaxis` → `update_yaxes`
- Line 362: `update_xaxis` → `update_xaxes`

## Why This Wasn't Caught Earlier

This bug was introduced in the judge analytics feature but only manifested when:
- The app tried to display the Judge Analytics tab
- Plotly attempted to format the chart axes

The bug was in dormant code that wasn't executed during initial testing.

## Data Quality Note

The recent data update actually **improved** data quality:

✅ **Better quality**: Removed 7 junk/header entries
✅ **Richer metadata**: Added `extended_data` with judges, citations, injuries
✅ **Cleaner structure**: All 805 cases now have proper case names and data
✅ **More searchable**: Better summary text generation for embeddings

The data update did not cause the bug - it simply revealed an existing code error.

## Verification

After the fix, both tabs work correctly:
- ✅ **Case Search tab**: Working (was always working)
- ✅ **Judge Analytics tab**: Now working (was broken)

To verify:
1. Pull the latest changes
2. Restart the Streamlit app
3. Navigate to the "Judge Analytics" tab
4. Charts should now display without errors
