"""
Family Law Act (FLA) Damages Analytics

This module provides specialized analytics for Family Law Act claims,
including award distributions and relationships.
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
    DEFAULT_REFERENCE_YEAR = 2024
    def adjust_for_inflation(amount, from_year, to_year):
        return None


def normalize_fla_relationship(description: str) -> Optional[str]:
    """
    Normalize FLA relationship descriptions and exclude non-relationship damages.

    Extracts relationship type from description and normalizes to singular forms:
    - Wife/Husband/Spouse → Spouse
    - Sister/Sisters/2 Sisters/Brother/Brothers → Sibling
    - Son/Daughter/Children → Child
    - Mother/Father/Mom/Dad → Parent

    Args:
        description: Raw FLA claim description

    Returns:
        Normalized relationship name or None if not a relationship claim
    """
    if not description:
        return None

    # Fix encoding errors (Euro sign and other mojibake)
    desc = description.replace('€', '').replace('â', '').strip()

    # Exclude general/punitive damages
    exclude_patterns = [
        r'\bgeneral\s+damages\b',
        r'\bpunitive\s+damages\b',
        r'\baggravated\s+damages\b',
        r'\bspecial\s+damages\b',
        r'\bcosts\b'
    ]

    for pattern in exclude_patterns:
        if re.search(pattern, desc, re.IGNORECASE):
            return None

    # Extract relationships using regex - normalized to singular forms
    # Order matters: check specific patterns before general ones
    relationship_patterns = {
        'Spouse': r'\b(spouse|wife|husband|partner)\b',
        'Child': r'\b(\d+\s+)?(child|son|daughter|children)\b',  # handles "2 children", "child", etc.
        'Parent': r'\b(parent|mother|father|mom|dad)\b',
        'Sibling': r'\b(\d+\s+)?(sibling|brother|sister)(s)?\b',  # handles "2 sisters", "sister", "sisters", etc.
        'Grandparent': r'\b(grandparent|grandfather|grandmother|grandpa|grandma)\b',
        'Grandchild': r'\b(grandchild|grandson|granddaughter)\b',
        'Other Family': r'\b(family|relative|kin)\b'
    }

    desc_lower = desc.lower()

    for relationship, pattern in relationship_patterns.items():
        if re.search(pattern, desc_lower):
            return relationship

    # If no pattern matches but description exists and isn't excluded, return cleaned desc
    # (up to first 50 chars, cleaned)
    if len(desc) > 0:
        cleaned = re.sub(r'\s+', ' ', desc).strip()
        return cleaned[:50] if len(cleaned) <= 50 else cleaned[:47] + "..."

    return None


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
    Extract FLA award information from a case with normalized relationships.

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
        description = claim.get('description', 'FLA Claim')

        # Normalize the relationship and filter out non-relationship damages
        normalized_relationship = normalize_fla_relationship(description)

        # Only include claims with valid relationships (excludes general/punitive damages)
        if amount and amount > 0 and normalized_relationship:
            awards.append({
                'amount': amount,
                'description': normalized_relationship,  # Use normalized relationship
                'original_description': description,  # Keep original for reference
                'category': claim.get('category', 'Family Law Act Claim'),
                'case_name': case.get('case_name', 'Unknown'),
                'year': case.get('year'),
                'court': case.get('court', 'Unknown')
            })

    return awards


def create_fla_distribution_chart(fla_awards: List[float]) -> Optional[go.Figure]:
    """
    Create a bar chart showing FLA award statistics distribution.

    Args:
        fla_awards: List of FLA award amounts

    Returns:
        Plotly figure or None if insufficient data
    """
    if not fla_awards or len(fla_awards) < 2:
        return None

    min_val = np.min(fla_awards)
    q25_val = np.percentile(fla_awards, 25)
    median_val = np.median(fla_awards)
    q75_val = np.percentile(fla_awards, 75)
    max_val = np.max(fla_awards)

    fig = go.Figure()

    bars_data = [
        {'label': 'Minimum', 'value': min_val, 'color': 'rgba(34, 197, 94, 0.8)'},
        {'label': '25th Percentile', 'value': q25_val, 'color': 'rgba(59, 130, 246, 0.8)'},
        {'label': 'Median', 'value': median_val, 'color': 'rgba(99, 102, 241, 0.8)'},
        {'label': '75th Percentile', 'value': q75_val, 'color': 'rgba(251, 146, 60, 0.8)'},
        {'label': 'Maximum', 'value': max_val, 'color': 'rgba(239, 68, 68, 0.8)'},
    ]

    fig.add_trace(go.Bar(
        x=[d['label'] for d in bars_data],
        y=[d['value'] for d in bars_data],
        marker=dict(
            color=[d['color'] for d in bars_data],
            line=dict(color='rgba(0,0,0,0.4)', width=2)
        ),
        text=[f"${d['value']:,.0f}" for d in bars_data],
        textposition='outside',
        textfont=dict(size=14, color='#1f2937'),
        hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title='FLA Award Distribution',
        xaxis_title='Statistic',
        yaxis_title='Award Amount',
        yaxis=dict(tickformat='$,.0f'),
        height=450,
        showlegend=False,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
        font=dict(size=13, color='#374151')
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
    Main function to display the FLA analytics page for fatal injury cases.

    Args:
        cases: List of all cases
    """
    st.header("⚰️ Fatal Injuries - Family Law Act Claims by Relationship")
    st.markdown("Analysis of Family Law Act claims in fatal injury cases, organized by relationship to the deceased")

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

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Cases with FLA Claims", len(fla_cases))

    with col2:
        st.metric("Total FLA Claims", len(all_fla_awards))

    with col3:
        if fla_award_amounts:
            st.metric("Median Award", f"${np.median(fla_award_amounts):,.0f}")
        else:
            st.metric("Median Award", "N/A")

    st.divider()

    # FLA Distribution Chart
    if fla_award_amounts:
        st.subheader("💰 FLA Award Distribution")
        dist_fig = create_fla_distribution_chart(fla_award_amounts)
        if dist_fig:
            st.plotly_chart(dist_fig, use_container_width=True)
            st.caption("💡 Distribution of Family Law Act awards across all cases")

        st.divider()

    # Timeline with relationship filter
    if all_fla_awards:
        st.subheader("📈 FLA Awards Over Time")

        # Extract unique relationships for filter
        unique_relationships = sorted(set(award['description'] for award in all_fla_awards))

        # Relationship filter
        selected_relationships = st.multiselect(
            "Filter by Relationship Type:",
            options=unique_relationships,
            default=unique_relationships,
            help="Select one or more relationship types to display in the timeline (e.g., select 'Spouse' to see all cases involving a spouse)"
        )

        # Filter awards based on selected relationships
        filtered_awards = [
            award for award in all_fla_awards
            if award['description'] in selected_relationships
        ]

        if filtered_awards:
            timeline_fig = create_fla_timeline_chart(filtered_awards)
            if timeline_fig:
                st.plotly_chart(timeline_fig, use_container_width=True)
            else:
                st.info("Insufficient data with year information to display timeline")
        else:
            st.info("No awards match the selected relationship filters")

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
