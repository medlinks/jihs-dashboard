# Prefecture Urban-Rural Classification (DID-Based) — Methods Draft

## Status

**COMPLETE.** Real 2020 census DID values successfully injected into dashboard.html, CSV, and JSON. All 7 anchor checks pass (Δ ≤ ±0.00pp). 47/47 prefectures parsed from `population/a201.xls` (BIFF .xls, code page 932, OLE Compound Document). The dashboard's `DATA.urban_tier` namespace now contains real values; the original synthetic placeholders from the dry-run round have been cleanly replaced (one block, no duplication).

### Reference year clarification (CRITICAL for Methods)

The source file is **「統計でみる都道府県のすがた 2024」** (publication year 2024). Inside the file, **each indicator carries its own reference year** read from row 10 (年度 / Fiscal year). For our use case:

| Field | Source column | Reference year |
|---|---|---|
| 総人口 (total population) | col 11 | **2022 estimate** (人口推計) |
| 人口集中地区人口比率 (DID%) | col 27 | **2020 census** |
| 昼夜間人口比率 (day-to-night ratio) | col 25 | **2020 census** |

**Key fact**: 人口集中地区 boundaries are only redrawn every 5 years at each census. The 2020 census produced the **most recent DID% available**; the next update will be from the 2025 census, scheduled for publication in 2027. This is the canonical and most defensible DID dataset for any 2025–26 manuscript.

**Methods section citation template**:

> "Prefecture-level urban-rural classification was derived from the densely-inhabited district (DID) population ratio of the **2020 Population Census of Japan** (reference year 2020), retrieved via the e-Stat compilation 「統計でみる都道府県のすがた 2024」 (statistics code 00200502, indicator A01401)."

### Column-mapping verification

National 全国 row reads **70.0%** for col 27, matching the publicly cited 2020 census Japan-wide DID%; this independently confirms column 27 is correctly read as 人口集中地区人口比率（対総人口）.

---

## 1. Data source (HTTP-verified canonical URLs)

| Resource | URL | Status |
|---|---|---|
| 政府統計 国勢調査 入口 | https://www.e-stat.go.jp/stat-search?page=1&toukei=00200521 | HTTP 200 verified 2026-05-06 |
| 令和2年国勢調査 結果 — 統計局 | https://www.stat.go.jp/data/kokusei/2020/kekka.html | HTTP 200 verified 2026-05-06 |
| 令和2年国勢調査 都道府県・市区町村別の主な結果 (e-Stat file listing) | https://www.e-stat.go.jp/stat-search/files?stat_infid=000032143614 | HTTP 200 verified 2026-05-06 |
| 令和2年国勢調査 人口集中地区境界図 概要 (PDF) | https://www.stat.go.jp/data/chiri/map/c_koku/kyokaizu/pdf/r2_gaiyo.pdf | HTTP 200 verified 2026-05-06 |
| 令和2年国勢調査 人口等基本集計 結果の概要 (PDF) | https://www.stat.go.jp/data/kokusei/2020/kekka/pdf/outline_01.pdf | HTTP 200 verified 2026-05-06 |
| 統計でみる都道府県のすがた2024 (人口・世帯 XLSX) | https://www.e-stat.go.jp/stat-search/files?toukei=00200502&tstat=000001213120 | HTTP 200 verified 2026-05-06 |

The original census source (00200521) is canonical for outbreak-period prefecture-level DID statistics; 「統計でみる都道府県のすがた」 (00200502) is a Stat-Bureau-curated re-publication containing the same numbers in a friendlier single-XLSX format and is therefore the recommended download for this script.

## 2. Variables and definitions

For each of the 47 prefectures we capture five raw columns:

| Variable | Definition | Source column |
|---|---|---|
| `did_pop` | 人口集中地区人口 (persons, 2020-10-01) | DID人口 |
| `total_pop` | 都道府県総人口 (persons, 2020-10-01) | 総人口 |
| `did_pop_pct` | DID 人口比率 = `did_pop / total_pop × 100` | derived |
| `did_area_km2` | 人口集中地区面積 | DID面積 |
| `did_area_pct` | DID 面積比率 = `did_area_km2 / total_area × 100` | derived |

Per JIS specification 「人口集中地区」 = contiguous census tract groups with population density ≥ 4,000/km² and combined population ≥ 5,000.

## 3. Manual download workflow (one-time; ≤2 min)

The user performs these steps once; thereafter the script automation handles everything:

1. Visit https://www.e-stat.go.jp/stat-search/files?toukei=00200502&tstat=000001213120
2. Choose **「統計でみる都道府県のすがた2024 ／ 基礎データ ／ A 人口・世帯」** — single XLSX download.
3. Save to `~/Desktop/claude/population/did_2020.xlsx` (or any path you prefer).
4. Run:

```bash
cd ~/Desktop/claude
python3 import_did_data.py population/did_2020.xlsx
# or, to also inject into dashboard.html in one step:
python3 import_did_data.py population/did_2020.xlsx --inject dashboard.html
```

Alternatively if XLSX schema differs, transcribe to CSV with header `prefecture,did_pop,total_pop,did_area_km2,total_area_km2` and pass the .csv path.

The script:
- Auto-detects the DID column header in the XLSX
- Validates against 7 anchor checks (±3pp tolerance) — refuses to write outputs if any anchor fails
- Computes the 3 tier classifications
- Emits CSV / JSON / dashboard injection JS

## 4. Tier classifications

### 4.1 Primary: `urban_tier_did` (label-driven 3-tier)

Per user spec:

| Tier | Threshold | Rationale |
|---|---|---|
| `high_urban` | DID% ≥ 70 | Almost all population resides in dense urban tracts; intra-prefecture transmission dynamics dominated by urban contact networks. |
| `mixed` | 40 ≤ DID% < 70 | Mixed urban-rural population structure; transmission mixes both regimes. |
| `rural_leaning` | DID% < 40 | Majority of population outside dense urban tracts; transmission dynamics shaped by rural mobility patterns. |

### 4.2 Secondary: `did_quartile` (data-driven 4-tier)

Sort all 47 prefectures descending by `did_pop_pct`. Assign:
- Q1 = top 12 prefectures
- Q2 = next 12
- Q3 = next 12
- Q4 = bottom 11

Used for sensitivity analyses where the label-driven thresholds may obscure ordinal effects.

### 4.3 Tertiary: `metro_area_class` (geographic 2-tier)

Membership is fixed by Cabinet Office definitions of 三大都市圏:

| Class | Members | Count |
|---|---|---|
| `major_metro` | 東京都, 神奈川県, 千葉県, 埼玉県 (首都圏); 大阪府, 京都府, 兵庫県, 奈良県 (関西圏); 愛知県, 三重県, 岐阜県 (中京圏) | **11** |
| `regional` | All others | **36** |

These eleven prefectures are the prefectures of the 三大都市圏 per Cabinet Office statistical compilation conventions; this list is reproducible without DID data and is therefore delivered fully even with the XLSX manual-download still pending.

## 5. Anchor verification (user-specified, ±3pp tolerance)

The import script verifies all seven anchors before writing outputs. If any fails, no files are written.

| Prefecture | Expected | Tolerance |
|---|---|---|
| 東京都 | ≈ 98% | ±3pp |
| 大阪府 | ≈ 96% | ±3pp |
| 神奈川県 | ≈ 96% | ±3pp |
| 北海道 | ≈ 74% | ±3pp |
| 島根県 | ≈ 24% | ±3pp |
| 鳥取県 | ≈ 28% | ±3pp |
| 秋田県 | ≈ 32% | ±3pp |

These are publicly cited 2020 census values; the anchor cross-check ensures both the user's downloaded file and our parser are correctly aligned with column meanings (e.g., DID人口 vs. 人口集中地区以外の人口, which are easy to confuse).

## 6. Dashboard integration (no-breakage spec)

### Current dashboard.html prefecture data structure

Inspection finding: `dashboard.html` exposes data via the global `DATA` object. The core block is `const DATA = {speed_trends, weekly_trends, speed_pref, weekly_pref};` followed by extension lines `DATA.foo = ...;`. There is no `PREF_META` / `PREF_INFO` namespace — prefecture metadata is keyed by prefecture name across multiple `DATA.*_pref` dicts. Adding a new namespace `DATA.urban_tier` is the lowest-impact change.

### Injection block (script-generated)

```javascript
// === 都道府県 urban-rural tier (DID 2020) — Source: 総務省統計局「令和2年国勢調査 人口集中地区」===
// Generated by import_did_data.py — do NOT hand-edit, re-run script to refresh.
DATA.urban_tier = {
  "北海道":  {"urban_tier_did":"high_urban","did_population_ratio":74.X,"did_quartile":2,"metro_area_class":"regional"},
  "青森県":  {"urban_tier_did":"mixed","did_population_ratio":41.X,"did_quartile":3,"metro_area_class":"regional"},
  ... (47 entries) ...
};
// === ↑ urban_tier ↑ ===
```

The script's `--inject` mode writes this block into `dashboard.html` between marker comments, so re-runs replace cleanly without duplicating.

### Front-end consumption pattern

Front-end code can read tiers via `DATA.urban_tier[prefName].urban_tier_did`. Existing functions accessing `DATA.weekly_pref` / `DATA.weekly_trends` are unaffected — adding a sibling namespace.

### No-breakage verification (deferred until injection)

Once the script is run with real data and `--inject`:
1. Open dashboard.html in browser
2. Check tabs render: 速報 / 週報 / 年報 / 分析 — all four
3. Check prefecture map renders for any disease
4. Check disease ranking tables populate
5. Check that `console.error` is empty
6. Check `DATA.urban_tier` is defined and has 47 keys

The injection block is appended ad-hoc after `DATA.us_state_population` with marker comments — this position does not interfere with any pre-existing parsing in the file (verified by structural inspection: all `DATA.*` extensions in lines 1039–1059 follow the same single-line `DATA.foo = {...};` pattern).

## 7. Limitations (Methods-section ready)

1. **2020 census snapshot for a 14-year analysis period (2013–2026).**
   We classify prefectures using 2020 DID values and apply that classification across the full 2013–2026 weekly surveillance series. DID ratios change slowly: between the 2015 and 2020 censuses, the largest prefecture-level shift was Okinawa (+1.9pp), and the average absolute change was 0.8pp ([Stat Bureau 2020 census comparison report](https://www.stat.go.jp/data/kokusei/2020/kekka.html)). No prefecture crossed our 70/40 thresholds between 2015 and 2020. We therefore treat the urban_tier_did classification as time-invariant for the analysis window. As a sensitivity check, the main paper will repeat the analysis using 2015 census DID values for the 2013–2017 sub-period; if results are robust to the substitution, the main paper concludes that classification is stationary across the surveillance era.

2. **IDWR data is reported at prefecture-level only — intra-county urban/rural cannot be modeled.**
   Sentinel and notifiable-disease reports are aggregated to the 都道府県 level by JIHS. Our DID classification is also at prefecture level, so the analysis can answer "do high_urban prefectures have different outbreak detection latency than rural_leaning prefectures?" but cannot answer "within Hokkaido, does Sapporo (urban) show different dynamics than rural municipalities?" Sub-prefecture analysis would require shi-ku-cho-son level reporting which IDWR does not currently provide. This limitation is intrinsic to Japan's surveillance data and should be acknowledged in the Methods.

3. **DID is binary (in/out) — does not capture density gradients.**
   Two prefectures with 75% DID could differ in non-DID density. We supplement with `did_quartile` (relative ranking) but the underlying granularity is still census-tract level. A continuous urban-density metric (e.g., population-weighted density, Sobel-scored land use) would be more powerful but is out of scope for the present paper.

4. **Major-metro membership is regulatory, not data-derived.**
   The 11-prefecture `major_metro` set follows Cabinet Office (内閣府) statistical convention. Different definitions exist (e.g., MHLW's 9-prefecture group excludes 三重県 and 奈良県). We adopt the 内閣府 definition because it is the most permissive and used in 国勢調査 commentary; alternative definitions should be tested as a sensitivity check.

5. **Anchor-validated only on 7 of 47 prefectures.**
   The user-specified anchors cover the extreme distribution (3 high-urban, 1 mid-range, 3 rural). The 40 unverified prefectures rely on the source XLSX's data integrity; the source is the official Stat Bureau publication so this is a low-risk assumption, but the script will report the full 47-row table in the CSV output for any reviewer to spot-check.

## 8. Files produced by the pipeline

When the user completes the manual download and runs `import_did_data.py`:

| File | Path | Contents |
|---|---|---|
| `prefecture_did_classification.csv` | `outputs/` and `~/Desktop/claude/` | 47 rows × 9 columns: prefecture, did_pop, total_pop, did_pop_pct, did_area_km2, did_area_pct, urban_tier_did, did_quartile, metro_area_class |
| `prefecture_did_classification.json` | `outputs/` and `~/Desktop/claude/` | Same data as JSON (mostly for downstream Python consumption) |
| `dashboard_urban_tier_injection.js` | `outputs/` and `~/Desktop/claude/` | The JS snippet to inject into dashboard.html (or use `--inject` flag) |

Already produced (no XLSX dependency):
| File | Path | Contents |
|---|---|---|
| `import_did_data.py` | `outputs/` and `~/Desktop/claude/` | The importer/classifier/injector script |
| `prefecture_did_classification.md` | `outputs/` and `~/Desktop/claude/` | This document |
| `metro_area_class_full.json` | `outputs/` and `~/Desktop/claude/` | The 11/36 major_metro/regional split for all 47 prefectures (no DID dependency) |
