from __future__ import annotations

TARGET_YEAR = 2025
PERSONA_COUNT = 8
ART_PULSE_TEXT_MIN_CHARS = 1800
ART_PULSE_TEXT_MAX_CHARS = 2000
ART_PULSE_THUMB_FROM_EXHIB = 4
ART_PULSE_THUMB_FROM_ARTIST = 4

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


ART_PULSE_ANGLE_QUERY_TERMS = {
    "alex_politics_social_message": [
        "政治",
        "社会",
        "制度",
        "権力",
        "批評",
        "protest",
        "activism",
        "social",
        "political",
    ],
    "alex_market_anti_thesis": [
        "市場",
        "商業",
        "コレクター",
        "価格",
        "資本",
        "market",
        "commercial",
        "collector",
        "auction",
    ],
    "alex_curation_intent": [
        "キュレーション",
        "展示構成",
        "空間",
        "導線",
        "curation",
        "installation",
        "display",
        "layout",
    ],
    "sophia_energy_emotion": [
        "エネルギー",
        "感情",
        "情熱",
        "解放",
        "衝動",
        "energy",
        "emotion",
        "passion",
        "intensity",
    ],
    "sophia_artist_story": [
        "背景",
        "物語",
        "人生",
        "個人的",
        "story",
        "biography",
        "narrative",
        "personal",
    ],
    "sophia_process": [
        "制作プロセス",
        "手法",
        "工程",
        "素材",
        "process",
        "method",
        "material",
        "technique",
    ],
    "marcus_quote_reinterpret": [
        "引用",
        "再解釈",
        "参照",
        "歴史",
        "quotation",
        "reinterpretation",
        "reference",
        "history",
    ],
    "marcus_traditional_technique": [
        "伝統",
        "技法",
        "古典",
        "継承",
        "traditional",
        "craft",
        "technique",
        "classical",
    ],
    "marcus_contemporaneity": [
        "同時代",
        "現代性",
        "今",
        "社会応答",
        "contemporary",
        "current",
        "present",
    ],
    "kai_multispecies": [
        "共生",
        "生態系",
        "動植物",
        "菌",
        "multispecies",
        "ecology",
        "ecosystem",
        "nonhuman",
    ],
    "kai_future_insight": [
        "未来",
        "科学",
        "バイオ",
        "技術",
        "future",
        "science",
        "bio",
        "technology",
    ],
    "kai_invisible_visible": [
        "不可視",
        "可視化",
        "気候",
        "物理",
        "invisible",
        "visualize",
        "climate",
        "physics",
    ],
    "zoe_sns_visual_power": [
        "SNS",
        "拡散",
        "ミーム",
        "見栄え",
        "viral",
        "meme",
        "instagram",
        "visual power",
    ],
    "zoe_post_internet": [
        "ポストインターネット",
        "仮想",
        "現実",
        "ネット",
        "post-internet",
        "virtual",
        "online",
        "hybrid",
    ],
    "zoe_high_low_boundary": [
        "ハイ＆ロー",
        "サブカル",
        "境界",
        "越境",
        "high and low",
        "subculture",
        "boundary",
        "crossover",
    ],
    "leo_asset_value": [
        "資産価値",
        "将来性",
        "投資",
        "価格",
        "asset",
        "value",
        "investment",
        "price",
    ],
    "leo_self_branding": [
        "セルフブランディング",
        "ブランド",
        "発信",
        "戦略",
        "branding",
        "positioning",
        "profile",
        "strategy",
    ],
    "leo_collector_desire": [
        "所有欲",
        "コレクター",
        "保存性",
        "需要",
        "collector",
        "demand",
        "collectible",
        "acquisition",
    ],
    "ren_handcraft_trace": [
        "手仕事",
        "痕跡",
        "執念",
        "密度",
        "handmade",
        "handcraft",
        "trace",
        "labor",
    ],
    "ren_material_fetish": [
        "素材",
        "質感",
        "テクスチャー",
        "物性",
        "material",
        "texture",
        "surface",
        "tactile",
    ],
    "ren_durability_finish": [
        "耐久性",
        "完成度",
        "仕上げ",
        "保存",
        "durability",
        "finish",
        "craftsmanship",
        "preservation",
    ],
    "nadia_local_climate": [
        "風土",
        "ローカル",
        "土地",
        "地域史",
        "local",
        "regional",
        "climate",
        "site-specific",
    ],
    "nadia_minority_diversity": [
        "多様性",
        "マイノリティ",
        "ジェンダー",
        "可視化",
        "diversity",
        "minority",
        "gender",
        "inclusion",
    ],
    "nadia_exhibition_as_ritual": [
        "儀式",
        "共同体",
        "振る舞い",
        "社会機能",
        "ritual",
        "community",
        "participation",
        "social function",
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
