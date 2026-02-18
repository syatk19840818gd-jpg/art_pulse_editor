import os
import streamlit as st

# ローカル(.env)でも動くようにする保険（Cloudでは無害）
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

APP_TITLE = "Smoke Test"

# ここだけプロジェクトごとに変えればOK
REQUIRED = [
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT",
    "R2_BUCKET",
]

# キー名ゆれの吸収（今回の事故対策）
ALIASES = {
    "R2_ENDPOINT": ["R2_ENDPOINT", "R2_ENDPOINT_URL", "R2_S3_ENDPOINT"],
    "OPENAI_API_KEY": ["OPENAI_API_KEY"],
    "GEMINI_API_KEY": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],  # どっちで入れてもOKにする場合
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

st.title(APP_TITLE)

for key in REQUIRED:
    names = ALIASES.get(key, [key])
    st.write(f"✅ {key} set:", bool(get_any(names)))

st.caption("表示できればデプロイ疎通OK。")