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


def get_all_judges(cases: List[Dict[str, Any]]) -> List[str]:
    """
    Extract all unique judge names from cases.

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
        if judge_name in case_judges:
            judge_cases.append(case)

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

    # Extract damages values
    damages_values = []
    for case in judge_cases:
        damage = case.get('damages')
        if damage and damage > 0:
            damages_values.append(damage)

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
    Create a timeline chart showing award amounts over years.

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
            data_points.append({
                'year': year,
                'damages': damage,
                'case_name': case_name,
                'region': region
            })

    if not data_points:
        return None

    df = pd.DataFrame(data_points)

    # Calculate yearly statistics
    yearly_stats = df.groupby('year')['damages'].agg(['mean', 'median', 'count']).reset_index()

    # Create figure with secondary y-axis
    fig = go.Figure()

    # Add scatter plot for individual cases
    fig.add_trace(go.Scatter(
        x=df['year'],
        y=df['damages'],
        mode='markers',
        name='Individual Awards',
        marker=dict(
            size=8,
            color=df['damages'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Award Amount"),
            line=dict(width=1, color='white')
        ),
        text=[f"{row['case_name']}<br>{row['region']}<br>${row['damages']:,.0f}"
              for _, row in df.iterrows()],
        hovertemplate='<b>%{text}</b><br>Year: %{x}<extra></extra>'
    ))

    # Add median trend line
    fig.add_trace(go.Scatter(
        x=yearly_stats['year'],
        y=yearly_stats['median'],
        mode='lines+markers',
        name='Yearly Median',
        line=dict(color='red', width=3),
        marker=dict(size=10, symbol='diamond'),
        text=[f"Median: ${val:,.0f}<br>Cases: {count}"
              for val, count in zip(yearly_stats['median'], yearly_stats['count'])],
        hovertemplate='Year: %{x}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title='Award Amounts Over Time',
        xaxis_title='Year',
        yaxis_title='Award Amount ($)',
        hovermode='closest',
        showlegend=True,
        height=500,
        template='plotly_white'
    )

    fig.update_yaxis(tickformat='$,.0f')

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


def create_damages_distribution_chart(stats: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Create a histogram showing distribution of damage awards.

    Args:
        stats: Statistics dictionary from calculate_judge_statistics

    Returns:
        Plotly figure or None if insufficient data
    """
    damages_values = stats['damages']['values']

    if not damages_values:
        return None

    fig = go.Figure(data=[
        go.Histogram(
            x=damages_values,
            nbinsx=30,
            marker=dict(
                color='rgba(54, 162, 235, 0.7)',
                line=dict(color='rgba(54, 162, 235, 1)', width=1)
            ),
            hovertemplate='Award Range: $%{x}<br>Count: %{y}<extra></extra>'
        )
    ])

    # Add median line
    median = stats['damages']['median']
    fig.add_vline(
        x=median,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Median: ${median:,.0f}",
        annotation_position="top"
    )

    fig.update_layout(
        title='Distribution of Award Amounts',
        xaxis_title='Award Amount ($)',
        yaxis_title='Number of Cases',
        height=400,
        template='plotly_white',
        showlegend=False
    )

    fig.update_xaxis(tickformat='$,.0f')

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

    # Damages statistics
    if stats['cases_with_damages'] > 0:
        st.subheader("💰 Award Statistics")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Median Award",
                f"${stats['damages']['median']:,.0f}",
                help="Middle value of all awards"
            )

        with col2:
            st.metric(
                "Mean Award",
                f"${stats['damages']['mean']:,.0f}",
                help="Average of all awards"
            )

        with col3:
            st.metric(
                "Std. Deviation",
                f"${stats['damages']['std']:,.0f}",
                help="Measure of award variability"
            )

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Minimum Award", f"${stats['damages']['min']:,.0f}")

        with col2:
            st.metric("Maximum Award", f"${stats['damages']['max']:,.0f}")

        st.divider()

    # Timeline chart
    st.subheader("📈 Awards Timeline")
    timeline_fig = create_awards_timeline_chart(judge_cases)

    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)
    else:
        st.info("Insufficient data with both year and damages information to display timeline")

    st.divider()

    # Two column layout for distributions
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Award Distribution")
        dist_fig = create_damages_distribution_chart(stats)
        if dist_fig:
            st.plotly_chart(dist_fig, use_container_width=True)
        else:
            st.info("No damages data available")

    with col2:
        st.subheader("📅 Case Volume by Year")
        volume_fig = create_yearly_case_volume_chart(stats)
        if volume_fig:
            st.plotly_chart(volume_fig, use_container_width=True)
        else:
            st.info("No year data available")

    st.divider()

    # Region distribution
    st.subheader("🏥 Cases by Body Region")
    region_fig = create_region_distribution_chart(stats)

    if region_fig:
        st.plotly_chart(region_fig, use_container_width=True)
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

        st.dataframe(court_df, use_container_width=True, hide_index=True)

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
        st.dataframe(cases_df, use_container_width=True, hide_index=True)
