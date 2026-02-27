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
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
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

---
## RUN 2026-02-26T10:50:56Z artists画像収集

参照元:
- `/home/syatk/my_projects/art_pulse_editor/data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2_athr.json`
- `/home/syatk/my_projects/art_pulse_editor/data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2_athr_report.json`

### サマリー
- 対象人数: 1
- 5枚達成人数: 0
- 達成率(>= 5枚): 0.0%
- 閾値通過(70%): False

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- artist_detail_fetch_failed: 1件

### 失敗ドメイン上位
- athrart.com: 1件

---
## TASK A-2R（Athr works優先 再検証）

参照元:
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115105Z.json`
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260226T115106Z.json`

### サマリー
- DNSゲート: fail（2回とも）
- 本体抽出: 未実行（fail-fast）

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |

### 失敗理由上位
- preflight_failed:dns_ok_rate_0.000

### works関連ノート
- `works_page_tried` / `works_page_found` / `works_candidates_count` は本体未実行のため今回未生成

---
## RUN 2026-02-26T15:32:43Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_20260226T153152Z.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_20260226T153152Z_report.json`

### サマリー
- 対象人数: 8
- 5枚達成人数: 6
- 達成率(>= 5枚): 75.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 1 | 5 | 100.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 1 | 1 | 5 | 100.0% |
| liste | A+ Works of Art | 1 | 1 | 5 | 100.0% |
| liste | Addis Fine Art | 1 | 1 | 5 | 100.0% |
| liste | Afriart Gallery | 1 | 1 | 5 | 100.0% |
| liste | Amanita | 1 | 1 | 4 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 1 | 5 | 100.0% |

### 失敗理由上位
- no_image_candidates_found_on_artist_detail: 1件
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- athrart.com: 1件
- spazioamanita.com: 1件

---
## PREP 2026-02-27T02:14:40Z image reset + git scope fix (before A-2R)

Refs:
- SSOT 01: 4-0 / 4-4 / 5-7 / 5-8 / 6-3
- DERIVED 02: CARD_ID 10 / 11 / 14 / 16

Summary:
- Goal: reset mixed image state before running issue 1-5 as one-gallery/one-artist tasks.
- Moved 34 files from `data/phase1_seed10/derived/images/artist_works_images/2025/*` to `_trash/artist_works_images_cleanup_20260227T021440Z`.
- Current source folder count: 0 files.
- Added `.gitignore` rule: `data/phase1_seed10/`.
- Ran `git rm -r --cached data/phase1_seed10` (index-only untrack; local files remain).

Fair/gallery breakdown (moved files):
| fair | gallery_group | before_count | after_count |
|---|---|---:|---:|
| frieze_london | frieze-london folder | 10 | 0 |
| liste | liste folder | 24 | 0 |

Extraction KPI for this prep task:
- target_artists: 0 (no extraction in this task)
- success_artists: 0
- images_saved: 0
- success_rate: 0.0%

Top failure reasons:
- none (this prep task only did reset + git scope fix)

Next action:
- Resume TASK A-2R after preflight passes twice consecutively.

---
## PREP 2026-02-26T18:10:20Z phase1 R2 sync fixed (before issue 1-5)

Summary:
- Added `run_phase1_seed10_r2_sync.py` for phase1 R2 synchronization.
- Verified dry-run and apply before starting issue 1-5.
- issue 1-5 extraction itself is still NOT started.

Commands:
- `python run_phase1_seed10_r2_sync.py --scope all --dry-run`
- `python run_phase1_seed10_r2_sync.py --scope all`

Artifacts:
- `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260226T181020Z.json`
- `data/phase1_seed10/derived/phase1_seed10_artifact_manifest.json`

Result:
- status: OK
- uploaded: 360
- skipped: 134
- failed: 0
- manifest upload: `phase1_seed10/derived/phase1_seed10_artifact_manifest.json` (uploaded=true)

Notes:
- This task is operational preparation only (R2 sync path + manifest). No issue 1-5 extraction run was executed.


### Re-apply consistency check (latest)
- Command: `python run_phase1_seed10_r2_sync.py --scope all`
- Summary: `data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260226T181511Z.json`
- Result: status=OK, uploaded=1, skipped=494, failed=0
- Manifest: `data/phase1_seed10/derived/phase1_seed10_artifact_manifest.json` with `failed_count=0`, `records_count=495`
