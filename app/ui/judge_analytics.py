"""
Judge-specific analytics and visualizations.

Provides analytics tools for examining individual judge's award patterns,
including temporal trends, damage ranges, and case distributions.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from collections import Counter

try:
    from inflation_adjuster import adjust_for_inflation, DEFAULT_REFERENCE_YEAR
except ImportError:
    DEFAULT_REFERENCE_YEAR = 2024
    def adjust_for_inflation(amount, from_year, to_year):
        return None

from app.core.search import filter_outliers

# MD3 color palette for charts
MD3_COLORS = [
    "#1a73e8", "#e8710a", "#1e8e3e", "#d93025",
    "#9334e6", "#f538a0", "#12b5cb", "#e37400",
]


def get_all_judges(cases: List[Dict[str, Any]]) -> List[str]:
    """Extract all unique judge names from cases."""
    judges = set()
    for case in cases:
        extended_data = case.get('extended_data', {})
        case_judges = extended_data.get('judges', [])
        if case_judges:
            for judge in case_judges:
                if judge and judge.strip():
                    normalized_judge = judge.strip().title()
                    judges.add(normalized_judge)
    return sorted(list(judges))


def get_judge_cases(cases: List[Dict[str, Any]], judge_name: str, deduplicate: bool = True) -> List[Dict[str, Any]]:
    """Filter cases decided by a specific judge."""
    judge_cases = []
    normalized_search_name = judge_name.strip().title()

    for case in cases:
        extended_data = case.get('extended_data', {})
        case_judges = extended_data.get('judges', [])
        if case_judges:
            for case_judge in case_judges:
                if case_judge and case_judge.strip().title() == normalized_search_name:
                    judge_cases.append(case)
                    break

    if deduplicate:
        seen = set()
        unique_cases = []
        for case in judge_cases:
            case_name = case.get('case_name', '')
            year = case.get('year', '')
            identifier = f"{case_name}|{year}"
            if identifier not in seen:
                seen.add(identifier)
                unique_cases.append(case)
        return unique_cases

    return judge_cases


def calculate_judge_statistics(judge_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate comprehensive statistics for a judge's cases."""
    total_cases = len(judge_cases)

    damages_values = []
    adjusted_damages_values = []
    for case in judge_cases:
        damage = case.get('damages')
        year = case.get('year')
        if damage and damage > 0:
            damages_values.append(damage)
            if year:
                adjusted = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                adjusted_damages_values.append(adjusted if adjusted else damage)
            else:
                adjusted_damages_values.append(damage)

    years = [case.get('year') for case in judge_cases if case.get('year')]

    regions = []
    for case in judge_cases:
        region = case.get('region')
        if region:
            regions.append(region.strip().upper() if isinstance(region, str) else region)

    courts = [case.get('court') for case in judge_cases if case.get('court')]

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
    """Create a timeline scatter plot showing award amounts over years."""
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
                'damages': damage,
                'adjusted_damages': adjusted_damage if adjusted_damage else damage,
                'case_name': case_name,
                'region': region,
                'court': court
            })

    if not data_points:
        return None

    df = pd.DataFrame(data_points)

    yearly_stats = df.groupby('year').agg({
        'adjusted_damages': ['mean', 'median', 'count']
    }).reset_index()
    yearly_stats.columns = ['year', 'mean', 'median', 'count']

    fig = go.Figure()

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
        name='Individual Awards',
        marker=dict(
            size=10,
            color=MD3_COLORS[0],
            line=dict(width=1, color='white'),
            opacity=0.7
        ),
        text=hover_text,
        hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=yearly_stats['year'],
        y=yearly_stats['median'],
        mode='lines+markers',
        name='Yearly Median',
        line=dict(color=MD3_COLORS[3], width=2, dash='dot'),
        marker=dict(size=8, symbol='diamond', line=dict(width=1, color=MD3_COLORS[3])),
        text=[f"Median: ${val:,.0f}<br>Cases that year: {int(count)}"
              for val, count in zip(yearly_stats['median'], yearly_stats['count'])],
        hovertemplate='Year: %{x}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text=f'Awards Over Time (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
            font=dict(size=16),
        ),
        xaxis_title='Year',
        yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
        hovermode='closest',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="center",
            x=0.5,
        ),
        height=500,
        template='plotly_white',
        font=dict(family="Google Sans, Roboto, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    fig.update_yaxes(tickformat='$,.0f')

    return fig


def _display_individual_judge_details(judge_name: str, judge_cases: List[Dict[str, Any]], stats: Dict[str, Any]) -> None:
    """Display detailed analytics for an individual judge."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Cases", stats['total_cases'])
    with col2:
        st.metric("Cases with Awards", stats['cases_with_damages'])
    with col3:
        if stats['years']['min'] and stats['years']['max']:
            st.metric("Year Range", f"{stats['years']['min']}-{stats['years']['max']}")
        else:
            st.metric("Year Range", "N/A")
    with col4:
        st.metric("Body Regions", stats['regions']['unique_count'])

    if stats['cases_with_damages'] > 0:
        st.markdown(f"**Award Statistics (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})**")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"Median ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['median']:,.0f}")
        with col2:
            st.metric(f"Mean ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['mean']:,.0f}")
        with col3:
            st.metric("Std. Deviation", f"${stats['adjusted_damages']['std']:,.0f}")

    st.markdown("**Awards Over Time**")
    timeline_fig = create_awards_timeline_chart(judge_cases)
    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)


def display_judge_analytics_page(cases: List[Dict[str, Any]], include_outliers: bool = True) -> None:
    """Main function to display the judge analytics page."""

    def get_filtered_judge_cases(judge_name: str) -> List[Dict[str, Any]]:
        judge_cases = get_judge_cases(cases, judge_name)
        if not include_outliers and judge_cases:
            judge_cases = filter_outliers(judge_cases)
        return judge_cases

    all_judges = get_all_judges(cases)

    if not all_judges:
        st.warning("No judge information found in the dataset.")
        st.info("Regenerate embeddings from the AI-parsed data to include judge information.")
        return

    st.caption(f"{len(all_judges)} unique judges in dataset")

    judge_case_counts = {}
    for judge_name in all_judges:
        judge_cases = get_filtered_judge_cases(judge_name)
        judge_case_counts[judge_name] = len(judge_cases)

    judges_by_count = sorted(judge_case_counts.items(), key=lambda x: x[1], reverse=True)
    judge_options = [f"{judge_name} ({count} cases)" for judge_name, count in judges_by_count]

    max_preselect = 10
    default_selections = judge_options[:min(max_preselect, len(judge_options))]

    selected_judge_options = st.multiselect(
        "Select judges to compare",
        options=judge_options,
        default=default_selections,
        help=f"Top {max_preselect} judges by case count are pre-selected.",
        key="judge_selector"
    )

    selected_judges = []
    for option in selected_judge_options:
        judge_name = option.rsplit(' (', 1)[0]
        selected_judges.append(judge_name)

    if not selected_judges:
        st.info("Select one or more judges above to view their analytics.")
        return

    is_comparison = len(selected_judges) > 1

    if is_comparison:
        st.subheader(f"Comparing {len(selected_judges)} Judges")

        comparison_data = []
        for judge_name in selected_judges:
            judge_cases = get_filtered_judge_cases(judge_name)
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

            st.subheader("Awards Over Time — Judge Comparison")

            fig_timeline = go.Figure()

            for i, judge_name in enumerate(selected_judges):
                judge_cases = get_filtered_judge_cases(judge_name)
                if judge_cases:
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
                            marker=dict(
                                size=10,
                                color=MD3_COLORS[i % len(MD3_COLORS)],
                                line=dict(width=1, color='white'),
                                opacity=0.7
                            ),
                            text=hover_text,
                            hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
                        ))

            if fig_timeline.data:
                fig_timeline.update_layout(
                    title=dict(
                        text=f'Awards Timeline Comparison (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
                        font=dict(size=16),
                    ),
                    xaxis_title='Year',
                    yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
                    hovermode='closest',
                    showlegend=True,
                    height=500,
                    template='plotly_white',
                    font=dict(family="Google Sans, Roboto, sans-serif"),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                )
                fig_timeline.update_yaxes(tickformat='$,.0f')
                st.plotly_chart(fig_timeline, use_container_width=True)
            else:
                st.info("Insufficient data to display timeline.")

        st.divider()
        st.subheader("Individual Judge Details")

        for judge_name in selected_judges:
            with st.expander(f"{judge_name}", expanded=False):
                judge_cases = get_filtered_judge_cases(judge_name)
                if judge_cases:
                    stats = calculate_judge_statistics(judge_cases)
                    _display_individual_judge_details(judge_name, judge_cases, stats)
                else:
                    st.warning(f"No cases found for {judge_name}")

        return

    # Single judge view
    selected_judge = selected_judges[0]
    judge_cases = get_filtered_judge_cases(selected_judge)

    if not judge_cases:
        st.warning(f"No cases found for {selected_judge}")
        return

    stats = calculate_judge_statistics(judge_cases)

    st.subheader(f"Overview: {selected_judge}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Cases", stats['total_cases'])
    with col2:
        st.metric("Cases with Awards", stats['cases_with_damages'])
    with col3:
        if stats['years']['min'] and stats['years']['max']:
            st.metric("Year Range", f"{stats['years']['min']}-{stats['years']['max']}")
        else:
            st.metric("Year Range", "N/A")
    with col4:
        st.metric("Body Regions", stats['regions']['unique_count'])

    st.divider()

    if stats['cases_with_damages'] > 0:
        st.subheader(f"Award Statistics (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})")

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

        st.caption(f"All awards adjusted to {DEFAULT_REFERENCE_YEAR} dollars using Canadian CPI")

        st.divider()

    st.subheader("Awards Over Time")
    st.caption("Hover over points for case details including region and court. The median trend line shows case volume per year.")
    timeline_fig = create_awards_timeline_chart(judge_cases)

    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)
    else:
        st.info("Insufficient data to display timeline.")

    st.divider()

    if stats['courts']['distribution']:
        st.subheader("Court Distribution")
        court_dist = stats['courts']['distribution']
        court_df = pd.DataFrame(
            list(court_dist.items()),
            columns=['Court', 'Cases']
        ).sort_values('Cases', ascending=False)
        st.dataframe(court_df, use_container_width=True, hide_index=True)

    with st.expander(f"View All {len(judge_cases)} Cases"):
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
        st.dataframe(cases_df, use_container_width=True, hide_index=True)
