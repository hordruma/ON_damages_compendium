"""
Family Law Act (FLA) Damages Analytics

This module provides specialized analytics for Family Law Act claims,
including award distributions, relationships, and comparisons to the FLA damages cap.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from collections import Counter

# Import inflation adjustment
try:
    from inflation_adjuster import adjust_for_inflation, DEFAULT_REFERENCE_YEAR
except ImportError:
    DEFAULT_REFERENCE_YEAR = 2024
    def adjust_for_inflation(amount, from_year, to_year):
        return None

# Ontario FLA damages cap (indexed annually)
FLA_DAMAGES_CAP = 100_000  # CAD, for loss of guidance, care and companionship


def get_fla_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter cases that have Family Law Act claims.

    Args:
        cases: List of all cases

    Returns:
        List of cases with FLA claims
    """
    fla_cases = []
    for case in cases:
        extended_data = case.get('extended_data', {})
        fla_claims = extended_data.get('family_law_act_claims', [])
        if fla_claims:
            fla_cases.append(case)

    return fla_cases


def extract_fla_awards(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract FLA award information from a case.

    Args:
        case: Case dictionary

    Returns:
        List of FLA award dictionaries
    """
    extended_data = case.get('extended_data', {})
    fla_claims = extended_data.get('family_law_act_claims', [])

    awards = []
    for claim in fla_claims:
        amount = claim.get('amount')
        if amount and amount > 0:
            awards.append({
                'amount': amount,
                'description': claim.get('description', 'FLA Claim'),
                'category': claim.get('category', 'Family Law Act Claim'),
                'case_name': case.get('case_name', 'Unknown'),
                'year': case.get('year'),
                'court': case.get('court', 'Unknown')
            })

    return awards


def create_fla_cap_chart(
    fla_awards: List[float],
    reference_year: int = DEFAULT_REFERENCE_YEAR,
    fla_cap: float = FLA_DAMAGES_CAP
) -> Optional[go.Figure]:
    """
    Create a bar chart showing FLA award statistics relative to the FLA cap.

    Args:
        fla_awards: List of FLA award amounts
        reference_year: Year for inflation adjustment
        fla_cap: FLA damages cap

    Returns:
        Plotly figure or None if insufficient data
    """
    if not fla_awards or len(fla_awards) < 2:
        return None

    min_val = np.min(fla_awards)
    median_val = np.median(fla_awards)
    max_val = np.max(fla_awards)

    # Calculate proportions relative to cap
    min_pct = (min_val / fla_cap) * 100
    median_pct = (median_val / fla_cap) * 100
    max_pct = (max_val / fla_cap) * 100

    # Color based on proportion to cap
    def get_color(pct):
        if pct < 25:
            return 'rgba(34, 197, 94, 0.7)'  # Green - low
        elif pct < 50:
            return 'rgba(59, 130, 246, 0.7)'  # Blue - moderate
        elif pct < 75:
            return 'rgba(251, 146, 60, 0.7)'  # Orange - high
        else:
            return 'rgba(239, 68, 68, 0.7)'  # Red - very high

    fig = go.Figure()

    bars_data = [
        {'label': 'Minimum', 'value': min_val, 'pct': min_pct, 'color': get_color(min_pct)},
        {'label': 'Median', 'value': median_val, 'pct': median_pct, 'color': get_color(median_pct)},
        {'label': 'Maximum', 'value': max_val, 'pct': max_pct, 'color': get_color(max_pct)},
    ]

    fig.add_trace(go.Bar(
        x=[d['label'] for d in bars_data],
        y=[d['value'] for d in bars_data],
        marker=dict(
            color=[d['color'] for d in bars_data],
            line=dict(color='rgba(0,0,0,0.3)', width=2)
        ),
        text=[f"${d['value']:,.0f}<br>({d['pct']:.1f}% of cap)" for d in bars_data],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.0f}<br>Percent of Cap: %{customdata:.1f}%<extra></extra>',
        customdata=[d['pct'] for d in bars_data]
    ))

    # Add horizontal line for FLA cap
    fig.add_hline(
        y=fla_cap,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"FLA Cap: ${fla_cap:,.0f}",
        annotation_position="right"
    )

    fig.update_layout(
        title=f'FLA Awards Relative to Ontario FLA Damages Cap ({reference_year})',
        xaxis_title='Statistic',
        yaxis_title=f'Award Amount ({reference_year}$)',
        yaxis=dict(tickformat='$,.0f'),
        height=400,
        showlegend=False,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
    )

    return fig


def create_fla_relationship_chart(fla_awards_data: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """
    Create a chart showing FLA awards by relationship type.

    Args:
        fla_awards_data: List of FLA award dictionaries

    Returns:
        Plotly figure or None if insufficient data
    """
    if not fla_awards_data:
        return None

    # Group by relationship description
    relationship_counts = Counter([award['description'] for award in fla_awards_data])

    if not relationship_counts:
        return None

    # Sort by count
    sorted_relationships = sorted(relationship_counts.items(), key=lambda x: x[1], reverse=True)
    relationships, counts = zip(*sorted_relationships)

    fig = go.Figure(data=[
        go.Bar(
            x=list(counts),
            y=list(relationships),
            orientation='h',
            marker=dict(
                color=list(counts),
                colorscale='Teal',
                showscale=False
            ),
            text=[f"{count} claim{'s' if count != 1 else ''}" for count in counts],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title='FLA Claims by Relationship Type',
        xaxis_title='Number of Claims',
        yaxis_title='Relationship',
        height=max(400, len(relationships) * 25),
        template='plotly_white',
        showlegend=False,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
    )

    return fig


def create_fla_timeline_chart(fla_awards_data: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """
    Create a timeline showing FLA awards over time.

    Args:
        fla_awards_data: List of FLA award dictionaries

    Returns:
        Plotly figure or None if insufficient data
    """
    # Filter to awards with year data
    awards_with_year = [a for a in fla_awards_data if a.get('year')]

    if not awards_with_year:
        return None

    df = pd.DataFrame(awards_with_year)

    # Calculate yearly statistics
    yearly_stats = df.groupby('year').agg({
        'amount': ['mean', 'median', 'count']
    }).reset_index()
    yearly_stats.columns = ['year', 'mean', 'median', 'count']

    fig = go.Figure()

    # Individual awards
    fig.add_trace(go.Scatter(
        x=df['year'],
        y=df['amount'],
        mode='markers',
        name='Individual Awards',
        marker=dict(
            size=8,
            color='rgba(59, 130, 246, 0.6)',
            line=dict(width=1, color='white')
        ),
        text=[f"<b>{row['case_name']}</b><br>{row['description']}<br>${row['amount']:,.0f}"
              for _, row in df.iterrows()],
        hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
    ))

    # Median trend line
    fig.add_trace(go.Scatter(
        x=yearly_stats['year'],
        y=yearly_stats['median'],
        mode='lines+markers',
        name='Yearly Median',
        line=dict(color='red', width=3),
        marker=dict(size=10, symbol='diamond'),
        text=[f"Median: ${val:,.0f}<br>Claims: {int(count)}"
              for val, count in zip(yearly_stats['median'], yearly_stats['count'])],
        hovertemplate='Year: %{x}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title=f'FLA Awards Over Time',
        xaxis_title='Year',
        yaxis_title='Award Amount',
        hovermode='closest',
        showlegend=True,
        height=500,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
    )

    fig.update_yaxes(tickformat='$,.0f')

    return fig


def display_fla_analytics_page(cases: List[Dict[str, Any]]) -> None:
    """
    Main function to display the FLA analytics page.

    Args:
        cases: List of all cases
    """
    st.header("👨‍👩‍👧‍👦 Family Law Act (FLA) Damages")
    st.markdown("Explore Family Law Act claims for loss of guidance, care, and companionship")

    # Get FLA cases
    fla_cases = get_fla_cases(cases)

    if not fla_cases:
        st.warning("⚠️ No Family Law Act claims found in the dataset.")
        return

    # Extract all FLA awards
    all_fla_awards = []
    fla_award_amounts = []

    for case in fla_cases:
        awards = extract_fla_awards(case)
        all_fla_awards.extend(awards)
        for award in awards:
            fla_award_amounts.append(award['amount'])

    # Display overview metrics
    st.subheader("📊 Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Cases with FLA Claims", len(fla_cases))

    with col2:
        st.metric("Total FLA Claims", len(all_fla_awards))

    with col3:
        if fla_award_amounts:
            st.metric("Median Award", f"${np.median(fla_award_amounts):,.0f}")
        else:
            st.metric("Median Award", "N/A")

    with col4:
        st.metric("FLA Cap", f"${FLA_DAMAGES_CAP:,.0f}")

    st.divider()

    # FLA Cap Comparison Chart
    if fla_award_amounts:
        st.subheader("💰 Awards Relative to FLA Damages Cap")
        cap_fig = create_fla_cap_chart(fla_award_amounts, DEFAULT_REFERENCE_YEAR, FLA_DAMAGES_CAP)
        if cap_fig:
            st.plotly_chart(cap_fig, use_container_width=True)
            st.caption("💡 Ontario FLA cap for loss of guidance, care, and companionship is indexed annually")

        st.divider()

    # Relationship distribution
    if all_fla_awards:
        st.subheader("👨‍👩‍👧 Claims by Relationship Type")
        rel_fig = create_fla_relationship_chart(all_fla_awards)
        if rel_fig:
            st.plotly_chart(rel_fig, use_container_width=True)

        st.divider()

    # Timeline
    if all_fla_awards:
        st.subheader("📈 FLA Awards Over Time")
        timeline_fig = create_fla_timeline_chart(all_fla_awards)
        if timeline_fig:
            st.plotly_chart(timeline_fig, use_container_width=True)
        else:
            st.info("Insufficient data with year information to display timeline")

        st.divider()

    # Detailed case list
    with st.expander(f"📋 View All {len(fla_cases)} Cases with FLA Claims"):
        case_list = []
        for case in fla_cases:
            fla_claims_summary = []
            extended_data = case.get('extended_data', {})
            fla_claims = extended_data.get('family_law_act_claims', [])

            for claim in fla_claims:
                amount = claim.get('amount', 0)
                desc = claim.get('description', 'FLA Claim')
                if amount:
                    fla_claims_summary.append(f"{desc}: ${amount:,.0f}")
                else:
                    fla_claims_summary.append(desc)

            case_list.append({
                'Case Name': case.get('case_name', 'Unknown'),
                'Year': case.get('year', 'N/A'),
                'Court': case.get('court', 'N/A'),
                'FLA Claims': '; '.join(fla_claims_summary) if fla_claims_summary else 'N/A'
            })

        cases_df = pd.DataFrame(case_list)
        st.dataframe(cases_df, use_container_width=True, hide_index=True)
