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


def get_all_judges(cases: List[Dict[str, Any]]) -> List[str]:
    """
    Extract all unique judge names from cases.

    Judge names are normalized by the LLM during parsing to last name only,
    with hyphenated surnames preserved (e.g., "Harrison-Young").

    Args:
        cases: List of case dictionaries

    Returns:
        Sorted list of unique judge names
    """
    judges = set()
    for case in cases:
        extended_data = case.get('extended_data', {})
        case_judges = extended_data.get('judges', [])
        if case_judges:
            for judge in case_judges:
                if judge and judge.strip():
                    judges.add(judge.strip())

    return sorted(list(judges))


def get_judge_cases(cases: List[Dict[str, Any]], judge_name: str) -> List[Dict[str, Any]]:
    """
    Filter cases decided by a specific judge.

    Judge names are already normalized by the LLM during parsing.

    Args:
        cases: List of all cases
        judge_name: Name of the judge to filter by

    Returns:
        List of cases decided by this judge
    """
    judge_cases = []
    for case in cases:
        extended_data = case.get('extended_data', {})
        case_judges = extended_data.get('judges', [])
        if case_judges:
            # Check if any case judge matches the search name
            for case_judge in case_judges:
                if case_judge and case_judge.strip() == judge_name:
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

    # Region distribution (normalize to uppercase for consistency)
    regions = []
    for case in judge_cases:
        region = case.get('region')
        if region:
            regions.append(region.strip().upper() if isinstance(region, str) else region)

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
    Create a timeline scatter plot showing award amounts over years with inflation adjustment.
    Includes region and court information in tooltips.

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
        region_raw = case.get('region', 'Unknown')
        region = region_raw.strip().upper() if isinstance(region_raw, str) and region_raw != 'Unknown' else region_raw
        court = case.get('court', 'N/A')

        if year and damage and damage > 0:
            # Calculate inflation-adjusted value
            adjusted_damage = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)

            data_points.append({
                'year': year,
                'damages': damage,
                'adjusted_damages': adjusted_damage if adjusted_damage else damage,
                'case_name': case_name,
                'region': region,
                'court': court
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
                f"Court: {row['court']}<br>"
                f"Original Award: ${row['damages']:,.0f}<br>"
                f"Adjusted ({DEFAULT_REFERENCE_YEAR}$): ${row['adjusted_damages']:,.0f}<br>"
                f"Inflation Impact: +{inflation_pct:.1f}%")
        hover_text.append(text)

    fig.add_trace(go.Scatter(
        x=df['year'],
        y=df['adjusted_damages'],
        mode='markers',
        name=f'Individual Awards',
        marker=dict(
            size=10,
            color=df['adjusted_damages'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title=f"Award ({DEFAULT_REFERENCE_YEAR}$)"),
            line=dict(width=1, color='white'),
            opacity=0.7
        ),
        text=hover_text,
        hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
    ))

    # Add median trend line (adjusted values) - shows volume via count in tooltip
    fig.add_trace(go.Scatter(
        x=yearly_stats['year'],
        y=yearly_stats['median'],
        mode='lines+markers',
        name=f'Yearly Median',
        line=dict(color='red', width=3, dash='dot'),
        marker=dict(size=12, symbol='diamond', line=dict(width=2, color='darkred')),
        text=[f"Median: ${val:,.0f}<br>Cases that year: {int(count)}"
              for val, count in zip(yearly_stats['median'], yearly_stats['count'])],
        hovertemplate='Year: %{x}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title=f'Awards Over Time (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
        xaxis_title='Year',
        yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
        hovermode='closest',
        showlegend=True,
        height=600,
        template='plotly_white'
    )

    fig.update_yaxes(tickformat='$,.0f')

    return fig


def _display_individual_judge_details(judge_name: str, judge_cases: List[Dict[str, Any]], stats: Dict[str, Any]) -> None:
    """
    Display detailed analytics for an individual judge.
    Helper function used in both single and comparison views.

    Args:
        judge_name: Name of the judge
        judge_cases: List of cases for this judge
        stats: Pre-calculated statistics dictionary
    """
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

    # Damages statistics
    if stats['cases_with_damages'] > 0:
        st.markdown(f"**💰 Award Statistics (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})**")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(f"Median ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['median']:,.0f}")

        with col2:
            st.metric(f"Mean ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['mean']:,.0f}")

        with col3:
            st.metric("Std. Deviation", f"${stats['adjusted_damages']['std']:,.0f}")

    # Timeline scatter plot
    st.markdown("**📈 Awards Over Time**")
    timeline_fig = create_awards_timeline_chart(judge_cases)
    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)


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

    # Calculate case counts for each judge
    judge_case_counts = {}
    for judge_name in all_judges:
        judge_cases = get_judge_cases(cases, judge_name)
        judge_case_counts[judge_name] = len(judge_cases)

    # Create judge options with case counts
    judge_options = [f"{judge_name} ({judge_case_counts[judge_name]} cases)" for judge_name in all_judges]

    # Judge selector - now with multi-select (max 8 for legibility)
    selected_judge_options = st.multiselect(
        "Select Judge(s) to Compare:",
        options=judge_options,
        default=[judge_options[0]] if judge_options else [],
        max_selections=8,
        help="Choose up to 8 judges to view and compare their award statistics and patterns. Each judge is shown in a different color."
    )

    # Extract judge names from selections (remove the case count suffix)
    selected_judges = []
    for option in selected_judge_options:
        # Extract judge name by removing the " (X cases)" suffix
        judge_name = option.rsplit(' (', 1)[0]
        selected_judges.append(judge_name)

    if not selected_judges:
        st.info("👆 Select one or more judges above to view their analytics")
        return

    # Check if we're comparing multiple judges
    is_comparison = len(selected_judges) > 1

    if is_comparison:
        # Display comparison view for multiple judges
        st.subheader(f"Comparing {len(selected_judges)} Judges")

        # Create comparison table
        comparison_data = []
        for judge_name in selected_judges:
            judge_cases = get_judge_cases(cases, judge_name)
            if judge_cases:
                stats = calculate_judge_statistics(judge_cases)
                comparison_data.append({
                    'Judge': judge_name,
                    'Total Cases': stats['total_cases'],
                    'Cases with Awards': stats['cases_with_damages'],
                    f'Median Award ({DEFAULT_REFERENCE_YEAR}$)': f"${stats['adjusted_damages']['median']:,.0f}",
                    f'Mean Award ({DEFAULT_REFERENCE_YEAR}$)': f"${stats['adjusted_damages']['mean']:,.0f}",
                    'Std. Deviation': f"${stats['adjusted_damages']['std']:,.0f}",
                    'Min Award': f"${stats['adjusted_damages']['min']:,.0f}",
                    'Max Award': f"${stats['adjusted_damages']['max']:,.0f}",
                    'Year Range': f"{stats['years']['min']}-{stats['years']['max']}" if stats['years']['min'] and stats['years']['max'] else "N/A",
                    'Body Regions': stats['regions']['unique_count']
                })

        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

            st.divider()

            # Combined timeline scatter plot for all selected judges
            st.subheader("📈 Awards Over Time - Judge Comparison")

            fig_timeline = go.Figure()

            for judge_name in selected_judges:
                judge_cases = get_judge_cases(cases, judge_name)
                if judge_cases:
                    # Prepare data
                    data_points = []
                    for case in judge_cases:
                        year = case.get('year')
                        damage = case.get('damages')
                        case_name = case.get('case_name', 'Unknown')
                        region_raw = case.get('region', 'Unknown')
                        region = region_raw.strip().upper() if isinstance(region_raw, str) and region_raw != 'Unknown' else region_raw
                        court = case.get('court', 'N/A')

                        if year and damage and damage > 0:
                            adjusted_damage = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                            data_points.append({
                                'year': year,
                                'adjusted_damages': adjusted_damage if adjusted_damage else damage,
                                'case_name': case_name,
                                'judge': judge_name,
                                'region': region,
                                'court': court
                            })

                    if data_points:
                        df = pd.DataFrame(data_points)

                        # Add scatter plot for this judge
                        hover_text = [f"<b>{row['case_name']}</b><br>"
                                      f"Judge: {row['judge']}<br>"
                                      f"Region: {row['region']}<br>"
                                      f"Court: {row['court']}<br>"
                                      f"Award ({DEFAULT_REFERENCE_YEAR}$): ${row['adjusted_damages']:,.0f}"
                                      for _, row in df.iterrows()]

                        fig_timeline.add_trace(go.Scatter(
                            x=df['year'],
                            y=df['adjusted_damages'],
                            mode='markers',
                            name=judge_name,
                            marker=dict(size=10, line=dict(width=1, color='white'), opacity=0.7),
                            text=hover_text,
                            hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
                        ))

            if fig_timeline.data:
                fig_timeline.update_layout(
                    title=f'Awards Timeline Comparison (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
                    xaxis_title='Year',
                    yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
                    hovermode='closest',
                    showlegend=True,
                    height=500,
                    template='plotly_white'
                )
                fig_timeline.update_yaxes(tickformat='$,.0f')
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("Insufficient data with both year and damages information to display timeline")

        # Individual judge details in expanders
        st.divider()
        st.subheader("📋 Individual Judge Details")

        for judge_name in selected_judges:
            with st.expander(f"View details for {judge_name}", expanded=False):
                judge_cases = get_judge_cases(cases, judge_name)
                if judge_cases:
                    stats = calculate_judge_statistics(judge_cases)
                    _display_individual_judge_details(judge_name, judge_cases, stats)
                else:
                    st.warning(f"No cases found for {judge_name}")

        return

    # Single judge view (original behavior)
    selected_judge = selected_judges[0]

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

    # Timeline scatter plot (includes volume info in median trend tooltips)
    st.subheader("📈 Awards Over Time")
    st.caption("💡 Hover over points to see case details including region and court. The red median trend line shows case volume per year in its tooltip.")
    timeline_fig = create_awards_timeline_chart(judge_cases)

    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)
    else:
        st.info("Insufficient data with both year and damages information to display timeline")

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
            region_raw = case.get('region', 'Unknown')
            region = region_raw.strip().upper() if isinstance(region_raw, str) and region_raw != 'Unknown' else region_raw
            case_list.append({
                'Case Name': case.get('case_name', 'Unknown'),
                'Year': case.get('year', 'N/A'),
                'Region': region,
                'Court': case.get('court', 'N/A'),
                'Award': f"${case.get('damages', 0):,.0f}" if case.get('damages') else 'N/A'
            })

        cases_df = pd.DataFrame(case_list)
        st.dataframe(cases_df, width='stretch', hide_index=True)
