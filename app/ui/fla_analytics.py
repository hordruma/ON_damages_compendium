"""
Family Law Act (FLA) Damages Analytics

Specialized analytics for Family Law Act claims,
including award distributions and relationships.
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

# MD3 color palette
MD3_COLORS = [
    "#1a73e8", "#e8710a", "#1e8e3e", "#d93025",
    "#9334e6", "#f538a0", "#12b5cb", "#e37400",
]


def get_fla_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter cases that have Family Law Act claims."""
    fla_cases = []
    for case in cases:
        extended_data = case.get('extended_data', {})
        fla_claims = extended_data.get('family_law_act_claims', [])
        if fla_claims:
            fla_cases.append(case)
    return fla_cases


def extract_fla_awards(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract FLA award information from a case."""
    extended_data = case.get('extended_data', {})
    fla_claims = extended_data.get('family_law_act_claims', [])

    awards = []
    for claim in fla_claims:
        amount = claim.get('amount')
        relationship = claim.get('relationship', 'FLA Claim')
        is_fla_award = claim.get('is_fla_award', True)

        if amount and amount > 0 and is_fla_award:
            awards.append({
                'amount': amount,
                'relationship': relationship,
                'description': claim.get('description', ''),
                'category': claim.get('category', 'Family Law Act Claim'),
                'case_name': case.get('case_name', 'Unknown'),
                'year': case.get('year'),
                'court': case.get('court', 'Unknown')
            })

    return awards


def create_fla_distribution_chart(fla_awards: List[float]) -> Optional[go.Figure]:
    """Create a bar chart showing FLA award statistics distribution."""
    if not fla_awards or len(fla_awards) < 2:
        return None

    min_val = np.min(fla_awards)
    q25_val = np.percentile(fla_awards, 25)
    median_val = np.median(fla_awards)
    q75_val = np.percentile(fla_awards, 75)
    max_val = np.max(fla_awards)

    fig = go.Figure()

    bars_data = [
        {'label': 'Minimum', 'value': min_val, 'color': MD3_COLORS[2]},
        {'label': '25th Percentile', 'value': q25_val, 'color': MD3_COLORS[0]},
        {'label': 'Median', 'value': median_val, 'color': MD3_COLORS[4]},
        {'label': '75th Percentile', 'value': q75_val, 'color': MD3_COLORS[1]},
        {'label': 'Maximum', 'value': max_val, 'color': MD3_COLORS[3]},
    ]

    fig.add_trace(go.Bar(
        x=[d['label'] for d in bars_data],
        y=[d['value'] for d in bars_data],
        marker=dict(
            color=[d['color'] for d in bars_data],
            line=dict(color='rgba(255,255,255,0.8)', width=1)
        ),
        text=[f"${d['value']:,.0f}" for d in bars_data],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text='FLA Award Distribution',
            font=dict(size=16),
        ),
        xaxis_title='Statistic',
        yaxis_title='Award Amount',
        yaxis=dict(tickformat='$,.0f'),
        height=450,
        showlegend=False,
        template='plotly_white',
        font=dict(family="Google Sans, Roboto, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig


def _format_relationship_label(rel: str) -> str:
    """Format a relationship enum value for display (e.g., 'grandchild' -> 'Grandchild')."""
    return rel.replace("_", " ").title() if rel else "Unknown"


def create_fla_relationship_chart(fla_awards_data: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """Create a chart showing FLA awards by relationship type."""
    if not fla_awards_data:
        return None

    relationship_counts = Counter([award['relationship'] for award in fla_awards_data])
    if not relationship_counts:
        return None

    sorted_relationships = sorted(relationship_counts.items(), key=lambda x: x[1], reverse=True)
    relationships, counts = zip(*sorted_relationships)
    # Format labels for display
    relationships = [_format_relationship_label(r) for r in relationships]

    fig = go.Figure(data=[
        go.Bar(
            x=list(counts),
            y=list(relationships),
            orientation='h',
            marker=dict(
                color=MD3_COLORS[0],
                line=dict(color='white', width=1)
            ),
            text=[f"{count} claim{'s' if count != 1 else ''}" for count in counts],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title=dict(
            text='FLA Claims by Relationship Type',
            font=dict(size=16),
        ),
        xaxis_title='Number of Claims',
        yaxis_title='Relationship',
        height=max(400, len(relationships) * 30),
        template='plotly_white',
        showlegend=False,
        font=dict(family="Google Sans, Roboto, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig


def create_fla_timeline_chart(fla_awards_data: List[Dict[str, Any]]) -> Optional[go.Figure]:
    """Create a timeline showing FLA awards over time."""
    awards_with_year = [a for a in fla_awards_data if a.get('year')]

    if not awards_with_year:
        return None

    df = pd.DataFrame(awards_with_year)

    yearly_stats = df.groupby('year').agg({
        'amount': ['mean', 'median', 'count']
    }).reset_index()
    yearly_stats.columns = ['year', 'mean', 'median', 'count']

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['year'],
        y=df['amount'],
        mode='markers',
        name='Individual Awards',
        marker=dict(
            size=8,
            color=MD3_COLORS[0],
            opacity=0.6,
            line=dict(width=1, color='white')
        ),
        text=[f"<b>{row['case_name']}</b><br>"
              f"Relationship: {row['relationship']}<br>"
              f"{('Comments: ' + row['description'] + '<br>') if row.get('description') else ''}"
              f"Award: ${row['amount']:,.0f}"
              for _, row in df.iterrows()],
        hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=yearly_stats['year'],
        y=yearly_stats['median'],
        mode='lines+markers',
        name='Yearly Median',
        line=dict(color=MD3_COLORS[3], width=2, dash='dot'),
        marker=dict(size=8, symbol='diamond'),
        text=[f"Median: ${val:,.0f}<br>Claims: {int(count)}"
              for val, count in zip(yearly_stats['median'], yearly_stats['count'])],
        hovertemplate='Year: %{x}<br>%{text}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text='FLA Awards Over Time',
            font=dict(size=16),
        ),
        xaxis_title='Year',
        yaxis_title='Award Amount',
        hovermode='closest',
        showlegend=True,
        height=500,
        template='plotly_white',
        font=dict(family="Google Sans, Roboto, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    fig.update_yaxes(tickformat='$,.0f')

    return fig


def display_fla_analytics_page(cases: List[Dict[str, Any]], include_outliers: bool = True) -> None:
    """Main function to display the FLA analytics page."""

    fla_cases = get_fla_cases(cases)

    if not fla_cases:
        st.warning("No Family Law Act claims found in the dataset.")
        return

    all_fla_awards = []
    fla_award_amounts = []

    for case in fla_cases:
        awards = extract_fla_awards(case)
        all_fla_awards.extend(awards)
        for award in awards:
            fla_award_amounts.append(award['amount'])

    st.subheader("Overview")

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

    if fla_award_amounts:
        st.subheader("FLA Award Distribution")
        dist_fig = create_fla_distribution_chart(fla_award_amounts)
        if dist_fig:
            st.plotly_chart(dist_fig, use_container_width=True)
            st.caption("Distribution of Family Law Act awards across all cases")

        st.divider()

    if all_fla_awards:
        st.subheader("Claims by Relationship")
        rel_fig = create_fla_relationship_chart(all_fla_awards)
        if rel_fig:
            st.plotly_chart(rel_fig, use_container_width=True)

        st.divider()

        st.subheader("FLA Awards Over Time")

        unique_relationships = sorted(set(award['relationship'] for award in all_fla_awards))

        selected_relationships = st.multiselect(
            "Filter by relationship type",
            options=unique_relationships,
            default=unique_relationships,
            format_func=_format_relationship_label,
            help="Select relationship types to display in the timeline."
        )

        filtered_awards = [
            award for award in all_fla_awards
            if award['relationship'] in selected_relationships
        ]

        if filtered_awards:
            timeline_fig = create_fla_timeline_chart(filtered_awards)
            if timeline_fig:
                st.plotly_chart(timeline_fig, use_container_width=True)
            else:
                st.info("Insufficient data with year information to display timeline.")
        else:
            st.info("No awards match the selected relationship filters.")

        st.divider()

    with st.expander(f"View All {len(fla_cases)} Cases with FLA Claims"):
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
