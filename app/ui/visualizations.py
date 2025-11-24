"""
Visualization components for the Ontario Damages Compendium.

This module contains functions for creating charts and visual displays
of damage award data, including inflation-adjusted comparisons.
"""

import plotly.graph_objects as go
import numpy as np
from typing import List, Tuple, Dict, Any

from inflation_adjuster import adjust_for_inflation, DEFAULT_REFERENCE_YEAR
from app.core.config import CHART_MAX_CASES
from app.core.search import extract_damages_value


def create_inflation_chart(
    results: List[Tuple[Dict[str, Any], float, float]],
    reference_year: int = DEFAULT_REFERENCE_YEAR
) -> go.Figure:
    """
    Create an interactive Plotly chart comparing original vs inflation-adjusted awards.

    Displays up to CHART_MAX_CASES with:
    - Original award amounts
    - Inflation-adjusted amounts to reference year
    - Match scores and case details in hover text

    Args:
        results: List of (case, embedding_sim, combined_score) tuples
        reference_year: Year to adjust awards to (default: 2024)

    Returns:
        Plotly Figure object ready to display with st.plotly_chart()
    """
    chart_data = []

    # Prepare data for top cases
    for case, emb_sim, combined_score in results[:CHART_MAX_CASES]:
        damage_val = extract_damages_value(case)
        year = case.get('year')
        case_name = case.get('case_name', 'Unknown')
        citation = case.get('citation', case.get('summary_text', '')[:50])

        if damage_val and year:
            adjusted_val = adjust_for_inflation(damage_val, year, reference_year)
            if adjusted_val:
                chart_data.append({
                    'case_name': case_name,
                    'year': year,
                    'original_award': damage_val,
                    'adjusted_award': adjusted_val,
                    'citation': citation,
                    'match_score': combined_score * 100
                })

    if not chart_data:
        return None

    # Create interactive Plotly chart
    fig = go.Figure()

    # Add original awards as bars
    fig.add_trace(go.Bar(
        name='Original Award',
        x=[f"{d['case_name'][:20]}... ({d['year']})" for d in chart_data],
        y=[d['original_award'] for d in chart_data],
        marker_color='lightblue',
        hovertemplate='<b>%{x}</b><br>' +
                      'Original Award: $%{y:,.0f}<br>' +
                      '<extra></extra>'
    ))

    # Add inflation-adjusted awards as bars
    fig.add_trace(go.Bar(
        name=f'Inflation-Adjusted ({reference_year}$)',
        x=[f"{d['case_name'][:20]}... ({d['year']})" for d in chart_data],
        y=[d['adjusted_award'] for d in chart_data],
        marker_color='darkblue',
        customdata=[[
            d['case_name'],
            d['citation'],
            d['match_score'],
            d['year'],
            d['original_award'],
            d['adjusted_award']
        ] for d in chart_data],
        hovertemplate='<b>%{customdata[0]}</b><br>' +
                      'Year: %{customdata[3]}<br>' +
                      'Original: $%{customdata[4]:,.0f}<br>' +
                      f'Adjusted ({reference_year}$): $%{{customdata[5]:,.0f}}<br>' +
                      'Match Score: %{customdata[2]:.1f}%<br>' +
                      'Citation: %{customdata[1]}<br>' +
                      '<extra></extra>'
    ))

    # Update layout for professional appearance
    fig.update_layout(
        barmode='group',
        title=f'Damage Awards: Original vs Inflation-Adjusted to {reference_year}',
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

    return fig


def calculate_chart_statistics(chart_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate summary statistics for chart data.

    Args:
        chart_data: List of dictionaries containing award data

    Returns:
        Dictionary with median_original, median_adjusted, avg_inflation_impact
    """
    if not chart_data:
        return {}

    median_original = np.median([d['original_award'] for d in chart_data])
    median_adjusted = np.median([d['adjusted_award'] for d in chart_data])

    avg_inflation = np.mean([
        ((d['adjusted_award'] - d['original_award']) / d['original_award']) * 100
        for d in chart_data
    ])

    return {
        'median_original': median_original,
        'median_adjusted': median_adjusted,
        'avg_inflation_impact': avg_inflation
    }
