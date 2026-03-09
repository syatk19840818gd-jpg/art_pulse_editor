import re
from html import escape

import streamlit as st

from phase2_art_pulse_config import PERSONAS
from phase2_art_pulse_draft import generate_art_pulse_draft
from phase2_art_pulse_readonly import build_art_pulse_overview
from phase2_advisor_draft import ADVISOR_TEXT_MAX_CHARS, generate_advisor_grounded_draft
from phase2_advisor_readonly import build_advisor_grounded_context
from phase2_advisor_type2_design import collect_failed_checks
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
from phase2_artist_search_readonly import apply_artist_filters, load_artist_records_readonly
from phase2_exhibition_search_readonly import (
    apply_exhibition_filters,
    load_exhibition_records_readonly,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

APP_TITLE = "Art Pulse Editor"
FAIR_OPTIONS = ["Frieze London", "Liste Art Fair Basel", "Frieze London + Liste Art Fair Basel"]
MODE_HEADING_FONT_SIZE_PX = 22
EXPLANATION_OF_MODES_FONT_SIZE_PX = 15
IMAGE_MARKDOWN_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)")
SOURCE_LINE_RE = re.compile(r"^Source:\s*<(?P<url>[^>]+)>\s*$")


def apply_global_font_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --font-latin: "DIN 2014", "DIN Alternate", "DIN Next LT Pro", "DINPro", "DIN";
          --font-cjk: "Yu Gothic", "YuGothic", "貂ｸ繧ｴ繧ｷ繝・け", "Meiryo", sans-serif;
          color-scheme: light;
        }
        html, body {
          background-color: #f5f7fb !important;
          color: #111111 !important;
        }
        .stApp, .stApp * {
          font-family: var(--font-latin), var(--font-cjk) !important;
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
        /* Layout: PC 縺ｯ蠎・￥縲√Δ繝舌う繝ｫ縺ｯ逕ｻ髱｢蟷・↓霑ｽ蠕・*/
        .stApp [data-testid="stMainBlockContainer"],
        .stApp .block-container {
          max-width: min(1680px, 96vw) !important;
          width: 100% !important;
          padding-left: clamp(0.75rem, 2vw, 2.25rem) !important;
          padding-right: clamp(0.75rem, 2vw, 2.25rem) !important;
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
        /* Art Pulse image gallery: PC讓ｪ荳ｦ縺ｳ / 繝｢繝舌う繝ｫ閾ｪ蜍戊ｿｽ蠕・*/
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
          display: block;
          width: 100%;
          aspect-ratio: 4 / 3;
          overflow: hidden;
          border-radius: 10px;
          border: 1px solid #d9dbe2;
          background: #f4f6fb;
        }
        .ap-gallery-thumb img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
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
          .ap-gallery-thumb {
            aspect-ratio: 16 / 10;
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


def _render_responsive_image_gallery(images: list[dict]) -> None:
    if not images:
        return
    html_items = []
    for item in images:
        image_url = str(item.get("image_url") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        alt = escape(str(item.get("alt") or "reference"))
        if not image_url:
            continue
        safe_img = escape(image_url, quote=True)
        safe_src = escape(source_url, quote=True)
        source_html = (
            f'<div class="ap-gallery-source">Source: <a href="{safe_src}" target="_blank">{safe_src}</a></div>'
            if source_url
            else '<div class="ap-gallery-source">Source: (not available)</div>'
        )
        html_items.append(
            (
                '<div class="ap-gallery-item">'
                f'<a class="ap-gallery-thumb" href="{safe_img}" target="_blank" title="逕ｻ蜒上ｒ諡｡螟ｧ陦ｨ遉ｺ">'
                f'<img src="{safe_img}" alt="{alt}" loading="lazy" />'
                "</a>"
                f"{source_html}"
                "</div>"
            )
        )
    if not html_items:
        return
    st.markdown(f'<div class="ap-gallery">{"".join(html_items)}</div>', unsafe_allow_html=True)


def _render_markdown_with_galleries(markdown_text: str) -> None:
    for kind, payload in _split_markdown_and_image_blocks(markdown_text):
        if kind == "markdown":
            st.markdown(payload)
        else:
            _render_responsive_image_gallery(payload)

@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False)
def get_exhibition_search_data():
    return load_exhibition_records_readonly()


@st.cache_data(show_spinner=False)
def get_artist_search_data():
    return load_artist_records_readonly()


@st.cache_data(show_spinner=False)
def get_gallery_list_data():
    return load_gallery_list_records_readonly()


def _exhibition_row_label(row: dict) -> str:
    title = row.get("exhibition_title") or "(辟｡鬘・"
    gallery = row.get("gallery_name") or "(繧ｮ繝｣繝ｩ繝ｪ繝ｼ荳肴・)"
    fair = row.get("fair_label") or "(繝輔ぉ繧｢荳肴・)"
    year = row.get("year") or "-"
    return f"[{fair}] {gallery} | {title} ({year})"


def _artist_row_label(row: dict) -> str:
    artist_name = row.get("artist_name") or "(菴懷ｮｶ蜷堺ｸ肴・)"
    gallery = row.get("gallery_name") or "(繧ｮ繝｣繝ｩ繝ｪ繝ｼ荳肴・)"
    fair = row.get("fair_label") or "(繝輔ぉ繧｢荳肴・)"
    year = row.get("year") or "-"
    return f"[{fair}] {gallery} | {artist_name} ({year})"


def _render_evidence_summary(summary: dict) -> None:
    st.markdown("**譬ｹ諡繧ｵ繝槭Μ**")
    st.write(summary)


def _render_evidence_urls(
    title: str,
    exhibition_urls: list,
    artist_urls: list,
    empty_message: str = "陦ｨ遉ｺ縺ｧ縺阪ｋ譬ｹ諡URL縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・,
) -> None:
    ex_rows = exhibition_urls or []
    ar_rows = artist_urls or []
    ex_urls = [str(x) for x in ex_rows if str(x).strip()]
    ar_urls = [str(x) for x in ar_rows if str(x).strip()]
    total = len(ex_urls) + len(ar_urls)
    st.markdown(f"**{title}**")
    st.caption(f"URL莉ｶ謨ｰ: {total}莉ｶ")
    if total == 0:
        st.info(empty_message)
        return
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"Exhibition URL謨ｰ: {len(ex_urls)}")
        if ex_urls:
            for url in ex_urls[:30]:
                st.write(f"- {url}")
        else:
            st.caption("陦ｨ遉ｺ縺ｧ縺阪ｋExhibition譬ｹ諡URL縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・)
    with c2:
        st.write(f"Artist URL謨ｰ: {len(ar_urls)}")
        if ar_urls:
            for url in ar_urls[:30]:
                st.write(f"- {url}")
        else:
            st.caption("陦ｨ遉ｺ縺ｧ縺阪ｋArtist譬ｹ諡URL縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・)


def _render_reference_image_candidates(
    title: str,
    reference_images: dict,
    target_total: int = 8,
    empty_message: str = "蜿り・判蜒丞呵｣懊・縺ゅｊ縺ｾ縺帙ｓ縲・,
) -> None:
    rows = []
    if isinstance(reference_images, dict):
        rows = list(reference_images.get("all", []) or [])
    st.markdown(f"**{title}**")
    summary = {
        "逶ｮ螳・: target_total,
        "蜿り・判蜒丞呵｣應ｻｶ謨ｰ": len(rows),
    }
    if isinstance(reference_images, dict):
        if "target_exhibition_images" in reference_images:
            summary["逶ｮ螳・Exhibition)"] = reference_images.get("target_exhibition_images")
        if "target_artist_images" in reference_images:
            summary["逶ｮ螳・Artist)"] = reference_images.get("target_artist_images")
    st.write(summary)
    if rows:
        st.dataframe(rows[:8], use_container_width=True, hide_index=True, height=220)
        st.caption("蜿り・判蜒丞呵｣懊・縲∝ｮ牙・縺ｪ荳閾ｴ縺ｧ蜿門ｾ励〒縺阪◆遽・峇縺ｮ縺ｿ陦ｨ遉ｺ縺励※縺・∪縺吶・)
    else:
        st.info(empty_message)


def render_art_pulse() -> None:
    _render_mode_heading("竭 Art Pulse")
    _render_mode_explanation("繧｢繝ｼ繝育ｷｨ髮・ｨ倩・′縲檎樟莉｣繧｢繝ｼ繝医・莉奇ｼ・ow・峨阪ｒ蜿匁攝縺励◆險倅ｺ九ｒ譖ｸ縺・)

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "繝輔ぉ繧｢驕ｸ謚・,
        FAIR_OPTIONS,
        index=2,
        key="artpulse_fair",
    )
    col2.text_input("蟇ｾ雎｡蟷ｴ", value="2025・亥崋螳夲ｼ・, disabled=True, key="artpulse_year")

    reporter = st.selectbox(
        "諡・ｽ楢ｨ倩・ｼ・莠ｺ・・,
        options=PERSONAS,
        format_func=lambda p: f"{p['label']} - {p['description']}",
        key="artpulse_reporter",
    )
    reporter_angles = list(reporter.get("angles", []) or [])
    def _format_angle_full(angle: dict) -> str:
        label = str(angle.get("label") or "")
        description = str(angle.get("description") or "")
        return f"{label}・嘴description}" if description else label

    if reporter_angles:
        selected_angle = st.selectbox(
            "繝・・繝・,
            options=reporter_angles,
            format_func=_format_angle_full,
            key="artpulse_angle",
        )
        angle_keys = [str(selected_angle.get("key") or "")]
    else:
        st.warning("縺薙・險倩・↓蛻・ｊ蜿｣縺悟ｮ夂ｾｩ縺輔ｌ縺ｦ縺・∪縺帙ｓ縲・)
        angle_keys = []

    st.caption("荳翫・譚｡莉ｶ繧帝∈繧薙〒縲窟rt Pulse縲阪ｒ謚ｼ縺吶→ 諡・ｽ楢ｨ倩・′險倅ｺ九ｒ譖ｸ縺阪∪縺吶・)
    run = st.button("Art Pulse", key="artpulse_generate")

    if run:
        try:
            overview = build_art_pulse_overview(
                fair_label=fair_mode,
                reporter_id=reporter["id"],
                angle_keys=angle_keys,
            )
            draft = generate_art_pulse_draft(
                overview=overview,
                reporter_id=reporter["id"],
                angle_keys=angle_keys,
            )
            st.session_state["artpulse_result"] = {"overview": overview, "draft": draft}
        except Exception as exc:
            st.error(f"Art Pulse 逕滓・繧ｨ繝ｩ繝ｼ: {type(exc).__name__}: {exc}")
            return

    result = st.session_state.get("artpulse_result")
    if not result:
        return

    draft = result.get("draft", {})
    st.markdown(f"### {draft.get('title', 'Art Pulse')}")
    _render_markdown_with_galleries(draft.get("body", ""))
    st.caption(f"譛ｬ譁・枚蟄玲焚・育判蜒・Source陦後ｒ髯､縺擾ｼ・ {int(draft.get('body_chars', 0))} / 2000")
    warnings = list(draft.get("warnings", []) or [])
    if warnings:
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・rt Pulse・・, expanded=False):
            for warning in warnings:
                st.write(f"- {warning}")


def render_exhibition_search() -> None:
    _render_mode_heading("竭｡ Exhibition Search・亥ｱ慕､ｺ讀懃ｴ｢・・)
    _render_mode_explanation("formal exhibitions text 縺ｮ隱ｭ縺ｿ蜿悶ｊ蟆ら畑荳隕ｧ縺ｧ縺吶・)

    try:
        data = get_exhibition_search_data()
    except Exception as exc:
        st.error(f"Exhibition 隱ｭ縺ｿ霎ｼ縺ｿ繧ｨ繝ｩ繝ｼ: {type(exc).__name__}: {exc}")
        return

    col1, col2 = st.columns([1, 2])
    fair_mode = col1.selectbox(
        "繝輔ぉ繧｢邨槭ｊ霎ｼ縺ｿ",
        FAIR_OPTIONS,
        index=2,
        key="exh_fair_filter",
    )
    keyword = col2.text_input(
        "繧ｭ繝ｼ繝ｯ繝ｼ繝会ｼ・allery / title / artist names / source_url・・,
        value="",
        placeholder="萓・ Adams and Ollman / Antonia Kuo / https://adamsandollman.com/Antonia-Kuo-Subcycle",
        key="exh_keyword",
    )

    effective_fair = fair_mode
    filtered = apply_exhibition_filters(data.records, effective_fair, keyword)

    st.caption(
        f"莉ｶ謨ｰ: 隱ｭ霎ｼ={data.total_rows} / 陦ｨ遉ｺ={len(filtered)} / "
        f"frieze={data.fair_rows.get('frieze_london', 0)} / liste={data.fair_rows.get('liste', 0)}"
    )
    st.caption(f"豕ｨ險・ {data.count_note}")

    if data.warnings:
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・xhibition Search・・, expanded=False):
            for warning in data.warnings[:20]:
                st.write(f"- {warning}")

    if not filtered:
        st.warning("譚｡莉ｶ縺ｫ荳閾ｴ縺吶ｋ螻慕､ｺ繝・・繧ｿ縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・)
        return

    view_rows = [
        {
            "fair": row.get("fair_label"),
            "gallery": row.get("gallery_name"),
            "title": row.get("exhibition_title"),
            "year": row.get("year"),
            "artists": row.get("artist_names"),
            "source_url": row.get("source_url"),
            "image_count_hint": row.get("image_count_hint", 0),
        }
        for row in filtered
    ]
    st.dataframe(view_rows, use_container_width=True, hide_index=True, height=320)

    selected_idx = st.selectbox(
        "隧ｳ邏ｰ陦ｨ遉ｺ",
        options=list(range(len(filtered))),
        format_func=lambda i: _exhibition_row_label(filtered[i]),
        key="exh_detail_select",
    )
    selected = filtered[selected_idx]

    st.markdown("**螻慕､ｺ隧ｳ邏ｰ・郁ｪｭ縺ｿ蜿悶ｊ蟆ら畑・・*")
    left, right = st.columns([2, 1])
    left.write(f"繝輔ぉ繧｢: {selected.get('fair_label')}")
    left.write(f"繧ｮ繝｣繝ｩ繝ｪ繝ｼ: {selected.get('gallery_name')}")
    left.write(f"螻慕､ｺ繧ｿ繧､繝医Ν: {selected.get('exhibition_title')}")
    left.write(f"蟷ｴ: {selected.get('year')}")
    left.write(f"蜿ょ刈菴懷ｮｶ: {selected.get('artist_names') or '(遨ｺ)'}")
    if selected.get("source_url"):
        left.markdown(f"Source URL: {selected.get('source_url')}")

    right.metric("逕ｻ蜒丈ｻｶ謨ｰ繝偵Φ繝・, int(selected.get("image_count_hint") or 0))
    right.caption("source_url 縺ｮ蜴ｳ蟇・ｸ閾ｴ繝吶・繧ｹ")
    _render_evidence_summary(
        {
            "譬ｹ諡莉ｶ謨ｰ": 1 if selected.get("source_url") else 0,
            "URL莉ｶ謨ｰ": 1 if selected.get("source_url") else 0,
            "蜿り・判蜒丞呵｣應ｻｶ謨ｰ(繝偵Φ繝・": int(selected.get("image_count_hint") or 0),
        }
    )
    _render_evidence_urls(
        title="譬ｹ諡URL荳隕ｧ",
        exhibition_urls=[selected.get("source_url")] if selected.get("source_url") else [],
        artist_urls=[],
    )
    st.markdown("**蜿り・判蜒丞呵｣・*")
    if int(selected.get("image_count_hint") or 0) > 0:
        st.caption("蜿り・判蜒丞呵｣懊・莉ｶ謨ｰ繝偵Φ繝医・縺ｿ陦ｨ遉ｺ縺励※縺・∪縺呻ｼ井ｸ隕ｧ縺ｯ縺薙・逕ｻ髱｢縺ｧ縺ｯ譛ｪ陦ｨ遉ｺ・峨・)
    else:
        st.info("蜿り・判蜒丞呵｣懊・縺ゅｊ縺ｾ縺帙ｓ縲・)

    body = (selected.get("text") or "").strip()
    if body:
        st.text_area("螻慕､ｺ繝・く繧ｹ繝・, value=body[:8000], height=260, disabled=True)
    else:
        st.warning("縺薙・繝ｬ繧ｳ繝ｼ繝峨↓縺ｯ譛ｬ譁・ユ繧ｭ繧ｹ繝医′縺ゅｊ縺ｾ縺帙ｓ縲・)


def render_artist_search() -> None:
    _render_mode_heading("竭｢ Artist Search・井ｽ懷ｮｶ讀懃ｴ｢・・)
    _render_mode_explanation("formal artists text 縺ｮ隱ｭ縺ｿ蜿悶ｊ蟆ら畑荳隕ｧ縺ｧ縺吶・)

    try:
        data = get_artist_search_data()
    except Exception as exc:
        st.error(f"Artist 隱ｭ縺ｿ霎ｼ縺ｿ繧ｨ繝ｩ繝ｼ: {type(exc).__name__}: {exc}")
        return

    col1, col2 = st.columns([1, 2])
    fair_mode = col1.selectbox(
        "繝輔ぉ繧｢邨槭ｊ霎ｼ縺ｿ",
        FAIR_OPTIONS,
        index=2,
        key="artist_fair_filter",
    )
    keyword = col2.text_input(
        "繧ｭ繝ｼ繝ｯ繝ｼ繝会ｼ・rtist / gallery / text / source_url・・,
        value="",
        placeholder="萓・ Sarah Abu Abdallah / Athr / painting / https://athrart.com/artists/",
        key="artist_keyword",
    )

    effective_fair = fair_mode
    filtered = apply_artist_filters(data.records, effective_fair, keyword)

    st.caption(
        f"莉ｶ謨ｰ: 隱ｭ霎ｼ={data.total_rows} / 陦ｨ遉ｺ={len(filtered)} / "
        f"frieze={data.fair_rows.get('frieze_london', 0)} / liste={data.fair_rows.get('liste', 0)}"
    )
    st.caption(f"豕ｨ險・ {data.count_note}")

    if data.warnings:
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・rtist Search・・, expanded=False):
            for warning in data.warnings[:20]:
                st.write(f"- {warning}")

    if not filtered:
        st.warning("譚｡莉ｶ縺ｫ荳閾ｴ縺吶ｋ菴懷ｮｶ繝・・繧ｿ縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・)
        return

    view_rows = [
        {
            "fair": row.get("fair_label"),
            "gallery": row.get("gallery_name"),
            "artist": row.get("artist_name"),
            "year": row.get("year"),
            "source_url": row.get("source_url"),
            "summary": row.get("summary_ja") or "",
            "works_image_count_hint": row.get("works_image_count_hint", 0),
        }
        for row in filtered
    ]
    st.dataframe(view_rows, use_container_width=True, hide_index=True, height=320)

    selected_idx = st.selectbox(
        "隧ｳ邏ｰ陦ｨ遉ｺ",
        options=list(range(len(filtered))),
        format_func=lambda i: _artist_row_label(filtered[i]),
        key="artist_detail_select",
    )
    selected = filtered[selected_idx]

    st.markdown("**菴懷ｮｶ隧ｳ邏ｰ・郁ｪｭ縺ｿ蜿悶ｊ蟆ら畑・・*")
    left, right = st.columns([2, 1])
    left.write(f"繝輔ぉ繧｢: {selected.get('fair_label')}")
    left.write(f"繧ｮ繝｣繝ｩ繝ｪ繝ｼ: {selected.get('gallery_name')}")
    left.write(f"菴懷ｮｶ蜷・ {selected.get('artist_name')}")
    left.write(f"蟷ｴ: {selected.get('year')}")
    if selected.get("source_url"):
        left.markdown(f"Source URL: {selected.get('source_url')}")

    summary_ja = (selected.get("summary_ja") or "").strip()
    if summary_ja:
        left.write(f"隕∫ｴ・ {summary_ja[:300]}")

    right.metric("菴懷刀逕ｻ蜒上ヲ繝ｳ繝・, int(selected.get("works_image_count_hint") or 0))
    right.caption("source_url 縺ｮ蜴ｳ蟇・ｸ閾ｴ繝吶・繧ｹ")
    _render_evidence_summary(
        {
            "譬ｹ諡莉ｶ謨ｰ": 1 if selected.get("source_url") else 0,
            "URL莉ｶ謨ｰ": 1 if selected.get("source_url") else 0,
            "蜿り・判蜒丞呵｣應ｻｶ謨ｰ(繝偵Φ繝・": int(selected.get("works_image_count_hint") or 0),
        }
    )
    _render_evidence_urls(
        title="譬ｹ諡URL荳隕ｧ",
        exhibition_urls=[],
        artist_urls=[selected.get("source_url")] if selected.get("source_url") else [],
    )
    st.markdown("**蜿り・判蜒丞呵｣・*")
    if int(selected.get("works_image_count_hint") or 0) > 0:
        st.caption("蜿り・判蜒丞呵｣懊・莉ｶ謨ｰ繝偵Φ繝医・縺ｿ陦ｨ遉ｺ縺励※縺・∪縺呻ｼ井ｸ隕ｧ縺ｯ縺薙・逕ｻ髱｢縺ｧ縺ｯ譛ｪ陦ｨ遉ｺ・峨・)
    else:
        st.info("蜿り・判蜒丞呵｣懊・縺ゅｊ縺ｾ縺帙ｓ縲・)

    body = (selected.get("text") or "").strip()
    if body:
        st.text_area("菴懷ｮｶ繝・く繧ｹ繝・, value=body[:8000], height=260, disabled=True)
    else:
        st.warning("縺薙・繝ｬ繧ｳ繝ｼ繝峨↓縺ｯ譛ｬ譁・ユ繧ｭ繧ｹ繝医′縺ゅｊ縺ｾ縺帙ｓ縲・)


def render_advisor() -> None:
    _render_mode_heading("竭｣ Advisor・育嶌隲・ｼ・)
    _render_mode_explanation(
        "question type 1・医ユ繧ｭ繧ｹ繝亥屓遲費ｼ峨→ type 2・医ユ繧ｭ繧ｹ繝茨ｼ狗判蜒冗函謌撰ｼ峨ｒ螳溯｣・・
        "type 2 縺ｯ gate 譚｡莉ｶ繧呈ｺ縺溘＠縺溷ｴ蜷医・縺ｿ螳溯｡後・
    )

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "繝輔ぉ繧｢驕ｸ謚・,
        FAIR_OPTIONS,
        index=2,
        key="advisor_fair_filter",
    )
    question_type_label = col2.selectbox(
        "雉ｪ蝠上ち繧､繝・,
        [
            "type 1 = 繝・く繧ｹ繝亥屓遲斐・縺ｿ・井ｻ雁屓螳溯｣・ｼ・,
            "type 2 = 繝・く繧ｹ繝茨ｼ狗判蜒冗函謌撰ｼ・ate莉倥″・・,
        ],
        index=0,
        key="advisor_question_type",
    )

    question_text = st.text_area(
        "逶ｸ隲・・螳ｹ・亥宛菴懊＠縺溘＞菴懷刀縺ｮ讎りｦ√ｄ謔ｩ縺ｿ・・,
        value="",
        height=140,
        key="advisor_question_text",
        placeholder="萓・ 2025蟷ｴ縺ｮ繝輔ぉ繧｢譁・ц縺ｧ縲∫ｴ譚舌→繧ｹ繧ｱ繝ｼ繝ｫ縺ｮ驕ｸ縺ｳ譁ｹ繧堤嶌隲・＠縺溘＞縲・,
    )
    uploaded_image = st.file_uploader(
        "雉ｪ蝠冗判蜒擾ｼ井ｻｻ諢擾ｼ・,
        type=["png", "jpg", "jpeg", "webp"],
        key="advisor_uploaded_image",
    )
    upload_valid = False
    upload_note = "豺ｻ莉倡判蜒上↑縺励・
    if uploaded_image is not None:
        try:
            raw = uploaded_image.getvalue()
            mime = str(getattr(uploaded_image, "type", "") or "")
            if not raw:
                upload_note = "豺ｻ莉倡判蜒上ｒ隱ｭ縺ｿ霎ｼ繧√↑縺九▲縺溘◆繧√∫判蜒上↑縺励→縺励※蜃ｦ逅・＠縺ｾ縺吶・
            elif mime and not mime.startswith("image/"):
                upload_note = "豺ｻ莉倥ヵ繧｡繧､繝ｫ縺檎判蜒丞ｽ｢蠑上〒縺ｯ縺ｪ縺・◆繧√∫判蜒上↑縺励→縺励※蜃ｦ逅・＠縺ｾ縺吶・
            else:
                upload_valid = True
                upload_note = f"豺ｻ莉倡判蜒・ {uploaded_image.name}・井ｿ晏ｭ倥＠縺ｪ縺・/ 繝吶け繝医Ν蛹悶＠縺ｪ縺・/ RAG豺ｷ蜈･縺ｪ縺暦ｼ・
        except Exception:
            upload_note = "豺ｻ莉倡判蜒上・隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺溘◆繧√∫判蜒上↑縺励→縺励※蜃ｦ逅・＠縺ｾ縺吶・

    st.caption(upload_note)
    if question_type_label.startswith("type 2"):
        st.info("type 2 縺ｯ gate 譚｡莉ｶ繧呈ｺ縺溘＠縺溷ｴ蜷医・縺ｿ逕ｻ蜒冗函謌植PI繧貞ｮ溯｡後＠縺ｾ縺吶よ擅莉ｶ荳崎ｶｳ譎ゅ・譛ｬ譁・→譬ｹ諡縺ｮ縺ｿ陦ｨ遉ｺ縺励∪縺吶・)

    run = st.button("Advisor 繧貞ｮ溯｡・, key="advisor_run")
    if run:
        if not question_text.strip():
            st.warning("逶ｸ隲・・螳ｹ繧貞・蜉帙＠縺ｦ縺上□縺輔＞縲・)
            return

        effective_fair = fair_mode
        try:
            context = build_advisor_grounded_context(
                fair_label=effective_fair,
                question_text=question_text,
            )
            st.session_state["advisor_context"] = context
            st.session_state["advisor_selection"] = {
                "fair": effective_fair,
                "question_text": question_text,
                "question_type_label": question_type_label,
            }

            # type2縺ｧ繧ゅ√∪縺喩rounded type1繧剃ｽ懊ｋ・・ext蝗樒ｭ斐・蝓ｺ逶､・・            draft_type1 = generate_advisor_grounded_draft(
                question_text=question_text,
                context=context,
                question_type="type1_text_only",
                has_uploaded_image=upload_valid,
                uploaded_image_name=(uploaded_image.name if uploaded_image is not None else ""),
            )
            st.session_state["advisor_draft"] = draft_type1

            if question_type_label.startswith("type 1"):
                st.session_state["advisor_type2_preview"] = None
            else:
                type2_preview = run_type2_gated_image_generation(
                    fair_label=effective_fair,
                    question_text=question_text,
                    type1_draft=draft_type1,
                    context=context,
                    has_uploaded_image=upload_valid,
                )
                st.session_state["advisor_type2_preview"] = type2_preview
        except Exception as exc:
            st.error("Advisor 螳溯｡御ｸｭ縺ｫ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆縲ょ・蜉帶擅莉ｶ繧定ｦ狗峩縺励※蜀榊ｮ溯｡後＠縺ｦ縺上□縺輔＞縲・)
            with st.expander("隧ｳ邏ｰ・磯幕逋ｺ遒ｺ隱咲畑・・, expanded=False):
                st.code(f"{type(exc).__name__}: {exc}")
            return

    context = st.session_state.get("advisor_context")
    selection = st.session_state.get("advisor_selection", {})
    draft = st.session_state.get("advisor_draft")
    type2_preview = st.session_state.get("advisor_type2_preview")
    selected_qtype = str(selection.get("question_type_label") or "type 1 = 繝・く繧ｹ繝亥屓遲斐・縺ｿ・井ｻ雁屓螳溯｣・ｼ・)

    if not context:
        st.caption("逶ｸ隲・・螳ｹ繧貞・蜉帙＠縺ｦ縲窟dvisor 繧貞ｮ溯｡後阪ｒ謚ｼ縺吶→縲∵ｹ諡譚溘→蝗樒ｭ比ｸ区嶌縺阪ｒ陦ｨ遉ｺ縺励∪縺吶・)
        return

    st.markdown("**Advisor grounding overview・郁ｪｭ縺ｿ蜿悶ｊ蟆ら畑・・*")
    st.write(
        {
            "fair": context["selection"]["fair_label"],
            "year": context["selection"]["year"],
            "question_type": selected_qtype,
            "token_count": len(context["selection"].get("tokens", [])),
        }
    )
    _render_evidence_summary(
        {
            "Exhibitions譬ｹ諡莉ｶ謨ｰ": context["counts"]["exhibitions_text_evidence_count"],
            "Artists譬ｹ諡莉ｶ謨ｰ": context["counts"]["artist_text_evidence_count"],
            "URL莉ｶ謨ｰ": context["counts"]["all_unique_url_count"],
            "蜿り・判蜒丞呵｣應ｻｶ謨ｰ": int(context["counts"]["reference_exhibition_images"])
            + int(context["counts"]["reference_artist_images"]),
        }
    )
    st.caption(f"豕ｨ險・ {context['count_note']}")

    ex_view = [
        {
            "fair": r.get("fair_label"),
            "gallery": r.get("gallery"),
            "title": r.get("title"),
            "year": r.get("year"),
            "source_url": r.get("source_url"),
        }
        for r in context.get("exhibition_evidence", [])[:12]
    ]
    ar_view = [
        {
            "fair": r.get("fair_label"),
            "gallery": r.get("gallery"),
            "artist": r.get("artist_name"),
            "year": r.get("year"),
            "source_url": r.get("source_url"),
        }
        for r in context.get("artist_evidence", [])[:12]
    ]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**譬ｹ諡繝悶Ο繝・け・・xhibitions・・*")
        st.dataframe(ex_view, use_container_width=True, hide_index=True, height=220)
    with c2:
        st.markdown("**譬ｹ諡繝悶Ο繝・け・・rtists・・*")
        st.dataframe(ar_view, use_container_width=True, hide_index=True, height=220)

    ref_images = context.get("reference_images", {})
    _render_reference_image_candidates("蜿り・判蜒丞呵｣・, ref_images, target_total=8)
    if context.get("warnings"):
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・dvisor・・, expanded=False):
            for warning in context["warnings"][:20]:
                st.write(f"- {warning}")

    if selected_qtype.startswith("type 2"):
        st.markdown("**Advisor type 2・・ate莉倥″螳溯｡鯉ｼ・*")
        if not type2_preview:
            st.caption("type 2 繧帝∈繧薙〒 Advisor 繧貞ｮ溯｡後☆繧九→縲“ate蛻､螳壼ｾ後↓譛ｬ譁・→逕ｻ蜒冗函謌千ｵ先棡繧定｡ｨ遉ｺ縺励∪縺吶・)
            return

        gate_ok = bool(type2_preview.get("gate_ok"))
        status = str(type2_preview.get("status") or ("success" if gate_ok else "gate_hold"))
        user_message = str(type2_preview.get("user_message") or "")
        if status == "success":
            st.success("type 2 迥ｶ諷・ 螳溯｡梧・蜉・)
        elif status == "image_failed":
            st.warning("type 2 迥ｶ諷・ 逕ｻ蜒冗函謌仙､ｱ謨暦ｼ域悽譁・→譬ｹ諡縺ｯ陦ｨ遉ｺ・・)
        elif status == "gate_hold":
            st.error("type 2 迥ｶ諷・ gate譛ｪ騾夐℃・域擅莉ｶ荳崎ｶｳ縺ｧ螳溯｡御ｸ榊庄・・)
        elif status == "ready_for_api":
            st.info("type 2 迥ｶ諷・ 蛻ｩ逕ｨ蜿ｯ閭ｽ")
        else:
            st.info("type 2 迥ｶ諷・ 譚｡莉ｶ遒ｺ隱堺ｸｭ")
        if user_message:
            st.caption(user_message)

        if status == "gate_hold":
            failed = collect_failed_checks(type2_preview)
            if failed:
                st.markdown("**譛ｪ騾夐℃譚｡莉ｶ・郁ｦ∫せ・・*")
                for reason in failed[:8]:
                    st.write(f"- {reason}")

        evidence_urls = type2_preview.get("evidence_urls", {}) or {}
        ex_urls = evidence_urls.get("exhibition") or []
        ar_urls = evidence_urls.get("artist") or []
        ref_images = type2_preview.get("reference_images", {}) or {}
        ref_rows = ref_images.get("all") or []

        st.markdown("**Advisor蝗樒ｭ費ｼ域律譛ｬ隱槭》ype 2・・*")
        _render_evidence_summary(
            {
                "譛ｬ譁・枚蟄玲焚": type2_preview.get("text_chars"),
                "譛ｬ譁・ｸ企剞": ADVISOR_TEXT_MAX_CHARS,
                "URL莉ｶ謨ｰ": len(ex_urls) + len(ar_urls),
                "蜿り・判蜒丞呵｣應ｻｶ謨ｰ": len(ref_rows),
            }
        )
        st.text_area(
            "Advisor蝗樒ｭ費ｼ域律譛ｬ隱橸ｼ・,
            value=str(type2_preview.get("text_answer") or ""),
            height=180,
            disabled=True,
        )
        st.caption(str(type2_preview.get("attachment_note") or ""))
        st.caption("豺ｻ莉倡判蜒・逕滓・逕ｻ蜒上・菫晏ｭ倥＠縺ｾ縺帙ｓ・医そ繝・す繝ｧ繝ｳ蜀・｡ｨ遉ｺ縺ｮ縺ｿ・峨・)

        image_bytes = type2_preview.get("generated_image_bytes")
        image_url = str(type2_preview.get("generated_image_url") or "")
        if image_bytes:
            st.image(image_bytes, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        elif image_url:
            st.image(image_url, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        else:
            st.info("逕滓・逕ｻ蜒上・縺ゅｊ縺ｾ縺帙ｓ・・ate譛ｪ騾夐℃縺ｾ縺溘・逕ｻ蜒冗函謌仙､ｱ謨暦ｼ峨・)

        _render_evidence_urls("譬ｹ諡URL荳隕ｧ", ex_urls, ar_urls)

        if isinstance(ref_images, dict):
            _render_reference_image_candidates("蜿り・判蜒丞呵｣・, ref_images, target_total=8)

        with st.expander("type2 gate 隧ｳ邏ｰ / prompt preview・磯幕逋ｺ遒ｺ隱咲畑・・, expanded=False):
            check_rows = [
                {
                    "check_id": c.get("id"),
                    "ok": bool(c.get("ok")),
                    "detail": c.get("detail"),
                }
                for c in type2_preview.get("checks", [])
            ]
            st.dataframe(check_rows, use_container_width=True, hide_index=True, height=260)
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
                "type 2 prompt 繝励Ξ繝薙Η繝ｼ",
                value=str(type2_preview.get("prompt_preview") or ""),
                height=260,
                disabled=True,
            )
            if type2_preview.get("error"):
                st.warning(f"逕ｻ蜒冗函謌千ｵ先棡: {type2_preview.get('error')}")
                debug_err = str(type2_preview.get("debug_error") or "")
                if debug_err:
                    st.code(debug_err)

        if draft:
            st.markdown("**type 2 螳溯｡悟燕縺ｮ grounded baseline・・ype 1・・*")
            st.write(
                {
                    "answer_chars": draft.get("answer_chars"),
                    "max_chars": ADVISOR_TEXT_MAX_CHARS,
                    "evidence_count": draft.get("evidence_counts", {}).get("all_unique_urls", 0),
                }
            )
            st.text_area("grounded 繝吶・繧ｹ繝ｩ繧､繝ｳ・・ype 1・・, value=draft.get("answer", ""), height=180, disabled=True)
        return

    if not draft:
        return

    st.markdown("**Advisor grounded draft・・ype 1・・*")
    _render_evidence_summary(
        {
            "雉ｪ蝠上ち繧､繝・: draft.get("question_type"),
            "繝｢繝ｼ繝・: draft.get("mode"),
            "譛ｬ譁・枚蟄玲焚": draft.get("answer_chars"),
            "譛ｬ譁・ｸ企剞": ADVISOR_TEXT_MAX_CHARS,
            "URL莉ｶ謨ｰ": draft.get("evidence_counts", {}).get("all_unique_urls", 0),
        }
    )
    st.text_area("Advisor蝗樒ｭ費ｼ域律譛ｬ隱橸ｼ・, value=draft.get("answer", ""), height=200, disabled=True)
    st.caption(draft.get("attachment_note", ""))

    urls = draft.get("evidence_urls", {})
    ex_urls = urls.get("exhibition", [])
    ar_urls = urls.get("artist", [])
    _render_evidence_urls("譬ｹ諡URL荳隕ｧ", ex_urls, ar_urls)
    _render_reference_image_candidates("蜿り・判蜒丞呵｣・, context.get("reference_images", {}), target_total=8)
    if draft.get("warnings"):
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・dvisor・・, expanded=False):
            for warning in draft["warnings"]:
                st.write(f"- {warning}")


def render_exclusive_advisor() -> None:
    _render_mode_heading("竭､ Exclusive Advisor・亥桙隹ｷ蟆ょｱ橸ｼ・)
    _render_mode_explanation(
        "type 1・医ユ繧ｭ繧ｹ繝亥屓遲費ｼ峨→ type 2・医ユ繧ｭ繧ｹ繝茨ｼ狗判蜒冗函謌撰ｼ峨ｒ螳溯｣・・
        "Tarutani_Text 縺ｯ譁・ц蜿ら・縺ｨ縺励※縺ｮ縺ｿ菴ｿ逕ｨ縺励∪縺吶・
    )

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "繝輔ぉ繧｢驕ｸ謚・,
        FAIR_OPTIONS,
        index=2,
        key="exclusive_fair_filter",
    )
    question_type_label = col2.selectbox(
        "雉ｪ蝠上ち繧､繝・,
        [
            "type 1 = 繝・く繧ｹ繝亥屓遲斐・縺ｿ・井ｻ雁屓螳溯｣・ｼ・,
            "type 2 = 繝・く繧ｹ繝茨ｼ狗判蜒冗函謌撰ｼ・ate莉倥″・・,
        ],
        index=0,
        key="exclusive_question_type",
    )

    question_text = st.text_area(
        "逶ｸ隲・・螳ｹ・亥桙隹ｷ譁・ц繧定ｸ上∪縺医◆蛻ｶ菴懃嶌隲・ｼ・,
        value="",
        height=140,
        key="exclusive_question_text",
        placeholder="萓・ 驕主悉菴懊→霑台ｽ懊・繧ｷ繝ｪ繝ｼ繧ｺ譁・ц繧定ｸ上∪縺医※縲・025蟷ｴ繝輔ぉ繧｢縺ｧ讖溯・縺吶ｋ螻慕､ｺ謠先｡医↓縺励◆縺・・,
    )
    uploaded_image = st.file_uploader(
        "雉ｪ蝠冗判蜒擾ｼ井ｻｻ諢擾ｼ・,
        type=["png", "jpg", "jpeg", "webp"],
        key="exclusive_uploaded_image",
    )

    upload_valid = False
    upload_note = "豺ｻ莉倡判蜒上↑縺励・
    if uploaded_image is not None:
        try:
            raw = uploaded_image.getvalue()
            mime = str(getattr(uploaded_image, "type", "") or "")
            if not raw:
                upload_note = "豺ｻ莉倡判蜒上ｒ隱ｭ縺ｿ霎ｼ繧√↑縺九▲縺溘◆繧√∫判蜒上↑縺励→縺励※蜃ｦ逅・＠縺ｾ縺吶・
            elif mime and not mime.startswith("image/"):
                upload_note = "豺ｻ莉倥ヵ繧｡繧､繝ｫ縺檎判蜒丞ｽ｢蠑上〒縺ｯ縺ｪ縺・◆繧√∫判蜒上↑縺励→縺励※蜃ｦ逅・＠縺ｾ縺吶・
            else:
                upload_valid = True
                upload_note = f"豺ｻ莉倡判蜒・ {uploaded_image.name}・井ｿ晏ｭ倥＠縺ｪ縺・/ 繝吶け繝医Ν蛹悶＠縺ｪ縺・/ RAG豺ｷ蜈･縺ｪ縺暦ｼ・
        except Exception:
            upload_note = "豺ｻ莉倡判蜒上・隱ｭ縺ｿ霎ｼ縺ｿ縺ｫ螟ｱ謨励＠縺溘◆繧√∫判蜒上↑縺励→縺励※蜃ｦ逅・＠縺ｾ縺吶・
    st.caption(upload_note)

    run = st.button("Exclusive Advisor 繧貞ｮ溯｡・, key="exclusive_run")
    if run:
        if not question_text.strip():
            st.warning("逶ｸ隲・・螳ｹ繧貞・蜉帙＠縺ｦ縺上□縺輔＞縲・)
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
            st.error("Exclusive Advisor 螳溯｡御ｸｭ縺ｫ繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺励◆縲ょ・蜉帶擅莉ｶ繧定ｦ狗峩縺励※蜀榊ｮ溯｡後＠縺ｦ縺上□縺輔＞縲・)
            with st.expander("隧ｳ邏ｰ・磯幕逋ｺ遒ｺ隱咲畑・・, expanded=False):
                st.code(f"{type(exc).__name__}: {exc}")
            return

    context = st.session_state.get("exclusive_context")
    selection = st.session_state.get("exclusive_selection", {})
    draft = st.session_state.get("exclusive_draft")
    type2_result = st.session_state.get("exclusive_type2")
    active_qtype = selection.get("question_type_label", question_type_label)

    if not context:
        st.caption("逶ｸ隲・・螳ｹ繧貞・蜉帙＠縺ｦ縲窪xclusive Advisor 繧貞ｮ溯｡後阪ｒ謚ｼ縺吶→縲“rounded draft 繧定｡ｨ遉ｺ縺励∪縺吶・)
        return

    st.markdown("**Exclusive Advisor grounding overview・郁ｪｭ縺ｿ蜿悶ｊ蟆ら畑・・*")
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
            "螟夜ΚExhibitions譬ｹ諡莉ｶ謨ｰ": context["external"].get("counts", {}).get("exhibitions_text_evidence_count", 0),
            "螟夜ΚArtists譬ｹ諡莉ｶ謨ｰ": context["external"].get("counts", {}).get("artist_text_evidence_count", 0),
            "螟夜ΚURL莉ｶ謨ｰ": context["external"].get("counts", {}).get("all_unique_url_count", 0),
            "Tarutani謚懃ｲ倶ｻｶ謨ｰ": context["tarutani"].get("count", 0),
            "蜿り・判蜒丞呵｣應ｻｶ謨ｰ": len((context["external"].get("reference_images", {}) or {}).get("all", [])),
        }
    )
    st.caption(f"豕ｨ險・螟夜Κ): {context['external'].get('count_note', '')}")
    st.caption(f"豕ｨ險・Tarutani): {context['tarutani'].get('count_note', '')}")

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
        st.markdown("**譬ｹ諡繝悶Ο繝・け・亥､夜ΚExhibitions・・*")
        st.dataframe(ex_view, use_container_width=True, hide_index=True, height=220)
    with c2:
        st.markdown("**譬ｹ諡繝悶Ο繝・け・亥､夜ΚArtists・・*")
        st.dataframe(ar_view, use_container_width=True, hide_index=True, height=220)

    ref_images = context["external"].get("reference_images", {})
    _render_reference_image_candidates("蜿り・判蜒丞呵｣・, ref_images, target_total=8)
    if context.get("warnings"):
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・xclusive Advisor・・, expanded=False):
            for warning in context["warnings"][:20]:
                st.write(f"- {warning}")

    if active_qtype.startswith("type 2"):
        st.markdown("**Exclusive Advisor type 2・・ate莉倥″螳溯｡鯉ｼ・*")
        if not type2_result:
            st.caption("type 2 繧帝∈繧薙〒 Exclusive Advisor 繧貞ｮ溯｡後☆繧九→縲“ate蛻､螳壼ｾ後↓譛ｬ譁・→逕ｻ蜒冗函謌千ｵ先棡繧定｡ｨ遉ｺ縺励∪縺吶・)
            return

        gate_ok = bool(type2_result.get("gate_ok"))
        status = str(type2_result.get("status") or "")
        user_message = str(type2_result.get("user_message") or "")
        if status == "success":
            st.success("type 2 迥ｶ諷・ 螳溯｡梧・蜉・)
        elif status == "image_failed":
            st.warning("type 2 迥ｶ諷・ 逕ｻ蜒冗函謌仙､ｱ謨暦ｼ域悽譁・→譬ｹ諡縺ｯ陦ｨ遉ｺ・・)
        elif status == "gate_hold":
            st.error("type 2 迥ｶ諷・ gate譛ｪ騾夐℃・域擅莉ｶ荳崎ｶｳ縺ｧ螳溯｡御ｸ榊庄・・)
        elif gate_ok:
            st.info("type 2 迥ｶ諷・ 蛻ｩ逕ｨ蜿ｯ閭ｽ")
        else:
            st.info("type 2 迥ｶ諷・ 譚｡莉ｶ遒ｺ隱堺ｸｭ")
        if user_message:
            st.caption(user_message)

        if status == "gate_hold":
            failed = collect_failed_checks_exclusive_type2(type2_result)
            if failed:
                st.markdown("**譛ｪ騾夐℃譚｡莉ｶ・郁ｦ∫せ・・*")
                for reason in failed[:8]:
                    st.write(f"- {reason}")

        external_urls = type2_result.get("external_evidence_urls", {}) or {}
        ex_urls = external_urls.get("exhibition") or []
        ar_urls = external_urls.get("artist") or []
        tarutani_rows = type2_result.get("tarutani_evidence_excerpts", []) or []
        ref_images = type2_result.get("reference_images", {}) or {}
        ref_rows = ref_images.get("all") or []

        st.markdown("**Exclusive Advisor蝗樒ｭ費ｼ域律譛ｬ隱槭》ype 2・・*")
        _render_evidence_summary(
            {
                "譛ｬ譁・枚蟄玲焚": type2_result.get("text_chars"),
                "譛ｬ譁・ｸ企剞": EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
                "螟夜ΚURL莉ｶ謨ｰ": len(ex_urls) + len(ar_urls),
                "Tarutani謚懃ｲ倶ｻｶ謨ｰ": len(tarutani_rows),
                "蜿り・判蜒丞呵｣應ｻｶ謨ｰ": len(ref_rows),
            }
        )
        st.text_area(
            "Exclusive Advisor蝗樒ｭ費ｼ域律譛ｬ隱橸ｼ・,
            value=str(type2_result.get("text_answer") or ""),
            height=220,
            disabled=True,
        )
        st.caption(str(type2_result.get("attachment_note") or ""))
        st.caption("豺ｻ莉倡判蜒・逕滓・逕ｻ蜒上・菫晏ｭ倥＠縺ｾ縺帙ｓ・医そ繝・す繝ｧ繝ｳ蜀・｡ｨ遉ｺ縺ｮ縺ｿ・峨・)

        image_bytes = type2_result.get("generated_image_bytes")
        image_url = str(type2_result.get("generated_image_url") or "")
        if image_bytes:
            st.image(image_bytes, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        elif image_url:
            st.image(image_url, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        else:
            st.info("逕滓・逕ｻ蜒上・縺ゅｊ縺ｾ縺帙ｓ・・ate譛ｪ騾夐℃縺ｾ縺溘・逕ｻ蜒冗函謌仙､ｱ謨暦ｼ峨・)

        _render_evidence_urls("螟夜Κ譬ｹ諡URL", ex_urls, ar_urls)

        st.markdown("**Tarutani_Text謚懃ｲ・*")
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
            st.info("陦ｨ遉ｺ縺ｧ縺阪ｋTarutani_Text謚懃ｲ九・縺ゅｊ縺ｾ縺帙ｓ縲・)

        if isinstance(ref_images, dict):
            _render_reference_image_candidates("蜿り・判蜒丞呵｣・, ref_images, target_total=8)

        with st.expander("type2 gate 隧ｳ邏ｰ / prompt preview・磯幕逋ｺ遒ｺ隱咲畑・・, expanded=False):
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
                "type 2 prompt 繝励Ξ繝薙Η繝ｼ",
                value=str(type2_result.get("prompt_preview") or ""),
                height=220,
                disabled=True,
            )
            if type2_result.get("error"):
                st.warning(f"逕ｻ蜒冗函謌千ｵ先棡: {type2_result.get('error')}")
                debug_err = str(type2_result.get("debug_error") or "")
                if debug_err:
                    st.code(debug_err)
        return

    if not draft:
        return

    st.markdown("**Exclusive Advisor grounded draft・・ype 1・・*")
    _render_evidence_summary(
        {
            "繝｢繝ｼ繝・: draft.get("mode"),
            "譛ｬ譁・枚蟄玲焚": draft.get("answer_chars"),
            "譛ｬ譁・ｸ企剞": EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
            "螟夜ΚURL莉ｶ謨ｰ": draft.get("counts", {}).get("external_url_count", 0),
            "Tarutani謚懃ｲ倶ｻｶ謨ｰ": draft.get("counts", {}).get("tarutani_excerpt_count", 0),
            "蜿り・判蜒丞呵｣應ｻｶ謨ｰ": len((context["external"].get("reference_images", {}) or {}).get("all", [])),
        }
    )
    st.text_area("Exclusive Advisor蝗樒ｭ費ｼ域律譛ｬ隱橸ｼ・, value=draft.get("answer", ""), height=260, disabled=True)
    st.caption(draft.get("attachment_note", ""))

    urls = draft.get("external_evidence_urls", {})
    ex_urls = urls.get("exhibition", [])
    ar_urls = urls.get("artist", [])
    _render_evidence_urls("螟夜Κ譬ｹ諡URL", ex_urls, ar_urls)

    st.markdown("**Tarutani_Text謚懃ｲ・*")
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
        st.info("陦ｨ遉ｺ縺ｧ縺阪ｋTarutani_Text謚懃ｲ九・縺ゅｊ縺ｾ縺帙ｓ縲・)

    _render_reference_image_candidates(
        "蜿り・判蜒丞呵｣・,
        context["external"].get("reference_images", {}),
        target_total=8,
    )

    if draft.get("warnings"):
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・xclusive Advisor・・, expanded=False):
            for warning in draft["warnings"]:
                st.write(f"- {warning}")


def render_gallery_list() -> None:
    _render_mode_heading("竭･ Gallery list・育匳骭ｲ繧ｮ繝｣繝ｩ繝ｪ繝ｼ荳隕ｧ / 隱ｭ縺ｿ蜿悶ｊ蟆ら畑・・)
    _render_mode_explanation("CSV豁｣譛ｬ繧定ｪｭ縺ｿ蜿悶ｊ蟆ら畑縺ｧ陦ｨ遉ｺ縺励∪縺呻ｼ育ｷｨ髮・・霑ｽ蜉繝ｻ蜑企勁繝ｻ菫晏ｭ倥↑縺暦ｼ峨・)

    try:
        data = get_gallery_list_data()
    except Exception as exc:
        st.error(f"Gallery list 隱ｭ縺ｿ霎ｼ縺ｿ繧ｨ繝ｩ繝ｼ: {type(exc).__name__}: {exc}")
        return

    col1, col2 = st.columns([1, 2])
    fair_mode = col1.selectbox(
        "繝輔ぉ繧｢蛻・崛",
        FAIR_OPTIONS,
        index=2,
        key="gallery_list_fair_filter",
    )
    keyword = col2.text_input(
        "繧ｮ繝｣繝ｩ繝ｪ繝ｼ蜷阪く繝ｼ繝ｯ繝ｼ繝・,
        value="",
        placeholder="萓・ Athr / Adams and Ollman / A+ Works of Art",
        key="gallery_list_keyword",
    )

    effective_fair = fair_mode
    filtered = apply_gallery_list_filters(data.records, effective_fair, keyword)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("邱丈ｻｶ謨ｰ", data.total_rows)
    m2.metric("Frieze", data.fair_rows.get("frieze_london", 0))
    m3.metric("Liste", data.fair_rows.get("liste", 0))
    m4.metric("fallback莉ｶ謨ｰ", data.artists_fallback_rows)
    m5.metric("隴ｦ蜻贋ｻｶ謨ｰ", len(data.warnings))
    st.write(
        {
            "陦ｨ遉ｺ莉ｶ謨ｰ": len(filtered),
            "artists_url蜈･蜉帙≠繧願｡・: getattr(data, "artists_raw_rows", 0),
            "artists_url遨ｺ陦・: getattr(data, "artists_empty_rows", 0),
            "隴ｦ蜻翫し繝槭Μ": getattr(data, "warning_counts", {}),
        }
    )
    st.caption(data.count_note)
    st.caption("蛻嶺ｺ呈鋤: 3蛻励・縺昴・縺ｾ縺ｾ / 2蛻励・ artists_url 縺ｫ exhibitions_url 繧剃ｽｿ逕ｨ・郁｡ｨ遉ｺ蟆ら畑・峨・)

    if data.warnings:
        with st.expander("隴ｦ蜻・豕ｨ險假ｼ・allery list・・, expanded=False):
            for warning in data.warnings[:30]:
                st.write(f"- {warning}")

    if not filtered:
        st.warning("譚｡莉ｶ縺ｫ荳閾ｴ縺吶ｋ繧ｮ繝｣繝ｩ繝ｪ繝ｼ縺ｯ縺ゅｊ縺ｾ縺帙ｓ縲・)
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
            "artists_mode": st.column_config.TextColumn("artists_url遞ｮ蛻･", width="small"),
            "exhibitions_link": st.column_config.LinkColumn("Exhibitions URL", display_text="髢九￥"),
            "artists_link": st.column_config.LinkColumn("Artists URL", display_text="髢九￥"),
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


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="collapsed")
    apply_global_font_styles()
    render_header()
    render_phase2_sections()


if __name__ == "__main__":
    main()
