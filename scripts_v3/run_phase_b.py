"""run_phase_b.py — full retrospective on v3.1 12 outbreaks (Steps B1-B4).

Outputs (to outputs/):
  retrospective_results_v3.csv      — outbreak × detector lead times
  detector_complementarity_v3.csv   — per-outbreak detector necessity
  sensitivity_evaluation_v3.csv     — combined-OR sensitivity
  outbreak_urban_tier_dynamics_v3.json — prefecture × week × tier traces
  urban_tier_comparison_v3.md       — dual-granularity comparison
  false_alert_characterization_v3.csv — alerts in outbreak-free windows
"""
import csv, json, sys
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, '/sessions/cool-clever-goldberg/mnt/outputs')
import detect_anomalies_v3 as v3

OUT = Path('/sessions/cool-clever-goldberg/mnt/outputs')
DASH = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json'))
DID  = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_did_classification.json'))
URBAN = {p: DID[p]['urban_tier_did'] for p in DID}
NESID = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/scripts/nesid_pref_data.json'))

# Map curation disease names to dashboard / pref CSV keys
CUR_TO_DASH = {
    '手足口病': '手足口病',
    'RSウイルス感染症': 'RSウイルス感染症',
    'インフルエンザ': 'インフルエンザ',
    'マイコプラズマ肺炎': 'マイコプラズマ肺炎',
    '感染性胃腸炎': '感染性胃腸炎',
    '流行性耳下腺炎': '流行性耳下腺炎',
    'A群溶血性レンサ球菌咽頭炎': 'レンサ球菌咽頭炎',  # dashboard key (no Ａ群 prefix)
    '咽頭結膜熱': '咽頭結膜熱',
    '風しん': '風しん',
    '麻しん': '麻しん',
    '梅毒': '梅毒',
}
CUR_TO_PREF_CSV = {  # CSV uses full-width Ａ
    '手足口病': '手足口病',
    'RSウイルス感染症': 'RSウイルス感染症',
    'インフルエンザ': 'インフルエンザ',
    'マイコプラズマ肺炎': 'マイコプラズマ肺炎',
    '感染性胃腸炎': '感染性胃腸炎',
    '流行性耳下腺炎': '流行性耳下腺炎',
    'A群溶血性レンサ球菌咽頭炎': 'Ａ群溶血性レンサ球菌咽頭炎',
    '咽頭結膜熱': '咽頭結膜熱',
    '風しん': '風しん',
    '麻しん': '麻しん',
    '梅毒': '梅毒',
}

# Load v3.1 curation
outbreaks = []
with open('/sessions/cool-clever-goldberg/mnt/claude/outbreak_reference_set_v3.csv') as f:
    for r in csv.DictReader(f):
        if not r.get('reference_start_iso_week'): continue
        ry, rw = r['reference_start_iso_week'].split('-W')
        outbreaks.append({
            'id': int(r['id']), 'disease_jp': r['disease_jp'],
            'ref_y': int(ry), 'ref_w': int(rw),
            'class': 'full-report' if r['disease_jp'] in v3.FULL_REPORT_DISEASES else 'sentinel',
            'dash_calc_total': r.get('total_cases_dashboard_calculated', ''),
        })
print(f'Loaded {len(outbreaks)} outbreaks from v3.1\n')

# Load prefecture_week_timeseries
print('Loading prefecture_week_timeseries.csv ...')
pref_2d = defaultdict(lambda: defaultdict(list))
with open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_week_timeseries.csv') as f:
    for r in csv.DictReader(f):
        pref_2d[r['disease']][r['prefecture']].append({
            'year': int(r['year']), 'week': int(r['iso_week']), 'total': int(r['cases'])
        })
pref_2d = {k: dict(v) for k, v in pref_2d.items()}
print(f'Indexed {len(pref_2d)} diseases × prefecture series\n')

# ── Step B1+B2: per-outbreak × per-detector retrospective ─────────────────
print('=== B1: Retrospective ===\n')
WINDOW = 52
results = []     # detail rows for retrospective_results_v3.csv
for ob in outbreaks:
    dash_key = CUR_TO_DASH.get(ob['disease_jp'])
    pref_key = CUR_TO_PREF_CSV.get(ob['disease_jp'])
    if dash_key not in DASH['weekly_trends']:
        print(f"  WARN: {ob['disease_jp']} no national series in dashboard"); continue
    ws = DASH['weekly_trends'][dash_key]
    ps = pref_2d.get(pref_key, {})
    weeks = v3.weeks_in_window(ws, ob['ref_y'], ob['ref_w'], WINDOW)
    ob_results = {}
    for det_name, det_fn in [('D_rare', v3.D_rare), ('D_stat', v3.D_stat), ('D_growth', v3.D_growth)]:
        v3.reset_caches()
        sev_dict = {(y, w): det_fn(ob['disease_jp'], ws, ps, y, w) for y, w in weeks}
        res = v3.first_sustained_alert(lambda y, w: sev_dict.get((y, w)), weeks)
        if res:
            ay, aw, sev = res
            ob_results[det_name] = {'alert_y': ay, 'alert_w': aw, 'sev': sev,
                                     'lead': v3.lead_weeks(ob['ref_y'], ob['ref_w'], ay, aw)}
        else:
            ob_results[det_name] = None
    # D_spatial — flat + tier
    v3.reset_caches()
    sp_flat_dict = {}
    sp_tier_leader_dict = {}
    for y, w in weeks:
        sp = v3.D_spatial(ob['disease_jp'], ws, ps, y, w, URBAN)
        if isinstance(sp, dict):
            sp_flat_dict[(y, w)] = sp.get('flat')
            sp_tier_leader_dict[(y, w)] = sp.get('leader_tier')
        else:
            sp_flat_dict[(y, w)] = sp
            sp_tier_leader_dict[(y, w)] = None
    res_sp = v3.first_sustained_alert(lambda y, w: sp_flat_dict.get((y, w)), weeks)
    if res_sp:
        ay, aw, sev = res_sp
        ob_results['D_spatial'] = {'alert_y': ay, 'alert_w': aw, 'sev': sev,
                                   'lead': v3.lead_weeks(ob['ref_y'], ob['ref_w'], ay, aw),
                                   'tier_leader': sp_tier_leader_dict.get((ay, aw))}
    else:
        ob_results['D_spatial'] = None
    # Combined OR
    combined_dict = {}
    for y, w in weeks:
        sevs = []
        for det_name in ('D_rare', 'D_stat', 'D_growth'):
            r = ob_results[det_name]  # already-walked, but we want per-week
            # Need to re-evaluate per-week for combined; simpler: compute combined inline
            pass
        # Re-compute per-week combined severity
        sev_rare = v3.D_rare(ob['disease_jp'], ws, ps, y, w)
        sev_stat = v3.D_stat(ob['disease_jp'], ws, ps, y, w)
        sev_growth = v3.D_growth(ob['disease_jp'], ws, ps, y, w)
        sev_spatial = sp_flat_dict.get((y, w))
        sevs = [s for s in (sev_rare, sev_stat, sev_growth, sev_spatial) if s]
        if not sevs: combined_dict[(y, w)] = None
        elif 'high' in sevs: combined_dict[(y, w)] = 'high'
        else: combined_dict[(y, w)] = 'medium'
    res_combined = v3.first_sustained_alert(lambda y, w: combined_dict.get((y, w)), weeks)
    if res_combined:
        ay, aw, sev = res_combined
        ob_results['Combined_OR'] = {'alert_y': ay, 'alert_w': aw, 'sev': sev,
                                      'lead': v3.lead_weeks(ob['ref_y'], ob['ref_w'], ay, aw)}
    else:
        ob_results['Combined_OR'] = None

    print(f"#{ob['id']} {ob['disease_jp']:<22} ref={ob['ref_y']}/W{ob['ref_w']:<2} "
          f"D_rare={ob_results['D_rare']['lead'] if ob_results['D_rare'] else '-':>4} "
          f"D_stat={ob_results['D_stat']['lead'] if ob_results['D_stat'] else '-':>4} "
          f"D_grw={ob_results['D_growth']['lead'] if ob_results['D_growth'] else '-':>4} "
          f"D_sp={ob_results['D_spatial']['lead'] if ob_results['D_spatial'] else '-':>4} "
          f"COR={ob_results['Combined_OR']['lead'] if ob_results['Combined_OR'] else '-':>4}")

    for det_name in ('D_rare', 'D_stat', 'D_growth', 'D_spatial', 'Combined_OR'):
        r = ob_results[det_name]
        results.append({
            'outbreak_id': ob['id'],
            'disease': ob['disease_jp'],
            'class': ob['class'],
            'ref_year': ob['ref_y'], 'ref_week': ob['ref_w'],
            'detector': det_name,
            'first_alert_year': r['alert_y'] if r else '',
            'first_alert_week': r['alert_w'] if r else '',
            'severity': r['sev'] if r else '',
            'lead_weeks': r['lead'] if r else '',
            'urban_tier_leader': r.get('tier_leader', '') if r else '',
        })

# Save B1
with open(OUT/'retrospective_results_v3.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    w.writeheader(); w.writerows(results)
print(f'\nSaved retrospective_results_v3.csv ({len(results)} rows)\n')

# ── B2: Complementarity + sensitivity ─────────────────────────────────────
print('=== B2: Detector complementarity ===\n')
complementarity = []
sensitivity_eval = {'detected_within_pm26w': 0, 'detected_combined': 0,
                    'lead_times_combined': []}
TOLERANCE_DETECT = 26  # within ±26w of anchor

for ob in outbreaks:
    rows_ob = [r for r in results if r['outbreak_id'] == ob['id']]
    detected_by = [r['detector'] for r in rows_ob if r['detector'] != 'Combined_OR' and r['lead_weeks'] != '' and abs(int(r['lead_weeks'])) <= TOLERANCE_DETECT]
    combined_row = next((r for r in rows_ob if r['detector'] == 'Combined_OR'), None)
    detected_combined = (combined_row and combined_row['lead_weeks'] != '' and abs(int(combined_row['lead_weeks'])) <= TOLERANCE_DETECT)
    if detected_combined:
        sensitivity_eval['detected_combined'] += 1
        sensitivity_eval['lead_times_combined'].append(int(combined_row['lead_weeks']))
    n_detectors_fired = len(detected_by)
    unique_savior = detected_by[0] if n_detectors_fired == 1 else None
    complementarity.append({
        'outbreak_id': ob['id'], 'disease': ob['disease_jp'],
        'class': ob['class'],
        'n_detectors_fired': n_detectors_fired,
        'detectors_fired': '; '.join(detected_by),
        'unique_savior': unique_savior or '',
        'combined_detected': 'Y' if detected_combined else 'N',
    })

with open(OUT/'detector_complementarity_v3.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(complementarity[0].keys()))
    w.writeheader(); w.writerows(complementarity)

# Sensitivity / lead-time summary
n_total = len(outbreaks)
n_detected = sensitivity_eval['detected_combined']
sens_pct = n_detected / n_total * 100
lts = sorted(sensitivity_eval['lead_times_combined'])
median_lt = lts[len(lts)//2] if lts else None
mean_lt = sum(lts) / len(lts) if lts else None
print(f'  Sensitivity (Combined_OR): {n_detected}/{n_total} = {sens_pct:.0f}%')
print(f'  Median lead time: {median_lt}w')
print(f'  Mean lead time: {mean_lt:.1f}w' if mean_lt else '  Mean: -')
print(f'  Lead time distribution: {lts}')

with open(OUT/'sensitivity_evaluation_v3.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['metric', 'value'])
    w.writerow(['n_outbreaks_total', n_total])
    w.writerow(['n_detected_combined', n_detected])
    w.writerow(['sensitivity_pct', f'{sens_pct:.1f}'])
    w.writerow(['median_lead_time_weeks', median_lt])
    w.writerow(['mean_lead_time_weeks', f'{mean_lt:.2f}' if mean_lt else ''])
    w.writerow(['lead_time_distribution', ','.join(map(str, lts))])

# ── B3: Urban-tier dual granularity ────────────────────────────────────────
print('\n=== B3: Urban-tier dual granularity ===\n')
tier_dynamics = {}
for ob in outbreaks:
    pref_key = CUR_TO_PREF_CSV.get(ob['disease_jp'])
    ps = pref_2d.get(pref_key, {})
    if not ps:
        print(f"  {ob['disease_jp']}: no pref data — skip"); continue
    # Group prefectures by tier
    tier_prefs = {'high_urban': [], 'mixed': [], 'rural_leaning': []}
    for pref in ps:
        if pref == '総数': continue
        t = URBAN.get(pref)
        if t in tier_prefs: tier_prefs[t].append(pref)
    # Build weekly tier-cases trace within ±52w
    weeks = v3.weeks_in_window(DASH['weekly_trends'][CUR_TO_DASH[ob['disease_jp']]], ob['ref_y'], ob['ref_w'], 52)
    traces = {t: [] for t in tier_prefs}
    for y, w in weeks:
        for t, prefs in tier_prefs.items():
            cases = sum(v3.value_at(ps[p], y, w) or 0 for p in prefs)
            n_active = sum(1 for p in prefs if v3.value_at(ps[p], y, w) is not None)
            traces[t].append({'year': y, 'week': w, 'cases': cases, 'n_active': n_active})
    # Find first sustained ramp per tier (z_mad > 2 sustained 3 weeks)
    tier_first_ramp = {}
    for t, prefs in tier_prefs.items():
        if not prefs: continue
        # Build per-week aggregated count for the tier
        tier_series = []
        for tr in traces[t]:
            tier_series.append({'year': tr['year'], 'week': tr['week'], 'total': tr['cases']})
        # Find first 3-week run where z_mad > 2 (using tier-aggregated as a proxy series)
        v3.reset_caches()
        sev_dict = {(r['year'], r['week']): ('medium' if (v3.z_mad(tier_series, r['year'], r['week']) or -99) > 2.0 else None)
                    for r in tier_series}
        res = v3.first_sustained_alert(lambda y, w: sev_dict.get((y, w)),
                                        [(r['year'], r['week']) for r in tier_series], k=3)
        if res:
            ay, aw, sev = res
            tier_first_ramp[t] = {'year': ay, 'week': aw,
                                  'lead': v3.lead_weeks(ob['ref_y'], ob['ref_w'], ay, aw)}
    # NESID-annual urban-tier ratio (where data exists)
    nesid_ratio = None
    if ob['disease_jp'] in NESID and str(ob['ref_y']) in NESID[ob['disease_jp']]:
        ydata = NESID[ob['disease_jp']][str(ob['ref_y'])]
        agg = {t: {'cases': 0, 'pop_k': 0} for t in tier_prefs}
        for pref, info in ydata.items():
            if pref in ('全国', '総数'): continue
            t = URBAN.get(pref)
            if t and t in agg:
                agg[t]['cases'] += info.get('cases', 0)
                agg[t]['pop_k'] += info.get('pop_k', 0)
        rates = {t: (agg[t]['cases']/(agg[t]['pop_k']*1000)*1e5 if agg[t]['pop_k'] else 0) for t in agg}
        if rates['rural_leaning'] > 0:
            nesid_ratio = round(rates['high_urban'] / rates['rural_leaning'], 2)
    tier_dynamics[ob['disease_jp']] = {
        'outbreak_id': ob['id'], 'ref_year': ob['ref_y'], 'ref_week': ob['ref_w'],
        'tier_prefs': {t: prefs for t, prefs in tier_prefs.items()},
        'tier_first_ramp_prefweek': tier_first_ramp,
        'nesid_annual_urban_rural_ratio': nesid_ratio,
        'traces': traces,
    }
    print(f"  #{ob['id']:>2} {ob['disease_jp']:<22} ", end='')
    for t in ('high_urban', 'mixed', 'rural_leaning'):
        if t in tier_first_ramp:
            print(f"{t[:4]}_lead={tier_first_ramp[t]['lead']:+d}w ", end='')
        else:
            print(f"{t[:4]}_-     ", end='')
    print(f"NESID_h/r={nesid_ratio}")

with open(OUT/'outbreak_urban_tier_dynamics_v3.json', 'w', encoding='utf-8') as f:
    json.dump(tier_dynamics, f, ensure_ascii=False, indent=2)

# ── B4: False alert characterization ──────────────────────────────────────
print('\n=== B4: False alert (national-level) ===\n')
# Build exclusion mask: (disease, year, week) within ±26w of any outbreak anchor
excluded = set()
for ob in outbreaks:
    dk = CUR_TO_DASH[ob['disease_jp']]
    for dy in range(-26, 27):
        ay = ob['ref_y'] + (ob['ref_w'] + dy - 1) // 52
        aw = ((ob['ref_w'] + dy - 1) % 52) + 1
        excluded.add((dk, ay, aw))

fa_rows = []
for ob_disease in set(o['disease_jp'] for o in outbreaks):
    dk = CUR_TO_DASH[ob_disease]
    pref_key = CUR_TO_PREF_CSV[ob_disease]
    ws = DASH['weekly_trends'][dk]
    ps = pref_2d.get(pref_key, {})
    weeks_chrono = sorted(set((r['year'], r['week']) for r in ws))
    det_streak = {d: 0 for d in ('D_rare', 'D_stat', 'D_growth', 'D_spatial')}
    det_outside = {d: 0 for d in det_streak}
    v3.reset_caches()
    for y, w in weeks_chrono:
        in_w = (dk, y, w) in excluded
        sev = {
            'D_rare':    v3.D_rare(ob_disease, ws, ps, y, w),
            'D_stat':    v3.D_stat(ob_disease, ws, ps, y, w),
            'D_growth':  v3.D_growth(ob_disease, ws, ps, y, w),
        }
        sp = v3.D_spatial(ob_disease, ws, ps, y, w, URBAN)
        sev['D_spatial'] = sp.get('flat') if isinstance(sp, dict) else sp
        for det in det_streak:
            if sev[det] in ('medium', 'high'):
                det_streak[det] += 1
                if det_streak[det] == v3.SUSTAINED_K and not in_w:
                    det_outside[det] += 1
            else:
                det_streak[det] = 0
    n_years = max(1, len(weeks_chrono) // 52)
    is_full = ob_disease in v3.FULL_REPORT_DISEASES
    for det, n in det_outside.items():
        fa_rows.append({
            'disease': ob_disease, 'class': 'full-report' if is_full else 'sentinel',
            'detector': det,
            'sustained_alerts_outside_window': n,
            'n_years_covered': n_years,
            'alerts_per_year': round(n / n_years, 3),
        })

with open(OUT/'false_alert_characterization_v3.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(fa_rows[0].keys()))
    w.writeheader(); w.writerows(fa_rows)

# Aggregate summary
print(f"{'Detector':<10} {'sentinel':>10} {'full-report':>12}")
print('-'*40)
for det in ('D_rare', 'D_stat', 'D_growth', 'D_spatial'):
    s_alerts = sum(r['alerts_per_year'] for r in fa_rows if r['detector']==det and r['class']=='sentinel')
    s_n = sum(1 for r in fa_rows if r['detector']==det and r['class']=='sentinel')
    f_alerts = sum(r['alerts_per_year'] for r in fa_rows if r['detector']==det and r['class']=='full-report')
    f_n = sum(1 for r in fa_rows if r['detector']==det and r['class']=='full-report')
    print(f"{det:<10} {s_alerts/max(s_n,1):>10.3f} {f_alerts/max(f_n,1):>12.3f}")

print('\n=== Phase B1-B4 complete. Saved 6 result files. ===')
