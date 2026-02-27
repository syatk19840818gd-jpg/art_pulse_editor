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


---
## TASK A-2R?Athr works?? ??? / 2026-02-27?

??:
- 01: 4-0 / 4-4 / 6-2 / 6-3 / SSOT?????
- 02: CARD_ID 10 / 11 / 14 / 16

????:
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020117Z.json`
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020135Z.json`

??????:
- preflight #1: `passed=False`, `dns_ok_rate=1.000 (21/21)`, `http_probe_ok=False`, `wrapper_exit_code=1`
- preflight #2: `passed=False`, `dns_ok_rate=1.000 (21/21)`, `http_probe_ok=False`, `wrapper_exit_code=1`
- fail-fast????? Athr???collect/report/guard?????

### fair/gallery??
| fair | gallery | ???? | ????(>=1?) | ????(????) | ???(>=5?) |
|---|---|---:|---:|---:|---:|
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |

### ??????
- `preflight_failed:http_probe_failed:example.com`

### works?????
- ??collect???????`failed_cases[].notes` ? `works_page_tried / works_page_found / works_candidates_count` ?????
- ??? preflight 2??PASS ?? Athr??collect??????works?????????

### ??0??????
- ????????Athr??? preflight ?????


---
## TASK D0-A2R-BLOCKER-ROOTCAUSE?2026-02-27 preflight????????? + ?????

??:
- 01: 4-0 / 6-3 / SSOT?????
- 02: CARD_ID 14 / 16

### ?????????????
- preflight ? `https://example.com` ??URL? HTTP/TLS ???????????
- 2026-02-27 ??????? DNS ????`dns_ok_rate=1.000`????`example.com` ? TLS ???????
- ?????????????????? fail-fast ????????????

### ????
- fail:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020117Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T020135Z.json`
  - HTTP error: `SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED`
- fix? pass:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T021906Z.json`
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T021937Z.json`

### ??????????
- `run_phase1_network_preflight.py` ???URL??????URL??????????
  - probe??: Google / GitHub / Cloudflare??????????
  - pass??: `http_ok_count >= http_required_successes` ?? `dns_ok_rate >= dns_threshold`
- ????????`tls_cert_verify_failed` ????????????????
- preflight??? `config/phase1_network_preflight_profile.json` ?????
- ??2????????????????????????????????????

### fair/gallery?????????????????
| fair | gallery | ???? | ????(>=1?) | ????(????) | ???(>=5?) |
|---|---|---:|---:|---:|---:|
| N/A | preflight system task | 0 | 0 | 0 | 0.0% |

### ??????
- pre-fix: `single_probe_tls_failure(example.com)`
- post-fix: ???2??PASS?

### ??0??????
- N/A?????????????

---
## RUN 2026-02-27T02:27:16Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json`

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
- no_image_candidates_found_on_artist_detail: 1件

### 失敗ドメイン上位
- athrart.com: 1件


---
## TASK A-2R-RESTART?Athr works?? ??? / 2026-02-27?

??:
- 01: 4-0 / 4-4 / 6-2 / 6-3 / SSOT?????
- 02: CARD_ID 10 / 11 / 14 / 16

??????:
- `python run_phase1_network_preflight.py`?PASS?
- `python run_phase1_network_preflight.py`?PASS?
- `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json"`
- `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json"`
- `PYTHONUTF8=1` ? report ????cp932????????
- `python run_compare_phase1_guard.py --target-year 2025`?PASS?

???:
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T022556Z.json`
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T022617Z.json`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr.json`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_restart_athr_report.json`
- `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T022757Z.json`

### fair/gallery??
| fair | gallery | ???? | ????(>=1?) | ????(????) | ???(>=5?) |
|---|---|---:|---:|---:|---:|
| frieze_london | Athr | 1 | 0 | 0 | 0.0% |

### ??????
- `no_image_candidates_found_on_artist_detail`: 1?
- domain: `athrart.com`?1??

### works??????failed_cases[].notes?
- `works_page_tried:3`
- `works_page_found:3`
- `works_candidates_count:0`
- `works_not_found_fallback_used`
- `no_image_candidates_on_detail:athrart.com`

### ??0??????
- ???????? Athr ?????

---
## RUN 2026-02-27T02:37:37Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json`

### サマリー
- 対象人数: 1
- 5枚達成人数: 1
- 達成率(>= 5枚): 100.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 1 | 5 | 100.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- なし

### 失敗ドメイン上位
- なし


---
## TASK A-2R-FIX?Athr works candidates=0 ???? + ???? / 2026-02-27?

??:
- 01: 4-0 / 4-4 / 6-2 / 6-3 / SSOT?????
- 02: CARD_ID 10 / 11 / 14 / 16

????:
- Athr works????????URL? `<img src="...shim.gif" data-lazy="https://...jpg">` ???
- ?? `extract_image_candidates(...)` ? `data-lazy` ??????????????????
  works???? `img` ??????????0????????

????????:
- `run_phase1_seed10_artist_image_collect.py`
  - ??????? `data-lazy` ????
- `run_phase1_seed10_artist_image_collect_report.py`
  - Windows cp932 ??????????????`sys.stdout.reconfigure(errors='backslashreplace')` ????

??????:
- `python run_phase1_network_preflight.py`?PASS?
- `python run_phase1_network_preflight.py`?PASS?
- `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug frieze_london --only-gallery-name Athr --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json"`
- `python run_phase1_seed10_artist_image_collect_report.py --summary-path "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json" --output-json "data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json"`
- `python run_compare_phase1_guard.py --target-year 2025`

???:
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T023327Z.json`
- `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T023343Z.json`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr.json`
- `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix_athr_report.json`
- `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T023851Z.json`

### fair/gallery??
| fair | gallery | ???? | ????(>=1?) | ????(????) | ???(>=5?) |
|---|---|---:|---:|---:|---:|
| frieze_london | Athr | 1 | 1 | 5 | 100.0% |

### ??????
- ??

### works?????
- ????A-2R-RESTART??? `failed_cases[].notes` ?
  - `works_page_tried:3`
  - `works_page_found:3`
  - `works_candidates_count:0`
  ????works??????????????????0??????????
- ????A-2R-FIX??????? `failed_cases` ???0??

### ??0??????
- Athr????????

---
## RUN 2026-02-27T03:05:46Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json`

### サマリー
- 対象人数: 1
- 5枚達成人数: 1
- 達成率(>= 5枚): 100.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 1 | 5 | 100.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- なし

### 失敗ドメイン上位
- なし


---
## TASK A-2R-FIX-1?Athr?????? + Sara Abdu Works????? / 2026-02-27?

??:
- 01: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10 / SSOT?????
- 02: CARD_ID 10 / 11 / 14 / 16

### ???????????????
- ???:
  - `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__*`
- ???:
  - `_trash/task_a2r_fix1_athr_reset_20260227T120334Z`
- ??:
  - before=5, after=0

### ?????Sara Abdu ???
- artist detail URL:
  - `https://athrart.com/artists/33-sara-abdu/biography`
- works candidate URLs:
  - `https://athrart.com/artists/33-sara-abdu/works/`
  - `https://athrart.com/artists/33/works/`
  - `https://athrart.com/artists/33-sara-abdu/biography/works`
- ????:
  - works???????URL? `data-lazy` ?????????????????

### ????????
- `run_phase1_seed10_artist_image_collect.py`
  - `extract_image_candidates` ?????? `data-lazy` ????
  - URL??artist slug??????`biography` ???? `sara-abdu` ?????
  - summary `per_artist_counts[]` ? `works_urls_tried` ???????URL????
- `run_phase1_seed10_artist_image_collect_report.py`
  - Windows???????????????stdout reconfigure??

### ????Sara Abdu ???
- preflight:
  - `phase1_network_preflight_summary_20260227T030220Z.json`?PASS?
  - `phase1_network_preflight_summary_20260227T030241Z.json`?PASS?
- collect summary:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu.json`
- report:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix1_athr_sara_abdu_report.json`
- guard:
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T030932Z.json`?guard_passed=true?

### fair/gallery??
| fair | gallery | ???? | ????(>=1?) | ????(????) | ???(>=5?) |
|---|---|---:|---:|---:|---:|
| frieze_london | Athr | 1 | 1 | 5 | 100.0% |

### ????????SSOT 5-4???artist?????
- `athr__sara-abdu__6a828828__img_01.jpg`
- `athr__sara-abdu__6a828828__img_02.jpg`
- `athr__sara-abdu__6a828828__img_03.jpg`
- `athr__sara-abdu__6a828828__img_04.jpg`
- `athr__sara-abdu__6a828828__img_05.jpg`

### ??????
- ??

### ??0??????
- Athr????????
