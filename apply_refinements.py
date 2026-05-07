"""Apply Refinement 1 (window) + Refinement 2 (#11/#12 anchor change), then rerun B1+B2+B4.
Outputs overwrite same filenames per spec; previous values preserved as v3-orig backup."""
import csv, json, sys, math
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, '/sessions/cool-clever-goldberg/mnt/outputs')
import detect_anomalies_v3 as v3

OUT = Path('/sessions/cool-clever-goldberg/mnt/outputs')
DASH = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json'))
DID  = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_did_classification.json'))
URBAN = {p: DID[p]['urban_tier_did'] for p in DID}

CUR_TO_DASH = {'手足口病':'手足口病', 'RSウイルス感染症':'RSウイルス感染症', 'インフルエンザ':'インフルエンザ',
    'マイコプラズマ肺炎':'マイコプラズマ肺炎', '感染性胃腸炎':'感染性胃腸炎', '流行性耳下腺炎':'流行性耳下腺炎',
    'A群溶血性レンサ球菌咽頭炎':'レンサ球菌咽頭炎', '咽頭結膜熱':'咽頭結膜熱',
    '風しん':'風しん', '麻しん':'麻しん', '梅毒':'梅毒'}
CUR_TO_PREF = {**CUR_TO_DASH, 'A群溶血性レンサ球菌咽頭炎':'Ａ群溶血性レンサ球菌咽頭炎'}

# ── Refinement 2: update #11 / #12 anchors in curation CSV ──────────────────
CSV = Path('/sessions/cool-clever-goldberg/mnt/claude/outbreak_reference_set_v3.csv')
# Backup original first
if not (OUT/'outbreak_reference_set_v3_BEFORE_REFINEMENT.csv').exists():
    import shutil
    shutil.copy(CSV, OUT/'outbreak_reference_set_v3_BEFORE_REFINEMENT.csv')

with open(CSV, encoding='utf-8') as f:
    rows = list(csv.DictReader(f))
fieldnames = list(rows[0].keys())
if 'anchor_method' not in fieldnames:
    fieldnames.append('anchor_method')
for r in rows:
    if 'anchor_method' not in r: r['anchor_method'] = 'external_official'
# patch #11 麻しん, #12 梅毒
for r in rows:
    if r['id'] == '11':
        r['reference_start_iso_week'] = '2026-W04'
        r['anchor_method'] = 'data_derived_yty50'
        r['notes'] = (r.get('notes','') or '') + ' [v3.1.1: anchor changed from 2026-W01 (conceptual year-start) to 2026-W04 (data-derived; YTD cum first exceeded prev-year same-period by 50%, ratio=9.0× at W4)]'
    if r['id'] == '12':
        r['reference_start_iso_week'] = '2024-W29'
        r['anchor_method'] = 'data_derived_50_of_prev_full'
        r['notes'] = (r.get('notes','') or '') + ' [v3.1.1: anchor changed from 2024-W01 (conceptual year-start) to 2024-W29 (data-derived fallback; 2024 YTD never exceeded 2023 same-period by 50% because 2023 was record-high, so used 50%-of-prev-year-full rule → W29 = 50% milestone)]'
with open(CSV, 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    w.writeheader(); w.writerows(rows)
print(f'CSV patched: 12 outbreaks; #11 anchor → 2026-W04, #12 anchor → 2024-W29\n')

# ── Refinement 1: rerun B1+B2+B4 with new window [anchor−4w, anchor+52w] ──
# Load prefecture_week_timeseries
pref_2d = defaultdict(lambda: defaultdict(list))
with open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_week_timeseries.csv') as f:
    for r in csv.DictReader(f):
        pref_2d[r['disease']][r['prefecture']].append({
            'year':int(r['year']),'week':int(r['iso_week']),'total':int(r['cases'])})
pref_2d = {k: dict(v) for k, v in pref_2d.items()}

# Reload patched outbreaks
outbreaks = []
with open(CSV) as f:
    for r in csv.DictReader(f):
        if not r.get('reference_start_iso_week'): continue
        ry, rw = r['reference_start_iso_week'].split('-W')
        outbreaks.append({
            'id':int(r['id']), 'disease_jp':r['disease_jp'],
            'ref_y':int(ry), 'ref_w':int(rw),
            'class':'full-report' if r['disease_jp'] in v3.FULL_REPORT_DISEASES else 'sentinel',
            'anchor_method': r.get('anchor_method', 'external_official'),
        })

# New window function
def weeks_in_new_window(weekly_series, ref_y, ref_w, before_w=4, after_w=52):
    """Refinement 1: [anchor-before_w, anchor+after_w]. Default −4 to +52."""
    out = []
    for r in weekly_series:
        y, w = r.get('year'), r.get('week')
        if y is None or w is None: continue
        dist = (y - ref_y) * 52 + (w - ref_w)
        if -before_w <= dist <= after_w:
            out.append((dist, y, w))
    out.sort()
    return [(y, w) for d, y, w in out]

print('=== B1 rerun (new window: anchor-4w to anchor+52w) ===\n')
print(f'{"#":>2} {"Disease":<22} {"Anchor":<10} {"D_rare":>6} {"D_stat":>6} {"D_grw":>6} {"D_sp":>6} {"COR":>6}')
print('-' * 78)

results = []
for ob in outbreaks:
    dk = CUR_TO_DASH.get(ob['disease_jp'])
    pk = CUR_TO_PREF.get(ob['disease_jp'])
    if dk not in DASH['weekly_trends']: continue
    ws = DASH['weekly_trends'][dk]
    ps = pref_2d.get(pk, {})
    weeks = weeks_in_new_window(ws, ob['ref_y'], ob['ref_w'])
    ob_res = {}
    for det_name, det_fn in [('D_rare',v3.D_rare),('D_stat',v3.D_stat),('D_growth',v3.D_growth)]:
        v3.reset_caches()
        sev_d = {(y,w): det_fn(ob['disease_jp'], ws, ps, y, w) for y, w in weeks}
        res = v3.first_sustained_alert(lambda y, w: sev_d.get((y,w)), weeks)
        ob_res[det_name] = ({'alert_y':res[0],'alert_w':res[1],'sev':res[2],
                              'lead':v3.lead_weeks(ob['ref_y'],ob['ref_w'],res[0],res[1])} if res else None)
    # D_spatial flat
    v3.reset_caches()
    sp_flat = {}
    sp_tier_leader = {}
    for y, w in weeks:
        sp = v3.D_spatial(ob['disease_jp'], ws, ps, y, w, URBAN)
        if isinstance(sp, dict):
            sp_flat[(y,w)] = sp.get('flat')
            sp_tier_leader[(y,w)] = sp.get('leader_tier')
        else:
            sp_flat[(y,w)] = sp
            sp_tier_leader[(y,w)] = None
    res = v3.first_sustained_alert(lambda y, w: sp_flat.get((y,w)), weeks)
    ob_res['D_spatial'] = ({'alert_y':res[0],'alert_w':res[1],'sev':res[2],
                             'lead':v3.lead_weeks(ob['ref_y'],ob['ref_w'],res[0],res[1]),
                             'tier_leader':sp_tier_leader.get((res[0],res[1]))} if res else None)
    # Combined OR
    combined = {}
    for y, w in weeks:
        sevs = [v3.D_rare(ob['disease_jp'],ws,ps,y,w),
                v3.D_stat(ob['disease_jp'],ws,ps,y,w),
                v3.D_growth(ob['disease_jp'],ws,ps,y,w),
                sp_flat.get((y,w))]
        sevs = [s for s in sevs if s]
        if not sevs: combined[(y,w)] = None
        elif 'high' in sevs: combined[(y,w)] = 'high'
        else: combined[(y,w)] = 'medium'
    res = v3.first_sustained_alert(lambda y, w: combined.get((y,w)), weeks)
    ob_res['Combined_OR'] = ({'alert_y':res[0],'alert_w':res[1],'sev':res[2],
                                'lead':v3.lead_weeks(ob['ref_y'],ob['ref_w'],res[0],res[1])} if res else None)

    print(f'{ob["id"]:>2} {ob["disease_jp"][:21]:<22} {ob["ref_y"]}/W{ob["ref_w"]:<2}    '
          f'{ob_res["D_rare"]["lead"] if ob_res["D_rare"] else "-":>6} '
          f'{ob_res["D_stat"]["lead"] if ob_res["D_stat"] else "-":>6} '
          f'{ob_res["D_growth"]["lead"] if ob_res["D_growth"] else "-":>6} '
          f'{ob_res["D_spatial"]["lead"] if ob_res["D_spatial"] else "-":>6} '
          f'{ob_res["Combined_OR"]["lead"] if ob_res["Combined_OR"] else "-":>6}')

    for det in ('D_rare','D_stat','D_growth','D_spatial','Combined_OR'):
        r = ob_res[det]
        results.append({
            'outbreak_id':ob['id'],'disease':ob['disease_jp'],'class':ob['class'],
            'anchor_method':ob['anchor_method'],
            'ref_year':ob['ref_y'],'ref_week':ob['ref_w'],
            'detector':det,
            'first_alert_year':r['alert_y'] if r else '',
            'first_alert_week':r['alert_w'] if r else '',
            'severity':r['sev'] if r else '',
            'lead_weeks':r['lead'] if r else '',
            'urban_tier_leader':r.get('tier_leader','') if r else '',
        })

with open(OUT/'retrospective_results_v3.csv','w',encoding='utf-8',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
    w.writeheader(); w.writerows(results)

# B2: complementarity + sensitivity (within ±26w)
print('\n=== B2 rerun ===\n')
TOL = 26
sens_count = 0
leads = []
complementarity = []
for ob in outbreaks:
    rows_o = [r for r in results if r['outbreak_id'] == ob['id']]
    detected_by = [r['detector'] for r in rows_o
                    if r['detector'] != 'Combined_OR' and r['lead_weeks'] != ''
                    and abs(int(r['lead_weeks'])) <= TOL]
    cor = next((r for r in rows_o if r['detector']=='Combined_OR'), None)
    cor_detected = (cor and cor['lead_weeks']!='' and abs(int(cor['lead_weeks']))<=TOL)
    if cor_detected:
        sens_count += 1
        leads.append(int(cor['lead_weeks']))
    complementarity.append({
        'outbreak_id':ob['id'],'disease':ob['disease_jp'],'class':ob['class'],
        'n_detectors_fired':len(detected_by),
        'detectors_fired':'; '.join(detected_by),
        'unique_savior':detected_by[0] if len(detected_by)==1 else '',
        'combined_detected':'Y' if cor_detected else 'N',
    })

with open(OUT/'detector_complementarity_v3.csv','w',encoding='utf-8',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(complementarity[0].keys()))
    w.writeheader(); w.writerows(complementarity)

n = len(outbreaks); sens_pct = sens_count/n*100
leads_sorted = sorted(leads)
median = leads_sorted[len(leads_sorted)//2] if leads_sorted else None
mean = sum(leads_sorted)/len(leads_sorted) if leads_sorted else None
print(f'  Sensitivity (Combined_OR within ±{TOL}w of anchor): {sens_count}/{n} = {sens_pct:.0f}%')
print(f'  Median lead: {median}w')
print(f'  Mean lead: {mean:.1f}w' if mean is not None else '')
print(f'  Lead distribution: {leads_sorted}')

with open(OUT/'sensitivity_evaluation_v3.csv','w',encoding='utf-8',newline='') as f:
    w = csv.writer(f)
    w.writerow(['metric','value'])
    w.writerow(['n_outbreaks',n])
    w.writerow(['n_detected_combined',sens_count])
    w.writerow(['sensitivity_pct',f'{sens_pct:.1f}'])
    w.writerow(['median_lead_weeks',median])
    w.writerow(['mean_lead_weeks',f'{mean:.2f}' if mean else ''])
    w.writerow(['lead_distribution',','.join(map(str,leads_sorted))])
    w.writerow(['detection_window','[anchor-4w, anchor+52w]'])
    w.writerow(['detection_tolerance_pm26w','True'])

# B4: false alert rate (same logic as before)
print('\n=== B4 rerun (false alert rate) ===\n')
excluded = set()
for ob in outbreaks:
    dk = CUR_TO_DASH[ob['disease_jp']]
    for dy in range(-26, 27):
        ay = ob['ref_y'] + (ob['ref_w']+dy-1)//52
        aw = ((ob['ref_w']+dy-1)%52)+1
        excluded.add((dk, ay, aw))

fa_rows = []
for d in set(o['disease_jp'] for o in outbreaks):
    dk = CUR_TO_DASH[d]
    pk = CUR_TO_PREF[d]
    ws = DASH['weekly_trends'][dk]
    ps = pref_2d.get(pk, {})
    weeks_chrono = sorted(set((r['year'],r['week']) for r in ws))
    streak = {dt:0 for dt in ('D_rare','D_stat','D_growth','D_spatial')}
    outside = {dt:0 for dt in streak}
    v3.reset_caches()
    for y, w in weeks_chrono:
        in_w = (dk, y, w) in excluded
        sev = {'D_rare':v3.D_rare(d,ws,ps,y,w), 'D_stat':v3.D_stat(d,ws,ps,y,w),
               'D_growth':v3.D_growth(d,ws,ps,y,w)}
        sp = v3.D_spatial(d, ws, ps, y, w, URBAN)
        sev['D_spatial'] = sp.get('flat') if isinstance(sp, dict) else sp
        for dt in streak:
            if sev[dt] in ('medium','high'):
                streak[dt] += 1
                if streak[dt] == v3.SUSTAINED_K and not in_w: outside[dt] += 1
            else: streak[dt] = 0
    n_years = max(1, len(weeks_chrono)//52)
    is_full = d in v3.FULL_REPORT_DISEASES
    for dt, n_alerts in outside.items():
        fa_rows.append({'disease':d,'class':'full-report' if is_full else 'sentinel',
                        'detector':dt,
                        'sustained_alerts_outside_window':n_alerts,
                        'n_years_covered':n_years,
                        'alerts_per_year':round(n_alerts/n_years, 3)})

with open(OUT/'false_alert_characterization_v3.csv','w',encoding='utf-8',newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(fa_rows[0].keys()))
    w.writeheader(); w.writerows(fa_rows)

print(f'{"Detector":<10} {"sentinel":>10} {"full-report":>12}')
print('-'*40)
for dt in ('D_rare','D_stat','D_growth','D_spatial'):
    s = [r['alerts_per_year'] for r in fa_rows if r['detector']==dt and r['class']=='sentinel']
    f_ = [r['alerts_per_year'] for r in fa_rows if r['detector']==dt and r['class']=='full-report']
    print(f'{dt:<10} {sum(s)/max(len(s),1):>10.3f} {sum(f_)/max(len(f_),1):>12.3f}')

print('\n=== Phase B rerun complete ===')
