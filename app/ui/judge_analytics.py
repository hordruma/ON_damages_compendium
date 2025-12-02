"""
Judge-specific analytics and visualizations.

This module provides analytics tools for examining individual judge's
award patterns, including temporal trends, damage ranges, and case distributions.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from collections import Counter
import re

# Import inflation adjustment
try:
    from inflation_adjuster import adjust_for_inflation, DEFAULT_REFERENCE_YEAR
except ImportError:
    # Fallback if module not available
    DEFAULT_REFERENCE_YEAR = 2024
    def adjust_for_inflation(amount, from_year, to_year):
        return None


def normalize_judge_name(judge_name: str) -> str:
    """
    Normalize judge names to handle variations with initials.

    Handles cases like:
    - "J.A.Harrison-Young" → "Harrison-Young"
    - "J.Harrison-Young" → "Harrison-Young"
    - "Harrison-Young" → "Harrison-Young"
    - "Smith J." → "Smith"
    - "J. Smith" → "Smith"

    Args:
        judge_name: Raw judge name

    Returns:
        Normalized judge name (last name, preserving hyphens)
    """
    if not judge_name:
        return ""

    name = judge_name.strip()

    # Remove trailing " J." or " JJ." suffixes (for Justice/Justices)
    name = re.sub(r'\s+J\.?J?\.?$', '', name, flags=re.IGNORECASE)

    # Pattern to match initials at the start: one or more initials with dots
    # e.g., "J.", "J.A.", "J.A.B."
    initial_pattern = r'^([A-Z]\.\s*)+\s*'

    # Remove leading initials
    normalized = re.sub(initial_pattern, '', name)

    # If nothing left after removing initials, return original
    if not normalized.strip():
        return name

    # Split by spaces to get parts
    parts = normalized.split()

    # If we have multiple parts, take the last one (the surname)
    # This handles cases like "John Smith" → "Smith"
    # But preserves hyphenated names like "Harrison-Young"
    if len(parts) > 1:
        # Check if last part contains hyphen (hyphenated surname)
        if '-' in parts[-1]:
            return parts[-1]
        # Otherwise return the last part
        return parts[-1]

    return normalized.strip()


def get_all_judges(cases: List[Dict[str, Any]]) -> List[str]:
    """
    Extract all unique judge names from cases with normalization.

    Normalizes judge names to handle variations with initials:
    - "J.A.Harrison-Young", "J.Harrison-Young", "Harrison-Young" → "Harrison-Young"

    Args:
        cases: List of case dictionaries

    Returns:
        Sorted list of unique normalized judge names
    """
    judges = set()
    for case in cases:
        extended_data = case.get('extended_data', {})
        case_judges = extended_data.get('judges', [])
        if case_judges:
            for judge in case_judges:
                if judge and judge.strip():
                    normalized = normalize_judge_name(judge.strip())
                    if normalized:
                        judges.add(normalized)

    return sorted(list(judges))


def get_judge_cases(cases: List[Dict[str, Any]], judge_name: str) -> List[Dict[str, Any]]:
    """
    Filter cases decided by a specific judge with name normalization.

    Matches the judge name after normalizing both the search name and case judges.
    This ensures that "J.A.Harrison-Young", "J.Harrison-Young", and "Harrison-Young"
    all match the same judge.

    Args:
        cases: List of all cases
        judge_name: Name of the judge to filter by (will be normalized)

    Returns:
        List of cases decided by this judge
    """
    # Normalize the search judge name
    normalized_search_name = normalize_judge_name(judge_name)

    judge_cases = []
    for case in cases:
        extended_data = case.get('extended_data', {})
        case_judges = extended_data.get('judges', [])
        if case_judges:
            # Check if any normalized case judge matches the search name
            for case_judge in case_judges:
                if case_judge and normalize_judge_name(case_judge.strip()) == normalized_search_name:
                    judge_cases.append(case)
                    break  # Don't add the same case multiple times

    return judge_cases


def calculate_judge_statistics(judge_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate comprehensive statistics for a judge's cases.

    Args:
        judge_cases: List of cases decided by the judge

    Returns:
        Dictionary containing various statistics
    """
    total_cases = len(judge_cases)

    # Extract damages values (both original and inflation-adjusted)
    damages_values = []
    adjusted_damages_values = []
    for case in judge_cases:
        damage = case.get('damages')
        year = case.get('year')

        if damage and damage > 0:
            damages_values.append(damage)

            # Calculate inflation-adjusted value
            if year:
                adjusted = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                adjusted_damages_values.append(adjusted if adjusted else damage)
            else:
                adjusted_damages_values.append(damage)

    # Year distribution
    years = []
    for case in judge_cases:
        year = case.get('year')
        if year:
            years.append(year)

    # Region distribution
    regions = []
    for case in judge_cases:
        region = case.get('region')
        if region:
            regions.append(region)

    # Court distribution
    courts = []
    for case in judge_cases:
        court = case.get('court')
        if court:
            courts.append(court)

    stats = {
        'total_cases': total_cases,
        'cases_with_damages': len(damages_values),
        'damages': {
            'values': damages_values,
            'mean': np.mean(damages_values) if damages_values else 0,
            'median': np.median(damages_values) if damages_values else 0,
            'min': min(damages_values) if damages_values else 0,
            'max': max(damages_values) if damages_values else 0,
            'std': np.std(damages_values) if damages_values else 0,
        },
        'adjusted_damages': {
            'values': adjusted_damages_values,
            'mean': np.mean(adjusted_damages_values) if adjusted_damages_values else 0,
            'median': np.median(adjusted_damages_values) if adjusted_damages_values else 0,
            'min': min(adjusted_damages_values) if adjusted_damages_values else 0,
            'max': max(adjusted_damages_values) if adjusted_damages_values else 0,
            'std': np.std(adjusted_damages_values) if adjusted_damages_values else 0,
        },
        'years': {
            'all': years,
            'min': min(years) if years else None,
            'max': max(years) if years else None,
            'distribution': dict(Counter(years))
        },
        'regions': {
            'distribution': dict(Counter(regions)),
            'unique_count': len(set(regions))
        },
        'courts': {
            'distribution': dict(Counter(courts)),
            'unique_count': len(set(courts))
        }
    }

    return stats


def create_awards_timeline_chart(judge_cases: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """
    Create a timeline chart showing award amounts over years with inflation adjustment.

    Args:
        judge_cases: List of cases decided by the judge

    Returns:
        Plotly figure or None if insufficient data
    """
    # Prepare data
    data_points = []
    for case in judge_cases:
        year = case.get('year')
        damage = case.get('damages')
        case_name = case.get('case_name', 'Unknown')
        region = case.get('region', 'Unknown')

        if year and damage and damage > 0:
            # Calculate inflation-adjusted value
            adjusted_damage = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)

            data_points.append({
                'year': year,
                'damages': damage,
                'adjusted_damages': adjusted_damage if adjusted_damage else damage,
                'case_name': case_name,
                'region': region
            })

    if not data_points:
        return None

    df = pd.DataFrame(data_points)

    # Calculate yearly statistics (using adjusted values)
    yearly_stats = df.groupby('year').agg({
        'adjusted_damages': ['mean', 'median', 'count']
    }).reset_index()
    yearly_stats.columns = ['year', 'mean', 'median', 'count']

    # Create figure
    fig = go.Figure()

    # Add scatter plot for individual cases (adjusted values)
    hover_text = []
    for _, row in df.iterrows():
        inflation_pct = ((row['adjusted_damages'] / row['damages']) - 1) * 100 if row['damages'] > 0 else 0
        text = (f"<b>{row['case_name']}</b><br>"
                f"Region: {row['region']}<br>"
                f"Original Award: ${row['damages']:,.0f}<br>"
                f"Adjusted ({DEFAULT_REFERENCE_YEAR}$): ${row['adjusted_damages']:,.0f}<br>"
                f"Inflation Impact: +{inflation_pct:.1f}%")
        hover_text.append(text)

    fig.add_trace(go.Scatter(
        x=df['year'],
        y=df['adjusted_damages'],
        mode='markers',
        name=f'Individual Awards ({DEFAULT_REFERENCE_YEAR}$)',
        marker=dict(
            size=8,
            color=df['adjusted_damages'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title=f"Award ({DEFAULT_REFERENCE_YEAR}$)"),
            line=dict(width=1, color='white')
        ),
        text=hover_text,
        hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
    ))

    # Add median trend line (adjusted values)
    fig.add_trace(go.Scatter(
        x=yearly_stats['year'],
        y=yearly_stats['median'],
        mode='lines+markers',
        name=f'Yearly Median ({DEFAULT_REFERENCE_YEAR}$)',
        line=dict(color='red', width=3),
        marker=dict(size=10, symbol='diamond'),
        text=[f"Median: ${val:,.0f}<br>Cases: {int(count)}"
              for val, count in zip(yearly_stats['median'], yearly_stats['count'])],
        hovertemplate='Year: %{x}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title=f'Award Amounts Over Time (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
        xaxis_title='Year',
        yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
        hovermode='closest',
        showlegend=True,
        height=500,
        template='plotly_white'
    )

    fig.update_yaxes(tickformat='$,.0f')

    return fig


def create_region_distribution_chart(stats: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Create a bar chart showing distribution of cases by body region.

    Args:
        stats: Statistics dictionary from calculate_judge_statistics

    Returns:
        Plotly figure or None if insufficient data
    """
    region_dist = stats['regions']['distribution']

    if not region_dist:
        return None

    # Sort by count
    sorted_regions = sorted(region_dist.items(), key=lambda x: x[1], reverse=True)
    regions, counts = zip(*sorted_regions)

    fig = go.Figure(data=[
        go.Bar(
            x=list(counts),
            y=list(regions),
            orientation='h',
            marker=dict(
                color=list(counts),
                colorscale='Blues',
                showscale=False
            ),
            text=[f"{count} case{'s' if count != 1 else ''}" for count in counts],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title='Cases by Body Region',
        xaxis_title='Number of Cases',
        yaxis_title='Body Region',
        height=max(400, len(regions) * 25),
        template='plotly_white',
        showlegend=False
    )

    return fig


def create_damages_distribution_chart(judge_cases: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """
    Create a histogram showing distribution of inflation-adjusted damage awards.

    Args:
        judge_cases: List of cases decided by the judge

    Returns:
        Plotly figure or None if insufficient data
    """
    # Collect inflation-adjusted damages
    adjusted_damages = []
    for case in judge_cases:
        year = case.get('year')
        damage = case.get('damages')

        if damage and damage > 0:
            if year:
                adjusted = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                adjusted_damages.append(adjusted if adjusted else damage)
            else:
                # If no year, use original value
                adjusted_damages.append(damage)

    if not adjusted_damages:
        return None

    median = np.median(adjusted_damages)

    fig = go.Figure(data=[
        go.Histogram(
            x=adjusted_damages,
            nbinsx=30,
            marker=dict(
                color='rgba(54, 162, 235, 0.7)',
                line=dict(color='rgba(54, 162, 235, 1)', width=1)
            ),
            hovertemplate=f'Award Range ({DEFAULT_REFERENCE_YEAR}$): $%{{x}}<br>Count: %{{y}}<extra></extra>'
        )
    ])

    # Add median line
    fig.add_vline(
        x=median,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Median: ${median:,.0f}",
        annotation_position="top"
    )

    fig.update_layout(
        title=f'Distribution of Award Amounts (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
        xaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
        yaxis_title='Number of Cases',
        height=400,
        template='plotly_white',
        showlegend=False
    )

    fig.update_xaxes(tickformat='$,.0f')

    return fig


def create_yearly_case_volume_chart(stats: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Create a bar chart showing case volume by year.

    Args:
        stats: Statistics dictionary from calculate_judge_statistics

    Returns:
        Plotly figure or None if insufficient data
    """
    year_dist = stats['years']['distribution']

    if not year_dist:
        return None

    # Sort by year
    sorted_years = sorted(year_dist.items())
    years, counts = zip(*sorted_years)

    fig = go.Figure(data=[
        go.Bar(
            x=list(years),
            y=list(counts),
            marker=dict(
                color='rgba(75, 192, 192, 0.7)',
                line=dict(color='rgba(75, 192, 192, 1)', width=1)
            ),
            text=list(counts),
            textposition='auto',
        )
    ])

    fig.update_layout(
        title='Case Volume by Year',
        xaxis_title='Year',
        yaxis_title='Number of Cases',
        height=400,
        template='plotly_white',
        showlegend=False
    )

    return fig


def display_judge_analytics_page(cases: List[Dict[str, Any]]) -> None:
    """
    Main function to display the judge analytics page.

    Args:
        cases: List of all cases
    """
    st.header("👨‍⚖️ Judge Analytics")
    st.markdown("Explore award patterns and statistics for individual judges")

    # Get all judges
    all_judges = get_all_judges(cases)

    if not all_judges:
        st.warning("⚠️ No judge information found in the dataset. Please ensure your data includes judge names.")
        st.info("💡 Regenerate embeddings from the AI-parsed data to include judge information.")
        return

    st.info(f"📊 Dataset contains {len(all_judges)} unique judges")

    # Judge selector
    selected_judge = st.selectbox(
        "Select a Judge:",
        options=all_judges,
        help="Choose a judge to view their award statistics and patterns"
    )

    if not selected_judge:
        st.info("👆 Select a judge above to view their analytics")
        return

    # Get cases for this judge
    judge_cases = get_judge_cases(cases, selected_judge)

    if not judge_cases:
        st.warning(f"No cases found for {selected_judge}")
        return

    # Calculate statistics
    stats = calculate_judge_statistics(judge_cases)

    # Display overview metrics
    st.subheader(f"Overview: {selected_judge}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Cases", stats['total_cases'])

    with col2:
        st.metric("Cases with Awards", stats['cases_with_damages'])

    with col3:
        if stats['years']['min'] and stats['years']['max']:
            year_range = f"{stats['years']['min']}-{stats['years']['max']}"
            st.metric("Year Range", year_range)
        else:
            st.metric("Year Range", "N/A")

    with col4:
        st.metric("Body Regions", stats['regions']['unique_count'])

    st.divider()

    # Damages statistics (inflation-adjusted)
    if stats['cases_with_damages'] > 0:
        st.subheader(f"💰 Award Statistics (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                f"Median Award ({DEFAULT_REFERENCE_YEAR}$)",
                f"${stats['adjusted_damages']['median']:,.0f}",
                help=f"Middle value of all awards, adjusted to {DEFAULT_REFERENCE_YEAR} dollars"
            )

        with col2:
            st.metric(
                f"Mean Award ({DEFAULT_REFERENCE_YEAR}$)",
                f"${stats['adjusted_damages']['mean']:,.0f}",
                help=f"Average of all awards, adjusted to {DEFAULT_REFERENCE_YEAR} dollars"
            )

        with col3:
            st.metric(
                "Std. Deviation",
                f"${stats['adjusted_damages']['std']:,.0f}",
                help="Measure of award variability (inflation-adjusted)"
            )

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Minimum Award", f"${stats['adjusted_damages']['min']:,.0f}")

        with col2:
            st.metric("Maximum Award", f"${stats['adjusted_damages']['max']:,.0f}")

        st.caption(f"💡 All awards adjusted to {DEFAULT_REFERENCE_YEAR} dollars using Canadian CPI")

        st.divider()

    # Timeline chart
    st.subheader("📈 Awards Timeline")
    timeline_fig = create_awards_timeline_chart(judge_cases)

    if timeline_fig:
        st.plotly_chart(timeline_fig, width='stretch')
    else:
        st.info("Insufficient data with both year and damages information to display timeline")

    st.divider()

    # Two column layout for distributions
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Award Distribution")
        dist_fig = create_damages_distribution_chart(judge_cases)
        if dist_fig:
            st.plotly_chart(dist_fig, width='stretch')
        else:
            st.info("No damages data available")

    with col2:
        st.subheader("📅 Case Volume by Year")
        volume_fig = create_yearly_case_volume_chart(stats)
        if volume_fig:
            st.plotly_chart(volume_fig, width='stretch')
        else:
            st.info("No year data available")

    st.divider()

    # Region distribution
    st.subheader("🏥 Cases by Body Region")
    region_fig = create_region_distribution_chart(stats)

    if region_fig:
        st.plotly_chart(region_fig, width='stretch')
    else:
        st.info("No region data available")

    st.divider()

    # Court distribution
    if stats['courts']['distribution']:
        st.subheader("🏛️ Court Distribution")
        court_dist = stats['courts']['distribution']
        court_df = pd.DataFrame(
            list(court_dist.items()),
            columns=['Court', 'Cases']
        ).sort_values('Cases', ascending=False)

        st.dataframe(court_df, width='stretch', hide_index=True)

    # Detailed case list
    with st.expander(f"📋 View All {len(judge_cases)} Cases"):
        case_list = []
        for case in judge_cases:
            case_list.append({
                'Case Name': case.get('case_name', 'Unknown'),
                'Year': case.get('year', 'N/A'),
                'Region': case.get('region', 'Unknown'),
                'Court': case.get('court', 'N/A'),
                'Award': f"${case.get('damages', 0):,.0f}" if case.get('damages') else 'N/A'
            })

        cases_df = pd.DataFrame(case_list)
        st.dataframe(cases_df, width='stretch', hide_index=True)
