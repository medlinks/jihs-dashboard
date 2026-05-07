"""detect_anomalies_v3.py — 4-detector framework for v3.1 12-outbreak retrospective.

Reuses archived v2 logic (D-rare / D-stat / D-growth-floored / D-spatial) with
no algorithmic changes per user spec — only repackaged for v3 inputs.

Inputs at runtime:
  - prefecture_week_timeseries.csv (12 diseases × 47 prefectures × 14 years)
  - DATA.weekly_trends from full_dashboard_data.json (national series, all 108 diseases)
  - DATA.urban_tier from prefecture_did_classification.json

As-of-week-t purity: every helper accepts (year, week) and reads only data with
(y, w) ≤ target. Truncation-invariance unit test included.
"""
from __future__ import annotations
import math, csv, json
from pathlib import Path
from collections import defaultdict

# ── Constants ──────────────────────────────────────────────────────────────
LOOKBACK_YEARS = 5
WEEK_WINDOW    = 2
MIN_REF_OBS    = 8
SUSTAINED_K    = 3
RARE_BASELINE  = 5
MAD_K_MED      = 2.0
MAD_K_HIGH     = 3.0
SPATIAL_FLAT   = 0.25
SPATIAL_TIER   = 0.40

# Full-report (全数把握) diseases relevant to v3.1 — only these can trigger D_rare
FULL_REPORT_DISEASES = {'風しん', '麻しん', '梅毒'}  # v3.1 scope

def growth_floor(median_baseline: float) -> int:
    if median_baseline < 5:   return 5
    if median_baseline < 50:  return 10
    return 50

# ── Cached lookups ─────────────────────────────────────────────────────────
_LUT, _ZMAD = {}, {}

def reset_caches(): _LUT.clear(); _ZMAD.clear()

def _build_lut(series):
    sid = id(series)
    if sid not in _LUT:
        _LUT[sid] = {(r['year'], r['week']): r.get('total', r.get('cases', 0))
                     for r in series if r.get('year') and r.get('week')}
    return _LUT[sid]

def value_at(series, year, week):
    return _build_lut(series).get((year, week))

def collect_reference(series, target_year, target_week, lookback=LOOKBACK_YEARS, window=WEEK_WINDOW):
    lut = _build_lut(series)
    refs = []
    for y in range(target_year - lookback, target_year):
        for w in range(target_week - window, target_week + window + 1):
            v = lut.get((y, w))
            if v is not None: refs.append(v)
    return refs

def step_back(year, week, n=1):
    for _ in range(n):
        if week == 1: year -= 1; week = 52
        else: week -= 1
    return year, week

def z_mad(series, year, week):
    key = (id(series), year, week)
    if key in _ZMAD: return _ZMAD[key]
    current = value_at(series, year, week)
    if current is None: _ZMAD[key] = None; return None
    refs = collect_reference(series, year, week)
    if len(refs) < MIN_REF_OBS: _ZMAD[key] = None; return None
    logs = sorted(math.log(v + 1) for v in refs)
    n = len(logs); med = logs[n//2] if n % 2 else (logs[n//2-1]+logs[n//2])/2
    abs_dev = sorted(abs(x - med) for x in logs)
    mad = abs_dev[n//2] if n % 2 else (abs_dev[n//2-1]+abs_dev[n//2])/2
    if mad < 0.01: mad = 0.01
    z = (math.log(current + 1) - med) / mad
    _ZMAD[key] = z
    return z

def baseline_median(series, year, week):
    refs = collect_reference(series, year, week)
    if len(refs) < MIN_REF_OBS: return None
    refs_sorted = sorted(refs); n = len(refs_sorted)
    return refs_sorted[n//2] if n % 2 else (refs_sorted[n//2-1]+refs_sorted[n//2])/2

# ── Detectors ──────────────────────────────────────────────────────────────
def D_rare(disease, weekly_series, pref_series_dict, year, week):
    if disease not in FULL_REPORT_DISEASES: return None
    cur = value_at(weekly_series, year, week)
    if cur is None or cur < 1: return None
    med = baseline_median(weekly_series, year, week)
    if med is None or med >= RARE_BASELINE: return None
    return 'high'

def D_stat(disease, weekly_series, pref_series_dict, year, week):
    z = z_mad(weekly_series, year, week)
    if z is None: return None
    if z >= MAD_K_HIGH: return 'high'
    if z >= MAD_K_MED:  return 'medium'
    return None

def D_growth(disease, weekly_series, pref_series_dict, year, week):
    cur = value_at(weekly_series, year, week)
    if cur is None or cur < 1: return None
    med_baseline = baseline_median(weekly_series, year, week)
    floor = growth_floor(med_baseline or 0)
    if cur < floor: return None
    # 4-week current slope
    slopes_recent, y, w = [], year, week
    for _ in range(4):
        v_now = value_at(weekly_series, y, w)
        py, pw = step_back(y, w); v_prev = value_at(weekly_series, py, pw)
        if v_now is None or v_prev is None: return None
        slopes_recent.append(v_now - v_prev)
        y, w = py, pw
    cur_slope = sum(slopes_recent) / len(slopes_recent)
    # 12-week historical slopes
    hist_slopes, y, w = [], step_back(year, week)[0], step_back(year, week)[1]
    for _ in range(12):
        v_now = value_at(weekly_series, y, w)
        py, pw = step_back(y, w); v_prev = value_at(weekly_series, py, pw)
        if v_now is None or v_prev is None: break
        hist_slopes.append(v_now - v_prev)
        y, w = py, pw
    if len(hist_slopes) < 8: return None
    hs = sorted(hist_slopes); n = len(hs)
    h_med = hs[n//2] if n % 2 else (hs[n//2-1]+hs[n//2])/2
    q1, q3 = hs[n//4], hs[3*n//4]
    iqr = max(q3 - q1, 1.0)
    threshold = h_med + 1.5 * iqr
    if cur_slope <= threshold: return None
    if med_baseline and cur >= 2 * med_baseline: return 'high'
    return 'medium'

def D_spatial(disease, weekly_series, pref_series_dict, year, week, urban_tier=None):
    if not pref_series_dict: return None
    active, elevated = 0, 0
    by_tier = defaultdict(lambda: {'active': 0, 'elevated': 0})
    for pref, series in pref_series_dict.items():
        if pref == '総数': continue
        refs = collect_reference(series, year, week)
        if sum(refs) < 1: continue
        active += 1
        z = z_mad(series, year, week)
        is_elev = z is not None and z > MAD_K_MED
        if is_elev: elevated += 1
        if urban_tier:
            t = urban_tier.get(pref)
            if t:
                by_tier[t]['active'] += 1
                if is_elev: by_tier[t]['elevated'] += 1
    if active == 0: return None
    flat_pct = elevated / active
    flat_sev = 'high' if flat_pct >= 0.5 else ('medium' if flat_pct >= SPATIAL_FLAT else None)
    if not urban_tier: return flat_sev
    tier_sev = {}; tier_pct = {}
    for t, agg in by_tier.items():
        if agg['active'] == 0: continue
        pct = agg['elevated'] / agg['active']
        tier_pct[t] = pct
        if pct >= 0.6: tier_sev[t] = 'high'
        elif pct >= SPATIAL_TIER: tier_sev[t] = 'medium'
    leader = max(tier_pct.items(), key=lambda kv: kv[1])[0] if tier_pct else None
    return {'flat': flat_sev, 'flat_pct': round(flat_pct, 3),
            'tier_sev': tier_sev, 'tier_pct': {t: round(p, 3) for t, p in tier_pct.items()},
            'leader_tier': leader}

# ── Sustained-alert wrapper ────────────────────────────────────────────────
def first_sustained_alert(severity_fn, weeks_iter, k=SUSTAINED_K):
    streak = []
    for y, w in weeks_iter:
        sev = severity_fn(y, w)
        if sev in ('medium', 'high'):
            streak.append((y, w, sev))
            if len(streak) >= k:
                worst = 'high' if any(s[2]=='high' for s in streak[:k]) else 'medium'
                return (streak[0][0], streak[0][1], worst)
        else:
            streak = []
    return None

def weeks_in_window(weekly_series, ref_y, ref_w, window):
    out = []
    for r in weekly_series:
        y, w = r.get('year'), r.get('week')
        if y is None or w is None: continue
        dist = (y - ref_y) * 52 + (w - ref_w)
        if -window <= dist <= window:
            out.append((dist, y, w))
    out.sort()
    return [(y, w) for d, y, w in out]

def lead_weeks(ref_y, ref_w, ay, aw):
    return (ref_y - ay) * 52 + (ref_w - aw)

# ── Leakage audit ──────────────────────────────────────────────────────────
def leakage_audit(weekly_series_dict, pref_series_2d, urban_tier_map, test_cases):
    """For each (disease, year, week), verify each detector returns identical
       output on full vs truncated input."""
    results = []
    for disease, ty, tw in test_cases:
        if disease not in weekly_series_dict: continue
        full = weekly_series_dict[disease]
        trunc = [r for r in full if (r['year'], r['week']) <= (ty, tw)]
        pf = pref_series_2d.get(disease, {})
        pf_t = {p: [r for r in s if (r['year'], r['week']) <= (ty, tw)] for p, s in pf.items()}
        for det_name, det_fn in [('D_rare', D_rare), ('D_stat', D_stat), ('D_growth', D_growth)]:
            reset_caches()
            r_full = det_fn(disease, full, pf, ty, tw)
            reset_caches()
            r_tr = det_fn(disease, trunc, pf_t, ty, tw)
            results.append((disease, ty, tw, det_name, r_full, r_tr, r_full == r_tr))
        # D_spatial: extract flat severity
        reset_caches()
        sp_full = D_spatial(disease, full, pf, ty, tw, urban_tier_map)
        reset_caches()
        sp_tr = D_spatial(disease, trunc, pf_t, ty, tw, urban_tier_map)
        ff = sp_full.get('flat') if isinstance(sp_full, dict) else sp_full
        ft = sp_tr.get('flat') if isinstance(sp_tr, dict) else sp_tr
        results.append((disease, ty, tw, 'D_spatial', ff, ft, ff == ft))
    return results

if __name__ == '__main__':
    import sys
    print('=== detect_anomalies_v3 leakage audit ===\n')
    DASH = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json'))
    DID = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_did_classification.json'))
    URBAN = {p: DID[p]['urban_tier_did'] for p in DID}
    # Build pref series from prefecture_week_timeseries.csv
    pref_2d = defaultdict(lambda: defaultdict(list))
    with open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_week_timeseries.csv') as f:
        for r in csv.DictReader(f):
            pref_2d[r['disease']][r['prefecture']].append({
                'year': int(r['year']), 'week': int(r['iso_week']), 'total': int(r['cases']),
            })
    # Map curation key 'A群溶血性レンサ球菌咽頭炎' → CSV key 'Ａ群溶血性レンサ球菌咽頭炎'
    pref_2d_dict = {k: dict(v) for k, v in pref_2d.items()}

    test_cases = [
        ('麻しん', 2026, 5),
        ('風しん', 2018, 30),
        ('インフルエンザ', 2022, 51),
        ('手足口病', 2018, 29),
    ]
    res = leakage_audit(DASH['weekly_trends'], pref_2d_dict, URBAN, test_cases)
    all_ok = True
    for d, y, w, det, vf, vt, ok in res:
        flag = 'OK' if ok else '*** LEAK ***'
        print(f'  {d:<8} {y}/W{w:<2} {det:<10}: full={vf!s:8} trunc={vt!s:8} {flag}')
        if not ok: all_ok = False
    print('\n' + ('PASS — no future-data leakage.' if all_ok else 'FAIL — leakage detected.'))
    if not all_ok: sys.exit(1)
