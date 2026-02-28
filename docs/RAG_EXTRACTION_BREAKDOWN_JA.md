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

---
## RUN 2026-02-27T07:09:30Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu_report.json`

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

### 年抽出（作品画像）
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[2024, 2024, 2024, 2022, 2022] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True

---
## TASK A-2R-FIX-2（Athr / Sara Abdu 年抽出ルール実装・再検証） / 2026-02-27

参照:
- 01: 4-0 / 4-4（年抽出ルール） / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16

### 旧画像退避（削除なし）
- 退避元:
  - `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__sara-abdu__*`
- 退避先:
  - `_trash/task_a2r_fix2_sara_abdu_reset_20260227_161353`
- 件数:
  - 5件（退避後 0件）

### 実装内容（汎用のみ）
- `run_phase1_seed10_artist_image_collect.py`
  - worksページ内の作品近傍テキスト/alt/figcaptionから年候補を抽出
  - 並び順を `year desc`（年不明は末尾）へ変更
  - summaryへ `year_sort_audit` / `works_candidate_years_top5` / `selected_image_years_top5` / `*_desc_ok` を記録
- `run_phase1_seed10_artist_image_collect_report.py`
  - reportへ `year_sort_audit` を転記

### Sara Abdu 再実測（1ギャラリー=1アーティスト）
- preflight:
  - `phase1_network_preflight_summary_20260227T065325Z.json`（PASS）
  - `phase1_network_preflight_summary_20260227T065331Z.json`（PASS）
- summary:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu.json`
- report:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a2r_fix2_athr_sara_abdu_report.json`
- guard:
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T071428Z.json`（guard_passed=true）

### 年抽出結果（上位5件）
- works候補年配列: `[2024, 2024, 2024, 2022, 2022]`
- 保存画像年配列: `[2024, 2024, 2024, 2022, 2022]`
- 降順性: `works_candidate_year_desc_ok=true` / `selected_image_year_desc_ok=true`

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/The Approach`
- `frieze_london/Arcadia Missa`
- `frieze_london/Gallery Baton`
- `liste/A+ Works of Art`

---
## TASK A-2R-FIX-4（evidence_text可読化） / 2026-02-27

### 退避
- 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__sara-abdu__*`
- 退避先: `_trash/task_a2r_fix4_sara_abdu_reset_20260227_163444`
- 退避件数: 5（退避後 0件）

### 年抽出結果（上位5件）
- works候補年配列: `[2024, 2024, 2024, 2022, 2022]`
- 保存画像年配列: `[2024, 2024, 2024, 2022, 2022]`
- 降順性: `selected_image_year_desc_ok=true`

### evidence_text（ノイズ除去後・抜粋）
- `year=2024` / `Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s`
- `year=2024` / `Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span`
- `year=2022` / `Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa`

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/The Approach`
- `frieze_london/Arcadia Missa`
- `frieze_london/Gallery Baton`
- `liste/A+ Works of Art`

---
## RUN 2026-02-27T07:28:20Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix3_athr_sara_abdu.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix3_athr_sara_abdu_report.json`

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

### 年抽出（作品画像）
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[2024, 2024, 2024, 2022, 2022] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 >2024 " data-imgwidth="2047" data-imgheight="2741" data-artwork_id=...
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 #34;year">2024 " data-imgwidth="2700" data-imgheight="1800" data-artwork_id="1116...
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan>" data-imgwidth="4752" data-imgheigh...
  - year=2022 evidence_text=Sara Abdu, To See the Infinite Within Me, 2022 4;>2022 " data-imgwidth="1811" data-imgheight="1017" data-artwork_id="...
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 " data-imgwidth="776" data-imgheight="1113" data-artwork_i...

---
## TASK A-2R-FIX-3（evidence_text保存） / 2026-02-27

### 退避
- 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/athr__sara-abdu__*`
- 退避先: `_trash/task_a2r_fix3_sara_abdu_reset_20260227_162659`
- 退避件数: 5（退避後 0件）

### 年抽出結果（上位5件）
- works候補年配列: `[2024, 2024, 2024, 2022, 2022]`
- 保存画像年配列: `[2024, 2024, 2024, 2022, 2022]`
- 降順性: `selected_image_year_desc_ok=true`

### evidence_text（抜粋）
- `year=2024` / `Sara Abdu, I Loved You Once: The Unveiled I, 2024 ...`
- `year=2024` / `Sara Abdu, The Infinite Now X, 2024 ...`
- `year=2022` / `Sara Abdu, To See the Infinite Within Me, 2022 ...`

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/The Approach`
- `frieze_london/Arcadia Missa`
- `frieze_london/Gallery Baton`
- `liste/A+ Works of Art`

---
## RUN 2026-02-27T07:36:00Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix4_athr_sara_abdu.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2r_fix4_athr_sara_abdu_report.json`

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

### 年抽出（作品画像）
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[2024, 2024, 2024, 2022, 2022] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan And Sometimes We Are Reminded of Wha...
  - year=2022 evidence_text=Sara Abdu, To See the Infinite Within Me, 2022 4; 2022 Now That I’ve Lost You In My Dreams Where Do We Meet? , /spa
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa

---
## RUN 2026-02-27T08:05:46Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2b_close1_gallery_baton.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2b_close1_gallery_baton_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 1 | 1 | 5 | 100.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- なし

### 失敗ドメイン上位
- なし

### 年抽出（作品画像）
- frieze_london/Gallery Baton gallery-baton__liam-gillick__f0c2c137: works_top5=[2025, 2025, 2025, 2025, 2024] selected_top5=[2025, 2025, 2025, 2025, 2024] desc_ok=True
  - year=2025 evidence_text=Expanded Endeavor _columns_3 flow_list clearwithin Liam Gillick Expanded Endeavor , 2025 a
  - year=2025 evidence_text=Endless Discussion Platforms Liam Gillick Endless Discussion Platforms , 2025
  - year=2025 evidence_text=Continual Discussion Platforms Liam Gillick Continual Discussion Platforms , 2025
  - year=2025 evidence_text=Cornered Development Liam Gillick Cornered Development , 2025 a hre
  - year=2024 evidence_text=Unassigned Pleasure Parameter Liam Gillick Unassigned Pleasure Parameter , 2024

---
## TASK A-2B-CLOSE-1（①-2 Gallery Baton） / 2026-02-27

参照:
- 01: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16

### 対象artist（1ギャラリー=1アーティスト）
- gallery: `frieze_london / Gallery Baton`
- source_url: `https://gallerybaton.com/artists/35-liam-gillick`
- artist_key: `gallery-baton__liam-gillick__f0c2c137`

### 退避
- 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/gallery-baton__*`
- 退避先: `_trash/task_a2b_close1_gallery_baton_reset_20260227_170505`
- 退避件数: 0（既存混在なし）

### 実測結果
- collect: `saved_images=5`, `target_met=true`, `failed_cases=0`
- 年配列: `selected_image_years_top5=[2025, 2025, 2025, 2025, 2024]`（降順OK）
- 混入判定: selected URL/evidence に `exhibition/profile/hero` 該当なし（0件）

### works由来判定
- `works_urls_tried=['https://gallerybaton.com/artists/35-liam-gillick']`
- `/works` サフィックスURL自体は出ないが、同一URL内の作品群から抽出できており、Exhibitions/Profile混入は確認されない

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/The Approach`
- `frieze_london/Arcadia Missa`
- `frieze_london/Athr`
- `liste/A+ Works of Art`

---
## RUN 2026-02-27T08:12:25Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_close1_a_plus_works.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_close1_a_plus_works_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 1 | 5 | 100.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- なし

### 失敗ドメイン上位
- なし

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__ahmad-fuad-osman__92ed6306: works_top5=[None, None, None, None, None] selected_top5=[None, None, None, None, None] desc_ok=True
  - year=None evidence_text=Dang Thuy Anh
  - year=None evidence_text=Tawatchai Puntusawasdi
  - year=None evidence_text=Mella Jaarsma
  - year=None evidence_text=Wiyoga Muhardanto
  - year=None evidence_text=Kentaro Hiroki

---
## TASK A-2A-CLOSE-1（①-3 A+ Works of Art） / 2026-02-27

参照:
- 01: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16

### 対象artist（1ギャラリー=1アーティスト）
- gallery: `liste / A+ Works of Art`
- source_url: `https://aplusart.asia/artists/46-ahmad-fuad-osman`
- artist_key: `a-works-of-art__ahmad-fuad-osman__92ed6306`

### 退避
- 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/liste/a-works-of-art__*`
- 退避先: `_trash/task_a2a_close1_a_plus_works_reset_20260227_171149`
- 退避件数: 0（既存混在なし）

### 実測結果
- collect: `saved_images=5`, `target_met=true`, `failed_cases=0`
- year配列: `selected_image_years_top5=[None, None, None, None, None]`
- `works_urls_tried=['https://aplusart.asia/artists/']`（artist detail ではなく一覧系）

### 判定（未解決）
- exhibition/profile/hero 混入は0件
- ただし selected URL に `thuy-anh` / `kentaro` 等の他作家トークンを確認
- ①-3完了条件（対象作家のWORKS優先抽出）は未達のため、次タスクで修正継続

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/The Approach`
- `frieze_london/Arcadia Missa`
- `frieze_london/Athr`
- `frieze_london/Gallery Baton`

---
## TASK A-2A-CLOSE-2（①-3最終確定 A+ Works of Art） / 2026-02-28

参照:
- 01: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16

### 対象artist（1ギャラリー=1アーティスト固定）
- Chong: `https://aplusart.asia/artists/35-chong-kim-chiew`
- Gan: `https://aplusart.asia/artists/41-gan-chin-lee`

### 実測結果
- Chong:
  - `saved_images=3`, `target_met=false`
  - `works_only_artist_match_unique_count=3`
  - `works_only_artist_match_unique_urls_top20` は 3件
- Gan:
  - `saved_images=0`, `target_met=false`
  - `works_only_artist_match_unique_count=0`
  - `works_only_artist_match_unique_urls_top20` は 0件

### 判定（01 6-2準拠: 理由付き確定）
- works-only範囲での追加ユニークソースが不足（Chong=3, Gan=0）のため、現時点で 5/5 到達は不可。
- ドメイン専用ハードコードは導入せず、未達を理由付きで確定。

### 再開条件
- サイト側で works 対象の新規作品画像が追加されること。
- もしくは 01 の仕様変更で抽出許容範囲が変更されること。

---
## RUN 2026-02-27T08:21:35Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_fix1_a_plus_works.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_fix1_a_plus_works_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 1 | 5 | 100.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- なし

### 失敗ドメイン上位
- なし

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__ahmad-fuad-osman__92ed6306: works_top5=[2024, 2023, 2022, 2021, 2019] selected_top5=[2024, 2023, 2022, 2021, 2019] desc_ok=True
  - year=2024 evidence_text=Art Jakarta 2024 Art Jakarta 2024 4 - 6 Oct 2024 div
  - year=2023 evidence_text=Swallow & Spit Swallow & Spit CIMB Art & Soul 2023 span cl
  - year=2022 evidence_text=Anniversary Exhibition 2022 Anniversary Exhibition 2022 Part II span cla
  - year=2021 evidence_text=No Vacancy No Vacancy CIMB Artober, Hotel Art Fair 2021
  - year=2019 evidence_text=A Different Corner A Different Corner Art Expo Malaysia 2019

---
## TASK A-2A-FIX-1（①-3 A+ Works of Art artist一致性ガード修正） / 2026-02-27

参照:
- 01: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16

### 対象artist（1ギャラリー=1アーティスト）
- gallery: `liste / A+ Works of Art`
- source_url: `https://aplusart.asia/artists/46-ahmad-fuad-osman`
- artist_key: `a-works-of-art__ahmad-fuad-osman__92ed6306`

### 退避
- 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/liste/a-works-of-art__*`
- 退避先: `_trash/task_a2a_fix1_a_plus_works_reset_20260227_172057`
- 退避件数: 5（退避後 `a-works-of-art__*` は 0件）

### 実測結果
- collect: `saved_images=5`, `target_met=true`, `failed_cases=0`
- `works_urls_tried=['https://aplusart.asia/artists/46-ahmad-fuad-osman/works']`
- 年配列: `selected_image_years_top5=[2024, 2023, 2022, 2021, 2019]`（降順OK）

### 判定
- 改善確認:
  - 旧 run の他作家混入トークン（`thuy-anh`, `kentaro` 等）は今回 evidence で未検出
  - works探索先が artist一覧 (`/artists/`) から artist works (`.../46-ahmad-fuad-osman/works`) へ修正
- 未解決:
  - selected URL 5/5 が `/exhibitions/main_image_override/` を含む
  - よって ①-3 の最終完了条件（WORKS優先のみ、Exhibitions/Profile混入ゼロ）は未達

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/The Approach`
- `frieze_london/Arcadia Missa`
- `frieze_london/Athr`
- `frieze_london/Gallery Baton`

---
## RUN 2026-02-27T08:34:48Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_fix2_a_plus_works.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_fix2_a_plus_works_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 1 | 5 | 100.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- なし

### 失敗ドメイン上位
- なし

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__ahmad-fuad-osman__92ed6306: works_top5=[1989, 1953, None, None, None] selected_top5=[1989, 1953, None, None, None] desc_ok=True
  - year=1989 evidence_text=Nicolae Ceausescu (1918 - 1989) Nicolae Ceausescu (1918 - 1989)
  - year=1953 evidence_text=Stalin (1878 - 1953) 1874 Stalin (1878 - 1953) !--
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #10 A VICTIM OF CIRCUMSTANCES #10 /l
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #11 A VICTIM OF CIRCUMSTANCES #11 /l
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #8 A VICTIM OF CIRCUMSTANCES #8 /li

---
## TASK A-2A-FIX-2（①-3 A+ Works of Art works-only画像選別ガード強化） / 2026-02-27

参照:
- 01: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16

### 対象artist（1ギャラリー=1アーティスト）
- gallery: `liste / A+ Works of Art`
- source_url: `https://aplusart.asia/artists/46-ahmad-fuad-osman`
- artist_key: `a-works-of-art__ahmad-fuad-osman__92ed6306`

### 退避
- 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/liste/a-works-of-art__*`
- 退避先: `_trash/task_a2a_fix2_a_plus_works_reset_20260227_173343`
- 退避件数: 5（退避後 `a-works-of-art__*` は 0件）

### 実測結果
- collect: `saved_images=5`, `target_met=true`, `failed_cases=0`
- `works_urls_tried=['https://aplusart.asia/artists/46-ahmad-fuad-osman/works']`
- 年配列: `selected_image_years_top5=[1989, 1953, None, None, None]`（降順OK, 年不明は末尾）

### 判定（クローズ）
- selected URL/evidence に `exhibition/profile/hero` 混入なし（0件）
- selected URL は `artlogicstorage/.../images/view/...` 系で、`/exhibitions/main_image_override/` は 0件
- ①-3（A+ Works of Art）は完了条件を満たしてクローズ

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/The Approach`
- `frieze_london/Arcadia Missa`
- `frieze_london/Athr`
- `frieze_london/Gallery Baton`

---
## RUN 2026-02-27T08:50:01Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach_report.json`

### サマリー
- 対象人数: 1
- 5枚達成人数: 1
- 達成率(>= 5枚): 100.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 1 | 5 | 100.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025, None, None, None, None] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
  - year=None evidence_text=0e179f7cb19ebbb79644a-2666x1500.jpg? data-v-2ece09e4 img
  - year=None evidence_text=-v-24c3423d img
  - year=None evidence_text=72a6562110866b91bfda7-2666x1500.jpg? data-v-2ece09e4 img
  - year=None evidence_text=b85f16878af166842d35a-2667x1500.jpg? data-v-2ece09e4 img

---
## TASK A-4-CLOSE-1（④ The Approach 破損画像） / 2026-02-27

参照:
- 01: 4-0 / 4-4 / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16

### 対象artist（1ギャラリー=1アーティスト）
- gallery: `frieze_london / The Approach`
- source_url: `https://www.theapproach.co.uk/artists/phillip-allen/`
- artist_key: `the-approach__phillip-allen__261b72a7`

### 退避
- 退避元: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/the-approach__*`
- 退避先: `_trash/task_a4_close1_the_approach_reset_20260227_174931`
- 退避件数: 0（既存混在なし）

### 破損原因の切り分け結果
- 旧退避ファイル（`_trash/artist_works_images_cleanup_20260227T021440Z/...the-approach__...jpg`）を確認
  - 5/5 で payloadシグネチャが `.avif`、保存拡張子は `.jpg`
  - 破損要因は「拡張子と実データの不整合」
- 汎用対策（ドメイン専用ifなし）:
  - content-type優先で拡張子決定
  - payloadシグネチャ（jpeg/png/webp/avif）で補正
  - HTML payload・極小payloadを除外

### 実測結果
- collect: `saved_images=5`, `target_met=true`, `failed_cases=0`
- `works_urls_tried=['https://www.theapproach.co.uk/artists/phillip-allen/works']`
- 年配列: `selected_image_years_top5=[2025, None, None, None, None]`（降順OK, 年不明は末尾）
- selected URL/evidence で `exhibition/profile/hero` 混入 0件
- 保存ファイルは `.avif` で 5件、payloadシグネチャ一致（この判定は後に再オープン）

### 失敗0件ギャラリー（抜粋）
- `frieze_london/Adams and Ollman`
- `frieze_london/Arcadia Missa`
- `frieze_london/Athr`
- `frieze_london/Gallery Baton`
- `liste/A+ Works of Art`

---
## RUN 2026-02-27T09:02:41Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach_jpegfix.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a4_close1_the_approach_jpegfix_report.json`

### サマリー
- 対象人数: 1
- 5枚達成人数: 1
- 達成率(>= 5枚): 100.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 1 | 5 | 100.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[] desc_ok=True

---
## RUN 2026-02-27T09:07:40Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit_2025.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit_2025_report.json`

### サマリー
- 対象人数: 8
- 5枚達成人数: 8
- 達成率(>= 5枚): 100.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 1 | 5 | 100.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 1 | 5 | 100.0% |
| frieze_london | Gallery Baton | 1 | 1 | 5 | 100.0% |
| liste | A+ Works of Art | 1 | 1 | 5 | 100.0% |
| liste | Addis Fine Art | 1 | 1 | 5 | 100.0% |
| liste | Afriart Gallery | 1 | 1 | 5 | 100.0% |
| liste | Amanita | 1 | 1 | 5 | 100.0% |
| liste | Anca Poteraşu Gallery | 1 | 1 | 5 | 100.0% |

### 失敗理由上位
- なし

### 失敗ドメイン上位
- なし

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[] desc_ok=True
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[] selected_top5=[] desc_ok=True
- frieze_london/Gallery Baton gallery-baton__liam-gillick__f0c2c137: works_top5=[] selected_top5=[] desc_ok=True
- liste/A+ Works of Art a-works-of-art__ahmad-fuad-osman__92ed6306: works_top5=[] selected_top5=[] desc_ok=True
- liste/Addis Fine Art addis-fine-art__dawit-adnew__eea389b0: works_top5=[] selected_top5=[] desc_ok=True

---
## RUN 2026-02-27T09:13:32Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit2_2025.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit2_2025_report.json`

### サマリー
- 対象人数: 8
- 5枚達成人数: 7
- 達成率(>= 5枚): 87.5%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 1 | 5 | 100.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 1 | 5 | 100.0% |
| frieze_london | Gallery Baton | 1 | 1 | 5 | 100.0% |
| liste | A+ Works of Art | 1 | 1 | 5 | 100.0% |
| liste | Addis Fine Art | 1 | 1 | 5 | 100.0% |
| liste | Afriart Gallery | 1 | 1 | 5 | 100.0% |
| liste | Amanita | 1 | 1 | 4 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 1 | 5 | 100.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- spazioamanita.com: 1件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025, None, None, None, None] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
  - year=None evidence_text=0e179f7cb19ebbb79644a-2666x1500.jpg? data-v-2ece09e4 img
  - year=None evidence_text=-v-24c3423d img
  - year=None evidence_text=72a6562110866b91bfda7-2666x1500.jpg? data-v-2ece09e4 img
  - year=None evidence_text=b85f16878af166842d35a-2667x1500.jpg? data-v-2ece09e4 img
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[2024, 2024, 2024, 2022, 2022] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan And Sometimes We Are Reminded of Wha...
  - year=2022 evidence_text=Sara Abdu, To See the Infinite Within Me, 2022 4; 2022 Now That I’ve Lost You In My Dreams Where Do We Meet? , /spa
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa
- frieze_london/Gallery Baton gallery-baton__liam-gillick__f0c2c137: works_top5=[2025, 2025, 2025, 2025, 2024] selected_top5=[2025, 2025, 2025, 2025, 2024] desc_ok=True
  - year=2025 evidence_text=Expanded Endeavor _columns_3 flow_list clearwithin Liam Gillick Expanded Endeavor , 2025 a
  - year=2025 evidence_text=Endless Discussion Platforms Liam Gillick Endless Discussion Platforms , 2025
  - year=2025 evidence_text=Continual Discussion Platforms Liam Gillick Continual Discussion Platforms , 2025
  - year=2025 evidence_text=Cornered Development Liam Gillick Cornered Development , 2025 a hre
  - year=2024 evidence_text=Unassigned Pleasure Parameter Liam Gillick Unassigned Pleasure Parameter , 2024
- liste/A+ Works of Art a-works-of-art__ahmad-fuad-osman__92ed6306: works_top5=[1989, 1953, None, None, None] selected_top5=[1989, 1953, None, None, None] desc_ok=True
  - year=1989 evidence_text=Nicolae Ceausescu (1918 - 1989) Nicolae Ceausescu (1918 - 1989)
  - year=1953 evidence_text=Stalin (1878 - 1953) 1874 Stalin (1878 - 1953) !--
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #10 A VICTIM OF CIRCUMSTANCES #10 /l
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #11 A VICTIM OF CIRCUMSTANCES #11 /l
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #8 A VICTIM OF CIRCUMSTANCES #8 /li
- liste/Addis Fine Art addis-fine-art__dawit-adnew__eea389b0: works_top5=[2022, 2022, 2022, 2022, 2022] selected_top5=[2022, 2022, 2022, 2022, 2022] desc_ok=True
  - year=2022 evidence_text=Dawit Adnew, Fraternalisation, 2022 tem Fraternalisation , 2022
  - year=2022 evidence_text=Dawit Adnew, Private Party, 2022 = item Private Party , 2022
  - year=2022 evidence_text=Dawit Adnew, Lifestyle, 2022 Lifestyle , 2022
  - year=2022 evidence_text=Dawit Adnew, Present Day, 2022 tem last Present Day , 2022
  - year=2022 evidence_text=Dawit Adnew, Vacation II, 2022 Vacation II , 2022

---
## 運用メモ（2026-02-27）

- Amanita（Eva Beresin）は作品候補4枚のみのため、`saved_images=4` は仕様上許容（重複取得で5枚化しない）。
- 再実行ポリシーを更新:
  - 成功済み画像は保持（全退避しない）
  - 無効画像のみ `_trash/invalid_cached_images_<run_ts>/...` へ隔離

---
## TASK A-4-CLOSE-1-REOPEN（JPEG/100KBホットフィックス） / 2026-02-27

背景:
- ユーザー確認で `.avif` が読めないため、A-4を再オープン
- 画像サイズが 100KB 目標から外れる（極小/過大）事象を確認

原因:
- CDN の `auto=format` と Accept 条件で AVIF が返り、閲覧側で非対応
- 取得時に「保存前JPEG正規化 + 目標容量圧縮」が未適用

対策（汎用）:
- 画像取得ヘッダを `image/jpeg,image/png,image/*` 優先へ変更
- 保存前に Pillow で JPEG 正規化（`run_phase1_seed10_artist_image_collect.py`）
- `IMAGE_TARGET_SIZE_KB=100` を目標に品質/縮小を段階調整
- 実画像 `120x120` 未満を除外（アイコン級の混入抑止）

全再生成:
- 2025配下の既存画像を `_trash/task_img_jpeg100_refit3_reset_20260227_181519` へ退避後、再収集
- summary: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit3_2025.json`
- report: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit3_2025_report.json`
- guard: `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T091928Z.json`

結果:
- 保存拡張子: `.jpg` のみ（39枚）
- サイズ分布: `min=19,096B / max=102,358B / >120KB=0 / <10KB=0`
- 80〜120KB帯: 29枚
- 失敗1件: `liste/Amanita`（works URL 404由来で 4枚）

---
## RUN 2026-02-27T09:19:16Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit3_2025.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_image_jpeg100_refit3_2025_report.json`

### サマリー
- 対象人数: 8
- 5枚達成人数: 7
- 達成率(>= 5枚): 87.5%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 1 | 1 | 5 | 100.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 1 | 1 | 5 | 100.0% |
| frieze_london | Gallery Baton | 1 | 1 | 5 | 100.0% |
| liste | A+ Works of Art | 1 | 1 | 5 | 100.0% |
| liste | Addis Fine Art | 1 | 1 | 5 | 100.0% |
| liste | Afriart Gallery | 1 | 1 | 5 | 100.0% |
| liste | Amanita | 1 | 1 | 4 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 1 | 5 | 100.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- spazioamanita.com: 1件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025, None, None, None, None] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
  - year=None evidence_text=0e179f7cb19ebbb79644a-2666x1500.jpg? data-v-2ece09e4 img
  - year=None evidence_text=-v-24c3423d img
  - year=None evidence_text=72a6562110866b91bfda7-2666x1500.jpg? data-v-2ece09e4 img
  - year=None evidence_text=b85f16878af166842d35a-2667x1500.jpg? data-v-2ece09e4 img
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[2024, 2024, 2024, 2022, 2022] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan And Sometimes We Are Reminded of Wha...
  - year=2022 evidence_text=Sara Abdu, To See the Infinite Within Me, 2022 4; 2022 Now That I’ve Lost You In My Dreams Where Do We Meet? , /spa
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa
- frieze_london/Gallery Baton gallery-baton__liam-gillick__f0c2c137: works_top5=[2025, 2025, 2025, 2025, 2024] selected_top5=[2025, 2025, 2025, 2025, 2024] desc_ok=True
  - year=2025 evidence_text=Expanded Endeavor _columns_3 flow_list clearwithin Liam Gillick Expanded Endeavor , 2025 a
  - year=2025 evidence_text=Endless Discussion Platforms Liam Gillick Endless Discussion Platforms , 2025
  - year=2025 evidence_text=Continual Discussion Platforms Liam Gillick Continual Discussion Platforms , 2025
  - year=2025 evidence_text=Cornered Development Liam Gillick Cornered Development , 2025 a hre
  - year=2024 evidence_text=Unassigned Pleasure Parameter Liam Gillick Unassigned Pleasure Parameter , 2024
- liste/A+ Works of Art a-works-of-art__ahmad-fuad-osman__92ed6306: works_top5=[1989, 1953, None, None, None] selected_top5=[1989, 1953, None, None, None] desc_ok=True
  - year=1989 evidence_text=Nicolae Ceausescu (1918 - 1989) Nicolae Ceausescu (1918 - 1989)
  - year=1953 evidence_text=Stalin (1878 - 1953) 1874 Stalin (1878 - 1953) !--
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #10 A VICTIM OF CIRCUMSTANCES #10 /l
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #11 A VICTIM OF CIRCUMSTANCES #11 /l
  - year=None evidence_text=A VICTIM OF CIRCUMSTANCES #8 A VICTIM OF CIRCUMSTANCES #8 /li
- liste/Addis Fine Art addis-fine-art__dawit-adnew__eea389b0: works_top5=[2022, 2022, 2022, 2022, 2022] selected_top5=[2022, 2022, 2022, 2022, 2022] desc_ok=True
  - year=2022 evidence_text=Dawit Adnew, Fraternalisation, 2022 tem Fraternalisation , 2022
  - year=2022 evidence_text=Dawit Adnew, Private Party, 2022 = item Private Party , 2022
  - year=2022 evidence_text=Dawit Adnew, Lifestyle, 2022 Lifestyle , 2022
  - year=2022 evidence_text=Dawit Adnew, Present Day, 2022 tem last Present Day , 2022
  - year=2022 evidence_text=Dawit Adnew, Vacation II, 2022 Vacation II , 2022

---
## RUN 2026-02-27T10:07:52Z artists画像収集（full re-extract）

- 参照:
  - data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227.json
  - data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_rag_full_reextract_20260227_report.json

- サマリー:
  - 対象人数: 8
  - 5枚達成人数: 7
  - 達成率(>=5枚): 87.5%
  - 閾値通過(70%): True

---
## TASK TARUTANI-SSOT-REFIT-20260227

- 目的:
  - TarutaniRAG の SSOT差分（4-5/5-5/5-8/5-9）を修正し、再ベクター化する。
- 実装修正:
  - run_tarutani_text_import.py: docx抽出を python-docx に統一、PDF抽出を import 本体で実装。
  - run_tarutani_r2_sync.py: source 同期 key を data/Tarutani_data/... ミラーへ修正。
  - run_vectorize_tarutani_text.py: manifest 最低項目（chunk_size/chunk_overlap/records_count/code_commit_id）を追加。
- 再生成:
  - _trash/task_tarutani_refit_20260227_102918/ へ旧成果物を退避。
  - run_tarutani_text_import.py 再実行（16 records）。
  - 旧 headline_ja を source_path で復元（16件）。
  - run_vectorize_tarutani_text.py 再実行（chunks=74, embedded=74, failed=0）。
  - run_tarutani_r2_sync.py --scope source --dry-run で key 規則確認。
- 主要成果物:
  - data/Tarutani_data/tarutani_text.jsonl
  - data/Tarutani_data/tarutani_text_import_summary.json
  - data/Tarutani_data/vector/tarutani_text_index.npy
  - data/Tarutani_data/vector/tarutani_text_meta.jsonl
  - data/Tarutani_data/vector/artifact_manifest.json

---

## TASK PREP-R2-GUARD-20260227 (R2 save/prune guard)

- Purpose:
  - Enforce R2 save + prune flow with dry-run-first guard to avoid drift and accidental deletes.
- Implementation:
  - run_phase1_seed10_r2_sync.py
    - --require-dry-run-log
    - --max-prune
  - run_tarutani_r2_sync.py
    - --require-dry-run-log
    - --max-prune
    - default scope changed to all
  - run_r2_sync_runbook.py
    - one-command orchestrator for fixed order and guarded apply
- Logs:
  - data/phase1_seed10/logs/phase1_seed10_r2_sync_all_20260227T121330Z.json (apply)
  - data/phase1_seed10/logs/phase1_seed10_r2_sync_logs_20260227T121741Z.json (prune apply)
  - data/Tarutani_data/logs/tarutani_r2_sync_all_20260227T121540Z.json (apply)
  - data/Tarutani_data/logs/tarutani_r2_sync_all_20260227T121748Z.json (prune apply)
- Current R2 state:
  - phase1_seed10/derived/images: 39
  - phase1_seed10/derived/vector: 5
  - tarutani/vectors: 5
  - data/Tarutani_data/* source keys: 16
  - legacy tarutani/source/* removed

---
## TASK A-3A-CLOSE-1（frieze_london / Adams and Ollman）

- 退避:
  - src: data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*
  - dst: _trash/task_a3a_close1_adams_ollman_reset_20260227_220415/
  - moved=0, src_remaining=0
- artist特定:
  - artists_frieze_london_2025.jsonl: 対象0件（gallery_name_en=Adams and Ollman）
  - fallback source_url（記録用）: https://adamsandollman.com/Past-Exhibitions
- 再実測:
  - summary: data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman.json
  - report: data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman_report.json
  - result: seed_artist_count=0, target_case_count=0, failed_cases=0
- 判定:
  - 理由付きスキップ（前提データ不足）
  - 理由: artists raw に対象galleryのartistレコードがないため、works優先抽出判定に進めない
  - 再開条件:
    - data/phase1_seed10/raw/artists_frieze_london_2025.jsonl に Adams and Ollman のartist 1件以上を生成し、同タスクを再実行する

---
## RUN 2026-02-27T13:05:07Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_close1_adams_ollman_report.json`

### サマリー
- 対象人数: 0
- 5枚達成人数: 0
- 達成率(>= 5枚): 0.0%
- 閾値通過(70%): False

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- なし

---
## RUN 2026-02-27T13:24:52Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_fix1_adams_ollman.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_fix1_adams_ollman_report.json`

### サマリー
- 対象人数: 1
- 5枚達成人数: 0
- 達成率(>= 5枚): 0.0%
- 閾値通過(70%): False

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 1 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- no_image_candidates_found_on_artist_detail: 1件

### 失敗ドメイン上位
- adamsandollman.com: 1件

### 年抽出（作品画像）
- frieze_london/Adams and Ollman adams-and-ollman__jonathan-berger-1__dc6f5a49: works_top5=[] selected_top5=[] desc_ok=True

---
## TASK A-3A-FIX-1（2026-02-27 / Adams and Ollman）
- 目的:
  - `Adams and Ollman` の artist seed を raw に1件生成し、`A-3A-CLOSE-1` を再実測可能な状態に戻す。
- preflight:
  - `python run_phase1_network_preflight.py` -> PASS
  - `python run_phase1_network_preflight.py` -> PASS
- seed生成:
  - 追記先: `data/phase1_seed10/raw/artists_frieze_london_2025.jsonl`
  - 追加source_url: `https://adamsandollman.com/Jonathan-Berger-1`
  - artist_id: `dc6f5a49383e316780a77a82a825536d83f663ef8e6fa9accaa83c7448043cf5`
  - backup: `data/phase1_seed10/raw/artists_frieze_london_2025.jsonl.bak_20260227_222406`
- 退避:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*`
  - dst: `_trash/task_a3a_close1_adams_ollman_reset_20260227_222418/`
  - moved=0, src_remaining=0
- 再実測:
  - summary: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_fix1_adams_ollman.json`
  - report: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_fix1_adams_ollman_report.json`
  - guard: `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T132432Z.json`
- 判定:
  - `seed_artist_count=1` まで回復（no targetsは解消）
  - `works_urls_tried` に `https://adamsandollman.com/Jonathan-Berger-1/works` を記録
  - ただし `works_candidates_count=0`, `saved_images=0`, `selected_image_years_top5=[]`
  - failed reason: `no_image_candidates_found_on_artist_detail`
- 継続方針:
  - 01 6-2（ドメイン専用ハードコード増殖禁止）を維持し、まずは汎用抽出で追加改善可能かを検討。
  - 改善余地がなければ「理由付きスキップ（再開条件付き）」へ移行する。

---
## TASK A-3A-CLOSE-2（2026-02-27 / Adams and Ollman, reasoned skip）
- SSOT整合ゲート:
  - 01: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- preflight:
  - `phase1_network_preflight_summary_20260227T134227Z_01.json` PASS
  - `phase1_network_preflight_summary_20260227T134227Z.json` PASS
- reset:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/adams-and-ollman__*`
  - dst: `_trash/task_a3a_close2_adams_ollman_reset_20260227_225228/`
  - moved=0, src_remaining=0
- generic verification (domain hack禁止):
  - works URL: `https://adamsandollman.com/Jonathan-Berger-1/works`
  - HTML実体で `<img>/<picture>/<source>` が 0、`data-src/data-lazy/srcset` も有効候補なし
  - collector側に非`<img>`参照の汎用抽出を追加:
    - `src/data-src/data-original/data-lazy-src/data-lazy/poster`
    - `srcset`（非`img`タグ）
    - inline image URL（jpg/png/webp/avif）
  - 併せて metadataノイズ抑止:
    - `meta` 由来（og/twitter preview）候補を除外
    - 非画像URL（js/css/json）混入を除外
  - 追加後も works candidate は 0 のまま（requests/Playwrightとも）
- rerun outputs:
  - summary: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close2_adams_ollman.json`
  - report: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close2_adams_ollman_report.json`
  - guard: `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T135303Z.json`
- result:
  - `works_urls_tried=['https://adamsandollman.com/Jonathan-Berger-1/works']`
  - `works_candidates_count=0`
  - `saved_images=0`, `selected_image_years_top5=[]`, `selected_image_year_desc_ok=true`
  - fail reason: `no_image_candidates_found_on_artist_detail`
- final decision (01 6-2):
  - **reasoned skip** を確定。
  - 理由: 現状はページ側の公開HTML/DOMに作品画像候補が実質露出しておらず、ここから先はCargo固有の内部API/構造依存になりやすく、ドメイン専用ハードコード増殖リスクが高い。
- reopen condition:
  - 複数ギャラリーで再利用できる汎用ロジック（例: 共通CMSの公開API形式）として検証できる経路が確認できた場合のみ再開。

---
## RUN 2026-02-27T13:53:03Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_close2_adams_ollman.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_close2_adams_ollman_report.json`

### サマリー
- 対象人数: 1
- 5枚達成人数: 0
- 達成率(>= 5枚): 0.0%
- 閾値通過(70%): False

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 1 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- no_image_candidates_found_on_artist_detail: 1件

### 失敗ドメイン上位
- adamsandollman.com: 1件

### 年抽出（作品画像）
- frieze_london/Adams and Ollman adams-and-ollman__jonathan-berger-1__dc6f5a49: works_top5=[] selected_top5=[] desc_ok=True

---
## RUN 2026-02-27T14:28:38Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_close1_arcadia_missa.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_close1_arcadia_missa_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__brad-kronz__7503a3e4: works_top5=[] selected_top5=[2026, 2026, 2026, 2026, 2026] desc_ok=True
  - year=2026 evidence_text=om/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_05-600x400.jpg 600w Installation view, Br...
  - year=2026 evidence_text=om/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_05-600x400.jpg 600w Installation view, Br...
  - year=2026 evidence_text=nt-width img 1024w, https://arcadiamissa.com/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view...
  - year=2026 evidence_text=fabric, paper, board, screws and bolts, mc cable, leaves, Speaker and Stool: 105.4 x 44.5 x 27.9 cm (41 1/2 x 17 1/2...
  - year=2026 evidence_text=m/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_012-600x400.jpg 600w Installation view, Br...

---
## TASK A-3B-CLOSE-1（2026-02-27 / Arcadia Missa）
- SSOT整合ゲート:
  - 01: 4-0, 4-4, 5-4, 6-2, 6-3, 10
  - 02: 10_NO_HERO_IMAGES, 11_IMAGE_TARGET_LINE, 14_CATEGORY_4_0_COMMON, 16_SSOT_COMPLIANCE_GATE
- preflight:
  - `phase1_network_preflight_summary_20260227T142604Z.json` PASS（2回連続PASS）
- artist特定（1ギャラリー=1アーティスト固定）:
  - 初期状態では `artists_frieze_london_2025.jsonl` に Arcadia Missa 行が 0 件
  - 実測成立のため seed 1件を追加
  - source_url: `https://arcadiamissa.com/brad-kronz/`
  - artist_id: `7503a3e4e65037add9cfe08788a677bb0df1159424dece0ddf3280f59657fe0c`
  - storage key: `arcadia-missa__brad-kronz__7503a3e4`
- 退避:
  - src: `data/phase1_seed10/derived/images/artist_works_images/2025/frieze-london/arcadia-missa__*`
  - dst: `_trash/task_a3b_close1_arcadia_missa_reset_20260227_232758/`
  - moved=0, src_remaining=0
- 再実測:
  - summary: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_close1_arcadia_missa.json`
  - report: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_close1_arcadia_missa_report.json`
  - guard: `data/phase1_seed10/logs/phase1_guard_summary_2025_20260227T142811Z.json`
- 判定:
  - `saved_images=5`, `target_met=true`, `failed_cases=0`
  - `works_urls_tried=['https://arcadiamissa.com/brad-kronz/works']`
  - selected URL に `exhibition/profile/hero` トークン混入は確認されず
  - `selected_image_years_top5=[2026, 2026, 2026, 2026, 2026]`, `selected_image_year_desc_ok=true`
  - 0件課題は「取得不能」から「取得可」へ解消

---
## RUN 2026-02-27T14:44:05Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_dupfix_arcadia_missa.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_dupfix_arcadia_missa_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__brad-kronz__7503a3e4: works_top5=[] selected_top5=[2026, 2026, 2026, 2026, 2026] desc_ok=True
  - year=2026 evidence_text=om/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_05-600x400.jpg 600w Installation view, Br...
  - year=2026 evidence_text=nt-width img 1024w, https://arcadiamissa.com/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view...
  - year=2026 evidence_text=fabric, paper, board, screws and bolts, mc cable, leaves, Speaker and Stool: 105.4 x 44.5 x 27.9 cm (41 1/2 x 17 1/2...
  - year=2026 evidence_text=m/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_012-600x400.jpg 600w Installation view, Br...
  - year=2026 evidence_text=om/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_05-600x400.jpg 600w Installation view, Br...

---
## RUN 2026-02-27T14:46:47Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_dupfix2_arcadia_missa.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_dupfix2_arcadia_missa_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 4 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- arcadiamissa.com: 1件

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__brad-kronz__7503a3e4: works_top5=[] selected_top5=[2026, 2026, 2026, 2026] desc_ok=True
  - year=2026 evidence_text=/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_05-600x400.jpg 600w / Installation view, Br...
  - year=2026 evidence_text=nt-width img 1024w, https://arcadiamissa.com/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view...
  - year=2026 evidence_text=fabric, paper, board, screws and bolts, mc cable, leaves, Speaker and Stool: 105.4 x 44.5 x 27.9 cm (41 1/2 x 17 1/2...
  - year=2026 evidence_text=wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_012-600x400.jpg 600w / Installation view, Br...


---
## TASK A-3B-DUP-FIX-1?2026-02-27 / Arcadia Missa duplicate fix?
- ??:
  - Arcadia Missa ? selected 5???????2???
  - ?:
    - `...Installation-view_012-1024x683.jpg`
    - `...Installation-view_012-2048x1365.jpg`
- ??????:
  - URL????? raw URL ?????`-1024x683` / `-2048x1365` ??????URL????????????
  - ??????????????metadata? fallback ??????????URL??????????????
- ??????:
  - `run_phase1_seed10_artist_image_collect.py`
    - `normalize_image_url_for_dedupe()` ????`-WxH` ????suffix?????
    - `image_url_hash()` ???dedupe?????????
    - metadata???? URL???identity ????????hash???????????
- ???:
  - ??: `_trash/task_a3b_dupfix_arcadia_reset_20260227_234325/`?5??
  - ???: `_trash/task_a3b_dupfix_arcadia_rerun_reset_20260227_234524/`?4??
  - summary: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_dupfix2_arcadia_missa.json`
  - report: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3b_dupfix2_arcadia_missa_report.json`
- ??:
  - selected URLs ? 4???????????0?
  - `saved_images=4`???????? 5->4?
  - fail reason: `insufficient_image_candidates_after_download`

---
## RUN 2026-02-27T14:58:39Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_fix4_arcadia_missa_brad_kronz.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_fix4_arcadia_missa_brad_kronz_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__brad-kronz__7503a3e4: works_top5=[] selected_top5=[2026, 2026, 2026, 2026, 2025] desc_ok=True
  - year=2026 evidence_text=om/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_05-600x400.jpg 600w Installation view, Br...
  - year=2026 evidence_text=nt-width img 1024w, https://arcadiamissa.com/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view...
  - year=2026 evidence_text=fabric, paper, board, screws and bolts, mc cable, leaves, Speaker and Stool: 105.4 x 44.5 x 27.9 cm (41 1/2 x 17 1/2...
  - year=2026 evidence_text=m/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_012-600x400.jpg 600w Installation view, Br...
  - year=2025 evidence_text=Anymoreb_2019_02-600x400.jpg 600w Brad Kron z It is Not Fun Anymore (b) , 2019, Wood, metal, fabric and stuffing, 152...

---
## RUN 2026-02-27T15:00:48Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_fix5_arcadia_missa_brad_kronz.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3b_fix5_arcadia_missa_brad_kronz_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__brad-kronz__7503a3e4: works_top5=[] selected_top5=[2026, 2026, 2026, 2026, 2025] desc_ok=True
  - year=2026 evidence_text=om/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_05-600x400.jpg 600w Installation view, Br...
  - year=2026 evidence_text=nt-width img 1024w, https://arcadiamissa.com/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view...
  - year=2026 evidence_text=fabric, paper, board, screws and bolts, mc cable, leaves, Speaker and Stool: 105.4 x 44.5 x 27.9 cm (41 1/2 x 17 1/2...
  - year=2026 evidence_text=m/wp-content/uploads/2026/01/AM_Brad-Kronz_Artists-Space_Installation-view_012-600x400.jpg 600w Installation view, Br...
  - year=2025 evidence_text=s-70s_2025_1-2-600x400.jpg 600w Brad Kronz, 80’s, 70’s , 2024, Graphite on paper, cedar, screws and masking tape, 60...

---
## RUN 2026-02-27T18:15:06Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a5_close1_anca_potera_u.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a5_close1_anca_potera_u_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 1 | 1 | 4 | 0.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- ancapoterasu.com: 1件

### 年抽出（作品画像）
- liste/Anca Poteraşu Gallery anca-potera-u-gallery__aurora-kiraly__3ef1b6fb: works_top5=[] selected_top5=[2022, 2022, 2022, 2021] desc_ok=True
  - year=2022 evidence_text=cm img 1024w, https://www.ancapoterasu.com/wp-content/uploads/2022/05/Aurora-Kiraly_Selfportrait-with-sunglasses_1998...
  - year=2022 evidence_text=HR0cHM6XC9cL3d3dy5hbmNhcG90ZXJhc3UuY29tXC93cC1jb250ZW50XC91cGxvYWRzXC8yMDIyXC8wNVwvQXVyb3JhLUtpcmFseV8xLmpwZyIsInNsaW...
  - year=2022 evidence_text=HR0cHM6XC9cL3d3dy5hbmNhcG90ZXJhc3UuY29tXC93cC1jb250ZW50XC91cGxvYWRzXC8yMDIyXC8wNVwvQXVyb3JhLUtpcmFseV8yLmpwZyIsInNsaW...
  - year=2021 evidence_text=seV9TRF9TTl9TZWxmcG9ydHJhaXQtYXMtUGllcnJvdF8yMDIwXzIwMDBweC0yLmpwZyIsInNsaWRlc2hvdyI6IjZiMzA3YmUifQ%3D%3D Self Portra...


## TASK A-5-CLOSE-1 memo (non-anetta rerun)
- target: liste / Anca Poteraşu Gallery (aurora-kiraly)
- works-first URL was tried: https://www.ancapoterasu.com/artists/aurora-kiraly/works (404)
- fallback detail extracted 4 images
- selected URL/evidence had no logo/icon/sprite/favicon/hero/profile/exhibition tokens
- 5-target miss reason: insufficient_image_candidates_after_download

---
## RUN 2026-02-27T18:57:21Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify_report.json`

### サマリー
- 対象人数: 0
- 5枚達成人数: 0
- 達成率(>= 5枚): 0.0%
- 閾値通過(70%): False

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 0 | 0 | 0 | 0.0% |
| frieze_london | Arcadia Missa | 0 | 0 | 0 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- なし
## TASK A-3A-CLOSE-3 (frieze_london / Adams and Ollman: skip finalization)
- 実施日: 2026-02-27
- preflight:
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T185628Z.json` (PASS)
  - `data/phase1_seed10/logs/phase1_network_preflight_summary_20260227T185636Z.json` (PASS)
- skip registry:
  - `data/gallery_lists/skipped_galleries_registry.csv` に既存登録あり（重複追記なし）
  - 行: `Adams and Ollman,https://adamsandollman.com/Past-Exhibitions,https://adamsandollman.com/Jonathan-Berger-1,公開HTML/DOMに作品画像候補が露出せず(01 6-2準拠でskip)`
- 自動スキップ再検証:
  - summary: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify.json`
  - report: `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a3a_close3_adams_ollman_skip_verify_report.json`
  - `notes` に `auto_skipped_by_registry:1` を確認
  - `per_artist_counts=0` / 新規画像保存 0件（抽出実行なし）
- 理由付きスキップ（最終確定）:
  - 理由: 公開HTML/DOM上で works 作品画像候補が取得不能。ドメイン専用ハードコードを追加すると 01 6-2 に抵触。
  - 再開条件: サイト側で works 画像URLが公開DOMで取得可能になる、または同問題を解く汎用抽出ロジックが別ギャラリーにも有効と実証できること。

---
## RUN 2026-02-28T02:23:40Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_max3_all_galleries.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_max3_all_galleries_report.json`

### サマリー
- 対象人数: 25
- 5枚達成人数: 18
- 達成率(>= 5枚): 72.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 3 | 2 | 6 | 33.33% |
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 3 | 3 | 15 | 100.0% |
| frieze_london | Gallery Baton | 3 | 3 | 15 | 100.0% |
| liste | A+ Works of Art | 3 | 3 | 15 | 100.0% |
| liste | Addis Fine Art | 3 | 3 | 15 | 100.0% |
| liste | Afriart Gallery | 3 | 3 | 10 | 33.33% |
| liste | Amanita | 3 | 3 | 13 | 33.33% |
| liste | Anca Poteraşu Gallery | 3 | 3 | 12 | 66.67% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 7件

### 失敗ドメイン上位
- theapproach.co.uk: 2件
- afriartgallery.org: 2件
- spazioamanita.com: 2件
- ancapoterasu.com: 1件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025, None, None, None, None] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
  - year=None evidence_text=1aef7652 Press Books & Editions img
  - year=None evidence_text=-v-24c3423d img
  - year=None evidence_text=dd352820ff6b929311b38-4000x2666.jpg? data-v-2ece09e4 img
  - year=None evidence_text=dc14a870d694062433779-4000x2666.jpg? data-v-2ece09e4 img
- frieze_london/The Approach the-approach__tom-allen__72951a84: works_top5=[] selected_top5=[None] desc_ok=True
  - year=None evidence_text=/artists/tom-allen/press Press img
- frieze_london/The Approach the-approach__helene-appel__3a8b864d: works_top5=[] selected_top5=[] desc_ok=True
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan And Sometimes We Are Reminded of Wha...
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa
  - year=2022 evidence_text=Sara Abdu, The infinite Now, 2022 = year 2022 To See the Infinite Within Me , span
- frieze_london/Athr athr__sarah-abu-abdallah__3d4bcfeb: works_top5=[2023, 2023, 2023, 2022, 2021] selected_top5=[2023, 2023, 2023, 2022, 2021] desc_ok=True
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.13 From the Blankets Series, 2023 div title Blanket No.30 From the Blankets Series spa...
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.30 From the Blankets Series, 2023 div title Blankets No.1 span , /span /span span cl
  - year=2023 evidence_text=Sarah Abu Abdallah, Blankets No.1, 2023 3 /span div title Multitude span , /span /span span class=
  - year=2022 evidence_text=Sarah Abu Abdallah, Multitude, 2022 ;2022 /span div title Horizontal Dimension span , /span /span
  - year=2021 evidence_text=Sarah Abu Abdallah, Horizontal Dimension, 2021 n div title Trees Speaking With Each other span , /span /s

---
## RUN 2026-02-28T02:32:12Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_max3_all_galleries_v2.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_max3_all_galleries_v2_report.json`

### サマリー
- 対象人数: 25
- 5枚達成人数: 18
- 達成率(>= 5枚): 72.0%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 3 | 2 | 6 | 33.33% |
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 3 | 3 | 15 | 100.0% |
| frieze_london | Gallery Baton | 3 | 3 | 15 | 100.0% |
| liste | A+ Works of Art | 3 | 3 | 15 | 100.0% |
| liste | Addis Fine Art | 3 | 3 | 15 | 100.0% |
| liste | Afriart Gallery | 3 | 3 | 10 | 33.33% |
| liste | Amanita | 3 | 3 | 13 | 33.33% |
| liste | Anca Poteraşu Gallery | 3 | 3 | 12 | 66.67% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 7件

### 失敗ドメイン上位
- theapproach.co.uk: 2件
- afriartgallery.org: 2件
- spazioamanita.com: 2件
- ancapoterasu.com: 1件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025, None, None, None, None] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
  - year=None evidence_text=1aef7652 Press Books & Editions img
  - year=None evidence_text=-v-24c3423d img
  - year=None evidence_text=dd352820ff6b929311b38-4000x2666.jpg? data-v-2ece09e4 img
  - year=None evidence_text=dc14a870d694062433779-4000x2666.jpg? data-v-2ece09e4 img
- frieze_london/The Approach the-approach__tom-allen__72951a84: works_top5=[] selected_top5=[None] desc_ok=True
  - year=None evidence_text=/artists/tom-allen/press Press img
- frieze_london/The Approach the-approach__helene-appel__3a8b864d: works_top5=[] selected_top5=[] desc_ok=True
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan And Sometimes We Are Reminded of Wha...
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa
  - year=2022 evidence_text=Sara Abdu, The infinite Now, 2022 = year 2022 To See the Infinite Within Me , span
- frieze_london/Athr athr__sarah-abu-abdallah__3d4bcfeb: works_top5=[] selected_top5=[2023, 2023, 2023, 2022, 2021] desc_ok=True
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.13 From the Blankets Series, 2023 div title Blanket No.30 From the Blankets Series spa...
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.30 From the Blankets Series, 2023 div title Blankets No.1 span , /span /span span cl
  - year=2023 evidence_text=Sarah Abu Abdallah, Blankets No.1, 2023 3 /span div title Multitude span , /span /span span class=
  - year=2022 evidence_text=Sarah Abu Abdallah, Multitude, 2022 ;2022 /span div title Horizontal Dimension span , /span /span
  - year=2021 evidence_text=Sarah Abu Abdallah, Horizontal Dimension, 2021 n div title Trees Speaking With Each other span , /span /s

---
## TASK A-REPRO-FIX-1 UPDATE (2026-02-28)
- 追加実装（`run_phase1_seed10_artist_image_collect.py`）:
  - payload hash 最終重複ガードを追加（同一artist内）
  - token空 artist seed を抽出対象から除外
  - `--force-retry-failed` 時は works URL の page失敗を再評価
- 退避:
  - `_trash/task_a_repro_fix1_reset_20260228_124820/` へ 20件移動
  - `_trash/task_a_repro_fix1_redo_20260228_125649/` へ 10件移動
- 実測ポイント:
  - `athr__30__*` は再生成なし（invalid seed skip）
  - `gallery-baton / Song Burnsoo` は 5件ユニーク（同一実体5連続重複なし）
  - `A+ Works / Chong Kim Chiew` は同一実体5連続重複を解消（3件ユニーク）
  - `A+ Works / Gan Chin Lee` は再抽出0件（重複再生成なし）
  - works URLは cooldown skip ではなく再評価され、404は `html_fetch_failed` として再記録

---
## TASK A-REPRO-FIX-2 UPDATE (2026-02-28)
- 追加実装:
  - artist一致性のartist配下緩和（work情報信号ベース）
  - works URL抽出をartist配下優先に変更
  - tiny画像URLの `large/medium` variant 取得を追加
  - 年抽出で次元値（`4000x2667` 等）の誤年認識を除外
  - foreign person slug 検知を追加
- 実測結果:
  - `ge_target=21/24`（87.5%, threshold_passed=true）
  - The Approach: 3/3 artists が 5枚達成
  - Afriart: 3/3 artists が 5枚達成
  - Anca Poterașu: 3/3 artists が 5枚達成
  - A+ Works of Art: `Chong Kim Chiew=3/5` が残課題（追加2件必要）

---
## RUN 2026-02-28T03:54:35Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix1.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix1_report.json`

### サマリー
- 対象人数: 25
- 5枚達成人数: 16
- 達成率(>= 5枚): 66.67%
- 閾値通過(70%): False

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 3 | 2 | 6 | 33.33% |
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 2 | 2 | 10 | 100.0% |
| frieze_london | Gallery Baton | 3 | 3 | 15 | 100.0% |
| liste | A+ Works of Art | 3 | 2 | 10 | 66.67% |
| liste | Addis Fine Art | 3 | 3 | 15 | 100.0% |
| liste | Afriart Gallery | 3 | 3 | 10 | 33.33% |
| liste | Amanita | 3 | 3 | 13 | 33.33% |
| liste | Anca Poteraşu Gallery | 3 | 3 | 12 | 66.67% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 8件

### 失敗ドメイン上位
- theapproach.co.uk: 2件
- afriartgallery.org: 2件
- spazioamanita.com: 2件
- aplusart.asia: 1件
- ancapoterasu.com: 1件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025, None, None, None, None] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
  - year=None evidence_text=1aef7652 Press Books & Editions img
  - year=None evidence_text=-v-24c3423d img
  - year=None evidence_text=dd352820ff6b929311b38-4000x2666.jpg? data-v-2ece09e4 img
  - year=None evidence_text=dc14a870d694062433779-4000x2666.jpg? data-v-2ece09e4 img
- frieze_london/The Approach the-approach__tom-allen__72951a84: works_top5=[] selected_top5=[None] desc_ok=True
  - year=None evidence_text=/artists/tom-allen/press Press img
- frieze_london/The Approach the-approach__helene-appel__3a8b864d: works_top5=[] selected_top5=[] desc_ok=True
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan And Sometimes We Are Reminded of Wha...
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa
  - year=2022 evidence_text=Sara Abdu, The infinite Now, 2022 = year 2022 To See the Infinite Within Me , span
- frieze_london/Athr athr__sarah-abu-abdallah__3d4bcfeb: works_top5=[] selected_top5=[2023, 2023, 2023, 2022, 2021] desc_ok=True
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.13 From the Blankets Series, 2023 div title Blanket No.30 From the Blankets Series spa...
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.30 From the Blankets Series, 2023 div title Blankets No.1 span , /span /span span cl
  - year=2023 evidence_text=Sarah Abu Abdallah, Blankets No.1, 2023 3 /span div title Multitude span , /span /span span class=
  - year=2022 evidence_text=Sarah Abu Abdallah, Multitude, 2022 ;2022 /span div title Horizontal Dimension span , /span /span
  - year=2021 evidence_text=Sarah Abu Abdallah, Horizontal Dimension, 2021 n div title Trees Speaking With Each other span , /span /s

---
## RUN 2026-02-28T04:26:09Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix2.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix2_report.json`

### サマリー
- 対象人数: 25
- 5枚達成人数: 21
- 達成率(>= 5枚): 87.5%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 3 | 3 | 15 | 100.0% |
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 2 | 2 | 10 | 100.0% |
| frieze_london | Gallery Baton | 3 | 3 | 15 | 100.0% |
| liste | A+ Works of Art | 3 | 3 | 13 | 66.67% |
| liste | Addis Fine Art | 3 | 3 | 15 | 100.0% |
| liste | Afriart Gallery | 3 | 3 | 15 | 100.0% |
| liste | Amanita | 3 | 3 | 13 | 33.33% |
| liste | Anca Poteraşu Gallery | 3 | 3 | 15 | 100.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 3件

### 失敗ドメイン上位
- spazioamanita.com: 2件
- aplusart.asia: 1件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025, None, None, None, None] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
  - year=None evidence_text=1aef7652 Press Books & Editions img
  - year=None evidence_text=-v-24c3423d img
  - year=None evidence_text=dd352820ff6b929311b38-4000x2666.jpg? data-v-2ece09e4 img
  - year=None evidence_text=dc14a870d694062433779-4000x2666.jpg? data-v-2ece09e4 img
- frieze_london/The Approach the-approach__tom-allen__72951a84: works_top5=[] selected_top5=[2023, 1956, None, None, None] desc_ok=True
  - year=2023 evidence_text=0e06c6ea0-4634x2606.jpg? The Hour , 2023 Oil on canvas 56 x 64 cm 22 1/16 x 25 3/16 in. /
  - year=1956 evidence_text=3e0dd7c9f-3476x1956.jpg? img
  - year=None evidence_text=img
  - year=None evidence_text=c68693ba7-3000x1688.jpg? img
  - year=None evidence_text=/artists/tom-allen/press Press img
- frieze_london/The Approach the-approach__helene-appel__3a8b864d: works_top5=[] selected_top5=[2023, 2021, 2000, 1928, None] desc_ok=True
  - year=2023 evidence_text=e86370ac4-2023x2910.jpg? img
  - year=2021 evidence_text=4492a6c36-4444x2500.jpg? Gehweg (pavement) , 2021 Pencil on Cotton 372 x 124 cm 146 15/32 x 48 13/16 i
  - year=2000 evidence_text=5fd545dfa-2000x1125.jpg? img
  - year=1928 evidence_text=ff5be5e28-3942x2218.jpg? img
  - year=None evidence_text=Books & Editions img
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[] selected_top5=[2024, 2024, 2024, 2022, 2022] desc_ok=True
  - year=2024 evidence_text=Sara Abdu, I Loved You Once: The Unveiled I, 2024 2024 The Infinite Now X , 2024 /s
  - year=2024 evidence_text=Sara Abdu, The Infinite Now X, 2024 year 2024 I loved you once: sound scape no. 02 , span
  - year=2024 evidence_text=Sara Abdu, Now That I’ve Lost You In My Dreams Where Do We Meet? , 2021/2024 pan And Sometimes We Are Reminded of Wha...
  - year=2022 evidence_text=Sara Abdu, I loved you once: sound scape no. 02, 2022 2022 The infinite Now , 2022 /spa
  - year=2022 evidence_text=Sara Abdu, The infinite Now, 2022 = year 2022 To See the Infinite Within Me , span
- frieze_london/Athr athr__sarah-abu-abdallah__3d4bcfeb: works_top5=[] selected_top5=[2023, 2023, 2023, 2022, 2021] desc_ok=True
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.13 From the Blankets Series, 2023 div title Blanket No.30 From the Blankets Series spa...
  - year=2023 evidence_text=Sarah Abu Abdallah, Blanket No.30 From the Blankets Series, 2023 div title Blankets No.1 span , /span /span span cl
  - year=2023 evidence_text=Sarah Abu Abdallah, Blankets No.1, 2023 3 /span div title Multitude span , /span /span span class=
  - year=2022 evidence_text=Sarah Abu Abdallah, Multitude, 2022 ;2022 /span div title Horizontal Dimension span , /span /span
  - year=2021 evidence_text=Sarah Abu Abdallah, Horizontal Dimension, 2021 n div title Trees Speaking With Each other span , /span /s

---
## RUN 2026-02-28T05:16:45Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix3.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix3_report.json`

### サマリー
- 対象人数: 25
- 5枚達成人数: 17
- 達成率(>= 5枚): 70.83%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 3 | 3 | 8 | 0.0% |
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 2 | 2 | 10 | 100.0% |
| frieze_london | Gallery Baton | 3 | 3 | 15 | 100.0% |
| liste | A+ Works of Art | 3 | 2 | 8 | 33.33% |
| liste | Addis Fine Art | 3 | 3 | 15 | 100.0% |
| liste | Afriart Gallery | 3 | 3 | 15 | 100.0% |
| liste | Amanita | 3 | 3 | 13 | 33.33% |
| liste | Anca Poteraşu Gallery | 3 | 3 | 15 | 100.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 4件
- target_not_met: 3件

### 失敗ドメイン上位
- theapproach.co.uk: 3件
- aplusart.asia: 2件
- spazioamanita.com: 2件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
- frieze_london/The Approach the-approach__tom-allen__72951a84: works_top5=[] selected_top5=[2023, 1956, None] desc_ok=True
  - year=2023 evidence_text=0e06c6ea0-4634x2606.jpg? The Hour , 2023 Oil on canvas 56 x 64 cm 22 1/16 x 25 3/16 in. /
  - year=1956 evidence_text=3e0dd7c9f-3476x1956.jpg? img
  - year=None evidence_text=/artists/tom-allen/press Press img
- frieze_london/The Approach the-approach__helene-appel__3a8b864d: works_top5=[] selected_top5=[2023, 2021, 2000, 1928] desc_ok=True
  - year=2023 evidence_text=e86370ac4-2023x2910.jpg? img
  - year=2021 evidence_text=4492a6c36-4444x2500.jpg? Gehweg (pavement) , 2021 Pencil on Cotton 372 x 124 cm 146 15/32 x 48 13/16 i
  - year=2000 evidence_text=5fd545dfa-2000x1125.jpg? img
  - year=1928 evidence_text=ff5be5e28-3942x2218.jpg? img
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[] selected_top5=[] desc_ok=True
- frieze_london/Athr athr__sarah-abu-abdallah__3d4bcfeb: works_top5=[] selected_top5=[] desc_ok=True

---
## TASK A-REPRO-TRIAGE-2（未達5件の原因分類確定） / 2026-02-28

参照:
- 01: 4-0 / 4-0-A / 4-4 / 5-4 / 6-2 / 6-3 / 10
- 02: CARD_ID 10 / 11 / 14 / 16
- 固定入力:
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1.json`
  - `data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1_report.json`
  - `data/phase1_seed10/logs/phase1_guard_summary_2025_20260228T062247Z.json`

### 原因分類（5件）
- Arcadia Missa 0/5 #1: `SEED_INVALID`
  - 根拠: `gallery_breakdown.artist_count=1`、Arcadia failed_cases 0件
- Arcadia Missa 0/5 #2: `SEED_INVALID`
  - 根拠: fixed summary内で追加2枠に対応するseed不在
- Athr 0/5（`https://athrart.com/artists/30-/biography`）: `SEED_INVALID`
  - 根拠: `skipped_invalid_artist_seed.reason_code=invalid_artist_seed_token_empty`
- A+ Works 0/5（Gan）: `ARTIST_CONSISTENCY_FILTERED_ALL`
  - 根拠: `works_candidates_count:27` / `artist_consistency_filtered:27` / `works_only_artist_match_unique:0`
- A+ Works 3/5（Chong）: `NO_NEW_IMAGES_GE_MAX_YEAR_SEEN`
  - 根拠: failed_case `reason=no_new_images_ge_max_year_seen`、`works_only_artist_match_unique_count=3`

### 次FIX向け最小対象
- `data/gallery_lists/reextract_targets_task_a_repro_check_all_1.csv`
- 残存対象: `A+ Works / Gan Chin Lee` 1件のみ

## TASK A-REPRO-FIX-3 補足（A+ Works / Gan Chin Lee）
- ユーザー指摘「Gan Chin Lee が一覧に存在しない」については、`data/phase1_seed10/raw/artists_liste_2025.jsonl` に `https://aplusart.asia/artists/41-gan-chin-lee` が存在することを確認。
- 問題の実体は seed 不在ではなく、Gan枠への他作家画像混入。
- 対応として、既存混入画像 `a-works-of-art__gan-chin-lee__*` 5件を `_trash/task_a_repro_fix3_gan_reset_manual/` へ退避し、誤成功状態を解除。
- 再実測結果（`phase1_seed10_artist_image_collect_summary_task_a_repro_fix3.json`）:
  - `Gan Chin Lee = 0/5`（混入5枚は再発せず）
  - `Chong Kim Chiew = 3/5`（未達継続。次タスクで補完）

## TASK A-REPRO-FIX-4（A+ Works / Chong Kim Chiew 3/5→5/5）
- 実行:
  - `python run_phase1_seed10_artist_image_collect.py --target-year 2025 --target-images-per-artist 5 --only-fair-slug liste --only-source-url https://aplusart.asia/artists/35-chong-kim-chiew --force-retry-failed --clear-failed-ledger target --output-json data/phase1_seed10/logs/phase1_seed10_artist_image_collect_summary_task_a_repro_fix4_chong.json`
- 結果:
  - `saved_images=3`, `target_met=false`, reason=`no_new_images_ge_max_year_seen`
- 取得根拠の切り分け:
  - works URL: 5件（`/works`、artist詳細、作品詳細3URL）
  - `extract_image_candidates` 総候補は多いが、works-only + artist一致性を同時に満たす候補はサイズ違いを除くとユニーク3件のみ
  - 追加2件の新規ユニーク候補は、works-only条件の範囲で確認できず

---
## RUN 2026-02-28T05:35:32Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix4_chong.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix4_chong_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 1 | 3 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- no_new_images_ge_max_year_seen: 1件

### 失敗ドメイン上位
- aplusart.asia: 1件

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__chong-kim-chiew__3441be17: works_top5=[2023, 2022, 2022] selected_top5=[] desc_ok=True

## TASK A-REPRO-FIX-5 判定メモ（Chong 5枚化可否）
- 対象: `https://aplusart.asia/artists/35-chong-kim-chiew`
- 再監査結果:
  - works URL 5件（`/works`、artist詳細、作品詳細3URL）
  - works-only + artist一致性を満たす候補の正規化ユニークURLは3件のみ
    - `.../a-worksofart-chong-kim-chiew-scape-with-map-2023.jpg`
    - `.../a-worksofart-chong-kim-chiew-boundary-fluidity-33-2022.png`
    - `.../a-worksofart-chong-kim-chiew-boundary-fluidity-36-2022.png`
- 結論（01 6-2準拠）:
  - 汎用ロジック範囲では 5枚化不可。domain専用ifを追加せず `3/5` を理由付き確定。

---
## RUN 2026-02-28T05:41:51Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix5_chong.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix5_chong_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 1 | 3 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- no_new_images_ge_max_year_seen: 1件

### 失敗ドメイン上位
- aplusart.asia: 1件

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__chong-kim-chiew__3441be17: works_top5=[2023, 2022, 2022] selected_top5=[] desc_ok=True

---
## RUN 2026-02-28T06:07:53Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_close2_gan.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_close2_gan_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- aplusart.asia: 1件

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__gan-chin-lee__9b6389f4: works_top5=[] selected_top5=[] desc_ok=True

---
## TASK A-REPRO-FIX-10 (2026-02-28)
- 目的:
  - `A+ Works` の artists raw を再生成して Gan seed を再供給し、単独再実測する
- 実施:
  - `run_phase1_seed10.py --include-artists-text` を再実行（raw再生成）
  - A+ artists導線 `https://aplusart.asia/artists/` と sitemap を再監査
  - Gan候補URLは `https://aplusart.asia/artists/41-gan-chin-lee/` のみ確認
  - ただし同URLは実アクセスで `https://aplusart.asia/artists/` へ 302 収束
- 単独再実測:
  - source_url=`https://aplusart.asia/artists/41-gan-chin-lee/`
  - 結果: `saved_images=0/5`, `reason=seed_invalid_redirected_to_listing`
  - 根拠: `html_redirected_to_generic_listing:aplusart.asia:/artists/`
- 判定（01 6-2準拠）:
  - artists導線上で有効な Gan 詳細URLが現時点で復活していないため未達確定
  - 再開条件:
    - A+ Works 側で Gan artist詳細URLが復活
    - または artists raw の供給元ロジックを更新し、現行導線から有効seedを再生成

---
## TASK A-REPRO-FIX-9 (2026-02-28)
- 対象:
  - fair=`liste`
  - gallery=`A+ Works of Art`
  - source_url=`https://aplusart.asia/artists/41-gan-chin-lee/`
- seed再解決監査:
  - artists導線（`https://aplusart.asia/artists/`）の現行artistリンクを再収集
  - Ganの現行有効artist詳細URLは導線上で検出できず
  - sitemap上の Gan URL（`/artists/41-gan-chin-lee/`）は実アクセスで `/artists/` に302収束
- 実測:
  - `saved_images=0/5`, `target_met=false`
  - `reason=seed_invalid_redirected_to_listing`
  - notes:
    - `html_redirected_to_generic_listing:aplusart.asia:/artists/`
    - `works_only_artist_match_unique=0`
- 判定（01 6-2準拠）:
  - 現在のGan seedは artist詳細として無効（一覧吸収）で確定
  - 再開条件:
    - A+ Works 側で Gan の有効artist詳細URLが復活
    - または seed供給元（artists_liste_2025.jsonl）を最新導線で再生成

---
## TASK A-REPRO-FIX-7 (2026-02-28)
- 対象:
  - fair=`liste`
  - gallery=`A+ Works of Art`
  - source_url=`https://aplusart.asia/artists/41-gan-chin-lee`
- preflight:
  - `phase1_network_preflight_summary_20260228T073032Z.json` PASS
  - `phase1_network_preflight_summary_20260228T073045Z.json` PASS
- 退避:
  - src=`data/phase1_seed10/derived/images/artist_works_images/2025/liste/a-works-of-art__gan-chin-lee__*`
  - dst=`_trash/task_a_repro_fix7_gan_reset_20260228_163555/`
  - moved=0, remaining=0
- 実装（汎用のみ）:
  - `run_phase1_seed10_artist_image_collect.py` の artist一致判定に compact alnum fallback を追加
  - 目的: `gan-chin-lee` のような記法ゆれ（ハイフン/空白）を一般化して吸収
  - ドメイン専用ifは未追加
- 再実測結果:
  - `saved_images=0/5`, `target_met=false`
  - reason=`insufficient_image_candidates_after_download`
  - notes根拠:
    - `works_page_found:1`
    - `works_url:https://aplusart.asia/artists/41-gan-chin-lee/works`
    - `works_candidates_count:27`
    - `artist_consistency_filtered:27`
    - `works_only_artist_match_unique:0`
- 判定（01 6-2準拠）:
  - 現時点の works-only 公開面では Gan 一致候補が0件のため未達確定（暫定）
  - 再開条件:
    - works配下に Gan 一致の新規画像/テキスト根拠が追加される
    - または 01 仕様変更で works-only / artist一致性の境界が更新される

---
## TASK A-REPRO-FIX-8 (2026-02-28)
- 目的:
  - `A+ Works / Gan Chin Lee` の 0/5 について、seed根拠を再監査し、works-only整合を崩さない最小修正で原因を確定する
- 実装（汎用のみ）:
  - `run_phase1_seed10_artist_image_collect.py`
    - `fetch_html_with_playwright` / `fetch_html` に `is_redirected_to_generic_listing()` 判定を追加
    - artist詳細URL系（`/artists/<slug>...`）が汎用一覧（`/artists`）へリダイレクトされた場合は
      `html_redirected_to_generic_listing` として失敗扱い
    - 最終 `case_reason` に `seed_invalid_redirected_to_listing` を追加
- 実測結果:
  - source_url=`https://aplusart.asia/artists/41-gan-chin-lee`
  - リクエストの実URLが `https://aplusart.asia/artists/` へ収束
  - summary:
    - `reason=seed_invalid_redirected_to_listing`
    - `notes=['html_redirected_to_generic_listing:aplusart.asia:/artists/', ...]`
    - `saved_images=0/5`
- 判定（01 6-2準拠）:
  - 現行seed URLは artist詳細として無効（一覧へ吸収）と確定
  - 再開条件:
    - artists seed を最新URLで再取得し、Ganの有効な詳細URLが復活すること

---
## RUN 2026-02-28T06:07:53Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_close2_chong.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a2a_close2_chong_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 1 | 3 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- no_new_images_ge_max_year_seen: 1件

### 失敗ドメイン上位
- aplusart.asia: 1件

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__chong-kim-chiew__3441be17: works_top5=[2023, 2022, 2022] selected_top5=[] desc_ok=True

---
## RUN 2026-02-28T06:22:47Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_check_all_1_report.json`

### サマリー
- 対象人数: 25
- 5枚達成人数: 17
- 達成率(>= 5枚): 70.83%
- 閾値通過(70%): True

### fair/gallery内訳
| fair | gallery | 対象人数 | 成功人数(>=1枚) | 取得件数(画像枚数) | 成功率(>=5枚) |
|---|---|---:|---:|---:|---:|
| frieze_london | Adams and Ollman | 0 | 0 | 0 | 0.0% |
| frieze_london | The Approach | 3 | 3 | 7 | 0.0% |
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 2 | 2 | 10 | 100.0% |
| frieze_london | Gallery Baton | 3 | 3 | 15 | 100.0% |
| liste | A+ Works of Art | 3 | 2 | 8 | 33.33% |
| liste | Addis Fine Art | 3 | 3 | 15 | 100.0% |
| liste | Afriart Gallery | 3 | 3 | 15 | 100.0% |
| liste | Amanita | 3 | 3 | 13 | 33.33% |
| liste | Anca Poteraşu Gallery | 3 | 3 | 15 | 100.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 4件
- target_not_met: 2件
- no_new_images_ge_max_year_seen: 1件

### 失敗ドメイン上位
- theapproach.co.uk: 3件
- aplusart.asia: 2件
- spazioamanita.com: 2件

### 年抽出（作品画像）
- frieze_london/The Approach the-approach__phillip-allen__261b72a7: works_top5=[] selected_top5=[2025] desc_ok=True
  - year=2025 evidence_text=3692265ed56572d84bfef-2666x1500.jpg? data-v-2ece09e4 Phillip Allen dry chord, wet edge (solar guest version) , 2025 O...
- frieze_london/The Approach the-approach__tom-allen__72951a84: works_top5=[] selected_top5=[1956, None] desc_ok=True
  - year=1956 evidence_text=3e0dd7c9f-3476x1956.jpg? img
  - year=None evidence_text=/artists/tom-allen/press Press img
- frieze_london/The Approach the-approach__helene-appel__3a8b864d: works_top5=[] selected_top5=[2023, 2021, 2000, 1928] desc_ok=True
  - year=2023 evidence_text=e86370ac4-2023x2910.jpg? img
  - year=2021 evidence_text=4492a6c36-4444x2500.jpg? Gehweg (pavement) , 2021 Pencil on Cotton 372 x 124 cm 146 15/32 x 48 13/16 i
  - year=2000 evidence_text=5fd545dfa-2000x1125.jpg? img
  - year=1928 evidence_text=ff5be5e28-3942x2218.jpg? img
- frieze_london/Athr athr__sara-abdu__6a828828: works_top5=[] selected_top5=[] desc_ok=True
- frieze_london/Athr athr__sarah-abu-abdallah__3d4bcfeb: works_top5=[] selected_top5=[] desc_ok=True

---
## RUN 2026-02-28T07:37:53Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix7_gan.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix7_gan_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- aplusart.asia: 1件

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__gan-chin-lee__9b6389f4: works_top5=[] selected_top5=[] desc_ok=True

---
## RUN 2026-02-28T08:03:36Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix8_gan.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix8_gan_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- insufficient_image_candidates_after_download: 1件

### 失敗ドメイン上位
- aplusart.asia: 1件

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__gan-chin-lee__9b6389f4: works_top5=[] selected_top5=[] desc_ok=True

---
## RUN 2026-02-28T08:15:49Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix9_gan_report.json`

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
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 1 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- seed_invalid_redirected_to_listing: 1件

### 失敗ドメイン上位
- aplusart.asia: 1件

### 年抽出（作品画像）
- liste/A+ Works of Art a-works-of-art__gan-chin-lee__9b6389f4: works_top5=[] selected_top5=[] desc_ok=True

---
## RUN 2026-02-28T08:57:23Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix11_arcadia_1.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix11_arcadia_1_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__hannah-black__80563f22: works_top5=[] selected_top5=[2025, 2025, 2025, 2025, 2025] desc_ok=True
  - year=2025 evidence_text=kt-mobile-layout-row kt-row-valign-top kb-theme-content-width Installation view, HUSH MR GIANT , Arcadia Missa, Londo...
  - year=2025 evidence_text=n Hannah Black, No one shall be subjected to torture or to cruel, inhuman or degrading treatment or punishment (Alger...
  - year=2025 evidence_text=t/uploads/2025/03/AM_Hannah-Black_The-Directions_Vleeshal_Installation-view_1-600x400.jpg 600w Installation view, The...
  - year=2025 evidence_text=t/uploads/2025/03/AM_Hannah-Black_The-Directions_Vleeshal_Installation-view_8-600x400.jpg 600w Installation view, The...
  - year=2025 evidence_text=/uploads/2025/03/AM_Hannah-Black_The-Directions_Vleeshal_Installation-view_10-600x400.jpg 600w Installation view, The...

---
## RUN 2026-02-28T08:57:23Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix11_arcadia_2.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix11_arcadia_2_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__jesse-darling__0fd78f9c: works_top5=[] selected_top5=[2025, 2025, 2025, 2024, 2024] desc_ok=True
  - year=2025 evidence_text=kt-mobile-layout-row kt-row-valign-top kb-theme-content-width Installation view, Chi esce entra , Bibliotheca Hertzia...
  - year=2025 evidence_text=ng_Chi-esce-entra_Installation-view_03.jpg 2000w Installation view, Chi esce entra , Bibliotheca Hertziana – Max Plan...
  - year=2025 evidence_text=adiamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_3-600x375.jpg 600w Installation v...
  - year=2024 evidence_text=diamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_30-600x400.jpg 600w Installation v...
  - year=2024 evidence_text=diamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_30-600x400.jpg 600w Installation v...

---
## RUN 2026-02-28T08:57:23Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix11_athr_1.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix11_athr_1_report.json`

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

### 年抽出（作品画像）
- frieze_london/Athr athr__ahaad-alamoudi__f4360dcd: works_top5=[None, 2024, 2022, 2020, 2020] selected_top5=[None, 2024, 2022, 2020, 2020] desc_ok=False
  - year=None evidence_text=Ahaad Alamoudi clearwithin View works. View works var data_track_addressbar: false, services_exclude: 'print, gmail,
  - year=2024 evidence_text=Ahaad Alamoudi, Moving Mountains, 2024 2024 /span div title A Clean You Can Feel span , /span /span
  - year=2022 evidence_text=Ahaad Alamoudi, A Clean You Can Feel, 2022 22 /span div title Makwah Man span , /span /span span class
  - year=2020 evidence_text=Ahaad Alamoudi, Makwah Man, 2020 uot; 2020 /span div title The outdoor health club span , /span /span &
  - year=2020 evidence_text=Ahaad Alamoudi, The outdoor health club, 2020 lt;/span div title The social health club span , /span /span &l

---
## TASK A-REPRO-FIX-11 (2026-02-28)
- 対象:
  - `frieze_london / Arcadia Missa` の 0枚枠2件
  - `frieze_london / Athr` の 0枚枠1件（token空seed由来）
- seed監査:
  - `artists_frieze_london_2025.jsonl` で Arcadia は 1件のみ（Brad Kronz）
  - Athr は token空seed（`/artists/<id>-/biography`）が残存
- seed補正（ロジック変更なし）:
  - Arcadia に 2 seed 追加:
    - `https://arcadiamissa.com/hannah-black/`
    - `https://arcadiamissa.com/jesse-darling/`
  - Athr の token空seedを有効URLへ置換:
    - `30-/biography` -> `30-ahaad-alamoudi/biography/`
    - `35-/biography` -> `35-mohammad-alfaraj/biography/`
    - `36-/biography` -> `36-zahrah-alghamdi/biography/`
    - `40-/biography` -> `40-ayman-yossri-daydban/biography/`
- 単独再実測結果:
  - Arcadia-1 `hannah-black`: `saved_images=5/5`, `target_met=true`
  - Arcadia-2 `jesse-darling`: `saved_images=5/5`, `target_met=true`
  - Athr-1 `ahaad-alamoudi`: `saved_images=5/5`, `target_met=true`
  - 3ケースとも `failed_cases=[]`
- 判定:
  - Arcadia/Athr の 0枚枠は seed不備起因で、seed補正のみで解消できることを確認
  - A+ Works / Gan は引き続き `seed_invalid_redirected_to_listing` で未解消

---
## RUN 2026-02-28T09:20:14Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix12_arcadia_jesse.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix12_arcadia_jesse_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 4 | 0.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
| frieze_london | Gallery Baton | 0 | 0 | 0 | 0.0% |
| liste | A+ Works of Art | 0 | 0 | 0 | 0.0% |
| liste | Addis Fine Art | 0 | 0 | 0 | 0.0% |
| liste | Afriart Gallery | 0 | 0 | 0 | 0.0% |
| liste | Amanita | 0 | 0 | 0 | 0.0% |
| liste | Anca Poteraşu Gallery | 0 | 0 | 0 | 0.0% |

### 失敗理由上位
- target_not_met: 1件

### 失敗ドメイン上位
- arcadiamissa.com: 1件

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__jesse-darling__0fd78f9c: works_top5=[] selected_top5=[2025, 2025, 2025, 2024] desc_ok=True
  - year=2025 evidence_text=kt-mobile-layout-row kt-row-valign-top kb-theme-content-width Installation view, Chi esce entra , Bibliotheca Hertzia...
  - year=2025 evidence_text=ng_Chi-esce-entra_Installation-view_03.jpg 2000w Installation view, Chi esce entra , Bibliotheca Hertziana – Max Plan...
  - year=2025 evidence_text=adiamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_3-600x375.jpg 600w Installation v...
  - year=2024 evidence_text=diamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_30-600x400.jpg 600w Installation v...

---
## RUN 2026-02-28T09:20:14Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix12_athr_ahaad.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix12_athr_ahaad_report.json`

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

### 年抽出（作品画像）
- frieze_london/Athr athr__ahaad-alamoudi__f4360dcd: works_top5=[2024, 2022, 2020, 2020, 2020] selected_top5=[2024, 2022, 2020, 2020, 2020] desc_ok=True
  - year=2024 evidence_text=Ahaad Alamoudi, Moving Mountains, 2024 2024 /span div title A Clean You Can Feel span , /span /span
  - year=2022 evidence_text=Ahaad Alamoudi, A Clean You Can Feel, 2022 22 /span div title Makwah Man span , /span /span span class
  - year=2020 evidence_text=Ahaad Alamoudi, Makwah Man, 2020 uot; 2020 /span div title The outdoor health club span , /span /span &
  - year=2020 evidence_text=Ahaad Alamoudi, The outdoor health club, 2020 lt;/span div title The social health club span , /span /span &l
  - year=2020 evidence_text=Ahaad Alamoudi, What is this, 2020 t; 2020 /span div title Land of Dreams 1 span , /span /span span

---
## RUN 2026-02-28T09:36:21Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix14_arcadia_jesse.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix14_arcadia_jesse_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__jesse-darling__0fd78f9c: works_top5=[] selected_top5=[2024, 2024, 2025, 2025, 2025] desc_ok=False
  - year=2024 evidence_text=cadiamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_10-scaled.jpg 2048w Installation...
  - year=2024 evidence_text=esse-Darling_VANITAS_Installation-view_17-600x400.jpg 600w Jesse Darling, Untitled (still life) , 2018 – ongoing, Vit...
  - year=2025 evidence_text=kt-mobile-layout-row kt-row-valign-top kb-theme-content-width Installation view, Chi esce entra , Bibliotheca Hertzia...
  - year=2025 evidence_text=ng_Chi-esce-entra_Installation-view_03.jpg 2000w Installation view, Chi esce entra , Bibliotheca Hertziana – Max Plan...
  - year=2025 evidence_text=adiamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_3-600x375.jpg 600w Installation v...

---
## RUN 2026-02-28T09:36:21Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix14_athr_ahaad.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix14_athr_ahaad_report.json`

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

### 年抽出（作品画像）
- frieze_london/Athr athr__ahaad-alamoudi__f4360dcd: works_top5=[] selected_top5=[2024, 2022, 2020, 2020, 2020] desc_ok=True
  - year=2024 evidence_text=Ahaad Alamoudi, Moving Mountains, 2024 2024 /span div title A Clean You Can Feel span , /span /span
  - year=2022 evidence_text=Ahaad Alamoudi, A Clean You Can Feel, 2022 22 /span div title Makwah Man span , /span /span span class
  - year=2020 evidence_text=Ahaad Alamoudi, Makwah Man, 2020 uot; 2020 /span div title The outdoor health club span , /span /span &
  - year=2020 evidence_text=Ahaad Alamoudi, The outdoor health club, 2020 lt;/span div title The social health club span , /span /span &l
  - year=2020 evidence_text=Ahaad Alamoudi, What is this, 2020 t; 2020 /span div title Land of Dreams 1 span , /span /span span

---
## RUN 2026-02-28T09:43:33Z artists画像収集

参照元:
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix17_arcadia_jesse.json`
- `C:\Users\tarutani tomoaki\Pictures\Dev\my_projects\art_pulse_editor\data\phase1_seed10\logs\phase1_seed10_artist_image_collect_summary_task_a_repro_fix17_arcadia_jesse_report.json`

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
| frieze_london | Arcadia Missa | 1 | 1 | 5 | 100.0% |
| frieze_london | Athr | 0 | 0 | 0 | 0.0% |
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

### 年抽出（作品画像）
- frieze_london/Arcadia Missa arcadia-missa__jesse-darling__0fd78f9c: works_top5=[] selected_top5=[2025, 2025, 2025, 2024, 2024] desc_ok=True
  - year=2025 evidence_text=kt-mobile-layout-row kt-row-valign-top kb-theme-content-width Installation view, Chi esce entra , Bibliotheca Hertzia...
  - year=2025 evidence_text=ng_Chi-esce-entra_Installation-view_03.jpg 2000w Installation view, Chi esce entra , Bibliotheca Hertziana – Max Plan...
  - year=2025 evidence_text=adiamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_3-600x375.jpg 600w Installation v...
  - year=2024 evidence_text=diamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_30-600x400.jpg 600w Installation v...
  - year=2024 evidence_text=cadiamissa.com/wp-content/uploads/2024/11/AM_Jesse-Darling_VANITAS_Installation-view_10-scaled.jpg 2048w Installation...
