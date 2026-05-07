"""Phase B+C+D retrospective evaluator.

Runs detect_anomalies_v2 on:
  Phase B — 6 anchored outbreaks (sensitivity + lead time per detector)
  Phase C — 108 diseases × 14 years for false-alert characterization
              (national-level only; prefecture-level grid feasible only
              for the 6 outbreaks where pref_ts data exists)
  Phase D — urban-tier dynamics for the 6 outbreaks (weekly tier-incidence)

Outputs:
  retrospective_alerts.csv          — full alert grid (6 outbreaks × all weeks ±26w × 4 detectors)
  detector_summary.csv              — counts by detector × disease class
  sensitivity_evaluation.csv        — sensitivity / lead time per outbreak × detector
  false_alert_characterization.csv  — alerts/year/disease outside outbreak windows
  outbreak_urban_tier_dynamics.json — tier-stratified weekly trace for 6 outbreaks
"""
from __future__ import annotations
import json, csv, sys, math
from pathlib import Path
sys.path.insert(0, '/sessions/cool-clever-goldberg/mnt/outputs')
import detect_anomalies_v2 as v2

# ── Paths ───────────────────────────────────────────────────────────────────
OUT = Path('/sessions/cool-clever-goldberg/mnt/outputs')
DASH_DATA   = Path('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json')
PREF_SENT   = OUT / 'pref_timeseries_sentinel.json'
PREF_3DIS   = OUT / 'pref_timeseries_3diseases.json'
DID_FILE    = OUT / 'prefecture_did_classification.json'

# ── Reference outbreaks (combined v1 + v2 curation) ────────────────────────
REFERENCE_OUTBREAKS = {
    # pilot v1 (acute rare/全数把握)
    "梅毒_2024":   {"idwr_key":"梅毒",   "year":2024, "week": 1, "tier":"silver", "category":"acute_rare"},
    "麻しん_2026": {"idwr_key":"麻しん", "year":2026, "week": 5, "tier":"b",       "category":"acute_rare"},
    "風疹_2018":   {"idwr_key":"風しん", "year":2018, "week":30, "tier":"c",       "category":"acute_rare"},
    # pilot v2 (sentinel)
    "RSV_2024":    {"idwr_key":"RSウイルス感染症", "year":2024, "week":13, "tier":"c", "category":"sentinel"},
    "HFMD_2018":   {"idwr_key":"手足口病",        "year":2018, "week":29, "tier":"c", "category":"sentinel"},
    "Influenza_2022": {"idwr_key":"インフルエンザ", "year":2022, "week":51, "tier":"c", "category":"sentinel"},
}

LEAD_WINDOW = 26  # ±26 weeks around anchor

def load():
    with open(DASH_DATA) as f: dash = json.load(f)
    pref_ts = {}
    if PREF_SENT.exists():
        with open(PREF_SENT) as f: pref_ts.update(json.load(f))
    if PREF_3DIS.exists():
        with open(PREF_3DIS) as f: pref_ts.update(json.load(f))
    with open(DID_FILE) as f: did = json.load(f)
    urban_tier_map = {p: did[p]['urban_tier_did'] for p in did}
    return dash, pref_ts, urban_tier_map

# ── Phase B: Sensitivity + lead time per (outbreak, detector) ──────────────
def phase_b_sensitivity_lead_time(dash, pref_ts, utm):
    rows_alert_grid = []
    rows_sensitivity = []
    print('\n=== Phase B — Sensitivity & lead time ===\n')
    print(f"{'Outbreak':<18} {'Detector':<11} {'Anchor':<11} {'1stAlert':<11} {'Sev':<7} {'Lead(w)':>7}")
    print('-'*70)
    for label, gt in REFERENCE_OUTBREAKS.items():
        idwr = gt['idwr_key']
        if idwr not in dash['weekly_trends']: continue
        ws = dash['weekly_trends'][idwr]
        ps = pref_ts.get(idwr, {})
        ref_y, ref_w = gt['year'], gt['week']
        weeks = v2.weeks_in_window(ws, ref_y, ref_w, LEAD_WINDOW)

        # Run all detectors at every week in window — record per-detector severity
        det_severity = {d: {} for d in ('D_rare','D_stat','D_growth','D_spatial','combined')}
        for y, w in weeks:
            res = v2.all_detectors(idwr, ws, ps, y, w, utm)
            det_severity['D_rare'][(y,w)]    = res['D_rare']
            det_severity['D_stat'][(y,w)]    = res['D_stat']
            det_severity['D_growth'][(y,w)]  = res['D_growth']
            sp = res['D_spatial']
            det_severity['D_spatial'][(y,w)] = sp.get('flat') if isinstance(sp, dict) else sp
            det_severity['combined'][(y,w)]  = v2.combined_severity(res)
            rows_alert_grid.append({
                'outbreak': label, 'idwr_key': idwr,
                'year': y, 'week': w,
                'D_rare':    det_severity['D_rare'][(y,w)] or '',
                'D_stat':    det_severity['D_stat'][(y,w)] or '',
                'D_growth':  det_severity['D_growth'][(y,w)] or '',
                'D_spatial': det_severity['D_spatial'][(y,w)] or '',
                'combined':  det_severity['combined'][(y,w)] or '',
            })

        # First sustained alert per detector
        for det in ('D_rare','D_stat','D_growth','D_spatial','combined'):
            sev_dict = det_severity[det]
            res = v2.first_sustained_alert(lambda yy, ww: sev_dict.get((yy,ww)), weeks)
            if res:
                ay, aw, sev = res
                lead = v2.lead_weeks(ref_y, ref_w, ay, aw)
                detected = True
            else:
                ay, aw, sev, lead, detected = None, None, None, None, False
            rows_sensitivity.append({
                'outbreak': label, 'idwr_key': idwr,
                'tier': gt['tier'], 'category': gt['category'],
                'detector': det,
                'ref_year': ref_y, 'ref_week': ref_w,
                'detected': detected,
                'first_alert_year':  ay,
                'first_alert_week':  aw,
                'severity':          sev,
                'lead_weeks':        lead,
            })
            ay_s = f'{ay}/W{aw}' if ay else '-'
            sev_s = sev or '-'
            lead_s = f'{lead:+d}' if lead is not None else '-'
            print(f'{label:<18} {det:<11} {ref_y}/W{ref_w:<5} {ay_s:<11} {sev_s:<7} {lead_s:>7}')
        print()
    return rows_alert_grid, rows_sensitivity

# ── Phase C: National-level false-alert characterization ───────────────────
def phase_c_false_alert_rate(dash, pref_ts, utm):
    """For each disease × year, count sustained alerts OUTSIDE any anchored
       outbreak ±26w window. Stratify by detector. national-level only."""
    print('\n=== Phase C — False-alert rate (national-level, all 108 diseases) ===\n')
    # Build exclusion mask: set of (year, week) that are within ±26w of any anchor
    excluded = set()
    for label, gt in REFERENCE_OUTBREAKS.items():
        ref_y, ref_w = gt['year'], gt['week']
        for dy in range(-LEAD_WINDOW, LEAD_WINDOW + 1):
            ay = ref_y + (ref_w + dy - 1) // 52
            aw = ((ref_w + dy - 1) % 52) + 1
            excluded.add((gt['idwr_key'], ay, aw))

    rows = []
    diseases_processed = 0
    for disease, ws in dash['weekly_trends'].items():
        # No prefecture data needed for this phase (D_spatial requires it but is skipped if missing)
        ps = pref_ts.get(disease, {})
        # Walk every week chronologically and count sustained alerts per detector
        weeks_chrono = sorted(set((r['year'], r['week']) for r in ws if r.get('year') and r.get('week')))
        det_streak = {d: 0 for d in ('D_rare','D_stat','D_growth','D_spatial','combined')}
        det_alerts_outside = {d: 0 for d in ('D_rare','D_stat','D_growth','D_spatial','combined')}
        det_alerts_total = {d: 0 for d in ('D_rare','D_stat','D_growth','D_spatial','combined')}
        for y, w in weeks_chrono:
            in_window = (disease, y, w) in excluded
            res = v2.all_detectors(disease, ws, ps, y, w, utm)
            det_sev = {
                'D_rare': res['D_rare'], 'D_stat': res['D_stat'],
                'D_growth': res['D_growth'],
                'D_spatial': res['D_spatial'].get('flat') if isinstance(res['D_spatial'], dict) else res['D_spatial'],
                'combined': v2.combined_severity(res),
            }
            for det, sev in det_sev.items():
                if sev in ('medium','high'):
                    det_streak[det] += 1
                    if det_streak[det] == v2.SUSTAINED_K:
                        det_alerts_total[det] += 1
                        if not in_window:
                            det_alerts_outside[det] += 1
                else:
                    det_streak[det] = 0
        is_full_report = disease in v2.FULL_REPORT_DISEASES
        n_years = max(1, len(weeks_chrono) // 52)  # crude
        for det in det_alerts_total:
            rows.append({
                'disease': disease,
                'disease_class': '全数把握' if is_full_report else 'sentinel/その他',
                'detector': det,
                'sustained_alerts_total': det_alerts_total[det],
                'sustained_alerts_outside_window': det_alerts_outside[det],
                'n_years_covered': n_years,
                'alerts_per_year': round(det_alerts_outside[det] / n_years, 3),
            })
        diseases_processed += 1
        if diseases_processed % 30 == 0:
            print(f'  ...processed {diseases_processed}/{len(dash["weekly_trends"])}')
        # Reset cache to bound memory
        if diseases_processed % 20 == 0:
            v2._LUT.clear(); v2._ZMAD_CACHE.clear()
    print(f'  Done — {diseases_processed} diseases.')
    return rows

# ── Phase D: Urban-tier dynamics ───────────────────────────────────────────
def phase_d_urban_tier_dynamics(dash, pref_ts, utm):
    """For each of 6 outbreaks: compute weekly tier-stratified incidence
       around ±26 weeks of anchor. Export JSON for later figure rendering."""
    print('\n=== Phase D — Urban-tier dynamics ===\n')
    out = {}
    for label, gt in REFERENCE_OUTBREAKS.items():
        idwr = gt['idwr_key']
        ps = pref_ts.get(idwr)
        if not ps:
            print(f'  {label} ({idwr}): no prefecture data — skip')
            continue
        ref_y, ref_w = gt['year'], gt['week']
        # Group prefectures by tier
        tier_prefs = {'high_urban': [], 'mixed': [], 'rural_leaning': []}
        for pref in ps:
            if pref == '総数': continue
            tier = utm.get(pref)
            if tier in tier_prefs: tier_prefs[tier].append(pref)
        # Weeks in window
        sample_pref_ts = next(iter(ps.values())) if ps else []
        # Use union of all weeks
        all_weeks = set()
        for s in ps.values():
            for r in s:
                if r.get('year') and r.get('week'):
                    dist = (r['year'] - ref_y) * 52 + (r['week'] - ref_w)
                    if -LEAD_WINDOW <= dist <= LEAD_WINDOW:
                        all_weeks.add((r['year'], r['week']))
        weeks_sorted = sorted(all_weeks)

        # For each week × tier compute total cases & total population (using static tier composition)
        traces = {'high_urban': [], 'mixed': [], 'rural_leaning': [], 'all': []}
        for y, w in weeks_sorted:
            tier_cases = {'high_urban': 0, 'mixed': 0, 'rural_leaning': 0}
            tier_pref_count = {'high_urban': 0, 'mixed': 0, 'rural_leaning': 0}
            total = 0
            for tier, prefs in tier_prefs.items():
                for p in prefs:
                    v = v2.value_at(ps[p], y, w)
                    if v is not None:
                        tier_cases[tier] += v
                        tier_pref_count[tier] += 1
                        total += v
            for tier in ('high_urban', 'mixed', 'rural_leaning'):
                traces[tier].append({'year': y, 'week': w, 'cases': tier_cases[tier],
                                      'n_active_pref': tier_pref_count[tier]})
            traces['all'].append({'year': y, 'week': w, 'cases': total})
        out[label] = {
            'idwr_key': idwr, 'ref_year': ref_y, 'ref_week': ref_w,
            'tier_prefs': tier_prefs,
            'traces': traces,
        }
        print(f'  {label}: {len(weeks_sorted)} weeks × 3 tiers extracted')
    return out

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    dash, pref_ts, utm = load()
    print(f'Loaded {len(dash["weekly_trends"])} diseases, '
          f'{len(pref_ts)} with prefecture time-series, '
          f'{len(utm)} prefectures with urban_tier.')

    # Phase B
    grid, sens = phase_b_sensitivity_lead_time(dash, pref_ts, utm)
    with open(OUT/'retrospective_alerts.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(grid[0].keys()))
        writer.writeheader(); writer.writerows(grid)
    with open(OUT/'sensitivity_evaluation.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(sens[0].keys()))
        writer.writeheader(); writer.writerows(sens)
    print(f'Saved: retrospective_alerts.csv ({len(grid)} rows), sensitivity_evaluation.csv ({len(sens)} rows)')

    # Phase D before C (lighter, gives tier traces immediately)
    dyn = phase_d_urban_tier_dynamics(dash, pref_ts, utm)
    with open(OUT/'outbreak_urban_tier_dynamics.json', 'w', encoding='utf-8') as f:
        json.dump(dyn, f, ensure_ascii=False, indent=2)
    print(f'Saved: outbreak_urban_tier_dynamics.json ({len(dyn)} outbreaks)')

    # Phase C — slow loop, do last
    fa = phase_c_false_alert_rate(dash, pref_ts, utm)
    with open(OUT/'false_alert_characterization.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(fa[0].keys()))
        writer.writeheader(); writer.writerows(fa)
    print(f'Saved: false_alert_characterization.csv ({len(fa)} rows)')

    # Detector summary table
    summary = {}
    for r in fa:
        key = (r['detector'], r['disease_class'])
        if key not in summary:
            summary[key] = {'detector': r['detector'], 'disease_class': r['disease_class'],
                            'n_diseases': 0, 'total_alerts_outside_window': 0, 'sum_alerts_per_year': 0.0}
        summary[key]['n_diseases'] += 1
        summary[key]['total_alerts_outside_window'] += r['sustained_alerts_outside_window']
        summary[key]['sum_alerts_per_year'] += r['alerts_per_year']
    summary_rows = []
    for v in summary.values():
        v['mean_alerts_per_year'] = round(v['sum_alerts_per_year'] / max(1, v['n_diseases']), 3)
        del v['sum_alerts_per_year']
        summary_rows.append(v)
    with open(OUT/'detector_summary.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader(); writer.writerows(summary_rows)
    print(f'Saved: detector_summary.csv ({len(summary_rows)} rows)')

    print('\n=== Summary table ===')
    print(f'{"Detector":<11} {"Class":<18} {"N_dis":>6} {"Alerts_outside":>16} {"Avg/yr/dis":>12}')
    print('-'*70)
    for r in sorted(summary_rows, key=lambda r: (r['detector'], r['disease_class'])):
        print(f'{r["detector"]:<11} {r["disease_class"]:<18} {r["n_diseases"]:>6} '
              f'{r["total_alerts_outside_window"]:>16} {r["mean_alerts_per_year"]:>12.3f}')

if __name__ == '__main__':
    main()
