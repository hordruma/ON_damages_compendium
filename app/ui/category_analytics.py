"""
Category-specific analytics and visualizations.

Provides analytics tools for examining awards by injury category/body region,
including comparative statistics, temporal trends, and case distributions.
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


def _load_valid_compendium_categories() -> set:
    """Load valid categories from compendium_regions.json."""
    import json
    from pathlib import Path

    valid_categories = set()

    try:
        compendium_path = Path("compendium_regions.json")
        with open(compendium_path, 'r') as f:
            compendium_data = json.load(f)

        injury_categories = compendium_data.get('injury_categories', {})
        for category_id, category_info in injury_categories.items():
            subcategories = category_info.get('subcategories', [])
            for subcat in subcategories:
                valid_categories.add(subcat.strip().upper())

    except Exception:
        pass

    return valid_categories


def get_all_categories(cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Extract all unique categories/regions from cases."""
    valid_categories = _load_valid_compendium_categories()

    injury_categories = set()
    fla_relationships = set()

    for case in cases:
        region = case.get('region')
        if region and region.strip():
            region_upper = region.strip().upper()
            if not valid_categories or region_upper in valid_categories:
                injury_categories.add(region_upper)

        extended_data = case.get('extended_data', {})
        regions = extended_data.get('regions', [])
        if regions:
            for r in regions:
                if r and r.strip():
                    r_upper = r.strip().upper()
                    if not valid_categories or r_upper in valid_categories:
                        injury_categories.add(r_upper)

        fla_claims = extended_data.get('family_law_act_claims', []) or []
        for claim in fla_claims:
            relationship = claim.get('relationship', '').strip()
            is_fla_award = claim.get('is_fla_award', True)
            if relationship and is_fla_award:
                fla_relationships.add(f"FLA: {relationship}")

    return {
        'injury_categories': sorted(list(injury_categories)),
        'fla_relationships': sorted(list(fla_relationships))
    }


def get_category_cases(cases: List[Dict[str, Any]], category_name: str) -> List[Dict[str, Any]]:
    """Filter cases belonging to a specific category."""
    category_cases = []
    is_fla_category = category_name.startswith("FLA: ")

    if is_fla_category:
        relationship_name = category_name[5:].strip().lower()
        for case in cases:
            extended_data = case.get('extended_data', {})
            fla_claims = extended_data.get('family_law_act_claims', []) or []
            for claim in fla_claims:
                if claim.get('relationship', '').strip().lower() == relationship_name:
                    is_fla_award = claim.get('is_fla_award', True)
                    if is_fla_award:
                        category_cases.append(case)
                        break
    else:
        category_name_upper = category_name.upper()
        for case in cases:
            region = case.get('region', '')
            extended_data = case.get('extended_data', {})
            regions = extended_data.get('regions', [])
            region_upper = region.upper() if region else ''
            regions_upper = [r.upper() if isinstance(r, str) else r for r in regions]
            if region_upper == category_name_upper or category_name_upper in regions_upper:
                category_cases.append(case)

    return category_cases


def calculate_category_statistics(category_cases: List[Dict[str, Any]], category_name: str = "") -> Dict[str, Any]:
    """Calculate comprehensive statistics for a category's cases."""
    total_cases = len(category_cases)
    is_fla_category = category_name.startswith("FLA: ")

    damages_values = []
    adjusted_damages_values = []

    if is_fla_category:
        relationship_name = category_name[5:].strip().lower()
        for case in category_cases:
            year = case.get('year')
            extended_data = case.get('extended_data', {})
            fla_claims = extended_data.get('family_law_act_claims', []) or []
            for claim in fla_claims:
                if claim.get('relationship', '').strip().lower() == relationship_name:
                    damage = claim.get('amount')
                    is_fla_award = claim.get('is_fla_award', True)
                    if damage and damage > 0 and is_fla_award:
                        damages_values.append(damage)
                        if year:
                            adjusted = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                            adjusted_damages_values.append(adjusted if adjusted else damage)
                        else:
                            adjusted_damages_values.append(damage)
                    break
    else:
        for case in category_cases:
            damage = case.get('damages')
            year = case.get('year')
            if damage and damage > 0:
                damages_values.append(damage)
                if year:
                    adjusted = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                    adjusted_damages_values.append(adjusted if adjusted else damage)
                else:
                    adjusted_damages_values.append(damage)

    years = [case.get('year') for case in category_cases if case.get('year')]

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
        }
    }

    return stats


def create_category_timeline_chart(category_cases: List[Dict[str, Any]], category_name: str) -> Optional[go.Figure]:
    """Create a timeline chart showing award amounts over years."""
    data_points = []
    for case in category_cases:
        year = case.get('year')
        damage = case.get('damages')
        case_name = case.get('case_name', 'Unknown')

        if year and damage and damage > 0:
            adjusted_damage = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
            data_points.append({
                'year': year,
                'damages': damage,
                'adjusted_damages': adjusted_damage if adjusted_damage else damage,
                'case_name': case_name
            })

    if not data_points:
        return None

    df = pd.DataFrame(data_points)

    fig = go.Figure()

    hover_text = []
    for _, row in df.iterrows():
        inflation_pct = ((row['adjusted_damages'] / row['damages']) - 1) * 100 if row['damages'] > 0 else 0
        text = (f"<b>{row['case_name']}</b><br>"
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
            color=MD3_COLORS[0],
            line=dict(width=1, color='white'),
            opacity=0.7
        ),
        text=hover_text,
        hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
    ))

    fig.update_layout(
        title=dict(
            text=f'{category_name} — Award Amounts Over Time ({DEFAULT_REFERENCE_YEAR}$)',
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

    fig.update_yaxes(tickformat='$,.0f')

    return fig


def display_category_analytics_page(cases: List[Dict[str, Any]], include_outliers: bool = True) -> None:
    """Main function to display the category analytics page."""

    def get_filtered_category_cases(category_name: str) -> List[Dict[str, Any]]:
        category_cases = get_category_cases(cases, category_name)
        if not include_outliers and category_cases:
            category_cases = filter_outliers(category_cases)
        return category_cases

    categories_dict = get_all_categories(cases)
    injury_categories = categories_dict['injury_categories']
    fla_relationships = categories_dict['fla_relationships']
    all_categories = injury_categories + fla_relationships

    if not all_categories:
        st.warning("No category information found in the dataset.")
        return

    st.caption(f"{len(injury_categories)} injury categories and {len(fla_relationships)} FLA relationship types")

    selected_categories = st.multiselect(
        "Select categories to analyze",
        options=all_categories,
        default=[],
        max_selections=8,
        help="Select up to 8 categories to compare (injury categories or FLA relationship types).",
        key="category_selector"
    )

    if not selected_categories:
        st.info("Select one or more categories above to view their analytics.")
        return

    if len(selected_categories) > 8:
        st.warning("Please reduce your selection to 8 or fewer categories for legible charts.")
        return

    is_comparison = len(selected_categories) > 1

    if is_comparison:
        st.subheader(f"Comparing {len(selected_categories)} Categories")

        comparison_data = []
        for category_name in selected_categories:
            category_cases = get_filtered_category_cases(category_name)
            if category_cases:
                stats = calculate_category_statistics(category_cases, category_name)
                comparison_data.append({
                    'Category': category_name,
                    'Sample Size': stats['total_cases'],
                    'Cases with Awards': stats['cases_with_damages'],
                    f'Median Award ({DEFAULT_REFERENCE_YEAR}$)': f"${stats['adjusted_damages']['median']:,.0f}",
                    f'Mean Award ({DEFAULT_REFERENCE_YEAR}$)': f"${stats['adjusted_damages']['mean']:,.0f}",
                    'Std. Deviation': f"${stats['adjusted_damages']['std']:,.0f}",
                    'Min Award': f"${stats['adjusted_damages']['min']:,.0f}",
                    'Max Award': f"${stats['adjusted_damages']['max']:,.0f}",
                })

        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

            st.divider()

            st.subheader("Comparative Analysis")

            fig_comparison = go.Figure()

            for i, category_name in enumerate(selected_categories):
                category_cases = get_filtered_category_cases(category_name)
                if category_cases:
                    stats = calculate_category_statistics(category_cases, category_name)
                    fig_comparison.add_trace(go.Bar(
                        name=category_name,
                        x=['Min Award', 'Median Award', 'Max Award'],
                        y=[stats['adjusted_damages']['min'],
                           stats['adjusted_damages']['median'],
                           stats['adjusted_damages']['max']],
                        text=[f"${stats['adjusted_damages']['min']:,.0f}",
                              f"${stats['adjusted_damages']['median']:,.0f}",
                              f"${stats['adjusted_damages']['max']:,.0f}"],
                        textposition='auto',
                        marker_color=MD3_COLORS[i % len(MD3_COLORS)],
                    ))

            fig_comparison.update_layout(
                title=dict(
                    text=f'Award Comparison by Category ({DEFAULT_REFERENCE_YEAR}$)',
                    font=dict(size=16),
                ),
                xaxis_title='Metric',
                yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
                yaxis=dict(tickformat='$,.0f'),
                barmode='group',
                height=500,
                template='plotly_white',
                showlegend=True,
                font=dict(family="Google Sans, Roboto, sans-serif"),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
            )

            st.plotly_chart(fig_comparison, use_container_width=True)

            st.divider()

            st.subheader("Awards Over Time by Category")

            fig_timeline = go.Figure()

            for i, category_name in enumerate(selected_categories):
                category_cases = get_filtered_category_cases(category_name)
                if category_cases:
                    data_points = []
                    for case in category_cases:
                        year = case.get('year')
                        damage = case.get('damages')
                        case_name = case.get('case_name', 'Unknown')

                        if year and damage and damage > 0:
                            adjusted_damage = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                            data_points.append({
                                'year': year,
                                'adjusted_damages': adjusted_damage if adjusted_damage else damage,
                                'case_name': case_name,
                                'category': category_name
                            })

                    if data_points:
                        df = pd.DataFrame(data_points)

                        hover_text = [f"<b>{row['case_name']}</b><br>Category: {row['category']}<br>Award ({DEFAULT_REFERENCE_YEAR}$): ${row['adjusted_damages']:,.0f}"
                                      for _, row in df.iterrows()]

                        fig_timeline.add_trace(go.Scatter(
                            x=df['year'],
                            y=df['adjusted_damages'],
                            mode='markers',
                            name=category_name,
                            marker=dict(
                                size=8,
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
                        text=f'Awards Over Time by Category ({DEFAULT_REFERENCE_YEAR}$)',
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
        st.subheader("Individual Category Details")

        for category_name in selected_categories:
            category_cases = get_filtered_category_cases(category_name)
            if category_cases:
                stats = calculate_category_statistics(category_cases, category_name)

                with st.expander(f"{category_name} ({len(category_cases)} cases)", expanded=False):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Sample Size", stats['total_cases'])
                    with col2:
                        st.metric(f"Median ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['median']:,.0f}")
                    with col3:
                        st.metric(f"Mean ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['mean']:,.0f}")
                    with col4:
                        st.metric("Std. Dev.", f"${stats['adjusted_damages']['std']:,.0f}")

                    st.divider()

                    timeline_fig = create_category_timeline_chart(category_cases, category_name)
                    if timeline_fig:
                        st.plotly_chart(timeline_fig, use_container_width=True)

                    st.divider()

                    st.markdown(f"**Cases in {category_name}**")
                    case_list = []
                    is_fla_category = category_name.startswith("FLA: ")

                    for case in category_cases:
                        damage = case.get('damages', 0)
                        year = case.get('year')
                        adjusted_damage = damage
                        if damage and year:
                            adj = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                            adjusted_damage = adj if adj else damage

                        fla_description = ""
                        if is_fla_category:
                            relationship_name = category_name[5:].strip().lower()
                            extended_data = case.get('extended_data', {})
                            fla_claims = extended_data.get('family_law_act_claims', []) or []
                            for claim in fla_claims:
                                if claim.get('relationship', '').strip().lower() == relationship_name:
                                    fla_description = claim.get('description', '')
                                    break

                        case_data = {
                            'Case Name': case.get('case_name', 'Unknown'),
                            'Year': year if year else 'N/A',
                            'Court': case.get('court', 'N/A'),
                            'Original Award': f"${damage:,.0f}" if damage else 'N/A',
                            f'Adjusted Award ({DEFAULT_REFERENCE_YEAR}$)': f"${adjusted_damage:,.0f}" if adjusted_damage else 'N/A'
                        }

                        if is_fla_category and fla_description:
                            case_data['Comments'] = fla_description

                        case_list.append(case_data)

                    cases_df = pd.DataFrame(case_list)
                    st.dataframe(cases_df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"No cases found for {category_name}")

        return

    # Single category view
    selected_category = selected_categories[0]
    category_cases = get_filtered_category_cases(selected_category)

    if not category_cases:
        st.warning(f"No cases found for {selected_category}")
        return

    stats = calculate_category_statistics(category_cases, selected_category)

    st.subheader(f"Overview: {selected_category}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sample Size", stats['total_cases'])
    with col2:
        st.metric("Cases with Awards", stats['cases_with_damages'])
    with col3:
        if stats['years']['min'] and stats['years']['max']:
            st.metric("Year Range", f"{stats['years']['min']}-{stats['years']['max']}")
        else:
            st.metric("Year Range", "N/A")
    with col4:
        st.metric(f"Median Award ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['median']:,.0f}")

    st.divider()

    if stats['cases_with_damages'] > 0:
        st.subheader(f"Award Statistics (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                f"Mean Award ({DEFAULT_REFERENCE_YEAR}$)",
                f"${stats['adjusted_damages']['mean']:,.0f}",
                help=f"Average of all awards, adjusted to {DEFAULT_REFERENCE_YEAR} dollars"
            )
        with col2:
            st.metric(
                "Std. Deviation",
                f"${stats['adjusted_damages']['std']:,.0f}",
                help="Measure of award variability (inflation-adjusted)"
            )
        with col3:
            st.metric("Range", f"${stats['adjusted_damages']['min']:,.0f} - ${stats['adjusted_damages']['max']:,.0f}")

        st.caption(f"All awards adjusted to {DEFAULT_REFERENCE_YEAR} dollars using Canadian CPI")

        st.divider()

    st.subheader("Awards Timeline")
    timeline_fig = create_category_timeline_chart(category_cases, selected_category)

    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)
    else:
        st.info("Insufficient data to display timeline.")

    st.divider()

    st.subheader(f"All {len(category_cases)} Cases")

    case_list = []
    is_fla_category = selected_category.startswith("FLA: ")

    for case in category_cases:
        damage = case.get('damages', 0)
        year = case.get('year')
        adjusted_damage = damage
        if damage and year:
            adj = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
            adjusted_damage = adj if adj else damage

        fla_description = ""
        if is_fla_category:
            relationship_name = selected_category[5:].strip().lower()
            extended_data = case.get('extended_data', {})
            fla_claims = extended_data.get('family_law_act_claims', []) or []
            for claim in fla_claims:
                if claim.get('relationship', '').strip().lower() == relationship_name:
                    fla_description = claim.get('description', '')
                    break

        case_data = {
            'Case Name': case.get('case_name', 'Unknown'),
            'Year': year if year else 'N/A',
            'Court': case.get('court', 'N/A'),
            'Original Award': f"${damage:,.0f}" if damage else 'N/A',
            f'Adjusted Award ({DEFAULT_REFERENCE_YEAR}$)': f"${adjusted_damage:,.0f}" if adjusted_damage else 'N/A'
        }

        if is_fla_category and fla_description:
            case_data['Comments'] = fla_description

        case_list.append(case_data)

    cases_df = pd.DataFrame(case_list)
    st.dataframe(cases_df, use_container_width=True, hide_index=True)
