# v3.1 Cleanup — Final Audit

**Status: COMPLETE.** All 4 user-mandated actions executed; final 12 rows pass HTTP-200 + Japanese-root + correct-disease-citation gates. Awaiting user sign-off before Phase B.

## Actions performed

| # | Action | Status | Detail |
|---|---|---|---|
| 1 | Re-source row 梅毒 (was tokyoweekender.com) | ✓ | Replaced with JIHS IDSS notification page + MHLW STD reporting page (both HTTP 200, Japanese root). |
| 2 | Replace row RSV source URL with JIHS Featured 2024/15 | ✓ | Now `https://id-info.jihs.go.jp/surveillance/idwr/featured/2024/15/index.html` (HTTP 200 verified). |
| 3 | Delete ヘルパンギーナ row | ✓ | Removed from 13-row v3 → 12-row v3.1. |
| 4 | Backfill `total_cases_dashboard_calculated` for all rows | ✓ | 26-week window starting at `reference_start_iso_week`, 47-prefecture sum from `prefecture_week_timeseries.csv`. |

**Bonus fixes** (caught during self-audit, not in original spec):
- STSS row #8 original URL `niid.go.jp/.../12594-stss-2023-2024.html` returned **persistent 404** (agent over-claimed). Replaced with HTTP-verified `id-info.jihs.go.jp/surveillance/iasr/IASR/Vol46/547/547r01.html`.
- 感染性胃腸炎 row #6 original URL `niid.go.jp/.../5701-iasr-noro-150529.html` returned **404**. Replaced with verified `id-info.jihs.go.jp/niid/ja/intestinal-m/intestinal-idwrc/10991-idwrc-2205.html`.
- 咽頭結膜熱 row #9 original URL `id-info.jihs.go.jp/surveillance/idwr/rapid/2023/42/article/adeno-pfc/index.html` was HTTP 200 once but **persistent 404 on retry** (server-side instability). Replaced with stable `id-info.jihs.go.jp/infectious-diseases/adenovirus/index.html` + IDWR 2023 archive index as secondary.

## Final 12 rows (with audit columns)

| # | Disease | Class | RefWk | total_cases_dash_calc (26w) | Primary source host | HTTP |
|---|---|---|---|---|---|---|
| 1 | 手足口病 | sentinel | 2018-W19 | 98,741 | id-info.jihs.go.jp | 200 ✓ |
| 2 | 手足口病 | sentinel | 2019-W20 | 370,364 | www.niid.go.jp (legacy redirect to JIHS) | 200 ✓ |
| 3 | RSウイルス感染症 | sentinel | 2024-W19 | 82,450 | id-info.jihs.go.jp | 200 ✓ |
| 4 | インフルエンザ | sentinel | 2022-W40 | 636,677 | id-info.jihs.go.jp | 200 ✓ |
| 5 | マイコプラズマ肺炎 | sentinel | 2024-W20 | 15,505 | id-info.jihs.go.jp | 200 ✓ |
| 6 | 感染性胃腸炎 | sentinel | 2023-W44 | 431,428 | id-info.jihs.go.jp | 200 ✓ |
| 7 | 流行性耳下腺炎 | sentinel | 2016-W20 | 91,150 | id-info.jihs.go.jp | 200 ✓ |
| 8 | A群溶血性レンサ球菌咽頭炎 | sentinel | 2023-W25 | 198,407 | id-info.jihs.go.jp | 200 ✓ |
| 9 | 咽頭結膜熱 (PCF) | sentinel | 2023-W33 | 169,579 | id-info.jihs.go.jp | 200 ✓ |
| 10 | 風しん | full-report | 2018-W26 | 2,451 | ojs.wpro.who.int (peer-reviewed WPSAR) | 200 ✓ |
| 11 | 麻しん | full-report | 2026-W01 | 322 | id-info.jihs.go.jp | 200 ✓ |
| 12 | 梅毒 | full-report | 2024-W01 | 4,497 | id-info.jihs.go.jp | 200 ✓ |

## Audit gate results

| Gate | Pass? | Detail |
|---|:-:|---|
| All URLs HTTP 200 | ✓ | 14 unique URLs verified this session |
| No tokyoweekender / English news as sole source | ✓ | row #13's tokyoweekender removed |
| No `/en/` paths | ✓ | All Japanese root |
| Each row's source actually about the cited disease | ✓ | RSV/ヘルパンギーナ wrong-disease citations from v3 fixed |
| All 12 diseases covered (after ヘルパンギーナ deletion) | ✓ | 8 sentinel + 3 full-report + 手足口病 ×2 = 12 outbreak rows / 11 unique diseases |
| total_cases_dashboard_calculated computed | ✓ | All 12 rows have non-empty value |

## Data alignment caveat (write into docx Methods)

The new column `total_cases_dashboard_calculated` represents the **47-prefecture 26-week-window sum from the dashboard's IDWR timeseries**, NOT the externally-cited "official" outbreak total. Use this for Phase B sensitivity/lead-time evaluation; the externally-cited `total_cases` field still carries the agent's original `[unverified]` markers for the rows where the agent could not HTTP-verify a specific number from a primary source.

For the JMIR paper Methods section: cite the dashboard-calculated total as the "IDWR aggregate over the outbreak window" and document that this differs from publicly-cited NESID/sentinel-multiplier totals (the very topic of the parallel short paper on reconciliation gaps).

## Files updated

- `outbreak_reference_set_v3.csv` — 12 rows (overwrite of v3 per spec; backup retained in `~/Desktop/claude/`)
- `outbreak_reference_set_v3_curation.md` — narrative not yet rewritten (does not block Phase B; can be regenerated at the docx-drafting step)
- `build_v3_1.py` — re-runnable cleanup script

## Disease coverage summary

**Sentinel (8/9 originally targeted)**: 手足口病 ×2, RSV, インフル, マイコプラズマ, 感染性胃腸炎, 流行性耳下腺炎, A群溶連菌, 咽頭結膜熱
**Full-report case studies (3/3)**: 風しん, 麻しん, 梅毒
**Removed per spec**: ヘルパンギーナ (1)

Total: **12 outbreaks across 11 unique diseases** — meets the user's "12-15 rows" target. Phase B retrospective will run on these 12.
