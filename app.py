import os
import time
import streamlit as st

# ローカル(.env)でも動くようにする保険（Cloudでは無害）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

APP_TITLE = "Art Pulse Editor - Cloud Smoke Test (Step7)"

REQUIRED = [
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT",
    "R2_BUCKET",
]

# キー名ゆれの吸収（事故対策）
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

def get_any(names, default=None):
    # Cloud: st.secrets → Local: env の順で探す
    for k in names:
        try:
            if k in st.secrets:
                v = st.secrets[k]
                if v:
                    return v
        except Exception:
            pass
        v = os.getenv(k)
        if v:
            return v
    return default

def get_key(key: str, default=None):
    return get_any(ALIASES.get(key, [key]), default=default)

st.title(APP_TITLE)

# ---- status ----
for key in REQUIRED:
    st.write(f"✅ {key} set:", bool(get_key(key)))

st.divider()
st.subheader("Live checks (click buttons)")

# ---- 1) OpenAI ping ----
if st.button("1) OpenAI ping"):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=get_key("OPENAI_API_KEY"))
        model = get_key("TEXT_MODEL", "gpt-5-mini")
        r = client.responses.create(model=model, input="ping")
        st.success(f"OpenAI OK: {r.output_text}")
    except Exception as e:
        st.error(f"OpenAI ERROR: {type(e).__name__}: {e}")

# ---- 2) Gemini embedding ----
if st.button("2) Gemini embedding (len=1536)"):
    try:
        from google import genai
        from google.genai import types

        c = genai.Client(api_key=get_key("GEMINI_API_KEY"))
        model = get_key("TEXT_EMBEDDING_MODEL", "gemini-embedding-001")

        # TOMLが文字列でも確実に1536へ寄せる
        dim_raw = get_key("TEXT_EMBEDDING_OUTPUT_DIM", 1536)
        dim = int(dim_raw)

        r = c.models.embed_content(
            model=model,
            contents="ping",
            config=types.EmbedContentConfig(output_dimensionality=dim),
        )
        emb = r.embeddings[0].values
        st.success(f"Gemini OK: embedding_len={len(emb)}")
    except Exception as e:
        st.error(f"Gemini ERROR: {type(e).__name__}: {e}")

# ---- 3) R2 upload/list/download ----
if st.button("3) R2 upload/list/download"):
    try:
        import boto3

        bucket = get_key("R2_BUCKET")
        endpoint = get_key("R2_ENDPOINT")  # ここが alias 吸収される
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

    except Exception as e:
        st.error(f"R2 ERROR: {type(e).__name__}: {e}")
