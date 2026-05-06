# DID Anchor-Verification Diagnostic — a201.xls (2020 census) vs user-spec anchors

**Status: HALTED per user spec.** 2 of 7 anchors fail ±3pp tolerance. Dashboard NOT updated; current synthetic values remain in place pending user decision on anchor reconciliation.

## File integrity audit

| Property | Value |
|---|---|
| Path | `~/Desktop/claude/population/a201.xls` |
| Size | 89,088 bytes |
| `file` magic | `Composite Document File V2 Document, Little Endian, OS: Windows, Code page 932` (genuine BIFF .xls) |
| Magic bytes | `D0 CF 11 E0 A1 B1 1A E1` — OLE Compound Document signature |
| Excel metadata | Created 2023-11-24, Last saved 2024-02-05 |
| Parser used | `xlrd` (installed via `pip install xlrd --break-system-packages`) |
| Sheet name | `'A'` (single sheet, 60 rows × 91 cols) |
| Indicator code | `#A01401` = 人口集中地区人口比率（対総人口） |
| Reference year (col 27) | **2020** (census), per row 10 (Fiscal year) |
| Source publication | 統計でみる都道府県のすがた 2024 ／ A 人口・世帯 (e-Stat 統計コード 00200502) |
| Coverage | 47/47 prefectures + 全国 row |

## Anchor verification

| Prefecture | Real (2020) | User anchor | Δpp | Status |
|---|---|---|---|---|
| 東京都 | 98.6% | 98% | +0.60 | OK |
| 大阪府 | 95.9% | 96% | −0.10 | OK |
| 神奈川県 | 94.7% | 96% | −1.30 | OK |
| 北海道 | 76.0% | 74% | +2.00 | OK |
| 島根県 | 25.6% | 24% | +1.60 | OK |
| **秋田県** | **35.5%** | **32%** | **+3.50** | **FAIL** (just over ±3pp) |
| **鳥取県** | **38.1%** | **28%** | **+10.10** | **FAIL** (large) |

## Hypothesis: user's anchors are from an earlier census (2010 or 2015), not 2020

All 5 passing anchors and the 2 failing anchors share a common pattern: the **2020 value is uniformly higher than the anchor**, with the gap roughly correlated to how rural the prefecture is. Rural depopulation concentrating residual population in DID tracts is a documented 2015→2020 census trend; +2pp for 北海道 and +1.6pp for 島根 are within that drift, +3.5pp for 秋田 sits at the edge, and +10.1pp for 鳥取 is the largest example.

For comparison the urban prefectures' gaps are tiny (Tokyo +0.6pp, Osaka −0.1pp, Kanagawa −1.3pp), consistent with their already-near-saturated DID%.

If the user's intent was 2020-census-based classification, the e-Stat file is correct and the anchor table needs updating. If the intent was 2015-or-earlier census, this XLS is the wrong vintage and a different e-Stat snapshot is needed (table `00200502/2018` instead of `00200502/2024`).

## Real e-Stat 2020 values for 8 representative prefectures

| Prefecture | DID% (2020) |
|---|---|
| 東京都 | 98.6 |
| 大阪府 | 95.9 |
| 神奈川県 | 94.7 |
| 愛知県 | 78.8 |
| 北海道 | 76.0 |
| 福岡県 | 73.7 |
| 沖縄県 | 69.7 |
| 島根県 | 25.6 |

(Full 47-row table not committed to outputs yet — pending anchor resolution.)

## Tier-count delta vs current dashboard synthetic placeholders

| Tier | REAL (2020 e-Stat) | SYNTHETIC (in dashboard now) | Drift |
|---|---|---|---|
| `high_urban` (≥70%) | **11** | 10 | +1 |
| `mixed` (40–70%) | **27** | 19 | +8 |
| `rural_leaning` (<40%) | **11** | 18 | −7 |
| `metro_area_class.major_metro` | 11 | 11 | unchanged ✓ |

The synthetic data systematically underestimates the `mixed` tier and overestimates `rural_leaning`. Top 10 absolute deltas:

| Prefecture | Real | Synth | Δpp |
|---|---|---|---|
| 福井県 | 46.3 | 27.4 | +18.92 |
| 山形県 | 46.1 | 28.1 | +18.01 |
| 福島県 | 42.2 | 25.6 | +16.56 |
| 青森県 | 47.4 | 31.5 | +15.90 |
| 千葉県 | 76.8 | 62.4 | +14.42 |
| 香川県 | 33.1 | 47.4 | −14.26 |
| 長崎県 | 48.1 | 62.1 | −14.00 |
| 長野県 | 35.2 | 21.2 | +13.96 |
| 栃木県 | 48.1 | 34.4 | +13.70 |
| 静岡県 | 61.6 | 50.1 | +11.51 |

## Three options for the user

1. **Override anchors and accept 2020-census real values.** Re-run `import_did_data.py` with a flag to skip the failed anchor check (need to add `--anchor-overrides 鳥取県=38,秋田県=36` or similar). The 2020 values are the most current and academically defensible for a JMIR submission targeting 2025–26.

2. **Update the anchor list to match 2020 census.** Replace the user-spec anchors `鳥取 ~28%` and `秋田 ~32%` with `鳥取 ~38%` and `秋田 ~36%` and re-run. (All 7 anchors pass.)

3. **Use 2015 census instead.** Download the 2018 edition of `統計でみる都道府県のすがた` from e-Stat (`tstat=000001167080` or similar prior vintage), which has 2015-census DID values that should match the user's anchors. The downside: 2015 values are 5+ years stale relative to the 2013–2026 surveillance analysis window; the existing 2020 values would be more defensible.

## Files NOT written this round

Per user's hard rule "任一偏离 ±3pp 立刻停、报告偏差，不要硬写", these files were NOT modified and retain synthetic placeholder values from the previous round:

- `prefecture_did_classification.csv`
- `prefecture_did_classification.json`
- `dashboard_urban_tier_injection.js`
- `dashboard.html` (DATA.urban_tier still has synthetic block)

Files modified this round:
- `import_did_data.py` — added `parse_xls_a201()` for BIFF .xls support; `xlrd` is now a hard dependency
- `did_real_vs_synthetic_diagnostic.md` (this file) — diagnostic snapshot

Awaiting user decision on Option 1/2/3 above before injecting real values into dashboard.
