# RAG抽出 内訳メモ（日本語・集約）

このファイルは、RAG抽出タスクの内訳を人間確認用に日本語でまとめる専用メモです。

## 運用ルール
- ファイルは増やさない。内訳はこの1ファイルに追記する。
- タスクごとに見出しを作り、以下を最低限記載する。
  - fair/gallery単位の対象人数
  - 成功人数
  - 取得件数（画像枚数またはテキスト抽出件数）
  - 成功率（%）
- 詳細JSON（英語キー）は正本として保持し、このメモは確認用サマリとする。

---

## TASK106 実測メモ（最新確認: `run_summary_seed10_2025.json`）

参照元:
- `data/phase1_seed10/logs/run_summary_seed10_2025.json`

### artists_text（テキスト抽出）
- 対象ギャラリー数: 10
- 1件以上抽出できたギャラリー数: 0
- 成功率: 0.0%

| fair | gallery | 対象人数 | 成功人数 | 抽出件数 | 成功率 |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 1 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 1 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 1 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 1 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 1 | 0 | 0 | 0.0% |
| liste | Amanita | 1 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 0 | 0 | 0.0% |

### exhibitions_text（テキスト抽出）
- 対象ギャラリー数: 10
- 1件以上抽出できたギャラリー数: 0
- 成功率: 0.0%

| fair | gallery | 対象人数 | 成功人数 | 抽出件数 | 成功率 |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 1 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 1 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 1 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 1 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 1 | 0 | 0 | 0.0% |
| liste | Amanita | 1 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 0 | 0 | 0.0% |

### 備考
- 画像系の最新実測summaryは現時点で `_trash` へ退避済みのため、このエントリはテキスト抽出ログを基準に記録。
- 以後、画像収集タスク（TASK100+）を再実行した回は同じ形式で本ファイルに追記する。

---
## TASK107 実測メモ（DNSブロッカー継続）
参照元:
- `data/phase1_seed10/logs/run_summary_seed10_2025.json`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T074456Z.json`

### artists_text（テキスト抽出）
- 対象ギャラリー数: 10
- 1件以上抽出できたギャラリー数: 0
- 成功率: 0.0%

| fair | gallery | 対象人数 | 成功人数 | 抽出件数 | 成功率 |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 1 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 1 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 1 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 1 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 1 | 0 | 0 | 0.0% |
| liste | Amanita | 1 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 0 | 0 | 0.0% |

### exhibitions_text（テキスト抽出）
- 対象ギャラリー数: 10
- 1件以上抽出できたギャラリー数: 0
- 成功率: 0.0%

| fair | gallery | 対象人数 | 成功人数 | 抽出件数 | 成功率 |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 1 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 1 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 1 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 1 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 1 | 0 | 0 | 0.0% |
| liste | Amanita | 1 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 0 | 0 | 0.0% |

### artists画像収集
- network_dns_probe_ok: False
- seed_artist_count: 0
- artists_with_ge_1_image: 0
- artists_with_ge_target_images: 0
- total_images_saved: 0
- success_rate_ge_target: 0.0
- 内訳: 対象artists rawが0件のため、fair/gallery内訳テーブルは今回出力なし。

### 失敗理由上位（今回）
- artists_text: DNS_ERROR 10件
- exhibitions_text: DNS_ERROR 10件
- 切り分け: artists失敗の大半は一覧URLフェーズ（list_stage 9 / detail_stage 1）


---
## TASK108 実測メモ（DNSブロッカー継続）

参照元:
- `data/phase1_seed10/logs/run_summary_seed10_2025.json`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T081940Z.json`

### artists_text（テキスト抽出）
- 対象ギャラリー数: 10
- 成功ギャラリー数: 0
- 抽出件数: 0
- 成功率: 0.0%

### exhibitions_text（テキスト抽出）
- 対象ギャラリー数: 10
- 成功ギャラリー数: 0
- 抽出件数: 0
- 成功率: 0.0%

### artists画像収集
- 対象人数: 0（raw未生成）
- 成功人数（>=1枚）: 0
- 取得画像枚数: 0
- 成功率（>=5枚）: 0.0%
- network_dns_probe_ok: false

### 失敗理由上位（今回）
- artists_text: DNS_ERROR 10件
- exhibitions_text: DNS_ERROR 10件
- 段階切り分け（artists）: 一覧URL段 9件 / 詳細URL段 1件

---
## TASK109 実測メモ（DNS preflight失敗で本体停止）

参照元:
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T083115Z.json`
- `data/phase1_seed10/logs/run_summary_seed10_2025.json`

### preflight結果
- dns_ok_rate: 0.0%（0/21）
- http_probe_ok: false
- 判定: preflight fail（本体実行停止）

### artists_text（テキスト抽出）
- 対象ギャラリー数: 10
- 成功ギャラリー数: 0
- 抽出件数: 0
- 成功率: 0.0%

### artists画像収集
- 対象人数: 0（preflight失敗のため未実行）
- 成功人数（>=1枚）: 0
- 取得画像枚数: 0
- 成功率（>=5枚）: 0.0%

### fair/gallery内訳（preflight fail時は実行対象ベースで記録）
| fair | gallery | 対象人数 | 成功人数 | 取得件数 | 成功率 |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 1 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 1 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 1 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 1 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 1 | 0 | 0 | 0.0% |
| liste | Amanita | 1 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 0 | 0 | 0.0% |

### 失敗理由上位（今回）
- preflight: `dns_ok_rate_below_threshold:0.000`
- preflight: `http_probe_failed:example.com`
- 前回本体（参考）: artists/exhibitions ともに `DNS_ERROR` が継続上位

---
## RUN 2026-02-26T09:22:07Z artists画像収集

参照元:
- `/home/syatk/my_projects/art_pulse_editor/data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T091442Z.json`
- `/home/syatk/my_projects/art_pulse_editor/data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_20260226T091442Z_report.json`

### サマリー
- 対象人数: 80
- 5枚達成人数: 66
- 達成率(>= 5枚): 82.5%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Athr | 10 | 3 | 3 | 0.0% |
| frieze_london | Gallery Baton | 10 | 10 | 50 | 100.0% |
| frieze_london | The Approach | 10 | 10 | 50 | 100.0% |
| liste | A+ Works of Art | 10 | 10 | 46 | 90.0% |
| liste | Addis Fine Art | 10 | 10 | 50 | 100.0% |
| liste | Afriart Gallery | 10 | 10 | 50 | 100.0% |
| liste | Amanita | 10 | 10 | 47 | 70.0% |
| liste | Anca Poteraşu Gallery | 10 | 10 | 50 | 100.0% |

### 失敗理由上位
- no_image_candidates_found_on_artist_detail: 7件
- insufficient_image_candidates_after_download: 7件

### 失敗ドメイン上位
- athrart.com: 10件
- spazioamanita.com: 3件
- aplusart.asia: 1件
