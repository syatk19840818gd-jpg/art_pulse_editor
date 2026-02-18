
import os
import streamlit as st

try:
    # ローカル開発で .env を使う場合の保険（Cloudでは無くてもOK）
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def get_secret(key: str, default=None):
    # Cloud: st.secrets（推奨）
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # Local/WSL: 環境変数
    return os.getenv(key, default)

st.title("Art Pulse Editor - Smoke Test (Step6)")

def is_set(k: str) -> bool:
    v = get_secret(k)
    return bool(v)

st.write("✅ OPENAI_API_KEY set:", is_set("OPENAI_API_KEY"))
st.write("✅ GEMINI_API_KEY set:", is_set("GEMINI_API_KEY"))

st.write("✅ R2_ACCESS_KEY_ID set:", is_set("R2_ACCESS_KEY_ID"))
st.write("✅ R2_SECRET_ACCESS_KEY set:", is_set("R2_SECRET_ACCESS_KEY"))
st.write("✅ R2_ENDPOINT set:", bool(get_secret("R2_ENDPOINT")))
st.write("✅ R2_BUCKET set:", bool(get_secret("R2_BUCKET")))

st.caption("この画面が Cloud 上で表示できれば Step6 合格（接続の実テストは Step7 で実施）")
