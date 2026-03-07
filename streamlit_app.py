"""
Ontario Damages Compendium — Legal Reference Tool

Material Design 3 UI v4.0: clean surfaces, elevation, proper typography,
consistent spacing, accessible color system.
"""

import streamlit as st
import numpy as np
import tempfile
import os
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re

# Core modules
from app.core.config import *
from app.core.data_loader import initialize_data
from app.core.search import (
    search_cases, extract_damages_value, boolean_search, filter_outliers
)
from app.ui.visualizations import (
    create_inflation_chart, calculate_chart_statistics, create_damages_cap_chart
)
from app.ui.judge_analytics import display_judge_analytics_page
from app.ui.category_analytics import display_category_analytics_page
from app.ui.fla_analytics import display_fla_analytics_page

from expert_report_analyzer import analyze_expert_report
from pdf_report_generator import generate_damages_report
from inflation_adjuster import (
    DEFAULT_REFERENCE_YEAR, get_data_source, get_cpi_data,
    BOC_CPI_CSV, reload_cpi_data, adjust_for_inflation
)

# =============================================================================
# VERSION & CACHE
# =============================================================================

APP_VERSION = "4.0.0"

if "app_version" not in st.session_state or st.session_state.app_version != APP_VERSION:
    st.cache_resource.clear()
    st.cache_data.clear()
    st.session_state.app_version = APP_VERSION

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="ON Damages Compendium",
    page_icon="balance_scale",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# MATERIAL DESIGN 3 — CSS
# =============================================================================

st.markdown("""
<style>
/* ─── MD3 DESIGN TOKENS ─────────────────────────────────────────────────── */
:root {
  /* Primary */
  --md-primary: #1a73e8;
  --md-on-primary: #ffffff;
  --md-primary-container: #d3e3fd;
  --md-on-primary-container: #041e49;

  /* Secondary */
  --md-secondary: #5f6368;
  --md-on-secondary: #ffffff;
  --md-secondary-container: #e8eaed;
  --md-on-secondary-container: #1f1f1f;

  /* Tertiary */
  --md-tertiary: #1e8e3e;
  --md-on-tertiary: #ffffff;
  --md-tertiary-container: #ceead6;
  --md-on-tertiary-container: #0d652d;

  /* Error */
  --md-error: #d93025;
  --md-error-container: #fce8e6;

  /* Surface */
  --md-surface: #ffffff;
  --md-surface-dim: #f8f9fa;
  --md-surface-container: #f1f3f4;
  --md-surface-container-high: #e8eaed;
  --md-surface-container-highest: #dadce0;
  --md-on-surface: #202124;
  --md-on-surface-variant: #5f6368;
  --md-outline: #dadce0;
  --md-outline-variant: #e8eaed;

  /* Elevation */
  --md-elevation-1: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
  --md-elevation-2: 0 1px 2px 0 rgba(60,64,67,0.3), 0 2px 6px 2px rgba(60,64,67,0.15);
  --md-elevation-3: 0 4px 8px 3px rgba(60,64,67,0.15), 0 1px 3px rgba(60,64,67,0.3);

  /* Typography */
  --md-font: 'Google Sans', 'Segoe UI', Roboto, -apple-system, sans-serif;
  --md-font-mono: 'Google Sans Mono', 'Roboto Mono', 'SF Mono', monospace;

  /* Shape */
  --md-shape-xs: 4px;
  --md-shape-sm: 8px;
  --md-shape-md: 12px;
  --md-shape-lg: 16px;
  --md-shape-xl: 28px;
}

/* ─── FONTS ──────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Google+Sans+Mono:wght@400;500&family=Roboto:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
  font-family: var(--md-font) !important;
  -webkit-font-smoothing: antialiased;
}

/* ─── GLOBAL CHROME ──────────────────────────────────────────────────────── */
#MainMenu, footer, .stDeployButton { visibility: hidden; display: none; }

.main .block-container {
  padding: 1.5rem 2rem 2rem !important;
  max-width: 100% !important;
}

/* ─── SIDEBAR — MD3 NAVIGATION DRAWER ────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: var(--md-surface) !important;
  border-right: 1px solid var(--md-outline-variant) !important;
}

section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
  color: var(--md-on-surface-variant) !important;
}

/* Nav buttons — MD3 nav item pattern */
section[data-testid="stSidebar"] .stButton > button {
  width: 100% !important;
  text-align: left !important;
  background: transparent !important;
  border: none !important;
  border-radius: var(--md-shape-xl) !important;
  color: var(--md-on-surface-variant) !important;
  font-family: var(--md-font) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 0.625rem 1rem !important;
  margin: 2px 0.5rem !important;
  letter-spacing: 0.01em !important;
  transition: background 0.2s ease, color 0.15s ease !important;
  box-shadow: none !important;
  line-height: 1.4 !important;
}

section[data-testid="stSidebar"] .stButton > button:hover {
  background: var(--md-secondary-container) !important;
  color: var(--md-on-secondary-container) !important;
}

section[data-testid="stSidebar"] .stButton > button:focus {
  box-shadow: none !important;
  outline: none !important;
}

/* Active nav item — MD3 active indicator */
.nav-active .stButton > button {
  background: var(--md-primary-container) !important;
  color: var(--md-on-primary-container) !important;
  font-weight: 700 !important;
}

/* Sidebar expander */
section[data-testid="stSidebar"] .stExpander {
  border: 1px solid var(--md-outline-variant) !important;
  border-radius: var(--md-shape-sm) !important;
}

section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] .stRadio label {
  font-size: 0.8125rem !important;
  color: var(--md-on-surface-variant) !important;
}

/* ─── PAGE HEADERS ───────────────────────────────────────────────────────── */
.page-overline {
  font-family: var(--md-font);
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--md-primary);
  margin-bottom: 0.25rem;
}

.page-headline {
  font-size: 1.75rem;
  font-weight: 400;
  letter-spacing: -0.01em;
  color: var(--md-on-surface);
  margin-bottom: 0.25rem;
  line-height: 1.3;
}

.page-supporting {
  font-size: 0.875rem;
  color: var(--md-on-surface-variant);
  margin-bottom: 1.5rem;
  line-height: 1.5;
}

/* ─── MD3 CARDS ──────────────────────────────────────────────────────────── */
.md-card {
  background: var(--md-surface);
  border-radius: var(--md-shape-md);
  box-shadow: var(--md-elevation-1);
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
  transition: box-shadow 0.2s ease;
}

.md-card:hover {
  box-shadow: var(--md-elevation-2);
}

.md-card-outlined {
  background: var(--md-surface);
  border: 1px solid var(--md-outline);
  border-radius: var(--md-shape-md);
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
}

/* ─── STAT CARDS (KPI) ───────────────────────────────────────────────────── */
.stat-card {
  background: var(--md-surface);
  border-radius: var(--md-shape-md);
  box-shadow: var(--md-elevation-1);
  padding: 1rem 1.25rem;
  text-align: center;
}

.stat-card-value {
  font-family: var(--md-font-mono);
  font-size: 1.375rem;
  font-weight: 500;
  color: var(--md-on-surface);
  display: block;
  line-height: 1.3;
}

.stat-card-label {
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--md-on-surface-variant);
  display: block;
  margin-top: 0.25rem;
}

/* Accent variants */
.stat-card-primary { border-top: 3px solid var(--md-primary); }
.stat-card-tertiary { border-top: 3px solid var(--md-tertiary); }

/* ─── DATA TABLE (Compendium) ────────────────────────────────────────────── */
.data-table-header {
  display: grid;
  grid-template-columns: 3fr 3.5rem 5rem 2.5fr 8rem;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-bottom: 2px solid var(--md-outline);
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--md-on-surface-variant);
  background: var(--md-surface-dim);
  border-radius: var(--md-shape-sm) var(--md-shape-sm) 0 0;
}

.data-table-row {
  display: grid;
  grid-template-columns: 3fr 3.5rem 5rem 2.5fr 8rem;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--md-outline-variant);
  font-size: 0.875rem;
  align-items: center;
  cursor: pointer;
  transition: background 0.15s ease;
}

.data-table-row:hover {
  background: var(--md-surface-container);
}

.data-table-row.row-selected {
  background: var(--md-primary-container);
}

.col-name { font-weight: 500; color: var(--md-on-surface); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.col-year { font-family: var(--md-font-mono); color: var(--md-on-surface-variant); font-size: 0.8125rem; }
.col-court { color: var(--md-on-surface-variant); font-size: 0.8125rem; }
.col-cat { color: var(--md-on-surface-variant); font-size: 0.8125rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.col-award {
  font-family: var(--md-font-mono);
  font-weight: 500;
  color: var(--md-tertiary);
  font-size: 0.875rem;
  text-align: right;
}

/* ─── DETAIL PANEL ───────────────────────────────────────────────────────── */
.detail-surface {
  background: var(--md-surface-container);
  border-radius: var(--md-shape-md);
  padding: 1.5rem;
  margin: 0.5rem 0 1rem 0;
  border: 1px solid var(--md-outline-variant);
}

.detail-award-display {
  font-family: var(--md-font-mono);
  font-size: 2rem;
  font-weight: 500;
  color: var(--md-tertiary);
  display: block;
}

.detail-label {
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--md-on-surface-variant);
}

/* ─── MD3 CHIPS ──────────────────────────────────────────────────────────── */
.chip {
  display: inline-flex;
  align-items: center;
  background: var(--md-secondary-container);
  color: var(--md-on-secondary-container);
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.25rem 0.75rem;
  border-radius: var(--md-shape-xs);
  margin: 0.125rem 0.25rem 0.125rem 0;
  letter-spacing: 0.02em;
  height: 1.75rem;
}

.chip-primary { background: var(--md-primary-container); color: var(--md-on-primary-container); }
.chip-success { background: var(--md-tertiary-container); color: var(--md-on-tertiary-container); }
.chip-warning { background: #fef7e0; color: #ea8600; }

/* ─── RESULT CARDS (AI Search) ───────────────────────────────────────────── */
.result-surface {
  background: var(--md-surface);
  border: 1px solid var(--md-outline-variant);
  border-radius: var(--md-shape-md);
  padding: 1.25rem;
  margin-bottom: 0.75rem;
  transition: box-shadow 0.2s ease;
}

.result-surface:hover {
  box-shadow: var(--md-elevation-1);
}

/* ─── TOC NAVIGATION ─────────────────────────────────────────────────────── */
.toc-label {
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--md-on-surface-variant);
  padding: 0.75rem 0 0.375rem 0;
  display: block;
}

/* ─── METRICS OVERRIDE ───────────────────────────────────────────────────── */
[data-testid="stMetricValue"] {
  font-family: var(--md-font-mono) !important;
  font-size: 1.25rem !important;
  font-weight: 500 !important;
  color: var(--md-on-surface) !important;
}

[data-testid="stMetricLabel"] {
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.04em !important;
  color: var(--md-on-surface-variant) !important;
}

/* ─── DIVIDERS ───────────────────────────────────────────────────────────── */
hr {
  border: none !important;
  border-top: 1px solid var(--md-outline-variant) !important;
  margin: 1rem 0 !important;
}

/* ─── EXPANDERS ──────────────────────────────────────────────────────────── */
.stExpander {
  border: 1px solid var(--md-outline-variant) !important;
  border-radius: var(--md-shape-sm) !important;
}

.stExpander > summary {
  font-size: 0.875rem !important;
  font-weight: 500 !important;
}

/* ─── BUTTONS — MD3 ──────────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
  border-radius: var(--md-shape-xl) !important;
  font-weight: 500 !important;
  letter-spacing: 0.02em !important;
  padding: 0.625rem 1.5rem !important;
  text-transform: none !important;
}

/* ─── INPUTS — MD3 ───────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
  border-radius: var(--md-shape-xs) !important;
  border-color: var(--md-outline) !important;
  font-family: var(--md-font) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--md-primary) !important;
  box-shadow: 0 0 0 1px var(--md-primary) !important;
}

.stSelectbox > div > div {
  border-radius: var(--md-shape-xs) !important;
}

/* ─── TABS — MD3 ─────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  gap: 0 !important;
  border-bottom: 1px solid var(--md-outline-variant) !important;
}

.stTabs [data-baseweb="tab"] {
  font-family: var(--md-font) !important;
  font-weight: 500 !important;
  font-size: 0.875rem !important;
  letter-spacing: 0.02em !important;
  padding: 0.75rem 1.25rem !important;
}

/* ─── DATAFRAMES ─────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border-radius: var(--md-shape-sm) !important;
  overflow: hidden;
}

/* ─── DARK MODE ──────────────────────────────────────────────────────────── */
@media (prefers-color-scheme: dark) {
  :root {
    --md-surface: #1e1e1e;
    --md-surface-dim: #141414;
    --md-surface-container: #252525;
    --md-surface-container-high: #2d2d2d;
    --md-surface-container-highest: #353535;
    --md-on-surface: #e3e3e3;
    --md-on-surface-variant: #c4c7c5;
    --md-outline: #444746;
    --md-outline-variant: #353535;
    --md-primary: #a8c7fa;
    --md-on-primary: #062e6f;
    --md-primary-container: #0842a0;
    --md-on-primary-container: #d3e3fd;
    --md-secondary-container: #444746;
    --md-on-secondary-container: #e3e3e3;
    --md-tertiary: #81c995;
    --md-tertiary-container: #0d652d;
    --md-on-tertiary-container: #ceead6;
    --md-elevation-1: 0 1px 3px 1px rgba(0,0,0,0.15), 0 1px 2px 0 rgba(0,0,0,0.3);
    --md-elevation-2: 0 2px 6px 2px rgba(0,0,0,0.15), 0 1px 2px 0 rgba(0,0,0,0.3);
  }
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA
# =============================================================================

model, cases, region_map = initialize_data()

# =============================================================================
# SESSION STATE
# =============================================================================

VIEWS = ["compendium", "ai_search", "judges", "categories", "fla"]

VIEW_META = {
    "compendium": {"label": "Compendium",       "num": "01"},
    "ai_search":  {"label": "AI Search",         "num": "02"},
    "judges":     {"label": "Judge Analytics",   "num": "03"},
    "categories": {"label": "Category Stats",    "num": "04"},
    "fla":        {"label": "FLA Claims",        "num": "05"},
}

_defaults = {
    "current_view":           "compendium",
    "search_results":         None,
    "analysis_data":          None,
    "dismissed_cases":        set(),
    "toc_selection":          None,
    "toc_group_by":           "category",
    "comp_search":            "",
    "comp_search_mode":       "fuzzy",
    "comp_sort":              "year_desc",
    "comp_selected_case_id":  None,
    "comp_page":              0,
    "_last_filter_key":       None,
}

for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def render_page_header(num: str, title: str, subtitle: str) -> None:
    """Render a consistent MD3 page header."""
    st.markdown(f'<div class="page-overline">Section {num}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-headline">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-supporting">{subtitle}</div>', unsafe_allow_html=True)


def display_enhanced_data(case: Dict, show_fla: bool = False) -> None:
    """Render structured case detail from extended_data."""
    ext = case.get("extended_data") or {}
    if not ext:
        return

    num_p = ext.get("num_plaintiffs", 0)
    if num_p > 1:
        st.info(f"Multi-plaintiff case ({num_p} plaintiffs)")

    demo = []
    if ext.get("plaintiff_id"):
        demo.append(f"Plaintiff {ext['plaintiff_id']}")
    if ext.get("sex"):
        demo.append(f"Sex: {ext['sex']}")
    if ext.get("age"):
        demo.append(f"Age at injury: {ext['age']}")
    if demo:
        st.markdown(f"**Demographics:** {'  &middot;  '.join(demo)}")

    injuries = ext.get("injuries") or []
    if injuries:
        st.markdown("**Injuries & Diagnoses**")
        seen, uniq = set(), []
        for inj in injuries:
            key = inj.strip().lower()
            if key not in seen:
                seen.add(key)
                uniq.append(inj)
        col_a, col_b = st.columns(2)
        mid = (len(uniq) + 1) // 2
        with col_a:
            for inj in uniq[:mid]:
                st.markdown(f"- {inj}")
        with col_b:
            for inj in uniq[mid:]:
                st.markdown(f"- {inj}")

    other_dmg = ext.get("other_damages") or []
    if other_dmg:
        st.markdown("**Pecuniary Damages (Economic Losses)**")
        for d in other_dmg:
            dtype = d.get("type", "Other").replace("_", " ").title()
            amt   = d.get("amount")
            desc  = d.get("description", "")
            line  = f"- {dtype}"
            if amt:
                line += f": ${amt:,.0f}"
            if desc:
                line += f" ({desc})"
            st.markdown(line)

    if show_fla:
        fla = ext.get("family_law_act_claims") or []
        if fla:
            st.markdown("**Family Law Act Claims**")
            for claim in fla:
                rel  = claim.get("relationship", "FLA claim")
                desc = claim.get("description", "")
                amt  = claim.get("amount")
                text = f"- {rel}" + (f" ({desc})" if desc else "")
                text += f": ${amt:,.0f}" if amt else ""
                st.markdown(text)

    cites = ext.get("citations") or []
    if cites:
        st.markdown(f"**Citations:** {', '.join(cites)}")

    judges = ext.get("judges") or []
    if judges:
        st.markdown(f"**Judge(s):** {', '.join(judges)}")

    if ext.get("is_provisional"):
        st.warning("Provisional damages award")

    comments = ext.get("comments") or case.get("comments") or ""
    if comments:
        st.markdown(f"**Comments:** {comments}")


def fuzzy_score(case: Dict, query: str) -> float:
    """Score a case against a free-text query. Returns 0-1."""
    if not query.strip():
        return 1.0
    q = query.lower()
    words = re.findall(r"\w+", q)
    if not words:
        return 1.0

    ext = case.get("extended_data") or {}
    injuries_text = " ".join(ext.get("injuries") or [])
    blob = " ".join([
        str(case.get("case_name", "")),
        str(case.get("citation", "")),
        str(case.get("comments", "")),
        str(case.get("summary_text", "")),
        injuries_text,
        str(ext.get("comments", "")),
    ]).lower()

    hit = sum(1 for w in words if w in blob)
    phrase_bonus = 0.25 if q in blob else 0.0
    return min((hit / len(words)) + phrase_bonus, 1.0)


def get_case_categories(case: Dict) -> List[str]:
    """Return display category list for a case."""
    ext = case.get("extended_data") or {}
    cats = ext.get("categories") or []
    if not cats:
        region = case.get("region") or case.get("category") or ""
        cats = [region] if region else []
    return [c.strip() for c in cats if c.strip()]


def build_toc_categories(cases_list: List[Dict]) -> Dict[str, int]:
    """Category -> count mapping, sorted by count desc."""
    counts: Dict[str, int] = {}
    for c in cases_list:
        for cat in get_case_categories(c):
            key = cat.upper()
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def build_toc_years(cases_list: List[Dict]) -> Dict[str, int]:
    """Decade -> count mapping, sorted by decade desc."""
    counts: Dict[str, int] = {}
    for c in cases_list:
        yr = c.get("year")
        if yr:
            decade = f"{(yr // 10) * 10}s"
            counts[decade] = counts.get(decade, 0) + 1
    return dict(sorted(counts.items(), reverse=True))


def filter_and_sort_cases(
    cases: List[Dict],
    query: str,
    search_mode: str,
    toc_selection: Optional[str],
    toc_group_by: str,
    sort: str,
) -> List[Dict]:
    """Apply ToC filter, search query, and sort to the case list."""
    filtered = list(cases)

    if toc_selection:
        sel = toc_selection.upper()
        if toc_group_by == "category":
            filtered = [
                c for c in filtered
                if sel in [cat.upper() for cat in get_case_categories(c)]
            ]
        elif toc_group_by == "year":
            decade_start = int(toc_selection.replace("s", ""))
            filtered = [
                c for c in filtered
                if c.get("year") and decade_start <= c["year"] < decade_start + 10
            ]

    if query.strip():
        if search_mode == "fuzzy":
            scored = [(c, fuzzy_score(c, query)) for c in filtered]
            filtered = [c for c, s in scored if s >= 0.3]
            filtered.sort(key=lambda c: fuzzy_score(c, query), reverse=True)
            return filtered
        elif search_mode == "boolean":
            try:
                filtered = boolean_search(
                    query=query,
                    cases=filtered,
                    search_fields=["case_name", "injuries", "comments", "summary"],
                )
            except Exception:
                pass

    if sort == "year_desc":
        filtered.sort(key=lambda c: c.get("year") or 0, reverse=True)
    elif sort == "year_asc":
        filtered.sort(key=lambda c: c.get("year") or 0)
    elif sort == "award_desc":
        filtered.sort(key=lambda c: extract_damages_value(c) or 0, reverse=True)
    elif sort == "award_asc":
        filtered.sort(key=lambda c: extract_damages_value(c) or 0)
    elif sort == "name_asc":
        filtered.sort(key=lambda c: (c.get("case_name") or "").lower())

    return filtered


def render_stat_bar(values: List[float], n_cases: int) -> None:
    """Render a 4-column MD3 stat card bar."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="stat-card stat-card-primary">'
            f'<span class="stat-card-value">{n_cases:,}</span>'
            f'<span class="stat-card-label">Cases</span></div>',
            unsafe_allow_html=True,
        )
    if values:
        median = int(np.median(values))
        lo = int(min(values))
        hi = int(max(values))
        with c2:
            st.markdown(
                f'<div class="stat-card">'
                f'<span class="stat-card-value">${median:,}</span>'
                f'<span class="stat-card-label">Median Award</span></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div class="stat-card">'
                f'<span class="stat-card-value">${lo:,}</span>'
                f'<span class="stat-card-label">Min Award</span></div>',
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f'<div class="stat-card stat-card-tertiary">'
                f'<span class="stat-card-value">${hi:,}</span>'
                f'<span class="stat-card-label">Max Award</span></div>',
                unsafe_allow_html=True,
            )


# =============================================================================
# SIDEBAR — MD3 NAVIGATION DRAWER
# =============================================================================

with st.sidebar:
    n_cases_total = len(cases) if cases else 0

    st.markdown(
        f"""
        <div style="padding:1.25rem 1rem 1rem;border-bottom:1px solid var(--md-outline-variant);margin-bottom:0.75rem;">
          <div style="font-size:0.6875rem;font-weight:500;letter-spacing:0.08em;
                      text-transform:uppercase;color:var(--md-primary);
                      margin-bottom:0.25rem;">Ontario</div>
          <div style="font-size:1.125rem;font-weight:700;color:var(--md-on-surface);
                      letter-spacing:-0.01em;line-height:1.3;">Damages
              Compendium</div>
          <div style="font-size:0.75rem;color:var(--md-on-surface-variant);
                      margin-top:0.5rem;">v{APP_VERSION} &middot; {n_cases_total:,} cases</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<span style="font-size:0.6875rem;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;'
        'color:var(--md-on-surface-variant);padding:0 1rem;display:block;margin-bottom:0.25rem;">Navigation</span>',
        unsafe_allow_html=True,
    )

    for vid in VIEWS:
        meta   = VIEW_META[vid]
        active = st.session_state.current_view == vid
        label  = f"{meta['label']}"
        if active:
            st.markdown('<div class="nav-active">', unsafe_allow_html=True)
        if st.button(label, key=f"nav_{vid}"):
            st.session_state.current_view = vid
            st.rerun()
        if active:
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div style="border-top:1px solid var(--md-outline-variant);margin:1rem 0.75rem 0.75rem;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span style="font-size:0.6875rem;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;'
        'color:var(--md-on-surface-variant);padding:0 1rem;display:block;margin-bottom:0.25rem;">Settings</span>',
        unsafe_allow_html=True,
    )

    include_outliers = st.checkbox(
        "Include outliers",
        value=True,
        key="include_outliers_global",
        help="When unchecked, awards outside 1.5x IQR are excluded from analytics and AI search.",
    )

    with st.expander("CPI Data", expanded=False):
        st.caption(get_data_source())
        cpi_raw = get_cpi_data()
        buf = io.StringIO()
        buf.write("Year,CPI\n")
        for yr_k in sorted(cpi_raw.keys()):
            buf.write(f"{yr_k},{cpi_raw[yr_k]:.2f}\n")
        st.download_button(
            "Download CPI CSV",
            buf.getvalue(),
            "cpi_data.csv",
            "text/csv",
            key="dl_cpi_sb",
        )
        cpi_upload = st.file_uploader(
            "Upload updated CPI CSV",
            type=["csv"],
            key="cpi_upload_sb",
        )
        if cpi_upload:
            try:
                BOC_CPI_CSV.parent.mkdir(parents=True, exist_ok=True)
                with open(BOC_CPI_CSV, "wb") as _f:
                    _f.write(cpi_upload.getbuffer())
                new_cpi = reload_cpi_data()
                st.success(f"Updated: {len(new_cpi)} years of CPI data")
            except Exception as _e:
                st.error(str(_e))

    st.markdown(
        '<div style="border-top:1px solid var(--md-outline-variant);margin-top:1rem;padding:1rem;">'
        '<span style="font-size:0.75rem;color:var(--md-on-surface-variant);line-height:1.6;display:block;">'
        "Reference only. Always verify case details and consult primary sources."
        "</span></div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# VIEW 01 — COMPENDIUM BROWSER
# =============================================================================

def render_compendium() -> None:
    """Browsable compendium with ToC, fuzzy search, boolean search."""
    render_page_header(
        "01",
        "Compendium Browser",
        "Browse all cases with fuzzy and boolean search. Navigate by category or decade.",
    )

    # Search controls
    sc1, sc2, sc3 = st.columns([6, 2, 2])
    with sc1:
        new_q = st.text_input(
            "Search",
            value=st.session_state.comp_search,
            placeholder="Search cases, injuries, comments, citations...",
            label_visibility="collapsed",
            key="comp_q_input",
        )
        if new_q != st.session_state.comp_search:
            st.session_state.comp_search = new_q
            st.session_state.comp_page = 0

    with sc2:
        mode_idx = 0 if st.session_state.comp_search_mode == "fuzzy" else 1
        new_mode = st.selectbox(
            "Mode",
            ["fuzzy", "boolean"],
            index=mode_idx,
            format_func=lambda x: "Fuzzy Search" if x == "fuzzy" else "Boolean Search",
            label_visibility="collapsed",
            key="comp_mode_sel",
        )
        if new_mode != st.session_state.comp_search_mode:
            st.session_state.comp_search_mode = new_mode
            st.session_state.comp_page = 0

    with sc3:
        sort_opts = ["year_desc", "year_asc", "award_desc", "award_asc", "name_asc"]
        sort_labels = {
            "year_desc":  "Year (Newest)",
            "year_asc":   "Year (Oldest)",
            "award_desc": "Award (Highest)",
            "award_asc":  "Award (Lowest)",
            "name_asc":   "Name (A-Z)",
        }
        cur_sort_idx = sort_opts.index(st.session_state.comp_sort) if st.session_state.comp_sort in sort_opts else 0
        new_sort = st.selectbox(
            "Sort",
            sort_opts,
            index=cur_sort_idx,
            format_func=lambda x: sort_labels[x],
            label_visibility="collapsed",
            key="comp_sort_sel",
        )
        if new_sort != st.session_state.comp_sort:
            st.session_state.comp_sort = new_sort
            st.session_state.comp_page = 0

    if new_mode == "boolean" and st.session_state.comp_search:
        st.caption("Boolean operators: `AND`  `OR`  `NOT`  `\"exact phrase\"`")

    st.markdown("")

    # Layout: ToC | Cases
    toc_col, main_col = st.columns([1, 4], gap="medium")

    toc_cats  = build_toc_categories(cases)
    toc_years = build_toc_years(cases)

    with toc_col:
        st.markdown(
            '<span class="toc-label">Group by</span>',
            unsafe_allow_html=True,
        )
        new_grp = st.radio(
            "Group",
            ["category", "year"],
            index=0 if st.session_state.toc_group_by == "category" else 1,
            format_func=lambda x: "Category" if x == "category" else "Decade",
            horizontal=True,
            label_visibility="collapsed",
            key="toc_group_radio",
        )
        if new_grp != st.session_state.toc_group_by:
            st.session_state.toc_group_by = new_grp
            st.session_state.toc_selection = None
            st.session_state.comp_page = 0

        st.markdown(
            '<span class="toc-label">'
            + ("Categories" if new_grp == "category" else "Decades")
            + "</span>",
            unsafe_allow_html=True,
        )

        all_active = st.session_state.toc_selection is None
        all_lbl = f"All ({n_cases_total:,})"
        if st.button(all_lbl, key="toc_all", use_container_width=True, type="primary" if all_active else "secondary"):
            st.session_state.toc_selection = None
            st.session_state.comp_page = 0
            st.rerun()

        groups = toc_cats if new_grp == "category" else toc_years
        for grp_label, grp_count in groups.items():
            is_active = st.session_state.toc_selection == grp_label
            btn_lbl = f"{grp_label} ({grp_count})"
            if st.button(btn_lbl, key=f"toc_{grp_label}", use_container_width=True, type="primary" if is_active else "secondary"):
                if is_active:
                    st.session_state.toc_selection = None
                else:
                    st.session_state.toc_selection = grp_label
                st.session_state.comp_page = 0
                st.rerun()

    # Main case list
    with main_col:
        filter_key = (
            st.session_state.comp_search,
            st.session_state.comp_search_mode,
            st.session_state.toc_selection,
            st.session_state.toc_group_by,
            st.session_state.comp_sort,
        )
        if st.session_state._last_filter_key != filter_key:
            st.session_state.comp_page = 0
            st.session_state._last_filter_key = filter_key

        filtered = filter_and_sort_cases(
            cases,
            st.session_state.comp_search,
            st.session_state.comp_search_mode,
            st.session_state.toc_selection,
            st.session_state.toc_group_by,
            st.session_state.comp_sort,
        )

        award_vals = [extract_damages_value(c) for c in filtered]
        award_vals = [a for a in award_vals if a]
        render_stat_bar(award_vals, len(filtered))

        st.markdown("")

        if not filtered:
            st.info("No cases match the current filters. Try broadening your search or clearing the category selection.")
            return

        # Pagination
        PAGE_SIZE = 50
        total_pages = max(1, (len(filtered) + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(st.session_state.comp_page, total_pages - 1)
        st.session_state.comp_page = page

        start = page * PAGE_SIZE
        page_cases = filtered[start : start + PAGE_SIZE]

        # Table header
        st.markdown(
            '<div class="data-table-header">'
            "<span>Case Name</span>"
            "<span>Year</span>"
            "<span>Court</span>"
            "<span>Category</span>"
            "<span style='text-align:right'>Non-Pec. Award</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Case rows
        for case in page_cases:
            cid   = case.get("id", "")
            name  = case.get("case_name", "Unknown")
            year  = str(case.get("year", "--"))
            court = case.get("court", "--")
            cats  = get_case_categories(case)
            cat   = cats[0] if cats else "--"
            award = extract_damages_value(case)
            award_str = f"${award:,.0f}" if award else "--"
            selected  = st.session_state.comp_selected_case_id == cid
            sel_class = " row-selected" if selected else ""

            st.markdown(
                f'<div class="data-table-row{sel_class}">'
                f'<span class="col-name">{name}</span>'
                f'<span class="col-year">{year}</span>'
                f'<span class="col-court">{court}</span>'
                f'<span class="col-cat">{cat}</span>'
                f'<span class="col-award">{award_str}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

            btn_label = "Close" if selected else "View Details"
            if st.button(btn_label, key=f"open_{cid}", help=f"Toggle detail for {name}"):
                st.session_state.comp_selected_case_id = None if selected else cid
                st.rerun()

            if selected:
                with st.container():
                    st.markdown('<div class="detail-surface">', unsafe_allow_html=True)
                    h1, h2 = st.columns([3, 1])
                    with h1:
                        st.markdown(f"#### {name}")
                        meta_parts = [p for p in [year, court, case.get("citation", "")] if p and p != "--"]
                        st.caption("  &middot;  ".join(meta_parts))
                    with h2:
                        if award:
                            st.markdown(
                                f'<span class="detail-award-display">${award:,.0f}</span>'
                                f'<span class="detail-label">Non-Pecuniary Award</span>',
                                unsafe_allow_html=True,
                            )
                    st.markdown("---")
                    display_enhanced_data(case, show_fla=True)
                    st.markdown("</div>", unsafe_allow_html=True)

        # Pagination controls
        if total_pages > 1:
            st.markdown("")
            pg1, pg2, pg3 = st.columns([1, 3, 1])
            with pg1:
                if page > 0 and st.button("Previous", key="pg_prev"):
                    st.session_state.comp_page -= 1
                    st.rerun()
            with pg2:
                range_start = start + 1
                range_end = min(start + PAGE_SIZE, len(filtered))
                st.markdown(
                    f'<div style="text-align:center;font-size:0.8125rem;'
                    f'color:var(--md-on-surface-variant);padding-top:0.5rem;">'
                    f"Showing {range_start}&ndash;{range_end} of {len(filtered):,}"
                    f" &middot; Page {page+1} of {total_pages}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with pg3:
                if page < total_pages - 1 and st.button("Next", key="pg_next"):
                    st.session_state.comp_page += 1
                    st.rerun()


# =============================================================================
# VIEW 02 — AI SEARCH
# =============================================================================

def render_ai_search() -> None:
    """Semantic AI search with expert report upload and PDF export."""
    render_page_header(
        "02",
        "AI Search",
        "Hybrid semantic search combining injury embeddings, BM25 keywords, and metadata matching.",
    )

    ctrl_col, res_col = st.columns([1, 3], gap="large")

    with ctrl_col:
        # Expert report upload
        with st.expander("Upload Expert Report", expanded=False):
            uploaded_file = st.file_uploader(
                "PDF report",
                type=["pdf"],
                key="ai_report_upload",
                help="Upload a medical or expert report PDF to auto-populate the injury description.",
            )
            use_llm = st.checkbox(
                "Use AI analysis",
                value=True,
                key="ai_use_llm",
                help="Requires OPENAI_API_KEY or ANTHROPIC_API_KEY in environment.",
            )
            if uploaded_file and st.button("Analyze Report", key="ai_analyze_btn", type="secondary"):
                with st.spinner("Analyzing report..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    try:
                        analysis = analyze_expert_report(tmp_path, use_llm=use_llm)
                        st.session_state.analysis_data = analysis
                        st.success("Report analyzed. Injury description updated below.")
                        detected = analysis.get("injured_regions", [])
                        if detected:
                            st.write("**Detected regions:**")
                            for rid in detected:
                                if rid in region_map:
                                    st.write(f"- {region_map[rid]['label']}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                        st.info("Try manual entry below, or disable AI analysis and retry.")
                    finally:
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)

        # Injury description
        st.markdown("**Injury Description**")
        default_text = ""
        if st.session_state.analysis_data:
            injuries_ex = st.session_state.analysis_data.get("injuries", [])
            sequelae_ex = st.session_state.analysis_data.get("sequelae", [])
            parts = []
            if injuries_ex:
                parts.append("; ".join(injuries_ex))
            if sequelae_ex:
                parts.append("; ".join(sequelae_ex))
            default_text = " | ".join(parts)

        injury_text = st.text_area(
            "Describe the injury",
            value=default_text,
            height=120,
            placeholder=(
                "e.g. C5-C6 disc herniation with radiculopathy, chronic cervicogenic headache, "
                "whiplash grade II, PTSD"
            ),
            label_visibility="collapsed",
            key="ai_injury_text",
        )

        if st.session_state.analysis_data and st.button("Clear report data", key="ai_clear_analysis"):
            st.session_state.analysis_data = None
            st.rerun()

        st.markdown("**Demographics** *(optional)*")
        gender = st.radio(
            "Gender",
            ["Not Specified", "Male", "Female"],
            index=0,
            horizontal=True,
            key="ai_gender",
        )
        age = st.slider("Age at injury", 5, 100, 35, key="ai_age")

        st.markdown("**Results**")
        num_results = st.slider("Number of results", 5, 50, 10, step=5, key="ai_num_results")

        st.markdown("**Search Strategy**")
        weight_preset = st.selectbox(
            "Strategy",
            ["Balanced (Default)", "Medical Focus", "Symptom/Impact Focus", "Custom"],
            label_visibility="collapsed",
            key="ai_weight_preset",
            help=(
                "Balanced: general-purpose. Medical: specific diagnoses. "
                "Symptom/Impact: functional limitations. Custom: set weights manually."
            ),
        )
        preset_map = {
            "Balanced (Default)":    (0.40, 0.35, 0.15, 0.10),
            "Medical Focus":          (0.65, 0.20, 0.10, 0.05),
            "Symptom/Impact Focus":   (0.15, 0.60, 0.15, 0.10),
        }
        if weight_preset != "Custom":
            inj_w, kw_w, sem_w, meta_w = preset_map[weight_preset]
            desc_map = {
                "Balanced (Default)":   "Balanced across all factors",
                "Medical Focus":         "Prioritises specific diagnoses and clinical terms",
                "Symptom/Impact Focus":  "Prioritises narrative and functional descriptions",
            }
            st.caption(desc_map[weight_preset])
        else:
            st.caption("Weights are normalised to sum to 100%")
            inj_w  = st.slider("Injury Embedding", 0.0, 1.0, 0.40, 0.05, key="ai_w_inj")
            kw_w   = st.slider("Keyword / BM25",   0.0, 1.0, 0.35, 0.05, key="ai_w_kw")
            sem_w  = st.slider("Semantic (full)",   0.0, 1.0, 0.15, 0.05, key="ai_w_sem")
            meta_w = st.slider("Demographics",      0.0, 1.0, 0.10, 0.05, key="ai_w_meta")
            total  = inj_w + kw_w + sem_w + meta_w
            if total > 0:
                inj_w, kw_w, sem_w, meta_w = (
                    inj_w / total, kw_w / total, sem_w / total, meta_w / total
                )
            st.caption(
                f"Injury {inj_w:.0%} / Keyword {kw_w:.0%} / "
                f"Semantic {sem_w:.0%} / Meta {meta_w:.0%}"
            )

        # Injury category filter
        st.markdown("**Category Filter** *(optional)*")
        compendium_regions = None
        try:
            with open("compendium_regions.json") as _f:
                compendium_regions = json.load(_f)
        except Exception:
            pass

        selected_regions: List[str] = []
        if compendium_regions and "injury_categories" in compendium_regions:
            for cat_id, cat_data in compendium_regions["injury_categories"].items():
                with st.expander(cat_data["label"], expanded=False):
                    for subcat in cat_data["subcategories"]:
                        if st.checkbox(subcat, key=f"ai_cat_{cat_id}_{subcat}"):
                            selected_regions.append(subcat)
        else:
            st.caption("Category filter unavailable (compendium_regions.json not found)")

        show_fla = st.checkbox(
            "Show Family Law Act claims in results",
            value=False,
            key="ai_show_fla",
        )

        st.markdown("")
        search_btn = st.button(
            "Find Comparable Cases",
            type="primary",
            use_container_width=True,
            key="ai_search_btn",
        )

    # Results panel
    with res_col:
        if search_btn:
            if not injury_text.strip():
                st.warning("Please enter an injury description.")
            else:
                with st.spinner("Searching comparable cases..."):
                    search_n = num_results * 3 if not include_outliers else num_results
                    try:
                        results = search_cases(
                            injury_text,
                            selected_regions,
                            cases,
                            region_map,
                            model,
                            gender=gender if gender != "Not Specified" else None,
                            age=age,
                            top_n=search_n,
                            semantic_weight=sem_w,
                            keyword_weight=kw_w,
                            meta_weight=meta_w,
                            injury_embedding_weight=inj_w,
                        )
                    except Exception as e:
                        st.error(f"Search error: {e}")
                        results = []

                    if not include_outliers and len(results) > 4:
                        kept_ids = {
                            c.get("id")
                            for c in filter_outliers([c for c, _, _ in results])
                        }
                        results = [
                            (c, e, s) for c, e, s in results
                            if c.get("id") in kept_ids
                        ]
                    results = results[:num_results]

                st.session_state.search_results = {
                    "results":          results,
                    "injury_text":      injury_text,
                    "selected_regions": selected_regions,
                    "gender":           gender,
                    "age":              age,
                    "num_results":      num_results,
                    "timestamp":        datetime.now(),
                }
                st.session_state.dismissed_cases = set()

        if st.session_state.search_results:
            results = st.session_state.search_results["results"]
            results = [
                (c, e, s) for c, e, s in results
                if c.get("id") not in st.session_state.dismissed_cases
            ]
            if not include_outliers and len(results) > 4:
                kept_ids = {c.get("id") for c in filter_outliers([c for c, _, _ in results])}
                results = [(c, e, s) for c, e, s in results if c.get("id") in kept_ids]

            dv = [extract_damages_value(c) for c, _, _ in results]
            dv = [v for v in dv if v]
            render_stat_bar(dv, len(results))

            st.markdown("")

            if not results:
                st.info("All results have been dismissed. Run a new search to start over.")
                return

            tab_charts, tab_cases = st.tabs(["Charts", "Cases"])

            with tab_charts:
                if dv:
                    cap_fig = create_damages_cap_chart(dv, DEFAULT_REFERENCE_YEAR)
                    if cap_fig:
                        st.plotly_chart(cap_fig, use_container_width=True)
                        st.caption(
                            "Non-pecuniary awards relative to Ontario damages cap "
                            f"(inflation-adjusted to {DEFAULT_REFERENCE_YEAR})"
                        )

                    infl_fig = create_inflation_chart(results, DEFAULT_REFERENCE_YEAR)
                    if infl_fig:
                        st.plotly_chart(infl_fig, use_container_width=True)
                        st.caption(
                            f"Award timeline, all values adjusted to {DEFAULT_REFERENCE_YEAR} dollars (CPI)"
                        )
                else:
                    st.info("No award data available for charting.")

            with tab_cases:
                dismissed_count = len(st.session_state.dismissed_cases)
                if dismissed_count:
                    st.caption(f"{dismissed_count} case(s) dismissed from view")

                for idx, (case, emb_sim, score) in enumerate(results, 1):
                    ext = case.get("extended_data") or {}
                    num_p = ext.get("num_plaintiffs", 0)
                    pid_sfx = f" [P{ext.get('plaintiff_id','')}]" if num_p > 1 else ""
                    award = extract_damages_value(case)
                    award_str = f"${award:,.0f}" if award else "N/A"

                    with st.expander(
                        f"{idx}.  {case.get('case_name','Unknown')}{pid_sfx}"
                        f"   |   {award_str}"
                        f"   |   Match {score*100:.0f}%",
                        expanded=(idx <= EXPANDED_RESULTS_COUNT),
                    ):
                        dm_col, sc_col = st.columns([4, 1])

                        with dm_col:
                            meta_parts = [
                                p for p in [
                                    str(case.get("year", "")),
                                    case.get("court", ""),
                                    case.get("region", ""),
                                ]
                                if p
                            ]
                            st.caption("  &middot;  ".join(meta_parts))
                            if award:
                                st.markdown(f"**Non-Pecuniary:** ${award:,.0f}")
                            st.divider()
                            display_enhanced_data(case, show_fla=show_fla)

                        with sc_col:
                            st.metric("Match", f"{score*100:.0f}%")
                            if emb_sim:
                                st.metric("Embed", f"{emb_sim*100:.0f}%")
                            if st.button(
                                "Dismiss",
                                key=f"dismiss_{case.get('id')}_{idx}",
                                help="Hide this case from results",
                            ):
                                st.session_state.dismissed_cases.add(case.get("id"))
                                st.rerun()

            # PDF Export
            st.divider()
            st.markdown("**Export**")
            ex1, ex2 = st.columns([1, 2])
            with ex1:
                n_pdf = st.number_input(
                    "Cases to include in PDF",
                    min_value=1,
                    max_value=50,
                    value=min(10, len(results)),
                    key="ai_pdf_n",
                )
            with ex2:
                if st.button("Generate PDF Report", type="secondary", key="ai_pdf_btn"):
                    with st.spinner("Generating PDF..."):
                        try:
                            sd  = st.session_state.search_results
                            all_dv = [
                                extract_damages_value(c)
                                for c, _, _ in sd["results"]
                                if extract_damages_value(c)
                            ]
                            region_labels = {
                                rid: region_map[rid]["label"]
                                for rid in sd["selected_regions"]
                                if rid in region_map
                            }
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            pf = f"damages_report_{ts}.pdf"
                            with tempfile.TemporaryDirectory() as td:
                                pp = os.path.join(td, pf)
                                generate_damages_report(
                                    output_path=pp,
                                    selected_regions=sd["selected_regions"],
                                    region_labels=region_labels,
                                    injury_description=sd["injury_text"],
                                    results=sd["results"],
                                    damages_values=all_dv,
                                    gender=(
                                        sd["gender"]
                                        if sd["gender"] != "Not Specified"
                                        else None
                                    ),
                                    age=sd["age"],
                                    max_cases=int(n_pdf),
                                )
                                pdf_bytes = open(pp, "rb").read()
                            st.success("PDF ready to download")
                            st.download_button(
                                "Download PDF Report",
                                pdf_bytes,
                                pf,
                                "application/pdf",
                                key="ai_pdf_dl",
                            )
                        except Exception as e:
                            st.error(f"PDF generation failed: {e}")
                            st.info("Ensure reportlab is installed: pip install reportlab")
        else:
            st.markdown(
                '<div class="md-card-outlined" style="text-align:center;padding:3rem 2rem;">'
                '<div style="font-size:1rem;color:var(--md-on-surface-variant);margin-bottom:0.5rem;">'
                'Enter an injury description and click <strong>Find Comparable Cases</strong> to begin.'
                '</div>'
                '<div style="font-size:0.8125rem;color:var(--md-on-surface-variant);">'
                'Optionally upload an expert report to auto-populate injuries.'
                '</div>'
                '</div>',
                unsafe_allow_html=True,
            )


# =============================================================================
# VIEW 03 — JUDGE ANALYTICS
# =============================================================================

def render_judges() -> None:
    render_page_header(
        "03",
        "Judge Analytics",
        "Award statistics, timelines, and comparisons by presiding judge.",
    )
    display_judge_analytics_page(cases, include_outliers)


# =============================================================================
# VIEW 04 — CATEGORY ANALYTICS
# =============================================================================

def render_categories() -> None:
    render_page_header(
        "04",
        "Category Analytics",
        "Award statistics by injury category, anatomical region, and FLA relationship.",
    )
    display_category_analytics_page(cases, include_outliers)


# =============================================================================
# VIEW 05 — FLA CLAIMS
# =============================================================================

def render_fla() -> None:
    render_page_header(
        "05",
        "FLA Claims",
        "Family Law Act claims analysis: fatal injuries, dependency awards, spousal and child claims.",
    )
    display_fla_analytics_page(cases, include_outliers)


# =============================================================================
# ROUTER
# =============================================================================

_view = st.session_state.current_view

if _view == "compendium":
    render_compendium()
elif _view == "ai_search":
    render_ai_search()
elif _view == "judges":
    render_judges()
elif _view == "categories":
    render_categories()
elif _view == "fla":
    render_fla()
else:
    st.session_state.current_view = "compendium"
    st.rerun()
