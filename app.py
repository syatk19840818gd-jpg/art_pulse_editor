import os
import time
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def get_secret(key: str, default=None):
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)


def is_set(k: str) -> bool:
    return bool(get_secret(k))


st.title("Art Pulse Editor - Cloud Smoke Test (Step7)")

st.write("✅ OPENAI_API_KEY set:", is_set("OPENAI_API_KEY"))
st.write("✅ GEMINI_API_KEY set:", is_set("GEMINI_API_KEY"))
st.write("✅ R2_ACCESS_KEY_ID set:", is_set("R2_ACCESS_KEY_ID"))
st.write("✅ R2_SECRET_ACCESS_KEY set:", is_set("R2_SECRET_ACCESS_KEY"))
st.write("✅ R2_ENDPOINT set:", bool(get_secret("R2_ENDPOINT")))
st.write("✅ R2_BUCKET set:", bool(get_secret("R2_BUCKET")))

st.divider()
st.subheader("Live checks (click buttons)")


# ---- 1) OpenAI ping ----
if st.button("1) OpenAI ping"):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
        r = client.responses.create(model=get_secret("TEXT_MODEL", "gpt-5-mini"), input="ping")
        st.success(f"OpenAI OK: {r.output_text}")
    except Exception as e:
        st.error(f"OpenAI ERROR: {type(e).__name__}: {e}")


# ---- 2) Gemini embedding ----
if st.button("2) Gemini embedding (len=1536)"):
    try:
        from google import genai
        from google.genai import types

        c = genai.Client(api_key=get_secret("GEMINI_API_KEY"))
        r = c.models.embed_content(
            model=get_secret("TEXT_EMBEDDING_MODEL", "gemini-embedding-001"),
            contents="ping",
            config=types.EmbedContentConfig(output_dimensionality=1536),
        )
        emb = r.embeddings[0].values
        st.success(f"Gemini OK: embedding_len={len(emb)}")
    except Exception as e:
        st.error(f"Gemini ERROR: {type(e).__name__}: {e}")


# ---- 3) R2 upload/list/download ----
if st.button("3) R2 upload/list/download"):
    try:
        import boto3

        bucket = get_secret("R2_BUCKET")
        endpoint = get_secret("R2_ENDPOINT")
        access_key = get_secret("R2_ACCESS_KEY_ID")
        secret_key = get_secret("R2_SECRET_ACCESS_KEY")
        region = get_secret("R2_REGION", "auto")

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
        st.write("list:", keys[-10:])  # 多すぎると見づらいので末尾10件だけ

        obj = s3.get_object(Bucket=bucket, Key=key)
        data = obj["Body"].read().decode("utf-8")
        st.success(f"download OK: {data}")

    except Exception as e:
        st.error(f"R2 ERROR: {type(e).__name__}: {e}")
