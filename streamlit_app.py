"""
Ontario Damages Compendium — Legal Reference Tool

Redesigned UI v3.0: flat console aesthetic, collapsible sidebar navigation,
browsable compendium with ToC, fuzzy/boolean search, and integrated analytics.
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

APP_VERSION = "3.0.0"

if "app_version" not in st.session_state or st.session_state.app_version != APP_VERSION:
    st.cache_resource.clear()
    st.cache_data.clear()
    st.session_state.app_version = APP_VERSION

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="ON Damages Compendium",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CSS — FLAT / CONSOLE AESTHETIC
# =============================================================================

st.markdown("""
<style>
/* ─── FONTS ──────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ─── GLOBAL CHROME ──────────────────────────────────────────────────────── */
#MainMenu, footer, .stDeployButton { visibility: hidden; display: none; }

.main .block-container {
  padding: 1.25rem 2rem 2rem !important;
  max-width: 100% !important;
}

/* ─── SIDEBAR ────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: #0d1117 !important;
  border-right: 1px solid #21262d !important;
}

/* All text inside sidebar forced light */
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {
  color: #8b949e !important;
}

/* Sidebar nav buttons — full-width, flush, no rounded box */
section[data-testid="stSidebar"] .stButton > button {
  width: 100% !important;
  text-align: left !important;
  background: transparent !important;
  border: none !important;
  border-left: 2px solid transparent !important;
  border-radius: 0 !important;
  color: #8b949e !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.82rem !important;
  font-weight: 400 !important;
  padding: 0.42rem 0.9rem !important;
  margin: 0 0 1px 0 !important;
  letter-spacing: 0.01em !important;
  transition: all 0.12s ease !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .stButton > button:hover {
  background: #161b22 !important;
  border-left-color: #3b82f6 !important;
  color: #c9d1d9 !important;
}

section[data-testid="stSidebar"] .stButton > button:focus {
  box-shadow: none !important;
  outline: none !important;
}

/* Active nav item — set via CSS on the container div */
.nav-active .stButton > button {
  border-left: 2px solid #3b82f6 !important;
  color: #e6edf3 !important;
  background: #161b22 !important;
  font-weight: 600 !important;
}

/* Sidebar checkbox & radio */
section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] .stRadio label {
  font-size: 0.8rem !important;
  color: #8b949e !important;
}

section[data-testid="stSidebar"] .stExpander {
  border: 1px solid #21262d !important;
  border-radius: 3px !important;
}

/* ─── VIEW HEADERS ───────────────────────────────────────────────────────── */
.view-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.65rem;
  font-weight: 500;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #9ca3af;
  margin-bottom: 0.2rem;
}

.view-heading {
  font-size: 1.75rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  color: #111827;
  margin-bottom: 0.15rem;
  line-height: 1.2;
}

.view-sub {
  font-size: 0.85rem;
  color: #6b7280;
  margin-bottom: 1.25rem;
}

/* ─── STATS BAR ──────────────────────────────────────────────────────────── */
.stat-block {
  border: 1px solid #e5e7eb;
  padding: 0.6rem 0.9rem;
  text-align: center;
  border-radius: 3px;
  background: #fafafa;
}

.stat-val {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  font-weight: 600;
  color: #111827;
  display: block;
}

.stat-lbl {
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #9ca3af;
  display: block;
  margin-top: 0.1rem;
}

/* ─── TABLE (Compendium) ─────────────────────────────────────────────────── */
.case-table { width: 100%; border-collapse: collapse; }

.table-header-row {
  display: grid;
  grid-template-columns: 3fr 3.5rem 4.5rem 2.5fr 8rem;
  gap: 0.5rem;
  padding: 0.3rem 0.5rem 0.35rem;
  border-bottom: 2px solid #e5e7eb;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #9ca3af;
}

.case-row-grid {
  display: grid;
  grid-template-columns: 3fr 3.5rem 4.5rem 2.5fr 8rem;
  gap: 0.5rem;
  padding: 0.5rem 0.5rem;
  border-bottom: 1px solid #f3f4f6;
  font-size: 0.855rem;
  align-items: center;
  cursor: pointer;
  transition: background 0.08s;
}

.case-row-grid:hover { background: #f9fafb; }

.case-row-grid.selected {
  background: #eff6ff;
  border-left: 2px solid #3b82f6;
  padding-left: 0.3rem;
}

.cn { font-weight: 500; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cy { font-family: 'JetBrains Mono', monospace; color: #6b7280; font-size: 0.78rem; }
.cc { color: #6b7280; font-size: 0.78rem; }
.ccat { color: #6b7280; font-size: 0.78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.caw {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: #059669;
  font-size: 0.83rem;
  text-align: right;
}

/* ─── DETAIL PANEL ───────────────────────────────────────────────────────── */
.detail-panel {
  border: 1px solid #e5e7eb;
  border-left: 3px solid #3b82f6;
  padding: 1.25rem 1.5rem;
  border-radius: 0 3px 3px 0;
  background: #f8fafc;
  margin: 0.25rem 0 0.5rem 0;
}

.detail-award {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.8rem;
  font-weight: 700;
  color: #059669;
  display: block;
}

.detail-meta-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #9ca3af;
}

/* ─── TAGS ───────────────────────────────────────────────────────────────── */
.tag {
  display: inline-block;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 0.68rem;
  font-weight: 500;
  padding: 0.12rem 0.45rem;
  border-radius: 2px;
  margin: 0.1rem 0.1rem 0.1rem 0;
  letter-spacing: 0.02em;
}

.tag-green { background: #d1fae5; color: #065f46; }
.tag-gray  { background: #f3f4f6; color: #374151; }
.tag-amber { background: #fef3c7; color: #92400e; }

/* ─── RESULT CARDS (AI Search) ───────────────────────────────────────────── */
.result-card {
  border: 1px solid #e5e7eb;
  border-left: 3px solid #3b82f6;
  padding: 0.9rem 1.1rem;
  margin-bottom: 0.6rem;
  border-radius: 0 3px 3px 0;
  background: #ffffff;
}

/* ─── TOC NAVIGATION ─────────────────────────────────────────────────────── */
.toc-section-label {
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: #9ca3af;
  padding: 0.6rem 0 0.2rem 0;
  display: block;
}

/* ─── METRICS OVERRIDE ───────────────────────────────────────────────────── */
[data-testid="stMetricValue"] {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 1.3rem !important;
  font-weight: 600 !important;
}

[data-testid="stMetricLabel"] {
  font-size: 0.7rem !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: #6b7280 !important;
}

/* ─── MISC ───────────────────────────────────────────────────────────────── */
hr {
  border: none !important;
  border-top: 1px solid #f3f4f6 !important;
  margin: 0.75rem 0 !important;
}

.stExpander > summary {
  font-size: 0.88rem !important;
  font-weight: 500 !important;
}

/* ─── DARK MODE ──────────────────────────────────────────────────────────── */
@media (prefers-color-scheme: dark) {
  .view-heading { color: #f9fafb; }
  .cn { color: #f3f4f6; }
  .stat-block { background: #1f2937; border-color: #374151; }
  .stat-val { color: #f9fafb; }
  .detail-panel { background: #1e293b; border-color: #334155; }
  .result-card { background: #1e293b; border-color: #334155; }
  .table-header-row, .case-row-grid { border-color: #374151; }
  .case-row-grid:hover { background: #1f2937; }
  .case-row-grid.selected { background: #1e3a5f; }
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
    "compendium": {"icon": "⊞", "label": "Compendium",       "num": "01"},
    "ai_search":  {"icon": "◈", "label": "AI Search",         "num": "02"},
    "judges":     {"icon": "◷", "label": "Judge Analytics",   "num": "03"},
    "categories": {"icon": "◫", "label": "Category Stats",    "num": "04"},
    "fla":        {"icon": "◻", "label": "FLA Claims",        "num": "05"},
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

def display_enhanced_data(case: Dict, show_fla: bool = False) -> None:
    """Render structured case detail from extended_data."""
    ext = case.get("extended_data") or {}
    if not ext:
        return

    num_p = ext.get("num_plaintiffs", 0)
    if num_p > 1:
        st.info(f"Multi-Plaintiff Case ({num_p} plaintiffs)")

    demo = []
    if ext.get("plaintiff_id"):
        demo.append(f"Plaintiff {ext['plaintiff_id']}")
    if ext.get("sex"):
        demo.append(f"Sex: {ext['sex']}")
    if ext.get("age"):
        demo.append(f"Age at injury: {ext['age']}")
    if demo:
        st.markdown(f"**Demographics:** {'  ·  '.join(demo)}")

    injuries = ext.get("injuries") or []
    if injuries:
        st.markdown("**Injuries & Diagnoses:**")
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
        st.markdown("**Pecuniary Damages (Economic Losses):**")
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
            st.markdown("**Family Law Act Claims:**")
            for claim in fla:
                rel  = claim.get("relationship", "FLA claim")
                desc = claim.get("description", "")
                amt  = claim.get("amount")
                text = f"- {rel}" + (f" ({desc})" if desc else "")
                text += f": ${amt:,.0f}" if amt else ""
                st.markdown(text)

    cites = ext.get("citations") or []
    if cites:
        st.markdown(f"**Citation(s):** {', '.join(cites)}")

    judges = ext.get("judges") or []
    if judges:
        st.markdown(f"**Judge(s):** {', '.join(judges)}")

    if ext.get("is_provisional"):
        st.warning("Provisional damages award")

    comments = ext.get("comments") or case.get("comments") or ""
    if comments:
        st.markdown(f"**Comments:** {comments}")


def fuzzy_score(case: Dict, query: str) -> float:
    """Score a case against a free-text query. Returns 0–1."""
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
    """Category → count mapping, sorted by count desc."""
    counts: Dict[str, int] = {}
    for c in cases_list:
        for cat in get_case_categories(c):
            key = cat.upper()
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def build_toc_years(cases_list: List[Dict]) -> Dict[str, int]:
    """Decade → count mapping, sorted by decade desc."""
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

    # ── ToC filter ────────────────────────────────────────────────
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

    # ── Query filter ──────────────────────────────────────────────
    if query.strip():
        if search_mode == "fuzzy":
            scored = [(c, fuzzy_score(c, query)) for c in filtered]
            filtered = [c for c, s in scored if s >= 0.3]
            # sort by relevance; we return early here
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
                pass  # fall through with unfiltered on parse error

    # ── Sort ──────────────────────────────────────────────────────
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
    """Render a 4-column stats bar for a list of award values."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="stat-block"><span class="stat-val">{n_cases:,}</span>'
            f'<span class="stat-lbl">Cases</span></div>',
            unsafe_allow_html=True,
        )
    if values:
        median = int(np.median(values))
        lo = int(min(values))
        hi = int(max(values))
        with c2:
            st.markdown(
                f'<div class="stat-block"><span class="stat-val">${median:,}</span>'
                f'<span class="stat-lbl">Median Award</span></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div class="stat-block"><span class="stat-val">${lo:,}</span>'
                f'<span class="stat-lbl">Min Award</span></div>',
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f'<div class="stat-block"><span class="stat-val">${hi:,}</span>'
                f'<span class="stat-lbl">Max Award</span></div>',
                unsafe_allow_html=True,
            )


# =============================================================================
# SIDEBAR — NAVIGATION
# =============================================================================

with st.sidebar:
    n_cases_total = len(cases) if cases else 0

    st.markdown(
        f"""
        <div style="padding:1rem 0.75rem 0.75rem;border-bottom:1px solid #21262d;margin-bottom:0.5rem;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;
                      letter-spacing:0.22em;text-transform:uppercase;color:#484f58;
                      margin-bottom:0.25rem;">Ontario</div>
          <div style="font-size:1rem;font-weight:700;color:#e6edf3;letter-spacing:-0.01em;
                      line-height:1.2;">Damages<br>Compendium</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:0.6rem;
                      color:#484f58;margin-top:0.35rem;">v{APP_VERSION} · {n_cases_total:,} cases</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<span style="font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;'
        'color:#484f58;padding:0 0.25rem;display:block;margin-bottom:0.25rem;">Views</span>',
        unsafe_allow_html=True,
    )

    for vid in VIEWS:
        meta   = VIEW_META[vid]
        active = st.session_state.current_view == vid
        prefix = "▶" if active else "  "
        label  = f"{prefix}  {meta['icon']}  {meta['label']}"
        # Wrap in a div we can target with CSS for the active state
        if active:
            st.markdown('<div class="nav-active">', unsafe_allow_html=True)
        if st.button(label, key=f"nav_{vid}"):
            st.session_state.current_view = vid
            st.rerun()
        if active:
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        '<div style="border-top:1px solid #21262d;margin:0.75rem 0 0.5rem;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span style="font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;'
        'color:#484f58;padding:0 0.25rem;display:block;margin-bottom:0.25rem;">Settings</span>',
        unsafe_allow_html=True,
    )

    include_outliers = st.checkbox(
        "Include outliers",
        value=True,
        key="include_outliers_global",
        help="When unchecked, awards outside 1.5×IQR are excluded from analytics and AI search.",
    )

    with st.expander("CPI Data", expanded=False):
        st.caption(get_data_source())
        cpi_raw = get_cpi_data()
        buf = io.StringIO()
        buf.write("Year,CPI\n")
        for yr_k in sorted(cpi_raw.keys()):
            buf.write(f"{yr_k},{cpi_raw[yr_k]:.2f}\n")
        st.download_button(
            "↓ Download CPI CSV",
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
        '<div style="border-top:1px solid #21262d;margin-top:0.75rem;padding:0.75rem 0.5rem 0;">'
        '<span style="font-size:0.62rem;color:#484f58;line-height:1.6;display:block;">'
        "Reference only. Always verify case details<br>and consult primary sources."
        "</span></div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# VIEW 01 — COMPENDIUM BROWSER
# =============================================================================

def render_compendium() -> None:
    """Browsable compendium with ToC, fuzzy search, boolean search."""
    st.markdown('<div class="view-label">View 01</div>', unsafe_allow_html=True)
    st.markdown('<div class="view-heading">Compendium Browser</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="view-sub">'
        "Browse all cases · Fuzzy and boolean search · Navigate by category or decade"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Search controls ───────────────────────────────────────────
    sc1, sc2, sc3 = st.columns([6, 2, 2])
    with sc1:
        new_q = st.text_input(
            "search",
            value=st.session_state.comp_search,
            placeholder="Search cases, injuries, comments, citations…",
            label_visibility="collapsed",
            key="comp_q_input",
        )
        if new_q != st.session_state.comp_search:
            st.session_state.comp_search = new_q
            st.session_state.comp_page = 0

    with sc2:
        mode_idx = 0 if st.session_state.comp_search_mode == "fuzzy" else 1
        new_mode = st.selectbox(
            "mode",
            ["fuzzy", "boolean"],
            index=mode_idx,
            format_func=lambda x: "≈  Fuzzy" if x == "fuzzy" else "±  Boolean",
            label_visibility="collapsed",
            key="comp_mode_sel",
        )
        if new_mode != st.session_state.comp_search_mode:
            st.session_state.comp_search_mode = new_mode
            st.session_state.comp_page = 0

    with sc3:
        sort_opts = ["year_desc", "year_asc", "award_desc", "award_asc", "name_asc"]
        sort_labels = {
            "year_desc": "Year ↓",
            "year_asc":  "Year ↑",
            "award_desc": "Award ↓",
            "award_asc":  "Award ↑",
            "name_asc":   "Name A–Z",
        }
        cur_sort_idx = sort_opts.index(st.session_state.comp_sort) if st.session_state.comp_sort in sort_opts else 0
        new_sort = st.selectbox(
            "sort",
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
        st.caption("Boolean operators: `AND` · `OR` · `NOT` · `\"exact phrase\"`")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Layout: ToC | Cases ───────────────────────────────────────
    toc_col, main_col = st.columns([1, 4], gap="medium")

    # Build ToC data
    toc_cats  = build_toc_categories(cases)
    toc_years = build_toc_years(cases)

    with toc_col:
        st.markdown(
            '<span class="toc-section-label">Group by</span>',
            unsafe_allow_html=True,
        )
        new_grp = st.radio(
            "group",
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
            '<span class="toc-section-label">'
            + ("Categories" if new_grp == "category" else "Decades")
            + "</span>",
            unsafe_allow_html=True,
        )

        # "All" button
        all_active = st.session_state.toc_selection is None
        all_lbl = ("▶  All  " if all_active else "   All  ") + f"[{n_cases_total:,}]"
        if st.button(all_lbl, key="toc_all", use_container_width=True):
            st.session_state.toc_selection = None
            st.session_state.comp_page = 0
            st.rerun()

        groups = toc_cats if new_grp == "category" else toc_years
        for grp_label, grp_count in groups.items():
            is_active = st.session_state.toc_selection == grp_label
            btn_lbl = ("▶  " if is_active else "   ") + grp_label + f"  [{grp_count}]"
            if st.button(btn_lbl, key=f"toc_{grp_label}", use_container_width=True):
                if is_active:
                    st.session_state.toc_selection = None
                else:
                    st.session_state.toc_selection = grp_label
                st.session_state.comp_page = 0
                st.rerun()

    # ── Main case list ────────────────────────────────────────────
    with main_col:
        # Apply filters
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

        # Stats bar
        award_vals = [extract_damages_value(c) for c in filtered]
        award_vals = [a for a in award_vals if a]
        render_stat_bar(award_vals, len(filtered))

        st.markdown("<br>", unsafe_allow_html=True)

        if not filtered:
            st.info("No cases match the current filters. Try broadening your search or clearing the ToC selection.")
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
            '<div class="table-header-row">'
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
            year  = str(case.get("year", "—"))
            court = case.get("court", "—")
            cats  = get_case_categories(case)
            cat   = cats[0] if cats else "—"
            award = extract_damages_value(case)
            award_str = f"${award:,.0f}" if award else "—"
            selected  = st.session_state.comp_selected_case_id == cid
            sel_class = " selected" if selected else ""

            # Row HTML (visual only — click handled by button below)
            st.markdown(
                f'<div class="case-row-grid{sel_class}">'
                f'<span class="cn">{name}</span>'
                f'<span class="cy">{year}</span>'
                f'<span class="cc">{court}</span>'
                f'<span class="ccat">{cat}</span>'
                f'<span class="caw">{award_str}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

            # Thin button row below the HTML row (expand/collapse)
            btn_label = "▲ Close" if selected else "▼ View"
            if st.button(btn_label, key=f"open_{cid}", help=f"Toggle detail for {name}"):
                st.session_state.comp_selected_case_id = None if selected else cid
                st.rerun()

            # Inline detail panel
            if selected:
                with st.container():
                    st.markdown('<div class="detail-panel">', unsafe_allow_html=True)
                    h1, h2 = st.columns([3, 1])
                    with h1:
                        st.markdown(f"#### {name}")
                        meta_parts = [p for p in [year, court, case.get("citation", "")] if p and p != "—"]
                        st.caption("  ·  ".join(meta_parts))
                    with h2:
                        if award:
                            st.markdown(
                                f'<span class="detail-award">${award:,.0f}</span>'
                                f'<span class="detail-meta-label">Non-Pecuniary Award</span>',
                                unsafe_allow_html=True,
                            )
                    st.markdown("---")
                    display_enhanced_data(case, show_fla=True)
                    st.markdown("</div>", unsafe_allow_html=True)

        # Pagination controls
        if total_pages > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            pg1, pg2, pg3 = st.columns([1, 3, 1])
            with pg1:
                if page > 0 and st.button("← Prev", key="pg_prev"):
                    st.session_state.comp_page -= 1
                    st.rerun()
            with pg2:
                range_start = start + 1
                range_end = min(start + PAGE_SIZE, len(filtered))
                st.markdown(
                    f'<div style="text-align:center;font-size:0.78rem;color:#6b7280;padding-top:0.4rem;">'
                    f"Showing {range_start}–{range_end} of {len(filtered):,} · "
                    f"Page {page+1} of {total_pages}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with pg3:
                if page < total_pages - 1 and st.button("Next →", key="pg_next"):
                    st.session_state.comp_page += 1
                    st.rerun()


# =============================================================================
# VIEW 02 — AI SEARCH
# =============================================================================

def render_ai_search() -> None:
    """Semantic AI search with expert report upload and PDF export."""
    st.markdown('<div class="view-label">View 02</div>', unsafe_allow_html=True)
    st.markdown('<div class="view-heading">AI Search</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="view-sub">'
        "Hybrid semantic search — injury embeddings · BM25 keywords · metadata matching"
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Two-panel layout: controls | results ──────────────────────
    ctrl_col, res_col = st.columns([1, 3], gap="large")

    with ctrl_col:
        # Expert report upload
        with st.expander("Upload Expert Report  (optional)", expanded=False):
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
                with st.spinner("Analyzing report…"):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    try:
                        analysis = analyze_expert_report(tmp_path, use_llm=use_llm)
                        st.session_state.analysis_data = analysis
                        st.success("Report analyzed — injury description updated below.")
                        detected = analysis.get("injured_regions", [])
                        if detected:
                            st.write("**Detected regions:**")
                            for rid in detected:
                                if rid in region_map:
                                    st.write(f"  · {region_map[rid]['label']}")
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

        st.markdown("**Demographics**  *(optional)*")
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
                "Balanced: general-purpose · Medical: specific diagnoses · "
                "Symptom/Impact: functional limitations · Custom: set weights manually"
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
                f"Injury {inj_w:.0%} · Keyword {kw_w:.0%} · "
                f"Semantic {sem_w:.0%} · Meta {meta_w:.0%}"
            )

        # Injury category filter
        st.markdown("**Category Filter**  *(optional — narrows search to selected regions)*")
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
            st.caption("compendium_regions.json not found — category filter unavailable")

        show_fla = st.checkbox(
            "Show Family Law Act claims in results",
            value=False,
            key="ai_show_fla",
        )

        st.markdown("<br>", unsafe_allow_html=True)
        search_btn = st.button(
            "Find Comparable Cases",
            type="primary",
            use_container_width=True,
            key="ai_search_btn",
        )

    # ── Results panel ─────────────────────────────────────────────
    with res_col:
        if search_btn:
            if not injury_text.strip():
                st.warning("Please enter an injury description.")
            else:
                with st.spinner("Searching comparable cases…"):
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

            # Stats bar
            dv = [extract_damages_value(c) for c, _, _ in results]
            dv = [v for v in dv if v]
            render_stat_bar(dv, len(results))

            st.markdown("<br>", unsafe_allow_html=True)

            if not results:
                st.info("All results have been dismissed. Run a new search to start over.")
                return

            # Tabs: Charts | Cases
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
                            f"Award timeline — all values adjusted to {DEFAULT_REFERENCE_YEAR} dollars (CPI)"
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
                        f"   ·   {award_str}"
                        f"   ·   Match {score*100:.0f}%",
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
                            st.caption("  ·  ".join(meta_parts))
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
                    with st.spinner("Generating PDF…"):
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
            st.info(
                "Enter an injury description in the left panel and click "
                "**Find Comparable Cases** to begin."
            )


# =============================================================================
# VIEW 03 — JUDGE ANALYTICS
# =============================================================================

def render_judges() -> None:
    st.markdown('<div class="view-label">View 03</div>', unsafe_allow_html=True)
    st.markdown('<div class="view-heading">Judge Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="view-sub">'
        "Award statistics, timelines, and comparisons by presiding judge"
        "</div>",
        unsafe_allow_html=True,
    )
    display_judge_analytics_page(cases, include_outliers)


# =============================================================================
# VIEW 04 — CATEGORY ANALYTICS
# =============================================================================

def render_categories() -> None:
    st.markdown('<div class="view-label">View 04</div>', unsafe_allow_html=True)
    st.markdown('<div class="view-heading">Category Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="view-sub">'
        "Award statistics by injury category, anatomical region, and FLA relationship"
        "</div>",
        unsafe_allow_html=True,
    )
    display_category_analytics_page(cases, include_outliers)


# =============================================================================
# VIEW 05 — FLA CLAIMS
# =============================================================================

def render_fla() -> None:
    st.markdown('<div class="view-label">View 05</div>', unsafe_allow_html=True)
    st.markdown('<div class="view-heading">FLA Claims</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="view-sub">'
        "Family Law Act claims — fatal injuries, dependency awards, spousal and child claims"
        "</div>",
        unsafe_allow_html=True,
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
    # Fallback — shouldn't happen
    st.session_state.current_view = "compendium"
    st.rerun()
