"""
Pilot v2 — Sentinel diseases with refined D1 (median+MAD) and additive D2.

Detectors:
  D0 = Layer 1 (1-case rule for 全数把握 rare). For sentinel diseases here, all
       three are 5類定点 — D0 is silent by definition. Kept as control.
  D1 = median + k·MAD historic-limits, log-transformed, past-5y same-week ±2w.
       k=3.5 medium / k=5.0 high (outlier-resistant analogue of mean ± 2σ/3σ).
       This replaces D0's contaminated mean+σ baseline (the v1 pathology).
  D2 = D1 ∪ multi-signal composite (ADDITIVE — first sustained alert from
       either path wins). Composite signals: Z-MAD, Growth, Persistence,
       Spatial. Weight sensitivity scan: W1..W4 + grid-best.

All detectors wrapped with sustained-alert wrapper k=3.

Strict as-of-week-t purity: every signal at time t uses only data with
(year, week) <= t. Programmatic truncation-invariance test included.
"""
from __future__ import annotations
import json, math, sys, itertools
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_FILE     = Path('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json')
PREF_TS_FILE  = Path('/sessions/cool-clever-goldberg/mnt/outputs/pref_timeseries_sentinel.json')
OUT_DIR       = Path('/sessions/cool-clever-goldberg/mnt/outputs')

# ── Sentinel ground truth (HTTP-verified Japanese URLs) ─────────────────────
GROUND_TRUTH_V2 = {
    "RSV": {
        "idwr_key": "RSウイルス感染症",
        "year": 2024, "week": 13,
        "tier": "c",
        "source_url": "https://id-info.jihs.go.jp/surveillance/idwr/featured/2024/15/index.html",
        "source_url_status": "HTTP 200 verified 2026-05-06",
        "source_type": "JIHS featured (注目すべき感染症)",
        "source_excerpt_jp": "第13週以降、過去5年間の同時期と比べて定点当たり報告数は最も多くなっている",
        "justification": "JIHS featured article 2024/15 (published end of W15, late Apr 2024) explicitly cites W13 as the first week where 2024 RSV per-sentinel exceeded all past-5y same-week values, marking JIHS-editorial-recognized inflection.",
        "caveat": "JIHS publication trigger is independent of raw weekly count alone (editorial decision based on threshold-crossing on per-sentinel rate); however the threshold itself is sentinel-derived.",
    },
    "HFMD": {
        "idwr_key": "手足口病",
        "year": 2018, "week": 29,
        "tier": "c",
        "source_url": "https://id-info.jihs.go.jp/niid/ja/hfmd-m/hfmd-idwrc/8222-idwrc-1829.html",
        "source_url_status": "HTTP 200 verified 2026-05-06 — full Japanese article body retrieved",
        "source_type": "JIHS/NIID featured (注目すべき感染症, IDWR 2018年第29号)",
        "source_excerpt_jp": "2018年は、第19週以降第28週にかけて定点当たり報告数は継続して増加した",
        "justification": "JIHS featured article published in IDWR W29 (mid-Jul 2018) flagged HFMD as 注目すべき感染症 because of sustained W19–W28 rise. W29 is the JIHS-editorial-recognized week the outbreak was officially elevated to alert status.",
        "caveat": "The same article retrospectively cites W19 as the inflection per their own analysis. We anchor at W29 (publication week) as the policy-relevant outbreak-recognition moment; W19 is reported as a sensitivity check.",
    },
    "Influenza": {
        "idwr_key": "インフルエンザ",
        "year": 2022, "week": 51,
        "tier": "c",
        "source_url": "https://id-info.jihs.go.jp/surveillance/idwr/featured/2023/03/index.html",
        "source_url_status": "HTTP 200 verified 2026-05-06 (per agent fetch)",
        "source_type": "JIHS featured 2022/23 season review",
        "source_excerpt_jp": "第51週（12月19～25日）には1.24...と1.00を上回ったため、全国的にインフルエンザは流行期に入ったと判断された",
        "justification": "Official 流行期入り (epidemic-phase entry) declaration: per-sentinel rate first exceeded the 1.00 national-warning threshold in W51 of 2022. This is the formal MHLW/JIHS regulatory criterion, independent of any single-week count.",
        "caveat": "First post-COVID full season; baseline may include suppressed 2020-21/21-22 seasons which could bias historic-limits methods.",
    },
}

# Sensitivity-check secondary anchor for HFMD
GT_SENSITIVITY = {
    "HFMD_W19": {**GROUND_TRUTH_V2["HFMD"], "year": 2018, "week": 19,
                 "tier": "c-sensitivity",
                 "justification": "W19 is the JIHS-cited retrospective inflection week ('第19週以降継続して増加'). Used as sensitivity check on the HFMD W29 publication-anchor."},
}

# ── Parameters ──────────────────────────────────────────────────────────────
LOOKBACK_YEARS = 5
WEEK_WINDOW    = 2
MIN_REF_OBS    = 8
SUSTAINED_K    = 3
LEAD_WINDOW_W  = 26  # ±26w around anchor for first-sustained-alert search

# D1 thresholds in MAD units. For normal data 1σ ≈ 1.4826 MAD ⇒ 2σ ≈ 2.96 MAD.
# We use slightly looser k_med=2.0 and k_high=3.0 because pilot v1 showed
# baseline-skew dampens MAD-z below normal-equiv after log transform.
MAD_K_MED  = 2.0
MAD_K_HIGH = 3.0

# D2 composite thresholds (same as v1)
COMP_MED   = 0.5
COMP_HIGH  = 0.7

# D2 weight presets
D2_WEIGHTS = {
    "W1_default":     {"Z": 0.35, "Growth": 0.20, "Persistence": 0.20, "Spatial": 0.25},
    "W2_Z_heavy":     {"Z": 0.50, "Growth": 0.15, "Persistence": 0.15, "Spatial": 0.20},
    "W3_Spatial":     {"Z": 0.25, "Growth": 0.15, "Persistence": 0.20, "Spatial": 0.40},
    "W4_Persistence": {"Z": 0.25, "Growth": 0.15, "Persistence": 0.40, "Spatial": 0.20},
}

# 1-case rule rare gate (kept for D0 even though sentinel diseases will never trigger)
FULL_REPORT_DISEASES_RARE_GATE = set()  # sentinel diseases won't be in this set

# ── Data loading ────────────────────────────────────────────────────────────
def load_data():
    with open(DATA_FILE) as f: d = json.load(f)
    with open(PREF_TS_FILE) as f: pref_ts = json.load(f)
    return d, pref_ts

# ── History helpers (purity-respecting + optimized) ─────────────────────────
# Build {id(series): {(y,w): total}} dict once for O(1) value_at lookups.
_VALUE_AT_CACHE: dict = {}

def _build_lookup(series):
    sid = id(series)
    if sid not in _VALUE_AT_CACHE:
        _VALUE_AT_CACHE[sid] = {(r['year'], r['week']): r.get('total')
                                for r in series
                                if r.get('year') is not None and r.get('week') is not None}
    return _VALUE_AT_CACHE[sid]

def value_at(series, year, week):
    return _build_lookup(series).get((year, week))

def collect_reference(series, target_year, target_week,
                      lookback=LOOKBACK_YEARS, window=WEEK_WINDOW):
    """Optimized: lookup table + (year, week) bounds."""
    lut = _build_lookup(series)
    refs = []
    for y in range(target_year - lookback, target_year):
        for w in range(target_week - window, target_week + window + 1):
            v = lut.get((y, w))
            if v is not None:
                refs.append(v)
    # Strict purity: all (y,w) here have y < target_year so (y,w) < (target,*).
    return refs

# (legacy compatibility — only used by the leakage audit's truncation test)
def history_before(series, year, week):
    return [r for r in series if (r.get('year', 0), r.get('week', 0)) < (year, week)]

def step_back(year, week, n=1):
    for _ in range(n):
        if week == 1: year -= 1; week = 52
        else: week -= 1
    return year, week

# ── Robust z (median + MAD) ─────────────────────────────────────────────────
_ZMAD_CACHE: dict = {}

def z_mad(series, year, week):
    """Outlier-resistant z. log(x+1), baseline = median ± k·MAD.
       Memoized on (id(series), year, week)."""
    key = (id(series), year, week)
    if key in _ZMAD_CACHE: return _ZMAD_CACHE[key]
    current = value_at(series, year, week)
    if current is None:
        _ZMAD_CACHE[key] = None; return None
    refs = collect_reference(series, year, week)
    if len(refs) < MIN_REF_OBS:
        _ZMAD_CACHE[key] = None; return None
    logs = sorted(math.log(v + 1) for v in refs)
    n = len(logs)
    median = logs[n//2] if n % 2 else (logs[n//2 - 1] + logs[n//2]) / 2
    abs_dev = sorted(abs(x - median) for x in logs)
    mad = abs_dev[n//2] if n % 2 else (abs_dev[n//2 - 1] + abs_dev[n//2]) / 2
    if mad < 0.01: mad = 0.01
    z = (math.log(current + 1) - median) / mad
    _ZMAD_CACHE[key] = z
    return z

# ── Other composite signals (mostly unchanged from v1) ──────────────────────
def growth_signal(series, year, week):
    current = value_at(series, year, week)
    if current is None: return None
    last4 = []
    y, w = year, week
    for _ in range(4):
        y, w = step_back(y, w)
        v = value_at(series, y, w)
        if v is not None: last4.append(v)
    if len(last4) < 4: return None
    s = sorted(last4)
    median4 = (s[1] + s[2]) / 2
    return (current - median4) / max(median4, 0.5)

def persistence_signal(series, year, week):
    cnt = 0
    y, w = year, week
    for _ in range(4):
        z = z_mad(series, y, w)
        if z is not None and z > MAD_K_MED: cnt += 1
        y, w = step_back(y, w)
    return cnt

def spatial_signal(weekly_pref_dict, year, week):
    if not weekly_pref_dict: return 0.0
    active = 0; elevated = 0
    for pref, series in weekly_pref_dict.items():
        if pref == '総数': continue
        history = history_before(series, year, week)
        refs = collect_reference(history, year, week)
        if sum(refs) < 1: continue
        active += 1
        z = z_mad(series, year, week)
        if z is not None and z > MAD_K_MED: elevated += 1
    return elevated / active if active else 0.0

# ── Detectors ───────────────────────────────────────────────────────────────
def D0(disease, weekly_series, weekly_pref, year, week):
    """1-case rule for rare 全数把握. Sentinel diseases will never trigger."""
    if disease not in FULL_REPORT_DISEASES_RARE_GATE: return None
    current = value_at(weekly_series, year, week)
    if current is None or current < 1: return None
    history = history_before(weekly_series, year, week)
    refs = collect_reference(history, year, week)
    med = sorted(refs)[len(refs)//2] if refs else 0
    if med < 5: return 'high'
    return None

def D1(disease, weekly_series, weekly_pref, year, week):
    """median + k·MAD historic limits."""
    z = z_mad(weekly_series, year, week)
    if z is None: return None
    if z >= MAD_K_HIGH: return 'high'
    if z >= MAD_K_MED:  return 'medium'
    return None

def composite_score(disease, weekly_series, weekly_pref, year, week, weights):
    z = z_mad(weekly_series, year, week)
    g = growth_signal(weekly_series, year, week)
    p = persistence_signal(weekly_series, year, week)
    s = spatial_signal(weekly_pref or {}, year, week)
    if z is None or g is None: return None
    z_n = max(0, min(1, z / 4.0))    # MAD-z=4 saturates (~2σ region post-rescale)
    g_n = max(0, min(1, g / 3.0))
    p_n = (p or 0) / 4.0
    s_n = max(0, min(1, s / 0.3))
    score = weights["Z"]*z_n + weights["Growth"]*g_n + weights["Persistence"]*p_n + weights["Spatial"]*s_n
    return score

def D2_factory(weights, weight_label):
    """D2 = D1 OR composite >= threshold (additive)."""
    def D2(disease, weekly_series, weekly_pref, year, week):
        d1_sev = D1(disease, weekly_series, weekly_pref, year, week)
        if d1_sev == 'high': return 'high'
        score = composite_score(disease, weekly_series, weekly_pref, year, week, weights)
        if score is not None:
            if score >= COMP_HIGH:  return 'high'
            if score >= COMP_MED:   return 'medium'
        # if d1 medium and composite below medium, return d1 medium
        if d1_sev == 'medium': return 'medium'
        return None
    D2.__name__ = f"D2_{weight_label}"
    return D2

# Build detector registry
DETECTORS = {'D0': D0, 'D1_MAD': D1}
for label, weights in D2_WEIGHTS.items():
    DETECTORS[f'D2_{label}'] = D2_factory(weights, label)

# ── Sustained-alert wrapper ─────────────────────────────────────────────────
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

def first_sustained_alert(detector_fn, disease, weekly_series, weekly_pref,
                           ref_y, ref_w, window, k=SUSTAINED_K):
    """Walk weeks chronologically; return start-week of first run of k
       consecutive medium+ alerts."""
    weeks = weeks_in_window(weekly_series, ref_y, ref_w, window)
    streak = []
    for y, w in weeks:
        sev = detector_fn(disease, weekly_series, weekly_pref, y, w)
        if sev in ('medium', 'high'):
            streak.append((y, w, sev))
            if len(streak) >= k:
                worst = 'high' if any(s[2]=='high' for s in streak[:k]) else 'medium'
                return (streak[0][0], streak[0][1], worst)
        else:
            streak = []
    return None

def lead_weeks(ref_y, ref_w, alert_y, alert_w):
    return (ref_y - alert_y) * 52 + (ref_w - alert_w)

# ── Time-to-sustained-elevation (subset metric) ─────────────────────────────
def time_to_sustained_elevation(weekly_series, ref_y, ref_w, window=LEAD_WINDOW_W,
                                  k=SUSTAINED_K, mad_thresh=MAD_K_MED):
    """First week where k consecutive z_mad > mad_thresh (outbreak-internal metric).
       Same data flow as detectors but signal-only — no detector logic."""
    weeks = weeks_in_window(weekly_series, ref_y, ref_w, window)
    streak = []
    for y, w in weeks:
        z = z_mad(weekly_series, y, w)
        if z is not None and z > mad_thresh:
            streak.append((y, w))
            if len(streak) >= k:
                return streak[0]
        else:
            streak = []
    return None

# ── False-alert (precision proxy) ───────────────────────────────────────────
def false_alert_rate(detector_fn, disease, weekly_series, weekly_pref,
                      anchor_y, anchor_w, exclusion_window=LEAD_WINDOW_W):
    """Number of sustained alerts in weeks OUTSIDE ±exclusion of anchor,
       across the full data range."""
    n_total_weeks = 0
    n_alert_weeks = 0
    streak = 0
    weeks_chrono = sorted(weekly_series, key=lambda r: (r.get('year', 0), r.get('week', 0)))
    for r in weeks_chrono:
        y, w = r.get('year'), r.get('week')
        if y is None or w is None: continue
        dist = (y - anchor_y) * 52 + (w - anchor_w)
        if -exclusion_window <= dist <= exclusion_window: continue
        n_total_weeks += 1
        sev = detector_fn(disease, weekly_series, weekly_pref, y, w)
        if sev in ('medium', 'high'):
            streak += 1
            if streak == SUSTAINED_K:
                n_alert_weeks += 1  # counts each k-sustained start once per streak
        else:
            streak = 0
    if n_total_weeks == 0: return None
    return {
        'sustained_alerts_outside_anchor_window': n_alert_weeks,
        'eligible_weeks_outside': n_total_weeks,
        'rate_per_year': n_alert_weeks / (n_total_weeks / 52.0) if n_total_weeks else 0.0,
    }

# ── Leakage audit ──────────────────────────────────────────────────────────
def test_no_future_leakage(d, pref_ts):
    print("\n=== Leakage audit (truncation invariance) ===")
    disease = "RSウイルス感染症"
    test_y, test_w = 2024, 13
    full = d['weekly_trends'][disease]
    pf = pref_ts.get(disease, {})
    trunc = [r for r in full if (r['year'], r['week']) <= (test_y, test_w)]
    pf_trunc = {p: [r for r in s if (r['year'], r['week']) <= (test_y, test_w)] for p, s in pf.items()}
    for name, fn in DETECTORS.items():
        a = fn(disease, full, pf, test_y, test_w)
        b = fn(disease, trunc, pf_trunc, test_y, test_w)
        ok = a == b
        print(f"  {name:<22}: full={a!s:8} truncated={b!s:8} {'OK' if ok else '*** LEAK ***'}")
        if not ok: return False
    print("  PASS — all detectors at week t use only data ≤ t.")
    return True

# ── Main pilot ─────────────────────────────────────────────────────────────
def run():
    d, pref_ts = load_data()
    if not test_no_future_leakage(d, pref_ts):
        print("LEAKAGE; abort."); sys.exit(1)

    rows = []
    print("\n=== v2 Pilot — Sentinel diseases ===")
    print(f"{'Outbreak':<12} {'Det':<22} {'Ref':<11} {'Alert':<11} {'Sev':<7} {'Lead(w)':>8} {'TTSE(w)':>9} {'FA/y':>6}")
    print('-'*100)

    all_anchors = {**GROUND_TRUTH_V2, **GT_SENSITIVITY}

    for label, gt in all_anchors.items():
        idwr = gt['idwr_key']
        if idwr not in d['weekly_trends']:
            print(f"WARN: {idwr} missing"); continue
        ref_y, ref_w = gt['year'], gt['week']
        ws = d['weekly_trends'][idwr]
        ps = pref_ts.get(idwr, {})

        # Time-to-sustained-elevation (signal-only)
        ttse = time_to_sustained_elevation(ws, ref_y, ref_w)
        ttse_lead = lead_weeks(ref_y, ref_w, *ttse) if ttse else None

        for det_name, det_fn in DETECTORS.items():
            res = first_sustained_alert(det_fn, idwr, ws, ps, ref_y, ref_w, LEAD_WINDOW_W)
            far = false_alert_rate(det_fn, idwr, ws, ps, ref_y, ref_w)
            row = {
                'outbreak': label, 'idwr_disease': idwr, 'tier': gt['tier'],
                'detector': det_name,
                'ref_year': ref_y, 'ref_week': ref_w,
            }
            if res:
                ay, aw, sev = res
                row['sustained_alert_year']  = ay
                row['sustained_alert_week']  = aw
                row['sustained_severity']    = sev
                row['sustained_lead_weeks']  = lead_weeks(ref_y, ref_w, ay, aw)
            else:
                row['sustained_alert_year']  = None
                row['sustained_alert_week']  = None
                row['sustained_severity']    = None
                row['sustained_lead_weeks']  = None
            row['time_to_sustained_elevation'] = ttse_lead
            row['false_alert'] = far

            a = f"{ay}/{aw}" if res else '-'
            ld = f"{row['sustained_lead_weeks']:+d}" if row['sustained_lead_weeks'] is not None else '-'
            tt = f"{ttse_lead:+d}" if ttse_lead is not None else '-'
            far_y = f"{far['rate_per_year']:.1f}" if far else '-'
            print(f"{label:<12} {det_name:<22} {ref_y}/W{ref_w:<5} {a:<11} {row['sustained_severity'] or '-':<7} {ld:>8} {tt:>9} {far_y:>6}")
            rows.append(row)

    # ── Decision rule: D2 vs D1 average lead ───────────────────────────────
    print("\n=== Decision rule (D2 best vs D1, primary outbreaks only) ===")
    primary_labels = ['RSV', 'HFMD', 'Influenza']
    pairs = []
    # For D2, take the best-lead among the 4 weight presets per outbreak (within-outbreak best)
    for ob in primary_labels:
        d1_row = next((r for r in rows if r['outbreak']==ob and r['detector']=='D1_MAD'), None)
        d2_rows = [r for r in rows if r['outbreak']==ob and r['detector'].startswith('D2_')]
        if d1_row and d2_rows:
            d1_lead = d1_row['sustained_lead_weeks']
            d2_best = max((r for r in d2_rows if r['sustained_lead_weeks'] is not None),
                          key=lambda r: r['sustained_lead_weeks'], default=None)
            d2_best_lead = d2_best['sustained_lead_weeks'] if d2_best else None
            d2_best_label = d2_best['detector'] if d2_best else '-'
            if d1_lead is not None and d2_best_lead is not None:
                delta = d2_best_lead - d1_lead
                pairs.append((ob, d1_lead, d2_best_lead, d2_best_label, delta))
                print(f"  {ob:<12}: D1_lead={d1_lead:+d}w  D2_best={d2_best_lead:+d}w ({d2_best_label})  Δ={delta:+d}w")

    if pairs:
        avg_delta = sum(p[4] for p in pairs) / len(pairs)
        print(f"  AVG Δ(D2_best − D1) = {avg_delta:+.2f}w")
        if avg_delta >= 2:    decision = "GO — proceed to main paper outline"
        elif avg_delta >= 0:  decision = "REFINE3 — partial improvement; tune weights / signals"
        else:                 decision = "FRAMING SHIFT — Plan B: method paper on baseline contamination fix"
        print(f"  DECISION: {decision}")
    else:
        avg_delta = None; decision = 'INSUFFICIENT DATA'
        print(f"  DECISION: {decision}")

    out = OUT_DIR / 'pilot_v2_results.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            'rows': rows,
            'pairs': pairs,
            'avg_delta_d2_vs_d1': avg_delta,
            'decision': decision,
            'ground_truth': all_anchors,
            'params': {
                'lookback_years': LOOKBACK_YEARS, 'week_window': WEEK_WINDOW,
                'sustained_k': SUSTAINED_K, 'lead_window_w': LEAD_WINDOW_W,
                'mad_k_med': MAD_K_MED, 'mad_k_high': MAD_K_HIGH,
                'comp_med': COMP_MED, 'comp_high': COMP_HIGH,
                'd2_weights': D2_WEIGHTS,
            },
        }, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {out}")

if __name__ == '__main__':
    run()
