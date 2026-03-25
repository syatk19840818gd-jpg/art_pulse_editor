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
from phase2_common_readonly import resolve_current_exhibitions_available_years
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
from phase2_exclusive_advisor_draft import (
    EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
    generate_exclusive_advisor_draft,
)
from phase2_exclusive_advisor_readonly import build_exclusive_advisor_context
from phase2_exclusive_advisor_type2_execute import (
    collect_failed_checks as collect_failed_checks_exclusive_type2,
    run_exclusive_type2_gated_image_generation,
)
from phase2_gallery_list_readonly import apply_gallery_list_filters, load_gallery_list_records_readonly
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
          color-scheme: light;
        }
        html, body {
          background-color: #f5f7fb !important;
          color: #111111 !important;
        }
        .stApp, .stApp * {
          font-family: var(--font-latin), var(--font-cjk) !important;
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
        .stApp {
          --background-color: #f5f7fb !important;
          --secondary-background-color: #ffffff !important;
          --text-color: #111111 !important;
          --primary-color: #0f62fe !important;
          background-color: #f5f7fb !important;
          color: #111111 !important;
        }
        .stApp [data-testid="stAppViewContainer"],
        .stApp [data-testid="stMain"],
        .stApp [data-testid="stMainBlockContainer"],
        .stApp [data-testid="stSidebar"] {
          background-color: #f5f7fb !important;
          color: #111111 !important;
        }
        /* Layout: PC は広く、モバイルは画面幅に追従 */
        .stApp [data-testid="stMainBlockContainer"],
        .stApp .block-container {
          max-width: min(1680px, 96vw) !important;
          width: 100% !important;
          padding-top: 0.8rem !important;
          padding-left: clamp(0.75rem, 2vw, 2.25rem) !important;
          padding-right: clamp(0.75rem, 2vw, 2.25rem) !important;
        }
        .stApp [data-testid="stHeadingWithActionElements"] h1 {
          font-size: 50px !important;
          width: 100%;
          text-align: center !important;
          margin-top: 0 !important;
          margin-bottom: 1 rem !important;
          line-height: 2.2 !important;
        }
        @media (max-width: 900px) {
          .stApp [data-testid="stMainBlockContainer"],
          .stApp .block-container {
            max-width: 100vw !important;
            padding-left: 0.55rem !important;
            padding-right: 0.55rem !important;
          }
        }
        .stApp [data-testid="stVerticalBlockBorderWrapper"] {
          background-color: #ffffff !important;
          border: 1px solid #d9dbe2 !important;
          border-radius: 12px !important;
        }
        .advisor-toggle-spacer {
          height: 2.1rem;
        }
        .advisor-generated-image-wrap {
          display: flex;
          justify-content: center;
          margin: 0.25rem 0 0.35rem 0;
        }
        .advisor-generated-image-link {
          display: block;
          width: min(100%, 560px);
          text-decoration: none;
        }
        .advisor-generated-image-link img {
          display: block;
          width: 100%;
          height: auto;
          max-height: 68vh;
          object-fit: contain;
          border-radius: 10px;
          border: 1px solid #d9dbe2;
          background: #f6f8fb;
        }
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stCaptionContainer"],
        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stMetricLabel"],
        .stApp p,
        .stApp label,
        .stApp li {
          color: #111111 !important;
        }
        .stApp a {
          color: #0a66c2 !important;
        }
        .stApp input,
        .stApp textarea,
        .stApp div[data-baseweb="select"] > div,
        .stApp div[data-baseweb="tag"] {
          background-color: #ffffff !important;
          color: #111111 !important;
          border-color: #cfcfcf !important;
        }
        .stApp input::placeholder,
        .stApp textarea::placeholder {
          color: #6b7280 !important;
          opacity: 1 !important;
        }
        .stApp [data-testid="stTextInputRootElement"],
        .stApp [data-testid="stTextAreaRootElement"],
        .stApp [data-testid="stSelectbox"] > div {
          color: #111111 !important;
        }
        .stApp [data-testid="stButton"] > button {
          background-color: #f3f4f6 !important;
          color: #111111 !important;
          border: 1px solid #cfcfcf !important;
        }
        .stApp [data-testid="stButton"] > button:disabled {
          background-color: #f3f4f6 !important;
          color: #6b7280 !important;
          opacity: 1 !important;
          border-color: #d5d8df !important;
        }
        .stApp [data-testid="stFileUploaderDropzone"] {
          background-color: #f8fafc !important;
          color: #111111 !important;
          border: 1px solid #d5d8df !important;
        }
        .stApp section[data-testid="stFileUploader"] button {
          background-color: #f3f4f6 !important;
          color: #111111 !important;
          border: 1px solid #cfcfcf !important;
        }
        .stApp [data-testid="stFileUploaderDropzone"] [data-baseweb="button"],
        .stApp [data-testid="stFileUploaderDropzone"] button {
          background-color: #f3f4f6 !important;
          color: #111111 !important;
          border: 1px solid #cfcfcf !important;
        }
        .stApp [data-testid="stDataFrame"] {
          --gdg-bg-cell: #ffffff;
          --gdg-bg-cell-medium: #f9fafb;
          --gdg-bg-header: #f1f3f7;
          --gdg-bg-header-hovered: #e9edf5;
          --gdg-bg-bubble: #f8fafc;
          --gdg-bg-bubble-selected: #e8eefc;
          --gdg-bg-search-result: #fff7d6;
          --gdg-border-color: #d4d7de;
          --gdg-horizontal-border-color: #e2e6ee;
          --gdg-drilldown-border: #d4d7de;
          --gdg-link-color: #0a66c2;
          --gdg-text-dark: #111111;
          --gdg-text-medium: #374151;
          --gdg-text-light: #6b7280;
          --gdg-text-bubble: #111111;
        }
        .stApp [data-testid="stDataFrame"] canvas {
          background-color: #ffffff !important;
        }
        .stApp [data-testid="stJson"],
        .stApp [data-testid="stJson"] * {
          background-color: #ffffff !important;
          color: #111111 !important;
        }
        .stApp [data-testid="stCodeBlock"],
        .stApp [data-testid="stCodeBlock"] * {
          background-color: #ffffff !important;
          color: #111111 !important;
        }
        .stApp pre, .stApp code {
          background-color: #f8fafc !important;
          color: #111111 !important;
        }
        /* Art Pulse image gallery: PC横並び / モバイル自動追従 */
        .ap-gallery {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 0.9rem;
          margin: 0.4rem 0 1.1rem 0;
        }
        .ap-gallery-item {
          display: flex;
          flex-direction: column;
          gap: 0.35rem;
        }
        .ap-gallery-thumb {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 260px;
          overflow: hidden;
          border-radius: 10px;
          border: 1px solid #d9dbe2;
          background: #f4f6fb;
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
          border-radius: 10px;
          border: 1px solid #d9dbe2;
          background: #f4f6fb;
          color: #5f6b7a;
          font-size: 0.86rem;
          line-height: 1.45;
          text-align: center;
          padding: 0.8rem;
        }
        .ap-gallery-source {
          font-size: 0.83rem;
          line-height: 1.25;
          color: #374151;
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
          border: 1px solid #d9dbe2;
          border-radius: 10px;
          background: #ffffff;
          padding: 0.65rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        .exh-search-title {
          font-size: 0.98rem;
          line-height: 1.4;
          font-weight: 700;
          color: #111111;
          margin: 0;
        }
        .exh-search-thumb {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          min-height: 240px;
          max-height: 240px;
          border-radius: 8px;
          border: 1px solid #d9dbe2;
          background: #f6f8fb;
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
          background: #f6f8fb;
        }
        .exh-search-fallback {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          min-height: 240px;
          max-height: 240px;
          border-radius: 8px;
          border: 1px solid #d9dbe2;
          color: #5f6b7a;
          font-size: 0.88rem;
          line-height: 1.45;
          text-align: center;
          background: #f6f8fb;
          padding: 0.8rem;
        }
        .exh-search-source {
          font-size: 0.82rem;
          line-height: 1.3;
          color: #374151;
          word-break: break-word;
          margin: 0;
        }
        .exh-search-summary {
          font-size: 0.94rem;
          line-height: 1.55;
          color: #111111;
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
          gap: 1rem;
          overflow-x: auto;
          overflow-y: hidden;
          margin: 0.4rem 0 0.35rem 0;
          padding-bottom: 0.35rem;
          overscroll-behavior-x: contain;
          -webkit-overflow-scrolling: touch;
          scroll-behavior: smooth;
        }
        .advisor-ref-scroll {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          overflow-x: auto;
          overflow-y: hidden;
          margin: 0.4rem 0 0.35rem 0;
          padding-bottom: 0.35rem;
          overscroll-behavior-x: contain;
          -webkit-overflow-scrolling: touch;
          scroll-behavior: smooth;
        }
        .artist-search-scroll .exh-search-card,
        .exh-results-scroll .exh-search-card {
          flex: 0 0 clamp(300px, 26vw, 460px);
          height: 590px;
          overflow: hidden;
        }
        .advisor-ref-scroll .exh-search-card {
          flex: 0 0 clamp(300px, 26vw, 460px);
          height: 590px;
          overflow: hidden;
        }
        .artist-search-scroll .exh-search-summary {
          overflow-y: auto;
          overflow-x: hidden;
          display: block;
          max-height: 15.5rem;
        }
        .advisor-ref-scroll .advisor-ref-artist-card .exh-search-summary {
          overflow-y: auto;
          overflow-x: hidden;
          display: block;
          max-height: 15.5rem;
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
          border-radius: 8px;
          border: 1px solid #d9dbe2;
          background: #f6f8fb;
          overflow: hidden;
          position: relative;
        }
        .artist-search-thumb img {
          width: 100%;
          height: 100%;
          object-fit: contain;
          display: block;
          background: #f6f8fb;
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
          font-size: 0.95rem;
          line-height: 1.4;
          color: rgba(49, 51, 63, 0.6);
          margin-top: 0.15rem;
          margin-bottom: 0.15rem;
        }
        .ap-progress-spinner {
          width: 0.95rem;
          height: 0.95rem;
          border: 2px solid rgba(49, 51, 63, 0.25);
          border-top-color: rgba(49, 51, 63, 0.6);
          border-radius: 50%;
          animation: ap-spin 0.9s linear infinite;
          flex: 0 0 auto;
        }
        @keyframes ap-spin {
          to { transform: rotate(360deg); }
        }
        @media (max-width: 900px) {
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
            max-height: 12rem;
            overflow-y: auto;
            overflow-x: hidden;
          }
          .advisor-ref-scroll .advisor-ref-artist-card .exh-search-summary {
            display: block;
            -webkit-line-clamp: unset;
            max-height: 12rem;
            overflow-y: auto;
            overflow-x: hidden;
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
            f'<h3 style="margin:0.15rem 0 0.6rem 0; '
            f'font-size:{MODE_HEADING_FONT_SIZE_PX}px; font-weight:700;">{text}</h3>'
        ),
        unsafe_allow_html=True,
    )


def _render_mode_explanation(text: str) -> None:
    st.markdown(
        (
            f'<p style="margin:0.1rem 0 0.7rem 0; color:#111111; font-weight:550; '
            f'font-size:{EXPLANATION_OF_MODES_FONT_SIZE_PX}px;">{text}</p>'
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


def _render_exhibition_result_cards(rows: list[dict]) -> None:
    cards: list[str] = []
    for idx, row in enumerate(rows, start=1):
        cards.append(_build_exhibition_card_html(row, idx))

    if cards:
        st.markdown(f'<div class="exh-results-scroll">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_artist_result_cards(rows: list[dict]) -> None:
    cards: list[str] = []
    for idx, row in enumerate(rows, start=1):
        row_copy = dict(row)
        if not row_copy.get("summary_display_ja"):
            row_copy["summary_display_ja"] = build_artist_summary_ja(row, max_chars=ARTIST_SEARCH_SUMMARY_MAX_CHARS)
        cards.append(_build_artist_card_html(row_copy, idx))

    if cards:
        st.markdown(f'<div class="artist-search-scroll">{"".join(cards)}</div>', unsafe_allow_html=True)


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
    _render_mode_explanation("アート編集記者が「現代アートの今（Now）」を取材し、記事を執筆する")

    available_years = get_art_pulse_available_years()
    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "フェア選択",
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
    _render_mode_explanation("トップギャラリーの展示検索（キーワード入力）")
    try:
        data = get_exhibition_search_data()
    except Exception as exc:
        st.error(f"Exhibition 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    results_key = "exh_search_results"
    query_key = "exh_search_query"
    keyword_key = "exh_keyword"
    search_reset_requested_key = "exh_search_reset_requested"
    spinner_complete = None

    if st.session_state.pop(search_reset_requested_key, False):
        st.session_state[keyword_key] = ""
        st.session_state.pop(results_key, None)
        st.session_state.pop(query_key, None)

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "フェア選択",
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
    st.caption("キーワード入力 ＋ Search で「展示情報」を表示します。")
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

    _render_exhibition_result_cards(display_rows)
    if spinner_complete:
        spinner_complete()
    status_slot.caption(_build_standard_search_caption(data.total_rows, len(filtered), data.fair_rows, total_hits))


def render_artist_search() -> None:
    _render_mode_heading("Artist Search")
    _render_mode_explanation("トップギャラリーの作家検索（キーワード入力）")

    try:
        data = get_artist_search_data()
    except Exception as exc:
        st.error(f"Artist 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    results_key = "artist_search_results"
    query_key = "artist_search_query"
    keyword_key = "artist_keyword"
    search_reset_requested_key = "artist_search_reset_requested"
    spinner_complete = None

    if st.session_state.pop(search_reset_requested_key, False):
        st.session_state[keyword_key] = ""
        st.session_state.pop(results_key, None)
        st.session_state.pop(query_key, None)

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "フェア選択",
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
    st.caption("キーワード入力 ＋ Search で「作家情報」を表示します。")
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

    _render_artist_result_cards(display_rows)
    if spinner_complete:
        spinner_complete()
    status_slot.caption(_build_standard_search_caption(data.total_rows, len(filtered), data.fair_rows, total_hits))


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
                        "local_path": str(row.get("local_path") or "").strip(),
                        "image_url": str(row.get("image_url") or "").strip(),
                    }
                ],
                "artist_image_layout": "single_wide",
            }
        )
    return display_rows


def render_artwork_search() -> None:
    _render_mode_heading("ArtWork Search")
    _render_mode_explanation("Artist Works Images の類似検索（text / image）")

    results_key = "artwork_search_results"
    query_key = "artwork_search_query"
    text_query_key = "artwork_search_text_query"
    fair_filter_key = "artwork_search_fair_filter"
    reset_requested_key = "artwork_search_reset_requested"
    uploaded_image_nonce_key = "artwork_search_uploaded_image_nonce"
    spinner_complete = None

    if st.session_state.pop(reset_requested_key, False):
        current_nonce = int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)
        st.session_state[text_query_key] = ""
        st.session_state.pop(results_key, None)
        st.session_state.pop(query_key, None)
        st.session_state.pop(f"artwork_search_uploaded_image_{current_nonce}", None)
        st.session_state[uploaded_image_nonce_key] = current_nonce + 1

    col1, col2 = st.columns([1, 1])
    fair_filter = col1.selectbox(
        "フェア選択",
        FAIR_OPTIONS,
        index=2,
        key=fair_filter_key,
    )
    text_query = col2.text_input(
        "text query",
        value="",
        placeholder="例 : blue geometric abstraction / warm red sculpture",
        key=text_query_key,
    )

    uploader_key = f"artwork_search_uploaded_image_{int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)}"
    uploaded_image = st.file_uploader(
        "image query (session-only)",
        type=["png", "jpg", "jpeg", "webp"],
        key=uploader_key,
    )
    uploaded_image_bytes = uploaded_image.getvalue() if uploaded_image is not None else b""
    if uploaded_image_bytes:
        st.caption("query image: session-only")
        _render_compact_generated_image(uploaded_image_bytes, caption="query image")

    st.caption("text または image query を入れて Search すると、Artist Works Images の top-k を表示します。")
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
    if not rows:
        if spinner_complete:
            spinner_complete()
        st.warning("条件に一致する作品画像はありません。")
        return

    display_rows = _build_artwork_result_artist_rows(rows)
    _render_artist_result_cards(display_rows)
    if spinner_complete:
        spinner_complete()

    corpus_stats = dict(result.get("corpus_stats") or {})
    fair_counts = dict(corpus_stats.get("available_fair_counts") or {})
    status_slot.caption(
        _build_standard_search_caption(
            int(corpus_stats.get("images_total", 0) or 0),
            len(rows),
            fair_counts,
            len(rows),
        )
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
        "ギャラリーを知り尽くすアート編集長によるアドバイス"
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
        st.session_state.pop(followup_clear_input_key, None)

    col1, col2 = st.columns([3, 2])
    fair_mode = col1.selectbox(
        "フェア選択",
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
        placeholder="例: 素材の選び方を教えて。",
    )
    effective_fair = str(fair_mode or FAIR_OPTIONS[0])
    uploader_key = f"advisor_uploaded_image_{int(st.session_state.get(uploaded_image_nonce_key, 0) or 0)}"
    uploaded_image = st.file_uploader(
        "画像添付（テキスト+画像添付で質問可）",
        type=["png", "jpg", "jpeg", "webp"],
        key=uploader_key,
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
        placeholder="例: さっきの方向で、もう少し素材の選び方だけ絞って教えてください。",
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


def render_exclusive_advisor() -> None:
    _render_mode_heading("⑤ Exclusive Advisor（垂谷専属）")
    _render_mode_explanation(
        "type 1（テキスト回答）と type 2（テキスト＋画像生成）を実装。"
        "Tarutani_Text は文脈参照としてのみ使用します。"
    )

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "フェア選択",
        FAIR_OPTIONS,
        index=2,
        key="exclusive_fair_filter",
    )
    question_type_label = col2.selectbox(
        "質問タイプ",
        [
            "type 1 = テキスト回答のみ（今回実装）",
            "type 2 = テキスト＋画像生成（gate付き）",
        ],
        index=0,
        key="exclusive_question_type",
    )

    question_text = st.text_area(
        "相談内容（垂谷文脈を踏まえた制作相談）",
        value="",
        height=140,
        key="exclusive_question_text",
        placeholder="例: 過去作と近作のシリーズ文脈を踏まえて、2025年フェアで機能する展示提案にしたい。",
    )
    uploaded_image = st.file_uploader(
        "質問画像（任意）",
        type=["png", "jpg", "jpeg", "webp"],
        key="exclusive_uploaded_image",
    )

    upload_valid = False
    upload_note = "添付画像なし。"
    if uploaded_image is not None:
        try:
            raw = uploaded_image.getvalue()
            mime = str(getattr(uploaded_image, "type", "") or "")
            if not raw:
                upload_note = "添付画像を読み込めなかったため、画像なしとして処理します。"
            elif mime and not mime.startswith("image/"):
                upload_note = "添付ファイルが画像形式ではないため、画像なしとして処理します。"
            else:
                upload_valid = True
                upload_note = f"添付画像: {uploaded_image.name}（保存しない / ベクトル化しない / RAG混入なし）"
        except Exception:
            upload_note = "添付画像の読み込みに失敗したため、画像なしとして処理します。"
    st.caption(upload_note)

    run = st.button("Exclusive Advisor を実行", key="exclusive_run")
    if run:
        if not question_text.strip():
            st.warning("相談内容を入力してください。")
            return
        effective_fair = fair_mode
        try:
            context = build_exclusive_advisor_context(
                fair_label=effective_fair,
                question_text=question_text,
            )
            st.session_state["exclusive_context"] = context
            st.session_state["exclusive_selection"] = {
                "fair": effective_fair,
                "question_text": question_text,
                "question_type_label": question_type_label,
            }
            if question_type_label.startswith("type 1"):
                draft = generate_exclusive_advisor_draft(
                    question_text=question_text,
                    context=context,
                    has_uploaded_image=upload_valid,
                    uploaded_image_name=(uploaded_image.name if uploaded_image is not None else ""),
                )
                st.session_state["exclusive_draft"] = draft
                st.session_state["exclusive_type2"] = None
            else:
                draft = generate_exclusive_advisor_draft(
                    question_text=question_text,
                    context=context,
                    has_uploaded_image=upload_valid,
                    uploaded_image_name=(uploaded_image.name if uploaded_image is not None else ""),
                )
                st.session_state["exclusive_draft"] = draft
                st.session_state["exclusive_type2"] = run_exclusive_type2_gated_image_generation(
                    fair_label=effective_fair,
                    question_text=question_text,
                    type1_draft=draft,
                    context=context,
                    has_uploaded_image=upload_valid,
                )
        except Exception as exc:
            st.error("Exclusive Advisor 実行中にエラーが発生しました。入力条件を見直して再実行してください。")
            with st.expander("詳細（開発確認用）", expanded=False):
                st.code(f"{type(exc).__name__}: {exc}")
            return

    context = st.session_state.get("exclusive_context")
    selection = st.session_state.get("exclusive_selection", {})
    draft = st.session_state.get("exclusive_draft")
    type2_result = st.session_state.get("exclusive_type2")
    active_qtype = selection.get("question_type_label", question_type_label)

    if not context:
        st.caption("相談内容を入力して「Exclusive Advisor を実行」を押すと、grounded draft を表示します。")
        return

    st.markdown("**Exclusive Advisor grounding overview（読み取り専用）**")
    st.write(
        {
            "fair": context["selection"]["fair_label"],
            "year": context["selection"]["year"],
            "question_type": active_qtype,
            "token_count": len(context["selection"].get("tokens", [])),
        }
    )
    _render_evidence_summary(
        {
            "外部Exhibitions根拠件数": context["external"].get("counts", {}).get("exhibitions_text_evidence_count", 0),
            "外部Artists根拠件数": context["external"].get("counts", {}).get("artist_text_evidence_count", 0),
            "外部URL件数": context["external"].get("counts", {}).get("all_unique_url_count", 0),
            "Tarutani抜粋件数": context["tarutani"].get("count", 0),
            "参考画像候補件数": len((context["external"].get("reference_images", {}) or {}).get("all", [])),
        }
    )
    ex_view = [
        {
            "fair": r.get("fair_label"),
            "gallery": r.get("gallery"),
            "title": r.get("title"),
            "year": r.get("year"),
            "source_url": r.get("source_url"),
        }
        for r in context["external"].get("exhibition_evidence", [])[:12]
    ]
    ar_view = [
        {
            "fair": r.get("fair_label"),
            "gallery": r.get("gallery"),
            "artist": r.get("artist_name"),
            "year": r.get("year"),
            "source_url": r.get("source_url"),
        }
        for r in context["external"].get("artist_evidence", [])[:12]
    ]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**根拠ブロック（外部Exhibitions）**")
        st.dataframe(ex_view, use_container_width=True, hide_index=True, height=220)
    with c2:
        st.markdown("**根拠ブロック（外部Artists）**")
        st.dataframe(ar_view, use_container_width=True, hide_index=True, height=220)

    ref_images = context["external"].get("reference_images", {})
    _render_reference_image_candidates("参考画像候補", ref_images, target_total=8)
    if context.get("warnings"):
        with st.expander("警告（Exclusive Advisor）", expanded=False):
            for warning in context["warnings"][:20]:
                st.write(f"- {warning}")

    if active_qtype.startswith("type 2"):
        st.markdown("**Exclusive Advisor type 2（gate付き実行）**")
        if not type2_result:
            st.caption("type 2 を選んで Exclusive Advisor を実行すると、gate判定後に本文と画像生成結果を表示します。")
            return

        gate_ok = bool(type2_result.get("gate_ok"))
        status = str(type2_result.get("status") or "")
        user_message = str(type2_result.get("user_message") or "")
        if status == "success":
            st.success("type 2 状態: 実行成功")
        elif status == "image_failed":
            st.warning("type 2 状態: 画像生成失敗（本文と根拠は表示）")
        elif status == "gate_hold":
            st.error("type 2 状態: gate未通過（条件不足で実行不可）")
        elif gate_ok:
            st.info("type 2 状態: 利用可能")
        else:
            st.info("type 2 状態: 条件確認中")
        if user_message:
            st.caption(user_message)

        if status == "gate_hold":
            failed = collect_failed_checks_exclusive_type2(type2_result)
            if failed:
                st.markdown("**未通過条件（要点）**")
                for reason in failed[:8]:
                    st.write(f"- {reason}")

        external_urls = type2_result.get("external_evidence_urls", {}) or {}
        ex_urls = external_urls.get("exhibition") or []
        ar_urls = external_urls.get("artist") or []
        tarutani_rows = type2_result.get("tarutani_evidence_excerpts", []) or []
        ref_images = type2_result.get("reference_images", {}) or {}
        ref_rows = ref_images.get("all") or []

        st.markdown("**Exclusive Advisor回答（日本語、type 2）**")
        _render_evidence_summary(
            {
                "本文文字数": type2_result.get("text_chars"),
                "本文上限": EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
                "外部URL件数": len(ex_urls) + len(ar_urls),
                "Tarutani抜粋件数": len(tarutani_rows),
                "参考画像候補件数": len(ref_rows),
            }
        )
        st.text_area(
            "Exclusive Advisor回答（日本語）",
            value=str(type2_result.get("text_answer") or ""),
            height=220,
            disabled=True,
        )
        st.caption(str(type2_result.get("attachment_note") or ""))
        st.caption("添付画像/生成画像は保存しません（セッション内表示のみ）。")

        image_bytes = type2_result.get("generated_image_bytes")
        image_url = str(type2_result.get("generated_image_url") or "")
        if image_bytes:
            st.image(image_bytes, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        elif image_url:
            st.image(image_url, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        else:
            st.info("生成画像はありません（gate未通過または画像生成失敗）。")

        _render_evidence_urls("外部根拠URL", ex_urls, ar_urls)

        st.markdown("**Tarutani_Text抜粋**")
        t_view = [
            {
                "series_name": r.get("series_name"),
                "source_path": r.get("source_path"),
                "excerpt": r.get("excerpt"),
            }
            for r in tarutani_rows[:8]
        ]
        if t_view:
            st.dataframe(t_view, use_container_width=True, hide_index=True, height=220)
        else:
            st.info("表示できるTarutani_Text抜粋はありません。")

        if isinstance(ref_images, dict):
            _render_reference_image_candidates("参考画像候補", ref_images, target_total=8)

        with st.expander("type2 gate 詳細 / prompt preview（開発確認用）", expanded=False):
            check_rows = [
                {
                    "check_id": c.get("id"),
                    "ok": bool(c.get("ok")),
                    "detail": c.get("detail"),
                }
                for c in type2_result.get("checks", [])
            ]
            st.dataframe(check_rows, use_container_width=True, hide_index=True, height=240)
            st.write(
                {
                    "status": status or ("success" if gate_ok else "gate_hold"),
                    "required_env_keys": type2_result.get("required_env_keys", []),
                    "optional_env_keys": type2_result.get("optional_env_keys", []),
                    "resolved_env": type2_result.get("resolved_env", {}),
                    "api_called": bool(type2_result.get("api_called", False)),
                }
            )
            st.text_area(
                "type 2 prompt プレビュー",
                value=str(type2_result.get("prompt_preview") or ""),
                height=220,
                disabled=True,
            )
            if type2_result.get("error"):
                st.warning(f"画像生成結果: {type2_result.get('error')}")
                debug_err = str(type2_result.get("debug_error") or "")
                if debug_err:
                    st.code(debug_err)
        return

    if not draft:
        return

    st.markdown("**Exclusive Advisor grounded draft（type 1）**")
    _render_evidence_summary(
        {
            "モード": draft.get("mode"),
            "本文文字数": draft.get("answer_chars"),
            "本文上限": EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
            "外部URL件数": draft.get("counts", {}).get("external_url_count", 0),
            "Tarutani抜粋件数": draft.get("counts", {}).get("tarutani_excerpt_count", 0),
            "参考画像候補件数": len((context["external"].get("reference_images", {}) or {}).get("all", [])),
        }
    )
    st.text_area("Exclusive Advisor回答（日本語）", value=draft.get("answer", ""), height=260, disabled=True)
    st.caption(draft.get("attachment_note", ""))

    urls = draft.get("external_evidence_urls", {})
    ex_urls = urls.get("exhibition", [])
    ar_urls = urls.get("artist", [])
    _render_evidence_urls("外部根拠URL", ex_urls, ar_urls)

    st.markdown("**Tarutani_Text抜粋**")
    tarutani_rows = draft.get("tarutani_evidence_excerpts", [])
    t_view = [
        {
            "series_name": r.get("series_name"),
            "source_path": r.get("source_path"),
            "excerpt": r.get("excerpt"),
        }
        for r in tarutani_rows[:8]
    ]
    if t_view:
        st.dataframe(t_view, use_container_width=True, hide_index=True, height=220)
    else:
        st.info("表示できるTarutani_Text抜粋はありません。")

    _render_reference_image_candidates(
        "参考画像候補",
        context["external"].get("reference_images", {}),
        target_total=8,
    )

    if draft.get("warnings"):
        with st.expander("警告（Exclusive Advisor）", expanded=False):
            for warning in draft["warnings"]:
                st.write(f"- {warning}")


def render_gallery_list() -> None:
    _render_mode_heading("⑥ Gallery list（登録ギャラリー一覧 / 読み取り専用）")
    _render_mode_explanation("CSV正本を読み取り専用で表示します（編集・追加・削除・保存なし）。")

    try:
        data = get_gallery_list_data()
    except Exception as exc:
        st.error(f"Gallery list 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    col1, col2 = st.columns([1, 2])
    fair_mode = col1.selectbox(
        "フェア切替",
        FAIR_OPTIONS,
        index=2,
        key="gallery_list_fair_filter",
    )
    keyword = col2.text_input(
        "ギャラリー名キーワード",
        value="",
        placeholder="例: Athr / Adams and Ollman / A+ Works of Art",
        key="gallery_list_keyword",
    )

    effective_fair = fair_mode
    filtered = apply_gallery_list_filters(data.records, effective_fair, keyword)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("総件数", data.total_rows)
    m2.metric("Frieze", data.fair_rows.get("frieze_london", 0))
    m3.metric("Liste", data.fair_rows.get("liste", 0))
    m4.metric("fallback件数", data.artists_fallback_rows)
    m5.metric("警告件数", len(data.warnings))
    st.write(
        {
            "表示件数": len(filtered),
            "artists_url入力あり行": getattr(data, "artists_raw_rows", 0),
            "artists_url空行": getattr(data, "artists_empty_rows", 0),
            "警告サマリ": getattr(data, "warning_counts", {}),
        }
    )
    st.caption("列互換: 3列はそのまま / 2列は artists_url に exhibitions_url を使用（表示専用）。")

    if data.warnings:
        with st.expander("警告（Gallery list）", expanded=False):
            for warning in data.warnings[:30]:
                st.write(f"- {warning}")

    if not filtered:
        st.warning("条件に一致するギャラリーはありません。")
        return

    view_rows = [
        {
            "fair": row.get("fair_label"),
            "gallery_name": row.get("gallery_name"),
            "exhibitions_url": row.get("exhibitions_url_display", row.get("exhibitions_url")),
            "artists_url": row.get("artists_url_display", row.get("artists_url")),
            "artists_mode": row.get("artists_url_mode_label", row.get("artists_url_mode")),
            "exhibitions_link": row.get("exhibitions_url"),
            "artists_link": row.get("artists_url"),
        }
        for row in filtered
    ]
    st.dataframe(
        view_rows,
        use_container_width=True,
        hide_index=True,
        height=360,
        column_config={
            "fair": st.column_config.TextColumn("fair", width="small"),
            "gallery_name": st.column_config.TextColumn("gallery_name", width="medium"),
            "exhibitions_url": st.column_config.TextColumn("exhibitions_url", width="large"),
            "artists_url": st.column_config.TextColumn("artists_url", width="large"),
            "artists_mode": st.column_config.TextColumn("artists_url種別", width="small"),
            "exhibitions_link": st.column_config.LinkColumn("Exhibitions URL", display_text="開く"),
            "artists_link": st.column_config.LinkColumn("Artists URL", display_text="開く"),
        },
    )


def render_phase2_sections() -> None:
    with st.container(border=True):
        render_art_pulse()

    with st.container(border=True):
        render_exhibition_search()

    with st.container(border=True):
        render_artist_search()

    with st.container(border=True):
        render_advisor()

    with st.container(border=True):
        render_exclusive_advisor()

    with st.container(border=True):
        render_gallery_list()

    with st.container(border=True):
        render_artwork_search()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")
    apply_global_font_styles()
    render_header()
    render_phase2_sections()


if __name__ == "__main__":
    main()
