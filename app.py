import os
import re
import ast
import json
import mimetypes
from base64 import b64encode
from html import escape
from pathlib import Path

import streamlit as st
try:
    import boto3
except Exception:
    boto3 = None

from phase2_art_pulse_config import PERSONAS
from phase2_art_pulse_draft import generate_art_pulse_draft
from phase2_art_pulse_readonly import build_art_pulse_overview
from phase2_common_readonly import (
    resolve_current_exhibitions_available_years,
    resolve_current_artist_works_local_path,
)
from phase2_advisor_draft import (
    ADVISOR_TEXT_MAX_CHARS,
    _build_visual_observation_digest,
    _build_art_pulse_style_reference_lines,
    _build_reference_images,
    _ensure_natural_ending,
    _ensure_plain_answer_text,
    _normalize_answer_text,
    _select_reference_entities_for_output,
    generate_advisor_grounded_draft,
)
from phase2_advisor_readonly import (
    build_advisor_followup_reference_patch,
    build_advisor_grounded_context,
)
from phase2_advisor_type2_execute import run_type2_gated_image_generation
from phase2_gallery_list_readonly import load_gallery_list_records_readonly
from phase2_artist_search_readonly import (
    ARTIST_SEARCH_SUMMARY_MAX_CHARS,
    ARTIST_SEARCH_THUMB_FROM_ARTIST,
    build_artist_summary_ja,
    load_artist_records_readonly,
    search_artists,
)
from phase2_artwork_search_readonly import (
    ARTWORK_SEARCH_TOP_K_DEFAULT,
    search_artwork_images_by_image,
    search_artwork_images_by_text,
)
from phase2_exhibition_search_readonly import (
    EXHIBITION_SEARCH_SUMMARY_MAX_CHARS,
    _derive_title,
    build_exhibition_summary_ja,
    load_exhibition_records_readonly,
    search_exhibitions,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

APP_TITLE = "Art Pulse Editor"
FAIR_OPTIONS = ["Frieze London", "Liste Art Fair Basel", "Frieze London + Liste Art Fair Basel"]
SEARCH_RESULTS_PAGE_SIZE = 30
MODE_HEADING_FONT_SIZE_PX = 30
EXPLANATION_OF_MODES_FONT_SIZE_PX = 15
IMAGE_MARKDOWN_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)")
SOURCE_LINE_RE = re.compile(r"^Source:\s*<(?P<url>[^>]+)>\s*$")
ADVISOR_UI_SHOW_DEBUG = False


def apply_global_font_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --font-latin: "DIN 2014", "DIN Alternate", "DIN Next LT Pro", "DINPro", "DIN";
          --font-cjk: "Yu Gothic", "YuGothic", "游ゴシック", "Meiryo", sans-serif;
          --font-display: "Aptos Display", "Palatino Linotype", "Book Antiqua", "Yu Mincho", "YuMincho", serif;
          --ap-bg: #eef0f3;
          --ap-bg-soft: #f6f7f9;
          --ap-surface-strong: #ffffff;
          --ap-border: rgba(34, 40, 48, 0.16);
          --ap-border-strong: rgba(34, 40, 48, 0.26);
          --ap-text: #17191c;
          --ap-text-soft: #27303a;
          --ap-muted: #66707b;
          --ap-muted-soft: #8b939b;
          --ap-link: #4a6278;
          --ap-shadow-soft: 0 18px 44px rgba(22, 28, 33, 0.06);
          --ap-shadow-card: 0 12px 30px rgba(22, 28, 33, 0.045);
          --ap-radius-xl: 24px;
          --ap-radius-md: 14px;
          color-scheme: light;
        }
        html, body {
          background: var(--ap-bg) !important;
          color: var(--ap-text) !important;
        }
        .stApp,
        .stApp div,
        .stApp span,
        .stApp p,
        .stApp a,
        .stApp li,
        .stApp label,
        .stApp button,
        .stApp input,
        .stApp textarea,
        .stApp select,
        .stApp option,
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4,
        .stApp h5,
        .stApp h6 {
          font-family: var(--font-latin), var(--font-cjk) !important;
        }
        .stApp h1,
        .stApp h2,
        .stApp h3,
        .stApp h4,
        .stApp h5,
        .stApp h6 {
          color: var(--ap-text) !important;
        }
        /* Keep expander toggle icons rendered with Material icon fonts. */
        .stApp [data-testid="stExpanderToggleIcon"],
        .stApp [data-testid="stExpanderToggleIcon"] *,
        .stApp [class*="material-symbols"],
        .stApp [class*="material-icons"] {
          font-family: "Material Symbols Rounded", "Material Symbols Outlined",
            "Material Symbols Sharp", "Material Icons", "Material Icons Outlined" !important;
          font-style: normal !important;
        }
        /* Hide heading anchor/link icons globally. */
        .stApp [data-testid="stHeaderActionElements"] {
          display: none !important;
        }
        .ap-section-heading {
          margin: 0.05rem 0 0.28rem 0;
        }
        .ap-section-title {
          margin: 0;
          font-family: var(--font-display) !important;
          font-weight: 500;
          line-height: 1.22;
          letter-spacing: 0.015em;
          color: var(--ap-text);
        }
        .ap-section-explanation {
          margin: 0 0 1.15rem 0;
          color: var(--ap-text-soft);
          font-weight: 500;
          line-height: 1.72;
          letter-spacing: 0.01em;
        }
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"] {
          width: 100% !important;
          justify-content: center !important;
          align-items: center !important;
          background: var(--ap-bg) !important;
          border: none !important;
          border-bottom: 1px solid var(--ap-border) !important;
          box-shadow: none !important;
          padding: clamp(0.95rem, 1.7vw, 1.18rem) 0.2rem !important;
          margin: 0 !important;
          min-height: auto !important;
          border-radius: 0 !important;
          color: var(--ap-text) !important;
          font-family: var(--font-display) !important;
          font-size: clamp(1.52rem, 2.15vw, 2.2rem) !important;
          font-weight: 500 !important;
          line-height: 1.2 !important;
          letter-spacing: 0.02em !important;
          text-align: center !important;
          transition:
            color 0.18s ease,
            border-color 0.18s ease,
            transform 0.18s ease !important;
        }
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"] > div,
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"] > div > span {
          justify-content: center !important;
          align-items: center !important;
          width: 100% !important;
          text-align: center !important;
        }
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"] [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"] [data-testid="stMarkdownContainer"] p {
          margin: 0 !important;
          font-size: inherit !important;
          font-weight: inherit !important;
          line-height: inherit !important;
          color: inherit !important;
          text-align: center !important;
        }
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"]:hover,
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"]:focus,
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"]:focus-visible,
        .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"]:active {
          background: var(--ap-bg) !important;
          border: none !important;
          border-bottom: 1px solid var(--ap-border-strong) !important;
          box-shadow: none !important;
          color: #314456 !important;
          transform: translateY(-1px);
        }
        .ap-top-nav-list-spacer {
          height: clamp(0.6rem, 1.6vw, 1.15rem);
        }
        .ap-top-nav-open-gap {
          height: clamp(1rem, 2vw, 1.35rem);
        }
        .about-panel {
          max-width: 1160px;
          margin: 0 auto;
          padding: clamp(0.2rem, 0.7vw, 0.4rem) 0 0 0;
        }
        .about-hero {
          padding: 0 0 1.55rem 0;
          border-bottom: 1px solid var(--ap-border);
          margin-bottom: 1.5rem;
        }
        .about-eyebrow {
          margin: 0 0 0.4rem 0;
          font-size: 0.82rem;
          font-weight: 600;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--ap-muted);
        }
        .about-title {
          margin: 0 0 0.7rem 0;
          font-family: var(--font-display) !important;
          font-size: clamp(2rem, 3vw, 2.7rem);
          line-height: 1.24;
          font-weight: 500;
          letter-spacing: 0.01em;
          color: var(--ap-text);
        }
        .about-lead {
          margin: 0;
          font-size: clamp(1rem, 1.25vw, 1.08rem);
          line-height: 1.92;
          color: var(--ap-text-soft);
          max-width: 62rem;
        }
        .about-section {
          margin-top: 1.55rem;
        }
        .about-section-title {
          margin: 0 0 0.95rem 0;
          font-size: 1.02rem;
          line-height: 1.35;
          font-weight: 600;
          color: var(--ap-text-soft);
          letter-spacing: 0.02em;
        }
        .about-fair-list {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 1rem;
          margin: 0;
        }
        .about-fair-item,
        .about-feature-card {
          background: var(--ap-surface-strong);
          border: 1px solid var(--ap-border);
          border-radius: var(--ap-radius-md);
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
        }
        .about-fair-item {
          padding: 1rem 1.05rem;
        }
        .about-fair-name {
          margin: 0 0 0.2rem 0;
          font-size: 1rem;
          line-height: 1.45;
          font-weight: 600;
          color: var(--ap-text);
        }
        .about-fair-desc {
          margin: 0;
          font-size: 0.96rem;
          line-height: 1.74;
          color: var(--ap-text-soft);
        }
        .about-feature-list {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 1rem;
          margin-top: 0.2rem;
        }
        .about-feature-card {
          padding: 1rem 1.05rem;
        }
        .about-feature-head {
          display: flex;
          align-items: baseline;
          gap: 0.7rem;
          margin-bottom: 0.45rem;
          flex-wrap: wrap;
        }
        .about-feature-no {
          font-family: var(--font-display) !important;
          font-size: 0.95rem;
          line-height: 1;
          font-weight: 500;
          color: var(--ap-muted);
          letter-spacing: 0.06em;
        }
        .about-feature-name {
          font-size: 1.04rem;
          line-height: 1.35;
          font-weight: 600;
          color: var(--ap-text);
        }
        .about-feature-body {
          margin: 0;
          font-size: 0.96rem;
          line-height: 1.8;
          color: var(--ap-text-soft);
        }
        .ap-gallery-kb-meta {
          margin-top: 0.05rem;
          margin-bottom: 0.95rem;
          color: var(--ap-muted);
          font-size: 0.82rem;
          font-weight: 500;
          letter-spacing: 0.02em;
        }
        .ap-gallery-kb-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 1rem;
          margin-top: 0.2rem;
        }
        .ap-gallery-kb-col {
          background: var(--ap-surface-strong);
          border: 1px solid var(--ap-border);
          border-radius: var(--ap-radius-md);
          padding: 1rem 1.05rem 1.1rem;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
        }
        .ap-gallery-kb-col h4 {
          margin: 0 0 0.85rem 0;
          font-family: var(--font-display) !important;
          font-size: 1.18rem;
          font-weight: 500;
          line-height: 1.32;
          color: var(--ap-text);
        }
        .ap-gallery-kb-col ol {
          margin: 0;
          padding-left: 1.25rem;
        }
        .ap-gallery-kb-col li {
          margin: 0;
          padding: 0.16rem 0;
          line-height: 1.54;
          font-size: 0.97rem;
          color: var(--ap-text-soft);
        }
        .ap-gallery-kb-col a {
          color: var(--ap-link) !important;
          text-decoration: none;
          border-bottom: 1px solid rgba(74, 98, 120, 0.24);
        }
        @media (max-width: 900px) {
          .stApp [data-testid="stButton"] > button[data-testid="stBaseButton-tertiary"] {
            padding: 0.82rem 0.15rem !important;
            font-size: clamp(1.28rem, 4.3vw, 1.72rem) !important;
          }
          .about-hero {
            padding-bottom: 1.15rem;
            margin-bottom: 1.15rem;
          }
          .about-fair-list,
          .about-feature-list,
          .ap-gallery-kb-grid {
            grid-template-columns: minmax(0, 1fr);
          }
          .about-fair-item,
          .about-feature-card,
          .ap-gallery-kb-col {
            padding-left: 0.9rem;
            padding-right: 0.9rem;
          }
          .about-feature-head {
            gap: 0.45rem;
            margin-bottom: 0.38rem;
          }
        }
        .stApp {
          --background-color: var(--ap-bg) !important;
          --secondary-background-color: var(--ap-surface-strong) !important;
          --text-color: var(--ap-text) !important;
          --primary-color: #32495c !important;
          background: var(--ap-bg) !important;
          background-color: var(--ap-bg) !important;
          color: var(--ap-text) !important;
        }
        .stApp header,
        .stApp [data-testid="stAppViewContainer"],
        .stApp [data-testid="stMain"],
        .stApp [data-testid="stMainBlockContainer"],
        .stApp .block-container,
        .stApp [data-testid="stHeader"],
        .stApp [data-testid="stToolbar"],
        .stApp [data-testid="stSidebar"] {
          background: var(--ap-bg) !important;
          background-color: var(--ap-bg) !important;
          color: var(--ap-text) !important;
        }
        .stApp [data-testid="stMainBlockContainer"],
        .stApp .block-container {
          max-width: min(1540px, 94vw) !important;
          width: 100% !important;
          padding-top: clamp(1.1rem, 2.3vw, 2.35rem) !important;
          padding-bottom: 2.4rem !important;
          padding-left: clamp(0.95rem, 2.2vw, 2.75rem) !important;
          padding-right: clamp(0.95rem, 2.2vw, 2.75rem) !important;
        }
        .stApp [data-testid="stHeadingWithActionElements"] {
          position: relative;
          margin-bottom: clamp(1.1rem, 2vw, 1.9rem) !important;
        }
        .stApp [data-testid="stHeadingWithActionElements"]::after {
          content: "";
          display: block;
          width: min(180px, 28vw);
          height: 1px;
          margin: 1rem auto 0;
          background: var(--ap-border-strong);
        }
        .stApp [data-testid="stHeadingWithActionElements"] h1 {
          font-family: var(--font-display) !important;
          font-size: clamp(3.5rem, 5vw, 4.85rem) !important;
          width: 100%;
          text-align: center !important;
          margin: 0.5rem 0 0 !important;
          line-height: 1.04 !important;
          letter-spacing: 0.015em !important;
          font-weight: 500 !important;
          color: var(--ap-text) !important;
        }
        .stApp [data-testid="stVerticalBlockBorderWrapper"] {
          background: var(--ap-surface-strong) !important;
          border: 1px solid var(--ap-border) !important;
          border-radius: calc(var(--ap-radius-xl) + 2px) !important;
          box-shadow: var(--ap-shadow-soft) !important;
          overflow: hidden !important;
          padding: clamp(1.15rem, 2vw, 1.65rem) !important;
        }
        .stApp [data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
          gap: 0.3rem !important;
        }
        .advisor-toggle-spacer {
          height: 1.9rem;
        }
        .advisor-generated-image-wrap {
          display: flex;
          justify-content: center;
          margin: 0.35rem 0 0.45rem 0;
        }
        .advisor-generated-image-link {
          display: block;
          width: min(100%, 560px);
          text-decoration: none;
          border-bottom: none !important;
        }
        .advisor-generated-image-link img {
          display: block;
          width: 100%;
          height: auto;
          max-height: 68vh;
          object-fit: contain;
          border-radius: 14px;
          border: 1px solid var(--ap-border);
          background: var(--ap-bg-soft);
          box-shadow: var(--ap-shadow-card);
        }
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stMetricLabel"],
        .stApp p,
        .stApp label,
        .stApp li {
          color: var(--ap-text) !important;
        }
        .stApp p,
        .stApp li {
          line-height: 1.72 !important;
        }
        .stApp strong {
          font-weight: 650 !important;
        }
        .stApp [data-testid="stMarkdownContainer"] h3,
        .stApp [data-testid="stMarkdownContainer"] h4,
        .stApp [data-testid="stMarkdownContainer"] h5 {
          font-family: var(--font-display) !important;
          font-weight: 500 !important;
          line-height: 1.32 !important;
          letter-spacing: 0.01em !important;
          color: var(--ap-text) !important;
        }
        .stApp [data-testid="stMarkdownContainer"] h3 {
          font-size: clamp(1.45rem, 2vw, 1.9rem) !important;
          margin: 1rem 0 0.7rem 0 !important;
        }
        .stApp [data-testid="stMarkdownContainer"] h4 {
          font-size: clamp(1.16rem, 1.6vw, 1.45rem) !important;
          margin: 0.9rem 0 0.55rem 0 !important;
        }
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stCaptionContainer"] p {
          color: var(--ap-muted) !important;
          font-size: 0.88rem !important;
          line-height: 1.55 !important;
          letter-spacing: 0.01em !important;
        }
        .stApp .ap-black-caption {
          color: var(--ap-text) !important;
          font-size: 0.88rem !important;
          line-height: 1.55 !important;
          letter-spacing: 0.01em !important;
          font-weight: 400 !important;
          margin: 0 !important;
        }
        .stApp [data-testid="stRadio"] label p,
        .stApp [data-testid="stRadio"] label span,
        .stApp [data-baseweb="radio"] label p,
        .stApp [data-baseweb="radio"] label span {
          font-size: 0.88rem !important;
          line-height: 1.55 !important;
          font-weight: 400 !important;
          color: var(--ap-text) !important;
        }
        .stApp [data-testid="stWidgetLabel"] p,
        .stApp [data-testid="stWidgetLabel"] span,
        .stApp label[data-testid="stWidgetLabel"] {
          color: var(--ap-text-soft) !important;
          font-size: 0.92rem !important;
          font-weight: 600 !important;
          letter-spacing: 0.02em !important;
        }
        .stApp a {
          color: var(--ap-link) !important;
          text-decoration: none !important;
          border-bottom: 1px solid rgba(74, 98, 120, 0.24);
          transition: border-color 0.18s ease, color 0.18s ease;
        }
        .stApp a:hover {
          color: #314456 !important;
          border-bottom-color: rgba(74, 98, 120, 0.52);
        }
        .stApp input,
        .stApp textarea,
        .stApp div[data-baseweb="select"] > div,
        .stApp div[data-baseweb="tag"] {
          background-color: rgba(255, 255, 255, 0.94) !important;
          color: var(--ap-text) !important;
          border-color: var(--ap-border) !important;
        }
        .stApp input::placeholder,
        .stApp textarea::placeholder {
          color: var(--ap-muted-soft) !important;
          opacity: 1 !important;
        }
        .stApp [data-testid="stTextInputRootElement"],
        .stApp [data-testid="stTextAreaRootElement"],
        .stApp [data-testid="stSelectbox"] > div,
        .stApp [data-testid="stFileUploaderDropzone"] {
          color: var(--ap-text) !important;
          border-radius: var(--ap-radius-md) !important;
          border: 1px solid var(--ap-border) !important;
          background: rgba(255, 255, 255, 0.94) !important;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.82) !important;
          transition:
            background 0.18s ease,
            border-color 0.18s ease,
            box-shadow 0.18s ease !important;
        }
        .stApp [data-testid="stTextInputRootElement"]:focus-within,
        .stApp [data-testid="stTextAreaRootElement"]:focus-within,
        .stApp div[data-baseweb="select"]:focus-within > div,
        .stApp [data-testid="stFileUploaderDropzone"]:focus-within {
          background: #ffffff !important;
          border-color: var(--ap-border-strong) !important;
          box-shadow: 0 0 0 4px rgba(74, 98, 120, 0.08) !important;
        }
        .stApp [data-testid="stTextInputRootElement"] input,
        .stApp [data-testid="stTextAreaRootElement"] textarea,
        .stApp div[data-baseweb="select"] input,
        .stApp div[data-baseweb="select"] span {
          font-size: 0.97rem !important;
          line-height: 1.55 !important;
        }
        .stApp [data-testid="stButton"] > button:not([data-testid="stBaseButton-tertiary"]),
        .stApp section[data-testid="stFileUploader"] button,
        .stApp [data-testid="stFileUploaderDropzone"] [data-baseweb="button"],
        .stApp [data-testid="stFileUploaderDropzone"] button {
          background: #ffffff !important;
          color: var(--ap-text) !important;
          border: 1px solid var(--ap-border-strong) !important;
          border-radius: 999px !important;
          min-height: 2.8rem !important;
          padding: 0.5rem 1.1rem !important;
          box-shadow: 0 6px 14px rgba(22, 28, 33, 0.04) !important;
          font-size: 0.95rem !important;
          font-weight: 600 !important;
          letter-spacing: 0.02em !important;
          transition:
            background 0.18s ease,
            border-color 0.18s ease,
            box-shadow 0.18s ease,
            transform 0.18s ease !important;
        }
        .stApp [data-testid="stButton"] > button:not([data-testid="stBaseButton-tertiary"]):hover,
        .stApp [data-testid="stButton"] > button:not([data-testid="stBaseButton-tertiary"]):focus-visible,
        .stApp section[data-testid="stFileUploader"] button:hover,
        .stApp [data-testid="stFileUploaderDropzone"] [data-baseweb="button"]:hover,
        .stApp [data-testid="stFileUploaderDropzone"] button:hover {
          background: #f8f9fb !important;
          border-color: rgba(60, 68, 77, 0.28) !important;
          box-shadow: 0 10px 18px rgba(22, 28, 33, 0.06) !important;
          transform: translateY(-1px);
        }
        .stApp [data-testid="stButton"] > button {
          outline: none !important;
        }
        .stApp [data-testid="stButton"] > button:disabled,
        .stApp section[data-testid="stFileUploader"] button:disabled,
        .stApp [data-testid="stFileUploaderDropzone"] button:disabled {
          background: #f1f2f5 !important;
          color: var(--ap-muted-soft) !important;
          opacity: 1 !important;
          box-shadow: none !important;
          border-color: var(--ap-border) !important;
        }
        .stApp [data-testid="stFileUploaderDropzone"] {
          padding: 1rem 1.1rem !important;
          background: #ffffff !important;
        }
        .stApp [data-testid="stFileUploaderDropzone"] [data-testid="stMarkdownContainer"] p,
        .stApp [data-testid="stFileUploaderDropzoneInstructions"] span {
          color: var(--ap-muted) !important;
        }
        .stApp [data-baseweb="checkbox"] label {
          color: var(--ap-text-soft) !important;
          font-size: 0.92rem !important;
        }
        .stApp [data-baseweb="checkbox"] [role="checkbox"] {
          border-radius: 6px !important;
          border-color: var(--ap-border-strong) !important;
        }
        .stApp [data-testid="stDataFrame"] {
          border: 1px solid var(--ap-border) !important;
          border-radius: var(--ap-radius-md) !important;
          overflow: hidden !important;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8) !important;
          --gdg-bg-cell: #ffffff;
          --gdg-bg-cell-medium: #f6f7fa;
          --gdg-bg-header: #eef1f5;
          --gdg-bg-header-hovered: #e4e8ed;
          --gdg-bg-bubble: #f7f8fb;
          --gdg-bg-bubble-selected: #edf1f6;
          --gdg-bg-search-result: #e7edf6;
          --gdg-border-color: rgba(34, 40, 48, 0.16);
          --gdg-horizontal-border-color: rgba(34, 40, 48, 0.12);
          --gdg-drilldown-border: rgba(34, 40, 48, 0.16);
          --gdg-link-color: #4a6278;
          --gdg-text-dark: #17191c;
          --gdg-text-medium: #3d4650;
          --gdg-text-light: #66707b;
          --gdg-text-bubble: #17191c;
        }
        .stApp [data-testid="stDataFrame"] canvas {
          background-color: #ffffff !important;
        }
        .stApp [data-testid="stExpander"] {
          border: 1px solid var(--ap-border) !important;
          border-radius: var(--ap-radius-md) !important;
          background: var(--ap-surface-strong) !important;
          box-shadow: none !important;
        }
        .stApp [data-testid="stAlert"] {
          border: 1px solid var(--ap-border) !important;
          border-radius: var(--ap-radius-md) !important;
          background: var(--ap-surface-strong) !important;
          color: var(--ap-text) !important;
          box-shadow: none !important;
        }
        .stApp [data-testid="stJson"],
        .stApp [data-testid="stJson"] * {
          background-color: #ffffff !important;
          color: var(--ap-text) !important;
        }
        .stApp [data-testid="stCodeBlock"],
        .stApp [data-testid="stCodeBlock"] * {
          background-color: #ffffff !important;
          color: var(--ap-text) !important;
        }
        .stApp pre, .stApp code {
          background-color: var(--ap-bg-soft) !important;
          color: var(--ap-text) !important;
        }
        .ap-gallery {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem;
          margin: 0.75rem 0 1.15rem 0;
        }
        .ap-gallery-item {
          display: flex;
          flex-direction: column;
          gap: 0.55rem;
          padding: 0.75rem;
          border: 1px solid var(--ap-border);
          border-radius: var(--ap-radius-md);
          background: var(--ap-surface-strong);
          box-shadow: var(--ap-shadow-card);
        }
        .ap-gallery-thumb {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 260px;
          overflow: hidden;
          border-radius: 12px;
          border: 1px solid var(--ap-border);
          background: var(--ap-bg-soft);
          border-bottom: none !important;
        }
        .ap-gallery-thumb img {
          width: auto;
          height: auto;
          max-width: 100%;
          max-height: 100%;
          object-fit: contain;
          display: block;
        }
        .ap-gallery-fallback {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 260px;
          border-radius: 12px;
          border: 1px solid var(--ap-border);
          background: var(--ap-bg-soft);
          color: var(--ap-muted);
          font-size: 0.86rem;
          line-height: 1.45;
          text-align: center;
          padding: 0.8rem;
        }
        .ap-gallery-source {
          font-size: 0.81rem;
          line-height: 1.45;
          color: var(--ap-muted);
          word-break: break-word;
        }
        @media (max-width: 900px) {
          .ap-gallery {
            grid-template-columns: 1fr;
            gap: 0.75rem;
          }
          .ap-gallery-thumb,
          .ap-gallery-fallback {
            height: 220px;
          }
        }
        .exh-search-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 1rem;
          margin: 0.4rem 0 0.9rem 0;
        }
        .exh-search-card {
          border: 1px solid var(--ap-border);
          border-radius: var(--ap-radius-md);
          background: var(--ap-surface-strong);
          padding: 0.95rem;
          display: flex;
          flex-direction: column;
          gap: 0.72rem;
          box-shadow: var(--ap-shadow-card);
        }
        .exh-search-title {
          font-family: var(--font-display) !important;
          font-size: 1.04rem;
          line-height: 1.42;
          font-weight: 500;
          color: var(--ap-text);
          margin: 0;
        }
        .exh-search-thumb {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          min-height: 240px;
          max-height: 240px;
          border-radius: 12px;
          border: 1px solid var(--ap-border);
          background: var(--ap-bg-soft);
          overflow: hidden;
          position: relative;
        }
        .exh-search-thumb img {
          width: 100% !important;
          height: 100% !important;
          max-width: 100% !important;
          max-height: 100% !important;
          object-fit: contain !important;
          object-position: center center !important;
          display: block;
          background: var(--ap-bg-soft);
        }
        .exh-search-fallback {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          min-height: 240px;
          max-height: 240px;
          border-radius: 12px;
          border: 1px solid var(--ap-border);
          color: var(--ap-muted);
          font-size: 0.88rem;
          line-height: 1.45;
          text-align: center;
          background: var(--ap-bg-soft);
          padding: 0.8rem;
        }
        .exh-search-source {
          font-size: 0.81rem;
          line-height: 1.42;
          color: var(--ap-muted);
          word-break: break-word;
          margin: 0;
        }
        .exh-search-summary {
          font-size: 0.95rem;
          line-height: 1.72;
          color: var(--ap-text-soft);
          margin: 0;
          max-height: 15.5rem;
          overflow-y: auto;
          overflow-x: hidden;
          padding-right: 0.22rem;
          scrollbar-gutter: stable;
        }
        .artist-search-scroll,
        .exh-results-scroll {
          display: flex;
          align-items: flex-start;
          gap: 1.05rem;
          overflow-x: auto;
          overflow-y: hidden;
          margin: 0.75rem 0 0.15rem 0;
          padding-bottom: 0.55rem;
          overscroll-behavior-x: contain;
          -webkit-overflow-scrolling: touch;
          scroll-behavior: smooth;
        }
        .advisor-ref-scroll {
          display: flex;
          align-items: flex-start;
          gap: 1.05rem;
          overflow-x: auto;
          overflow-y: hidden;
          margin: 0.75rem 0 0.15rem 0;
          padding-bottom: 0.55rem;
          overscroll-behavior-x: contain;
          -webkit-overflow-scrolling: touch;
          scroll-behavior: smooth;
        }
        .artist-search-scroll::-webkit-scrollbar,
        .exh-results-scroll::-webkit-scrollbar,
        .advisor-ref-scroll::-webkit-scrollbar {
          height: 6px;
        }
        .artist-search-scroll::-webkit-scrollbar-thumb,
        .exh-results-scroll::-webkit-scrollbar-thumb,
        .advisor-ref-scroll::-webkit-scrollbar-thumb,
        .exh-search-summary::-webkit-scrollbar-thumb {
          background: rgba(102, 112, 123, 0.36);
          border-radius: 999px;
        }
        .exh-search-summary::-webkit-scrollbar {
          width: 6px;
        }
        .artist-search-scroll .exh-search-card,
        .exh-results-scroll .exh-search-card {
          flex: 0 0 clamp(310px, 26vw, 430px);
          height: 590px;
          overflow: hidden;
        }
        .advisor-ref-scroll .exh-search-card {
          flex: 0 0 clamp(310px, 26vw, 430px);
          height: 590px;
          overflow: hidden;
        }
        .artist-search-scroll .exh-search-summary {
          overflow-y: auto;
          overflow-x: hidden;
          display: block;
          flex: 1;
          min-height: 0;
          max-height: none;
        }
        .advisor-ref-scroll .advisor-ref-artist-card .exh-search-summary {
          overflow-y: auto;
          overflow-x: hidden;
          display: block;
          flex: 1;
          min-height: 0;
          max-height: none;
        }
        .artist-search-thumb-row {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 0.45rem;
        }
        .artist-search-thumb {
          display: block;
          width: 100%;
          min-height: 140px;
          max-height: 140px;
          border-radius: 10px;
          border: 1px solid var(--ap-border);
          background: var(--ap-bg-soft);
          overflow: hidden;
          position: relative;
          border-bottom: none !important;
        }
        .artist-search-thumb img {
          width: 100%;
          height: 100%;
          object-fit: contain;
          display: block;
          background: var(--ap-bg-soft);
        }
        .artist-search-scroll .exh-search-fallback {
          min-height: 140px;
          max-height: 140px;
        }
        .advisor-ref-scroll .advisor-ref-artist-card .exh-search-fallback {
          min-height: 140px;
          max-height: 140px;
        }
        .ap-progress-row {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.93rem;
          line-height: 1.45;
          color: var(--ap-muted);
          margin-top: 0.2rem;
          margin-bottom: 0.2rem;
        }
        .ap-progress-spinner {
          width: 0.95rem;
          height: 0.95rem;
          border: 2px solid rgba(74, 98, 120, 0.18);
          border-top-color: rgba(74, 98, 120, 0.52);
          border-radius: 50%;
          animation: ap-spin 0.9s linear infinite;
          flex: 0 0 auto;
        }
        @keyframes ap-spin {
          to { transform: rotate(360deg); }
        }
        @media (max-width: 900px) {
          .stApp [data-testid="stMainBlockContainer"],
          .stApp .block-container {
            max-width: 100vw !important;
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
          }
          .stApp [data-testid="stHeadingWithActionElements"] h1 {
            font-size: clamp(2.75rem, 8.2vw, 3.35rem) !important;
          }
          .stApp [data-testid="stVerticalBlockBorderWrapper"] {
            padding: 1rem !important;
            border-radius: 18px !important;
          }
          .exh-search-grid {
            grid-template-columns: 1fr;
            gap: 0.8rem;
          }
          .exh-search-thumb,
          .exh-search-fallback {
            min-height: 210px;
            max-height: 210px;
          }
          .artist-search-thumb {
            min-height: 110px;
            max-height: 110px;
          }
          .artist-search-scroll .exh-search-fallback {
            min-height: 110px;
            max-height: 110px;
          }
          .exh-results-scroll .exh-search-card {
            flex-basis: 84vw;
            height: auto;
            min-height: 600px;
            overflow: visible;
          }
          .exh-results-scroll .exh-search-summary {
            display: block;
            -webkit-line-clamp: unset;
            max-height: 12rem;
            overflow-y: auto;
            overflow-x: hidden;
          }
          .artist-search-scroll .exh-search-card {
            flex-basis: 84vw;
            height: auto;
            min-height: 600px;
            overflow: visible;
          }
          .artist-search-scroll .exh-search-summary {
            display: block;
            -webkit-line-clamp: unset;
            overflow-y: auto;
            overflow-x: hidden;
            flex: 1;
            min-height: 0;
            max-height: none;
          }
          .advisor-ref-scroll .advisor-ref-artist-card .exh-search-summary {
            display: block;
            -webkit-line-clamp: unset;
            overflow-y: auto;
            overflow-x: hidden;
            flex: 1;
            min-height: 0;
            max-height: none;
          }
          .advisor-ref-scroll .exh-search-card {
            flex-basis: 84vw;
            height: auto;
            min-height: 600px;
            overflow: visible;
          }
          .advisor-ref-scroll .advisor-ref-artist-card .exh-search-fallback {
            min-height: 110px;
            max-height: 110px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.title(APP_TITLE)


def _render_mode_heading(text: str) -> None:
    st.markdown(
        (
            '<div class="ap-section-heading">'
            f'<h3 class="ap-section-title" style="font-size:{MODE_HEADING_FONT_SIZE_PX}px;">{text}</h3>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_mode_explanation(text: str) -> None:
    st.markdown(
        (
            f'<p class="ap-section-explanation" style="font-size:{EXPLANATION_OF_MODES_FONT_SIZE_PX}px;">{text}</p>'
        ),
        unsafe_allow_html=True,
    )


def _run_search_with_spinner(search_fn, progress_line=None):
    if progress_line is None:
        progress_line = st.empty()

    def _render_searching() -> None:
        progress_line.markdown(
            (
                '<div class="ap-progress-row">'
                '<span class="ap-progress-spinner"></span>'
                f"<span>{escape('探しています...')}</span>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    def _complete() -> None:
        progress_line.empty()

    try:
        _render_searching()
        result = search_fn()
        return result, _complete
    except Exception:
        _complete()
        raise


def _split_markdown_and_image_blocks(markdown_text: str):
    lines = (markdown_text or "").splitlines()
    blocks = []
    text_buf = []
    i = 0
    while i < len(lines):
        line = lines[i]
        image_match = IMAGE_MARKDOWN_RE.match(line.strip())
        if not image_match:
            text_buf.append(line)
            i += 1
            continue

        if text_buf:
            text = "\n".join(text_buf).strip()
            if text:
                blocks.append(("markdown", text))
            text_buf = []

        images = []
        while i < len(lines):
            image_match = IMAGE_MARKDOWN_RE.match(lines[i].strip())
            if not image_match:
                break
            image_alt = image_match.group("alt") or "reference"
            image_url = image_match.group("url") or ""
            i += 1
            source_url = ""
            if i < len(lines):
                source_match = SOURCE_LINE_RE.match(lines[i].strip())
                if source_match:
                    source_url = source_match.group("url") or ""
                    i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            images.append(
                {
                    "alt": image_alt,
                    "image_url": image_url,
                    "source_url": source_url,
                }
            )
        if images:
            blocks.append(("gallery", images))

    if text_buf:
        text = "\n".join(text_buf).strip()
        if text:
            blocks.append(("markdown", text))
    return blocks


def _get_runtime_secret(*keys: str) -> str:
    for key in keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    try:
        secrets = st.secrets
    except Exception:
        secrets = None
    if secrets is None:
        return ""
    for key in keys:
        try:
            value = str(secrets.get(key, "")).strip()
        except Exception:
            value = ""
        if value:
            return value
    return ""


def _get_r2_settings() -> dict[str, str]:
    return {
        "endpoint": _get_runtime_secret("R2_ENDPOINT", "R2_ENDPOINT_URL", "R2_S3_ENDPOINT"),
        "bucket": _get_runtime_secret("R2_BUCKET"),
        "access_key": _get_runtime_secret("R2_ACCESS_KEY_ID"),
        "secret_key": _get_runtime_secret("R2_SECRET_ACCESS_KEY"),
        "region": _get_runtime_secret("R2_REGION") or "auto",
    }


@st.cache_resource(show_spinner=False)
def _get_r2_s3_client():
    if boto3 is None:
        return None
    settings = _get_r2_settings()
    if not settings["endpoint"] or not settings["access_key"] or not settings["secret_key"]:
        return None
    try:
        return boto3.client(
            "s3",
            endpoint_url=settings["endpoint"],
            aws_access_key_id=settings["access_key"],
            aws_secret_access_key=settings["secret_key"],
            region_name=settings["region"],
        )
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=1800)
def _resolve_existing_r2_key(r2_key: str) -> str:
    key = str(r2_key or "").strip().lstrip("/")
    if not key:
        return ""
    client = _get_r2_s3_client()
    settings = _get_r2_settings()
    bucket = settings.get("bucket", "")
    if client is None or not bucket:
        return ""
    candidates = [key]
    if key.startswith("data/phase1_seed10/"):
        candidates.append(key[len("data/") :])
    elif key.startswith("data/"):
        candidates.append(key[len("data/") :])
    for cand in candidates:
        try:
            client.head_object(Bucket=bucket, Key=cand)
            return cand
        except Exception:
            continue
    return ""


@st.cache_data(show_spinner=False, ttl=1800)
def _presign_r2_get_url(r2_key: str) -> str:
    resolved_key = _resolve_existing_r2_key(r2_key)
    if not resolved_key:
        return ""
    client = _get_r2_s3_client()
    settings = _get_r2_settings()
    bucket = settings.get("bucket", "")
    if client is None or not bucket:
        return ""
    try:
        return str(
            client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": resolved_key},
                ExpiresIn=1800,
            )
        )
    except Exception:
        return ""


@st.cache_data(show_spinner=False, ttl=1800)
def _local_image_path_to_data_uri(path_text: str) -> str:
    path = Path(str(path_text or "").strip())
    if not path.exists() or not path.is_file():
        return ""
    try:
        mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
        raw = path.read_bytes()
        return f"data:{mime};base64,{b64encode(raw).decode('ascii')}"
    except Exception:
        return ""


def _resolve_cached_or_remote_image_url(r2_key: object = "", local_path: object = "", direct_image_url: object = "") -> str:
    resolved = _presign_r2_get_url(str(r2_key or "").strip())
    if not resolved:
        resolved = _local_image_path_to_data_uri(str(local_path or "").strip())
    if not resolved:
        resolved = str(direct_image_url or "").strip()
    return resolved


def _build_standard_search_caption(total_rows: int, hit_rows: int, fair_rows: dict[str, int], total_hits: int) -> str:
    return (
        f"件数: 読込={int(total_rows or 0)} / ヒット={int(hit_rows or 0)} / "
        f"frieze={int(fair_rows.get('frieze_london', 0) or 0)} / "
        f"liste={int(fair_rows.get('liste', 0) or 0)}  \n"
        f"検索結果: {int(total_hits or 0)}件（横スクロールで閲覧 / タップで画像拡大）"
    )


def _render_black_caption(text: str, slot=None) -> None:
    escaped_text = escape(str(text or "")).replace("\n", "<br>")
    rendered = f'<div class="ap-black-caption">{escaped_text}</div>'
    if slot is None:
        st.markdown(rendered, unsafe_allow_html=True)
        return
    slot.markdown(rendered, unsafe_allow_html=True)


def _build_art_pulse_local_image_lookup(overview: dict) -> dict[str, dict[str, dict[str, str]]]:
    by_source: dict[str, dict[str, str]] = {}
    by_image_url: dict[str, dict[str, str]] = {}

    def _upsert(target: dict[str, dict[str, str]], key: str, ref: dict[str, str]) -> None:
        if not key:
            return
        current = dict(target.get(key, {}) or {})
        if not current:
            target[key] = ref
            return
        if not current.get("r2_key") and ref.get("r2_key"):
            target[key] = ref
            return
        if not current.get("local_path") and ref.get("local_path"):
            target[key] = ref

    plan = dict(overview.get("image_reference_plan", {}) or {})
    for key in ("exhibition_image_candidates", "artist_image_candidates"):
        for row in list(plan.get(key, []) or []):
            source_url = str(row.get("source_url") or "").strip()
            image_url = str(row.get("image_url") or "").strip()
            r2_key = str(row.get("r2_key") or "").strip()
            local_path_raw = str(row.get("local_path") or "").strip()
            local_path = ""
            if local_path_raw:
                local_file = Path(local_path_raw).expanduser()
                if local_file.exists():
                    local_path = str(local_file)
            ref = {"r2_key": r2_key, "local_path": local_path}
            _upsert(by_source, source_url, ref)
            _upsert(by_image_url, image_url, ref)

    return {"by_source": by_source, "by_image_url": by_image_url}


def _resolve_art_pulse_image_ref(item: dict, local_lookup: dict[str, dict[str, dict[str, str]]]) -> dict[str, str]:
    by_source = dict(local_lookup.get("by_source", {}) or {})
    by_image_url = dict(local_lookup.get("by_image_url", {}) or {})
    source_url = str(item.get("source_url") or "").strip()
    image_url = str(item.get("image_url") or "").strip()
    ref = dict(by_source.get(source_url) or by_image_url.get(image_url) or {})
    r2_key = str(ref.get("r2_key") or item.get("r2_key") or "").strip()
    local_path = str(ref.get("local_path") or item.get("local_path") or "").strip()
    if local_path and not Path(local_path).exists():
        local_path = ""
    return {"r2_key": r2_key, "local_path": local_path, "image_url": image_url}


def _render_responsive_image_gallery(images: list[dict], local_lookup: dict[str, dict[str, dict[str, str]]]) -> None:
    if not images:
        return
    html_items: list[str] = []
    for item in images:
        source_url = str(item.get("source_url") or "").strip()
        image_ref = _resolve_art_pulse_image_ref(item, local_lookup)
        image_url = _resolve_cached_or_remote_image_url(
            image_ref.get("r2_key"),
            image_ref.get("local_path"),
            image_ref.get("image_url"),
        )
        safe_src = escape(source_url, quote=True)

        if image_url:
            safe_img = escape(image_url, quote=True)
            image_html = (
                f'<a class="ap-gallery-thumb" href="{safe_img}" target="_blank" rel="noopener noreferrer" '
                'title="画像を拡大表示">'
                f'<img src="{safe_img}" alt="reference image" loading="lazy" /></a>'
            )
        else:
            image_html = '<div class="ap-gallery-fallback">参考画像は未取得です。<br>Sourceから確認できます。</div>'

        source_html = (
            f'<div class="ap-gallery-source">Source: <a href="{safe_src}" target="_blank" rel="noopener noreferrer">{safe_src}</a></div>'
            if source_url
            else '<div class="ap-gallery-source">Source: (not available)</div>'
        )

        html_items.append(
            (
                '<div class="ap-gallery-item">'
                f"{image_html}"
                f"{source_html}"
                "</div>"
            )
        )

    if html_items:
        st.markdown(f'<div class="ap-gallery">{"".join(html_items)}</div>', unsafe_allow_html=True)


def _render_markdown_with_galleries(
    markdown_text: str,
    local_lookup: dict[str, dict[str, dict[str, str]]],
    preserve_linebreaks: bool = False,
) -> None:
    for kind, payload in _split_markdown_and_image_blocks(markdown_text):
        if kind == "markdown":
            text = str(payload or "")
            if preserve_linebreaks:
                text = re.sub(r"(?<!\n)\n(?!\n)", "  \n", text)
            st.markdown(text)
        else:
            _render_responsive_image_gallery(payload, local_lookup)


def _build_exhibition_card_html(row: dict, idx: int) -> str:
    title = escape(str(row.get("exhibition_title") or "(untitled)"))
    source_url = str(row.get("source_url") or "").strip()
    safe_src = escape(source_url, quote=True)
    summary = escape(str(row.get("summary_display_ja") or "\u672a\u4ed8\u4e0e"))

    image_url = str(row.get("image_direct_url") or "").strip()
    if not image_url:
        image_url = _presign_r2_get_url(str(row.get("image_preview_r2_key") or ""))
    if not image_url:
        image_url = _local_image_path_to_data_uri(str(row.get("image_preview") or ""))
    if not image_url:
        reference_images = list(row.get("reference_images") or [])
        if reference_images:
            ref0 = reference_images[0] or {}
            image_url = _presign_r2_get_url(str(ref0.get("r2_key") or ""))
            if not image_url:
                image_url = _local_image_path_to_data_uri(str(ref0.get("local_path") or ""))
            if not image_url:
                image_url = str(ref0.get("image_url") or "").strip()

    if image_url:
        safe_img = escape(image_url, quote=True)
        image_html = (
            f'<a class="exh-search-thumb" href="{safe_img}" target="_blank" rel="noopener noreferrer" '
            f'title="\u753b\u50cf\u3092\u62e1\u5927\u8868\u793a" '
            f'style="background-image:url(\'{safe_img}\');'
            'background-size:contain;background-position:center center;'
            'background-repeat:no-repeat;"></a>'
        )
    else:
        image_html = (
            '<div class="exh-search-fallback">'
            "\u53c2\u8003\u753b\u50cf\u306f\u672a\u53d6\u5f97\u3067\u3059\u3002<br>"
            "Source\u304b\u3089\u78ba\u8a8d\u3067\u304d\u307e\u3059\u3002"
            "</div>"
        )

    source_html = (
        f'<p class="exh-search-source">Source: <a href="{safe_src}" '
        f'target="_blank" rel="noopener noreferrer">{safe_src}</a></p>'
        if source_url
        else '<p class="exh-search-source">Source: (not available)</p>'
    )

    return (
        '<div class="exh-search-card advisor-ref-exhibition-card">'
        f'<p class="exh-search-title">{idx}. {title}</p>'
        f"{image_html}"
        f"{source_html}"
        f'<p class="exh-search-summary">{summary}</p>'
        "</div>"
    )


def _build_artist_card_html(row: dict, idx: int) -> str:
    artist_name = str(row.get("artist_name") or "(untitled)").strip()
    artist_name_kana = str(row.get("artist_name_kana") or "").strip()
    title = escape(
        f"{artist_name}（{artist_name_kana}）" if artist_name_kana else artist_name
    )
    gallery = escape(str(row.get("gallery_name") or row.get("gallery") or "").strip())
    fair = escape(str(row.get("fair_label") or "").strip())
    source_url = str(row.get("source_url") or "").strip()
    safe_src = escape(source_url, quote=True)
    summary = escape(str(row.get("summary_display_ja") or "\u672a\u4ed8\u4e0e"))
    image_layout = str(row.get("artist_image_layout") or "").strip()

    preview_urls: list[str] = []
    preview_candidates = list(row.get("artist_image_preview_candidates") or [])[:ARTIST_SEARCH_THUMB_FROM_ARTIST]
    for candidate in preview_candidates:
        resolved = _resolve_cached_or_remote_image_url(
            candidate.get("r2_key"),
            candidate.get("local_path"),
            candidate.get("image_url"),
        )
        if resolved:
            preview_urls.append(resolved)

    if preview_urls and image_layout == "single_wide":
        safe_img = escape(preview_urls[0], quote=True)
        image_html = (
            f'<a class="exh-search-thumb" href="{safe_img}" target="_blank" rel="noopener noreferrer" '
            f'title="\u753b\u50cf\u3092\u62e1\u5927\u8868\u793a" '
            f'style="background-image:url(\'{safe_img}\');'
            'background-size:contain;background-position:center center;'
            'background-repeat:no-repeat;"></a>'
        )
    elif preview_urls:
        image_html = '<div class="artist-search-thumb-row">' + "".join(
            (
                f'<a class="artist-search-thumb" href="{escape(url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer" title="\u753b\u50cf\u3092\u62e1\u5927\u8868\u793a">'
                f'<img src="{escape(url, quote=True)}" alt="{title}" loading="lazy" /></a>'
            )
            for url in preview_urls
        ) + "</div>"
    else:
        image_html = (
            '<div class="exh-search-fallback">'
            "\u53c2\u8003\u753b\u50cf\u306f\u672a\u53d6\u5f97\u3067\u3059\u3002<br>"
            "Source\u304b\u3089\u78ba\u8a8d\u3067\u304d\u307e\u3059\u3002"
            "</div>"
        )

    meta_html = ""
    if gallery or fair:
        meta_text = " / ".join([item for item in [gallery, fair] if item])
        meta_html = f'<p class="exh-search-source">{meta_text}</p>'
    source_html = (
        f'<p class="exh-search-source">Source: <a href="{safe_src}" '
        f'target="_blank" rel="noopener noreferrer">{safe_src}</a></p>'
        if source_url
        else '<p class="exh-search-source">Source: (not available)</p>'
    )

    return (
        '<div class="exh-search-card advisor-ref-artist-card">'
        f'<p class="exh-search-title">{idx}. {title}</p>'
        f"{image_html}"
        f"{meta_html}"
        f"{source_html}"
        f'<p class="exh-search-summary">{summary}</p>'
        "</div>"
    )


def _render_exhibition_result_cards(rows: list[dict], start_index: int = 1) -> None:
    cards: list[str] = []
    for idx, row in enumerate(rows, start=start_index):
        cards.append(_build_exhibition_card_html(row, idx))

    if cards:
        st.markdown(f'<div class="exh-results-scroll">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_artist_result_cards(rows: list[dict], start_index: int = 1) -> None:
    cards: list[str] = []
    for idx, row in enumerate(rows, start=start_index):
        row_copy = dict(row)
        if not row_copy.get("summary_display_ja"):
            row_copy["summary_display_ja"] = build_artist_summary_ja(row, max_chars=ARTIST_SEARCH_SUMMARY_MAX_CHARS)
        cards.append(_build_artist_card_html(row_copy, idx))

    if cards:
        st.markdown(f'<div class="artist-search-scroll">{"".join(cards)}</div>', unsafe_allow_html=True)


def _slice_rows_by_page(rows: list[dict], page_state_key: str) -> tuple[list[dict], int, int]:
    total_rows = len(rows)
    total_pages = max(1, (total_rows + SEARCH_RESULTS_PAGE_SIZE - 1) // SEARCH_RESULTS_PAGE_SIZE)
    try:
        current_page = int(st.session_state.get(page_state_key, 1))
    except Exception:
        current_page = 1
    current_page = min(max(current_page, 1), total_pages)
    st.session_state[page_state_key] = current_page

    start = (current_page - 1) * SEARCH_RESULTS_PAGE_SIZE
    end = start + SEARCH_RESULTS_PAGE_SIZE
    return rows[start:end], current_page, total_pages


def _render_page_switcher(page_state_key: str, current_page: int, total_pages: int) -> None:
    if total_pages <= 1:
        return
    options = list(range(1, total_pages + 1))
    if st.session_state.get(page_state_key) not in options:
        st.session_state[page_state_key] = current_page
    st.markdown('<p class="ap-black-caption" style="margin:0 0 -0.45rem 0;">Page（30件づつ表示）</p>', unsafe_allow_html=True)
    st.radio("", options=options, horizontal=True, key=page_state_key, label_visibility="collapsed")


@st.cache_data(show_spinner=False)
def get_exhibition_search_data():
    return load_exhibition_records_readonly()


@st.cache_data(show_spinner=False)
def get_art_pulse_available_years() -> list[int]:
    return resolve_current_exhibitions_available_years()


@st.cache_data(show_spinner=False)
def get_artist_search_data():
    return load_artist_records_readonly()


@st.cache_data(show_spinner=False)
def get_gallery_list_data():
    return load_gallery_list_records_readonly()


def _exhibition_row_label(row: dict) -> str:
    title = row.get("exhibition_title") or "(無題)"
    gallery = row.get("gallery_name") or "(ギャラリー不明)"
    fair = row.get("fair_label") or "(フェア不明)"
    year = row.get("year") or "-"
    return f"[{fair}] {gallery} | {title} ({year})"


def _render_evidence_summary(summary: dict) -> None:
    st.markdown("**根拠サマリ**")
    st.write(summary)


def _render_evidence_urls(
    title: str,
    exhibition_urls: list,
    artist_urls: list,
    empty_message: str = "表示できる根拠URLはありません。",
) -> None:
    ex_rows = exhibition_urls or []
    ar_rows = artist_urls or []
    ex_urls = [str(x) for x in ex_rows if str(x).strip()]
    ar_urls = [str(x) for x in ar_rows if str(x).strip()]
    total = len(ex_urls) + len(ar_urls)
    st.markdown(f"**{title}**")
    st.caption(f"URL件数: {total}件")
    if total == 0:
        st.info(empty_message)
        return

    ex_table = [{"ref": f"EX-{idx:02d}", "url": url} for idx, url in enumerate(ex_urls[:30], start=1)]
    ar_table = [{"ref": f"AR-{idx:02d}", "url": url} for idx, url in enumerate(ar_urls[:30], start=1)]

    c1, c2 = st.columns(2)
    with c1:
        st.write(f"Exhibition URL数: {len(ex_urls)}")
        if ex_table:
            st.dataframe(ex_table, use_container_width=True, hide_index=True, height=220)
        else:
            st.caption("表示できるExhibition根拠URLはありません。")
    with c2:
        st.write(f"Artist URL数: {len(ar_urls)}")
        if ar_table:
            st.dataframe(ar_table, use_container_width=True, hide_index=True, height=220)
        else:
            st.caption("表示できるArtist根拠URLはありません。")


def _render_reference_image_candidates(
    title: str,
    reference_images: dict,
    target_total: int = 8,
    empty_message: str = "参考画像候補はありません。",
    compact_advisor_cards: bool = False,
    show_title: bool = True,
    show_summary: bool = True,
    show_empty_message: bool = True,
    evidence_context: dict | None = None,
) -> None:
    def _match_advisor_reference_evidence(item: dict) -> dict:
        if not isinstance(evidence_context, dict):
            return {}
        kind = str(item.get("kind") or "").strip()
        label = str(item.get("label") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        if kind == "artist":
            for row in list(evidence_context.get("artist_evidence", []) or []):
                if source_url and str(row.get("source_url") or "").strip() != source_url:
                    continue
                if label and str(row.get("artist_name") or "").strip() != label:
                    continue
                return dict(row)
            return {}
        for row in list(evidence_context.get("exhibition_evidence", []) or []):
            if source_url and str(row.get("source_url") or "").strip() != source_url:
                continue
            if label and str(row.get("title") or "").strip() != label:
                continue
            return dict(row)
        return {}

    def _render_reference_image_cards(items: list[dict]) -> None:
        cards: list[str] = []
        for idx, item in enumerate(items, start=1):
            kind = str(item.get("kind") or "").strip()
            if compact_advisor_cards and evidence_context:
                matched_row = _match_advisor_reference_evidence(item)
                if kind == "artist":
                    preview_candidates = list(matched_row.get("artist_image_preview_candidates") or [])
                    if not preview_candidates:
                        preview_candidates = [{
                            "local_path": str(item.get("local_path") or "").strip(),
                            "r2_key": str(item.get("r2_key") or "").strip(),
                            "image_url": str(item.get("image_url") or "").strip(),
                        }]
                    artist_summary = str(
                        matched_row.get("summary_ja")
                        or matched_row.get("headline_ja")
                        or matched_row.get("text")
                        or ""
                    ).strip()
                    if not artist_summary and matched_row:
                        artist_summary = build_artist_summary_ja(
                            matched_row,
                            max_chars=ARTIST_SEARCH_SUMMARY_MAX_CHARS,
                        )
                    artist_row = {
                        "artist_name": str(item.get("label") or "").strip(),
                        "artist_name_kana": str(matched_row.get("artist_name_kana") or item.get("artist_name_kana") or "").strip(),
                        "gallery_name": str(matched_row.get("gallery") or item.get("gallery") or "").strip(),
                        "gallery": str(matched_row.get("gallery") or item.get("gallery") or "").strip(),
                        "fair_label": str(matched_row.get("fair_label") or item.get("fair_label") or "").strip(),
                        "source_url": str(item.get("source_url") or matched_row.get("source_url") or "").strip(),
                        "summary_display_ja": artist_summary,
                        "artist_image_preview_candidates": preview_candidates,
                    }
                    cards.append(_build_artist_card_html(artist_row, idx))
                else:
                    exhibition_summary = str(
                        matched_row.get("summary_ja")
                        or matched_row.get("headline_ja")
                        or matched_row.get("text")
                        or ""
                    ).strip()
                    if not exhibition_summary and matched_row:
                        exhibition_summary = build_exhibition_summary_ja(
                            matched_row,
                            max_chars=EXHIBITION_SEARCH_SUMMARY_MAX_CHARS,
                        )
                    exhibition_row = {
                        "exhibition_title": str(item.get("label") or "").strip(),
                        "source_url": str(item.get("source_url") or matched_row.get("source_url") or "").strip(),
                        "summary_display_ja": exhibition_summary,
                        "image_preview_r2_key": str(matched_row.get("image_preview_r2_key") or item.get("r2_key") or "").strip(),
                        "image_preview": str(matched_row.get("image_preview") or item.get("local_path") or "").strip(),
                        "image_direct_url": str(item.get("image_url") or "").strip(),
                    }
                    cards.append(_build_exhibition_card_html(exhibition_row, idx))
                continue

            source_url = str(item.get("source_url") or "").strip()
            gallery = escape(str(item.get("gallery") or "").strip())
            kind_label = "Artist" if kind == "artist" else "Exhibition"
            entity_label = escape(str(item.get("label") or "").strip())
            title_text = " / ".join([part for part in [kind_label, entity_label or gallery] if part]) or kind_label

            image_ref = _resolve_art_pulse_image_ref(item, {"by_source": {}, "by_image_url": {}})
            r2_url = _presign_r2_get_url(str(image_ref.get("r2_key") or ""))
            local_path = str(image_ref.get("local_path") or "").strip()
            direct_image_url = str(image_ref.get("image_url") or "").strip()
            image_url = r2_url or _local_image_path_to_data_uri(local_path) or direct_image_url

            if image_url:
                safe_img = escape(image_url, quote=True)
                image_html = (
                    f'<a class="exh-search-thumb" href="{safe_img}" target="_blank" rel="noopener noreferrer" '
                    f'title="画像を拡大表示" '
                    f'style="background-image:url(\'{safe_img}\');'
                    'background-size:contain;background-position:center center;'
                    'background-repeat:no-repeat;"></a>'
                )
            else:
                image_html = (
                    '<div class="exh-search-fallback">'
                    "参考画像は未取得です。<br>"
                    "Sourceから確認できます。"
                    "</div>"
                )

            meta_text = " / ".join([part for part in [gallery, escape(str(item.get("fair_label") or "").strip())] if part])
            meta_html = f'<p class="exh-search-source">{meta_text}</p>' if meta_text else ""
            source_html = (
                f'<p class="exh-search-source">Source: <a href="{escape(source_url, quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{escape(source_url)}</a></p>'
                if source_url
                else '<p class="exh-search-source">Source: (not available)</p>'
            )
            extra_html = source_html if compact_advisor_cards else f"{meta_html}{source_html}"

            cards.append(
                (
                    '<div class="exh-search-card">'
                    f'<p class="exh-search-title">{idx}. {escape(title_text)}</p>'
                    f"{image_html}"
                    f"{extra_html}"
                    "</div>"
                )
            )
        if cards:
            container_class = "advisor-ref-scroll" if compact_advisor_cards else "exh-results-scroll"
            st.markdown(f'<div class="{container_class}">{"".join(cards)}</div>', unsafe_allow_html=True)

    rows = []
    if isinstance(reference_images, dict):
        rows = list(reference_images.get("all", []) or [])
    if show_title and title:
        st.markdown(f"**{title}**")
    if show_summary:
        summary = {
            "目安": target_total,
            "参考画像候補件数": len(rows),
        }
        if isinstance(reference_images, dict):
            if "target_exhibition_images" in reference_images:
                summary["目安(Exhibition)"] = reference_images.get("target_exhibition_images")
            if "target_artist_images" in reference_images:
                summary["目安(Artist)"] = reference_images.get("target_artist_images")
        st.write(summary)
    if rows:
        _render_reference_image_cards(rows[:8])
    elif show_empty_message:
        st.info(empty_message)


def _render_compact_generated_image(image_source, caption: str = "AI generated") -> None:
    if isinstance(image_source, (bytes, bytearray)):
        raw = bytes(image_source)
        mime = "image/png"
        if raw.startswith(b"\xff\xd8"):
            mime = "image/jpeg"
        elif raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
            mime = "image/webp"
        image_href = f"data:{mime};base64,{b64encode(raw).decode('ascii')}"
    else:
        image_href = str(image_source or "").strip()

    if not image_href:
        return

    st.markdown(
        (
            '<div class="advisor-generated-image-wrap">'
            f'<a class="advisor-generated-image-link" href="{escape(image_href, quote=True)}" '
            'target="_blank" rel="noopener noreferrer" title="画像を拡大表示">'
            f'<img src="{escape(image_href, quote=True)}" alt="{escape(caption, quote=True)}">'
            "</a>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_art_pulse() -> None:
    _render_mode_heading("Art Pulse")
    _render_mode_explanation("8名の記者が「世界トップのアートフェア」を取材し、記事を執筆する")

    available_years = get_art_pulse_available_years()
    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "取材範囲",
        FAIR_OPTIONS,
        index=2,
        key="artpulse_fair",
    )
    selected_year: int | None = None
    if available_years:
        selected_year = int(
            col2.selectbox(
                "対象年",
                options=available_years,
                index=0,
                key="artpulse_selected_year",
            )
        )
    else:
        col2.text_input("対象年", value="利用可能な年がありません", disabled=True, key="artpulse_selected_year_empty")

    reporter = st.selectbox(
        "担当記者（8人）",
        options=PERSONAS,
        format_func=lambda p: f"{p['label']} - {p['description']}",
        key="artpulse_reporter",
    )
    reporter_angles = list(reporter.get("angles", []) or [])
    def _format_angle_full(angle: dict) -> str:
        label = str(angle.get("label") or "")
        description = str(angle.get("description") or "")
        return f"{label}：{description}" if description else label

    if reporter_angles:
        selected_angle = st.selectbox(
            "テーマ",
            options=reporter_angles,
            format_func=_format_angle_full,
            key="artpulse_angle",
        )
        angle_keys = [str(selected_angle.get("key") or "")]
    else:
        st.warning("この記者に切り口が定義されていません。")
        angle_keys = []

    st.caption("条件を選んで「Art Pulse」を押すと担当記者が記事を書きます。")
    run = st.button("Art Pulse", key="artpulse_generate")
    reset_article = st.button("リセット", key="artpulse_reset_result")
    if reset_article:
        st.session_state.pop("artpulse_result", None)
        st.rerun()

    if run:
        if selected_year is None:
            st.warning("Art Pulse で参照可能なExhibition年データが見つかりません。")
            return
        progress_line = st.empty()
        waiting_line = st.empty()
        waiting_line.caption("担当記者が執筆中...数分おまちください。")

        def _render_progress_row(text: str, active: bool) -> None:
            if active:
                progress_line.markdown(
                    (
                        '<div class="ap-progress-row">'
                        '<span class="ap-progress-spinner"></span>'
                        f"<span>{escape(text)}</span>"
                        "</div>"
                    ),
                    unsafe_allow_html=True,
                )
            else:
                progress_line.caption(text)

        def _on_progress(pct: int) -> None:
            safe_pct = max(0, min(100, int(pct)))
            if safe_pct >= 100:
                _render_progress_row("執筆完了", active=False)
                waiting_line.empty()
                return
            _render_progress_row(f"{safe_pct}%", active=True)

        try:
            _on_progress(5)
            overview = build_art_pulse_overview(
                fair_label=fair_mode,
                reporter_id=reporter["id"],
                angle_keys=angle_keys,
                target_year=selected_year,
            )
            _on_progress(20)
            draft = generate_art_pulse_draft(
                overview=overview,
                reporter_id=reporter["id"],
                angle_keys=angle_keys,
                progress_callback=_on_progress,
            )
            _on_progress(100)
            st.session_state["artpulse_result"] = {"overview": overview, "draft": draft}
        except Exception as exc:
            progress_line.empty()
            waiting_line.empty()
            st.error(f"Art Pulse 生成エラー: {type(exc).__name__}: {exc}")
            return

    result = st.session_state.get("artpulse_result")
    if not result:
        return

    overview = result.get("overview", {})
    draft = result.get("draft", {})
    local_lookup = _build_art_pulse_local_image_lookup(overview if isinstance(overview, dict) else {})
    st.markdown(f"### {draft.get('title', 'Art Pulse')}")
    _render_markdown_with_galleries(draft.get("body", ""), local_lookup)
    st.caption(f"本文文字数（Source行を除く）: {int(draft.get('body_chars', 0))} / 2000")


def render_exhibition_search() -> None:
    _render_mode_heading("Exhibition Search")
    _render_mode_explanation("全ギャラリーの「展示」検索")
    try:
        data = get_exhibition_search_data()
    except Exception as exc:
        st.error(f"Exhibition 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    results_key = "exh_search_results"
    query_key = "exh_search_query"
    keyword_key = "exh_keyword"
    page_key = "exh_search_page"
    search_reset_requested_key = "exh_search_reset_requested"
    spinner_complete = None

    if st.session_state.pop(search_reset_requested_key, False):
        st.session_state[keyword_key] = ""
        st.session_state.pop(results_key, None)
        st.session_state.pop(query_key, None)
        st.session_state.pop(page_key, None)

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "対象範囲",
        FAIR_OPTIONS,
        index=2,
        key="exh_fair_filter",
    )
    keyword = col2.text_input(
        "キーワード",
        value="",
        placeholder="例 : テーマ / ジャンル / アーティスト名 など",
        key=keyword_key,
    )
    _render_black_caption("キーワード入力 ＋ Search で「展示情報」を表示します。")
    search_clicked = st.button("Search", key="exh_search_button")
    if st.button("リセット", key="exh_search_reset_button"):
        st.session_state[search_reset_requested_key] = True
        st.rerun()
    status_slot = st.empty()
    current_query = {
        "fair": fair_mode,
        "keyword": (keyword or "").strip(),
    }
    if search_clicked:
        try:
            result_rows, spinner_complete = _run_search_with_spinner(
                lambda: search_exhibitions(
                    data.records,
                    fair_mode,
                    current_query["keyword"],
                    limit=max(1, len(data.records)),
                ),
                progress_line=status_slot,
            )
            st.session_state[results_key] = result_rows
            st.session_state[page_key] = 1
        except Exception as exc:
            st.error(f"Exhibition 検索エラー: {type(exc).__name__}: {exc}")
            return
        st.session_state[query_key] = current_query

    filtered = st.session_state.get(results_key)
    if filtered is None:
        if spinner_complete:
            spinner_complete()
        return

    if data.warnings:
        with st.expander("警告（Exhibition Search）", expanded=False):
            for warning in data.warnings[:20]:
                st.write(f"- {warning}")

    if not filtered:
        if spinner_complete:
            spinner_complete()
        st.warning("条件に一致する展示データはありません。")
        return

    all_rows = list(filtered)
    total_hits = len(all_rows)
    display_rows: list[dict] = []
    for row in all_rows:
        row_copy = dict(row)
        row_copy["exhibition_title"] = _derive_title(row_copy)
        row_copy["summary_display_ja"] = build_exhibition_summary_ja(
            row_copy,
            max_chars=EXHIBITION_SEARCH_SUMMARY_MAX_CHARS,
        )
        display_rows.append(row_copy)

    page_rows, current_page, total_pages = _slice_rows_by_page(display_rows, page_key)
    page_start_index = (current_page - 1) * SEARCH_RESULTS_PAGE_SIZE + 1
    _render_exhibition_result_cards(page_rows, start_index=page_start_index)
    _render_page_switcher(page_key, current_page, total_pages)
    if spinner_complete:
        spinner_complete()
    _render_black_caption(
        _build_standard_search_caption(data.total_rows, len(filtered), data.fair_rows, total_hits),
        slot=status_slot,
    )


def render_artist_search() -> None:
    _render_mode_heading("Artist Search")
    _render_mode_explanation("全ギャラリーの「作家」検索")

    try:
        data = get_artist_search_data()
    except Exception as exc:
        st.error(f"Artist 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    results_key = "artist_search_results"
    query_key = "artist_search_query"
    keyword_key = "artist_keyword"
    page_key = "artist_search_page"
    search_reset_requested_key = "artist_search_reset_requested"
    spinner_complete = None

    if st.session_state.pop(search_reset_requested_key, False):
        st.session_state[keyword_key] = ""
        st.session_state.pop(results_key, None)
        st.session_state.pop(query_key, None)
        st.session_state.pop(page_key, None)

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "対象範囲",
        FAIR_OPTIONS,
        index=2,
        key="artist_fair_filter",
    )
    keyword = col2.text_input(
        "キーワード",
        value="",
        placeholder="例 : ジャンル / テーマ / アーティスト名 など",
        key=keyword_key,
    )
    _render_black_caption("キーワード入力 ＋ Search で「作家情報」を表示します。")
    search_clicked = st.button("Search", key="artist_search_button")
    if st.button("リセット", key="artist_search_reset_button"):
        st.session_state[search_reset_requested_key] = True
        st.rerun()
    status_slot = st.empty()
    current_query = {
        "fair": fair_mode,
        "keyword": (keyword or "").strip(),
    }
    if search_clicked:
        try:
            result_rows, spinner_complete = _run_search_with_spinner(
                lambda: search_artists(
                    data.records,
                    fair_mode,
                    current_query["keyword"],
                    limit=max(1, len(data.records)),
                ),
                progress_line=status_slot,
            )
            st.session_state[results_key] = result_rows
            st.session_state[page_key] = 1
        except Exception as exc:
            st.error(f"Artist 検索エラー: {type(exc).__name__}: {exc}")
            return
        st.session_state[query_key] = current_query

    filtered = st.session_state.get(results_key)
    if filtered is None:
        if spinner_complete:
            spinner_complete()
        return

    if data.warnings:
        with st.expander("警告（Artist Search）", expanded=False):
            for warning in data.warnings[:20]:
                st.write(f"- {warning}")

    if not filtered:
        if spinner_complete:
            spinner_complete()
        st.warning("条件に一致する作家データはありません。")
        return

    all_rows = list(filtered)
    total_hits = len(all_rows)
    display_rows: list[dict] = []
    for row in all_rows:
        row_copy = dict(row)
        row_copy["summary_display_ja"] = build_artist_summary_ja(
            row_copy,
            max_chars=ARTIST_SEARCH_SUMMARY_MAX_CHARS,
        )
        display_rows.append(row_copy)

    page_rows, current_page, total_pages = _slice_rows_by_page(display_rows, page_key)
    page_start_index = (current_page - 1) * SEARCH_RESULTS_PAGE_SIZE + 1
    _render_artist_result_cards(page_rows, start_index=page_start_index)
    _render_page_switcher(page_key, current_page, total_pages)
    if spinner_complete:
        spinner_complete()
    _render_black_caption(
        _build_standard_search_caption(data.total_rows, len(filtered), data.fair_rows, total_hits),
        slot=status_slot,
    )


def _build_artwork_result_artist_rows(rows: list[dict]) -> list[dict]:
    try:
        artist_data = get_artist_search_data()
        artist_rows = list(artist_data.records)
    except Exception:
        artist_rows = []

    artist_by_identity = {
        str(row.get("artist_identity_key") or "").strip(): row
        for row in artist_rows
        if str(row.get("artist_identity_key") or "").strip()
    }
    artist_by_source = {
        str(row.get("source_url") or "").strip(): row
        for row in artist_rows
        if str(row.get("source_url") or "").strip()
    }

    display_rows: list[dict] = []
    for row in rows:
        source_url = str(row.get("source_url") or "").strip()
        identity_key = str(row.get("artist_identity_key") or "").strip()
        matched_row = dict(artist_by_identity.get(identity_key) or artist_by_source.get(source_url) or {})
        summary_ja = str(matched_row.get("summary_ja") or "").strip()
        display_rows.append(
            {
                "artist_name": str(matched_row.get("artist_name") or row.get("artist_name_en") or "").strip() or "(artist unknown)",
                "artist_name_kana": str(matched_row.get("artist_name_kana") or "").strip(),
                "gallery_name": str(matched_row.get("gallery_name") or row.get("gallery_name_en") or "").strip(),
                "gallery": str(matched_row.get("gallery_name") or row.get("gallery_name_en") or "").strip(),
                "fair_label": str(row.get("fair_label") or matched_row.get("fair_label") or "").strip(),
                "source_url": source_url or str(matched_row.get("source_url") or "").strip(),
                "summary_ja": summary_ja,
                "summary_display_ja": build_artist_summary_ja(
                    {"summary_ja": summary_ja},
                    max_chars=ARTIST_SEARCH_SUMMARY_MAX_CHARS,
                ),
                "artist_image_preview_candidates": [
                    {
                        "r2_key": str(row.get("r2_key") or "").strip(),
                        "local_path": resolve_current_artist_works_local_path(
                            row.get("local_path"),
                            fair_slug=str(row.get("fair_slug") or "").strip(),
                        ),
                        "image_url": str(row.get("image_url") or "").strip(),
                    }
                ],
                "artist_image_layout": "single_wide",
            }
        )
    return display_rows


def _count_artwork_hits_by_fair(rows: list[dict]) -> dict[str, int]:
    counts = {"frieze_london": 0, "liste": 0}
    for row in rows:
        fair_slug = str(row.get("fair_slug") or "").strip()
        if fair_slug in counts:
            counts[fair_slug] += 1
    return counts


def render_artwork_search() -> None:
    _render_mode_heading("Art Work Search")
    _render_mode_explanation("全アーティストの「作品」検索")

    results_key = "artwork_search_results"
    query_key = "artwork_search_query"
    text_query_key = "artwork_search_text_query"
    fair_filter_key = "artwork_search_fair_filter"
    page_key = "artwork_search_page"
    reset_requested_key = "artwork_search_reset_requested"
    uploaded_image_nonce_key = "artwork_search_uploaded_image_nonce"
    spinner_complete = None

    if st.session_state.pop(reset_requested_key, False):
        current_nonce = int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)
        st.session_state[text_query_key] = ""
        st.session_state.pop(results_key, None)
        st.session_state.pop(query_key, None)
        st.session_state.pop(page_key, None)
        st.session_state.pop(f"artwork_search_uploaded_image_{current_nonce}", None)
        st.session_state[uploaded_image_nonce_key] = current_nonce + 1

    col1, col2 = st.columns([1, 1])
    fair_filter = col1.selectbox(
        "対象範囲",
        FAIR_OPTIONS,
        index=2,
        key=fair_filter_key,
    )
    text_query = col2.text_input(
        "キーワードで類似検索（英語可）",
        value="",
        placeholder="例 : 幾何学 / 赤い抽象画 / 人物 / Flour など",
        key=text_query_key,
    )

    uploader_key = f"artwork_search_uploaded_image_{int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)}"
    uploaded_image = st.file_uploader(
        "画像添付で類似検索",
        type=["png", "jpg", "jpeg", "webp"],
        key=uploader_key,
        label_visibility="collapsed",
    )
    uploaded_image_bytes = uploaded_image.getvalue() if uploaded_image is not None else b""
    if uploaded_image_bytes:
        st.caption("query image: session-only")
        _render_compact_generated_image(uploaded_image_bytes, caption="query image")

    _render_black_caption("キーワード or 画像で類似する「作品」を表示します。")
    search_clicked = st.button("Search", key="artwork_search_button")
    if st.button("リセット", key="artwork_search_reset_button"):
        st.session_state[reset_requested_key] = True
        st.rerun()

    status_slot = st.empty()
    current_query = {
        "mode": "image" if uploaded_image_bytes else "text",
        "fair_filter": fair_filter,
        "text_query": (text_query or "").strip(),
        "has_uploaded_image": bool(uploaded_image_bytes),
    }

    if search_clicked:
        if not uploaded_image_bytes and not current_query["text_query"]:
            st.warning("text query または image query を入力してください。")
            return
        try:
            if uploaded_image_bytes:
                result, spinner_complete = _run_search_with_spinner(
                    lambda: search_artwork_images_by_image(
                        uploaded_image_bytes,
                        fair_filter=fair_filter,
                        top_k=ARTWORK_SEARCH_TOP_K_DEFAULT,
                    ),
                    progress_line=status_slot,
                )
            else:
                result, spinner_complete = _run_search_with_spinner(
                    lambda: search_artwork_images_by_text(
                        current_query["text_query"],
                        fair_filter=fair_filter,
                        top_k=ARTWORK_SEARCH_TOP_K_DEFAULT,
                    ),
                    progress_line=status_slot,
                )
            st.session_state[results_key] = result
            st.session_state[query_key] = current_query
            st.session_state[page_key] = 1
        except Exception as exc:
            st.error(f"ArtWork Search エラー: {type(exc).__name__}: {exc}")
            return

    result = st.session_state.get(results_key)
    if result is None:
        if spinner_complete:
            spinner_complete()
        return

    warnings = list(result.get("warnings") or [])
    if warnings:
        with st.expander("警告（ArtWork Search）", expanded=False):
            for warning in warnings[:20]:
                st.write(f"- {warning}")

    rows = list(result.get("rows") or [])
    corpus_stats = dict(result.get("corpus_stats") or {})
    hit_fair_counts = _count_artwork_hits_by_fair(rows)
    if not rows:
        if spinner_complete:
            spinner_complete()
        _render_black_caption(
            _build_standard_search_caption(
                int(corpus_stats.get("images_total", 0) or 0),
                len(rows),
                hit_fair_counts,
                len(rows),
            ),
            slot=status_slot,
        )
        st.warning("条件に一致する作品画像はありません。")
        return

    display_rows = _build_artwork_result_artist_rows(rows)
    page_rows, current_page, total_pages = _slice_rows_by_page(display_rows, page_key)
    page_start_index = (current_page - 1) * SEARCH_RESULTS_PAGE_SIZE + 1
    _render_artist_result_cards(page_rows, start_index=page_start_index)
    _render_page_switcher(page_key, current_page, total_pages)
    if spinner_complete:
        spinner_complete()
    _render_black_caption(
        _build_standard_search_caption(
            int(corpus_stats.get("images_total", 0) or 0),
            len(rows),
            hit_fair_counts,
            len(rows),
        ),
        slot=status_slot,
    )



def _clip_compact_text(text: object, max_chars: int = 280) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _unwrap_followup_answer_text(raw_output: object) -> str:
    if isinstance(raw_output, dict):
        raw = str(raw_output.get("answer") or "").strip()
    else:
        raw = str(raw_output or "").strip()
    if not raw:
        return ""

    candidates = [raw]
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
    if fence_match:
        candidates.insert(0, fence_match.group(1).strip())
    brace_match = re.search(r"\{[\s\S]*\}", raw)
    if brace_match:
        candidates.insert(0, brace_match.group(0).strip())

    parsed_payload = None
    for candidate in candidates:
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                parsed_payload = parsed
                break
            if isinstance(parsed, str) and parsed.strip():
                parsed_payload = {"answer": parsed}
                break
        if parsed_payload is not None:
            break

    if isinstance(parsed_payload, dict):
        answer_text = str(parsed_payload.get("answer") or "").strip()
    else:
        answer_text = raw

    if raw and raw.lstrip().startswith("{") and '"answer"' in raw:
        answer_field = re.search(r'"answer"\s*:\s*"([\s\S]*)', raw)
        if answer_field:
            answer_text = answer_field.group(1).strip() or answer_text

    answer_text = (
        answer_text.replace(r"\r\n", "\n")
        .replace(r"\n\n", "\n\n")
        .replace(r"\n", "\n")
        .replace(r"\r", "\n")
        .replace(r'\"', '"')
    )
    answer_text = re.sub(r'"\s*,\s*"memory_summary"\s*:\s*"[\s\S]*$', "", answer_text).strip()
    answer_text = re.sub(r'"\s*\}\s*$', "", answer_text).strip()
    answer_text = _ensure_plain_answer_text(answer_text)
    if not answer_text:
        fallback = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
        fallback = (
            fallback.replace(r"\r\n", "\n")
            .replace(r"\n\n", "\n\n")
            .replace(r"\n", "\n")
            .replace(r"\r", "\n")
            .replace(r'\"', '"')
        )
        fallback = re.sub(r'^\s*\{\s*"answer"\s*:\s*', "", fallback).strip()
        fallback = re.sub(r'"\s*,\s*"memory_summary"\s*:\s*"[\s\S]*$', "", fallback).strip()
        fallback = re.sub(r'"\s*\}\s*$', "", fallback).strip()
        answer_text = _ensure_plain_answer_text(fallback) or fallback
    answer_text = _normalize_answer_text(answer_text)
    answer_text = re.sub(r"^\s*-\s*$", "", answer_text, flags=re.MULTILINE)
    answer_text = re.sub(r"^\s*-\s+", "", answer_text)
    return answer_text.strip()


def _finalize_followup_answer_text(text: object, soft_limit: int = 850) -> str:
    cleaned = _normalize_answer_text(_unwrap_followup_answer_text(text))
    if not cleaned:
        return ""
    if len(cleaned) > soft_limit:
        truncated = cleaned[:soft_limit]
        sentence_ends = [truncated.rfind(mark) for mark in ("。", "！", "？", ".", "!", "?")]
        cut = max(sentence_ends)
        if cut >= max(soft_limit // 2, 80):
            cleaned = truncated[: cut + 1].strip()
        else:
            newline_cut = max(truncated.rfind("\n\n"), truncated.rfind("\n- "), truncated.rfind("\n"))
            if newline_cut >= max(soft_limit // 2, 80):
                cleaned = truncated[:newline_cut].strip()
            else:
                cleaned = truncated.rstrip(" 、,;:-—・")
    cleaned = re.sub(r"\n-\s*$", "", cleaned).strip()
    cleaned = _ensure_natural_ending(cleaned)
    cleaned = _normalize_answer_text(cleaned)
    return cleaned.strip()

def _sentence_compact_summary(text: object, max_chars: int = 260, max_sentences: int = 3) -> str:
    cleaned = _clip_compact_text(
        re.sub(r"!?\[[^\]]*\]\([^)]*\)", "", str(text or "")),
        max_chars=max_chars * 3,
    )
    if not cleaned:
        return ""
    parts = [
        part.strip()
        for part in re.split(r"(?<=[\u3002\uff01\uff1f!?])\s*", cleaned)
        if part.strip()
    ]
    selected: list[str] = []
    total = ""
    for part in parts:
        candidate = (" ".join(selected + [part])).strip()
        if len(candidate) > max_chars and selected:
            break
        selected.append(part)
        total = candidate
        if len(selected) >= max_sentences:
            break
    return total or _clip_compact_text(cleaned, max_chars=max_chars)


def _build_advisor_followup_reference_core_context(context: dict) -> dict:
    selection = dict((context or {}).get("selection", {}) or {})
    return {
        "selection": selection,
        "exhibition_evidence": [dict(row) for row in list((context or {}).get("exhibition_evidence", []))[:2]],
        "artist_evidence": [dict(row) for row in list((context or {}).get("artist_evidence", []))[:2]],
    }


def _empty_advisor_followup_reference_context(selection: dict | None = None) -> dict:
    return {
        "selection": dict(selection or {}),
        "exhibition_evidence": [],
        "artist_evidence": [],
    }


def _merge_advisor_followup_reference_contexts(core_context: dict, dynamic_context: dict) -> dict:
    base_selection = dict((core_context or {}).get("selection", {}) or {})
    dynamic_selection = dict((dynamic_context or {}).get("selection", {}) or {})
    merged_selection = dict(base_selection)
    for key, value in dynamic_selection.items():
        if value not in ("", [], {}, None):
            merged_selection[key] = value
    return {
        "selection": merged_selection,
        "exhibition_evidence": (
            [dict(row) for row in list((core_context or {}).get("exhibition_evidence", []))]
            + [dict(row) for row in list((dynamic_context or {}).get("exhibition_evidence", []))]
        )[:4],
        "artist_evidence": (
            [dict(row) for row in list((core_context or {}).get("artist_evidence", []))]
            + [dict(row) for row in list((dynamic_context or {}).get("artist_evidence", []))]
        )[:4],
    }


def _derive_advisor_followup_reference_outputs(reference_context: dict) -> dict:
    reference_entities = _select_reference_entities_for_output(reference_context, [])
    reference_examples = _build_art_pulse_style_reference_lines(reference_entities)
    reference_images = _build_reference_images(reference_entities)
    urls: list[str] = []
    seen = set()
    for row in list(reference_context.get("exhibition_evidence", [])) + list(reference_context.get("artist_evidence", [])):
        url = str(row.get("source_url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= 8:
            break
    return {
        "reference_examples": reference_examples,
        "reference_images": reference_images,
        "reference_urls": urls,
    }


def _build_advisor_followup_base_payload(question_text: str, context: dict, draft: dict) -> dict:
    reference_examples = [
        _clip_compact_text(line, 120)
        for line in list(draft.get("reference_examples", []) or [])[:4]
        if str(line or "").strip()
    ]
    urls = draft.get("evidence_urls", {}) if isinstance(draft, dict) else {}
    all_urls = []
    for url in list(urls.get("exhibition", []) or []) + list(urls.get("artist", []) or []):
        val = str(url or "").strip()
        if not val or val in all_urls:
            continue
        all_urls.append(val)
        if len(all_urls) >= 6:
            break
    visual_summary = _clip_compact_text(
        _build_visual_observation_digest((context or {}).get("visual_observation", {})),
        max_chars=280,
    )
    base_answer = str((draft or {}).get("answer") or "").strip()
    return {
        "base_question": str(question_text or "").strip(),
        "base_answer": base_answer,
        "base_summary": _sentence_compact_summary(base_answer, max_chars=260, max_sentences=3),
        "base_entities": reference_examples,
        "base_urls": all_urls,
        "base_visual_summary": visual_summary,
    }


def _ensure_advisor_followup_base_state(question_text: str, context: dict, draft: dict) -> None:
    payload = _build_advisor_followup_base_payload(question_text, context, draft)
    reference_core_context = _build_advisor_followup_reference_core_context(context)
    reference_dynamic_context = _empty_advisor_followup_reference_context(reference_core_context.get("selection"))
    st.session_state["advisor_followup_base_question"] = payload["base_question"]
    st.session_state["advisor_followup_base_answer"] = payload["base_answer"]
    st.session_state["advisor_followup_base_summary"] = payload["base_summary"]
    st.session_state["advisor_followup_base_entities"] = payload["base_entities"]
    st.session_state["advisor_followup_base_urls"] = payload["base_urls"]
    st.session_state["advisor_followup_base_visual_summary"] = payload["base_visual_summary"]
    st.session_state["advisor_followup_memory_summary"] = ""
    st.session_state["advisor_followup_turns"] = []
    st.session_state["advisor_followup_last_question"] = ""
    st.session_state["advisor_followup_last_answer"] = ""
    st.session_state["advisor_followup_reference_core_context"] = reference_core_context
    st.session_state["advisor_followup_reference_dynamic_context"] = reference_dynamic_context
    st.session_state["advisor_followup_reference_examples"] = list(draft.get("reference_examples", []) or [])
    st.session_state["advisor_followup_reference_images"] = dict(draft.get("reference_images") or {})


def _format_uploaded_file_size(size_bytes: int) -> str:
    size = max(0, int(size_bytes or 0))
    if size >= 1024 * 1024:
        value = round(size / (1024 * 1024), 1)
        return f"{value:.1f}MB"
    if size >= 1024:
        return f"{int(round(size / 1024))}KB"
    return f"{size}B"


def _build_advisor_uploaded_image_label(uploaded_image_payload: dict | None) -> str:
    if not isinstance(uploaded_image_payload, dict):
        return ""
    name = str(uploaded_image_payload.get("name") or "").strip()
    raw_bytes = uploaded_image_payload.get("bytes")
    if not name:
        return ""
    size_label = _format_uploaded_file_size(len(raw_bytes) if isinstance(raw_bytes, (bytes, bytearray)) else 0)
    return f"添付画像:{name}/{size_label}"


def _build_advisor_followup_prompt(base_payload: dict, memory_summary: str, turns: list[dict], new_question: str) -> str:
    previous_turn = turns[-1] if turns else {}
    include_full_base = not turns
    base_entities = [
        str(item or "").strip()
        for item in list(base_payload.get("base_entities", []) or [])
        if str(item or "").strip()
    ]
    base_urls = [
        str(item or "").strip()
        for item in list(base_payload.get("base_urls", []) or [])
        if str(item or "").strip()
    ]
    visual_summary = str(base_payload.get("base_visual_summary") or "").strip()
    base_answer = str(base_payload.get("base_answer") or "").strip()
    base_summary = str(base_payload.get("base_summary") or "").strip()
    current_reference_examples = [
        _clip_compact_text(item, 120)
        for item in list(base_payload.get("current_reference_examples", []) or [])
        if str(item or "").strip()
    ]
    current_reference_urls = [
        str(item or "").strip()
        for item in list(base_payload.get("current_reference_urls", []) or [])
        if str(item or "").strip()
    ]
    previous_q = str(previous_turn.get("question") or "").strip()
    previous_a = str(previous_turn.get("answer") or "").strip()
    sections = [
        "You are answering a Japanese follow-up question for an existing Advisor conversation.",
        "Keep continuity with the initial answer, but answer the new question directly.",
        "Do not restate the whole conversation.",
        "Use the initial anchor as canonical context.",
        "If an initial image observation summary exists, use it only as remembered context. Do not pretend to re-read the image.",
        'Output JSON only: {"answer":"...","memory_summary":"..."}',
        "The answer must be natural Japanese prose.",
        "Aim for about 700 Japanese characters, with a soft range around 550-850 characters.",
        "Prefer one clear line of development over listing many options.",
        "Keep bullets to a minimum unless the user's question clearly requires a list.",
        "The memory_summary must be a short Japanese memo (about 120-220 chars) capturing decided direction, avoided directions, focal points, and unresolved points for the next follow-up.",
        "Avoid inventing facts or references.",
        "",
        "Fixed anchor:",
        f"- Initial question: {base_payload.get('base_question') or '-'}",
        f"- Initial answer summary: {base_summary or '-'}",
    ]
    if include_full_base and base_answer:
        sections.append(f"- Initial answer full text: {_clip_compact_text(base_answer, max_chars=1200)}")
    if base_entities:
        sections.append(f"- Main references: {' / '.join(base_entities)}")
    if base_urls:
        sections.append(f"- Main URLs: {' | '.join(base_urls)}")
    if visual_summary:
        sections.append(f"- Initial image observation summary: {visual_summary}")
    if current_reference_examples:
        sections.append(f"- Current refreshed references: {' / '.join(current_reference_examples[:6])}")
    if current_reference_urls:
        sections.append(f"- Current refreshed URLs: {' | '.join(current_reference_urls[:6])}")
    sections.extend([
        "",
        "Compressed memory:",
        memory_summary if str(memory_summary or '').strip() else "- none yet",
        "",
        "Latest one-turn context:",
    ])
    if previous_q and previous_a:
        sections.append(f"- Previous follow-up question: {previous_q}")
        sections.append(f"- Previous follow-up answer: {_clip_compact_text(previous_a, max_chars=480)}")
    else:
        sections.append("- none yet")
    sections.extend([
        "",
        "Current follow-up question:",
        str(new_question or "").strip(),
    ])
    return "\n".join(sections).strip()


def _extract_followup_response_payload(raw_output: str, fallback_memory_summary: str) -> dict:
    raw = str(raw_output or "").strip()
    payload = None
    candidates = [raw]
    matched = re.search(r"\{[\s\S]*\}", raw)
    if matched:
        candidates.insert(0, matched.group(0))
    for candidate in candidates:
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(candidate)
            except Exception:
                continue
            if isinstance(parsed, dict):
                payload = parsed
                break
        if isinstance(payload, dict):
            break
    if not isinstance(payload, dict):
        return {
            "answer": _finalize_followup_answer_text(_unwrap_followup_answer_text(raw)),
            "memory_summary": str(fallback_memory_summary or "").strip(),
        }
    return {
        "answer": _finalize_followup_answer_text(_unwrap_followup_answer_text(payload.get("answer") or raw)),
        "memory_summary": _clip_compact_text(
            payload.get("memory_summary") or fallback_memory_summary,
            max_chars=260,
        ),
    }


def _run_advisor_followup_turn(base_payload: dict, memory_summary: str, turns: list[dict], new_question: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    model = os.getenv("TEXT_MODEL", "gpt-5-mini")
    prompt = _build_advisor_followup_prompt(base_payload, memory_summary, turns, new_question)
    response = client.responses.create(model=model, input=prompt, max_output_tokens=900)
    output_text = str(getattr(response, "output_text", "") or "")
    return _extract_followup_response_payload(output_text, memory_summary)


def render_advisor() -> None:
    _render_mode_heading("Advisor")
    _render_mode_explanation(
        "最前線のアート事情を知り尽くした「AIアドバイザー」"
    )
    reset_requested_key = "advisor_reset_requested"
    question_clear_input_key = "advisor_question_clear_input_requested"
    followup_clear_input_key = "advisor_followup_clear_input_requested"
    uploaded_image_clear_key = "advisor_uploaded_image_clear_requested"
    uploaded_image_nonce_key = "advisor_uploaded_image_nonce"
    if st.session_state.pop(question_clear_input_key, False):
        st.session_state["advisor_question_text"] = ""
    if st.session_state.pop(followup_clear_input_key, False):
        st.session_state["advisor_followup_input"] = ""
    if st.session_state.pop(uploaded_image_clear_key, False):
        current_nonce = int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)
        st.session_state.pop(f"advisor_uploaded_image_{current_nonce}", None)
        st.session_state[uploaded_image_nonce_key] = current_nonce + 1
    if st.session_state.pop(reset_requested_key, False):
        current_nonce = int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)
        st.session_state.pop("advisor_fair_filter", None)
        st.session_state.pop("advisor_wants_image_generation", None)
        st.session_state.pop("advisor_question_text", None)
        st.session_state.pop("advisor_broad_query_rotation", None)
        st.session_state.pop("advisor_broad_query_history", None)
        st.session_state.pop(f"advisor_uploaded_image_{current_nonce}", None)
        st.session_state[uploaded_image_nonce_key] = current_nonce + 1
        st.session_state.pop("advisor_context", None)
        st.session_state.pop("advisor_selection", None)
        st.session_state.pop("advisor_draft", None)
        st.session_state.pop("advisor_type2_preview", None)
        st.session_state.pop("advisor_followup_base_question", None)
        st.session_state.pop("advisor_followup_base_answer", None)
        st.session_state.pop("advisor_followup_base_summary", None)
        st.session_state.pop("advisor_followup_base_entities", None)
        st.session_state.pop("advisor_followup_base_urls", None)
        st.session_state.pop("advisor_followup_base_visual_summary", None)
        st.session_state.pop("advisor_followup_memory_summary", None)
        st.session_state.pop("advisor_followup_turns", None)
        st.session_state.pop("advisor_followup_last_question", None)
        st.session_state.pop("advisor_followup_last_answer", None)
        st.session_state.pop("advisor_followup_base_image_label", None)
        st.session_state.pop("advisor_followup_reference_core_context", None)
        st.session_state.pop("advisor_followup_reference_dynamic_context", None)
        st.session_state.pop("advisor_followup_reference_examples", None)
        st.session_state.pop("advisor_followup_reference_images", None)
        st.session_state.pop("advisor_followup_input", None)
        st.session_state.pop(question_clear_input_key, None)
        st.session_state.pop(followup_clear_input_key, None)
        st.session_state.pop(uploaded_image_clear_key, None)

    col1, col2 = st.columns([3, 2])
    fair_mode = col1.selectbox(
        "知識範囲",
        FAIR_OPTIONS,
        index=2,
        key="advisor_fair_filter",
    )
    with col2:
        st.markdown('<div class="advisor-toggle-spacer"></div>', unsafe_allow_html=True)
        wants_image_generation = st.checkbox(
            "画像生成（✓でON）",
            value=False,
            key="advisor_wants_image_generation",
        )

    question_text = st.text_area(
        "相談内容",
        height=140,
        key="advisor_question_text",
        placeholder="例 : 面白い作品コンセプトの作家をおしえて",
    )
    effective_fair = str(fair_mode or FAIR_OPTIONS[0])
    uploader_key = f"advisor_uploaded_image_{int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)}"
    st.markdown("**画像添付**（任意 / テキスト+画像添付で質問可）")
    uploaded_image = st.file_uploader(
        "画像添付（任意 / テキスト+画像添付で質問可）",
        type=["png", "jpg", "jpeg", "webp"],
        key=uploader_key,
        label_visibility="collapsed",
    )
    upload_valid = False
    uploaded_image_payload = None
    if uploaded_image is not None:
        try:
            raw = uploaded_image.getvalue()
            mime = str(getattr(uploaded_image, "type", "") or "")
            if not raw:
                uploaded_image_payload = None
            elif mime and not mime.startswith("image/"):
                uploaded_image_payload = None
            else:
                upload_valid = True
                uploaded_image_payload = {
                    "bytes": raw,
                    "mime_type": mime or mimetypes.guess_type(str(uploaded_image.name or ""))[0] or "image/png",
                    "name": str(uploaded_image.name or ""),
                }
        except Exception:
            uploaded_image_payload = None

    run = st.button("相談する", key="advisor_run")
    if st.button("リセット", key="advisor_reset_button"):
        st.session_state[reset_requested_key] = True
        st.rerun()
    status_slot = st.empty()
    if run:
        if not question_text.strip():
            st.warning("相談内容を入力してください。")
            return

        def _render_advisor_progress(pct: int) -> None:
            status_slot.markdown(
                (
                    '<div class="ap-progress-row">'
                    '<span class="ap-progress-spinner"></span>'
                    f"<span>{escape('少々お待ちください...（特に画像生成は数分かかります）')}</span>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

        effective_fair = fair_mode
        rotation_key = f"{effective_fair}::{question_text.strip().casefold()}"
        rotation_map = dict(st.session_state.get("advisor_broad_query_rotation", {}) or {})
        rotation_index = int(rotation_map.get(rotation_key, 0) or 0)
        rotation_map[rotation_key] = rotation_index + 1
        st.session_state["advisor_broad_query_rotation"] = rotation_map
        broad_history = list(st.session_state.get("advisor_broad_query_history", []) or [])
        recent_broad_history = [item for item in broad_history if str(item.get("fair_mode") or "") == effective_fair][-8:]
        try:
            _render_advisor_progress(8)
            context = build_advisor_grounded_context(
                fair_label=effective_fair,
                question_text=question_text,
                rotation_index=rotation_index,
                recent_broad_history=recent_broad_history,
            )
            _render_advisor_progress(34)
            st.session_state["advisor_context"] = context
            st.session_state["advisor_selection"] = {
                "fair": effective_fair,
                "question_text": question_text,
                "wants_image_generation": wants_image_generation,
                "rotation_index": rotation_index,
            }

            # type2でも、まずgrounded type1を作る（text回答の基盤）
            draft_type1 = generate_advisor_grounded_draft(
                question_text=question_text,
                context=context,
                question_type="type1_text_only",
                has_uploaded_image=upload_valid,
                uploaded_image_name=(uploaded_image.name if uploaded_image is not None else ""),
                uploaded_image_payload=uploaded_image_payload,
            )
            _render_advisor_progress(68)
            st.session_state["advisor_draft"] = draft_type1
            _ensure_advisor_followup_base_state(question_text, context, draft_type1)
            broad_meta = dict(draft_type1.get("broad_diversity_meta") or {})
            if broad_meta:
                broad_meta["fair_mode"] = effective_fair
                broad_meta["question_text"] = question_text.strip()
                broad_history.append(broad_meta)
                st.session_state["advisor_broad_query_history"] = broad_history[-12:]

            if wants_image_generation:
                _render_advisor_progress(86)
                type2_preview = run_type2_gated_image_generation(
                    fair_label=effective_fair,
                    question_text=question_text,
                    type1_draft=draft_type1,
                    context=context,
                    has_uploaded_image=upload_valid,
                )
                st.session_state["advisor_type2_preview"] = type2_preview
            else:
                st.session_state["advisor_type2_preview"] = None
            st.session_state["advisor_followup_base_image_label"] = _build_advisor_uploaded_image_label(uploaded_image_payload)
            st.session_state[question_clear_input_key] = True
            st.session_state[uploaded_image_clear_key] = True
            st.rerun()
        except Exception as exc:
            status_slot.empty()
            st.error("Advisor 実行中にエラーが発生しました。入力条件を見直して再実行してください。")
            with st.expander("詳細（開発確認用）", expanded=False):
                st.code(f"{type(exc).__name__}: {exc}")
            return

    context = st.session_state.get("advisor_context")
    selection = st.session_state.get("advisor_selection", {})
    draft = st.session_state.get("advisor_draft")
    type2_preview = st.session_state.get("advisor_type2_preview")
    wants_image_generation = bool(selection.get("wants_image_generation"))

    if not context:
        return

    if not draft:
        return

    if not st.session_state.get("advisor_followup_base_question"):
        _ensure_advisor_followup_base_state(
            str(selection.get("question_text") or question_text or ""),
            context,
            draft,
        )

    reference_core_context = dict(
        st.session_state.get("advisor_followup_reference_core_context")
        or _build_advisor_followup_reference_core_context(context)
    )
    reference_dynamic_context = dict(
        st.session_state.get("advisor_followup_reference_dynamic_context")
        or _empty_advisor_followup_reference_context((context or {}).get("selection", {}))
    )
    advisor_reference_context = _merge_advisor_followup_reference_contexts(
        reference_core_context,
        reference_dynamic_context,
    )
    has_dynamic_reference_rows = bool(
        list(reference_dynamic_context.get("exhibition_evidence", []) or [])
        or list(reference_dynamic_context.get("artist_evidence", []) or [])
    )
    advisor_reference_display_context = advisor_reference_context if has_dynamic_reference_rows else context
    advisor_reference_images = dict(
        st.session_state.get("advisor_followup_reference_images")
        or draft.get("reference_images")
        or {}
    )
    advisor_reference_examples = list(
        st.session_state.get("advisor_followup_reference_examples")
        or draft.get("reference_examples")
        or []
    )
    advisor_reference_rows = list(advisor_reference_images.get("all", []) or [])

    reference_year_display = (
        context.get("selection", {}).get("reference_year_display")
        or context.get("selection", {}).get("year")
        or "-"
    )
    st.markdown("**回答**")
    st.caption(f"参照年: {reference_year_display}")
    if ADVISOR_UI_SHOW_DEBUG:
        _render_evidence_summary(
            {
                "質問タイプ": "type 2 希望（画像補助）" if wants_image_generation else "type 1",
                "参照年": reference_year_display,
                "モード": draft.get("mode"),
                "本文文字数": draft.get("answer_chars"),
                "本文上限": ADVISOR_TEXT_MAX_CHARS,
                "URL件数": draft.get("evidence_counts", {}).get("all_unique_urls", 0),
            }
        )
    initial_question_label = _clip_compact_text(
        st.session_state.get("advisor_followup_base_question")
        or selection.get("question_text")
        or question_text,
        max_chars=220,
    )
    if initial_question_label:
        st.caption(f"Q1: {initial_question_label}")
    initial_uploaded_image_label = str(st.session_state.get("advisor_followup_base_image_label") or "").strip()
    if initial_uploaded_image_label:
        st.caption(initial_uploaded_image_label)
    _render_markdown_with_galleries(
        str(draft.get("answer", "")),
        {"by_source": {}, "by_image_url": {}},
        preserve_linebreaks=True,
    )
    followup_turns = list(st.session_state.get("advisor_followup_turns", []) or [])
    followup_memory_summary = str(st.session_state.get("advisor_followup_memory_summary") or "")
    base_payload = {
        "base_question": str(st.session_state.get("advisor_followup_base_question") or ""),
        "base_answer": str(st.session_state.get("advisor_followup_base_answer") or ""),
        "base_summary": str(st.session_state.get("advisor_followup_base_summary") or ""),
        "base_entities": list(st.session_state.get("advisor_followup_base_entities", []) or []),
        "base_urls": list(st.session_state.get("advisor_followup_base_urls", []) or []),
        "base_visual_summary": str(st.session_state.get("advisor_followup_base_visual_summary") or ""),
        "current_reference_examples": list(st.session_state.get("advisor_followup_reference_examples", []) or []),
        "current_reference_urls": _derive_advisor_followup_reference_outputs(advisor_reference_context).get("reference_urls", []),
    }
    if followup_turns:
        for idx, turn in enumerate(followup_turns, start=2):
            question_label = _clip_compact_text(turn.get("question"), max_chars=220)
            if question_label:
                st.caption(f"Q{idx}: {question_label}")
            _render_markdown_with_galleries(
                str(turn.get("answer") or ""),
                {"by_source": {}, "by_image_url": {}},
                preserve_linebreaks=True,
            )
    st.markdown("**さらに質問**")
    followup_question = st.text_input(
        "追加質問",
        key="advisor_followup_input",
        label_visibility="collapsed",
        placeholder="例 : 他に面白い作品コンセプトの作家いますか？",
    )
    followup_run = st.button("質問する", key="advisor_followup_run")
    followup_status_slot = st.empty()
    if followup_run:
        if not followup_question.strip():
            st.warning("追加質問を入力してください。")
        else:
            followup_status_slot.markdown(
                (
                    '<div class="ap-progress-row">'
                    '<span class="ap-progress-spinner"></span>'
                    "<span>深掘り中...</span>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
            try:
                followup_stage = "reference_patch"
                reference_patch = build_advisor_followup_reference_patch(
                    fair_label=effective_fair,
                    question_text=followup_question,
                    base_context=context,
                    existing_urls=list(base_payload.get("current_reference_urls", []) or []),
                    limit_total=5,
                )
                if bool(reference_patch.get("refreshed")):
                    followup_stage = "reference_refresh"
                    reference_dynamic_context = {
                        "selection": dict(reference_patch.get("selection", {}) or {}),
                        "exhibition_evidence": list(reference_patch.get("exhibition_evidence", []) or []),
                        "artist_evidence": list(reference_patch.get("artist_evidence", []) or []),
                    }
                    advisor_reference_context = _merge_advisor_followup_reference_contexts(
                        reference_core_context,
                        reference_dynamic_context,
                    )
                    refreshed_reference_state = _derive_advisor_followup_reference_outputs(advisor_reference_context)
                    st.session_state["advisor_followup_reference_dynamic_context"] = reference_dynamic_context
                    st.session_state["advisor_followup_reference_examples"] = list(
                        refreshed_reference_state.get("reference_examples", []) or []
                    )
                    st.session_state["advisor_followup_reference_images"] = dict(
                        refreshed_reference_state.get("reference_images") or {}
                    )
                    base_payload["current_reference_examples"] = list(
                        refreshed_reference_state.get("reference_examples", []) or []
                    )
                    base_payload["current_reference_urls"] = list(
                        refreshed_reference_state.get("reference_urls", []) or []
                    )
                followup_stage = "openai_followup"
                followup_result = _run_advisor_followup_turn(
                    base_payload=base_payload,
                    memory_summary=followup_memory_summary,
                    turns=followup_turns,
                    new_question=followup_question,
                )
                followup_stage = "answer_finalize"
                followup_answer = str(followup_result.get("answer") or "").strip()
                if not followup_answer:
                    raise ValueError("empty_followup_answer")
                updated_turns = (
                    followup_turns
                    + [{"question": followup_question.strip(), "answer": followup_answer}]
                )[-3:]
                st.session_state["advisor_followup_turns"] = updated_turns
                st.session_state["advisor_followup_last_question"] = followup_question.strip()
                st.session_state["advisor_followup_last_answer"] = followup_answer
                st.session_state["advisor_followup_memory_summary"] = str(
                    followup_result.get("memory_summary") or followup_memory_summary
                ).strip()
                st.session_state[followup_clear_input_key] = True
                st.rerun()
            except Exception as exc:
                followup_status_slot.empty()
                st.error("追加質問の生成中にエラーが発生しました。しばらくしてから再実行してください。")
                if ADVISOR_UI_SHOW_DEBUG:
                    st.code(f"stage={locals().get('followup_stage', 'unknown')} | {type(exc).__name__}: {exc}")
    if wants_image_generation:
        st.markdown("**画像生成**")
        if not type2_preview:
            st.caption("画像生成を希望して Advisor を実行すると、画像補助結果を表示します。")
        else:
            status = str(type2_preview.get("status") or "")
            user_message = str(type2_preview.get("user_message") or "")
            if status != "success":
                st.info(user_message or "今回は画像補助を表示できなかったため、本文と根拠のみ表示しています。")

            image_bytes = type2_preview.get("generated_image_bytes")
            image_url = str(type2_preview.get("generated_image_url") or "")
            if image_bytes:
                _render_compact_generated_image(image_bytes, caption="AI generated")
                st.caption("Source: AI generated")
                rationale = str(type2_preview.get("image_rationale") or "")
                if rationale:
                    st.caption(rationale)
            elif image_url:
                _render_compact_generated_image(image_url, caption="AI generated")
                st.caption("Source: AI generated")
                rationale = str(type2_preview.get("image_rationale") or "")
                if rationale:
                    st.caption(rationale)
            else:
                st.caption("生成画像はありません。")

            if ADVISOR_UI_SHOW_DEBUG:
                with st.expander("type2 詳細 / prompt preview（開発確認用）", expanded=False):
                    check_rows = [
                        {
                            "check_id": c.get("id"),
                            "ok": bool(c.get("ok")),
                            "detail": c.get("detail"),
                        }
                        for c in type2_preview.get("checks", [])
                    ]
                    st.dataframe(check_rows, use_container_width=True, hide_index=True, height=240)
                    st.write(
                        {
                            "status": status,
                            "required_env_keys": type2_preview.get("required_env_keys", []),
                            "optional_env_keys": type2_preview.get("optional_env_keys", []),
                            "resolved_env": type2_preview.get("resolved_env", {}),
                            "api_called": bool(type2_preview.get("api_called", False)),
                        }
                    )
                    st.text_area(
                        "type 2 prompt プレビュー",
                        value=str(type2_preview.get("prompt_preview") or ""),
                        height=240,
                        disabled=True,
                    )
                    if type2_preview.get("error"):
                        st.warning(f"画像生成結果: {type2_preview.get('error')}")
                        debug_err = str(type2_preview.get("debug_error") or "")
                        if debug_err:
                            st.code(debug_err)

    if advisor_reference_examples:
        st.markdown("**参照例**")
        st.markdown("\n".join(advisor_reference_examples))

    if advisor_reference_rows:
        _render_reference_image_candidates(
            "",
            advisor_reference_images,
            target_total=8,
            compact_advisor_cards=True,
            show_title=False,
            show_summary=False,
            show_empty_message=False,
            evidence_context=advisor_reference_display_context,
        )

    urls = draft.get("evidence_urls", {})
    ex_urls = urls.get("exhibition", [])
    ar_urls = urls.get("artist", [])

    if ADVISOR_UI_SHOW_DEBUG:
        with st.expander("根拠と参照データ（source refs / URL）", expanded=True):
            st.markdown("**Advisor grounding overview（読み取り専用）**")
            st.write(
                {
                    "fair": context["selection"]["fair_label"],
                    "year": reference_year_display,
                    "question_type": "type 2 希望（画像補助）" if wants_image_generation else "type 1",
                    "token_count": len(context["selection"].get("tokens", [])),
                }
            )
            _render_evidence_summary(
                {
                    "Exhibitions根拠件数": context["counts"]["exhibitions_text_evidence_count"],
                    "Artists根拠件数": context["counts"]["artist_text_evidence_count"],
                    "URL件数": context["counts"]["all_unique_url_count"],
                    "参考画像候補件数": len(advisor_reference_rows),
                }
            )
            st.markdown("**根拠一覧（source refs + snippet）**")
            evidence_rows = list(context.get("evidence_rows", []) or [])
            if evidence_rows:
                st.dataframe(evidence_rows[:16], use_container_width=True, hide_index=True, height=260)
            else:
                st.info("表示可能な根拠行はありません。")

            _render_evidence_urls("根拠URL一覧", ex_urls, ar_urls)
            _render_reference_image_candidates(
                "参考画像候補",
                advisor_reference_images,
                target_total=8,
                compact_advisor_cards=True,
            )

            if context.get("warnings"):
                with st.expander("警告（Advisor）", expanded=False):
                    for warning in context["warnings"][:20]:
                        st.write(f"- {warning}")
            if draft.get("warnings"):
                with st.expander("警告（Advisor draft）", expanded=False):
                    for warning in draft["warnings"]:
                        st.write(f"- {warning}")


def render_gallery_list() -> None:
    _render_mode_heading("Gallery list")
    _render_mode_explanation("取材ギャラリーリスト（知識のベース）")

    try:
        data = get_gallery_list_data()
    except Exception as exc:
        st.error(f"Gallery list 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    total_count = int(getattr(data, "total_rows", 0) or 0)
    frieze_rows = [row for row in data.records if row.get("fair_slug") == "frieze_london"]
    liste_rows = [row for row in data.records if row.get("fair_slug") == "liste"]
    frieze_count = int(getattr(data, "fair_rows", {}).get("frieze_london", len(frieze_rows)) or 0)
    liste_count = int(getattr(data, "fair_rows", {}).get("liste", len(liste_rows)) or 0)

    def _split_gallery_name(value: str) -> tuple[str, str]:
        text = str(value or "").strip()
        for open_paren, close_paren in (("（", "）"), ("(", ")")):
            left = text.find(open_paren)
            right = text.rfind(close_paren)
            if left > 0 and right > left:
                return text[:left].strip(), text[left + 1 : right].strip()
        return text, ""

    def _sort_key(row: dict) -> str:
        en_name, _ = _split_gallery_name(str(row.get("gallery_name") or ""))
        return en_name.casefold()

    frieze_rows.sort(key=_sort_key)
    liste_rows.sort(key=_sort_key)

    def _render_list_items(rows: list[dict]) -> str:
        items: list[str] = []
        for row in rows:
            gallery_name = str(row.get("gallery_name") or "").strip()
            en_name, kana_info = _split_gallery_name(gallery_name)
            exhibitions_url = str(row.get("exhibitions_url") or "").strip()
            linked_name = (
                f'<a href="{escape(exhibitions_url, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(en_name)}</a>'
                if exhibitions_url
                else escape(en_name)
            )
            label = f"{linked_name}（{escape(kana_info)}）" if kana_info else linked_name
            items.append(f"<li>{label}</li>")
        return "".join(items)

    st.markdown(
        f'<div class="ap-gallery-kb-meta">総ギャラリー数/{total_count}　Frieze/{frieze_count}　Liste/{liste_count}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        (
            '<div class="ap-gallery-kb-grid">'
            '<section class="ap-gallery-kb-col">'
            "<h4>- Frieze London -</h4>"
            f"<ol>{_render_list_items(frieze_rows)}</ol>"
            "</section>"
            '<section class="ap-gallery-kb-col">'
            "<h4>- Liste Art Fair Basel -</h4>"
            f"<ol>{_render_list_items(liste_rows)}</ol>"
            "</section>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_about() -> None:
    _render_mode_heading("About")
    st.markdown(
        """
        <div class="about-panel">
          <section class="about-hero">
            <h4 class="about-title">【Art Pulse Editor】（アート・パルス・エディター）について</h4>
            <p class="about-lead">
              世界トップ級の現代アートフェアに出展するギャラリー情報をRAGとして参照する、現代アート特化型AIアプリです。<br>
              RAG知識をベースに、<strong>「トレンド抽出」</strong>、<strong>「制作アドバイス」</strong>、<strong>「全ギャラリー横断検索」</strong>、<strong>「日本語での整理・要約」</strong> などの機能を、1つにまとめています。
            </p>
          </section>

          <section class="about-section">
            <h5 class="about-section-title">対象アートフェア（RAG対象範囲）</h5>
            <div class="about-fair-list">
              <div class="about-fair-item">
                <p class="about-fair-name">Frieze London</p>
                <p class="about-fair-desc">国際的な「巨匠・中堅中心」の現代アートフェア</p>
              </div>
              <div class="about-fair-item">
                <p class="about-fair-name">Liste Art Fair Basel</p>
                <p class="about-fair-desc">国際的な「若手中心」の現代アートフェア</p>
              </div>
            </div>
          </section>

          <section class="about-section">
            <h5 class="about-section-title">アプリ機能について</h5>
            <div class="about-feature-list">
              <div class="about-feature-card">
                <div class="about-feature-head">
                  <span class="about-feature-no">01</span>
                  <span class="about-feature-name">Art Pulse</span>
                </div>
                <p class="about-feature-body">性格や嗜好が異なる8名のAI記者が、アートフェアを独自に取材し、記事を執筆する機能。</p>
              </div>
              <div class="about-feature-card">
                <div class="about-feature-head">
                  <span class="about-feature-no">02</span>
                  <span class="about-feature-name">Advisor</span>
                </div>
                <p class="about-feature-body">全ギャラリーのRAG知識をもとにした「AIアートアドバイザー」が、アートに関するアドバイスを行う機能。<br>テキスト質問だけでなく、画像添付付き質問や画像生成にも対応。</p>
              </div>
              <div class="about-feature-card">
                <div class="about-feature-head">
                  <span class="about-feature-no">03</span>
                  <span class="about-feature-name">Art Work Search</span>
                </div>
                <p class="about-feature-body">登録されている「アートワーク」を、テキスト入力や画像添付で類似検索する機能。<br><strong>入力例：</strong>幾何学 / 赤い抽象画 / 人物 / Flower など</p>
              </div>
              <div class="about-feature-card">
                <div class="about-feature-head">
                  <span class="about-feature-no">04</span>
                  <span class="about-feature-name">Artist Search</span>
                </div>
                <p class="about-feature-body">登録されている「アーティスト」を、テキスト入力で検索する機能。<br><strong>入力例：</strong>ジャンル / テーマ / アーティスト名 など</p>
              </div>
              <div class="about-feature-card">
                <div class="about-feature-head">
                  <span class="about-feature-no">05</span>
                  <span class="about-feature-name">Exhibition Search</span>
                </div>
                <p class="about-feature-body">登録されている「エキシビション」を、テキスト入力で検索する機能。<br><strong>入力例：</strong>テーマ / ジャンル / アーティスト名 など</p>
              </div>
              <div class="about-feature-card">
                <div class="about-feature-head">
                  <span class="about-feature-no">06</span>
                  <span class="about-feature-name">Gallery list</span>
                </div>
                <p class="about-feature-body">登録されている「ギャラリー」の一覧を表示する機能。<br>全RAGの根拠となるギャラリー情報を確認できます。</p>
              </div>
            </div>
          </section>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_phase2_sections() -> None:
    sections = [
        ("Art Pulse", "art_pulse", render_art_pulse),
        ("Advisor", "advisor", render_advisor),
        ("Art Work Search", "artwork_search", render_artwork_search),
        ("Artist Search", "artist_search", render_artist_search),
        ("Exhibition Search", "exhibition_search", render_exhibition_search),
        ("Gallery list", "gallery_list", render_gallery_list),
        ("About", "about", render_about),
    ]
    open_key = "top_level_open_section"
    current_open = str(st.session_state.get(open_key) or "")

    st.markdown('<div class="ap-top-nav-list-spacer"></div>', unsafe_allow_html=True)

    for label, slug, renderer in sections:
        if st.button(label, key=f"top_level_section_button_{slug}", use_container_width=True, type="tertiary"):
            st.session_state[open_key] = "" if current_open == slug else slug
            st.rerun()

        if str(st.session_state.get(open_key) or "") == slug:
            with st.container(border=True):
                renderer()
            st.markdown('<div class="ap-top-nav-open-gap"></div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")
    apply_global_font_styles()
    render_header()
    render_phase2_sections()


if __name__ == "__main__":
    main()
