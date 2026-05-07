# archived_pilot_v1_v2_DO_NOT_USE — README

**Archived: 2026-05-06.** All files in this directory are previous pilot / retrospective / validation outputs that are now considered **contaminated and must not be reused**.

## Why archived

The user identified a credibility-blocking concern with pilot v2 and the subsequent retrospective:

1. **インフルエンザ data uncertainty.** Pilot v2 §6 used "Influenza 2022/W51 post-COVID rebound" as one of three sentinel-disease case studies, claiming D_growth detected the rebound +8 weeks before the official 流行入り declaration. This sensitivity number depended on the assumption that `DATA.weekly_trends['インフルエンザ']` exists in the user's dashboard. **That assumption was never independently audited.** If the dashboard does not contain seasonal influenza sentinel data, the +8-week claim is sourced from data that is either an external import or a synthetic placeholder — not the user's own pipeline.

2. **Curation row #15 (2025 H1N1) used un-verified training memory.** The reference set's reference_start = 2025-W40 / total_cases = 57,424 / source URL = MHLW press release was not HTTP-tested in the curation round. Combined with #1 above, this means the retrospective's "6/6 outbreaks detected with median +12.5 weeks lead time" headline includes at least 1 outbreak whose validity is not independently confirmable.

3. **Cascading contamination of derived outputs.** Once one of the six anchored outbreaks is suspect, all summary numbers built from the 6-outbreak grid are degraded:
   - `sensitivity_evaluation.csv` — sensitivity 6/6 = 100% may be 5/6 if インフル is dropped
   - `retrospective_evaluation_report.md` — GO/NO-GO verdict (median +12.5w) may shift to median +9w on 5 outbreaks
   - `outbreak_urban_tier_dynamics.json` — 1 of 6 panels (Influenza) may not reflect dashboard-internal data
   - `fig1_leadtime_matrix.png`, `fig2_urban_tier_dynamics.png` — visual outputs include the suspect row
   - `outbreak_reference_validation.md` — even the validation report itself confirmed #15 H1N1 had a 33× magnitude gap (1.85M dashboard vs 57K curation), unresolved

## Lesson captured for the restart

**Future pilots / retrospectives must FIRST audit dashboard data presence + time coverage + geographic granularity, and obtain user sign-off, BEFORE running any detection or evaluation.**

The new audit (`dashboard_data_audit.md` in the parent directory `~/Desktop/claude/`) lists every disease key actually present in the dashboard's embedded JSON, with explicit treatment of seasonal influenza. The user must confirm the audit before any new pilot/retrospective is started.

## Contents — what's archived

| File | Type | Was used for |
|---|---|---|
| `pilot_lead_time.py` / `pilot_extended.py` / `pilot_v2.py` | code | v1 + v2 detector implementations |
| `detect_anomalies_v2.py` / `run_retrospective.py` / `render_figures.py` | code | Production-port retrospective evaluator |
| `run_validation.py` | code | Curation cross-check (used the contaminated retrospective set as gold) |
| `pilot_lead_time_results.md` / `pilot_lead_time_results.json` | report+data | v1 lead-time results (3 acute outbreaks) |
| `pilot_v2_results.json` / `pilot_extended_results.json` | data | v2 sentinel pilot intermediate results |
| `retrospective_evaluation_report.md` / `retrospective_alerts.csv` / `sensitivity_evaluation.csv` / `false_alert_characterization.csv` / `detector_summary.csv` | report+data | Full retrospective output |
| `outbreak_urban_tier_dynamics.json` / `tier_leadership_summary.json` | data | Phase D urban-tier traces |
| `fig1_leadtime_matrix.png` / `fig2_urban_tier_dynamics.png` | figure | Lead-time + tier-dynamics visualizations |
| `llm_commentary_template_v2.md` | template | Urban-aware commentary (uses retrospective findings) |
| `outbreak_reference_validation.md` / `outbreak_validation_raw.json` | report+data | Curation cross-check report |
| `outbreak_reference_set.csv` | data | Curation reference set (the 18-row source) |
| `pref_timeseries_3diseases.json` / `pref_timeseries_sentinel.json` | data | Prefecture × week extracts (used by archived pilots) |

## Files NOT archived (still valid)

- `prefecture_did_classification.csv/.json/.md` — DID urban-tier data (independent of influenza issue)
- `import_did_data.py` / `dashboard_urban_tier_injection.js` — DID infrastructure
- `inject_urban_rural_card.py` / `inject_urban_ranking_card.py` — dashboard ⑦⑧ card scripts
- `urban_rural_ranking.json` / `metro_area_class_full.json` — urban-tier derived analysis
- `dashboard.html` — main dashboard with ⑦⑧ cards
- `jmir_paper_landscape_review.md` — JMIR paper landscape research
- `a201.xls` — official e-Stat 2020 census XLS source
- The short paper draft (in a separate session's outputs) is not affected

## Recovery procedure

If after audit + user sign-off it turns out:
- **Influenza data IS in dashboard** with adequate coverage → can re-promote the relevant pilot v2 / retrospective files back from this directory after re-running with verified data.
- **Influenza data is NOT in dashboard** → drop influenza from case studies, re-run retrospective on a smaller curated set (likely 5 outbreaks: 風疹 / 麻しん / RSV / HFMD / 梅毒). All numbers in archived files must be re-computed.

Either way, **do not directly cite files from this directory in the JMIR docx**. Re-derivation through the audited pipeline is required.
