import streamlit as st
import streamlit.components.v1 as components
import html
import time
from backend import (
    AudioRecorder, STTEngine, MeetingSummarizer,
    save_to_md, send_email_func, SOUNDDEVICE_AVAILABLE,
    audio_has_speech,
)
from audio_recorder_streamlit import audio_recorder

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1 — SECURITY: server-owned key, never rendered to the page
# ─────────────────────────────────────────────────────────────────────────────
def _load_groq_key() -> str:
    """
    Read GROQ_API_KEY exclusively from st.secrets (server side).
    The value is NEVER injected into any UI widget — not as a default,
    not as a placeholder, not as a pre-filled value.
    """
    try:
        return st.secrets["GROQ_API_KEY"]
    except (KeyError, FileNotFoundError):
        return ""

_GROQ_KEY: str = _load_groq_key()

# Safety assertion: if the key somehow ends up being non-string it means
# something in the secrets file is misconfigured — catch it before any widget
# renders, and never surface the key value in the message.
assert isinstance(_GROQ_KEY, str), (
    "GROQ_API_KEY in st.secrets must be a plain string."
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Live Meeting Intelligence",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
# Palette
#   #0d0f14  — near-black base (blue-undertone, not flat grey)
#   #141720  — elevated surface / card
#   #1a1f2e  — raised surface / inputs
#   #1f2535  — border / divider
#   #7c6ef2  — violet-indigo accent  (distinct from overused teal/cyan)
#   #6254c8  — accent pressed/hover
#   #e8eaf0  — primary text
#   #94a3b8  — secondary text
#   #6b7280  — muted / placeholder
#   #374151  — very muted / empty state
#   #34d399  — success / connected (emerald)
#   #f87171  — danger / recording
#   #fbbf24  — warning / processing
#
# Typography
#   Headings  → Inter 700/600  (clean, modern, professional)
#   Body      → Inter 400/500
#   Transcript→ IBM Plex Mono 400  (legible at length, clearly distinct from UI)
#
# Background
#   Pure CSS radial mesh — no stock photo, no visual noise
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ── BASE ──────────────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; }

html, body, .stApp {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
}

/* BACKGROUND: asymmetric electric-blue mesh, DESIGN_VARIANCE 8
   Dominant ellipse top-left (asymmetric visual weight).
   Hardware-accelerated: no transforms on scroll, pointer-events-none implied. */
.stApp {
    background-color: #0c0e12;
    background-image:
        radial-gradient(ellipse 70% 50% at -5% -5%,   rgba(29,155,240,0.065) 0%, transparent 60%),
        radial-gradient(ellipse 50% 40% at 105% 110%,  rgba(29,155,240,0.04)  0%, transparent 55%),
        radial-gradient(ellipse 40% 30% at 55% 50%,    rgba(12,14,20,0.62)    0%, transparent 70%);
    color: #f0f2f5;
}

/* ── STREAMLIT CHROME & SIDEBAR ───────────────────────────────────────────── */
#MainMenu                      { visibility: hidden; }
footer                         { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; }
.stDeployButton                { display: none !important; }
div[data-testid="stDecoration"]{ display: none !important; }

/* PERMANENT SIDEBAR — desktop only (≥769px): pinned to left, never collapsed.
   On mobile (≤768px) these rules DO NOT apply, so Streamlit's native
   collapsible sidebar drawer and toggle arrow work normally. */
@media (min-width: 769px) {
    section[data-testid="stSidebar"] {
        display: flex !important;
        visibility: visible !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        bottom: 0 !important;
        width: 280px !important;
        min-width: 280px !important;
        transform: none !important;
        margin-left: 0 !important;
        z-index: 100 !important;
        background-color: #09090c !important;
        border-right: 1px solid #202530 !important;
    }
    /* Adjust main app container padding to account for pinned 280px sidebar */
    .stApp > div:first-child {
        margin-left: 280px !important;
    }
}
/* Bottom-right Streamlit "running" spinner badge */
div[data-testid="stStatusWidget"] { display: none !important; }

/* ── SIDEBAR ─────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #09090c;
    border-right: 1px solid #202530;
}
section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2 {
    color: #f0f2f5 !important; font-size: 0.9rem !important; font-weight: 600 !important;
    letter-spacing: 0 !important; text-transform: none !important;
}
section[data-testid="stSidebar"] h3 {
    color: #4b5563 !important; font-size: 0.65rem !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: 0.1em !important;
}

/* ── BLOCK CONTAINER ─────────────────────────────────────────────────────── */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1360px;
}

/* TYPOGRAPHY: Outfit for UI (anti-Inter rule), DESIGN_VARIANCE 8 left-weighted */
.lmi-title {
    font-family: 'Outfit', system-ui, sans-serif;
    font-size: clamp(1.6rem, 3.8vw, 2.5rem);
    font-weight: 700;
    color: #f0f2f5;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin-left: -0.05em;
}
.lmi-title-accent { color: #1d9bf0; }  /* single electric-blue accent, LILA BAN */

.lmi-subtitle {
    font-size: 0.8rem;
    color: #4b5563;
    font-weight: 400;
    letter-spacing: 0.01em;
    margin-top: 0.4rem;
    padding-left: 0.15em;
}

h2 {
    font-family: 'Outfit', sans-serif !important;
    color: #4b5563 !important; font-size: 0.68rem !important; font-weight: 600 !important;
    text-transform: uppercase !important; letter-spacing: 0.12em !important;
    margin-bottom: 0.8rem !important;
}
h3 { color: #8b95a5 !important; font-size: 0.88rem !important; }

/* ── STATUS BADGE ────────────────────────────────────────────────────────── */
.lmi-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    padding: 0.3rem 0.8rem; border-radius: 999px;
    font-family: 'Outfit', sans-serif; font-size: 0.68rem; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase; border: 1px solid; white-space: nowrap;
}
.lmi-badge-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

/* MOTION_INTENSITY 6: perpetual micro-animation per state, no generic badge-pulse */
.badge-ready .lmi-badge-dot      { animation: dot-breathe 2.8s ease-in-out infinite; }
.badge-recording .lmi-badge-dot  { animation: dot-rec     0.9s ease-in-out infinite; }
.badge-processing .lmi-badge-dot { animation: dot-spin    1.2s linear     infinite; border-radius: 2px; }

@keyframes dot-breathe { 0%,100%{transform:scale(1);    opacity:1;  } 50%{transform:scale(1.45);opacity:0.65;} }
@keyframes dot-rec     { 0%,100%{transform:scale(1);    opacity:1;  } 50%{transform:scale(0.5); opacity:0.3; } }
@keyframes dot-spin    { from{transform:rotate(0deg);}  to{transform:rotate(360deg);} }

.badge-ready      { background:rgba(35,195,126,0.07);  border-color:rgba(35,195,126,0.22);  color:#23c37e; }
.badge-recording  { background:rgba(229,83,75,0.09);   border-color:rgba(229,83,75,0.28);   color:#e5534b; }
.badge-processing { background:rgba(229,164,75,0.08);  border-color:rgba(229,164,75,0.25);  color:#e5a44b; }
.badge-error      { background:rgba(229,83,75,0.07);   border-color:rgba(229,83,75,0.22);   color:#e5534b; }

/* ── CARDS / BORDERED CONTAINERS ─────────────────────────────────────────── */
/* CARDS: Liquid Glass — 1px inner border + inset highlight, hue-tinted shadow */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #131518 !important;
    border: 1px solid #202530 !important;
    border-radius: 12px !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.05),
        inset 0 0 0 1px rgba(255,255,255,0.02),
        0 4px 24px rgba(0,5,18,0.30) !important;
}

/* ── TEXT AREA — transcript ──────────────────────────────────────────────── */
/* TEXT AREA: Geist Mono per TECHNICAL UI RULE, optimised for long reading */
.stTextArea textarea {
    background-color: #0c0e12 !important;
    color: #ffffff !important;
    border: 1px solid #202530 !important;
    border-radius: 10px !important;
    font-family: 'Geist Mono', 'Menlo', 'Consolas', monospace !important;
    font-size: 0.78rem !important;
    line-height: 1.82 !important;
    padding: 1rem 1.2rem !important;
    letter-spacing: 0.012em !important;
    resize: vertical;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.stTextArea textarea:focus {
    border-color: #1d9bf0 !important;
    box-shadow: 0 0 0 2px rgba(29,155,240,0.14) !important;
    outline: none !important;
}
.stTextArea textarea::placeholder { color: #2d3340 !important; font-style: italic; }
/* Hide the auto-label Streamlit adds */
.stTextArea > label { display: none !important; }

/* ── TEXT INPUTS (email / sidebar) ──────────────────────────────────────── */
.stTextInput input {
    background: #131518 !important;
    color: #f0f2f5 !important;
    border: 1px solid #202530 !important;
    border-radius: 8px !important;
    font-size: 0.84rem !important;
    font-family: 'Outfit', sans-serif !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.stTextInput input:focus {
    border-color: #1d9bf0 !important;
    box-shadow: 0 0 0 2px rgba(29,155,240,0.14) !important;
}

/* BUTTONS: flat electric blue, liquid-glass inset, no gradient (LILA BAN) */
button[kind="primary"] {
    background: #1d9bf0 !important;
    border: 1px solid rgba(29,155,240,0.5) !important;
    color: #fff !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border-radius: 10px !important;
    letter-spacing: 0.01em !important;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.14),
        0 4px 14px rgba(29,155,240,0.22) !important;
    transition:
        transform 0.12s cubic-bezier(0.34,1.56,0.64,1),
        box-shadow 0.15s ease, background 0.15s ease !important;
}
button[kind="primary"]:hover {
    background: #2aa8ff !important;
    box-shadow: 0 6px 22px rgba(29,155,240,0.38) !important;
    transform: translateY(-1px) !important;
}
button[kind="primary"]:active {
    transform: scale(0.98) translateY(0) !important;
    box-shadow: 0 2px 8px rgba(29,155,240,0.16) !important;
}

button[kind="secondary"] {
    background: #191c22 !important;
    color: #8b95a5 !important;
    border: 1px solid #202530 !important;
    border-radius: 10px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03) !important;
    transition: all 0.12s ease !important;
}
button[kind="secondary"]:hover { background:#232830 !important; color:#f0f2f5 !important; border-color:#3d4757 !important; }
button[kind="secondary"]:active { transform: scale(0.98) !important; }

.lmi-record-wrap button { min-height: 52px !important; font-size: 0.9rem !important; }

/* ── RADIO ───────────────────────────────────────────────────────────────── */
.stRadio > label { color:#4b5563 !important; font-size:0.68rem !important; font-weight:600 !important; text-transform:uppercase !important; letter-spacing:0.1em !important; }
.stRadio [data-baseweb="radio"] > div:first-child { border-color: #3d4757 !important; }

/* ── TABS ─────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #131518 !important; border: 1px solid #202530 !important;
    border-radius: 10px !important; padding: 0.2rem !important; gap: 0.15rem !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important; color: #4b5563 !important;
    border-radius: 8px !important; border: none !important;
    font-family: 'Outfit', sans-serif !important; font-size: 0.8rem !important;
    font-weight: 500 !important; letter-spacing: 0.01em !important; padding: 0.38rem 1rem !important;
    transition: color 0.15s ease !important;
}
.stTabs [aria-selected="true"] {
    background: #1d9bf0 !important; color: #fff !important; font-weight: 600 !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.15) !important;
}
.stTabs [data-baseweb="tab-panel"] {
    background: #131518 !important; border: 1px solid #202530 !important;
    border-top: none !important; border-radius: 0 0 10px 10px !important;
    padding: 1.25rem !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.02) !important;
}

/* ── ALERTS ──────────────────────────────────────────────────────────────── */
.stAlert { border-radius: 10px !important; }

/* ── EXPANDER ────────────────────────────────────────────────────────────── */
details { background: #0c0e12 !important; border: 1px solid #202530 !important; border-radius: 8px !important; }
details summary { color: #4b5563 !important; font-size: 0.82rem !important; padding: 0.6rem 0.75rem !important; }

hr { border-color: #202530 !important; margin: 1.5rem 0 !important; }

/* SPINNER: electric blue, overrides any purple */
.stSpinner > div { border-top-color: #1d9bf0 !important; }

/* SKELETON LOADER: matches layout sizes, not generic circular spinner */
@keyframes shimmer {
    0%   { background-position: -600px 0; }
    100% { background-position:  600px 0; }
}
.lmi-skeleton-block {
    height: 11px; margin-bottom: 9px; border-radius: 6px;
    background: linear-gradient(90deg, #191c22 25%, #232830 50%, #191c22 75%);
    background-size: 600px 100%;
    animation: shimmer 1.6s ease-in-out infinite;
}
.lmi-skeleton-block.wide  { width: 82%; }
.lmi-skeleton-block.med   { width: 60%; }
.lmi-skeleton-block.short { width: 38%; }

/* ── EMPTY STATE ─────────────────────────────────────────────────────────── */
/* EMPTY STATES: beautifully composed with SVG icons (ANTI-EMOJI POLICY) */
.lmi-empty {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    gap: 0.65rem; text-align: center;
    background: #0c0e12; border: 1px dashed #202530; border-radius: 10px;
}
.lmi-empty-icon { opacity: 0.22; line-height: 1; }
.lmi-empty-icon svg { width: 36px; height: 36px; stroke: #8b95a5; fill: none; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
.lmi-empty-label { font-size: 0.82rem; color: #3d4757; line-height: 1.55; font-family: 'Outfit', sans-serif; }
.lmi-empty-hint  { font-size: 0.7rem;  color: #2d3340; margin-top: 0.1rem; }

/* ── STAT PILL ───────────────────────────────────────────────────────────── */
.lmi-stat-row { display: flex; gap: 0.65rem; margin-top: 0.5rem; }
.lmi-stat {
    flex: 1; background: #131518; border: 1px solid #202530; border-radius: 8px;
    padding: 0.6rem 0.5rem; text-align: center;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}
.lmi-stat-val  { font-size: 1.2rem; font-weight: 700; color: #1d9bf0; font-family: 'Outfit', sans-serif; line-height: 1; letter-spacing: -0.02em; }
.lmi-stat-label{ font-size: 0.6rem; color: #4b5563; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.25rem; }

/* ── SUMMARY OUTPUT ──────────────────────────────────────────────────────── */
.lmi-summary {
    background: #0c0e12; border: 1px solid #202530; border-radius: 10px;
    padding: 1.25rem 1.5rem; margin-top: 0.75rem;
    color: #b8c4d0; font-size: 0.875rem; line-height: 1.75; font-family: 'Outfit', sans-serif;
}
.lmi-summary h2 {
    font-family: 'Outfit', sans-serif !important; color: #f0f2f5 !important;
    font-size: 0.95rem !important; font-weight: 600 !important;
    text-transform: none !important; letter-spacing: 0 !important; margin-bottom: 0.75rem !important;
}

.lmi-version { font-size: 0.65rem; color: #2d3340; text-align: center; letter-spacing: 0.06em; padding-top: 0.5rem; }

/* MOBILE: full responsive overhaul at ≤768px
   — Sidebar reverts to Streamlit's native collapsible drawer
   — Main content reclaims full viewport width
   — Two-column layout stacks vertically
   — Title and badge scale down for readability */
@media (max-width: 768px) {
    /* ── Show Streamlit header on mobile for sidebar toggle arrow ── */
    header[data-testid="stHeader"] {
        display: flex !important;
        background: transparent !important;
        height: 2.5rem !important;
    }
    /* Style the mobile sidebar drawer */
    section[data-testid="stSidebar"] {
        max-width: 85vw !important;
        background-color: #09090c !important;
        border-right: 1px solid #202530 !important;
    }

    /* ── Typography scale-down ── */
    .lmi-title {
        font-size: clamp(1.15rem, 5vw, 1.6rem) !important;
        letter-spacing: -0.02em;
    }
    .lmi-subtitle {
        font-size: 0.7rem !important;
    }

    /* ── Block container padding ── */
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 1rem !important;
    }

    /* ── Force columns to stack vertically ── */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: column !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    /* ── Badge (status pill) — shrink so it doesn't clip ── */
    .lmi-badge {
        font-size: 0.58rem !important;
        padding: 0.2rem 0.55rem !important;
    }

    /* ── Bigger touch targets ── */
    .lmi-record-wrap button {
        min-height: 56px !important;
        font-size: 0.95rem !important;
    }
    button[kind="primary"],
    button[kind="secondary"] {
        min-height: 44px !important;
    }

    /* ── Stat pills: allow wrapping ── */
    .lmi-stat-row {
        flex-wrap: wrap !important;
    }
    .lmi-stat {
        min-width: 80px !important;
    }

    /* ── Simplified background for performance on mobile GPUs ── */
    .stApp {
        background-image: radial-gradient(ellipse 100% 35% at 50% 0%,
            rgba(29,155,240,0.04) 0%, transparent 55%) !important;
    }

    /* ── Export tab columns: stack ── */
    .lmi-empty { padding: 1.5rem 0.75rem !important; }

    /* ── Waveform: reduce height on small screens ── */
    iframe { max-height: 80px !important; }
}
</style>
""", unsafe_allow_html=True)

# ── DYNAMIC THEME ENGINE (Dark / Light / System) ────────────────────────────
_curr_theme = st.session_state.get("theme_mode", "🌙 Dark")

_light_styles = """
.stApp {
    background-color: #f8fafc !important;
    background-image: radial-gradient(ellipse 70% 50% at -5% -5%, rgba(29,155,240,0.08) 0%, transparent 60%) !important;
    color: #000000 !important;
}
section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] p {
    color: #0f172a !important;
}
.lmi-title { color: #0f172a !important; }
.lmi-subtitle { color: #475569 !important; }
.stTextArea textarea,
.stTextArea textarea:disabled,
.stTextArea textarea[disabled] {
    background-color: #ffffff !important;
    color: #000000 !important;
    -webkit-text-fill-color: #000000 !important;
    border-color: #cbd5e1 !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}
.stTextInput input {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border-color: #cbd5e1 !important;
}
button[kind="secondary"] {
    background: #f1f5f9 !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
}
.lmi-stat { background: #ffffff !important; border-color: #e2e8f0 !important; }
.lmi-stat-label { color: #64748b !important; }
.lmi-summary { background: #ffffff !important; border-color: #e2e8f0 !important; color: #0f172a !important; }
.lmi-empty { background: #ffffff !important; border-color: #cbd5e1 !important; }
.lmi-empty-label { color: #475569 !important; }
.stTabs [data-baseweb="tab-list"] { background: #f1f5f9 !important; border-color: #cbd5e1 !important; }
.stTabs [data-baseweb="tab"] { color: #64748b !important; }
.stTabs [data-baseweb="tab-panel"] { background: #ffffff !important; border-color: #e2e8f0 !important; }
details { background: #ffffff !important; border-color: #cbd5e1 !important; }
details summary { color: #0f172a !important; }
.lmi-status-ok { color: #059669 !important; font-weight: 600 !important; }
"""

_dark_styles = """
.stApp {
    background-color: #0c0e12 !important;
    color: #ffffff !important;
}
section[data-testid="stSidebar"] {
    background-color: #09090c !important;
    border-right: 1px solid #202530 !important;
}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] p {
    color: #f0f2f5 !important;
}
.lmi-title { color: #f0f2f5 !important; }
.lmi-subtitle { color: #8b95a5 !important; }
.stTextArea textarea,
.stTextArea textarea:disabled,
.stTextArea textarea[disabled] {
    background-color: #0c0e12 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: #202530 !important;
    font-weight: 500 !important;
    opacity: 1 !important;
}
.stTextInput input {
    background-color: #131518 !important;
    color: #f0f2f5 !important;
    border-color: #202530 !important;
}
button[kind="secondary"] {
    background: #191c22 !important;
    color: #8b95a5 !important;
    border: 1px solid #202530 !important;
}
.lmi-stat { background: #131518 !important; border-color: #202530 !important; }
.lmi-stat-label { color: #4b5563 !important; }
.lmi-summary { background: #0c0e12 !important; border-color: #202530 !important; color: #f0f2f5 !important; }
.lmi-empty { background: #0c0e12 !important; border-color: #202530 !important; }
.lmi-empty-label { color: #3d4757 !important; }
.stTabs [data-baseweb="tab-list"] { background: #131518 !important; border-color: #202530 !important; }
.stTabs [data-baseweb="tab"] { color: #4b5563 !important; }
.stTabs [data-baseweb="tab-panel"] { background: #131518 !important; border-color: #202530 !important; }
details { background: #0c0e12 !important; border-color: #202530 !important; }
details summary { color: #4b5563 !important; }
.lmi-status-ok { color: #34d399 !important; font-weight: 600 !important; }

/* ── Contrast boost: lift dim secondary text so it is readable on dark ── */
.lmi-subtitle    { color: #b4bdca !important; }
.lmi-stat-label  { color: #9aa4b2 !important; }
.lmi-empty-label { color: #cbd2dd !important; }
.lmi-empty-hint  { color: #8b94a2 !important; }
.lmi-version     { color: #7c8494 !important; }
.stTabs [data-baseweb="tab"] { color: #9aa4b2 !important; }
details summary  { color: #cbd2dd !important; }
button[kind="secondary"] { color: #cbd2dd !important; }

/* Streamlit widget labels, radio options, captions, placeholders */
[data-testid="stWidgetLabel"] p,
.stRadio label p,
.stRadio label {
    color: #cbd2dd !important;
}
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    color: #9aa4b2 !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #8b94a2 !important;
    opacity: 1 !important;
}

/* Override too-dim inline colors used in custom markdown (dark mode only) */
.stApp [style*="color:#4b5563"] { color: #9aa4b2 !important; }
.stApp [style*="color:#6b7280"] { color: #a1abb9 !important; }
.stApp [style*="color:#3d4757"] { color: #8b94a2 !important; }
.stApp [style*="color:#2d3340"] { color: #7c8494 !important; }
"""

if "Light" in _curr_theme:
    st.markdown(f"<style>{_light_styles}</style>", unsafe_allow_html=True)
else:
    st.markdown(f"<style>{_dark_styles}</style>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# LIVE WAVEFORM COMPONENT  (components.html iframe — no external deps)
# ─────────────────────────────────────────────────────────────────────────────
# Native-phone-recorder idiom: mirrored vertical bars scrolling right→left,
# heights driven by real mic amplitude via Web Audio API (getUserMedia +
# AnalyserNode + requestAnimationFrame, throttled to 30 fps).
#
# States   idle      → flat resting bars (#2d3340), no loop running
#          waiting   → gentle low shimmer + "waiting for microphone" caption
#          live      → real amplitude, silence settles low (attack/decay smoothing)
#          fallback  → synthetic pulse tied to recording state only (getUserMedia
#                      blocked/unsupported) — never an alarming error
#
# Modes    server    → driven by Python st.session_state.is_recording
#          browser   → self-detects the sibling audio_recorder iframe's
#                      recording color (same-origin poll, try/catch-guarded;
#                      inaccessible ⇒ stays idle gracefully)
#
# Perf     30 fps cap · one RMS calc per frame · loop fully cancelled on stop,
#          on tab hide (visibilitychange) and on pagehide · mic tracks stopped
#          and AudioContext closed the instant recording ends.
#
# NOTE: html string must stay byte-identical per (state, mode) — the server-mode
# 50 ms rerun loop relies on Streamlit not remounting an unchanged iframe.
# ─────────────────────────────────────────────────────────────────────────────
_WAVEFORM_TPL = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:transparent;overflow:hidden;}
  canvas{display:block;width:100%;height:64px;}
  #cap{font:600 9.5px system-ui,-apple-system,sans-serif;letter-spacing:.09em;
       text-transform:uppercase;color:#8b95a5;text-align:center;height:14px;
       line-height:14px;margin-top:4px;user-select:none;}
</style></head>
<body><canvas id="wf"></canvas><div id="cap"></div>
<script>
(function(){
  var MODE="__MODE__", PYSTATE="__STATE__";
  var ACCENT="#1d9bf0", REST="#2d3340";
  var canvas=document.getElementById('wf'), cap=document.getElementById('cap');
  var ctx=canvas.getContext('2d');
  var W=0, H=64, dpr=Math.min(window.devicePixelRatio||1,2);
  var BAR=3, GAP=3, STEP=BAR+GAP, nBars=0;
  var levels=[], cur=0;
  var uiState='idle';                    /* idle|waiting|live|fallback */
  var raf=null, last=0, FRAME=1000/30, pushTick=0, poll=null;
  var stream=null, actx=null, analyser=null, buf=null;
  var reduced=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;

  function resize(){
    W=canvas.clientWidth;
    canvas.width=W*dpr; canvas.height=H*dpr;
    ctx.setTransform(dpr,0,0,dpr,0,0);
    nBars=Math.max(12,Math.floor(W/STEP));
    while(levels.length<nBars)levels.unshift(0);
    if(levels.length>nBars)levels=levels.slice(levels.length-nBars);
    if(!raf)paint();
  }
  if(window.ResizeObserver)new ResizeObserver(resize).observe(canvas);

  function bar(x,lvl,color,alpha){
    var h=Math.max(2,lvl*(H-8)), y=(H-h)/2;
    ctx.globalAlpha=alpha; ctx.fillStyle=color;
    if(ctx.roundRect){ctx.beginPath();ctx.roundRect(x,y,BAR,h,1.5);ctx.fill();}
    else ctx.fillRect(x,y,BAR,h);
  }
  function paint(){
    ctx.clearRect(0,0,W,H);
    var active=(uiState==='live'||uiState==='fallback'||uiState==='waiting');
    for(var i=0;i<nBars;i++){
      var x=W-((nBars-i)*STEP);
      var a=active?(0.35+0.65*(i/(nBars-1||1))):1;
      bar(x,levels[i]||0,active?ACCENT:REST,a);
    }
    ctx.globalAlpha=1;
  }
  function frame(t){
    raf=requestAnimationFrame(frame);
    if(t-last<FRAME)return;                       /* 30 fps throttle */
    last=t;
    var target=0;
    if(uiState==='live'&&analyser){
      analyser.getByteTimeDomainData(buf);
      var sum=0;
      for(var i=0;i<buf.length;i+=2){var v=(buf[i]-128)/128;sum+=v*v;}
      target=Math.min(1,Math.sqrt(sum/(buf.length/2))*2.6);
    }else if(uiState==='fallback'){
      target=0.16+0.13*Math.sin(t*0.005)+0.05*Math.sin(t*0.013);
    }else if(uiState==='waiting'){
      target=0.06+0.05*Math.sin(t*0.006);
    }
    /* fast attack, slow decay — silence settles low, never freezes */
    cur+=(target-cur)*(target>cur?0.55:0.18);
    if(reduced){
      /* prefers-reduced-motion: level meter without lateral scroll */
      for(var j=0;j<nBars;j++)levels[j]=cur*(0.55+0.45*Math.sin(j*0.9));
    }else{
      pushTick++;
      if(pushTick>=2){pushTick=0;levels.push(cur);if(levels.length>nBars)levels.shift();}
    }
    paint();
  }
  function startLoop(){if(!raf){last=0;raf=requestAnimationFrame(frame);}}
  function stopLoop(){if(raf){cancelAnimationFrame(raf);raf=null;}}
  function setCap(t){cap.textContent=t;}

  function startLive(){
    if(uiState==='live'||uiState==='waiting')return;
    uiState='waiting'; setCap('waiting for microphone'); startLoop();
    if(!(navigator.mediaDevices&&navigator.mediaDevices.getUserMedia)){
      uiState='fallback'; setCap(''); return;
    }
    navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){
      if(uiState!=='waiting'){s.getTracks().forEach(function(t){t.stop();});return;}
      stream=s;
      var AC=window.AudioContext||window.webkitAudioContext;
      actx=new AC();
      analyser=actx.createAnalyser();
      analyser.fftSize=1024;
      buf=new Uint8Array(analyser.fftSize);
      actx.createMediaStreamSource(s).connect(analyser);
      uiState='live'; setCap('');
    }).catch(function(){
      if(uiState==='waiting'){uiState='fallback';setCap('');}
    });
  }
  function stopLive(){
    stopLoop();
    if(stream){stream.getTracks().forEach(function(t){t.stop();});stream=null;}
    if(actx){try{actx.close();}catch(e){} actx=null;}
    analyser=null; buf=null; cur=0;
    for(var i=0;i<levels.length;i++)levels[i]=0;
    uiState='idle'; setCap(''); paint();
  }

  /* battery: never draw while hidden */
  document.addEventListener('visibilitychange',function(){
    if(document.hidden)stopLoop();
    else if(uiState!=='idle')startLoop();
  });
  window.addEventListener('pagehide',function(){
    stopLive(); if(poll){clearInterval(poll);poll=null;}
  });

  /* browser mode: poll the sibling audio_recorder iframe for its
     recording color (#f87171 → rgb(248, 113, 113)). Same-origin in
     Streamlit; any access failure ⇒ null ⇒ stay gracefully idle. */
  function detectRecording(){
    try{
      var frames=window.parent.document.querySelectorAll('iframe');
      var cands=[], all=[];
      for(var i=0;i<frames.length;i++){
        var f=frames[i];
        if(f===window.frameElement)continue;
        all.push(f);
        var tag=(f.getAttribute('title')||'')+' '+(f.getAttribute('src')||'');
        if(/audio_recorder/i.test(tag))cands.push(f);
      }
      var list=cands.length?cands:all, sawOne=false;
      for(var k=0;k<list.length;k++){
        var idoc; try{idoc=list[k].contentDocument;}catch(e){continue;}
        if(!idoc||!idoc.body)continue;
        sawOne=true;
        var els=idoc.body.querySelectorAll('*');
        var n=Math.min(els.length,400);
        for(var j=0;j<n;j++){
          var cs=list[k].contentWindow.getComputedStyle(els[j]);
          if((cs.color&&cs.color.indexOf('248, 113, 113')>-1)||
             (cs.fill&&cs.fill.indexOf('248, 113, 113')>-1))return true;
        }
      }
      return sawOne?false:null;
    }catch(e){return null;}
  }

  resize();
  if(MODE==='server'){
    if(PYSTATE==='recording')startLive(); else paint();
  }else{
    paint();
    poll=setInterval(function(){
      var r=detectRecording();
      if(r===true&&uiState==='idle')startLive();
      else if(r===false&&uiState!=='idle')stopLive();
    },400);
  }
})();
</script></body></html>
"""

def render_waveform(state: str, mode: str) -> None:
    """Render the live waveform. state: idle|recording · mode: server|browser."""
    html = _WAVEFORM_TPL.replace("__STATE__", state).replace("__MODE__", mode)
    components.html(html, height=86)


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE SIGN-IN GATE  (Streamlit native OIDC — st.login / st.user / st.logout)
# ─────────────────────────────────────────────────────────────────────────────
# - Configured via [auth] in st.secrets (client_id/client_secret are the OAuth
#   web-client credentials; cookie_secret signs the local session cookie).
# - Identity key: st.user.sub — Google's stable OIDC subject claim. This is
#   THE key tying a user to their Firestore data (users/{sub}/meetings).
# - No long-lived credential ever enters st.session_state; Streamlit keeps
#   only a signed identity cookie, and st.logout() destroys it.
# - If [auth] is absent (local dev without OAuth set up) the app runs in
#   "local mode": no login wall, no cloud persistence — never a crash.
# ─────────────────────────────────────────────────────────────────────────────
import db as clouddb

def _auth_configured() -> bool:
    try:
        return "auth" in st.secrets
    except FileNotFoundError:
        return False

# st.login/st.user need Streamlit >= 1.42 — degrade loudly, not with a crash
_AUTH_SUPPORTED = hasattr(st, "login") and hasattr(st, "user")
_AUTH = _auth_configured() and _AUTH_SUPPORTED

if _auth_configured() and not _AUTH_SUPPORTED:
    st.warning(
        "Google Sign-In is configured in secrets, but this Streamlit version "
        "doesn't support st.login. Run: pip install --upgrade 'streamlit>=1.42' Authlib"
    )
_USER_UID:   str | None = None
_USER_EMAIL: str = ""
_USER_NAME:  str = ""

if _AUTH:
    if not st.user.is_logged_in:
        # ── Login page (inherits design system, perfectly centered horizontally & vertically) ──
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"] { display: none !important; }
            .stApp > div:first-child, .stApp { margin-left: 0 !important; }
            .block-container { max-width: 480px !important; margin: 0 auto !important; padding-top: 18vh !important; text-align: center !important; }
            </style>
            <div style="text-align:center;margin-bottom:1.5rem;">
                <h1 class="lmi-title" style="margin-left:0;font-size:2.2rem;">🎙️ Live Meeting <span class="lmi-title-accent">Intelligence</span></h1>
                <p class="lmi-subtitle" style="padding-left:0;margin-top:0.5rem;color:#8b95a5;">Sign in to record, transcribe and keep your meetings.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _placeholder_creds = "REPLACE" in st.secrets["auth"].get("client_id", "")
        if _placeholder_creds:
            st.warning(
                "Almost there — paste your real Google client_id and "
                "client_secret into .streamlit/secrets.toml (the two lines "
                "marked REPLACE), then refresh. Get them at "
                "console.cloud.google.com/apis/credentials"
            )
        st.markdown('<div class="lmi-record-wrap">', unsafe_allow_html=True)
        if st.button("Sign in with Google", type="primary",
                     use_container_width=True, disabled=_placeholder_creds):
            st.login()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(
            '<p style="font-size:0.68rem;color:#4b5563;text-align:center;'
            'margin-top:0.9rem;">Your meetings are private to your Google account.</p>',
            unsafe_allow_html=True,
        )
        st.stop()

    _USER_UID   = st.user.sub
    _USER_EMAIL = getattr(st.user, "email", "") or ""
    _USER_NAME  = getattr(st.user, "name", "") or _USER_EMAIL

    # Profile upsert once per session — never let a Firestore hiccup block the app
    if clouddb.firestore_configured() and not st.session_state.get("_profile_synced"):
        try:
            clouddb.upsert_user(_USER_UID, _USER_EMAIL, _USER_NAME)
            st.session_state["_profile_synced"] = True
        except Exception:
            pass

_CLOUD = _AUTH and _USER_UID is not None and clouddb.firestore_configured()


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_STATES = {
    "recorder":    None,
    "is_recording": False,
    "transcript":  "",
    "summary":     "",
    "last_audio":  None,
    # app_state: idle | recording | processing | transcribed | error
    "app_state":   "idle",
    "theme_mode":  "🌙 Dark",
}
for k, v in _STATES.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    if _AUTH and _USER_UID:
        st.markdown(
            f'<div style="padding:0.2rem 0 0.6rem;">'
            f'<p style="font-size:0.84rem;color:#f0f2f5;font-weight:600;margin:0;">{_USER_NAME}</p>'
            f'<p style="font-size:0.7rem;color:#6b7280;margin:0.15rem 0 0;">{_USER_EMAIL}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign out", use_container_width=True, key="logout_btn"):
            # st.logout() clears the identity cookie AND ends the OIDC session,
            # so the next login re-prompts Google — not just local state.
            st.logout()
        st.divider()
    elif not _AUTH:
        # Local mode is a deliberate fallback — but say so, don't hide it.
        st.markdown(
            '<div style="background:rgba(229,164,75,0.08);border:1px solid '
            'rgba(229,164,75,0.25);border-radius:8px;padding:0.6rem 0.75rem;'
            'margin-bottom:0.9rem;">'
            '<p style="font-size:0.72rem;color:#e5a44b;font-weight:600;margin:0;">'
            'Local mode — Google Sign-In not configured</p>'
            '<p style="font-size:0.68rem;color:#8b95a5;line-height:1.5;margin:0.3rem 0 0;">'
            'Add an <code style="font-size:0.64rem;">[auth]</code> section to '
            '<code style="font-size:0.64rem;">.streamlit/secrets.toml</code> '
            '(see secrets.example.toml) to enable login and cloud meetings.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("## ⚙️ Settings")

    st.markdown('<p style="font-size:0.72rem;font-weight:600;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;margin:0.4rem 0 0.3rem;">Theme Mode</p>', unsafe_allow_html=True)
    st.radio(
        "Theme",
        ["🌙 Dark", "☀️ Light"],
        key="theme_mode",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown('<div style="margin-bottom:0.8rem;"></div>', unsafe_allow_html=True)

    # PHASE 1: No API key widget — status indicator only.
    if _GROQ_KEY:
        st.markdown(
            '<p class="lmi-status-ok" style="font-size:0.78rem;margin:0;">● Groq API connected</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p style="font-size:0.78rem;color:#f87171;line-height:1.5;margin:0;">'
            '● Groq API key missing.<br>'
            'Add <code style="font-size:0.72rem;">GROQ_API_KEY</code> to '
            '<code style="font-size:0.72rem;">.streamlit/secrets.toml</code> '
            'or Streamlit Cloud Secrets.</p>',
            unsafe_allow_html=True,
        )

    # Cloud storage status — mirrors the Groq indicator pattern
    if _CLOUD:
        st.markdown(
            '<p class="lmi-status-ok" style="font-size:0.78rem;margin:0.4rem 0 0;">'
            '● Cloud storage connected</p>',
            unsafe_allow_html=True,
        )
    elif _AUTH and _USER_UID:
        st.markdown(
            '<p style="font-size:0.78rem;color:#e5a44b;line-height:1.5;margin:0.4rem 0 0;">'
            '● Cloud storage off — transcripts won\'t be saved.<br>'
            'Add <code style="font-size:0.72rem;">[firebase_service_account]</code> to '
            '<code style="font-size:0.72rem;">.streamlit/secrets.toml</code> '
            '(see secrets.example.toml).</p>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### 📧 Email Reports")
    with st.expander("Configure email details"):
        email_user = st.text_input("Gmail address", key="email_user")
        email_pass = st.text_input(
            "App password", type="password",
            help="Use a Google App Password — not your Gmail account password.",
            key="email_pass",
        )
        email_to = st.text_input("Recipient email", key="email_to")

    st.markdown("---")
    st.markdown(
        '<div class="lmi-version">v1.2.0 · Live Meeting Intelligence</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
hdr_l, hdr_r = st.columns([4, 1])

with hdr_l:
    st.markdown(
        '<h1 class="lmi-title">🎙️ Live Meeting '
        '<span class="lmi-title-accent">Intelligence</span></h1>'
        '<p class="lmi-subtitle">'
        'Groq Whisper transcription · Llama 3 summarisation · Email reports'
        '</p>',
        unsafe_allow_html=True,
    )

with hdr_r:
    state = st.session_state.app_state
    _badge_map = {
        "idle":        ("badge-ready",      "Ready · Standby"),
        "transcribed": ("badge-ready",      "Transcribed"),
        "recording":   ("badge-recording",  "REC · Live"),
        "processing":  ("badge-processing", "Processing…"),
        "error":       ("badge-error",      "Error"),
    }
    badge_cls, badge_txt = _badge_map.get(state, ("badge-ready", "Ready"))
    st.markdown(
        f'<div style="display:flex;justify-content:flex-end;padding-top:0.35rem;">'
        f'<div class="lmi-badge {badge_cls}">'
        f'<span class="lmi-badge-dot"></span>{badge_txt}</div></div>',
        unsafe_allow_html=True,
    )

st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN COLUMNS
# ─────────────────────────────────────────────────────────────────────────────
col_ctrl, col_tx = st.columns([1, 2], gap="large")


# ── LEFT · CONTROL PANEL ─────────────────────────────────────────────────────
with col_ctrl:
    st.subheader("Control Panel")

    # Recording mode (only surfaced when sounddevice is available)
    recording_mode = "Browser-based"
    if SOUNDDEVICE_AVAILABLE:
        recording_mode = st.radio(
            "Recording mode",
            ["Server-side (Local Mic)", "Browser-based"],
            horizontal=True,
        )

    # Hard stop — no UI if key is missing; message is already in sidebar
    if not _GROQ_KEY:
        st.error(
            "⚠️ Groq API key not configured. See sidebar for setup instructions."
        )
    else:
        with st.container(border=True):

            # ── Server-side (local mic) ─────────────────────────────────────
            if recording_mode == "Server-side (Local Mic)":
                if not st.session_state.is_recording:
                    render_waveform("idle", "server")
                    st.markdown(
                        '<p style="font-size:0.72rem;color:#6b7280;text-align:center;'
                        'margin:0 0 0.6rem;">Local microphone · ready to capture</p>',
                        unsafe_allow_html=True,
                    )
                    st.markdown('<div class="lmi-record-wrap" style="margin-top:0.3rem;">', unsafe_allow_html=True)
                    if st.button("▶  Start Recording", type="primary", use_container_width=True):
                        st.session_state.is_recording = True
                        st.session_state.app_state   = "recording"
                        st.session_state.recorder    = AudioRecorder()
                        st.session_state.recorder.start()
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

                else:
                    render_waveform("recording", "server")
                    st.markdown(
                        '<div style="text-align:center;padding:0.25rem 0 0.9rem;">'
                        '<div style="font-size:0.78rem;color:#f87171;font-weight:600;'
                        'letter-spacing:0.05em;">RECORDING IN PROGRESS</div>'
                        '<div style="font-size:0.72rem;color:#6b7280;margin-top:0.3rem;">'
                        'Microphone is live</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("⏹  Stop & Transcribe", type="secondary", use_container_width=True):
                        st.session_state.is_recording = False
                        st.session_state.app_state   = "processing"
                        st.session_state.recorder.stop()

                        if not audio_has_speech("temp_meeting.wav"):
                            st.session_state.app_state = "idle"
                            st.warning(
                                "No speech detected — the recording was silent. "
                                "The server microphone may be unavailable (this mode "
                                "cannot work on a cloud server) or the wrong input "
                                "device is selected. Switch to **Browser-based** mode "
                                "to record from your own microphone."
                            )
                        else:
                            with st.spinner("Sending to Whisper Large v3 via Groq…"):
                                try:
                                    stt = STTEngine(api_key=_GROQ_KEY)
                                    text = stt.transcribe_file("temp_meeting.wav")
                                    ts   = time.strftime("%H:%M:%S")
                                    st.session_state.transcript += f"[{ts}] {text}\n"
                                    st.session_state.app_state = "transcribed"
                                except Exception:
                                    # Never surface raw exception — may contain key fragments
                                    st.session_state.app_state = "error"
                                    st.error(
                                        "Transcription failed. "
                                        "Check your Groq account limits or audio quality."
                                    )
                        st.rerun()

            # ── Browser-based ───────────────────────────────────────────────
            else:
                render_waveform("idle", "browser")
                st.markdown(
                    '<p style="font-size:0.8rem;color:#6b7280;margin-bottom:0.6rem;">'
                    'Click the mic to start · click again to stop &amp; transcribe.</p>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="lmi-record-wrap">', unsafe_allow_html=True)
                audio_bytes = audio_recorder(
                    text="Click to Record",
                    recording_color="#f87171",
                    neutral_color="#1d9bf0",
                    icon_size="2x",
                    pause_threshold=600.0,
                )
                st.markdown('</div>', unsafe_allow_html=True)

                if audio_bytes and audio_bytes != st.session_state.last_audio:
                    st.session_state.last_audio = audio_bytes
                    st.session_state.app_state  = "processing"

                    with open("temp_meeting.wav", "wb") as f:
                        f.write(audio_bytes)

                    if not audio_has_speech("temp_meeting.wav"):
                        st.session_state.app_state = "idle"
                        st.warning(
                            "No speech detected — the clip was silent. "
                            "Check that your microphone is unmuted and try again."
                        )
                    else:
                        with st.spinner("Sending to Whisper Large v3 via Groq…"):
                            try:
                                stt  = STTEngine(api_key=_GROQ_KEY)
                                text = stt.transcribe_file("temp_meeting.wav")
                                ts   = time.strftime("%H:%M:%S")
                                st.session_state.transcript += f"[{ts}] {text}\n"
                                st.session_state.app_state = "transcribed"
                            except Exception:
                                st.session_state.app_state = "error"
                                st.error(
                                    "Transcription failed. "
                                    "Check your Groq account limits or audio quality."
                                )
                    st.rerun()

    # Local recording re-render loop
    if st.session_state.is_recording and recording_mode == "Server-side (Local Mic)":
        if st.session_state.recorder:
            for _ in st.session_state.recorder.process_queue():
                pass
        time.sleep(0.05)
        st.rerun()

    # ── Session stats — fills dead space, shows value ───────────────────────
    if st.session_state.transcript:
        words = len(st.session_state.transcript.split())
        chars = len(st.session_state.transcript)
        segs  = st.session_state.transcript.count("[")  # timestamp count = segments
        st.markdown("---")
        st.markdown(
            f'<div class="lmi-stat-row">'
            f'  <div class="lmi-stat"><div class="lmi-stat-val">{words:,}</div>'
            f'    <div class="lmi-stat-label">Words</div></div>'
            f'  <div class="lmi-stat"><div class="lmi-stat-val">{segs}</div>'
            f'    <div class="lmi-stat-label">Segments</div></div>'
            f'  <div class="lmi-stat"><div class="lmi-stat-val">{chars:,}</div>'
            f'    <div class="lmi-stat-label">Chars</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── RIGHT · TRANSCRIPT ───────────────────────────────────────────────────────
with col_tx:
    tx_l, tx_r = st.columns([4, 1])
    with tx_l:
        st.subheader("Transcript")
    with tx_r:
        if st.button("Clear", use_container_width=True, key="clear_btn"):
            st.session_state.transcript = ""
            st.session_state.summary    = ""
            st.session_state.app_state  = "idle"
            st.rerun()

    if st.session_state.transcript:
        st.text_area(
            "transcript_output",
            value=st.session_state.transcript,
            height=420,
            label_visibility="collapsed",
        )
    else:
        st.markdown(
            '<div class="lmi-empty" style="height:420px;">'
            '  <div class="lmi-empty-icon">'
            '    <svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>'
            '  </div>'
            '  <span class="lmi-empty-label">No transcript yet.</span>'
            '  <span class="lmi-empty-hint">'
            '    Record audio &rarr; stop &rarr; transcript appears here automatically.'
            '  </span>'
            '</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS — summary + export (appears only when there's content)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.transcript and not st.session_state.is_recording:
    st.divider()
    tab_sum, tab_exp = st.tabs(["AI Summary", "Export"])

    with tab_sum:
        if st.button("Generate Summary", type="primary"):
            with st.spinner("Analysing with Llama 3.3 70B via Groq…"):
                try:
                    summarizer = MeetingSummarizer(_GROQ_KEY)
                    st.session_state.summary = summarizer.generate_summary(
                        st.session_state.transcript
                    )
                except Exception:
                    st.error(
                        "Summary generation failed. "
                        "Check your Groq account limits and try again."
                    )

        if st.session_state.summary:
            st.markdown(
                f'<div class="lmi-summary">{st.session_state.summary}</div>',
                unsafe_allow_html=True,
            )

    with tab_exp:
        ec1, ec2, ec3 = st.columns(3)

        with ec1:
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:600;color:#4b5563;'
                'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;">'
                'File</p>',
                unsafe_allow_html=True,
            )
            if st.button("Save summary as Markdown", use_container_width=True):
                if st.session_state.summary:
                    path = save_to_md(st.session_state.summary)
                    st.success(f"Saved → `{path}`")
                else:
                    st.warning("Generate a summary first.")

        with ec2:
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:600;color:#4b5563;'
                'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;">'
                'Email</p>',
                unsafe_allow_html=True,
            )
            if st.button("Send email report", use_container_width=True):
                eu = st.session_state.get("email_user", "")
                ep = st.session_state.get("email_pass", "")
                et = st.session_state.get("email_to", "")
                if not (eu and ep and et):
                    st.error("Fill in all email fields in the sidebar first.")
                elif not st.session_state.summary:
                    st.warning("Generate a summary before sending.")
                else:
                    with st.spinner("Sending…"):
                        result = send_email_func(
                            eu, ep, et, "Meeting Notes", st.session_state.summary
                        )
                    # Never surface raw result string — may contain credentials
                    if "sent" in result.lower():
                        st.success("Email sent successfully.")
                    else:
                        st.error(
                            "Email failed. Verify your Gmail App Password "
                            "and recipient address."
                        )

        with ec3:
            st.markdown(
                '<p style="font-size:0.72rem;font-weight:600;color:#4b5563;'
                'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;">'
                'Cloud</p>',
                unsafe_allow_html=True,
            )
            if _CLOUD:
                meeting_title = st.text_input(
                    "Meeting title", key="cloud_title",
                    placeholder="e.g. Sprint planning",
                    label_visibility="collapsed",
                )
                if st.button("Save to My Meetings", use_container_width=True):
                    if not st.session_state.transcript:
                        st.warning("Record something first — nothing to save.")
                    else:
                        try:
                            clouddb.save_meeting(
                                _USER_UID,
                                title=(meeting_title or "Untitled meeting").strip(),
                                transcript=st.session_state.transcript,
                                summary=st.session_state.summary,  # may be empty — transcript alone is worth keeping
                                date=time.strftime("%Y-%m-%d"),
                            )
                            st.success("Saved to your account.")
                        except Exception:
                            st.error("Cloud save failed. Check Firestore configuration.")
            else:
                st.markdown(
                    '<p style="font-size:0.72rem;color:#4b5563;line-height:1.5;">'
                    'Sign-in + Firestore not configured — cloud save unavailable '
                    'in local mode.</p>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# MY MEETINGS — Firestore dashboard (only when signed in + Firestore ready)
# ─────────────────────────────────────────────────────────────────────────────
if _CLOUD:
    st.divider()
    mh_l, mh_r = st.columns([3, 2])
    with mh_l:
        st.subheader("My Meetings")
    with mh_r:
        search_term = st.text_input(
            "Search meetings", key="meet_search",
            placeholder="Search title, transcript, summary…",
            label_visibility="collapsed",
        )

    try:
        _meetings = (
            clouddb.search_meetings(_USER_UID, search_term)
            if search_term else clouddb.list_meetings(_USER_UID)
        )
    except Exception:
        _meetings = None
        st.error("Could not load meetings. Check Firestore configuration.")

    if _meetings is not None:
        if not _meetings:
            st.markdown(
                '<div class="lmi-empty" style="padding:2.25rem 1rem;">'
                '  <div class="lmi-empty-icon">'
                '    <svg viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>'
                '  </div>'
                '  <span class="lmi-empty-label">'
                + ("No meetings match your search."
                   if search_term else "No meetings saved yet.") +
                '  </span>'
                '  <span class="lmi-empty-hint">'
                + ("Try a different term."
                   if search_term else
                   "Record → summarise → &ldquo;Save to My Meetings&rdquo; in the Export tab.") +
                '  </span>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            for m in _meetings:
                mid   = m["id"]
                title = m.get("title") or "Untitled meeting"
                date  = m.get("date") or ""
                words = len(str(m.get("transcript", "")).split())
                with st.expander(f"{title}  ·  {date}  ·  {words:,} words"):
                    if m.get("summary"):
                        st.markdown(
                            f'<div class="lmi-summary">{html.escape(m["summary"])}</div>',
                            unsafe_allow_html=True,
                        )
                    if m.get("transcript"):
                        st.text_area(
                            "Transcript", value=m["transcript"], height=180,
                            key=f"tx_{mid}", disabled=True,
                            label_visibility="collapsed",
                        )
                    dc1, dc2 = st.columns([1, 4])
                    with dc1:
                        if st.session_state.get("confirm_del") == mid:
                            if st.button("Confirm delete", type="primary",
                                         key=f"cd_{mid}", use_container_width=True):
                                try:
                                    clouddb.delete_meeting(_USER_UID, mid)
                                    st.session_state.pop("confirm_del", None)
                                    st.rerun()
                                except Exception:
                                    st.error("Delete failed.")
                        else:
                            if st.button("Delete", key=f"del_{mid}",
                                         use_container_width=True):
                                st.session_state["confirm_del"] = mid
                                st.rerun()