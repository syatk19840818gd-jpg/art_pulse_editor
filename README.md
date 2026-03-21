# <<プロジェクト名>>

- <<1行説明：何をする？>>

## Repo Hygiene
- root 直下に backup / snapshot / temp を置かない
- 一時物は `tmp/`、一時退避は `_trash/` に限定する
- `data/current` / `data/history` / `data/runtime` と一時物を混在させない
- 作業後の `.bak` や snapshot は repo root に残さない
- preview / diagnostics / report / latest は通常運用で常時生成しない
- 追加出力が必要な場合だけ `ART_PULSE_OUTPUT_ARTIFACTS=preview,diagnostics,report,latest` を明示する
- 新しい temp / backup / report root は増やさず、正式出力は既存レーンへ寄せる

---

## 現状ステータス
- Step: <<例 Step1 seed準備 / Step2 実装中>>
- 更新日: <<YYYY-MM-DD>>

---

## 初期データ（Step1）
- <<例 data/gallery_seed_10.json>>
- <<例 prompts/extract_rules_current_v2.4.txt>>
- <<例 docs/step1_typing_patch_v2.4.docx>>

---

## セットアップ（後で埋める：今は空でOK）
- Python: <<例 3.11>>
- Install: `pip install -r requirements.txt`
- Run: <<例 streamlit run app.py / python main.py>>

---

## 設定（後で埋める：今は空でOK）
- Env: <<例 OPENAI_API_KEY>>
- `.env` 使用: <<Yes/No>>

---

## フォルダ構成
```
<<プロジェクト名>>/
  例 data/
  例 prompts/
  例 docs/
  README.md
  requirements.txt 
```
