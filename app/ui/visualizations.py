"""
Visualization components for the Ontario Damages Compendium.

Charts and visual displays of damage award data,
including inflation-adjusted comparisons.
"""

import plotly.graph_objects as go
import numpy as np
from typing import List, Tuple, Dict, Any, Optional

from inflation_adjuster import adjust_for_inflation, DEFAULT_REFERENCE_YEAR
from app.core.config import CHART_MAX_CASES
from app.core.search import extract_damages_value

# Ontario non-pecuniary damages cap (as of 2024, indexed annually)
ONTARIO_DAMAGES_CAP = 434_000

# MD3 color palette
MD3_COLORS = [
    "#1a73e8", "#e8710a", "#1e8e3e", "#d93025",
    "#9334e6", "#f538a0", "#12b5cb", "#e37400",
]


def create_inflation_chart(
    results: List[Tuple[Dict[str, Any], float, float]],
    reference_year: int = DEFAULT_REFERENCE_YEAR
) -> go.Figure:
    """
    Create an interactive scatter plot of inflation-adjusted awards over time.

    Args:
        results: List of (case, embedding_sim, combined_score) tuples
        reference_year: Year to adjust awards to (default: 2024)

    Returns:
        Plotly Figure object ready to display with st.plotly_chart()
    """
    chart_data = []

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

    chart_data.sort(key=lambda x: x['year'])

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        name=f'Awards ({reference_year}$)',
        x=[d['year'] for d in chart_data],
        y=[d['adjusted_award'] for d in chart_data],
        mode='markers',
        marker=dict(
            size=10,
            color=MD3_COLORS[0],
            line=dict(color='white', width=1),
            opacity=0.8
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

    # Trend line
    years = np.array([d['year'] for d in chart_data])
    awards = np.array([d['adjusted_award'] for d in chart_data])
    coefficients = np.polyfit(years, awards, 1)
    trend_line = np.poly1d(coefficients)
    year_range = np.linspace(years.min(), years.max(), 100)
    trend_values = trend_line(year_range)

    fig.add_trace(go.Scatter(
        name='Trend Line',
        x=year_range,
        y=trend_values,
        mode='lines',
        line=dict(color=MD3_COLORS[3], width=2, dash='dash'),
        hovertemplate='Trend: $%{y:,.0f}<br>Year: %{x:.0f}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text=f'Non-Pecuniary Awards Over Time ({reference_year}$)',
            font=dict(size=16),
        ),
        xaxis_title='Year of Award',
        yaxis_title=f'Non-Pecuniary Award Amount ({reference_year}$)',
        yaxis=dict(tickformat='$,.0f'),
        xaxis=dict(
            tickmode='linear',
            dtick=5,
            gridcolor='rgba(128, 128, 128, 0.15)'
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
        template='plotly_white',
        font=dict(family="Google Sans, Roboto, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=True
    )

    return fig


def calculate_chart_statistics(chart_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate summary statistics for chart data."""
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
    Create a bar chart showing min, median, and max awards relative to the Ontario damages cap.

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

    min_pct = (min_val / damages_cap) * 100
    median_pct = (median_val / damages_cap) * 100
    max_pct = (max_val / damages_cap) * 100

    def get_color(pct):
        if pct < 25:
            return MD3_COLORS[2]  # Green
        elif pct < 50:
            return MD3_COLORS[0]  # Blue
        elif pct < 75:
            return MD3_COLORS[1]  # Orange
        else:
            return MD3_COLORS[3]  # Red

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
            line=dict(color='white', width=1)
        ),
        text=[f"${d['value']:,.0f}<br>({d['pct']:.1f}% of cap)" for d in bars_data],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Amount: $%{y:,.0f}<br>Percent of Cap: %{customdata:.1f}%<extra></extra>',
        customdata=[d['pct'] for d in bars_data]
    ))

    fig.add_hline(
        y=damages_cap,
        line_dash="dash",
        line_color=MD3_COLORS[3],
        line_width=2,
        annotation_text=f"Ontario Cap: ${damages_cap:,.0f}",
        annotation_position="right"
    )

    fig.update_layout(
        title=dict(
            text=f'Award Statistics Relative to Ontario Damages Cap ({reference_year})',
            font=dict(size=16),
        ),
        xaxis_title='Statistic',
        yaxis_title=f'Non-Pecuniary Award Amount ({reference_year}$)',
        yaxis=dict(tickformat='$,.0f'),
        height=400,
        showlegend=False,
        template='plotly_white',
        font=dict(family="Google Sans, Roboto, sans-serif"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig
