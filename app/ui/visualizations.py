"""
Visualization components for the Ontario Damages Compendium.

This module contains functions for creating charts and visual displays
of damage award data, including inflation-adjusted comparisons.
"""

import plotly.graph_objects as go
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

from inflation_adjuster import adjust_for_inflation, DEFAULT_REFERENCE_YEAR
from app.core.config import CHART_MAX_CASES
from app.core.search import extract_damages_value

# Ontario non-pecuniary damages cap (as of 2024, indexed annually)
ONTARIO_DAMAGES_CAP = 434_000  # CAD, adjusted for inflation to 2024


def create_inflation_chart(
    results: List[Tuple[Dict[str, Any], float, float]],
    reference_year: int = DEFAULT_REFERENCE_YEAR
) -> go.Figure:
    """
    Create an interactive scatter plot of inflation-adjusted awards over time.

    Displays up to CHART_MAX_CASES with:
    - X-axis: Year of award
    - Y-axis: Inflation-adjusted award amount (to reference year)
    - Trend line showing overall pattern
    - Tooltips with original amount, adjusted amount, and delta

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
                delta = adjusted_val - damage_val
                delta_pct = ((adjusted_val - damage_val) / damage_val) * 100
                chart_data.append({
                    'case_name': case_name,
                    'year': year,
                    'original_award': damage_val,
                    'adjusted_award': adjusted_val,
                    'delta': delta,
                    'delta_pct': delta_pct,
                    'citation': citation,
                    'match_score': combined_score * 100
                })

    if not chart_data:
        return None

    # Sort by year for better visualization
    chart_data.sort(key=lambda x: x['year'])

    # Create interactive Plotly scatter chart
    fig = go.Figure()

    # Add scatter plot for cases
    fig.add_trace(go.Scatter(
        name=f'Awards ({reference_year}$)',
        x=[d['year'] for d in chart_data],
        y=[d['adjusted_award'] for d in chart_data],
        mode='markers',
        marker=dict(
            size=10,
            color='darkblue',
            line=dict(color='white', width=1)
        ),
        customdata=[[
            d['case_name'],
            d['citation'],
            d['match_score'],
            d['year'],
            d['original_award'],
            d['adjusted_award'],
            d['delta'],
            d['delta_pct']
        ] for d in chart_data],
        hovertemplate='<b>%{customdata[0]}</b><br>' +
                      'Year: %{customdata[3]}<br>' +
                      'Original Award: $%{customdata[4]:,.0f}<br>' +
                      f'Adjusted ({reference_year}$): $%{{customdata[5]:,.0f}}<br>' +
                      'Delta: $%{customdata[6]:,.0f} (+%{customdata[7]:.1f}%)<br>' +
                      'Match Score: %{customdata[2]:.1f}%<br>' +
                      'Citation: %{customdata[1]}<br>' +
                      '<extra></extra>'
    ))

    # Calculate and add trend line using linear regression
    years = np.array([d['year'] for d in chart_data])
    awards = np.array([d['adjusted_award'] for d in chart_data])

    # Linear regression: y = mx + b
    coefficients = np.polyfit(years, awards, 1)
    trend_line = np.poly1d(coefficients)

    # Generate trend line points
    year_range = np.linspace(years.min(), years.max(), 100)
    trend_values = trend_line(year_range)

    fig.add_trace(go.Scatter(
        name='Trend Line',
        x=year_range,
        y=trend_values,
        mode='lines',
        line=dict(color='rgba(255, 0, 0, 0.5)', width=2, dash='dash'),
        hovertemplate='Trend: $%{y:,.0f}<br>Year: %{x:.0f}<extra></extra>'
    ))

    # Update layout for professional appearance with dark mode support
    fig.update_layout(
        title=f'Damage Awards Over Time (Inflation-Adjusted to {reference_year}$)',
        xaxis_title='Year of Award',
        yaxis_title=f'Award Amount ({reference_year}$)',
        yaxis=dict(tickformat='$,.0f'),
        xaxis=dict(
            tickmode='linear',
            dtick=5,  # Show tick every 5 years
            gridcolor='rgba(128, 128, 128, 0.2)'
        ),
        hovermode='closest',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0, 0, 0, 0)',  # Transparent background for dark mode compatibility
        paper_bgcolor='rgba(0, 0, 0, 0)',  # Transparent paper background
        showlegend=True
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


def create_damages_cap_chart(
    damages_values: List[float],
    reference_year: int = DEFAULT_REFERENCE_YEAR,
    damages_cap: float = ONTARIO_DAMAGES_CAP
) -> Optional[go.Figure]:
    """
    Create a bar chart showing min, median, and max awards colored proportionally
    to the Ontario damages cap.

    Args:
        damages_values: List of damage award amounts
        reference_year: Year for inflation adjustment
        damages_cap: Ontario non-pecuniary damages cap

    Returns:
        Plotly figure or None if insufficient data
    """
    if not damages_values or len(damages_values) < 2:
        return None

    min_val = np.min(damages_values)
    median_val = np.median(damages_values)
    max_val = np.max(damages_values)

    # Calculate proportions relative to cap
    min_pct = (min_val / damages_cap) * 100
    median_pct = (median_val / damages_cap) * 100
    max_pct = (max_val / damages_cap) * 100

    # Color based on proportion to cap
    def get_color(pct):
        """Get color based on percentage of cap"""
        if pct < 25:
            return 'rgba(34, 197, 94, 0.7)'  # Green - low
        elif pct < 50:
            return 'rgba(59, 130, 246, 0.7)'  # Blue - moderate
        elif pct < 75:
            return 'rgba(251, 146, 60, 0.7)'  # Orange - high
        else:
            return 'rgba(239, 68, 68, 0.7)'  # Red - very high

    fig = go.Figure()

    # Add bars for min, median, max
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

    # Add horizontal line for damages cap
    fig.add_hline(
        y=damages_cap,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"Ontario Cap: ${damages_cap:,.0f}",
        annotation_position="right"
    )

    fig.update_layout(
        title=f'Award Statistics Relative to Ontario Damages Cap ({reference_year})',
        xaxis_title='Statistic',
        yaxis_title=f'Award Amount ({reference_year}$)',
        yaxis=dict(tickformat='$,.0f'),
        height=400,
        showlegend=False,
        plot_bgcolor='rgba(0, 0, 0, 0)',
        paper_bgcolor='rgba(0, 0, 0, 0)',
    )

    return fig
