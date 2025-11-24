# Expert Report Analysis Guide

## Overview

The Ontario Damages Compendium tool now supports automatic analysis of medical and expert reports. Upload a PDF report and the system will extract:

- **Injured body regions** - Automatically detected anatomical areas
- **Injury descriptions** - Clinical details extracted from the report
- **Functional limitations** - Identified restrictions and impairments
- **Chronicity** - Whether injuries are acute, chronic, or permanent
- **Severity** - Mild, moderate, or severe classification
- **Demographics** - Age and gender if mentioned

## How It Works

### Method 1: AI-Powered Analysis (Recommended)

Uses a Large Language Model (LLM) to intelligently parse the report and extract structured medical information.

**Advantages:**
- High accuracy
- Understands medical terminology and context
- Handles varied report formats
- Extracts nuanced details

**Requirements:**
- OpenAI API key OR Anthropic API key
- Internet connection

**Cost:**
- ~$0.001-0.005 per report (very low)
- Uses efficient models (GPT-4o-mini or Claude Haiku)

### Method 2: Regex-Based Extraction (Fallback)

Uses pattern matching and keyword detection.

**Advantages:**
- No API key required
- Works offline
- Free

**Limitations:**
- Less accurate
- May miss context
- Rigid pattern matching

## Setup

### 1. Get an API Key

#### Option A: OpenAI (Recommended)

1. Go to https://platform.openai.com/api-keys
2. Create an account / sign in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)
5. Add credits to your account ($5 minimum, lasts a very long time)

#### Option B: Anthropic

1. Go to https://console.anthropic.com/
2. Create an account / sign in
3. Navigate to API Keys
4. Create a new key
5. Copy the key (starts with `sk-ant-`)

### 2. Configure the API Key

#### Method 1: Environment Variable (Recommended for Production)

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
streamlit run streamlit_app.py
```

**Windows:**
```cmd
set OPENAI_API_KEY=sk-your-key-here
streamlit run streamlit_app.py
```

**Windows PowerShell:**
```powershell
$env:OPENAI_API_KEY="sk-your-key-here"
streamlit run streamlit_app.py
```

#### Method 2: .env File (Recommended for Development)

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your key:
   ```
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

3. Save and run the app:
   ```bash
   streamlit run streamlit_app.py
   ```

**Note:** The `.env` file is gitignored and won't be committed.

## Usage

### Step-by-Step

1. **Open the app**
   ```bash
   streamlit run streamlit_app.py
   ```

2. **Expand "Upload Expert/Medical Report"** section

3. **Upload PDF**
   - Click "Choose a PDF file"
   - Select medical report, IME, expert opinion, etc.

4. **Select analysis method**
   - ✅ "Use AI Analysis" - Use LLM (requires API key)
   - ❌ "Use AI Analysis" - Use regex fallback (no API key)

5. **Click "Analyze Expert Report"**
   - Wait 5-15 seconds for analysis
   - Review extracted information

6. **Edit auto-populated fields**
   - Injury description is pre-filled
   - Detected regions are highlighted
   - Make any necessary corrections

7. **Run search**
   - Click "Find Comparable Cases"
   - Review results

8. **Download PDF report** (optional)
   - Click "Generate PDF Report"
   - Download professional formatted report

## Supported Report Types

### Works Best With:

- ✅ Medical-legal reports
- ✅ Independent Medical Examinations (IME)
- ✅ Expert opinions
- ✅ Functional capacity evaluations
- ✅ Occupational therapy assessments
- ✅ Physiotherapy reports
- ✅ Orthopedic assessments
- ✅ Neuropsychological evaluations

### May Work With:

- ⚠️ Hospital discharge summaries
- ⚠️ Diagnostic imaging reports (MRI, CT, X-ray)
- ⚠️ Treatment notes
- ⚠️ Rehabilitation plans

### Won't Work Well With:

- ❌ Scanned handwritten notes
- ❌ Low-quality scans
- ❌ Password-protected PDFs
- ❌ Image-only PDFs (without OCR)

## Tips for Best Results

1. **Use clear, well-formatted PDFs**
   - Digital PDFs are better than scans
   - Text-based PDFs work best
   - Good quality scans with OCR are acceptable

2. **Full reports are better than excerpts**
   - Complete medical context improves extraction
   - Summary sections are most useful

3. **Review and edit extracted data**
   - AI isn't perfect - always verify
   - Clinical terminology may be simplified
   - Add missing details manually

4. **Combine with manual selection**
   - Use extracted regions as a starting point
   - Add additional regions if needed
   - Refine injury description for precision

## Troubleshooting

### "API key not found"

**Problem:** API key not configured

**Solution:**
1. Check `.env` file exists and contains key
2. Verify key starts with `sk-` (OpenAI) or `sk-ant-` (Anthropic)
3. Try setting environment variable instead
4. Restart the Streamlit app

### "Error analyzing report"

**Common causes:**
1. PDF is password protected → Remove password
2. PDF is corrupted → Try re-saving or re-downloading
3. PDF is image-only → Use OCR software first
4. API key is invalid → Check key is correct and has credits

**Solution:**
- Try the regex fallback method (uncheck "Use AI Analysis")
- Check PDF can be opened in a PDF viewer
- Verify PDF contains selectable text

### "Extraction method: regex" when you wanted LLM

**Problem:** API key not detected

**Solution:**
1. Verify `.env` file is in the project root
2. Check API key is uncommented in `.env`
3. Restart Streamlit app
4. Check console for error messages

### Poor extraction quality

**With AI:**
- Try a different API provider (OpenAI vs Anthropic)
- Ensure PDF text is clear and selectable
- Check if report uses non-standard terminology

**With Regex:**
- This is expected - regex is less accurate
- Use AI analysis for better results
- Manually review and correct all fields

## Cost Considerations

### AI Analysis Costs

**OpenAI (GPT-4o-mini):**
- ~$0.001-0.005 per report
- $5 credit = ~1000-5000 reports
- Very affordable

**Anthropic (Claude Haiku):**
- ~$0.001-0.003 per report
- $5 credit = ~1500-5000 reports
- Slightly cheaper

### Cost Optimization

1. **Use regex for simple cases**
   - If report is straightforward, regex may be sufficient
   - Save AI analysis for complex reports

2. **Batch processing**
   - Process multiple reports in one session
   - API calls are only made when you click "Analyze"

3. **Monitor usage**
   - Check API dashboard for usage
   - Set spending limits if desired

## Privacy & Security

### Data Handling

**What gets sent to the API:**
- Only the text extracted from the PDF
- First ~4000 characters (to limit cost)
- No identifying information is required

**What stays local:**
- Original PDF file
- Search results
- Generated reports
- All case law data

### Best Practices

1. **Remove patient identifiers** before uploading (if required by privacy regulations)
2. **Use environment variables** instead of .env in production
3. **Don't commit .env** to version control
4. **Rotate API keys** periodically
5. **Review API provider's terms** regarding medical data

### HIPAA/PIPEDA Compliance

**Note:** If you're handling protected health information:
- Consult your organization's privacy officer
- Review API provider's BAA (Business Associate Agreement)
- Consider using regex-only mode for maximum privacy
- Or redact all PHI before uploading

## Advanced Usage

### Custom Prompts

You can modify the LLM prompt in `expert_report_analyzer.py`:

```python
# Line ~85-90
prompt = f"""Analyze this medical/expert report...
"""
```

Customize to:
- Extract additional fields
- Use different medical terminology
- Focus on specific injury types
- Match your jurisdiction's standards

### Integrating Other LLM Providers

Currently supports:
- OpenAI (GPT-4, GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3 Haiku, Sonnet, Opus)

To add others (Cohere, Llama, etc.):
1. Edit `expert_report_analyzer.py`
2. Add provider in `__init__` method
3. Add API call logic in `analyze_with_llm` method
4. Update requirements.txt

## Examples

### Example 1: MVA with Multiple Injuries

**Input:** 25-page IME report

**Extracted:**
- Regions: Cervical spine, Right shoulder, Lumbar spine
- Description: "Post-MVA cervical and lumbar soft tissue injuries with chronic pain syndrome..."
- Limitations: Reduced ROM, Unable to lift >10lbs, Difficulty prolonged sitting
- Chronicity: Chronic
- Severity: Moderate

**Result:** Auto-populated search finds 12 comparable cases

### Example 2: Workplace Knee Injury

**Input:** 8-page orthopedic assessment

**Extracted:**
- Regions: Right knee
- Description: "Complete ACL tear with meniscal damage, surgical reconstruction performed..."
- Limitations: Unable to kneel, Difficulty stairs, Reduced athletic capacity
- Chronicity: Permanent
- Severity: Severe

**Result:** Search returns relevant ACL tear cases with similar functional impacts

## FAQ

**Q: Do I need an API key?**
A: No, but AI analysis works much better. Regex fallback is available.

**Q: Which API provider is better?**
A: Both work well. OpenAI is slightly more popular, Anthropic is slightly cheaper.

**Q: How long does analysis take?**
A: Usually 5-15 seconds depending on report length and API speed.

**Q: Can I analyze multiple reports at once?**
A: Not currently, but you can analyze them sequentially.

**Q: Is my data private?**
A: API providers may log data. Check their privacy policies. Use regex mode for maximum privacy.

**Q: Can I use this offline?**
A: Yes, with regex mode (no API key required).

**Q: What if the extraction is wrong?**
A: Always review and manually correct the auto-populated fields before searching.

**Q: Can I improve extraction accuracy?**
A: Yes - edit the prompt in `expert_report_analyzer.py` to be more specific for your use case.

## Support

For issues:
- Check this guide first
- Review error messages in the UI
- Check the console for detailed errors
- Open an issue on GitHub with example (redacted) report

## Future Enhancements

Planned features:
- [ ] Batch report processing
- [ ] Custom extraction templates
- [ ] OCR for scanned reports
- [ ] Multi-language support
- [ ] Report comparison tool
- [ ] Automatic chronology generation

Contributions welcome!
