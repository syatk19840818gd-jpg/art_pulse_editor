import os
import time

import streamlit as st

from phase2_art_pulse_config import ANGLES, PERSONAS
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
from phase2_formal_readonly_summary import build_counts

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

APP_TITLE = "Art Pulse Editor"
PHASE2_LABEL = "Phase2 kickoff: read-only formal viewer"

REQUIRED = [
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT",
    "R2_BUCKET",
]

ALIASES = {
    "R2_ENDPOINT": ["R2_ENDPOINT", "R2_ENDPOINT_URL", "R2_S3_ENDPOINT"],
    "OPENAI_API_KEY": ["OPENAI_API_KEY"],
    "GEMINI_API_KEY": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "R2_BUCKET": ["R2_BUCKET"],
    "R2_ACCESS_KEY_ID": ["R2_ACCESS_KEY_ID"],
    "R2_SECRET_ACCESS_KEY": ["R2_SECRET_ACCESS_KEY"],
    "R2_REGION": ["R2_REGION"],
    "TEXT_MODEL": ["TEXT_MODEL"],
    "TEXT_EMBEDDING_MODEL": ["TEXT_EMBEDDING_MODEL"],
    "TEXT_EMBEDDING_OUTPUT_DIM": ["TEXT_EMBEDDING_OUTPUT_DIM"],
}

FAIR_OPTIONS = ["Frieze London", "Liste Art Fair Basel", "Frieze London + Liste Art Fair Basel"]


def get_any(names, default=None):
    for key in names:
        try:
            if key in st.secrets:
                value = st.secrets[key]
                if value:
                    return value
        except Exception:
            pass
        value = os.getenv(key)
        if value:
            return value
    return default


def get_key(key: str, default=None):
    return get_any(ALIASES.get(key, [key]), default=default)


def render_sidebar() -> str:
    st.sidebar.header("Phase2 scope")
    selected_fair = st.sidebar.selectbox("フェア", FAIR_OPTIONS, index=2)
    st.sidebar.text_input("対象年", value="2025（固定）", disabled=True)
    st.sidebar.caption("read-only: formal参照のみ（抽出/R2同期/formal更新なし）")
    return selected_fair


def render_header(selected_fair: str) -> None:
    st.title(APP_TITLE)
    st.caption(PHASE2_LABEL)
    st.info(
        f"対象フェア: {selected_fair} / 年: 2025\n\n"
        "この画面は formal データを読み取り専用で表示します。"
    )


def render_count_summary(selected_fair: str) -> None:
    st.subheader("formal 件数サマリ（read-only）")
    try:
        counts = build_counts(selected_fair)
    except Exception as exc:
        st.error(f"件数サマリ生成エラー: {type(exc).__name__}: {exc}")
        return

    rows = list(counts["breakdown_rows"])
    if counts["total_row"]:
        rows.append(counts["total_row"])
    st.table(rows)
    st.metric("Tarutani Text rows", counts["tarutani_total_rows"])
    st.caption(
        f"Tarutani non-empty rows: {counts['tarutani_non_empty_text_rows']} / "
        f"derived/images files: {counts['images_cache_file_count']}"
    )
    st.caption(f"count note: {counts['count_note']}")

    if counts["warnings"]:
        with st.expander("件数サマリ警告", expanded=False):
            for warning in counts["warnings"][:20]:
                st.write(f"- {warning}")


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
    title = row.get("exhibition_title") or "(untitled)"
    gallery = row.get("gallery_name") or "(no gallery)"
    fair = row.get("fair_label") or "(no fair)"
    year = row.get("year") or "-"
    return f"[{fair}] {gallery} | {title} ({year})"


def _artist_row_label(row: dict) -> str:
    artist_name = row.get("artist_name") or "(unknown artist)"
    gallery = row.get("gallery_name") or "(no gallery)"
    fair = row.get("fair_label") or "(no fair)"
    year = row.get("year") or "-"
    return f"[{fair}] {gallery} | {artist_name} ({year})"


def render_art_pulse(selected_fair: str) -> None:
    st.markdown("**① Art Pulse**")
    st.caption("記事生成の前段として、read-only で evidence overview を表示します。")

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "フェア選択",
        ["サイドバー選択を使用"] + FAIR_OPTIONS,
        index=0,
        key="artpulse_fair",
    )
    col2.text_input("対象年", value="2025（固定）", disabled=True, key="artpulse_year")

    reporter = st.selectbox(
        "担当記者（8名）",
        options=PERSONAS,
        format_func=lambda p: f"{p['label']} - {p['description']}",
        key="artpulse_reporter",
    )
    selected_angles = st.multiselect(
        "切り口（angles）",
        options=ANGLES,
        default=ANGLES[:2],
        format_func=lambda a: a["label"],
        key="artpulse_angles",
    )

    run = st.button("Art Pulse overview を表示", key="artpulse_run")
    if not run:
        st.caption("上の条件を選んでボタンを押すと、根拠候補の概要を表示します。")
        overview = st.session_state.get("artpulse_overview")
        if not overview:
            return
    else:
        effective_fair = selected_fair if fair_mode == "サイドバー選択を使用" else fair_mode
        angle_keys = [a["key"] for a in selected_angles]

        try:
            overview = build_art_pulse_overview(
                fair_label=effective_fair,
                reporter_id=reporter["id"],
                angle_keys=angle_keys,
            )
        except Exception as exc:
            st.error(f"Art Pulse overview 生成エラー: {type(exc).__name__}: {exc}")
            return

        st.session_state["artpulse_overview"] = overview
        st.session_state["artpulse_selection"] = {
            "fair": effective_fair,
            "reporter_id": reporter["id"],
            "angle_keys": angle_keys,
        }
        st.session_state["artpulse_draft"] = None
    overview = st.session_state.get("artpulse_overview")
    selection = st.session_state.get("artpulse_selection", {})

    st.markdown("**選択中の条件**")
    st.write(
        {
            "fair": overview["selection"]["fair_label"],
            "year": overview["selection"]["year"],
            "reporter": overview["selection"]["reporter_label"],
            "angles": overview["selection"]["angle_labels"],
        }
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Exhibitions text", overview["counts"]["exhibitions_text_count"])
    m2.metric("Artist text", overview["counts"]["artist_text_count"])
    m3.metric("Exhibitions image候補", overview["counts"]["exhibitions_image_candidate_count"])
    m4.metric("Artist works image候補", overview["counts"]["artist_image_candidate_count"])
    st.caption(overview["count_note"])

    if overview["warnings"]:
        with st.expander("Art Pulse 読み込み警告", expanded=False):
            for warning in overview["warnings"][:20]:
                st.write(f"- {warning}")

    c1, c2 = st.columns(2)
    c1.markdown("**gallery分布（上位）**")
    c1.dataframe(overview["top_galleries"], use_container_width=True, hide_index=True, height=220)
    c2.markdown("**artist頻出（上位）**")
    c2.dataframe(overview["top_artists"], use_container_width=True, hide_index=True, height=220)

    st.markdown("**exhibition候補（上位）**")
    st.dataframe(
        overview["exhibition_candidates"],
        use_container_width=True,
        hide_index=True,
        height=260,
    )

    st.markdown("**参照画像候補（目安: Exhibition 4 + Artist 4）**")
    plan = overview["image_reference_plan"]
    p1, p2 = st.columns(2)
    p1.write(
        {
            "target_exhibition_images": plan["target_exhibition_images"],
            "available_exhibition_images": plan["available_exhibition_images"],
        }
    )
    p2.write(
        {
            "target_artist_images": plan["target_artist_images"],
            "available_artist_images": plan["available_artist_images"],
        }
    )
    st.dataframe(
        plan["exhibition_image_candidates"] + plan["artist_image_candidates"],
        use_container_width=True,
        hide_index=True,
        height=220,
    )

    st.info(overview["preview_note"])

    st.markdown("**Art Pulse 下書き生成（日本語 / 2000字上限）**")
    st.caption("複数angle選択時は先頭1件のみ生成に使用します。")
    if st.button("この条件で下書きを生成", key="artpulse_draft_run"):
        try:
            draft = generate_art_pulse_draft(
                overview=overview,
                reporter_id=str(selection.get("reporter_id") or reporter["id"]),
                angle_keys=list(selection.get("angle_keys") or [ANGLES[0]["key"]]),
            )
            st.session_state["artpulse_draft"] = draft
        except Exception as exc:
            st.error(f"Art Pulse 下書き生成エラー: {type(exc).__name__}: {exc}")

    draft = st.session_state.get("artpulse_draft")
    if draft:
        st.markdown("**生成下書き**")
        st.write(
            {
                "title": draft["title"],
                "persona": draft["persona_label"],
                "angle": draft["angle_label"],
                "fair": draft["fair_label"],
                "body_chars": draft["body_chars"],
                "mode": draft["mode"],
                "evidence_count": draft["evidence_counts"]["all_unique_urls"],
            }
        )
        st.text_area("Art Pulse draft（本文）", value=draft["body"], height=300, disabled=True)
        st.caption("本文文字数は上限2000字で制御（URL一覧は本文文字数に含めない）。")

        urls = draft.get("evidence_urls", {})
        ex_urls = urls.get("exhibition", [])
        ar_urls = urls.get("artist", [])
        st.markdown("**根拠URL一覧**")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"Exhibition URLs: {len(ex_urls)}")
            for url in ex_urls[:30]:
                st.write(f"- {url}")
        with c2:
            st.write(f"Artist URLs: {len(ar_urls)}")
            for url in ar_urls[:30]:
                st.write(f"- {url}")
        if draft.get("warnings"):
            with st.expander("Draft generation warnings", expanded=False):
                for warning in draft["warnings"]:
                    st.write(f"- {warning}")


def render_exhibition_search(selected_fair: str) -> None:
    st.markdown("**② Exhibition Search（展示検索）**")
    st.caption("formal exhibitions text の read-only 一覧です。")

    try:
        data = get_exhibition_search_data()
    except Exception as exc:
        st.error(f"Exhibition 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    col1, col2 = st.columns([1, 2])
    fair_mode = col1.selectbox(
        "フェア絞り込み",
        ["サイドバー選択を使用"] + FAIR_OPTIONS,
        index=0,
        key="exh_fair_filter",
    )
    keyword = col2.text_input(
        "キーワード（gallery / title / artist names / source_url）",
        value="",
        key="exh_keyword",
    )

    effective_fair = selected_fair if fair_mode == "サイドバー選択を使用" else fair_mode
    filtered = apply_exhibition_filters(data.records, effective_fair, keyword)

    st.caption(
        f"rows: loaded={data.total_rows} / filtered={len(filtered)} / "
        f"frieze={data.fair_rows.get('frieze_london', 0)} / liste={data.fair_rows.get('liste', 0)}"
    )
    st.caption(f"data note: {data.count_note}")

    if data.warnings:
        with st.expander("Exhibition 読み込み警告", expanded=False):
            for warning in data.warnings[:20]:
                st.write(f"- {warning}")

    if not filtered:
        st.warning("該当する展示データがありません。")
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
        "詳細表示",
        options=list(range(len(filtered))),
        format_func=lambda i: _exhibition_row_label(filtered[i]),
        key="exh_detail_select",
    )
    selected = filtered[selected_idx]

    st.markdown("**展示詳細（read-only）**")
    left, right = st.columns([2, 1])
    left.write(f"Fair: {selected.get('fair_label')}")
    left.write(f"Gallery: {selected.get('gallery_name')}")
    left.write(f"Title: {selected.get('exhibition_title')}")
    left.write(f"Year: {selected.get('year')}")
    left.write(f"Artist names: {selected.get('artist_names') or '(empty)'}")
    if selected.get("source_url"):
        left.markdown(f"Source URL: {selected.get('source_url')}")

    right.metric("Image count hint", int(selected.get("image_count_hint") or 0))
    right.caption("source_url strict-match hint only")

    body = (selected.get("text") or "").strip()
    if body:
        st.text_area("Exhibition text", value=body[:8000], height=260, disabled=True)
    else:
        st.warning("このレコードは text が空です。")


def render_artist_search(selected_fair: str) -> None:
    st.markdown("**③ Artist Search（作家検索）**")
    st.caption("formal artists text の read-only 一覧です。")

    try:
        data = get_artist_search_data()
    except Exception as exc:
        st.error(f"Artist 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    col1, col2 = st.columns([1, 2])
    fair_mode = col1.selectbox(
        "フェア絞り込み",
        ["サイドバー選択を使用"] + FAIR_OPTIONS,
        index=0,
        key="artist_fair_filter",
    )
    keyword = col2.text_input(
        "キーワード（artist / gallery / text / source_url）",
        value="",
        key="artist_keyword",
    )

    effective_fair = selected_fair if fair_mode == "サイドバー選択を使用" else fair_mode
    filtered = apply_artist_filters(data.records, effective_fair, keyword)

    st.caption(
        f"rows: loaded={data.total_rows} / filtered={len(filtered)} / "
        f"frieze={data.fair_rows.get('frieze_london', 0)} / liste={data.fair_rows.get('liste', 0)}"
    )
    st.caption(f"data note: {data.count_note}")

    if data.warnings:
        with st.expander("Artist 読み込み警告", expanded=False):
            for warning in data.warnings[:20]:
                st.write(f"- {warning}")

    if not filtered:
        st.warning("該当する作家データがありません。")
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
        "詳細表示",
        options=list(range(len(filtered))),
        format_func=lambda i: _artist_row_label(filtered[i]),
        key="artist_detail_select",
    )
    selected = filtered[selected_idx]

    st.markdown("**作家詳細（read-only）**")
    left, right = st.columns([2, 1])
    left.write(f"Fair: {selected.get('fair_label')}")
    left.write(f"Gallery: {selected.get('gallery_name')}")
    left.write(f"Artist: {selected.get('artist_name')}")
    left.write(f"Year: {selected.get('year')}")
    if selected.get("source_url"):
        left.markdown(f"Source URL: {selected.get('source_url')}")

    summary_ja = (selected.get("summary_ja") or "").strip()
    if summary_ja:
        left.write(f"Summary: {summary_ja[:300]}")

    right.metric("Works image hint", int(selected.get("works_image_count_hint") or 0))
    right.caption("source_url strict-match hint only")

    body = (selected.get("text") or "").strip()
    if body:
        st.text_area("Artist text", value=body[:8000], height=260, disabled=True)
    else:
        st.warning("このレコードは text が空です。")


def render_advisor(selected_fair: str) -> None:
    st.markdown("**④ Advisor（相談）**")
    st.caption("question type 1（テキスト回答）実装済み。type 2（テキスト＋画像生成）は gate/design preview のみ。")

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "フェア選択",
        ["サイドバー選択を使用"] + FAIR_OPTIONS,
        index=0,
        key="advisor_fair_filter",
    )
    question_type_label = col2.selectbox(
        "質問タイプ",
        [
            "type 1 = テキスト回答のみ（今回実装）",
            "type 2 = テキスト＋画像生成（未実装）",
        ],
        index=0,
        key="advisor_question_type",
    )

    question_text = st.text_area(
        "相談内容（制作したい作品の概要や悩み）",
        value="",
        height=140,
        key="advisor_question_text",
        placeholder="例: 2025年のフェア文脈で、素材とスケールの選び方を相談したい。",
    )
    uploaded_image = st.file_uploader(
        "質問画像（任意）",
        type=["png", "jpg", "jpeg", "webp"],
        key="advisor_uploaded_image",
    )
    upload_valid = False
    upload_note = "添付画像なし。"
    if uploaded_image is not None:
        try:
            raw = uploaded_image.getvalue()
            mime = str(getattr(uploaded_image, "type", "") or "")
            if not raw:
                upload_note = "添付画像を読み取れなかったため、画像入力なしとして扱います。"
            elif mime and not mime.startswith("image/"):
                upload_note = "添付ファイルが画像形式ではないため、画像入力なしとして扱います。"
            else:
                upload_valid = True
                upload_note = f"添付画像: {uploaded_image.name}（保存しない / ベクトル化しない / RAG混入しない）"
        except Exception:
            upload_note = "添付画像の読み取りに失敗したため、画像入力なしとして扱います。"

    st.caption(upload_note)

    if question_type_label.startswith("type 2"):
        st.info("type 2 は本実装前です。今回は gate 判定と prompt preview のみ表示します（画像生成APIは未実行）。")

    run = st.button("Advisor を実行", key="advisor_run")
    if run:
        if not question_text.strip():
            st.warning("相談内容を入力してください。")
            return

        effective_fair = selected_fair if fair_mode == "サイドバー選択を使用" else fair_mode
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

            # type2でも、まず grounded type1 を必ず作る（text基盤）。
            draft_type1 = generate_advisor_grounded_draft(
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
            st.error("Advisor 実行中にエラーが発生しました。入力条件を見直して再実行してください。")
            with st.expander("詳細（開発確認用）", expanded=False):
                st.code(f"{type(exc).__name__}: {exc}")
            return

    context = st.session_state.get("advisor_context")
    selection = st.session_state.get("advisor_selection", {})
    draft = st.session_state.get("advisor_draft")
    type2_preview = st.session_state.get("advisor_type2_preview")
    selected_qtype = str(selection.get("question_type_label") or "type 1 = テキスト回答のみ（今回実装）")

    if not context:
        st.caption("相談内容を入力して「Advisor を実行」を押すと、根拠束と回答下書きを表示します。")
        return

    st.markdown("**Advisor grounding overview（read-only）**")
    st.write(
        {
            "fair": context["selection"]["fair_label"],
            "year": context["selection"]["year"],
            "question_type": selected_qtype,
            "token_count": len(context["selection"].get("tokens", [])),
        }
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Exhibitions evidence", context["counts"]["exhibitions_text_evidence_count"])
    m2.metric("Artists evidence", context["counts"]["artist_text_evidence_count"])
    m3.metric("Unique URLs", context["counts"]["all_unique_url_count"])
    m4.metric(
        "Ref images",
        int(context["counts"]["reference_exhibition_images"]) + int(context["counts"]["reference_artist_images"]),
    )
    st.caption(context["count_note"])

    if context.get("warnings"):
        with st.expander("Advisor 読み込み警告", expanded=False):
            for warning in context["warnings"][:20]:
                st.write(f"- {warning}")

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
        st.markdown("**Exhibitions evidence（上位）**")
        st.dataframe(ex_view, use_container_width=True, hide_index=True, height=220)
    with c2:
        st.markdown("**Artists evidence（上位）**")
        st.dataframe(ar_view, use_container_width=True, hide_index=True, height=220)

    ref_images = context.get("reference_images", {})
    st.markdown("**参考画像候補（read-only）**")
    st.write(
        {
            "target_total": 8,
            "target_exhibition_images": ref_images.get("target_exhibition_images", 4),
            "target_artist_images": ref_images.get("target_artist_images", 4),
            "available_total": len(ref_images.get("all", [])),
        }
    )
    if ref_images.get("all"):
        st.dataframe(ref_images.get("all", [])[:8], use_container_width=True, hide_index=True, height=220)

    if selected_qtype.startswith("type 2"):
        st.markdown("**Advisor type 2（gated execution）**")
        if not type2_preview:
            st.caption("type 2 を選んで Advisor を実行すると、gate判定と生成結果を表示します。")
            return

        gate_ok = bool(type2_preview.get("gate_ok"))
        if gate_ok:
            st.success("type 2 gate: PASS")
        else:
            st.error("type 2 gate: HOLD（画像生成APIは未実行）")
            failed = collect_failed_checks(type2_preview)
            if failed:
                st.markdown("**未通過条件**")
                for reason in failed:
                    st.write(f"- {reason}")

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
                "required_env_keys": type2_preview.get("required_env_keys", []),
                "optional_env_keys": type2_preview.get("optional_env_keys", []),
                "resolved_env": type2_preview.get("resolved_env", {}),
                "api_called": bool(type2_preview.get("api_called", False)),
            }
        )

        st.text_area(
            "type 2 prompt preview",
            value=str(type2_preview.get("prompt_preview") or ""),
            height=260,
            disabled=True,
        )
        if type2_preview.get("error"):
            st.warning(f"画像生成結果: {type2_preview.get('error')}")
            debug_err = str(type2_preview.get("debug_error") or "")
            if debug_err:
                with st.expander("生成エラー詳細（開発確認用）", expanded=False):
                    st.code(debug_err)

        st.markdown("**type 2 テキスト回答（500字以内）**")
        st.write(
            {
                "text_chars": type2_preview.get("text_chars"),
                "max_chars": ADVISOR_TEXT_MAX_CHARS,
                "image_source": type2_preview.get("image_source_label", "AI generated"),
                "generated_image_count": type2_preview.get("generated_image_count", 0),
            }
        )
        st.text_area(
            "Advisor回答（日本語）",
            value=str(type2_preview.get("text_answer") or ""),
            height=180,
            disabled=True,
        )
        st.caption(str(type2_preview.get("attachment_note") or ""))

        image_bytes = type2_preview.get("generated_image_bytes")
        image_url = str(type2_preview.get("generated_image_url") or "")
        if image_bytes:
            st.image(image_bytes, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        elif image_url:
            st.image(image_url, caption="AI generated", use_container_width=True)
            st.caption("Source: AI generated")
        else:
            st.info("生成画像はまだありません（gate未通過または生成失敗）。")

        urls = type2_preview.get("evidence_urls", {})
        ex_urls = urls.get("exhibition", [])
        ar_urls = urls.get("artist", [])
        st.markdown("**根拠URL一覧**")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"Exhibition URLs: {len(ex_urls)}")
            for url in ex_urls[:30]:
                st.write(f"- {url}")
        with c2:
            st.write(f"Artist URLs: {len(ar_urls)}")
            for url in ar_urls[:30]:
                st.write(f"- {url}")

        ref_images = type2_preview.get("reference_images", {})
        if isinstance(ref_images, dict):
            st.markdown("**参考画像候補（read-only）**")
            st.write(
                {
                    "target_total": 8,
                    "available_total": len(ref_images.get("all", [])),
                }
            )
            if ref_images.get("all"):
                st.dataframe(ref_images.get("all", [])[:8], use_container_width=True, hide_index=True, height=220)

        if draft:
            st.markdown("**type 2 前提の grounded baseline（type 1）**")
            st.write(
                {
                    "answer_chars": draft.get("answer_chars"),
                    "max_chars": ADVISOR_TEXT_MAX_CHARS,
                    "evidence_count": draft.get("evidence_counts", {}).get("all_unique_urls", 0),
                }
            )
            st.text_area("grounded text baseline", value=draft.get("answer", ""), height=180, disabled=True)
        return

    if not draft:
        return

    st.markdown("**Advisor grounded draft（type 1）**")
    st.write(
        {
            "question_type": draft.get("question_type"),
            "mode": draft.get("mode"),
            "answer_chars": draft.get("answer_chars"),
            "max_chars": ADVISOR_TEXT_MAX_CHARS,
            "evidence_count": draft.get("evidence_counts", {}).get("all_unique_urls", 0),
        }
    )
    st.text_area("Advisor回答（日本語）", value=draft.get("answer", ""), height=200, disabled=True)
    st.caption(draft.get("attachment_note", ""))

    urls = draft.get("evidence_urls", {})
    ex_urls = urls.get("exhibition", [])
    ar_urls = urls.get("artist", [])
    st.markdown("**根拠URL一覧**")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"Exhibition URLs: {len(ex_urls)}")
        for url in ex_urls[:30]:
            st.write(f"- {url}")
    with c2:
        st.write(f"Artist URLs: {len(ar_urls)}")
        for url in ar_urls[:30]:
            st.write(f"- {url}")
    if draft.get("warnings"):
        with st.expander("Advisor generation warnings", expanded=False):
            for warning in draft["warnings"]:
                st.write(f"- {warning}")


def render_exclusive_advisor(selected_fair: str) -> None:
    st.markdown("**⑤ Exclusive Advisor（垂谷専属）**")
    st.caption(
        "type 1（テキスト回答）と type 2（テキスト＋画像生成）を実装。"
        "Tarutani_Textは内部文脈としてのみ利用します。"
    )

    col1, col2 = st.columns([1, 1])
    fair_mode = col1.selectbox(
        "フェア選択",
        ["サイドバー選択を使用"] + FAIR_OPTIONS,
        index=0,
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
        placeholder="例: 曲線と直線のシリーズ文脈を保ちつつ、2025年フェアで通用する展示構成にしたい。",
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
                upload_note = "添付画像を読み取れなかったため、画像入力なしとして扱います。"
            elif mime and not mime.startswith("image/"):
                upload_note = "添付ファイルが画像形式ではないため、画像入力なしとして扱います。"
            else:
                upload_valid = True
                upload_note = f"添付画像: {uploaded_image.name}（保存しない / ベクトル化しない / RAG混入しない）"
        except Exception:
            upload_note = "添付画像の読み取りに失敗したため、画像入力なしとして扱います。"
    st.caption(upload_note)

    run = st.button("Exclusive Advisor を実行", key="exclusive_run")
    if run:
        if not question_text.strip():
            st.warning("相談内容を入力してください。")
            return
        effective_fair = selected_fair if fair_mode == "サイドバー選択を使用" else fair_mode
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

    st.markdown("**Exclusive Advisor grounding overview（read-only）**")
    st.write(
        {
            "fair": context["selection"]["fair_label"],
            "year": context["selection"]["year"],
            "question_type": active_qtype,
            "token_count": len(context["selection"].get("tokens", [])),
        }
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("External Exh evidence", context["external"].get("counts", {}).get("exhibitions_text_evidence_count", 0))
    m2.metric("External Artist evidence", context["external"].get("counts", {}).get("artist_text_evidence_count", 0))
    m3.metric("External URLs", context["external"].get("counts", {}).get("all_unique_url_count", 0))
    m4.metric("Tarutani excerpts", context["tarutani"].get("count", 0))
    st.caption(context["external"].get("count_note", ""))
    st.caption(context["tarutani"].get("count_note", ""))

    if context.get("warnings"):
        with st.expander("Exclusive Advisor 読み込み警告", expanded=False):
            for warning in context["warnings"][:20]:
                st.write(f"- {warning}")

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
        st.markdown("**外部RAG: Exhibitions（上位）**")
        st.dataframe(ex_view, use_container_width=True, hide_index=True, height=220)
    with c2:
        st.markdown("**外部RAG: Artists（上位）**")
        st.dataframe(ar_view, use_container_width=True, hide_index=True, height=220)

    ref_images = context["external"].get("reference_images", {})
    st.markdown("**外部参考画像候補（read-only, 最大8目安）**")
    st.write(
        {
            "target_total": 8,
            "available_total": len(ref_images.get("all", [])),
        }
    )
    if ref_images.get("all"):
        st.dataframe(ref_images.get("all", [])[:8], use_container_width=True, hide_index=True, height=220)

    if active_qtype.startswith("type 2"):
        st.markdown("**Exclusive Advisor type 2（gated execution）**")
        if not type2_result:
            st.caption("type 2 を選んで Exclusive Advisor を実行すると、gate判定と生成結果を表示します。")
            return

        gate_ok = bool(type2_result.get("gate_ok"))
        status = str(type2_result.get("status") or "")
        user_message = str(type2_result.get("user_message") or "")
        if gate_ok:
            st.success("type 2 gate: PASS（条件通過）")
        else:
            st.error("type 2 gate: HOLD（画像生成APIは未実行）")
        if user_message:
            st.caption(user_message)

        st.write(
            {
                "status": status or ("success" if gate_ok else "gate_hold"),
                "required_env_keys": type2_result.get("required_env_keys", []),
                "optional_env_keys": type2_result.get("optional_env_keys", []),
                "api_called": bool(type2_result.get("api_called", False)),
            }
        )
        failed = collect_failed_checks_exclusive_type2(type2_result)
        if failed:
            st.markdown("**未通過条件（要点）**")
            for reason in failed[:8]:
                st.write(f"- {reason}")

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
            st.write({"resolved_env": type2_result.get("resolved_env", {})})
            st.text_area(
                "type 2 prompt preview",
                value=str(type2_result.get("prompt_preview") or ""),
                height=220,
                disabled=True,
            )

        if type2_result.get("error"):
            st.warning(f"画像生成結果: {type2_result.get('error')}")
            debug_err = str(type2_result.get("debug_error") or "")
            if debug_err:
                with st.expander("生成エラー詳細（開発確認用）", expanded=False):
                    st.code(debug_err)

        st.markdown("**Exclusive Advisor回答（日本語、type 2）**")
        st.write(
            {
                "text_chars": type2_result.get("text_chars"),
                "max_chars": EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
                "generated_image_count": type2_result.get("generated_image_count", 0),
                "image_source": type2_result.get("image_source_label", "AI generated"),
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
            st.info("生成画像はまだありません（gate未通過または生成失敗）。")

        urls = type2_result.get("external_evidence_urls", {})
        ex_urls = urls.get("exhibition", [])
        ar_urls = urls.get("artist", [])
        st.markdown("**外部根拠URL一覧**")
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"Exhibition URLs: {len(ex_urls)}")
            for url in ex_urls[:30]:
                st.write(f"- {url}")
        with c2:
            st.write(f"Artist URLs: {len(ar_urls)}")
            for url in ar_urls[:30]:
                st.write(f"- {url}")

        st.markdown("**根拠（Tarutani_Text 抜粋）**")
        tarutani_rows = type2_result.get("tarutani_evidence_excerpts", [])
        t_view = [
            {
                "series_name": r.get("series_name"),
                "source_path": r.get("source_path"),
                "excerpt": r.get("excerpt"),
            }
            for r in tarutani_rows[:8]
        ]
        st.dataframe(t_view, use_container_width=True, hide_index=True, height=220)

        ref_images = type2_result.get("reference_images", {})
        if isinstance(ref_images, dict):
            st.markdown("**外部参考画像候補（read-only, 最大8目安）**")
            st.write(
                {
                    "target_total": 8,
                    "available_total": len(ref_images.get("all", [])),
                }
            )
            if ref_images.get("all"):
                st.dataframe(ref_images.get("all", [])[:8], use_container_width=True, hide_index=True, height=220)
        return

    if not draft:
        return

    st.markdown("**Exclusive Advisor grounded draft（type 1）**")
    st.write(
        {
            "mode": draft.get("mode"),
            "answer_chars": draft.get("answer_chars"),
            "max_chars": EXCLUSIVE_ADVISOR_TEXT_MAX_CHARS,
            "external_url_count": draft.get("counts", {}).get("external_url_count", 0),
            "tarutani_excerpt_count": draft.get("counts", {}).get("tarutani_excerpt_count", 0),
        }
    )
    st.text_area("Exclusive Advisor回答（日本語）", value=draft.get("answer", ""), height=260, disabled=True)
    st.caption(draft.get("attachment_note", ""))

    urls = draft.get("external_evidence_urls", {})
    ex_urls = urls.get("exhibition", [])
    ar_urls = urls.get("artist", [])
    st.markdown("**外部根拠URL一覧**")
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"Exhibition URLs: {len(ex_urls)}")
        for url in ex_urls[:30]:
            st.write(f"- {url}")
    with c2:
        st.write(f"Artist URLs: {len(ar_urls)}")
        for url in ar_urls[:30]:
            st.write(f"- {url}")

    st.markdown("**根拠（Tarutani_Text 抜粋）**")
    tarutani_rows = draft.get("tarutani_evidence_excerpts", [])
    t_view = [
        {
            "series_name": r.get("series_name"),
            "source_path": r.get("source_path"),
            "excerpt": r.get("excerpt"),
        }
        for r in tarutani_rows[:8]
    ]
    st.dataframe(t_view, use_container_width=True, hide_index=True, height=220)

    if draft.get("warnings"):
        with st.expander("Exclusive Advisor generation warnings", expanded=False):
            for warning in draft["warnings"]:
                st.write(f"- {warning}")


def render_gallery_list(selected_fair: str) -> None:
    st.markdown("**⑥ Gallery list（登録ギャラリー一覧 / read-only）**")
    st.caption("CSV正本を読み取り専用で表示します（編集・追加・削除・保存なし）。")

    try:
        data = get_gallery_list_data()
    except Exception as exc:
        st.error(f"Gallery list 読み込みエラー: {type(exc).__name__}: {exc}")
        return

    col1, col2 = st.columns([1, 2])
    fair_mode = col1.selectbox(
        "フェア切替",
        ["サイドバー選択を使用"] + FAIR_OPTIONS,
        index=0,
        key="gallery_list_fair_filter",
    )
    keyword = col2.text_input(
        "ギャラリー名キーワード",
        value="",
        key="gallery_list_keyword",
    )

    effective_fair = selected_fair if fair_mode == "サイドバー選択を使用" else fair_mode
    filtered = apply_gallery_list_filters(data.records, effective_fair, keyword)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("総件数", data.total_rows)
    m2.metric("Frieze", data.fair_rows.get("frieze_london", 0))
    m3.metric("Liste", data.fair_rows.get("liste", 0))
    m4.metric("fallback件数", data.artists_fallback_rows)
    m5.metric("警告件数", len(data.warnings))
    st.write(
        {
            "filtered_rows": len(filtered),
            "artists_url_raw_rows": getattr(data, "artists_raw_rows", 0),
            "artists_url_empty_rows": getattr(data, "artists_empty_rows", 0),
            "warning_summary": getattr(data, "warning_counts", {}),
        }
    )
    st.caption(data.count_note)
    st.caption("列互換: 3列=そのまま / 2列=artists_url は exhibitions_url fallback（表示専用）。")

    if data.warnings:
        with st.expander("Gallery list 読み込み警告", expanded=False):
            for warning in data.warnings[:30]:
                st.write(f"- {warning}")

    if not filtered:
        st.warning("該当するギャラリーがありません。")
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
            "artists_mode": st.column_config.TextColumn("artists_mode", width="small"),
            "exhibitions_link": st.column_config.LinkColumn("Exhibitions link", display_text="open"),
            "artists_link": st.column_config.LinkColumn("Artists link", display_text="open"),
        },
    )


def render_phase2_sections(selected_fair: str) -> None:
    st.subheader("機能骨格（Phase2）")

    with st.container(border=True):
        render_art_pulse(selected_fair)

    with st.container(border=True):
        render_exhibition_search(selected_fair)

    with st.container(border=True):
        render_artist_search(selected_fair)

    with st.container(border=True):
        render_advisor(selected_fair)

    with st.container(border=True):
        render_exclusive_advisor(selected_fair)

    with st.container(border=True):
        render_gallery_list(selected_fair)


def render_legacy_smoke_checks() -> None:
    with st.expander("Legacy Cloud Smoke Checks（既存機能）", expanded=False):
        st.caption("既存の接続確認機能を保持しています。")
        for key in REQUIRED:
            st.write(f"[env] {key} set:", bool(get_key(key)))

        col1, col2, col3 = st.columns(3)

        if col1.button("OpenAI ping"):
            try:
                from openai import OpenAI

                client = OpenAI(api_key=get_key("OPENAI_API_KEY"))
                model = get_key("TEXT_MODEL", "gpt-5-mini")
                result = client.responses.create(model=model, input="ping")
                st.success(f"OpenAI OK: {result.output_text}")
            except Exception as exc:
                st.error(f"OpenAI ERROR: {type(exc).__name__}: {exc}")

        if col2.button("Gemini embedding"):
            try:
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=get_key("GEMINI_API_KEY"))
                model = get_key("TEXT_EMBEDDING_MODEL", "gemini-embedding-001")
                dim_raw = get_key("TEXT_EMBEDDING_OUTPUT_DIM", 1536)
                dim = int(dim_raw)
                result = client.models.embed_content(
                    model=model,
                    contents="ping",
                    config=types.EmbedContentConfig(output_dimensionality=dim),
                )
                emb = result.embeddings[0].values
                st.success(f"Gemini OK: embedding_len={len(emb)}")
            except Exception as exc:
                st.error(f"Gemini ERROR: {type(exc).__name__}: {exc}")

        if col3.button("R2 upload/list/download"):
            try:
                import boto3

                bucket = get_key("R2_BUCKET")
                endpoint = get_key("R2_ENDPOINT")
                access_key = get_key("R2_ACCESS_KEY_ID")
                secret_key = get_key("R2_SECRET_ACCESS_KEY")
                region = get_key("R2_REGION", "auto")

                s3 = boto3.client(
                    "s3",
                    endpoint_url=endpoint,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region,
                )

                ts = int(time.time())
                key = f"smoke_test_cloud/{ts}.txt"
                body = f"hello r2 cloud {ts}".encode("utf-8")
                s3.put_object(Bucket=bucket, Key=key, Body=body)
                st.write("upload: OK", key)

                resp = s3.list_objects_v2(Bucket=bucket, Prefix="smoke_test_cloud/")
                keys = [x["Key"] for x in resp.get("Contents", [])]
                st.write("list (last 10):", keys[-10:])

                obj = s3.get_object(Bucket=bucket, Key=key)
                data = obj["Body"].read().decode("utf-8")
                st.success(f"download OK: {data}")
            except Exception as exc:
                st.error(f"R2 ERROR: {type(exc).__name__}: {exc}")


def main() -> None:
    selected_fair = render_sidebar()
    render_header(selected_fair)
    render_count_summary(selected_fair)
    st.divider()
    render_phase2_sections(selected_fair)
    st.divider()
    render_legacy_smoke_checks()


if __name__ == "__main__":
    main()
