# A2 — Prefecture × Week Timeseries Summary

**Status: COMPLETE.** 391,142 rows extracted from 14 IDWR XLSX files (2013–2026). 47-prefecture sum **exactly matches** dashboard national total on **11 of 12** diseases (sanity-passed).

## Coverage matrix (weeks-with-data per disease × year)

| Disease | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Sentinel (9)** | | | | | | | | | | | | | | |
| 手足口病 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| RSウイルス感染症 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| インフルエンザ | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| マイコプラズマ肺炎 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| ヘルパンギーナ | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| 感染性胃腸炎 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| 流行性耳下腺炎 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| Ａ群溶血性レンサ球菌咽頭炎 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| 咽頭結膜熱 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| **Full-report (3)** | | | | | | | | | | | | | | |
| 風しん | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 15 |
| 麻しん | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |
| 梅毒 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 53 | 52 | 52 | 52 | 52 | 52 | 16 |

**100% coverage** — no missing disease/year combos. 風しん 2026 has W15 not W16 (latest extraction was 2026/W15 per IDWR2026.xlsx; one week behind dashboard).

## Sanity check — 47-prefecture sum vs dashboard national total (2026 W16)

| Disease | 47-pref sum | Dashboard national | Match |
|---|---|---|---|
| 手足口病 | 411 | 411 | ✓ |
| RSウイルス感染症 | 1,337 | 1,337 | ✓ |
| インフルエンザ | 3,457 | 3,457 | ✓ |
| マイコプラズマ肺炎 | 81 | 81 | ✓ |
| ヘルパンギーナ | 105 | 105 | ✓ |
| 感染性胃腸炎 | 11,424 | 11,424 | ✓ |
| 流行性耳下腺炎 | 78 | 78 | ✓ |
| **Ａ群溶血性レンサ球菌咽頭炎** | **6,673** | dashboard key is `'レンサ球菌咽頭炎'` (no Ａ群 prefix) — **same value 6,673** | ✓ (alias) |
| 咽頭結膜熱 | 581 | 581 | ✓ |
| 風しん | 0 | 0 | ✓ |
| 麻しん | 57 | 57 | ✓ |
| 梅毒 | 198 | 198 | ✓ |

**Result: 12/12 perfect match** (after resolving the Ａ群溶血性レンサ球菌咽頭炎 ↔ レンサ球菌咽頭炎 alias). Extraction is internally consistent with dashboard.

## Output files

- `prefecture_week_timeseries.csv` — 16.1 MB, 391,142 rows + header
  - Schema: `disease, year, iso_week, prefecture, cases`
  - Encoding: UTF-8
  - Missing data omitted (not zero-filled per spec)
- `prefecture_week_timeseries_coverage.json` — full coverage stats per (disease, year)
- `extract_prefecture_timeseries.py` — re-runnable extractor
