# Methods (extended) — Quantifying the discrepancy between weekly aggregate IDWR counts and annual NESID reports for notifiable diseases in Japan, 2024

This document is the extended, machine-traceable methodology for the JMIR short paper. It contains the data sources, ISO-week-to-calendar-year alignment rules, computation formulas, and the exact disease list used in the analytic table.

## 1. Data sources

| Source | URL (HTTP-verified) | Use in this paper |
|---|---|---|
| JIHS — IDWR Annual Report 2024 (感染症発生動向調査事業年報 2024) | https://id-info.jihs.go.jp/surveillance/idwr/annual/2024/index.html | Source of the **NESID 2024 annual** counts (final, post-reconciliation totals released 2026-03-02). |
| JIHS — IDWR landing page and weekly PDFs (2024 weeks 1–52) | https://id-info.jihs.go.jp/surveillance/idwr/index.html | Source of the **IDWR weekly** aggregate counts. The 52 weekly PDFs for ISO weeks 2024-W01 through 2024-W52 were extracted into `weekly_extracted/IDWR2024.xlsx` (per-disease worksheet, 都道府県 × 第X週 layout, with the 総数 row giving the national weekly count). |
| JIHS — Notifiable disease form filling guide (届出票記入時のお願い、注意点) | https://id-info.jihs.go.jp/surveillance/idwr/guidelines/how-to-fill-out-notifiable-disease-surveillance-form/index.html | Defines case-definition fields used by reporting physicians (発病年月日, 診断年月日, 感染地域). |
| JIHS — Notification quality improvement guideline 2025 | https://id-info.jihs.go.jp/surveillance/idwr/guidance/how-to-improve-the-quality-of-notification/guideline2025dc.pdf | Describes data-quality control and post-publication corrections. |
| MHLW — Infectious Diseases Control Law (感染症法) classification & timelines | https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/kenkou/kekkaku-kansenshou/kekkaku-kansenshou11/01.html | Statutory definition of Class I–V notifiable diseases and reporting timelines (Class I/II/III/IV: directly/within 24 h; Class V "all-case" diseases: within 7 days, with measles and a small subset within 24 h). |

Note on JIHS URL discipline: only the Japanese root (`id-info.jihs.go.jp`) is used; English `/en/` paths are unreliable.

## 2. ISO week ↔ calendar year alignment

The IDWR uses the official 厚生労働省 reporting-week calendar (報告週対応表), which in 2024 corresponds to ISO 8601 weeks W01 through W52 (calendar 2024 has 52 ISO weeks; the first week containing Thursday 4 January is W01). All 52 weekly PDFs were obtained and aggregated.

The NESID annual report covers the calendar year 2024 (1 January – 31 December 2024) by **diagnosis week (診断週)**, not by report transmission date. Late reports — that is, cases diagnosed in 2024 but reported (届出) by physicians or transmitted by prefectures after the publication of the W52 weekly tally — are added to the diagnosis week to which they belong, increasing the annual count above the running W01–W52 sum.

We therefore expect *N_annual ≥ N_weekly_sum* for diseases with non-trivial reporting lag, and the gap is interpretable as the **delayed-reporting backfill** for that disease in 2024, plus any duplicate-removal or case-classification adjustments.

## 3. Eligible disease set (analytic n = 49)

Inclusion criteria:
1. Listed in the NESID Class I–V notifiable (全数把握) full-count categories — 88 diseases in the NESID 2024 annual workbook (Syu_4_1.xlsx).
2. Has a worksheet in the IDWR 2024 weekly Excel (107 worksheets) — i.e. a published weekly time series.
3. Has at least one case in *both* the NESID annual count and the IDWR weekly sum (excludes the long tail of zero-zero exotic Class I diseases such as Ebola, Lassa, plague, smallpox, etc., which had zero cases in 2024).
4. Has 52 weeks of weekly data.

49 diseases meet all four criteria. The full 88-disease NESID list with match status, including the 39 zero/non-matched diseases, is in `short_paper_underreporting_data.csv`.

## 4. Computation

For each eligible disease *d*:

- **N_annual(d)** = `nesid_2024.json → notifiable[d].prefectures.全国.総数.total`
- **N_weekly(d)** = ∑ over weeks 1..52 of `weekly_extracted/IDWR2024.xlsx[d]` row 総数, ignoring blank cells.
- **abs_discrepancy(d)** = N_annual(d) − N_weekly(d)
- **rel_underreport_pct(d)** = (N_annual − N_weekly) / N_annual × 100  — share of NESID-confirmed cases not yet captured by W52
- **rel_uplift_pct(d)** = (N_annual − N_weekly) / N_weekly × 100  — uplift the annual report adds to the running weekly cumulative count

Both relative measures are reported in the table; we use uplift % as the headline ranking variable because it most directly answers the practical question "by what percentage does the published weekly cumulative under-state the eventual annual figure?"

## 5. Reference-value verification

Two reference values were stated by the user before computation, both reproduced exactly:

| Disease | N_annual | N_weekly | abs | uplift % | underreport % |
|---|---|---|---|---|---|
| 梅毒 (syphilis) | 14,829 | 9,201 | +5,628 | **+61.17 %** | 37.95 % |
| 結核 (tuberculosis) | 16,240 | 12,403 | +3,837 | **+30.94 %** | 23.63 % |

These values match the dashboard project's PROJECT_CONTEXT.md (recorded 2026-04-17) to the unit, confirming both data extraction pipelines (PDF → Excel and NESID Excel → JSON) are stable.

## 6. Outlier interpretation framework

Diseases with |uplift %| > 25 % were treated as outliers requiring mechanistic discussion. Candidate mechanisms (each grounded in the cited official documentation, not speculation):

- **Reporting timeline (Class V vs Class I-IV)** — Class V diseases are reported by clinicians within 7 days of diagnosis (and not within 24 hours, as for Class I-IV); the JIHS form-filling guide and MHLW classification page both state this. The uplift is concentrated in Class V diseases (e.g. syphilis, CJD, amebic dysentery, AFP, cryptosporidiosis, disseminated cryptococcosis, viral hepatitis (other), VRE, CRE infection), consistent with a longer clinician-to-public-health-centre lag.
- **Diagnosis-week vs transmission-date assignment** — NESID assigns each case to its 診断週 (diagnosis week), but a case diagnosed in (e.g.) week 50 but transmitted in February 2025 is added to W50 in the annual report yet is missing from the W01–W52 weekly sum that was published in early January 2025.
- **Annual deduplication and reclassification** — the JIHS quality improvement guideline 2025 documents post-publication 訂正 (correction) procedures, including duplicate removal and case-classification revision.
- **Reverse case (麻しん, measles, uplift = −4.3 %)** — measles is a Class V disease with a 24-hour reporting requirement and is subject to active enhanced surveillance; weekly counts can briefly exceed the annual count when initial provisional cases are subsequently reclassified or deduplicated, producing a negative uplift.

## 7. Limitations of this short-paper analysis

- Single calendar year (2024). Multi-year cohort analysis is left to a longer companion study.
- We do not have line-list access to the NESID database; we use the publicly released aggregate counts from JIHS only.
- We do not separate the relative contribution of "late reports" vs "post-hoc deduplication" — both move the count, but in opposite directions, and the publicly released aggregate figures combine them.

## 8. Files produced

- `short_paper_underreporting_data.csv` — full 88-disease NESID list with match status and discrepancy metrics for the 49 analytic diseases.
- `short_paper_underreporting_analytic.json` — same data in JSON form.
- `short_paper_figure1.png` — horizontal bar chart, 33 diseases with NESID annual ≥ 20 (sample-size cutoff to reduce ratio noise).
- `short_paper_underreporting.docx` — JMIR short-paper draft.
- `short_paper_underreporting_methods.md` — this document.
