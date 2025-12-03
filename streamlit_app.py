"""
Ontario Damages Compendium - Visual Search Tool
A professional legal tool for searching comparable personal injury awards

Main application file - handles UI and user interactions only.
Business logic has been moved to app/ modules for better organization.
"""

import streamlit as st
import numpy as np
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Import custom modules (refactored into app/ package)
from app.core.config import *
from app.core.data_loader import initialize_data
from app.core.search import search_cases, extract_damages_value, boolean_search
from app.ui.visualizations import create_inflation_chart, calculate_chart_statistics, create_damages_cap_chart
from app.ui.judge_analytics import display_judge_analytics_page
from app.ui.category_analytics import display_category_analytics_page

# Import other application modules
from expert_report_analyzer import analyze_expert_report
from pdf_report_generator import generate_damages_report
from inflation_adjuster import (
    DEFAULT_REFERENCE_YEAR,
    get_data_source,
    get_cpi_data,
    BOC_CPI_CSV,
    reload_cpi_data
)

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Ontario Damages Compendium",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling with improved UX and dark mode support
st.markdown("""
<style>
    /* Light mode defaults */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.15rem;
        margin-bottom: 2rem;
        line-height: 1.6;
    }
    .region-badge {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        margin: 0.25rem;
        background-color: #2563eb;
        color: #ffffff;
        border-radius: 0.375rem;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .case-card {
        border: 2px solid #d1d5db;
        border-radius: 0.625rem;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
    }
    .damage-summary {
        border-left: 5px solid #059669;
        padding: 1.25rem;
        margin: 1rem 0;
        border-radius: 0.375rem;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
    }
    .similarity-score {
        color: #4f46e5;
        font-weight: 700;
        font-size: 1.1rem;
    }
    /* Improve readability */
    .stMarkdown {
        font-size: 1.05rem;
        line-height: 1.7;
    }
    /* Better expander visibility */
    .streamlit-expanderHeader {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    /* Improve metric contrast */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
    }
    /* Better button contrast */
    .stButton>button {
        font-weight: 600;
        font-size: 1rem;
    }

    /* Dark mode overrides - use Streamlit's color variables instead of hardcoded colors */
    [data-theme="dark"] .case-card {
        border-color: #4b5563;
        background-color: rgba(255, 255, 255, 0.05);
    }
    [data-theme="dark"] .damage-summary {
        background-color: rgba(5, 150, 105, 0.15);
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# INITIALIZE DATA
# =============================================================================

model, cases, region_map = initialize_data()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def display_enhanced_data(case: Dict) -> None:
    """Display enhanced AI-parsed data if available."""
    extended_data = case.get('extended_data')
    if not extended_data:
        return

    # Multi-plaintiff information
    num_plaintiffs = extended_data.get('num_plaintiffs', 0)
    if num_plaintiffs > 1:
        st.info(f"⚠️ Multi-Plaintiff Case ({num_plaintiffs} plaintiffs)")

    # Plaintiff-specific details
    plaintiff_id = extended_data.get('plaintiff_id')
    if plaintiff_id:
        st.markdown(f"**Plaintiff:** {plaintiff_id}")

    sex = extended_data.get('sex')
    age = extended_data.get('age')
    if sex or age:
        demo = []
        if sex:
            demo.append(f"Sex: {sex}")
        if age:
            demo.append(f"Age: {age}")
        st.markdown(f"**Demographics:** {', '.join(demo)}")

    # Injuries (deduplicated)
    injuries = extended_data.get('injuries')
    if injuries:
        st.markdown("**Injuries:**")
        # Deduplicate while preserving order
        seen = set()
        unique_injuries = []
        for injury in injuries:
            # Normalize for comparison (case-insensitive, strip whitespace)
            injury_normalized = injury.strip().lower()
            if injury_normalized not in seen:
                seen.add(injury_normalized)
                unique_injuries.append(injury)

        for injury in unique_injuries:
            st.markdown(f"- {injury}")

    # Other damages
    other_damages = extended_data.get('other_damages')
    if other_damages:
        st.markdown("**Other Damages:**")
        for damage in other_damages:
            damage_type = damage.get('type', 'Other')
            amount = damage.get('amount')
            desc = damage.get('description', '')
            if amount:
                st.markdown(f"- {damage_type}: ${amount:,.0f}" + (f" ({desc})" if desc else ""))
            else:
                st.markdown(f"- {damage_type}" + (f": {desc}" if desc else ""))

    # Family Law Act claims
    fla_claims = extended_data.get('family_law_act_claims')
    if fla_claims:
        st.markdown("**Family Law Act Claims:**")
        for claim in fla_claims:
            desc = claim.get('description', 'FLA claim')
            amount = claim.get('amount')
            if amount:
                st.markdown(f"- {desc}: ${amount:,.0f}")
            else:
                st.markdown(f"- {desc}")

    # Citations
    citations = extended_data.get('citations')
    if citations:
        st.markdown(f"**Citations:** {', '.join(citations)}")

    # Judges
    judges = extended_data.get('judges')
    if judges:
        st.markdown(f"**Judges:** {', '.join(judges)}")

    # Provisional damages flag
    is_provisional = extended_data.get('is_provisional')
    if is_provisional:
        st.warning("⚠️ Provisional damages award")

    # Comments
    comments = extended_data.get('comments')
    if comments:
        st.markdown(f"**Comments:** {comments}")

# =============================================================================
# INITIALIZE SESSION STATE
# =============================================================================

if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None

# =============================================================================
# MAIN UI
# =============================================================================

# Header
st.markdown('<div class="main-header">⚖️ Ontario Damages Compendium</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Visual search tool for comparable personal injury awards in Ontario</div>', unsafe_allow_html=True)

# Create tabs for different pages
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Case Search", "👨‍⚖️ Judge Analytics", "🩺 Category Statistics", "🕵️ Boolean Search"])

# =============================================================================
# TAB 1: CASE SEARCH
# =============================================================================

with tab1:
    # Instructions - Always visible
    st.info("""
    **How to Search:** Describe the injury in detail below, optionally select demographics and injury categories in the sidebar, then click "Find Comparable Cases" to see similar awards.

    **💡 Tips:** Use clinical terminology (e.g., "C5-C6 disc herniation"), include severity and chronicity, mention mechanism of injury if relevant.
    """)

    # =============================================================================
    # EXPERT REPORT UPLOAD (OPTIONAL)
    # =============================================================================

    with st.expander("📄 **Optional:** Upload Expert/Medical Report for Auto-Extraction", expanded=False):
        st.markdown("""
        Upload a medical or expert report PDF, and the system will automatically extract injuries,
        limitations, and other relevant information to populate the search fields.
        """)

        col_upload1, col_upload2 = st.columns([2, 1])

        with col_upload1:
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type=['pdf'],
                help="Upload medical report, IME, expert opinion, or similar document"
            )

        with col_upload2:
            use_llm = st.checkbox(
                "Use AI Analysis",
                value=True,
                help="Use LLM for more accurate extraction (requires API key in .env file)"
            )

        if uploaded_file is not None:
            if st.button("🔍 Analyze Expert Report", type="secondary"):
                with st.spinner("Analyzing expert report..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name

                    try:
                        analysis = analyze_expert_report(tmp_path, use_llm=use_llm)
                        st.session_state.analysis_data = analysis

                        st.success("✅ Expert report analyzed successfully!")

                        st.subheader("Extracted Information")

                        if analysis.get('injured_regions'):
                            st.write("**Detected Categories:**")
                            for region_id in analysis['injured_regions']:
                                if region_id in region_map:
                                    st.write(f"• {region_map[region_id]['label']}")

                        if analysis.get('injury_description'):
                            st.write("**Injury Description:**")
                            st.write(analysis['injury_description'][:500])

                        if analysis.get('limitations'):
                            st.write("**Functional Limitations:**")
                            for limitation in analysis['limitations'][:5]:
                                st.write(f"• {limitation}")

                        if analysis.get('chronicity'):
                            st.write(f"**Chronicity:** {analysis['chronicity']}")

                        if analysis.get('severity'):
                            st.write(f"**Severity:** {analysis['severity']}")

                        st.info("💡 Review the auto-populated injury description below and edit as needed before searching.")

                    except Exception as e:
                        st.error(f"❌ Error analyzing report: {str(e)}")
                        st.info("Try using the manual input field below instead.")
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

    # =============================================================================
    # INJURY DESCRIPTION - MAIN INPUT
    # =============================================================================

    st.markdown("### 🔍 Describe the Injury")

    # Pre-populate if analysis exists (from expert report analyzer)
    default_injury_text = ""
    if st.session_state.analysis_data:
        # Build injury text from extracted injuries and sequelae
        injuries = st.session_state.analysis_data.get('injuries', [])
        sequelae = st.session_state.analysis_data.get('sequelae', [])
        parts = []
        if injuries:
            parts.append("; ".join(injuries))
        if sequelae:
            parts.append("; ".join(sequelae))
        default_injury_text = " | ".join(parts) if parts else ""

    injury_text = st.text_area(
        "Injury details",
        value=default_injury_text,
        height=180,
        placeholder="Example: C5-C6 disc herniation with chronic radicular pain radiating to right upper extremity. Failed conservative management. MRI shows central disc protrusion with nerve root impingement. Ongoing neurological deficits including weakness and paresthesias...",
        help="Include: mechanism, anatomical structures, severity, chronicity, and functional impact",
        label_visibility="collapsed"
    )

    # Case Characteristics - moved from sidebar for better workflow
    st.markdown("#### Case Characteristics (Optional)")
    st.caption("Additional filters for case characteristics")

    # Load compendium regions for status filters
    status_filters = {}
    compendium_regions_for_status = None
    try:
        with open("compendium_regions.json", "r") as f:
            compendium_regions_for_status = json.load(f)
    except:
        pass

    if compendium_regions_for_status and "status_filters" in compendium_regions_for_status:
        # Create columns for better layout
        num_filters = len(compendium_regions_for_status["status_filters"])
        cols_per_row = 3
        rows_needed = (num_filters + cols_per_row - 1) // cols_per_row

        filters_list = list(compendium_regions_for_status["status_filters"].items())

        for row_idx in range(rows_needed):
            cols = st.columns(cols_per_row)
            for col_idx in range(cols_per_row):
                filter_idx = row_idx * cols_per_row + col_idx
                if filter_idx < len(filters_list):
                    filter_id, filter_data = filters_list[filter_idx]
                    with cols[col_idx]:
                        status_filters[filter_id] = st.checkbox(
                            filter_data["label"],
                            help=filter_data["description"],
                            key=f"status_{filter_id}"
                        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        search_button = st.button("🔍 Find Comparable Cases", type="primary", use_container_width=True)

# =============================================================================
# SIDEBAR - SEARCH PARAMETERS
# =============================================================================

with st.sidebar:
    st.header("Search Parameters")

    # Demographics - back in sidebar for better organization
    st.subheader("Demographics")
    gender = st.radio("Gender:", ["Male", "Female", "Not Specified"], index=2, horizontal=False)
    age = st.slider("Age:", 5, 100, 35, help="Age of plaintiff at time of injury")

    st.divider()

    # Load compendium regions
    compendium_regions = None
    try:
        with open("compendium_regions.json", "r") as f:
            compendium_regions = json.load(f)
    except:
        pass

    # Injury Categories (based on compendium structure)
    st.subheader("Injury Categories")
    st.caption("Select injury types based on compendium categories")

    selected_injury_categories = []

    if compendium_regions and "injury_categories" in compendium_regions:
        for category_id, category_data in compendium_regions["injury_categories"].items():
            with st.expander(category_data["label"]):
                for subcategory in category_data["subcategories"]:
                    key = f"cat_{category_id}_{subcategory}"
                    if st.checkbox(subcategory, key=key):
                        selected_injury_categories.append(subcategory)
    else:
        # Fallback to simple text input if config not available
        st.info("Using simplified injury search - describe injuries in the text box below")

    st.divider()

    # Display selected categories
    if selected_injury_categories:
        st.subheader("Selected Categories")
        for cat in selected_injury_categories[:5]:  # Show first 5
            st.markdown(f'<span class="region-badge">{cat}</span>', unsafe_allow_html=True)
        if len(selected_injury_categories) > 5:
            st.caption(f"+ {len(selected_injury_categories) - 5} more...")
    else:
        st.info("No categories selected - will search all cases")

    st.divider()

    # CPI Data Upload Section
    with st.expander("📊 Update CPI Data (Optional)", expanded=False):
        st.caption("Upload Bank of Canada CPI data to ensure accurate inflation adjustments")
        st.info(f"**Current:** {get_data_source()}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Download current data:**")
            import io
            cpi_data = get_cpi_data()
            csv_buffer = io.StringIO()
            csv_buffer.write("Year,CPI\n")
            for year in sorted(cpi_data.keys()):
                csv_buffer.write(f"{year},{cpi_data[year]:.2f}\n")

            st.download_button(
                label="📥 Download Current CPI Data",
                data=csv_buffer.getvalue(),
                file_name="cpi_data_template.csv",
                mime="text/csv",
                help="Download the current CPI data as a CSV template"
            )

        with col2:
            st.markdown("**Or get latest from:**")
            st.markdown("[Bank of Canada](https://www.bankofcanada.ca/valet/observations/group/CPI_MONTHLY/csv)")

        cpi_file = st.file_uploader(
            "Upload CPI CSV",
            type=['csv'],
            help="Bank of Canada CPI monthly data in CSV format",
            key="cpi_upload"
        )

        if cpi_file is not None:
            try:
                BOC_CPI_CSV.parent.mkdir(parents=True, exist_ok=True)
                with open(BOC_CPI_CSV, 'wb') as f:
                    f.write(cpi_file.getbuffer())

                new_data = reload_cpi_data()
                st.success(f"✓ CPI data updated successfully! Now have {len(new_data)} years of data.")

            except Exception as e:
                st.error(f"Failed to update CPI data: {e}")

    st.divider()

    # Search filters
    st.subheader("Search Filters")

    num_results = st.slider(
        "Number of results:",
        min_value=5,
        max_value=50,
        value=15,
        step=5,
        help="Maximum number of cases to return"
    )

    # Wire injury categories to selected_regions for exclusive filtering
    # selected_regions is used as an exclusive filter: only cases with at least one selected region
    selected_regions = selected_injury_categories

with tab1:
    # =============================================================================
    # SEARCH EXECUTION AND RESULTS DISPLAY
    # =============================================================================

    if search_button:
        if not injury_text.strip():
            st.warning("⚠️ Please enter an injury description")
        else:
            with st.spinner("Searching comparable cases..."):
                # Get search results (no minimum threshold - user sees all results)
                results = search_cases(
                    injury_text,
                    selected_regions,
                    cases,
                    region_map,
                    model,
                    gender=gender if gender != "Not Specified" else None,
                    age=age,
                    top_n=num_results
                )

            # Store results in session state
            st.session_state.search_results = {
                'results': results,
                'injury_text': injury_text,
                'selected_regions': selected_regions,
                'gender': gender,
                'age': age,
                'num_results': num_results,
                'timestamp': datetime.now()
            }

            st.divider()
            st.header("Search Results")

            # Display search info
            st.info(f"🔍 Showing {len(results)} comparable cases (sorted by relevance)")

            # Extract damages for charts
            damages_values = []
            for case, emb_sim, combined_score in results:
                damage_val = extract_damages_value(case)
                if damage_val:
                    damages_values.append(damage_val)

            # Charts Section (min/med/max shown in cap chart below)
            if damages_values and len(results) > 0:
                st.divider()

                # Damages Cap Comparison Chart
                st.subheader("📊 Awards Relative to Ontario Damages Cap")
                cap_fig = create_damages_cap_chart(damages_values, DEFAULT_REFERENCE_YEAR)
                if cap_fig:
                    st.plotly_chart(cap_fig, use_container_width=True)
                    st.caption("💡 Bars are colored based on their proportion to the Ontario non-pecuniary damages cap")

                st.divider()

                # Inflation-Adjusted Timeline Chart
                st.subheader("📈 Inflation-Adjusted Award Timeline")

                fig = create_inflation_chart(results, DEFAULT_REFERENCE_YEAR)

                if fig:
                    st.plotly_chart(fig, use_container_width=True)

                    # Calculate and display statistics
                    chart_data = []
                    for case, emb_sim, combined_score in results[:CHART_MAX_CASES]:
                        damage_val = extract_damages_value(case)
                        year = case.get('year')
                        if damage_val and year:
                            from inflation_adjuster import adjust_for_inflation
                            adjusted_val = adjust_for_inflation(damage_val, year, DEFAULT_REFERENCE_YEAR)
                            if adjusted_val:
                                chart_data.append({
                                    'original_award': damage_val,
                                    'adjusted_award': adjusted_val
                                })

                    if chart_data:
                        stats = calculate_chart_statistics(chart_data)

                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric(
                                f"Median Award ({DEFAULT_REFERENCE_YEAR}$)",
                                f"${stats['median_adjusted']:,.0f}",
                                help=f"Median of all awards adjusted to {DEFAULT_REFERENCE_YEAR} dollars"
                            )

                        with col2:
                            st.metric(
                                "Avg. Inflation Impact",
                                f"+{stats['avg_inflation_impact']:.1f}%",
                                help="Average percentage increase from original award year to current dollars"
                            )

                        st.caption(
                            f"💡 All awards adjusted to {DEFAULT_REFERENCE_YEAR} dollars using "
                            "Canadian CPI. Original amounts are not shown as they are not comparable across different years."
                        )
                else:
                    st.info("Inflation adjustment requires case year information. Some cases may not have dates.")

            st.divider()

            # Display individual cases
            st.subheader(f"Top {len(results)} Comparable Cases")

            for idx, (case, emb_sim, combined_score) in enumerate(results, 1):
                # Build expander title with multi-plaintiff indicator and award amount
                extended_data = case.get('extended_data', {})
                num_plaintiffs = extended_data.get('num_plaintiffs', 0)
                title_suffix = f" [P{extended_data.get('plaintiff_id', '')}]" if num_plaintiffs > 1 else ""

                # Get damage value for expander title
                damage_val = extract_damages_value(case)
                damage_display = f" | Award: ${damage_val:,.0f}" if damage_val else ""

                with st.expander(
                    f"**Case {idx}** - {case.get('case_name', 'Unknown')}{title_suffix} | "
                    f"Category: {case.get('region', 'Unknown')}{damage_display} | "
                    f"Match: {combined_score*100:.1f}%",
                    expanded=(idx <= EXPANDED_RESULTS_COUNT)
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.markdown(f"**Category:** {case.get('region', 'Unknown')}")

                        if case.get('year'):
                            st.markdown(f"**Year:** {case['year']}")

                        if case.get('court'):
                            st.markdown(f"**Court:** {case['court']}")

                        if damage_val:
                            st.markdown(f"**Damages:** ${damage_val:,.0f}")

                        # Summary paragraph removed - pertinent info shown in enhanced data below

                        # Display enhanced AI-parsed data
                        st.divider()
                        display_enhanced_data(case)

                    with col2:
                        st.metric("Match Score", f"{combined_score*100:.1f}%", help="Overall similarity based on injury description and categories")

                        if case.get("region_score", 0) > 0:
                            st.metric("Category Match", f"{case['region_score']*100:.0f}%")

    # =============================================================================
    # PDF REPORT GENERATION
    # =============================================================================

    if st.session_state.search_results:
        st.divider()

        st.subheader("📥 Generate PDF Report")
        st.markdown("Create a professional PDF report with search parameters, damage analysis, and comparable cases.")

        col_dl1, col_dl2 = st.columns([1, 3])

        with col_dl1:
            num_cases = st.number_input(
                "Number of cases to include:",
                min_value=1,
                max_value=50,
                value=10,
                help="Number of top cases to include in PDF report"
            )

        with col_dl2:
            if st.button("📄 Generate PDF Report", type="primary", use_container_width=True):
                with st.spinner("Generating PDF report..."):
                    try:
                        search_data = st.session_state.search_results
                        results = search_data['results']

                        damages_values = []
                        for case, emb_sim, combined_score in results:
                            damage_val = extract_damages_value(case)
                            if damage_val:
                                damages_values.append(damage_val)

                        region_labels = {
                            rid: region_map[rid]["label"]
                            for rid in search_data['selected_regions']
                            if rid in region_map
                        }

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        pdf_filename = f"damages_report_{timestamp}.pdf"

                        with tempfile.TemporaryDirectory() as tmpdir:
                            pdf_path = os.path.join(tmpdir, pdf_filename)

                            generate_damages_report(
                                output_path=pdf_path,
                                selected_regions=search_data['selected_regions'],
                                region_labels=region_labels,
                                injury_description=search_data['injury_text'],
                                results=results,
                                damages_values=damages_values,
                                gender=search_data['gender'] if search_data['gender'] != "Not Specified" else None,
                                age=search_data['age'],
                                max_cases=num_cases
                            )

                            with open(pdf_path, 'rb') as pdf_file:
                                pdf_data = pdf_file.read()

                            st.success("✅ PDF report generated successfully!")

                            st.download_button(
                                label="💾 Download PDF Report",
                                data=pdf_data,
                                file_name=pdf_filename,
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True
                            )

                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
                        st.info("Please ensure all dependencies are installed: pip install reportlab")

# =============================================================================
# TAB 2: JUDGE ANALYTICS
# =============================================================================

with tab2:
    display_judge_analytics_page(cases)

# =============================================================================
# TAB 3: CATEGORY STATISTICS (includes injury categories and FLA relationships)
# =============================================================================

with tab3:
    display_category_analytics_page(cases)

# =============================================================================
# TAB 4: BOOLEAN SEARCH
# =============================================================================

with tab4:
    st.info("""
    **Boolean Search:** Use logical operators to find specific cases with field-specific search and damage filters.

    **Operators:**
    - **AND**: Both terms must be present (e.g., `whiplash AND herniation`)
    - **OR**: At least one term must be present (e.g., `fracture OR break`)
    - **NOT**: Term must not be present (e.g., `spine NOT surgery`)
    - **Quotes**: Exact phrase matching (e.g., `"disc herniation"`)

    **💡 Examples:**
    - Search for `MVA` in **Comments only** with awards over **$100,000**
    - Search for `neck AND "disc herniation"` in **Injuries** field
    - Search for `(fracture OR break) AND spine` across **all fields**
    - Search for `brain NOT surgery` in **Comments** with awards between **$50k-$200k**
    """)

    # Boolean query input
    st.subheader("Enter Boolean Query")
    boolean_query = st.text_input(
        "Boolean Query",
        placeholder='e.g., MVA, neck AND herniation, (fracture OR break) AND spine',
        help="Use AND, OR, NOT operators to combine search terms. Use quotes for exact phrases.",
        label_visibility="collapsed"
    )

    # Field selection
    st.subheader("🔍 Search In (select fields to search)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        search_case_name = st.checkbox("Case Name", value=True, key="bool_search_case_name")
    with col2:
        search_injuries = st.checkbox("Injuries", value=True, key="bool_search_injuries")
    with col3:
        search_comments = st.checkbox("Comments", value=True, key="bool_search_comments")
    with col4:
        search_summary = st.checkbox("Summary", value=True, key="bool_search_summary")

    # Build search_fields list
    search_fields = []
    if search_case_name:
        search_fields.append('case_name')
    if search_injuries:
        search_fields.append('injuries')
    if search_comments:
        search_fields.append('comments')
    if search_summary:
        search_fields.append('summary')

    # Damages filter
    st.subheader("💰 Damages Filter")
    col1, col2 = st.columns(2)
    with col1:
        min_damages_enabled = st.checkbox("Minimum Award", key="bool_min_damages_enabled")
        min_damages = None
        if min_damages_enabled:
            min_damages = st.number_input(
                "Min Amount ($)",
                min_value=0,
                max_value=10_000_000,
                value=100_000,
                step=10_000,
                key="bool_min_damages"
            )

    with col2:
        max_damages_enabled = st.checkbox("Maximum Award", key="bool_max_damages_enabled")
        max_damages = None
        if max_damages_enabled:
            max_damages = st.number_input(
                "Max Amount ($)",
                min_value=0,
                max_value=10_000_000,
                value=500_000,
                step=10_000,
                key="bool_max_damages"
            )

    # Year range filter
    st.subheader("📅 Year Range Filter")
    year_filter_enabled = st.checkbox("Filter by year range", key="bool_year_filter_enabled")
    min_year = None
    max_year = None
    if year_filter_enabled:
        # Get min/max years from cases for slider range
        all_years = [case.get('year') for case in cases if case.get('year')]
        if all_years:
            min_case_year = min(all_years)
            max_case_year = max(all_years)
            year_range = st.slider(
                "Select year range",
                min_value=min_case_year,
                max_value=max_case_year,
                value=(min_case_year, max_case_year),
                key="bool_year_range"
            )
            min_year, max_year = year_range

    # Sidebar filters
    with st.sidebar:
        st.header("Boolean Search Filters")

        # Category filter
        bool_selected_regions = []
        with st.expander("🎯 Injury Categories (Optional)", expanded=False):
            if region_map:
                for category_id, category_data in region_map.items():
                    if st.checkbox(
                        category_data.get('label', category_id),
                        key=f"bool_category_{category_id}"
                    ):
                        # Add main category
                        bool_selected_regions.append(category_data.get('label', category_id))

                        # Add subcategories if available
                        subcats = category_data.get('subcategories', [])
                        if subcats:
                            bool_selected_regions.extend(subcats)

        # Demographics
        st.subheader("👤 Demographics (Optional)")
        bool_gender = st.selectbox(
            "Gender",
            options=["Any", "Male", "Female"],
            key="bool_gender"
        )
        if bool_gender == "Any":
            bool_gender = None

        bool_use_age = st.checkbox("Filter by age", key="bool_use_age")
        bool_age = None
        if bool_use_age:
            bool_age = st.slider(
                "Age (±5 years)",
                min_value=0,
                max_value=100,
                value=40,
                key="bool_age"
            )

    # Search button
    if st.button("🔍 Search Cases", type="primary", key="bool_search_btn"):
        if not boolean_query.strip():
            st.warning("⚠️ Please enter a Boolean query to search.")
        elif not search_fields:
            st.warning("⚠️ Please select at least one field to search in.")
        else:
            with st.spinner("Searching cases..."):
                # Perform Boolean search with field-specific, damage, and year filters
                bool_results = boolean_search(
                    query=boolean_query,
                    cases=cases,
                    selected_regions=bool_selected_regions if bool_selected_regions else None,
                    gender=bool_gender,
                    age=bool_age,
                    search_fields=search_fields,
                    min_damages=min_damages,
                    max_damages=max_damages,
                    min_year=min_year,
                    max_year=max_year
                )

                st.divider()
                st.header("Search Results")

                # Display search info
                st.info(f"🔍 Found {len(bool_results)} matching cases")

                if bool_results:
                    # Extract damages for charts
                    bool_damages_values = []
                    for case in bool_results:
                        damage_val = extract_damages_value(case)
                        if damage_val:
                            bool_damages_values.append(damage_val)

                    # Display charts if we have damages data
                    if bool_damages_values:
                        st.divider()

                        # Damages Cap Comparison Chart
                        st.subheader("📊 Awards Relative to Ontario Damages Cap")
                        cap_fig = create_damages_cap_chart(bool_damages_values, DEFAULT_REFERENCE_YEAR)
                        if cap_fig:
                            st.plotly_chart(cap_fig, use_container_width=True)
                            st.caption("💡 Bars are colored based on their proportion to the Ontario non-pecuniary damages cap")

                    st.divider()
                    st.subheader("📋 Case Results")

                    # Display cases
                    for idx, case in enumerate(bool_results, 1):
                        with st.container():
                            # Case header
                            col1, col2 = st.columns([3, 1])

                            with col1:
                                case_name = case.get('case_name', 'Unknown Case')
                                year = case.get('year', 'N/A')
                                court = case.get('court', 'N/A')
                                st.markdown(f"### {idx}. {case_name}")
                                st.caption(f"📅 {year} | 🏛️ {court}")

                            with col2:
                                damage_val = extract_damages_value(case)
                                if damage_val:
                                    st.metric("💰 Award", f"${damage_val:,.0f}")

                            # Case details
                            ext = case.get('extended_data', {})

                            # Injuries
                            injuries = ext.get('injuries', [])
                            if injuries:
                                st.markdown("**🩹 Injuries:**")
                                for injury in injuries[:5]:  # Show first 5 injuries
                                    st.markdown(f"- {injury}")
                                if len(injuries) > 5:
                                    st.caption(f"... and {len(injuries) - 5} more")

                            # Comments
                            comments = ext.get('comments') or case.get('comments')
                            if comments:
                                st.markdown(f"**💬 Comments:** {comments}")

                            # Categories
                            regions = case.get('regions') or ext.get('regions', [])
                            if regions:
                                st.markdown(f"**📍 Categories:** {', '.join(regions[:5])}")

                            # Citation
                            citation = case.get('citation', '')
                            if citation:
                                st.caption(f"📖 Citation: {citation}")

                            st.divider()
                else:
                    st.warning("No cases found matching your Boolean query. Try adjusting your search terms or operators.")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption("© 2025 Ontario Damages Compendium Tool | Built for legal professionals | Data source: CCLA Damages Compendium 2024")
st.caption("⚠️ This tool provides reference information only. Always verify case details and consult primary sources.")
