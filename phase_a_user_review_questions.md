# Phase A — User Review Gate

**Status: PAUSED at A4 per spec.** Phase B (4-detector retrospective + 2× urban-tier granularity comparison) will NOT begin until you sign off on the items below.

## TL;DR — what's clean and what needs you to look at

| Deliverable | Status | Action |
|---|---|---|
| A1: scripts_v3/ template setup | ✅ clean | none — 4 templates copied, archived originals intact |
| A2: prefecture × week timeseries (391K rows) | ✅ clean | none — 12/12 disease national-sum match dashboard |
| **A3: outbreak_reference_set_v3.csv** (13 rows) | ⚠️ **3 quality issues found** | **needs your decision** |
| A4: This document | ✅ ready | you read + answer Q1–Q4 |

## A3 Quality issues that I'm flagging honestly (not silently passing)

The agent claimed 100% HTTP-verified and 100% rule-compliant. **I spot-checked and found 3 violations** of the user-spec hard rules:

### Issue ❶ — Row #13 梅毒 uses tokyoweekender.com (English news blog) — **HARD RULE VIOLATION**

| Field | Value |
|---|---|
| `source_url_primary` | `https://www.tokyoweekender.com/japan-life/news-and-opinion/tokyo-battles-record-surge-in-syphilis-cases/` |
| HTTP status | 200 (verified) |
| Rule violated | "不准用：主流媒体单独作为来源（必须配合官方 press release）、Wikipedia、blogs" |

The user spec explicitly forbade mainstream news as sole source. Tokyo Weekender is an **English-language news blog**, also violating the "JIHS Japanese root only, no /en/" rule (this URL isn't even Japanese-government). **Reject and re-source from Tokyo IDSC + JIHS Q4 quarterly report (Japanese pages).**

### Issue ❷ — Row #6 ヘルパンギーナ cites a 手足口病 URL — **WRONG-DISEASE CITATION**

| Field | Value |
|---|---|
| `source_url_primary` | `https://www.niid.go.jp/niid/ja/hfmd-m/hfmd-idwrc/9017-idwrc-1929.html` |
| Article subject | 手足口病 (HFMD) — **not** ヘルパンギーナ |
| HTTP status | 200 (URL exists) |
| Rule violated | The cited document is about a different disease entirely. |

Same URL is correctly cited for row #2 (HFMD 2019). Using it for ヘルパンギーナ is a citation-correctness failure. **Re-source from a herpangina-specific JIHS or IASR article.**

### Issue ❸ — Row #3 RSV 2024 cites a 風しん URL — **WRONG-DISEASE CITATION**

| Field | Value |
|---|---|
| `source_url_primary` | `https://ojs.wpro.who.int/ojs/index.php/wpsar/article/view/697` |
| Article subject | Kanbayashi et al. **rubella** outbreak Osaka 2018-19 (correctly cited for row #11) |
| HTTP status | 200 (URL exists) |
| Rule violated | Cited paper is about 風しん, not RSV. |

The agent used the same URL for two different rows. Row #11 is correct; row #3 is wrong. **Re-source from JIHS featured 2024/15 (id-info.jihs.go.jp/surveillance/idwr/featured/2024/15/index.html — known HTTP 200 from prior session).**

### Issue ❹ — 8 of 13 rows have `total_cases = [unverified]` — soft fail

Agent acknowledged it could not extract a confirmed case count from the cited source for 8 rows. Per spec: "如果你不能 HTTP-verify a number, drop it from `total_cases` and write `[unverified]`" — so this technically followed the rule. **But:** without `total_cases`, we cannot do the ±20% magnitude cross-check that's required to enter Phase B retrospective.

Rows with `[unverified]`:
- #2 手足口病 2019, #3 RSV 2024, #4 インフル 2022, #5 マイコプラズマ 2024, #6 ヘルパンギーナ 2019, #7 感染性胃腸炎 2023-24, #9 A群溶連菌 2023-24, #11 風しん 2018-19

For each, the dashboard timeseries (now in `prefecture_week_timeseries.csv`) **can compute the actual outbreak-window cumulative**. We can backfill these — but who chooses the window endpoints? Options below in Q3.

## Questions for you (4 total)

### Q1 — Reject row #13 梅毒 (tokyoweekender) — yes / no?

(a) **Yes, reject** — agent re-curates with Tokyo IDSC + JIHS Japanese sources only (estimated 5 min for a research agent re-run on this single row)
(b) **Accept temporarily** — flag in docx Limitations as "secondary citation"; replace before submission
(c) **Drop the row entirely** — proceed Phase B with 12 outbreaks instead of 13

### Q2 — Re-source rows #3 (RSV) and #6 (ヘルパンギーナ) — yes / no?

(a) **Yes, re-source both** — agent re-curates from JIHS featured articles (RSV 2024/15 known HTTP 200; ヘルパンギーナ needs a IASR or JIHS herpangina-specific article)
(b) **Accept #3 RSV with prior-session-verified URL** (id-info.jihs.go.jp/surveillance/idwr/featured/2024/15/index.html — I have HTTP-verified this in earlier session) — drop #6 ヘルパンギーナ entirely
(c) **Drop both** — proceed with 11 outbreaks instead of 13

### Q3 — Backfill `[unverified]` total_cases — which method?

For 8 rows missing `total_cases`, options:
(a) **Compute from dashboard timeseries** — for each row, sum cases in window [reference_start_iso_week, peak_iso_week + 4 weeks] from `prefecture_week_timeseries.csv`. This is dashboard-self-consistent (passes ±20% trivially since it IS the dashboard data) but doesn't validate the outbreak existed externally. Honest framing: "outbreak existence verified via independent source per `independence_rationale`; magnitude reported as IDWR sum".
(b) **Re-curate to find each row's official count** — slower (5 min × 8 = 40 min), not all rows may have HTTP-verifiable totals.
(c) **Drop the magnitude check entirely** — accept curation as-is and let Phase B retrospective focus on lead-time only (sensitivity + start-week alignment, no magnitude cross-check).

### Q4 — Phase B start gating: do you want a final v3.1 cleaned curation before B starts?

(a) **Yes, clean first** — wait for me to redo Q1+Q2+Q3 actions, generate v3.1, you approve, then Phase B starts. Adds ~30-45 min.
(b) **Run Phase B on v3 as-is** — proceed with 13 (or 11) rows, document the citation issues in the retrospective limitations section.
(c) **Run Phase B on a subset** — e.g., the 4 rows that have BOTH (verified URL AND verified total_cases AND no citation issues): #1 手足口病 2018, #8 流行性耳下腺炎 2016, #10 咽頭結膜熱 2023-24, #12 麻しん 2026.

## Proposed answers (my recommendation)

If you want fastest GO without re-curation:
- Q1: (c) drop row #13 梅毒 (tokyoweekender unfixable in v3)
- Q2: (b) accept RSV #3 with my prior-verified URL substitution; drop #6 ヘルパンギーナ
- Q3: (a) backfill from `prefecture_week_timeseries.csv` (dashboard-self-consistent, honest framing)
- Q4: (a) wait for v3.1 cleaned

Result: 11 rows, all citations correct, all magnitudes computable, Phase B gate ready.

If you want strict and slow:
- Q1: (a) re-source 梅毒 row
- Q2: (a) re-source both
- Q3: (b) re-curate each total_cases
- Q4: (a) wait for v3.1

Result: 13 rows, ~45 min agent re-run, then Phase B.

## What's NOT done (per Phase A spec)

- 4-detector framework not re-implemented in scripts_v3/ (Phase B)
- No retrospective evaluation run (Phase B)
- No urban-tier × prefecture-week analysis (Phase B)
- No figures rendered (Phase B)
- No LLM commentary template work (Phase B)
- No docx draft (later phases)

All deliverables for Phase A are in `~/Desktop/claude/`:
- `scripts_v3/` — 4 template files (.../detect_anomalies_v2_v2_template.py etc.)
- `prefecture_week_timeseries.csv` — 391K rows
- `prefecture_week_timeseries_summary.md`
- `prefecture_week_timeseries_coverage.json`
- `outbreak_reference_set_v3.csv` (13 rows, ⚠️ with the issues above)
- `outbreak_reference_set_v3_curation.md` (29 KB narrative)
- `extract_prefecture_timeseries.py`
- `phase_a_user_review_questions.md` (this file)
