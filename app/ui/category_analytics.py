"""
Category-specific analytics and visualizations.

This module provides analytics tools for examining awards by injury category/body region,
including comparative statistics, temporal trends, and case distributions.
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
    # Fallback if module not available
    DEFAULT_REFERENCE_YEAR = 2024
    def adjust_for_inflation(amount, from_year, to_year):
        return None

# Import outlier filtering
from app.core.search import filter_outliers


def _load_valid_compendium_categories() -> set:
    """
    Load valid categories from compendium_regions.json.

    Returns:
        Set of valid category names (case-insensitive, uppercased)
    """
    import json
    from pathlib import Path

    valid_categories = set()

    try:
        compendium_path = Path("compendium_regions.json")
        with open(compendium_path, 'r') as f:
            compendium_data = json.load(f)

        # Extract all subcategories from injury_categories
        injury_categories = compendium_data.get('injury_categories', {})
        for category_id, category_info in injury_categories.items():
            subcategories = category_info.get('subcategories', [])
            for subcat in subcategories:
                # Normalize to uppercase for matching
                valid_categories.add(subcat.strip().upper())

    except Exception as e:
        # If we can't load the compendium, return empty set (will show all categories)
        st.warning(f"Could not load compendium categories: {e}")

    return valid_categories


def get_all_categories(cases: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Extract all unique categories/regions from cases that match the compendium structure,
    including FLA relationship types.

    Args:
        cases: List of case dictionaries

    Returns:
        Dictionary with 'injury_categories' and 'fla_relationships' lists
    """
    # Load valid categories from compendium
    valid_categories = _load_valid_compendium_categories()

    injury_categories = set()
    fla_relationships = set()

    for case in cases:
        # Injury categories (normalize to uppercase for consistency)
        region = case.get('region')
        if region and region.strip():
            region_upper = region.strip().upper()
            # Only add if it matches a valid compendium category
            if not valid_categories or region_upper in valid_categories:
                injury_categories.add(region_upper)

        # Also check extended_data for additional regions
        extended_data = case.get('extended_data', {})
        regions = extended_data.get('regions', [])
        if regions:
            for r in regions:
                if r and r.strip():
                    r_upper = r.strip().upper()
                    # Only add if it matches a valid compendium category
                    if not valid_categories or r_upper in valid_categories:
                        injury_categories.add(r_upper)

        # FLA relationship types
        fla_claims = extended_data.get('family_law_act_claims', [])
        for claim in fla_claims:
            relationship = claim.get('relationship', '').strip()
            is_fla_award = claim.get('is_fla_award', True)
            if relationship and is_fla_award:
                # Prefix with "FLA: " to distinguish from injury categories
                fla_relationships.add(f"FLA: {relationship}")

    return {
        'injury_categories': sorted(list(injury_categories)),
        'fla_relationships': sorted(list(fla_relationships))
    }


def get_category_cases(cases: List[Dict[str, Any]], category_name: str) -> List[Dict[str, Any]]:
    """
    Filter cases belonging to a specific category (injury or FLA relationship).

    Args:
        cases: List of all cases
        category_name: Name of the category to filter by (may be prefixed with "FLA: ")

    Returns:
        List of cases in this category
    """
    category_cases = []

    # Check if this is an FLA relationship category
    is_fla_category = category_name.startswith("FLA: ")

    if is_fla_category:
        # Extract the relationship name (remove "FLA: " prefix, case-insensitive)
        relationship_name = category_name[5:].strip().lower()

        for case in cases:
            extended_data = case.get('extended_data', {})
            fla_claims = extended_data.get('family_law_act_claims', [])

            # Check if this case has this FLA relationship (case-insensitive)
            for claim in fla_claims:
                if claim.get('relationship', '').strip().lower() == relationship_name:
                    is_fla_award = claim.get('is_fla_award', True)
                    if is_fla_award:
                        category_cases.append(case)
                        break  # Don't add the same case multiple times
    else:
        # Regular injury category (case-insensitive matching)
        category_name_upper = category_name.upper()

        for case in cases:
            region = case.get('region', '')
            extended_data = case.get('extended_data', {})
            regions = extended_data.get('regions', [])

            # Normalize region and regions list for comparison
            region_upper = region.upper() if region else ''
            regions_upper = [r.upper() if isinstance(r, str) else r for r in regions]

            # Check if case belongs to this category
            if region_upper == category_name_upper or category_name_upper in regions_upper:
                category_cases.append(case)

    return category_cases


def calculate_category_statistics(category_cases: List[Dict[str, Any]], category_name: str = "") -> Dict[str, Any]:
    """
    Calculate comprehensive statistics for a category's cases.

    Args:
        category_cases: List of cases in the category
        category_name: Name of the category (used to determine if it's FLA)

    Returns:
        Dictionary containing various statistics
    """
    total_cases = len(category_cases)
    is_fla_category = category_name.startswith("FLA: ")

    # Extract damages values (both original and inflation-adjusted)
    damages_values = []
    adjusted_damages_values = []

    if is_fla_category:
        # For FLA categories, get the specific FLA claim amounts (case-insensitive)
        relationship_name = category_name[5:].strip().lower()

        for case in category_cases:
            year = case.get('year')
            extended_data = case.get('extended_data', {})
            fla_claims = extended_data.get('family_law_act_claims', [])

            for claim in fla_claims:
                if claim.get('relationship', '').strip().lower() == relationship_name:
                    damage = claim.get('amount')
                    is_fla_award = claim.get('is_fla_award', True)

                    if damage and damage > 0 and is_fla_award:
                        damages_values.append(damage)

                        # Calculate inflation-adjusted value
                        if year:
                            adjusted = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                            adjusted_damages_values.append(adjusted if adjusted else damage)
                        else:
                            adjusted_damages_values.append(damage)
                    break  # Only count first matching claim per case
    else:
        # Regular injury categories - use main damages field
        for case in category_cases:
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
    for case in category_cases:
        year = case.get('year')
        if year:
            years.append(year)

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
    """
    Create a timeline chart showing award amounts over years with inflation adjustment.

    Args:
        category_cases: List of cases in the category
        category_name: Name of the category

    Returns:
        Plotly figure or None if insufficient data
    """
    # Prepare data
    data_points = []
    for case in category_cases:
        year = case.get('year')
        damage = case.get('damages')
        case_name = case.get('case_name', 'Unknown')

        if year and damage and damage > 0:
            # Calculate inflation-adjusted value
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

    # Create figure
    fig = go.Figure()

    # Add scatter plot for individual cases (adjusted values)
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
            color=df['adjusted_damages'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title=f"Award ({DEFAULT_REFERENCE_YEAR}$)"),
            line=dict(width=1, color='white')
        ),
        text=hover_text,
        hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
    ))

    fig.update_layout(
        title=f'{category_name} - Award Amounts Over Time (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
        xaxis_title='Year',
        yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
        hovermode='closest',
        showlegend=True,
        height=500,
        template='plotly_white'
    )

    fig.update_yaxes(tickformat='$,.0f')

    return fig


def display_category_analytics_page(cases: List[Dict[str, Any]], include_outliers: bool = True) -> None:
    """
    Main function to display the category analytics page.

    Args:
        cases: List of all cases
        include_outliers: Whether to include statistical outliers in calculations (default True)
    """
    st.header("🩺 Category Statistics")
    st.markdown("Explore award patterns and statistics by injury category or FLA relationship type. Compare different types of losses (e.g., injury categories vs. FLA claims).")

    # Helper function to get category cases with optional outlier filtering
    def get_filtered_category_cases(category_name: str) -> List[Dict[str, Any]]:
        """Get cases for a category, optionally filtering outliers."""
        category_cases = get_category_cases(cases, category_name)
        if not include_outliers and category_cases:
            category_cases = filter_outliers(category_cases)
        return category_cases

    # Get all categories (injury and FLA)
    categories_dict = get_all_categories(cases)
    injury_categories = categories_dict['injury_categories']
    fla_relationships = categories_dict['fla_relationships']

    # Combine all categories for selection
    all_categories = injury_categories + fla_relationships

    if not all_categories:
        st.warning("⚠️ No category information found in the dataset.")
        return

    st.info(f"📊 Dataset contains {len(injury_categories)} injury categories and {len(fla_relationships)} FLA relationship types ({len(all_categories)} total)")

    # Universal category selector - combines injury categories and FLA relationships
    selected_categories = st.multiselect(
        "Select Categories (Injury Types or FLA Relationships):",
        options=all_categories,
        default=[],
        max_selections=8,
        help="Select up to 8 categories to compare (injury categories or FLA relationship types). Each category is shown in a different color.",
        key="category_selector"
    )

    if not selected_categories:
        st.info("👆 Select one or more categories above to view their analytics")
        return

    # Warn if too many total selections (max 8 combined for legibility)
    if len(selected_categories) > 8:
        st.warning("⚠️ You've selected more than 8 categories total. For better chart legibility, please reduce your selection to 8 or fewer.")
        return

    # Check if we're comparing multiple categories
    is_comparison = len(selected_categories) > 1

    if is_comparison:
        # Display comparison view for multiple categories
        st.subheader(f"Comparing {len(selected_categories)} Categories")

        # Create comparison table
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

            # Comparison charts
            st.subheader("📊 Comparative Analysis")

            # Create comparison bar chart for key statistics
            fig_comparison = go.Figure()

            for category_name in selected_categories:
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
                    ))

            fig_comparison.update_layout(
                title=f'Award Comparison by Category (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
                xaxis_title='Metric',
                yaxis_title=f'Award Amount ({DEFAULT_REFERENCE_YEAR} $)',
                yaxis=dict(tickformat='$,.0f'),
                barmode='group',
                height=500,
                template='plotly_white',
                showlegend=True
            )

            st.plotly_chart(fig_comparison, use_container_width=True)

            st.divider()

            # Combined timeline for all selected categories
            st.subheader("📈 Awards Over Time by Category")

            fig_timeline = go.Figure()

            for category_name in selected_categories:
                category_cases = get_filtered_category_cases(category_name)
                if category_cases:
                    # Prepare data
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

                        # Add scatter plot for this category
                        hover_text = [f"<b>{row['case_name']}</b><br>Category: {row['category']}<br>Award ({DEFAULT_REFERENCE_YEAR}$): ${row['adjusted_damages']:,.0f}"
                                      for _, row in df.iterrows()]

                        fig_timeline.add_trace(go.Scatter(
                            x=df['year'],
                            y=df['adjusted_damages'],
                            mode='markers',
                            name=category_name,
                            marker=dict(size=8, line=dict(width=1, color='white')),
                            text=hover_text,
                            hovertemplate='%{text}<br>Year: %{x}<extra></extra>'
                        ))

            if fig_timeline.data:
                fig_timeline.update_layout(
                    title=f'Awards Over Time by Category (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})',
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

        # Individual category details and case lists in expanders
        st.divider()
        st.subheader("📋 Individual Category Details & Cases")

        for category_name in selected_categories:
            category_cases = get_filtered_category_cases(category_name)
            if category_cases:
                stats = calculate_category_statistics(category_cases, category_name)

                with st.expander(f"View {len(category_cases)} cases for {category_name}", expanded=False):
                    # Summary stats
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

                    # Timeline chart for this category
                    timeline_fig = create_category_timeline_chart(category_cases, category_name)
                    if timeline_fig:
                        st.plotly_chart(timeline_fig, use_container_width=True)

                    st.divider()

                    # Case list
                    st.markdown(f"**Cases in {category_name}:**")
                    case_list = []
                    for case in category_cases:
                        damage = case.get('damages', 0)
                        year = case.get('year')

                        # Calculate adjusted damage
                        adjusted_damage = damage
                        if damage and year:
                            adj = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
                            adjusted_damage = adj if adj else damage

                        case_list.append({
                            'Case Name': case.get('case_name', 'Unknown'),
                            'Year': year if year else 'N/A',
                            'Court': case.get('court', 'N/A'),
                            'Original Award': f"${damage:,.0f}" if damage else 'N/A',
                            f'Adjusted Award ({DEFAULT_REFERENCE_YEAR}$)': f"${adjusted_damage:,.0f}" if adjusted_damage else 'N/A'
                        })

                    cases_df = pd.DataFrame(case_list)
                    st.dataframe(cases_df, use_container_width=True, hide_index=True)
            else:
                st.warning(f"No cases found for {category_name}")

        return

    # Single category view
    selected_category = selected_categories[0]

    # Get cases for this category
    category_cases = get_filtered_category_cases(selected_category)

    if not category_cases:
        st.warning(f"No cases found for {selected_category}")
        return

    # Calculate statistics
    stats = calculate_category_statistics(category_cases, selected_category)

    # Display overview metrics
    st.subheader(f"Overview: {selected_category}")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Sample Size", stats['total_cases'])

    with col2:
        st.metric("Cases with Awards", stats['cases_with_damages'])

    with col3:
        if stats['years']['min'] and stats['years']['max']:
            year_range = f"{stats['years']['min']}-{stats['years']['max']}"
            st.metric("Year Range", year_range)
        else:
            st.metric("Year Range", "N/A")

    with col4:
        st.metric(f"Median Award ({DEFAULT_REFERENCE_YEAR}$)", f"${stats['adjusted_damages']['median']:,.0f}")

    st.divider()

    # Damages statistics (inflation-adjusted)
    if stats['cases_with_damages'] > 0:
        st.subheader(f"💰 Award Statistics (Inflation-Adjusted to {DEFAULT_REFERENCE_YEAR})")

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

        st.caption(f"💡 All awards adjusted to {DEFAULT_REFERENCE_YEAR} dollars using Canadian CPI")

        st.divider()

    # Timeline chart
    st.subheader("📈 Awards Timeline")
    timeline_fig = create_category_timeline_chart(category_cases, selected_category)

    if timeline_fig:
        st.plotly_chart(timeline_fig, use_container_width=True)
    else:
        st.info("Insufficient data with both year and damages information to display timeline")

    st.divider()

    # Detailed case list
    st.subheader(f"📋 All {len(category_cases)} Cases")

    case_list = []
    for case in category_cases:
        damage = case.get('damages', 0)
        year = case.get('year')

        # Calculate adjusted damage
        adjusted_damage = damage
        if damage and year:
            adj = adjust_for_inflation(damage, year, DEFAULT_REFERENCE_YEAR)
            adjusted_damage = adj if adj else damage

        case_list.append({
            'Case Name': case.get('case_name', 'Unknown'),
            'Year': year if year else 'N/A',
            'Court': case.get('court', 'N/A'),
            'Original Award': f"${damage:,.0f}" if damage else 'N/A',
            f'Adjusted Award ({DEFAULT_REFERENCE_YEAR}$)': f"${adjusted_damage:,.0f}" if adjusted_damage else 'N/A'
        })

    cases_df = pd.DataFrame(case_list)
    st.dataframe(cases_df, use_container_width=True, hide_index=True)
