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
from app.core.search import search_cases, extract_damages_value
from app.ui.visualizations import create_inflation_chart, calculate_chart_statistics

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

# Custom CSS for professional styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .region-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        background-color: #3b82f6;
        color: white;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .case-card {
        border: 1px solid #e5e7eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: #f9fafb;
    }
    .damage-summary {
        background-color: #ecfdf5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #059669;
    }
    .similarity-score {
        color: #6366f1;
        font-weight: 600;
    }
    .instructions {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# INITIALIZE DATA
# =============================================================================

model, cases, region_map = initialize_data()

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

# Instructions
with st.expander("ℹ️ How to Use This Tool", expanded=False):
    st.markdown("""
    <div class="instructions">
    <h4>Search Process:</h4>
    <ol>
        <li><strong>Select Demographics:</strong> Choose gender and age of the plaintiff</li>
        <li><strong>Select Body Regions:</strong> Click on anatomical regions in the sidebar (multi-select supported)</li>
        <li><strong>Describe Injury:</strong> Provide detailed injury description including mechanism, severity, and chronicity</li>
        <li><strong>Search:</strong> Click "Find Comparable Cases" to see results</li>
        <li><strong>Review:</strong> Examine matched cases and damage award ranges</li>
    </ol>
    <p><strong>Tips:</strong></p>
    <ul>
        <li>Use clinical terminology for best results (e.g., "C5-C6 disc herniation" not "neck pain")</li>
        <li>Include chronicity information (acute, chronic, permanent)</li>
        <li>Mention mechanism of injury (MVA, slip & fall, etc.) if relevant</li>
        <li>Select multiple regions for complex multi-injury cases</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# SIDEBAR - SEARCH PARAMETERS
# =============================================================================

with st.sidebar:
    st.header("Search Parameters")

    # Demographics
    st.subheader("Demographics")
    gender = st.radio("Gender:", ["Male", "Female", "Not Specified"], index=2)
    age = st.slider("Age:", 5, 100, 35, help="Age of plaintiff at time of injury")

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

    # Region selection
    st.subheader("Body Regions")
    st.caption("Select one or more injured regions")

    selected_regions = []

    # Group regions by body area
    region_groups = {
        "Head & Spine": ["head", "cervical_spine", "thoracic_spine", "lumbar_spine", "sacroiliac"],
        "Torso": ["chest", "abdomen", "pelvis"],
        "Left Upper Limb": ["shoulder_left", "arm_left", "elbow_left", "forearm_left", "wrist_left", "hand_left"],
        "Right Upper Limb": ["shoulder_right", "arm_right", "elbow_right", "forearm_right", "wrist_right", "hand_right"],
        "Left Lower Limb": ["hip_left", "thigh_left", "knee_left", "lower_leg_left", "ankle_left", "foot_left"],
        "Right Lower Limb": ["hip_right", "thigh_right", "knee_right", "lower_leg_right", "ankle_right", "foot_right"]
    }

    for group_name, region_ids in region_groups.items():
        with st.expander(group_name):
            for region_id in region_ids:
                if region_id in region_map:
                    label = region_map[region_id]["label"]
                    if st.checkbox(label, key=region_id):
                        selected_regions.append(region_id)

    st.divider()

    # Display selected regions
    if selected_regions:
        st.subheader("Selected Regions")
        for region_id in selected_regions:
            st.markdown(f'<span class="region-badge">{region_map[region_id]["label"]}</span>', unsafe_allow_html=True)
    else:
        st.info("No regions selected - will search all cases")

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

    min_similarity = st.slider(
        "Minimum similarity (%):",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        help="Filter out cases below this similarity threshold"
    )

# =============================================================================
# MAIN CONTENT - EXPERT REPORT UPLOAD
# =============================================================================

st.divider()

with st.expander("📄 Upload Expert/Medical Report (Optional)", expanded=False):
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
                        st.write("**Detected Regions:**")
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

                    st.info("💡 Scroll down to review and edit the auto-populated fields before searching.")

                except Exception as e:
                    st.error(f"❌ Error analyzing report: {str(e)}")
                    st.info("Try using the manual input fields below instead.")
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

# =============================================================================
# MAIN CONTENT - SEARCH INPUT
# =============================================================================

st.divider()

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Injury Description")

    # Pre-populate if analysis exists
    default_injury_text = ""
    if st.session_state.analysis_data:
        default_injury_text = st.session_state.analysis_data.get('injury_description', '')

    injury_text = st.text_area(
        "Describe the injury in detail:",
        value=default_injury_text,
        height=150,
        placeholder="Example: C5-C6 disc herniation with chronic radicular pain radiating to right upper extremity. Failed conservative management. MRI shows central disc protrusion with nerve root impingement. Ongoing neurological deficits including weakness and paresthesias...",
        help="Include: mechanism, anatomical structures, severity, chronicity, functional impact"
    )

    search_button = st.button("🔍 Find Comparable Cases", type="primary", use_container_width=True)

with col2:
    st.subheader("Body Map Reference")

    # Display interactive body diagram
    body_tab1, body_tab2 = st.tabs(["Front View", "Back View"])

    with body_tab1:
        # Read and display front view SVG
        svg_path_front = Path(__file__).parent / "assets" / "body_front.svg"
        if svg_path_front.exists():
            with open(svg_path_front, 'r') as f:
                svg_content = f.read()

            # Add CSS styling for interactive regions
            svg_html = f"""
            <style>
                .body-svg {{
                    width: 100%;
                    max-width: 300px;
                    margin: 0 auto;
                    display: block;
                }}
                .clickable-region {{
                    cursor: pointer;
                    transition: all 0.2s;
                }}
                .clickable-region:hover {{
                    fill: rgba(59, 130, 246, 0.4) !important;
                    stroke: rgba(59, 130, 246, 0.8) !important;
                    stroke-width: 2 !important;
                }}
                .region-selected {{
                    fill: rgba(16, 185, 129, 0.5) !important;
                    stroke: rgba(16, 185, 129, 1) !important;
                    stroke-width: 2 !important;
                }}
            </style>
            <div class="body-svg">
                {svg_content}
            </div>
            <script>
                // Highlight selected regions from sidebar
                const selectedRegions = {json.dumps(selected_regions)};
                selectedRegions.forEach(regionId => {{
                    const element = document.getElementById(regionId);
                    if (element) {{
                        element.classList.add('region-selected');
                    }}
                }});

                // Add click handlers
                document.querySelectorAll('.clickable-region').forEach(region => {{
                    region.addEventListener('click', function() {{
                        const regionId = this.getAttribute('data-region');
                        alert('Region: ' + regionId + '\\n\\nPlease use the checkboxes in the sidebar to select regions.');
                    }});
                }});
            </script>
            """
            st.markdown(svg_html, unsafe_allow_html=True)
        else:
            st.info("Body diagram not found. Use the region selector in the sidebar.")

    with body_tab2:
        # Read and display back view SVG
        svg_path_back = Path(__file__).parent / "assets" / "body_back.svg"
        if svg_path_back.exists():
            with open(svg_path_back, 'r') as f:
                svg_content = f.read()

            # Add CSS styling for interactive regions
            svg_html = f"""
            <style>
                .body-svg {{
                    width: 100%;
                    max-width: 300px;
                    margin: 0 auto;
                    display: block;
                }}
                .clickable-region {{
                    cursor: pointer;
                    transition: all 0.2s;
                }}
                .clickable-region:hover {{
                    fill: rgba(59, 130, 246, 0.4) !important;
                    stroke: rgba(59, 130, 246, 0.8) !important;
                    stroke-width: 2 !important;
                }}
                .region-selected {{
                    fill: rgba(16, 185, 129, 0.5) !important;
                    stroke: rgba(16, 185, 129, 1) !important;
                    stroke-width: 2 !important;
                }}
            </style>
            <div class="body-svg">
                {svg_content}
            </div>
            <script>
                // Highlight selected regions from sidebar
                const selectedRegions = {json.dumps(selected_regions)};
                selectedRegions.forEach(regionId => {{
                    const element = document.getElementById(regionId);
                    if (element) {{
                        element.classList.add('region-selected');
                    }}
                }});

                // Add click handlers
                document.querySelectorAll('.clickable-region').forEach(region => {{
                    region.addEventListener('click', function() {{
                        const regionId = this.getAttribute('data-region');
                        alert('Region: ' + regionId + '\\n\\nPlease use the checkboxes in the sidebar to select regions.');
                    }});
                }});
            </script>
            """
            st.markdown(svg_html, unsafe_allow_html=True)
        else:
            st.info("Body diagram not found. Use the region selector in the sidebar.")

    st.caption("💡 Click regions in sidebar to highlight on the body map")

# =============================================================================
# SEARCH EXECUTION AND RESULTS DISPLAY
# =============================================================================

if search_button:
    if not injury_text.strip():
        st.warning("⚠️ Please enter an injury description")
    else:
        with st.spinner("Searching comparable cases..."):
            # Convert similarity percentage to decimal (0-1 range)
            min_similarity_threshold = min_similarity / 100.0

            # Get search results
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

            # Apply similarity filtering
            if min_similarity_threshold > 0:
                results = [
                    (case, emb_sim, combined_score)
                    for case, emb_sim, combined_score in results
                    if combined_score >= min_similarity_threshold
                ]

        # Store results in session state
        st.session_state.search_results = {
            'results': results,
            'injury_text': injury_text,
            'selected_regions': selected_regions,
            'gender': gender,
            'age': age,
            'num_results': num_results,
            'min_similarity': min_similarity,
            'timestamp': datetime.now()
        }

        st.divider()
        st.header("Search Results")

        # Display filter info if active
        if min_similarity_threshold > 0:
            st.info(f"🔍 Showing {len(results)} cases with similarity ≥ {min_similarity}% (filtered from top {num_results})")
        else:
            st.info(f"🔍 Showing top {len(results)} of {num_results} requested cases")

        # Extract damages for summary
        damages_values = []
        for case, emb_sim, combined_score in results:
            damage_val = extract_damages_value(case)
            if damage_val:
                damages_values.append(damage_val)

        # Damage summary metrics
        if damages_values:
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown('<div class="damage-summary">', unsafe_allow_html=True)
                st.markdown("**Median Award**")
                st.markdown(f'<div class="metric-value">${np.median(damages_values):,.0f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col2:
                st.markdown('<div class="damage-summary">', unsafe_allow_html=True)
                st.markdown("**Range (Min)**")
                st.markdown(f'<div class="metric-value">${np.min(damages_values):,.0f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col3:
                st.markdown('<div class="damage-summary">', unsafe_allow_html=True)
                st.markdown("**Range (Max)**")
                st.markdown(f'<div class="metric-value">${np.max(damages_values):,.0f}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            st.caption(f"Based on {len(damages_values)} cases with identified damage awards")

        # Inflation-Adjusted Chart
        if damages_values and len(results) > 0:
            st.divider()
            st.subheader("📊 Inflation-Adjusted Award Comparison")

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

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Median (Original)",
                            f"${stats['median_original']:,.0f}",
                            help="Median of original award amounts"
                        )

                    with col2:
                        st.metric(
                            f"Median ({DEFAULT_REFERENCE_YEAR}$)",
                            f"${stats['median_adjusted']:,.0f}",
                            delta=f"+${stats['median_adjusted'] - stats['median_original']:,.0f}",
                            help=f"Median adjusted to {DEFAULT_REFERENCE_YEAR} dollars"
                        )

                    with col3:
                        st.metric(
                            "Avg. Inflation Impact",
                            f"+{stats['avg_inflation_impact']:.1f}%",
                            help="Average percentage increase due to inflation"
                        )

                    st.caption(
                        f"💡 **Note:** Awards adjusted to {DEFAULT_REFERENCE_YEAR} dollars using "
                        "Canadian Consumer Price Index (Statistics Canada). "
                        "Hover over bars for detailed case information."
                    )
            else:
                st.info("Inflation adjustment requires case year information. Some cases may not have dates.")

        st.divider()

        # Display individual cases
        st.subheader(f"Top {len(results)} Comparable Cases")

        for idx, (case, emb_sim, combined_score) in enumerate(results, 1):
            with st.expander(
                f"**Case {idx}** - {case.get('case_name', 'Unknown')} | "
                f"Region: {case.get('region', 'Unknown')} | "
                f"Match: {combined_score*100:.1f}%",
                expanded=(idx <= EXPANDED_RESULTS_COUNT)
            ):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Region:** {case.get('region', 'Unknown')}")

                    if case.get('year'):
                        st.markdown(f"**Year:** {case['year']}")

                    if case.get('court'):
                        st.markdown(f"**Court:** {case['court']}")

                    damage_val = extract_damages_value(case)
                    if damage_val:
                        st.markdown(f"**Damages:** ${damage_val:,.0f}")

                    st.markdown("**Case Summary:**")
                    st.text(case.get('summary_text', 'No summary available')[:CASE_SUMMARY_MAX_LENGTH] + "...")

                with col2:
                    st.metric("Similarity Score", f"{emb_sim*100:.1f}%")
                    st.metric("Combined Score", f"{combined_score*100:.1f}%")

                    if case.get("region_score", 0) > 0:
                        st.metric("Region Match", f"{case['region_score']*100:.0f}%")

# =============================================================================
# PDF REPORT GENERATION
# =============================================================================

if st.session_state.search_results:
    st.divider()

    st.subheader("📥 Download Report")

    col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 2])

    with col_dl1:
        num_cases = st.number_input(
            "Cases in report:",
            min_value=1,
            max_value=50,
            value=10,
            help="Number of top cases to include in PDF"
        )

    with col_dl2:
        if st.button("📄 Generate PDF Report", type="secondary"):
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
                            type="primary"
                        )

                except Exception as e:
                    st.error(f"❌ Error generating PDF: {str(e)}")
                    st.info("Please ensure all dependencies are installed: pip install reportlab")

    with col_dl3:
        st.caption("Generate a professional PDF report with search parameters, damage analysis, and comparable cases.")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.caption("© 2024 Ontario Damages Compendium Tool | Built for legal professionals | Data source: CCLA Damages Compendium 2024")
st.caption("⚠️ This tool provides reference information only. Always verify case details and consult primary sources.")
