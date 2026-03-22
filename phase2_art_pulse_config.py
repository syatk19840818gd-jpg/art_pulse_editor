from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
TARGET_YEAR = 2025
PERSONA_COUNT = 8
ART_PULSE_TEXT_MIN_CHARS = 1800
ART_PULSE_TEXT_MAX_CHARS = 2000
ART_PULSE_THUMB_FROM_EXHIB = 4
ART_PULSE_THUMB_FROM_ARTIST = 4
MAX_EVIDENCE_URLS = 8
MIN_IMAGE_PER_NONEMPTY_SECTION = 1
MAX_IMAGE_TOTAL = ART_PULSE_THUMB_FROM_EXHIB + ART_PULSE_THUMB_FROM_ARTIST
ART_PULSE_TEXT_SOFT_OVER_CHARS = 200
ART_PULSE_TARGET_CHARS = (ART_PULSE_TEXT_MIN_CHARS + ART_PULSE_TEXT_MAX_CHARS) // 2
ART_PULSE_TARGET_TOLERANCE = (ART_PULSE_TEXT_MAX_CHARS - ART_PULSE_TEXT_MIN_CHARS) // 2
ART_PULSE_EXPAND_TRIGGER_CHARS = 1700
ART_PULSE_PAYLOAD_CANDIDATE_CAP = 18
ART_PULSE_PROMPT_EXHIBITION_ROWS = 12
ART_PULSE_PROMPT_ARTIST_ROWS = 12
ART_PULSE_PROMPT_SNIPPET_CHARS = 72
ART_PULSE_MAX_OUTPUT_TOKENS = 3600
ART_PULSE_SECTION1_MIN_CHARS = 450
ART_PULSE_SECTION2_MIN_CHARS = 600
ART_PULSE_SECTION3_MIN_CHARS = 600

DATA_ROOT = Path("data")
PHASE1_SEED10_ROOT = DATA_ROOT / "phase1_seed10"
PHASE1_SEED10_DERIVED_DIR = PHASE1_SEED10_ROOT / "derived"
PHASE1_SEED10_DERIVED_R2_PREFIX = "phase1_seed10/derived"
IMAGE_CACHE_DIR = DATA_ROOT / "current" / "images" / "cache"
IMAGE_CACHE_R2_PREFIX = "data/current/images/cache"
CURRENT_RAW_DIR = DATA_ROOT / "current" / "raw"
CURRENT_RAW_R2_PREFIX = "data/current/raw"
CURRENT_IMAGES_METADATA_DIR = DATA_ROOT / "current" / "images" / "metadata"
CURRENT_IMAGES_METADATA_R2_PREFIX = "data/current/images/metadata"
SUPPORTED_FAIR_SLUGS = ("frieze_london", "liste")
ENRICHMENT_CURRENT_DIR = DATA_ROOT / "current" / "enrichment"
ENRICHMENT_HISTORY_DIR = DATA_ROOT / "history" / "enrichment"
ENRICHMENT_HISTORY_ARTISTS_DIR = ENRICHMENT_HISTORY_DIR / "artists"
ENRICHMENT_HISTORY_EXHIBITIONS_DIR = ENRICHMENT_HISTORY_DIR / "exhibitions"
ENRICHMENT_RUNTIME_REQUESTS_DIR = DATA_ROOT / "runtime" / "enrichment_requests"
ENRICHMENT_RUNTIME_REQUESTS_REPORTS_DIR = ENRICHMENT_RUNTIME_REQUESTS_DIR / "_reports"


def get_phase1_seed10_derived_dir(root: Path | None = None) -> Path:
    if root is None:
        return PHASE1_SEED10_DERIVED_DIR
    return Path(root) / "derived"


def get_image_cache_dir(root: Path | None = None) -> Path:
    if root is None:
        return IMAGE_CACHE_DIR
    return Path(root) / "images" / "cache"


def get_artist_image_cache_dir(root: Path | None = None) -> Path:
    return get_image_cache_dir(root) / "artist_works_images"


def get_exhibition_image_cache_dir(root: Path | None = None) -> Path:
    return get_image_cache_dir(root) / "exhibition_works_images"


def get_current_images_metadata_dir(root: Path | None = None) -> Path:
    if root is None:
        return CURRENT_IMAGES_METADATA_DIR
    return Path(root) / "images" / "metadata"


def get_current_artist_image_meta_path(fair_slug: str, *, root: Path | None = None) -> Path:
    _validate_supported_fair_slug(fair_slug)
    return get_current_images_metadata_dir(root) / f"artist_works_images_{fair_slug}.jsonl"


def get_current_artist_image_meta_paths(*, root: Path | None = None) -> dict[str, Path]:
    return {fair_slug: get_current_artist_image_meta_path(fair_slug, root=root) for fair_slug in SUPPORTED_FAIR_SLUGS}


def get_current_exhibitions_image_meta_path(
    fair_slug: str,
    target_year: int = TARGET_YEAR,
    *,
    root: Path | None = None,
) -> Path:
    _validate_supported_fair_slug(fair_slug)
    return get_current_images_metadata_dir(root) / f"exhibitions_images_{fair_slug}_{target_year}.jsonl"


def get_current_exhibitions_image_meta_paths(
    target_year: int = TARGET_YEAR,
    *,
    root: Path | None = None,
) -> dict[str, Path]:
    return {
        fair_slug: get_current_exhibitions_image_meta_path(
            fair_slug,
            target_year,
            root=root,
        )
        for fair_slug in SUPPORTED_FAIR_SLUGS
    }


def resolve_image_local_path(path_text: str | Path, *, repo_root: Path = REPO_ROOT) -> Path | None:
    raw = str(path_text or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return (Path(repo_root) / path).resolve()


def normalize_image_local_path_text(
    path_text: str | Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> str:
    path = resolve_image_local_path(path_text, repo_root=repo_root)
    return str(path) if path is not None else ""


def get_image_cache_rel_path(
    path_text: str | Path,
    *,
    images_root: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> str:
    path = resolve_image_local_path(path_text, repo_root=repo_root)
    if path is None:
        return ""
    cache_root = _resolve_repo_path(images_root or IMAGE_CACHE_DIR, repo_root=repo_root)
    try:
        rel = path.resolve().relative_to(cache_root.resolve())
    except Exception:
        return ""
    return rel.as_posix()


def get_image_r2_key(
    path_text: str | Path,
    *,
    images_root: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> str:
    rel = get_image_cache_rel_path(
        path_text,
        images_root=images_root,
        repo_root=repo_root,
    )
    if not rel:
        return ""
    return f"{IMAGE_CACHE_R2_PREFIX}/{rel}"


def get_current_raw_dir(root: Path | None = None) -> Path:
    if root is None:
        return CURRENT_RAW_DIR
    return Path(root) / "raw"


def get_current_raw_path(
    category: str,
    fair_slug: str,
    target_year: int = TARGET_YEAR,
    *,
    root: Path | None = None,
) -> Path:
    _validate_enrichment_category(category)
    _validate_supported_fair_slug(fair_slug)
    return get_current_raw_dir(root) / f"{category}_{fair_slug}_{target_year}.jsonl"


def get_current_raw_paths(
    category: str,
    target_year: int = TARGET_YEAR,
    *,
    root: Path | None = None,
) -> dict[str, Path]:
    _validate_enrichment_category(category)
    return {
        fair_slug: get_current_raw_path(
            category,
            fair_slug,
            target_year,
            root=root,
        )
        for fair_slug in SUPPORTED_FAIR_SLUGS
    }


def get_enrichment_current_output_path(category: str, target_year: int = TARGET_YEAR) -> Path:
    _validate_enrichment_category(category)
    return ENRICHMENT_CURRENT_DIR / f"{category}_enrichment_apply_output_{target_year}.jsonl"


def get_enrichment_current_summary_path(category: str, target_year: int = TARGET_YEAR) -> Path:
    _validate_enrichment_category(category)
    return ENRICHMENT_CURRENT_DIR / f"{category}_enrichment_apply_summary_{target_year}.json"


def get_enrichment_history_output_path(category: str, stamp: str, target_year: int = TARGET_YEAR) -> Path:
    _validate_enrichment_category(category)
    return get_enrichment_history_dir(category) / f"{category}_enrichment_apply_output_{target_year}_{stamp}.jsonl"


def get_enrichment_history_summary_path(category: str, stamp: str, target_year: int = TARGET_YEAR) -> Path:
    _validate_enrichment_category(category)
    return get_enrichment_history_dir(category) / f"{category}_enrichment_apply_summary_{target_year}_{stamp}.json"


def get_enrichment_history_dir(category: str) -> Path:
    _validate_enrichment_category(category)
    if category == "artists":
        return ENRICHMENT_HISTORY_ARTISTS_DIR
    return ENRICHMENT_HISTORY_EXHIBITIONS_DIR


def get_enrichment_runtime_requests_dir(category: str) -> Path:
    _validate_enrichment_category(category)
    return ENRICHMENT_RUNTIME_REQUESTS_DIR / category


def get_enrichment_runtime_requests_path(category: str, target_year: int = TARGET_YEAR) -> Path:
    _validate_enrichment_category(category)
    return get_enrichment_runtime_requests_dir(category) / f"{category}_enrichment_requests_{target_year}.jsonl"


def get_enrichment_runtime_requests_completed_dir(category: str) -> Path:
    _validate_enrichment_category(category)
    return get_enrichment_runtime_requests_dir(category) / "_completed"


def get_enrichment_runtime_requests_reports_dir() -> Path:
    return ENRICHMENT_RUNTIME_REQUESTS_REPORTS_DIR


def get_enrichment_seed10_legacy_requests_path(category: str, target_year: int = TARGET_YEAR) -> Path:
    _validate_enrichment_category(category)
    return DATA_ROOT / "phase1_seed10" / "derived" / f"{category}_enrichment_requests_{target_year}.jsonl"


def get_enrichment_scaffold_dirs() -> tuple[Path, ...]:
    return (
        ENRICHMENT_CURRENT_DIR,
        ENRICHMENT_HISTORY_ARTISTS_DIR,
        ENRICHMENT_HISTORY_EXHIBITIONS_DIR,
        get_enrichment_runtime_requests_dir("artists"),
        get_enrichment_runtime_requests_dir("exhibitions"),
        ENRICHMENT_RUNTIME_REQUESTS_REPORTS_DIR,
    )


def promote_history_file_to_current(history_path: Path, current_path: Path) -> None:
    if not history_path.exists():
        raise FileNotFoundError(f"Missing history artifact for promotion: {history_path}")
    current_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = current_path.with_name(f"{current_path.name}.tmp")
    try:
        shutil.copyfile(history_path, tmp_path)
        os.replace(tmp_path, current_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _validate_enrichment_category(category: str) -> None:
    if category not in {"artists", "exhibitions"}:
        raise ValueError(f"Unsupported enrichment category: {category}")


def _validate_supported_fair_slug(fair_slug: str) -> None:
    if fair_slug not in SUPPORTED_FAIR_SLUGS:
        raise ValueError(f"Unsupported fair slug: {fair_slug}")


def _resolve_repo_path(path: Path | str, *, repo_root: Path = REPO_ROOT) -> Path:
    resolved = Path(path)
    if resolved.is_absolute():
        return resolved
    return (Path(repo_root) / resolved).resolve()

PERSONAS = [
    {
        "id": "reporter_01",
        "name_en": "Alex",
        "name_ja": "アレックス",
        "label": "Alex（アレックス）",
        "description": "辛口の批評家",
        "style": "鋭い視点でトレンドを斬る。安易な共感を拒絶し、構造的な欠陥や欺瞞を指摘。",
        "tone": "理知的、批判的、断定的、シニカル（『素晴らしい』等の単純な賛辞は使わない）",
        "angles": [
            {
                "key": "alex_politics_social_message",
                "label": "政治性や社会メッセージ",
                "description": "表層で終わっていないか厳しく評価する。",
            },
            {
                "key": "alex_market_anti_thesis",
                "label": "アートマーケットや商業主義へのアンチテーゼ",
                "description": "作品の市場文脈と批評性の緊張を読み解く。",
            },
            {
                "key": "alex_curation_intent",
                "label": "キュレーション（展示構成）の意図",
                "description": "展覧会としての強度を問う。",
            },
        ],
    },
    {
        "id": "reporter_02",
        "name_en": "Sophia",
        "name_ja": "ソフィア",
        "label": "Sophia（ソフィア）",
        "description": "情熱的ライター",
        "style": "作品世界に没入し、鑑賞体験の熱量を物語として描く。読者の感情を動かす描写を優先する。",
        "tone": "情熱的、感覚的、詩的、一人称的（『私』の体験として語る）",
        "angles": [
            {
                "key": "sophia_energy_emotion",
                "label": "作品から感じるエネルギーや感情",
                "description": "理屈より先に心が震えた瞬間を描写する。",
            },
            {
                "key": "sophia_artist_story",
                "label": "アーティスト本人の背景や個人的な物語",
                "description": "制作と人生の接点を掘る。",
            },
            {
                "key": "sophia_process",
                "label": "独特な制作プロセス",
                "description": "背景や意図を丁寧に掘る。",
            },
        ],
    },
    {
        "id": "reporter_03",
        "name_en": "Marcus",
        "name_ja": "マーカス",
        "label": "Marcus（マーカス）",
        "description": "美術史家",
        "style": "美術史の重厚な文脈から現在を位置づける。一過性の流行を排し、歴史的必然性を問う。",
        "tone": "冷静、アカデミック、重厚、教育的（俗語や流行語は使用しない）",
        "angles": [
            {
                "key": "marcus_quote_reinterpret",
                "label": "美術史上の引用と再解釈",
                "description": "歴史を引用し、現代的に更新されているか論じる。",
            },
            {
                "key": "marcus_traditional_technique",
                "label": "伝統的な技法の現代的転用",
                "description": "温故知新の視点で作品を評価する。",
            },
            {
                "key": "marcus_contemporaneity",
                "label": "同時代性",
                "description": "なぜ今この作品・テーマなのかを社会応答として検証する。",
            },
        ],
    },
    {
        "id": "reporter_04",
        "name_en": "Kai",
        "name_ja": "カイ",
        "label": "Kai（カイ）",
        "description": "自然と科学の観測者",
        "style": "アートを生態系の一部として捉える。環境負荷や倫理、科学的整合性を重視する。",
        "tone": "有機的、警鐘的、サステナブル、倫理的（素材の廃棄やエネルギー効率にも言及）",
        "angles": [
            {
                "key": "kai_multispecies",
                "label": "多種共生",
                "description": "人間中心主義を離れ、動植物・菌類・AIとの共存観点で評価する。",
            },
            {
                "key": "kai_future_insight",
                "label": "未来の洞察",
                "description": "バイオ技術や科学進化が示す未来像を考察する。",
            },
            {
                "key": "kai_invisible_visible",
                "label": "不可視の可視化",
                "description": "気候・音・物理法則など不可視現象の美的翻訳を評価する。",
            },
        ],
    },
    {
        "id": "reporter_05",
        "name_en": "Zoe",
        "name_ja": "ゾーイ",
        "label": "Zoe（ゾーイ）",
        "description": "デジタル・カルチャー記者",
        "style": "アテンション・エコノミーを前提に、拡散力と文脈消費の速度を解体する。",
        "tone": "現代的、フラット、スピーディー、ミレニアル/Z世代的（ネットスラングを適度に許容）",
        "angles": [
            {
                "key": "zoe_sns_visual_power",
                "label": "SNS時代の視覚的強度",
                "description": "画像拡散・見栄え・ミーム性の観点から考察する。",
            },
            {
                "key": "zoe_post_internet",
                "label": "ポストインターネットの感性",
                "description": "現実と仮想の境界が溶け合う表現や美学を拾う。",
            },
            {
                "key": "zoe_high_low_boundary",
                "label": "ハイ＆ローの境界",
                "description": "サブカルチャーと現代アートの接続を読む。",
            },
        ],
    },
    {
        "id": "reporter_06",
        "name_en": "Leo",
        "name_ja": "レオ",
        "label": "Leo（レオ）",
        "description": "アート・ストラテジスト",
        "style": "作品を資産クラスとして評価し、プライマリー/セカンダリー市場の力学で語る。",
        "tone": "実利的、戦略的、ビジネスライク、自信に満ちた（『買い』か『売り』かを意識）",
        "angles": [
            {
                "key": "leo_asset_value",
                "label": "資産価値と将来性",
                "description": "資産価値やコレクション魅力を分析する。",
            },
            {
                "key": "leo_self_branding",
                "label": "セルフブランディング",
                "description": "セルフプロデュースの巧みさを評価する。",
            },
            {
                "key": "leo_collector_desire",
                "label": "コレクターの所有欲",
                "description": "サイズ・保存性・ステータス性など購買者視点で語る。",
            },
        ],
    },
    {
        "id": "reporter_07",
        "name_en": "Ren",
        "name_ja": "レン",
        "label": "Ren（レン）",
        "description": "マテリアルの職人",
        "style": "作り手視点で物理的完成度と制作の狂気を執拗に追う。デジタル作品のレンダリング品質も対象。",
        "tone": "職人気質、実直、触覚的、マニアック（質感・解像度・収縮率などの語彙を好む）",
        "angles": [
            {
                "key": "ren_handcraft_trace",
                "label": "圧倒的な手仕事の痕跡",
                "description": "時間密度と執念をレポートする。",
            },
            {
                "key": "ren_material_fetish",
                "label": "素材へのフェティシズム",
                "description": "テクスチャーや素材特性の活かし方を掘る。",
            },
            {
                "key": "ren_durability_finish",
                "label": "耐久性と完成度",
                "description": "保存強度・細部仕上げ・工芸的完成度を問う。",
            },
        ],
    },
    {
        "id": "reporter_08",
        "name_en": "Nadia",
        "name_ja": "ナディア",
        "label": "Nadia（ナディア）",
        "description": "文化人類学者",
        "style": "アートを土地やコミュニティの文化現象として観察し、展示室から社会へ解釈を広げる。",
        "tone": "観察的、包摂的、グローバル、物語るような（フィールドワークノート風）",
        "angles": [
            {
                "key": "nadia_local_climate",
                "label": "ローカルと風土",
                "description": "土地特有の歴史・信仰・生活習慣の反映を掘る。",
            },
            {
                "key": "nadia_minority_diversity",
                "label": "マイノリティと多様性",
                "description": "ジェンダー・人種・社会的弱者の可視化を論じる。",
            },
            {
                "key": "nadia_exhibition_as_ritual",
                "label": "現代の儀式としての展覧会",
                "description": "鑑賞者の振る舞いと社会的機能を分析する。",
            },
        ],
    },
]

ANGLES = [
    {**angle, "persona_id": persona["id"], "persona_label": persona["label"]}
    for persona in PERSONAS
    for angle in persona["angles"]
]

if len(PERSONAS) != PERSONA_COUNT:
    raise ValueError(f"PERSONA_COUNT mismatch: expected={PERSONA_COUNT}, actual={len(PERSONAS)}")


ART_PULSE_ANGLE_QUERY_TERMS = {
    "alex_politics_social_message": [
        # ja (12)
        "政治",
        "社会",
        "制度",
        "権力",
        "批評",
        "社会運動",
        "抗議",
        "抵抗",
        "監視",
        "統治",
        "格差",
        "人権",
        # en (18)
        "political",
        "social",
        "institutional critique",
        "power structure",
        "activism",
        "protest",
        "resistance",
        "surveillance",
        "governance",
        "inequality",
        "human rights",
        "social justice",
        "identity politics",
        "postcolonial",
        "decolonial",
        "censorship",
        "public sphere",
        "collective action",
    ],

    "alex_market_anti_thesis": [
        # ja (12)
        "市場",
        "商業",
        "コレクター",
        "価格",
        "資本",
        "投機",
        "商品化",
        "オークション",
        "ブランド",
        "消費",
        "価値付け",
        "収集",
        # en (18)
        "market",
        "commercial",
        "collector",
        "price",
        "capital",
        "speculation",
        "commodification",
        "auction",
        "branding",
        "consumption",
        "valuation",
        "acquisition",
        "art fair economy",
        "market critique",
        "blue-chip",
        "resale",
        "financialization",
        "luxury",
    ],

    "alex_curation_intent": [
        # ja (12)
        "キュレーション",
        "展示構成",
        "空間",
        "導線",
        "配置",
        "インスタレーション",
        "文脈",
        "順序",
        "対比",
        "照明",
        "スケール",
        "会場設計",
        # en (18)
        "curation",
        "installation",
        "display",
        "layout",
        "spatial narrative",
        "sequencing",
        "juxtaposition",
        "exhibition design",
        "circulation",
        "site-responsive",
        "framing",
        "scenography",
        "wall text",
        "rhythm",
        "viewer journey",
        "atmosphere",
        "curatorial thesis",
        "staging",
    ],

    "sophia_energy_emotion": [
        # ja (12)
        "エネルギー",
        "感情",
        "情熱",
        "解放",
        "衝動",
        "熱量",
        "高揚",
        "緊張",
        "不安",
        "陶酔",
        "痛み",
        "癒やし",
        # en (18)
        "energy",
        "emotion",
        "passion",
        "intensity",
        "release",
        "urgency",
        "tension",
        "ecstasy",
        "vulnerability",
        "catharsis",
        "tenderness",
        "longing",
        "emotional charge",
        "mood",
        "atmosphere",
        "sensation",
        "visceral",
        "resonance",
    ],

    "sophia_artist_story": [
        # ja (12)
        "背景",
        "物語",
        "人生",
        "個人的",
        "記憶",
        "家族",
        "出自",
        "移動",
        "喪失",
        "回復",
        "日記性",
        "自伝性",
        # en (18)
        "story",
        "biography",
        "narrative",
        "personal",
        "memory",
        "family history",
        "origin",
        "migration",
        "loss",
        "healing",
        "intimacy",
        "autobiography",
        "lived experience",
        "testimony",
        "confession",
        "identity",
        "turning point",
        "inner life",
    ],

    "sophia_process": [
        # ja (12)
        "制作プロセス",
        "手法",
        "工程",
        "素材",
        "反復",
        "実験",
        "即興",
        "手仕事",
        "痕跡",
        "変形",
        "乾燥",
        "焼成",
        # en (18)
        "process",
        "method",
        "material",
        "technique",
        "iteration",
        "experimentation",
        "improvisation",
        "making-of",
        "labor",
        "transformation",
        "trial and error",
        "studio practice",
        "layering",
        "casting",
        "weaving",
        "welding",
        "residue",
        "gesture",
    ],

    "marcus_quote_reinterpret": [
        # ja (12)
        "引用",
        "再解釈",
        "参照",
        "歴史",
        "受容",
        "反復",
        "翻案",
        "パロディ",
        "オマージュ",
        "系譜",
        "典拠",
        "図像学",
        # en (18)
        "quotation",
        "reinterpretation",
        "reference",
        "history",
        "appropriation",
        "adaptation",
        "parody",
        "homage",
        "genealogy",
        "iconography",
        "citation",
        "canon",
        "art-historical lineage",
        "modernism",
        "afterimage",
        "revision",
        "dialog with tradition",
        "historiography",
    ],

    "marcus_traditional_technique": [
        # ja (12)
        "伝統",
        "技法",
        "古典",
        "継承",
        "工芸",
        "筆致",
        "染織",
        "陶芸",
        "鋳造",
        "木工",
        "漆",
        "手業",
        # en (18)
        "traditional",
        "craft",
        "technique",
        "classical",
        "inheritance",
        "workmanship",
        "brushwork",
        "textile",
        "ceramics",
        "casting",
        "woodworking",
        "lacquer",
        "artisanal",
        "medium specificity",
        "restoration",
        "manual skill",
        "discipline",
        "old master",
    ],

    "marcus_contemporaneity": [
        # ja (12)
        "同時代",
        "現代性",
        "今",
        "社会応答",
        "更新",
        "危機",
        "現在地",
        "時代精神",
        "変容",
        "接続",
        "切迫感",
        "応答性",
        # en (18)
        "contemporary",
        "current",
        "present",
        "contemporaneity",
        "social response",
        "timeliness",
        "relevance",
        "urgency",
        "crisis",
        "present tense",
        "historical moment",
        "adaptation",
        "update",
        "global condition",
        "political present",
        "responsiveness",
        "now-ness",
        "societal reflection",
    ],

    "kai_multispecies": [
        # ja (12)
        "共生",
        "生態系",
        "動植物",
        "菌",
        "非人間",
        "相互依存",
        "生息地",
        "種間関係",
        "循環",
        "腐植",
        "発酵",
        "生物多様性",
        # en (18)
        "multispecies",
        "ecology",
        "ecosystem",
        "nonhuman",
        "interdependence",
        "habitat",
        "biodiversity",
        "mycelium",
        "fermentation",
        "symbiosis",
        "more-than-human",
        "species entanglement",
        "coexistence",
        "food web",
        "kinship",
        "regenerative",
        "wetland",
        "pollination",
    ],

    "kai_future_insight": [
        # ja (12)
        "未来",
        "科学",
        "バイオ",
        "技術",
        "予測",
        "進化",
        "実験室",
        "合成",
        "遺伝子",
        "センサー",
        "宇宙",
        "倫理",
        # en (18)
        "future",
        "science",
        "bio",
        "technology",
        "foresight",
        "evolution",
        "laboratory",
        "synthetic",
        "genetics",
        "sensor",
        "speculative design",
        "biotech",
        "planetary",
        "data-driven",
        "future scenario",
        "innovation",
        "ethics",
        "posthuman",
    ],

    "kai_invisible_visible": [
        # ja (12)
        "不可視",
        "可視化",
        "気候",
        "物理",
        "音",
        "温度",
        "圧力",
        "放射",
        "振動",
        "微粒子",
        "気流",
        "データ",
        # en (18)
        "invisible",
        "visualize",
        "climate",
        "physics",
        "sound",
        "temperature",
        "pressure",
        "radiation",
        "vibration",
        "particles",
        "airflow",
        "data",
        "atmospheric",
        "signal",
        "field",
        "wave",
        "hidden system",
        "translation",
    ],

    "zoe_sns_visual_power": [
        # ja (12)
        "SNS",
        "拡散",
        "ミーム",
        "見栄え",
        "バズ",
        "サムネ映え",
        "スクロール",
        "一瞥性",
        "共有",
        "反応",
        "中毒性",
        "切り抜き",
        # en (18)
        "viral",
        "meme",
        "instagram",
        "visual power",
        "shareable",
        "scroll-stopping",
        "thumbnail-friendly",
        "attention economy",
        "engagement",
        "clickability",
        "screenshotable",
        "platform-native",
        "feed aesthetic",
        "loop",
        "trend",
        "algorithm",
        "short-form",
        "image-first",
    ],

    "zoe_post_internet": [
        # ja (12)
        "ポストインターネット",
        "仮想",
        "現実",
        "ネット",
        "ハイブリッド",
        "画面",
        "アバター",
        "配信",
        "バグ",
        "シミュレーション",
        "メタデータ",
        "低解像度",
        # en (18)
        "post-internet",
        "virtual",
        "online",
        "hybrid",
        "screen culture",
        "avatar",
        "livestream",
        "glitch",
        "simulation",
        "metadata",
        "interface",
        "browser",
        "networked",
        "remix",
        "copy-paste",
        "low-res",
        "digital residue",
        "URL aesthetics",
    ],

    "zoe_high_low_boundary": [
        # ja (12)
        "ハイ＆ロー",
        "サブカル",
        "境界",
        "越境",
        "ポップ",
        "ファンダム",
        "ストリート",
        "ゲーム",
        "アニメ",
        "ファッション",
        "広告",
        "消費文化",
        # en (18)
        "high and low",
        "subculture",
        "boundary",
        "crossover",
        "pop culture",
        "fandom",
        "street culture",
        "gaming",
        "anime",
        "fashion",
        "advertising",
        "consumer culture",
        "kitsch",
        "camp",
        "vernacular",
        "mass culture",
        "design language",
        "collectible culture",
    ],

    "leo_asset_value": [
        # ja (12)
        "資産価値",
        "将来性",
        "投資",
        "価格",
        "流動性",
        "需給",
        "実績",
        "市場性",
        "希少性",
        "上昇余地",
        "指標",
        "収益性",
        # en (18)
        "asset",
        "value",
        "investment",
        "price",
        "liquidity",
        "supply-demand",
        "track record",
        "marketability",
        "scarcity",
        "upside",
        "benchmark",
        "return potential",
        "blue-chip",
        "primary market",
        "secondary market",
        "price discovery",
        "comparable sales",
        "appreciation",
    ],

    "leo_self_branding": [
        # ja (12)
        "セルフブランディング",
        "ブランド",
        "発信",
        "戦略",
        "ポジショニング",
        "露出",
        "一貫性",
        "物語化",
        "発言力",
        "可視性",
        "シグネチャー",
        "認知",
        # en (18)
        "branding",
        "positioning",
        "profile",
        "strategy",
        "visibility",
        "narrative control",
        "signature style",
        "consistency",
        "audience building",
        "reputation",
        "media presence",
        "market positioning",
        "self-presentation",
        "recognizability",
        "network effect",
        "press-ready",
        "identity design",
        "platform presence",
    ],

    "leo_collector_desire": [
        # ja (12)
        "所有欲",
        "コレクター",
        "保存性",
        "需要",
        "サイズ感",
        "希少",
        "ステータス",
        "飾りやすさ",
        "エディション",
        "物質感",
        "収蔵適性",
        "贈与性",
        # en (18)
        "collector",
        "demand",
        "collectible",
        "acquisition",
        "desirability",
        "scarcity",
        "status",
        "displayability",
        "edition",
        "material presence",
        "condition",
        "provenance",
        "trophy work",
        "portable",
        "interior-friendly",
        "giftable",
        "resale appeal",
        "institutional appeal",
    ],

    "ren_handcraft_trace": [
        # ja (12)
        "手仕事",
        "痕跡",
        "執念",
        "密度",
        "刻み",
        "縫い目",
        "削り",
        "積層",
        "継ぎ目",
        "筆圧",
        "摩耗",
        "労働",
        # en (18)
        "handmade",
        "handcraft",
        "trace",
        "labor",
        "obsession",
        "density",
        "seam",
        "carving",
        "layering",
        "joinery",
        "brush pressure",
        "wear",
        "residue",
        "manual process",
        "touch",
        "effort",
        "obsessive detail",
        "maker's hand",
    ],

    "ren_material_fetish": [
        # ja (12)
        "素材",
        "質感",
        "テクスチャー",
        "物性",
        "表面",
        "硬度",
        "光沢",
        "透明感",
        "粘度",
        "反射",
        "重み",
        "触感",
        # en (18)
        "material",
        "texture",
        "surface",
        "tactile",
        "finish",
        "hardness",
        "gloss",
        "translucency",
        "viscosity",
        "reflection",
        "weight",
        "grain",
        "fiber",
        "patina",
        "sheen",
        "haptic",
        "material behavior",
        "sensory detail",
    ],

    "ren_durability_finish": [
        # ja (12)
        "耐久性",
        "完成度",
        "仕上げ",
        "保存",
        "精度",
        "接合",
        "研磨",
        "防汚",
        "安定性",
        "耐候性",
        "修復性",
        "長期性",
        # en (18)
        "durability",
        "finish",
        "craftsmanship",
        "preservation",
        "precision",
        "join integrity",
        "polishing",
        "stability",
        "weather resistance",
        "longevity",
        "archival quality",
        "restoration",
        "structural soundness",
        "museum-grade",
        "flawless execution",
        "condition",
        "maintenance",
        "permanence",
    ],

    "nadia_local_climate": [
        # ja (12)
        "風土",
        "ローカル",
        "土地",
        "地域史",
        "信仰",
        "習俗",
        "記憶",
        "景観",
        "方言",
        "地場産業",
        "土着性",
        "場所性",
        # en (18)
        "local",
        "regional",
        "climate",
        "site-specific",
        "vernacular",
        "local history",
        "belief system",
        "landscape",
        "memory of place",
        "custom",
        "rootedness",
        "indigenous context",
        "situated knowledge",
        "neighborhood",
        "everyday life",
        "geography",
        "place-based",
        "community memory",
    ],

    "nadia_minority_diversity": [
        # ja (12)
        "多様性",
        "マイノリティ",
        "ジェンダー",
        "可視化",
        "人種",
        "障害",
        "クィア",
        "包摂",
        "交差性",
        "代表性",
        "周縁",
        "当事者性",
        # en (18)
        "diversity",
        "minority",
        "gender",
        "inclusion",
        "race",
        "disability",
        "queer",
        "intersectionality",
        "representation",
        "marginality",
        "visibility",
        "lived reality",
        "care",
        "social justice",
        "decolonial",
        "anti-bias",
        "plural voices",
        "belonging",
    ],

    "nadia_exhibition_as_ritual": [
        # ja (12)
        "儀式",
        "共同体",
        "振る舞い",
        "社会機能",
        "参加",
        "観客",
        "集合",
        "祝祭",
        "規範",
        "身体動作",
        "巡礼",
        "共有体験",
        # en (18)
        "ritual",
        "community",
        "participation",
        "social function",
        "spectatorship",
        "gathering",
        "ceremony",
        "festival",
        "norm",
        "embodied behavior",
        "pilgrimage",
        "shared experience",
        "collective memory",
        "public gathering",
        "social choreography",
        "etiquette",
        "encounter",
        "belonging",
    ],
}


def get_angle_query_terms(angle_key: str, angle_label: str = "", angle_description: str = "") -> list[str]:
    base = list(ART_PULSE_ANGLE_QUERY_TERMS.get(angle_key, []))
    if angle_label:
        base.append(angle_label)
    if angle_description:
        base.append(angle_description)

    out: list[str] = []
    seen = set()
    for term in base:
        t = str(term or "").strip()
        if len(t) < 2:
            continue
        key = t.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def find_persona(reporter_id: str):
    return next((p for p in PERSONAS if p["id"] == reporter_id), PERSONAS[0])


def find_persona_angle(persona: dict, angle_key: str):
    return next((a for a in persona.get("angles", []) if a.get("key") == angle_key), None)
