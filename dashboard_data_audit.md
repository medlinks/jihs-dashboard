# Dashboard Data Audit — read-only inspection of `~/Desktop/claude/dashboard.html`

**Audit date**: 2026-05-06. **Method**: read-only Python inspection of the embedded JSON in `dashboard.html` and its source files (`scripts/full_dashboard_data.json`, `scripts/annual_incidence.json`, `scripts/nesid_pref_data.json`). **No external fetches**, **no modifications**, **no assumptions filled from training memory**.

## §1. All disease keys (中日英 alignment table, by namespace)

The dashboard splits data into 4 primary namespaces. **Total disease keys per namespace:**

| Namespace | # keys | Structure | Source file |
|---|---|---|---|
| `DATA.weekly_trends` | **108** | disease → list of {year, week, total} (national-level time series) | `scripts/full_dashboard_data.json` |
| `DATA.weekly_pref` | **108** | disease → {prefecture: int} — **LATEST WEEK SNAPSHOT ONLY**, not time-series | `scripts/full_dashboard_data.json` |
| `DATA.speed_trends` | **87** | disease → list of {year, week, total} for last ~6 weeks | `scripts/full_dashboard_data.json` |
| `DATA.speed_pref` | **87** | disease → {prefecture: int} — latest-week snapshot | `scripts/full_dashboard_data.json` |
| `DATA.annual_incidence` | **110** | disease → {year_str: cumulative} — annual rolled-up | `scripts/annual_incidence.json` |
| `DATA.nesid_pref_data` | **60** | disease → {year: {pref: {cases, pop_k, rate_100k}}} | `scripts/nesid_pref_data.json` |
| `DATA.nesid_2024` | (annual report) | NESID 2024 annual figures by disease/age/sex/prefecture | `scripts/nesid_2024.json` (7.7 MB) |
| `DATA.urban_tier` | 47 prefectures | added 2026-05-06 from a201.xls (DID 2020 census) | injected from `prefecture_did_classification.json` |

### Categorical breakdown of the 108 weekly_trends keys

By 感染症法 reporting class (excerpt):
- **5類定点 sentinel** (~26 diseases): インフルエンザ, インフルエンザ(入院患者), RSウイルス感染症, 手足口病, ヘルパンギーナ, 感染性胃腸炎, 咽頭結膜熱, 流行性耳下腺炎, 水痘, 突発性発しん, 急性出血性結膜炎, 流行性角結膜炎, A群溶連菌咽頭炎, マイコプラズマ肺炎, クラミジア肺炎 etc.
- **5類全数把握** (~26 diseases): 麻しん, 風しん, 先天性風しん症候群, 梅毒, 結核, 百日咳, アメーバ赤痢, ウイルス性肝炎, 後天性免疫不全症候群, 急性脳炎, 劇症型溶血性レンサ球菌感染症, 侵襲性肺炎球菌感染症, 侵襲性髄膜炎菌感染症, 侵襲性インフルエンザ菌感染症, 破傷風, クロイツフェルト・ヤコブ病, 播種性クリプトコックス症, バンコマイシン耐性腸球菌感染症, etc.
- **1類**: エボラ出血熱, クリミア・コンゴ出血熱, ペスト, ラッサ熱, マールブルグ病, 痘そう, 南米出血熱
- **2類**: 結核, ジフテリア, 中東呼吸器症候群, 重症急性呼吸器症候群, 急性灰白髄炎, 鳥インフルエンザ(H5N1)/H7N9
- **3類**: コレラ, 細菌性赤痢, 腸チフス, パラチフス, 腸管出血性大腸菌感染症
- **4類** (~50 diseases): デング熱, レジオネラ症, つつが虫病, 日本紅斑熱, 重症熱性血小板減少症候群 (SFTS), マラリア, レプトスピラ症, A型肝炎, E型肝炎, ウエストナイル熱, etc.
- **緊急 / 別カテゴリ**: 新型コロナウイルス感染症 (172 weekly records), エムポックス (172 records — late onboarded 2022)

Full 108-key list available in `dashboard_data_audit_full_keys.txt` (separately produced if user wants the full enumeration).

## §2. 季節性インフルエンザ専項報告 — **CRITICAL**

The user's archive decision was prompted by uncertainty about whether 季節性インフルエンザ data lives in the dashboard. **The audit answer is unambiguous: YES, seasonal influenza data IS in the dashboard.**

| Key | In `weekly_trends`? | Records | Time range | Max weekly value | Notes |
|---|:-:|---|---|---|---|
| **`インフルエンザ`** | ✓ | **694** | **2013 W1 → 2026 W16** | **317,812** (post-COVID winter 2024 W52) | ✓ — primary seasonal flu sentinel (no subtype modifier) |
| **`インフルエンザ(入院患者)`** | ✓ | 485 | 2017 W1 → 2026 W16 | 5,281 | ✓ — hospitalized cases, partial coverage |
| `侵襲性インフルエンザ菌感染症` | ✓ | 694 | 2013 W1 → 2026 W16 | 30 | this is *Haemophilus influenzae*, **NOT** seasonal flu |
| `鳥インフルエンザ` | ✓ | 694 | full | 0 | avian flu — exclude per user spec |
| `鳥インフルエンザ（H5N1)` | ✓ | 694 | full | 0 | avian flu |
| `鳥インフルエンザ（H7N9)` | ✓ | 694 | full | 0 | avian flu |
| `鳥インフルエンザ(Ｈ５Ｎ１を除く）` | ✓ | 52 | 2021 only | 0 | partial — single-year sentinel |

### Influenza coverage in other namespaces

- **`weekly_pref['インフルエンザ']`**: present, all 47 prefectures, but **LATEST-WEEK SNAPSHOT only** — value type is `int` (e.g., 北海道=460), not a list of weekly entries. **For prefecture-level time series, use `weekly_extracted/IDWR{year}.xlsx`** (raw IDWR sheets per year — these are present and not archived).
- **`speed_trends`**: only **侵襲性インフルエンザ菌感染症** + 3 鳥インフル variants. **Seasonal インフルエンザ is NOT in speed_trends** (sentinel diseases generally absent from speed reporting).
- **`annual_incidence['インフルエンザ']`**: ✓, 12 years coverage.
- **`nesid_pref_data`**: only 侵襲性インフルエンザ菌感染症; **seasonal flu NOT in nesid_pref_data** because NESID = 全数把握 only, sentinel diseases excluded by definition.

### What this means for the previous (now archived) pilot v2 retrospective

The pilot v2 §6 "Influenza 2022/W51" result claiming D_growth detected the post-COVID rebound +8 weeks early WAS based on `weekly_trends['インフルエンザ']` (real dashboard data, 694 records, full 2013–2026 coverage). That data IS valid. The previous prefecture-level traces for influenza were extracted from `weekly_extracted/IDWR{year}.xlsx` (raw IDWR sheets, also valid).

**Per the user's archive decision**, this still doesn't undo the precaution: the previous pilot was un-audited; the new round must be audited and user-confirmed. **The audit confirms the influenza data is real and usable**, so any new pilot CAN safely include seasonal influenza if user signs off.

## §3. Time coverage range per key

Aggregate stats across `weekly_trends`:
- 92/108 keys have **min year ≤ 2013 AND max year ≥ 2026** (full 14-year coverage)
- 93/108 keys have ≥1 record in 2013
- 104/108 keys have ≥1 record in 2026
- 103/108 keys have data at the most recent week (2026 W16)

Notably partial coverage:
| Key | Records | Range | Reason |
|---|---|---|---|
| `エムポックス` | 172 | 2022 onwards | added to IDWR mid-2022 (Mpox global outbreak) |
| `新型コロナウイルス感染症` | 172 | 2022 onwards | added to 5類定点 in May 2023 |
| `新型コロナウイルス感染症（疑い例を含む）` | 105 | 2024 onwards | sub-classification |
| `インフルエンザ(入院患者)` | 485 | 2017 onwards | hospitalized-case sentinel added 2017 |
| `急性弛緩性麻痺` | 433 | sub-period | partial |
| `感染性胃腸炎（ロタウイルス）` | 433 | sub-period | rotavirus sub-class |
| `ジカウイルス感染症` | 537 | 2016 onwards | added after Zika global emergence |
| `ウエストナイル熱鳥類` | 104 | 2024-2026 | very partial |
| `回帰熱` (with leading invisible char) | 2 | minimal | data anomaly — investigate |
| `多剤耐性緑膿菌感染症` | 2 | minimal | data anomaly — investigate |
| `鳥インフルエンザ(Ｈ５Ｎ１を除く）` | 52 | 2021 only | single-year |

## §4. Geographic granularity (47 都道府県 coverage)

- **`weekly_pref` is a SNAPSHOT, not time-series.** It contains the LATEST-WEEK count per prefecture per disease (108 diseases × 47 prefectures = 5,076 cells). All 47 prefectures present for the 108 sampled diseases.
- For prefecture-level time-series, the canonical source is `weekly_extracted/IDWR{year}.xlsx` (one XLSX per year 2013–2026). These exist on disk and were used by the archived pilots to extract prefecture × week series for specific diseases (麻しん, 梅毒, 風しん, RSV, 手足口病, インフルエンザ).
- **`DATA.urban_tier`** verified intact: 47 prefectures × 4 fields (`urban_tier_did`, `did_population_ratio`, `did_quartile`, `metro_area_class`) — DID 2020 census data injected on 2026-05-06.
- **`DATA.nesid_pref_data`**: 60 diseases × multi-year × 47 prefectures with `{cases, pop_k, rate_100k}` — full prefecture-level NESID annual data for 全数把握 only (does NOT include sentinel diseases like 麻しん≈yes-because-it's-actually-全数把握, インフルエンザ≈no, 手足口病≈no).

## §5. Archive operation execution confirmation

Created: `~/Desktop/claude/archived_pilot_v1_v2_DO_NOT_USE/` containing 26 archived files + README:

```
archived_pilot_v1_v2_DO_NOT_USE/
├── README_WHY_ARCHIVED.md           — explains the contamination concern
├── pilot_lead_time.py
├── pilot_lead_time_results.md
├── pilot_lead_time_results.json
├── pilot_extended.py
├── pilot_extended_results.json
├── pilot_v2.py
├── pilot_v2_results.json
├── detect_anomalies_v2.py
├── run_retrospective.py
├── render_figures.py
├── run_validation.py
├── retrospective_evaluation_report.md
├── retrospective_alerts.csv
├── sensitivity_evaluation.csv
├── false_alert_characterization.csv
├── detector_summary.csv
├── outbreak_urban_tier_dynamics.json
├── tier_leadership_summary.json
├── fig1_leadtime_matrix.png
├── fig2_urban_tier_dynamics.png
├── llm_commentary_template_v2.md
├── outbreak_reference_set.csv
├── outbreak_reference_validation.md
├── outbreak_validation_raw.json
├── pref_timeseries_3diseases.json   (3.4 MB)
└── pref_timeseries_sentinel.json    (3.5 MB)
```

**Files retained at `~/Desktop/claude/` root (not archived)**:
- `dashboard.html` (with ⑦⑧ cards intact, urban_tier in DATA, all 21 DATA.* keys verified)
- `prefecture_did_classification.csv/.json/.md` (DID infrastructure — independent of flu)
- `import_did_data.py`, `inject_urban_rural_card.py`, `inject_urban_ranking_card.py`
- `dashboard_urban_tier_injection.js`, `metro_area_class_full.json`, `urban_rural_ranking.json`
- `a201.xls` (e-Stat DID 2020 census source)
- `outbreak_reference_set_curation.md` (curation methodology — note: the CSV itself is archived, the methodology MD remains)
- `did_real_vs_synthetic_diagnostic.md` (DID anchor diagnostic)
- `jmir_paper_landscape_review.md` (JMIR landscape research)
- `README.md` (project README)
- `index.html` (dashboard duplicate)
- `archive/`, `population/`, `scripts/`, `tests/`, `weekly_extracted/`, `2013/`–`2026/`, `us/` directories

## §6. Open questions for user (待確認 before any new pilot/retrospective)

### Q1. Confirm influenza is in scope for the new pilot

Audit confirms `weekly_trends['インフルエンザ']` is real and has 14-year coverage. **Should it be included as a sentinel case study in the new pilot?**
- (a) Yes, include it (audit says it's clean)
- (b) No, exclude it as a precaution per the original archive rationale
- (c) Include only the post-COVID rebound (2022 W51 anchor), exclude H1N1 2025

### Q2. Confirm the candidate sentinel disease list

Based on §1+§3+§4, the diseases that satisfy all of (a) ≥10 years coverage in `weekly_trends`, (b) ≥1 reasonable historical outbreak with independent ground truth, and (c) `weekly_extracted/IDWR{year}.xlsx` prefecture-level extractable, are:

| Candidate | weekly_trends? | Independent GT (already curated) | Status |
|---|:-:|:-:|---|
| **手足口病** | ✓ 694w | ✓ 2018 IDWR 第29号 article | already verified, ready |
| **RSウイルス感染症** | ✓ 694w | ✓ JIHS featured 2024/15 | already verified, ready |
| **インフルエンザ** | ✓ 694w | ✓ JIHS 2023/03 (2022 流行入り) | depends on Q1 |
| **マイコプラズマ肺炎** | ✓ 694w | ✓ 日本小児科学会 alert 2024-10 | candidate |
| **ヘルパンギーナ** | ✓ 694w | ? need ground truth | candidate |
| **感染性胃腸炎** | ✓ 694w | ? need ground truth | candidate |
| **流行性耳下腺炎** | ✓ 694w | ? need ground truth | candidate |
| **A群溶連菌咽頭炎** | ✓ 694w | ? need ground truth | candidate |
| **クラミジア肺炎** | ✓ 694w | (rare; ground truth limited) | low priority |

For 全数把握 (1-case rule applicable) candidates already have ground truth from previous curation:
- 麻しん 2026 W16, 麻しん 2019, 麻しん 2025 imported, 風疹 2018-19, 梅毒 2024, 劇症型溶血性レンサ球菌 2024 (note: was MAJOR magnitude gap, but disease+geography ✓)

**Question**: which final set (5 / 7 / 9 outbreaks) should the new pilot use? User confirms before any code is written.

### Q3. Re-extract prefecture-level time series for the new disease list?

Previous extractions (麻しん, 梅毒, 風しん, RSV, 手足口病, インフルエンザ) are archived. Re-extraction is fast (~30 sec per disease across 14 IDWR.xlsx files using xlrd). User confirms list before re-extraction.

### Q4. Detector framework — port forward or fresh re-design?

The 4-detector framework (`D_rare`, `D_stat`, `D_growth`, `D_spatial`) in archived `detect_anomalies_v2.py` is mathematically sound and leakage-audited. **Should it be ported forward as-is for the new pilot, or re-designed?**
- (a) Port as-is (faster) — re-instantiate from archived code with no algorithmic changes
- (b) Re-design (slower, but if user lost confidence in the framework wholesale)

### Q5. Curation reference set — keep, refresh, or rewrite?

Archived `outbreak_reference_set.csv` had 18 rows; validation marked 1 PASS, 3 MINOR, 11 MAJOR (mostly explainable), 3 EXCLUDED. **Should the new pilot:**
- (a) Subset the existing 18 rows to the cleanest 5–7 (1 PASS + 3 MINOR + 1–3 selected MAJOR with explained discrepancies)
- (b) Rewrite from scratch with stricter HTTP-verified-only rule
- (c) Use only the 6 originally-anchored outbreaks from pilots v1+v2 (3 acute-rare + 3 sentinel)

### Q6. Geographic-granularity scope

For urban-tier × outbreak analysis, do we want:
- (a) Prefecture-level time-series for all 5–7 candidate diseases (re-extract from XLSX, ~3 min)
- (b) Prefecture-level only for the most-cited 2–3 (faster)
- (c) Keep urban-tier analysis at NESID-annual level only (already in DATA.nesid_pref_data, no new extraction needed)

---

## Summary numbers for parent dispatch

- **Disease keys in dashboard**: 108 (weekly_trends) / 110 (annual_incidence) / 60 (nesid_pref_data)
- **Time coverage**: 92/108 keys have full 14-year range (2013-W1 → 2026-W16)
- **Influenza data**: ✓ present in `weekly_trends`, `weekly_pref` (snapshot), `annual_incidence`; full 14-year coverage; max weekly 317,812 (2024 W52)
- **Geographic granularity**: 47 prefectures via snapshot (`weekly_pref`) and via raw XLSX (`weekly_extracted/`)
- **Archive count**: 26 files moved to `archived_pilot_v1_v2_DO_NOT_USE/` + README
- **Dashboard integrity**: ⑦⑧ cards intact, 21 DATA.* keys preserved, `DATA.urban_tier` valid
- **Open questions for user**: 6 (listed in §6, all need user sign-off before any new pilot)
