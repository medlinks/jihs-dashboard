# DOCX v1 Summary

`main_paper_draft_v1.docx` (49.6 KB) is the JMIR Public Health and Surveillance v1 draft. **A-route framing** (system success story); 12 outbreak retrospective + 2 live demos.

## Structure & word counts (approx, 4,164 total)

| Section | Words | Notes |
|---|---|---|
| Title page | 90 | [TBD] author/affiliation/correspondent |
| Abstract (structured) | 360 | Background / Objective / Methods / Results / Conclusions / Keywords |
| 1. Introduction | 470 | 4 paragraphs covering IDWR background, prior multi-detector work, framework motivation |
| 2. Methods (§2.1-2.7) | 1,420 | Data sources, 4-detector specs, disease class, urban-tier, ground truth, lead-time, live-demo protocol |
| 3. Results (§3.1-3.6) | 980 | Aggregate + complementarity + false-alert + urban-tier + 2 live demos |
| 4. Discussion (§4.1-4.5) | 540 | Findings, prior-work comparison, public-health implications, limitations, future work |
| 5. Conclusions | 130 | Headline + take-aways |
| Statements + References | 174 | CoI / Funding / Data / IRB / Acknowledgments / 12 references |

Target was 5-7K words. **Current is 4.2K** — under target. Reasons:
1. Tables 1+2 contribute table cell text rather than running prose
2. Section 4 (Discussion) is conservative — could be expanded with extra paragraphs on detector calibration tuning rationale and a deeper look at false-alert burden tradeoffs
3. Reference list is 12 entries vs JMIR's typical 40-60

**Recommendation**: expand sections §3.1-§3.6 results prose and §4.1-§4.4 discussion in next iteration to reach 6,000 words. Or accept 4,200-word manuscript as a "compact" submission since some JMIR papers run 4-5K.

## Figures referenced (8 total)

| Figure | File | Status | Used in §  |
|---|---|---|---|
| Figure 1 | `figures_v3/fig1_leadtime_heatmap.png` | re-rendered with CJK ✓ | §3.1 |
| Figure 2 | `figures_v3/fig2_urban_tier_dynamics.png` | available | §3.4 |
| Figure 3 | `figures_v3/fig3_detector_necessity.png` | re-rendered with CJK ✓ | §3.2 |
| Figure 4 | `figures_v3/fig4_false_alert_rate.png` | re-rendered with CJK ✓ | §3.3 |
| Figure 5 | `figures_v3/fig5_urban_tier_dual_granularity.png` | available | §3.4 |
| Figure 6 | `figures_v3/fig6_measles_2026_live_demo.png` | rendered with CJK ✓ | §3.5 |
| Figure 7 | `figures_v3/fig7_measles_2026_prefecture_heatmap.png` | rendered with CJK ✓ | §3.5 |
| Figure 8 | `figures_v3/fig8_rsv_2024_live_demo.png` | rendered with CJK ✓ | §3.6 |
| Figure 9 | `figures_v3/fig9_rsv_2024_prefecture_heatmap.png` | rendered with CJK ✓ | §3.6 |

Figures are referenced inline in docx with `[Figure N — caption. File: figures_v3/figN_*.png]` placeholders. **Embedding actual figure images into the docx is not done in v1**; the placeholder approach allows authors to drag-drop figures into final submission. To embed images programmatically, add `doc.add_picture(path, width=Inches(6))` calls in `build_docx_v1.py`.

## Tables included (2 of 4 planned)

- ✓ **Table 1** — 12-outbreak × 4-detector lead-time matrix (in §3.1, fully populated from `retrospective_results_v3.csv`)
- ✓ **Table 2** — False-alert rate by detector × class (in §3.3, from `false_alert_characterization_v3.csv`)
- [TBD] Table 3 — 47-prefecture urban_tier classification (supplement; data in `prefecture_did_classification.csv`)
- [TBD] Table 4 — Per-outbreak urban-tier dynamics (could extract from `outbreak_urban_tier_dynamics_v3.json`)

## Key numbers (all sourced from generated CSV/JSON, no hallucination)

- **Sensitivity**: 91.7% (11/12) — from `sensitivity_evaluation_v3.csv`
- **Median lead time**: +1 week
- **Mean lead time**: −0.73 weeks
- **Lead distribution**: [−15, −10, −1, −1, 0, 1, 2, 4, 4, 4, 4]
- **2026 measles W05 sustained**: from `measles_2026_weekly_simulation.csv`
- **2026 measles +11w vs JIHS W16**: confirmed in narrative
- **2024 RSV W17 sustained**: from `rsv_2024_milestones.json`
- **2024 RSV +2w vs anchor / −2w vs JIHS**: from `rsv_2024_milestones.json`
- **80% high_urban (measles 2026)**: from `measles_2026_live_demo.py` aggregation
- **47% high_urban (RSV 2024)**: from `rsv_2024_milestones.json` tier_totals
- **False-alert rates 0.000 / 0.529 / 0.231 / 0.548 sentinel**: from `false_alert_characterization_v3.csv` averages

## Reviewer-anticipated attack points (self-anticipation)

1. **n=12 outbreaks too few**: defended in Limitations §4.4(a) — original aspiration was 14, 8 were never properly curated. Mitigation: explicitly state this and propose 14-18 expansion in resubmission round.
2. **Median lead time +1w fails strict GO criterion**: defended in Discussion §4.1 — 7 of 11 detected outbreaks had lead ≥0w (timely or early); +1w is operationally useful. Could be reframed as "near-real-time detection" rather than "early warning".
3. **D_growth low hit rate (1/12)**: defended in §4.4(c) — its absolute floor calibration was conservative; tuning per disease (not done in v1) would improve hit rate. Mitigation: propose calibration sensitivity analysis as supplementary work.
4. **2023-24 norovirus undetected**: defended in §4.4(g) — single failure case explicitly named; syndromic-overlay proposed.
5. **No real LLM commentary benchmark**: defended in §4.4(f) and §4.5(1) — described as deterministic prototype, production deployment future work. Reviewer may push for at least one batch of human-evaluated LLM outputs; mitigation: produce 5-10 LLM samples in resubmission.
6. **Truncation-invariance only spot-tested**: defended via 4 test cases × 4 detectors = 16 OK results (Methods §2.6 cites). Reviewer might want full-grid randomized testing; supplementary.
7. **Boundary saturation in v3.1 v1 (now fixed)**: not currently mentioned in v1 docx. Should be added to §4.4 as honest disclosure of methodological iteration.

## [TBD] fields for user to complete before submission

1. **Title page**: Authors and affiliations; corresponding author name + email
2. **Title**: Confirm full title (currently includes "Real-Time Demonstration on the 2026 Measles and 2024 RSV Outbreaks" — RSV demo is mixed-results, may want to drop or hedge)
3. **Conflict of Interest**: every author's CoI statement
4. **Funding**: grant numbers / funder names; if none → "This research received no external funding"
5. **Data and Code Availability**: GitHub repo URL + dashboard deploy URL (currently [TBD CODE REPO URL] / [TBD DEPLOY URL])
6. **IRB / Ethics**: institution name + exemption confirmation date (recommended template language pre-written in docx)
7. **Acknowledgments**: collaborators, JIHS staff, reviewers
8. **References [TBD] expansion**: 12 currently; expand to 40-60 with HTTP-verified DOIs from `outbreak_reference_set_v3_curation.md` curation evidence pack
9. **Figure embedding**: drag-drop the 8 PNGs from `figures_v3/` into the docx (or modify `build_docx_v1.py` to use `doc.add_picture`)
10. **Supplementary material packaging**: bundle `prefecture_did_classification.csv`, `prefecture_week_timeseries.csv`, `outbreak_reference_set_v3.csv` as supplementary files

## What's NOT in v1 (deferred to v2)

- LLM commentary section (described as future work; no actual model outputs)
- Refinement 3 (per-tier ramp metric — Phase B leftover)
- 14-outbreak expanded curation (current 12)
- Embedded figures (placeholder text only)
- 40-60 references (current 12)
- Sub-supplementary breakdown of NESID reconciliation gap (referenced as parallel short paper)
- Live deployment URL (currently [TBD])

## File locations

- `~/Desktop/claude/main_paper_draft_v1.docx` — main draft
- `~/Desktop/claude/scripts_v3/build_docx_v1.py` — re-runnable builder (re-runs after data updates produce a fresh draft)
- `~/Desktop/claude/main_paper_draft_v1_summary.md` — this summary
- `~/Desktop/claude/figures_v3/fig{1..9}*.png` — all 8 figures (CJK-rendered correctly)
- `~/Desktop/claude/{retrospective_results,detector_complementarity,sensitivity_evaluation,false_alert_characterization}_v3.csv` — data sources cited in tables
- `~/Desktop/claude/outbreak_reference_set_v3.csv` — 12-outbreak curation
- `~/Desktop/claude/{measles_2026_weekly_simulation,rsv_2024_weekly_simulation}.csv` — live demo data
- `~/Desktop/claude/rsv_2024_milestones.json` + `~/Desktop/claude/{measles_2026,rsv_2024}_live_demo.md` — live demo narratives
