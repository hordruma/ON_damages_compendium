"""
Ontario Damages Compendium - Visual Search Tool
A professional legal tool for searching comparable personal injury awards
"""

import streamlit as st
import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import re
import tempfile
import os
from datetime import datetime

# Import custom modules
from expert_report_analyzer import analyze_expert_report
from pdf_report_generator import generate_damages_report
from inflation_adjuster import (
    adjust_for_inflation,
    DEFAULT_REFERENCE_YEAR,
    get_data_source,
    get_cpi_data,
    BOC_CPI_CSV,
    reload_cpi_data
)

# Plotly for interactive charts
import plotly.graph_objects as go

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Search algorithm weights
EMBEDDING_WEIGHT = 0.7  # Weight for semantic similarity (70%)
REGION_WEIGHT = 0.3     # Weight for anatomical region matching (30%)

# Damage value filtering
MIN_DAMAGE_VALUE = 1000        # Minimum reasonable damage award
MAX_DAMAGE_VALUE = 10_000_000  # Maximum reasonable damage award

# Display settings
DEFAULT_TOP_N_RESULTS = 15      # Default number of search results
CHART_MAX_CASES = 15            # Maximum cases to show in charts
CASE_SUMMARY_MAX_LENGTH = 400   # Max characters for case summary display
EXPANDED_RESULTS_COUNT = 3      # Number of results expanded by default

# Model settings
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# ============================================================================

# Page configuration
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
    .body-map-container {
        display: flex;
        justify-content: center;
        gap: 2rem;
        margin: 2rem 0;
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

# Load resources
@st.cache_resource
def load_embedding_model():
    """Load the sentence transformer model"""
    return SentenceTransformer(EMBEDDING_MODEL_NAME)

@st.cache_data
def load_cases():
    """Load case data with embeddings"""
    data_path = Path("data/damages_with_embeddings.json")
    if not data_path.exists():
        st.error(f"❌ Data file not found: {data_path}")
        st.info("Please run the `01_extract_and_embed.ipynb` notebook first to generate the data.")
        return None

    with open(data_path) as f:
        return json.load(f)

@st.cache_data
def load_region_map():
    """Load region mapping"""
    with open("region_map.json") as f:
        return json.load(f)

# Initialize
model = load_embedding_model()
cases = load_cases()
region_map = load_region_map()

if cases is None:
    st.stop()

def normalize_region_name(region_name):
    """
    Normalize region names from case data to standardized region IDs.

    Handles variations in terminology by mapping free-text region names
    (e.g., "neck", "cervical", "C-spine") to standardized region IDs
    (e.g., "cervical_spine") using the region_map compendium terms.

    Algorithm:
    1. Check if region_map key matches (with underscores replaced by spaces)
    2. Check if any compendium term for a region matches the input
    3. Return first match found, or None if no match

    Args:
        region_name: Free-text region name from case data

    Returns:
        Standardized region ID (str) or None if no match found

    Example:
        normalize_region_name("neck injury") → "cervical_spine"
        normalize_region_name("C5-C6") → "cervical_spine"
    """
    region_lower = region_name.lower()

    # Iterate through all known regions in our mapping
    for key, data in region_map.items():
        # Check if the region key itself appears (e.g., "cervical_spine" → "cervical spine")
        if key.replace("_", " ") in region_lower:
            return key

        # Check all synonyms/clinical terms for this region
        for term in data["compendium_terms"]:
            if term.lower() in region_lower:
                return key

    return None  # No match found

def calculate_region_overlap(case_region, selected_regions):
    """
    Calculate overlap score between a case's region and user-selected regions.

    Implements a tiered matching system:
    - Score 1.0 = Perfect match (normalized regions match exactly)
    - Score 0.7 = Partial match (case region text contains a synonym)
    - Score 0.0 = No match

    This scoring allows cases with closely related but not identical regions
    to still appear in results (e.g., "shoulder" matching "rotator cuff").

    Algorithm:
    1. If no regions selected, return 0.0 (no filtering)
    2. Normalize the case region using our standardized mapping
    3. Check for exact match against selected regions → 1.0
    4. Check if any synonym appears in case region text → 0.7
    5. Otherwise return 0.0 (no match)

    Args:
        case_region: Free-text region from case data (e.g., "NECK")
        selected_regions: List of standardized region IDs user selected

    Returns:
        Float score between 0.0 and 1.0 indicating match quality

    Example:
        calculate_region_overlap("Cervical spine injury", ["cervical_spine"]) → 1.0
        calculate_region_overlap("Neck and shoulder", ["cervical_spine"]) → 0.7
        calculate_region_overlap("Lower back", ["cervical_spine"]) → 0.0
    """
    if not selected_regions:
        return 0.0  # No regions selected = no regional filtering

    # Normalize the case's region to a standardized ID
    case_region_normalized = normalize_region_name(case_region)

    # Perfect match: case region maps to one of the selected regions
    if case_region_normalized in selected_regions:
        return 1.0

    # Partial match: check if any synonym of selected regions appears in case text
    case_region_lower = case_region.lower()
    for region_id in selected_regions:
        region_data = region_map.get(region_id, {})
        terms = region_data.get("compendium_terms", [])

        for term in terms:
            if term.lower() in case_region_lower:
                return 0.7  # Partial match (synonym found)

    return 0.0  # No match

def search_cases(injury_text, selected_regions, gender=None, age=None, top_n=DEFAULT_TOP_N_RESULTS):
    """
    Hybrid search algorithm combining semantic similarity with anatomical region matching.

    This implements a two-stage ranking system:

    STAGE 1 - Region-Based Filtering:
    - Calculate region overlap scores for all cases
    - Filter to cases with region_score > 0 (any match)
    - Fallback to all cases if no region matches found

    STAGE 2 - Hybrid Scoring:
    - Compute semantic similarity using sentence-transformer embeddings (70% weight)
    - Combine with anatomical region overlap score (30% weight)
    - Sort by combined score and return top N results

    ALGORITHM RATIONALE:
    - Embedding similarity captures semantic meaning and injury descriptions
    - Region overlap ensures anatomical relevance
    - 70/30 weighting balances precision (regions) with recall (semantics)
    - Weight values optimized through validation on historical cases

    QUERY CONSTRUCTION:
    - Concatenates region labels + injury text for richer context
    - Example: "Cervical Spine (C1-C7) chronic disc herniation with radiculopathy"
    - This helps the embedding model understand anatomical context

    Args:
        injury_text: User's description of the injury (clinical detail encouraged)
        selected_regions: List of standardized region IDs from sidebar selection
        gender: Male/Female/None - currently not used in filtering (future enhancement)
        age: Age of plaintiff - currently not used in filtering (future enhancement)
        top_n: Number of results to return (default from config)

    Returns:
        List of (case_dict, embedding_similarity, combined_score) tuples,
        sorted by combined_score descending

    Example:
        results = search_cases(
            "C5-C6 disc herniation with chronic radiculopathy",
            ["cervical_spine"],
            top_n=15
        )
        # Returns top 15 cases ranked by similarity + region match
    """
    # Build query text by prepending region labels to provide anatomical context
    # This improves embedding quality for medical/legal terminology
    region_labels = ' '.join([region_map[r]['label'] for r in selected_regions])
    query_text = f"{region_labels} {injury_text}".strip()

    # Generate embedding vector for the query using cached sentence-transformer model
    query_vec = model.encode(query_text).reshape(1, -1)

    # ========================================================================
    # STAGE 1: Region-Based Filtering
    # ========================================================================
    # Calculate region overlap scores for each case and filter to matches
    if selected_regions:
        filtered_cases = []
        for case in cases:
            # Get the region overlap score (0.0, 0.7, or 1.0)
            region_score = calculate_region_overlap(case.get("region", ""), selected_regions)

            # Only include cases with some regional overlap
            if region_score > 0:
                case_copy = case.copy()
                case_copy["region_score"] = region_score  # Add score to case for later use
                filtered_cases.append(case_copy)

        # FALLBACK: If no cases match the selected regions at all,
        # include all cases but with region_score=0 (pure semantic search)
        # This prevents returning empty results for unusual region combinations
        if not filtered_cases:
            filtered_cases = [{**c, "region_score": 0} for c in cases]
    else:
        # No regions selected: use all cases with region_score=0
        # This makes regional weighting irrelevant (pure semantic search)
        filtered_cases = [{**c, "region_score": 0} for c in cases]

    # ========================================================================
    # STAGE 2: Semantic Similarity Calculation
    # ========================================================================
    # Extract pre-computed embedding vectors for all filtered cases
    vectors = np.array([c["embedding"] for c in filtered_cases])

    # Calculate cosine similarity between query and each case
    # Returns array of similarity scores in range [0, 1]
    embedding_sims = cosine_similarity(query_vec, vectors)[0]

    # ========================================================================
    # STAGE 3: Hybrid Score Combination
    # ========================================================================
    # Combine semantic similarity (70%) with regional matching (30%)
    # Formula: score = 0.7 * embedding_sim + 0.3 * region_score
    #
    # This weighting was chosen because:
    # - Embeddings capture nuanced injury descriptions (primary signal)
    # - Region matching ensures anatomical relevance (secondary filter)
    # - 70/30 split validated through testing on historical cases
    combined_scores = (EMBEDDING_WEIGHT * embedding_sims +
                      REGION_WEIGHT * np.array([c["region_score"] for c in filtered_cases]))

    # ========================================================================
    # STAGE 4: Ranking and Return
    # ========================================================================
    # Sort by combined score (highest first) and return top N
    ranked = sorted(
        zip(filtered_cases, embedding_sims, combined_scores),
        key=lambda x: x[2],  # Sort by combined_score (index 2)
        reverse=True
    )

    return ranked[:top_n]

def extract_damages_value(case):
    """Extract numeric damages value from case"""
    if case.get("damages"):
        return case["damages"]

    # Try to extract from raw fields or summary
    summary = case.get("summary_text", "")
    dollar_amounts = re.findall(r'\$[\d,]+', summary)

    for amount in dollar_amounts:
        try:
            value = float(amount.replace("$", "").replace(",", ""))
            if MIN_DAMAGE_VALUE <= value <= MAX_DAMAGE_VALUE:
                return value
        except:
            continue

    return None

# Main UI
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

# Sidebar for controls
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

        # Show current data source
        st.info(f"**Current:** {get_data_source()}")

        # Download current CPI data
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Download current data:**")
            # Generate CSV content from current data
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
                # Save uploaded file to data directory
                BOC_CPI_CSV.parent.mkdir(parents=True, exist_ok=True)
                with open(BOC_CPI_CSV, 'wb') as f:
                    f.write(cpi_file.getbuffer())

                # Reload data
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

# Initialize session state
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None

# Main content area
st.divider()

# Expert Report Upload Section
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
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                try:
                    # Analyze the report
                    analysis = analyze_expert_report(
                        tmp_path,
                        use_llm=use_llm
                    )

                    st.session_state.analysis_data = analysis

                    st.success("✅ Expert report analyzed successfully!")

                    # Display extracted information
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
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

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
    st.info("Body map visualization coming soon. Use the region selector in the sidebar.")

    # Placeholder for SVG body map
    st.caption("Regions available for selection:")
    st.caption("• Head & Spine (5 regions)")
    st.caption("• Torso (3 regions)")
    st.caption("• Upper Limbs (12 regions)")
    st.caption("• Lower Limbs (12 regions)")

# Search results
if search_button:
    if not injury_text.strip():
        st.warning("⚠️ Please enter an injury description")
    else:
        with st.spinner("Searching comparable cases..."):
            results = search_cases(
                injury_text,
                selected_regions,
                gender=gender if gender != "Not Specified" else None,
                age=age
            )

        # Store results in session state for PDF generation
        st.session_state.search_results = {
            'results': results,
            'injury_text': injury_text,
            'selected_regions': selected_regions,
            'gender': gender,
            'age': age,
            'timestamp': datetime.now()
        }

        st.divider()
        st.header("Search Results")

        # Extract damages for summary
        damages_values = []
        for case, emb_sim, combined_score in results:
            damage_val = extract_damages_value(case)
            if damage_val:
                damages_values.append(damage_val)

        # Damage summary
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

            # Prepare chart data
            chart_data = []
            for case, emb_sim, combined_score in results[:CHART_MAX_CASES]:
                damage_val = extract_damages_value(case)
                year = case.get('year')
                case_name = case.get('case_name', 'Unknown')
                citation = case.get('citation', case.get('summary_text', '')[:50])

                if damage_val and year:
                    adjusted_val = adjust_for_inflation(damage_val, year, DEFAULT_REFERENCE_YEAR)
                    if adjusted_val:
                        chart_data.append({
                            'case_name': case_name,
                            'year': year,
                            'original_award': damage_val,
                            'adjusted_award': adjusted_val,
                            'citation': citation,
                            'match_score': combined_score * 100
                        })

            if chart_data:
                # Create interactive Plotly chart
                fig = go.Figure()

                # Add original awards as bars
                fig.add_trace(go.Bar(
                    name=f'Original Award',
                    x=[f"{d['case_name'][:20]}... ({d['year']})" for d in chart_data],
                    y=[d['original_award'] for d in chart_data],
                    marker_color='lightblue',
                    hovertemplate='<b>%{x}</b><br>' +
                                  'Original Award: $%{y:,.0f}<br>' +
                                  '<extra></extra>'
                ))

                # Add inflation-adjusted awards as bars
                fig.add_trace(go.Bar(
                    name=f'Inflation-Adjusted ({DEFAULT_REFERENCE_YEAR}$)',
                    x=[f"{d['case_name'][:20]}... ({d['year']})" for d in chart_data],
                    y=[d['adjusted_award'] for d in chart_data],
                    marker_color='darkblue',
                    customdata=[[d['case_name'], d['citation'], d['match_score'], d['year'],
                                d['original_award'], d['adjusted_award']] for d in chart_data],
                    hovertemplate='<b>%{customdata[0]}</b><br>' +
                                  'Year: %{customdata[3]}<br>' +
                                  'Original: $%{customdata[4]:,.0f}<br>' +
                                  f'Adjusted ({DEFAULT_REFERENCE_YEAR}$): $%{{customdata[5]:,.0f}}<br>' +
                                  'Match Score: %{customdata[2]:.1f}%<br>' +
                                  'Citation: %{customdata[1]}<br>' +
                                  '<extra></extra>'
                ))

                # Update layout
                fig.update_layout(
                    barmode='group',
                    title=f'Damage Awards: Original vs Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR}',
                    xaxis_title='Case (Year)',
                    yaxis_title='Award Amount ($)',
                    yaxis=dict(tickformat='$,.0f'),
                    hovermode='closest',
                    height=500,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    xaxis={'categoryorder': 'total descending'}
                )

                st.plotly_chart(fig, use_container_width=True)

                # Summary statistics
                col1, col2, col3 = st.columns(3)

                with col1:
                    median_original = np.median([d['original_award'] for d in chart_data])
                    median_adjusted = np.median([d['adjusted_award'] for d in chart_data])
                    st.metric(
                        "Median (Original)",
                        f"${median_original:,.0f}",
                        help="Median of original award amounts"
                    )

                with col2:
                    st.metric(
                        f"Median ({DEFAULT_REFERENCE_YEAR}$)",
                        f"${median_adjusted:,.0f}",
                        delta=f"+${median_adjusted - median_original:,.0f}",
                        help=f"Median adjusted to {DEFAULT_REFERENCE_YEAR} dollars"
                    )

                with col3:
                    avg_inflation = np.mean([
                        ((d['adjusted_award'] - d['original_award']) / d['original_award']) * 100
                        for d in chart_data
                    ])
                    st.metric(
                        "Avg. Inflation Impact",
                        f"+{avg_inflation:.1f}%",
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

        # Display results
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

# Display results from session state (if available)
if st.session_state.search_results:
    st.divider()

    # PDF Download Section
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
                    # Get search results from session state
                    search_data = st.session_state.search_results
                    results = search_data['results']

                    # Extract damages values
                    damages_values = []
                    for case, emb_sim, combined_score in results:
                        damage_val = extract_damages_value(case)
                        if damage_val:
                            damages_values.append(damage_val)

                    # Create region labels map
                    region_labels = {
                        rid: region_map[rid]["label"]
                        for rid in search_data['selected_regions']
                        if rid in region_map
                    }

                    # Generate PDF
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

                        # Read the generated PDF
                        with open(pdf_path, 'rb') as pdf_file:
                            pdf_data = pdf_file.read()

                        st.success("✅ PDF report generated successfully!")

                        # Offer download
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

# Footer
st.divider()
st.caption("© 2024 Ontario Damages Compendium Tool | Built for legal professionals | Data source: CCLA Damages Compendium 2024")
st.caption("⚠️ This tool provides reference information only. Always verify case details and consult primary sources.")
