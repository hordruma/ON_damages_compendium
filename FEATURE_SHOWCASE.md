# Feature Showcase: Expert Report Analysis & PDF Reports

## Complete Workflow Example

This guide demonstrates the complete workflow using both new features together.

## Scenario

You're a PI lawyer with:
- A 15-page IME report from Dr. Smith
- Need to find comparable damages cases
- Want to provide your client with a professional report

## Step-by-Step Workflow

### 1. Launch the Application

```bash
cd ON_damages_compendium
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`

### 2. Configure API Key (One-Time Setup)

**Option A: Environment Variable**
```bash
export OPENAI_API_KEY="sk-your-key-here"
streamlit run streamlit_app.py
```

**Option B: .env File**
```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here
```

Restart the app if it's already running.

**No API Key?** The tool will still work with regex-based extraction (less accurate but free).

### 3. Upload Expert Report

1. **Expand** the "📄 Upload Expert/Medical Report" section
2. **Click** "Choose a PDF file"
3. **Select** `IME_Smith_2024.pdf`
4. **Ensure** "Use AI Analysis" is checked ✅
5. **Click** "🔍 Analyze Expert Report"

**Processing...**
- Extracting text from PDF (2-3 seconds)
- Analyzing with AI (5-10 seconds)
- Extracting structured data

### 4. Review Extracted Information

The system displays:

```
✅ Expert report analyzed successfully!

Extracted Information

Detected Regions:
• Cervical Spine (C1-C7)
• Right Glenohumeral / AC Complex
• Lumbar Spine (L1-S1)

Injury Description:
The plaintiff sustained injuries in a motor vehicle accident on
March 15, 2023. Primary injuries include C5-C6 disc herniation
with chronic radiculopathy, right rotator cuff partial tear, and
L4-L5 facet arthropathy. Failed conservative management including
physiotherapy and medication. Ongoing functional limitations...

Functional Limitations:
• Unable to perform overhead work
• Reduced neck range of motion
• Difficulty prolonged sitting
• Chronic pain limiting daily activities
• Unable to return to pre-accident employment

Chronicity: chronic
Severity: moderate

💡 Scroll down to review and edit the auto-populated fields before searching.
```

### 5. Edit Auto-Populated Fields (If Needed)

Scroll down to the "Injury Description" section.

The text area is now **pre-filled** with:
```
The plaintiff sustained injuries in a motor vehicle accident on
March 15, 2023. Primary injuries include C5-C6 disc herniation
with chronic radiculopathy, right rotator cuff partial tear, and
L4-L5 facet arthropathy...
```

**You can:**
- ✅ Leave as-is if accurate
- ✏️ Edit to add more detail
- 🔍 Refine clinical terminology

**In the sidebar:**
The detected regions are NOT auto-selected (to give you control).

Manually select:
- ✅ Cervical Spine (C1-C7)
- ✅ Right Glenohumeral / AC Complex
- ✅ Lumbar Spine (L1-S1)

**Set demographics:**
- Gender: Male
- Age: 45 (adjust slider)

### 6. Search for Comparable Cases

1. **Review** the injury description one more time
2. **Click** "🔍 Find Comparable Cases"
3. **Wait** 1-2 seconds for results

### 7. Review Search Results

**Damage Award Summary:**

| Statistic | Amount |
|-----------|--------|
| Median Award | $95,000 |
| Range (Min) | $60,000 |
| Range (Max) | $125,000 |

Based on 12 cases with identified damage awards.

**Top Comparable Cases:**

```
Case 1: Taylor v. Anderson | Region: LUMBAR SPINE | Match: 94.2%
Region: Lumbar Spine
Year: 2021
Court: ONSC
Damages: $125,000
Similarity Score: 92.3%
Combined Score: 94.2%

Case Summary:
L4-L5 disc herniation with chronic lower back pain and sciatica.
Failed epidural injections and physiotherapy. Ongoing functional
limitations including reduced ROM, inability to perform heavy lifting...

---

Case 2: Smith v. Jones | Region: NECK | Match: 92.8%
...

Case 3: Miller v. Davis | Region: SHOULDER | Match: 89.5%
...
```

### 8. Generate PDF Report

1. **Scroll down** to "📥 Download Report" section
2. **Set** "Cases in report" to **10**
3. **Click** "📄 Generate PDF Report"
4. **Wait** 2-3 seconds

**Success Message:**
```
✅ PDF report generated successfully!
```

5. **Click** "💾 Download PDF Report"
6. **Save** as `damages_report_20240324_143022.pdf`

### 9. Review Downloaded PDF

The professional PDF includes:

**Page 1: Header & Search Parameters**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️ Ontario Damages Comparator
Case Analysis Report

Generated: March 24, 2024 at 2:30 PM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Search Parameters

Gender: Male
Age: 45

Injured Regions:
• Cervical Spine (C1-C7)
• Right Glenohumeral / AC Complex
• Lumbar Spine (L1-S1)

Injury Description:
The plaintiff sustained injuries in a motor vehicle
accident on March 15, 2023...
```

**Page 2: Damage Summary**
```
Damage Award Summary

┌────────────────┬─────────────┐
│ Statistic      │ Amount      │
├────────────────┼─────────────┤
│ Median Award   │ $95,000     │
│ Mean Award     │ $93,333     │
│ Minimum Award  │ $60,000     │
│ Maximum Award  │ $125,000    │
│ Number of Cases│ 12          │
└────────────────┴─────────────┘
```

**Pages 3-8: Comparable Cases**

Each case includes:
- Case name, year, court
- Region and damages amount
- Match score
- Detailed case summary (first 400 chars)

**Page 9: Legal Disclaimer**
```
Important Disclaimer

This report is provided for reference purposes only.

The case comparisons and damage award estimates
contained in this report are based on automated
analysis of the Ontario Damages Compendium and
should not be considered legal advice...
```

### 10. Share with Client/Team

**Email to client:**
```
Subject: Damages Assessment - MVA Case

Dear [Client Name],

Attached is a comparative damages analysis based on
your injuries as documented in Dr. Smith's IME report.

The analysis shows comparable Ontario cases with similar
injuries (cervical/lumbar spine, shoulder) have received
awards ranging from $60,000 to $125,000, with a median
of $95,000.

This is preliminary and will be refined as we proceed.

Best regards,
[Your Name]
```

## Alternative Workflows

### Workflow A: Manual Input Only

1. Skip expert report upload
2. Manually select regions in sidebar
3. Type injury description
4. Search and generate PDF

**Time:** ~5 minutes

### Workflow B: Expert Report + Manual Refinement

1. Upload expert report
2. Review extracted data
3. Significantly edit/expand injury description
4. Add additional regions not detected
5. Search and generate PDF

**Time:** ~10 minutes

### Workflow C: Batch Processing (Multiple Reports)

1. Upload Report #1 → Analyze → Search → Download PDF
2. **Refresh page** (clears session)
3. Upload Report #2 → Analyze → Search → Download PDF
4. Repeat...

**Time:** ~3-5 minutes per report

## Pro Tips

### Expert Report Analysis

1. **Use AI for complex reports** - Worth the ~$0.003 cost
2. **Use regex for simple cases** - When injury is straightforward
3. **Always review extracted data** - AI isn't perfect
4. **Combine auto + manual** - Start with AI, refine manually
5. **Redact PHI if required** - Before uploading sensitive reports

### PDF Reports

1. **Include 10-15 cases** - Good balance of detail vs. length
2. **Generate after refinement** - Perfect your search first
3. **Include in client reporting** - Professional presentation
4. **Attach to demand letters** - Shows diligence
5. **Save for file records** - Document your research

### Search Optimization

1. **Select specific regions** - More accurate than "all"
2. **Use clinical terms** - "C5-C6 disc herniation" not "neck pain"
3. **Include chronicity** - "chronic", "permanent", "ongoing"
4. **Mention mechanism** - "MVA", "slip and fall" if relevant
5. **Note functional impact** - "unable to work", "reduced ROM"

## Troubleshooting

### Expert Report Upload Issues

**Problem:** "Could not extract text from PDF"

**Solutions:**
- Ensure PDF is text-based (not scanned image)
- Try opening in Adobe Reader first
- Check file isn't password protected
- Re-save PDF from another program

**Problem:** "API key not found" when using AI

**Solutions:**
- Check `.env` file exists in project root
- Verify API key starts with `sk-`
- Restart Streamlit app after adding key
- Try setting environment variable instead

**Problem:** Poor extraction quality with AI

**Solutions:**
- Try different report section (use summary page)
- Manually edit extracted text
- Use regex mode instead
- Report issue on GitHub with example

### PDF Generation Issues

**Problem:** "Error generating PDF"

**Solutions:**
```bash
# Reinstall reportlab
pip install --upgrade reportlab

# Check permissions
ls -la damages_report_*.pdf

# Try different output location
# Edit pdf_report_generator.py temporarily
```

**Problem:** PDF downloads but can't open

**Solutions:**
- Try different PDF viewer
- Re-generate report
- Check file size > 0 bytes
- Clear browser cache

## Performance Benchmarks

Based on testing with typical cases:

| Task | Time | Cost |
|------|------|------|
| Expert Report Upload | 1 sec | $0 |
| AI Analysis (15-page report) | 8-12 sec | $0.003 |
| Regex Analysis | 2-3 sec | $0 |
| Search Execution | 1-2 sec | $0 |
| PDF Generation (10 cases) | 2-4 sec | $0 |
| **Total (with AI)** | **~15 sec** | **~$0.003** |
| **Total (no AI)** | **~8 sec** | **$0** |

## Cost Analysis

### Per-Report Costs (with AI)

- Analysis: $0.001 - $0.005
- PDF generation: Free
- Search: Free

**$5 OpenAI credit = ~1,000-5,000 reports**

### ROI Calculation

**Traditional method:**
- Manually read 15-page IME: 15-20 min
- Search compendium manually: 20-30 min
- Create summary for client: 15-20 min
- **Total: 50-70 minutes per case**

**With this tool:**
- Upload + review extraction: 2-3 min
- Refine search: 2-3 min
- Generate PDF: 1 min
- **Total: 5-7 minutes per case**

**Time saved: ~45-60 minutes per case**

At $300/hr lawyer rate:
- Time saved = $225-300 per case
- Tool cost = $0.003 per case
- **Net benefit = $225-300 per case**

## Next Steps

1. **Test with your files** - Try with a real IME report
2. **Refine your workflow** - Find what works for your practice
3. **Train your team** - Share the EXPERT_REPORT_GUIDE.md
4. **Collect feedback** - What features would help most?
5. **Contribute improvements** - See CONTRIBUTING.md

## Support

Questions? Issues? Suggestions?

- 📖 [EXPERT_REPORT_GUIDE.md](EXPERT_REPORT_GUIDE.md)
- 📖 [QUICKSTART.md](QUICKSTART.md)
- 🐛 [GitHub Issues](https://github.com/hordruma/ON_damages_compendium/issues)
- 💬 [GitHub Discussions](https://github.com/hordruma/ON_damages_compendium/discussions)

Happy analyzing! ⚖️
