from __future__ import annotations

GENERATION_MODEL = "gpt-5-mini"
VISION_MODEL = "gpt-5-mini"

ENRICH_USE_OPENAI_BATCH_DEFAULT = "1"
ENRICH_BATCH_COMPLETION_WINDOW_DEFAULT = "24h"

ARTISTS_ENRICHMENT_BATCH_FIELDS: tuple[str, ...] = (
    "artist_name_kana",
    "headline_ja",
    "summary_ja",
)
EXHIBITIONS_ENRICHMENT_BATCH_FIELDS: tuple[str, ...] = (
    "headline_ja",
    "summary_ja",
)

ARTISTS_ENRICHMENT_FIELD_MODELS: dict[str, str] = {
    # OpenAI Batch requires a single model per batch input file.
    "artist_name_kana": "gpt-5-mini",
    "headline_ja": "gpt-5-mini",
    "summary_ja": "gpt-5-mini",
}
EXHIBITIONS_ENRICHMENT_FIELD_MODELS: dict[str, str] = {
    # OpenAI Batch requires a single model per batch input file.
    "headline_ja": "gpt-5-mini",
    "summary_ja": "gpt-5-mini",
}


def get_artists_enrichment_model(field_name: str) -> str:
    field = str(field_name or "").strip()
    model = ARTISTS_ENRICHMENT_FIELD_MODELS.get(field)
    if not model:
        raise ValueError(f"unsupported_artists_field:{field}")
    return model


def get_exhibitions_enrichment_model(field_name: str) -> str:
    field = str(field_name or "").strip()
    model = EXHIBITIONS_ENRICHMENT_FIELD_MODELS.get(field)
    if not model:
        raise ValueError(f"unsupported_exhibitions_field:{field}")
    return model


def get_enrichment_model_fingerprint(category: str) -> str:
    token = str(category or "").strip()
    if token == "artists":
        field_order = ARTISTS_ENRICHMENT_BATCH_FIELDS
        model_map = ARTISTS_ENRICHMENT_FIELD_MODELS
    elif token == "exhibitions":
        field_order = EXHIBITIONS_ENRICHMENT_BATCH_FIELDS
        model_map = EXHIBITIONS_ENRICHMENT_FIELD_MODELS
    else:
        raise ValueError(f"unsupported_enrichment_category:{token}")
    return "|".join(f"{field}:{model_map[field]}" for field in field_order)
