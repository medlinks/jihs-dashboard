"""
detect_anomalies_v2.py — 4-detector framework for IDWR/JIHS surveillance.

Replaces the v1 two-layer system in scripts/detect_anomalies.py with:

  D_rare        — 1-case rule for 全数把握 with rare gate (5y same-week median < 5)
  D_stat        — median + k·MAD historic limits, gated by baseline stability
  D_growth      — sustained slope + dynamic absolute-count floor
  D_spatial     — fraction of active prefectures elevated in current week
                  (with optional urban_tier stratified variant)

Final alert = D_rare ∪ D_stat ∪ D_growth ∪ D_spatial, each tagged by which
detector(s) fired. Sustained-alert wrapper (k=3 consecutive medium+ weeks)
is the default reporting unit.

As-of-week-t purity: every internal helper accepts (year, week) and only
reads data with (y, w) ≤ target. Truncation-invariance unit test included.

This module is self-contained and re-runnable; it does not modify any
existing dashboard or scripts/ files.
"""
from __future__ import annotations
import math
import json
from pathlib import Path
from collections import defaultdict

# ── Constants (extracted from scripts/detect_anomalies.py) ─────────────────
FULL_REPORT_DISEASES = {
    # 1類
    'エボラ出血熱','クリミア・コンゴ出血熱','痘そう','南米出血熱','ペスト','マールブルグ病','ラッサ熱',
    # 2類
    '急性灰白髄炎','結核','ジフテリア','重症急性呼吸器症候群','中東呼吸器症候群',
    '鳥インフルエンザ（Ｈ５Ｎ１）','鳥インフルエンザ（Ｈ７Ｎ９）',
    # 3類
    'コレラ','細菌性赤痢','腸管出血性大腸菌感染症','腸チフス','パラチフス',
    # 4類
    'Ｅ型肝炎','ウエストナイル熱','Ａ型肝炎','エキノコックス症','エムポックス','黄熱','オウム病',
    'オムスク出血熱','回帰熱','キャサヌル森林病','Ｑ熱','狂犬病','コクシジオイデス症',
    'ジカウイルス感染症','重症熱性血小板減少症候群','腎症候性出血熱','西部ウマ脳炎','ダニ媒介脳炎',
    '炭疽','チクングニア熱','つつが虫病','デング熱','東部ウマ脳炎','鳥インフルエンザ(Ｈ５Ｎ１を除く）',
    'ニパウイルス感染症','日本紅斑熱','日本脳炎','ハンタウイルス肺症候群','Ｂウイルス病','鼻疽',
    'ブルセラ症','ベネズエラウマ脳炎','ヘンドラウイルス感染症','発しんチフス','ボツリヌス症',
    'マラリア','野兎病','ライム病','リッサウイルス感染症','リフトバレー熱','類鼻疽','レジオネラ症',
    'レプトスピラ症','ロッキー山紅斑熱',
    # 5類全数把握
    'アメーバ赤痢','ウイルス性肝炎','カルバペネム耐性腸内細菌目細菌感染症','急性弛緩性麻痺','急性脳炎',
    'クリプトスポリジウム症','クロイツフェルト・ヤコブ病','劇症型溶血性レンサ球菌感染症',
    '後天性免疫不全症候群','ジアルジア症','侵襲性インフルエンザ菌感染症','侵襲性髄膜炎菌感染症',
    '侵襲性肺炎球菌感染症','水痘（入院例）','水痘（入院例に限る）','先天性風しん症候群',
    '多剤耐性緑膿菌感染症','梅毒','播種性クリプトコックス症','破傷風',
    'バンコマイシン耐性黄色ブドウ球菌感染症','バンコマイシン耐性腸球菌感染症','百日咳',
    '風しん','麻しん','薬剤耐性アシネトバクター感染症',
}

# Parameters
LOOKBACK_YEARS = 5
WEEK_WINDOW    = 2
MIN_REF_OBS    = 8
SUSTAINED_K    = 3

# D_rare
RARE_BASELINE_THRESHOLD = 5

# D_stat (median + k·MAD)
MAD_K_MED  = 2.0
MAD_K_HIGH = 3.0
STABILITY_MIN_RATIO = 0.5  # MAD/median ≥ 0.5 → unstable; < 0.5 → stable
STABILITY_MIN_MEDIAN = 1.0  # if median < 1 case, baseline is essentially zero — not "stable"

# D_growth — dynamic floor lookup by historical median
def growth_floor_for(median_baseline: float) -> int:
    """Dynamic absolute-count floor. Higher median → higher floor (avoid noise)."""
    if median_baseline < 5:   return 5
    if median_baseline < 50:  return 10
    return 50

GROWTH_SUSTAINED = 3
GROWTH_SLOPE_IQR_K = 1.5

# D_spatial
SPATIAL_FLAT_THRESH = 0.25
SPATIAL_TIER_THRESH = 0.40

# ── Cache for value-at lookups ──────────────────────────────────────────────
_LUT: dict = {}

def _lookup(series):
    sid = id(series)
    if sid not in _LUT:
        _LUT[sid] = {(r['year'], r['week']): r.get('total')
                     for r in series
                     if r.get('year') is not None and r.get('week') is not None}
    return _LUT[sid]

def value_at(series, year, week):
    return _lookup(series).get((year, week))

def collect_reference(series, target_year, target_week,
                      lookback=LOOKBACK_YEARS, window=WEEK_WINDOW):
    """Past lookback years' same-week ±window values. Strict y < target_year purity."""
    lut = _lookup(series)
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

# ── Z-MAD ───────────────────────────────────────────────────────────────────
_ZMAD_CACHE: dict = {}

def z_mad(series, year, week):
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

def baseline_median_and_mad(series, year, week):
    """Return (median_count, MAD_count, stability_flag) on RAW (non-log) scale."""
    refs = collect_reference(series, year, week)
    if len(refs) < MIN_REF_OBS: return None, None, False
    refs_sorted = sorted(refs)
    n = len(refs_sorted)
    median = refs_sorted[n//2] if n % 2 else (refs_sorted[n//2 - 1] + refs_sorted[n//2]) / 2
    abs_dev = sorted(abs(v - median) for v in refs_sorted)
    mad = abs_dev[n//2] if n % 2 else (abs_dev[n//2 - 1] + abs_dev[n//2]) / 2
    # Stability: median ≥ 1 case AND MAD/median < STABILITY_MIN_RATIO
    if median < STABILITY_MIN_MEDIAN: stable = False
    else:
        stable = (mad / max(median, 0.5)) < STABILITY_MIN_RATIO
    return median, mad, stable

# ── Detectors ───────────────────────────────────────────────────────────────
def D_rare(disease, weekly_series, prefecture_pref, year, week):
    """Layer-1 1-case alert for rare 全数把握 diseases.
       Triggers iff: disease ∈ FULL_REPORT_DISEASES AND current ≥ 1
                    AND past-5y same-week median < RARE_BASELINE_THRESHOLD."""
    if disease not in FULL_REPORT_DISEASES: return None
    current = value_at(weekly_series, year, week)
    if current is None or current < 1: return None
    median_count, _, _ = baseline_median_and_mad(weekly_series, year, week)
    if median_count is None: return None
    if median_count >= RARE_BASELINE_THRESHOLD: return None
    return 'high'

def D_stat(disease, weekly_series, prefecture_pref, year, week):
    """Median + k·MAD historic limits, gated by baseline-stability check.
       Only fires if baseline is 'stable' (median ≥ 1, MAD/median < 0.5)."""
    median_count, mad, stable = baseline_median_and_mad(weekly_series, year, week)
    if not stable: return None  # baseline not stable — defer to D_growth
    z = z_mad(weekly_series, year, week)
    if z is None: return None
    if z >= MAD_K_HIGH: return 'high'
    if z >= MAD_K_MED:  return 'medium'
    return None

def _growth_history(series, year, week, n=12):
    """Past n-week WoW slopes (current_value − prev_value) up to t-1."""
    slopes = []
    y, w = year, week
    # walk back 1 step first to start at t-1
    y, w = step_back(y, w)
    for _ in range(n):
        v_now = value_at(series, y, w)
        py, pw = step_back(y, w)
        v_prev = value_at(series, py, pw)
        if v_now is None or v_prev is None: break
        slopes.append(v_now - v_prev)
        y, w = py, pw
    return slopes

def D_growth(disease, weekly_series, prefecture_pref, year, week):
    """Sustained slope + dynamic absolute-count floor.
       Triggers iff current count ≥ floor (function of historical median)
       AND current 4-week slope > median(history_slopes) + 1.5·IQR(history_slopes)
       AND >=2 of the last 3 weeks also exceeded that threshold."""
    current = value_at(weekly_series, year, week)
    if current is None or current < 1: return None
    median_baseline, _, _ = baseline_median_and_mad(weekly_series, year, week)
    floor = growth_floor_for(median_baseline or 0)
    if current < floor: return None
    # Compute current slope (last 4 weeks)
    slopes_last4 = []
    y, w = year, week
    for _ in range(4):
        v_now = value_at(weekly_series, y, w)
        py, pw = step_back(y, w)
        v_prev = value_at(weekly_series, py, pw)
        if v_now is None or v_prev is None: return None
        slopes_last4.append(v_now - v_prev)
        y, w = py, pw
    current_slope = sum(slopes_last4) / len(slopes_last4)
    # History slopes (12 weeks back, ending at t-1)
    history_slopes = _growth_history(weekly_series, year, week, n=12)
    if len(history_slopes) < 8: return None
    history_slopes_sorted = sorted(history_slopes)
    n = len(history_slopes_sorted)
    median_slope = history_slopes_sorted[n//2] if n % 2 else (history_slopes_sorted[n//2-1]+history_slopes_sorted[n//2])/2
    q1 = history_slopes_sorted[n//4]
    q3 = history_slopes_sorted[3*n//4]
    iqr = max(q3 - q1, 1.0)
    threshold = median_slope + GROWTH_SLOPE_IQR_K * iqr
    if current_slope <= threshold: return None
    # severity: 'high' if current also > median_baseline × 2; else 'medium'
    if median_baseline and current >= 2 * median_baseline: return 'high'
    return 'medium'

def D_spatial(disease, weekly_series, prefecture_pref, year, week,
              urban_tier_map=None):
    """Fraction of active prefectures with z_mad > MAD_K_MED in current week.
       Returns dict {flat: severity, by_tier: {tier: severity}} OR severity.
       Caller controls return type via urban_tier_map presence."""
    if not prefecture_pref:
        return None
    active = 0; elevated = 0
    by_tier = defaultdict(lambda: {'active': 0, 'elevated': 0})
    for pref, series in prefecture_pref.items():
        if pref == '総数': continue
        refs = collect_reference(series, year, week)
        if sum(refs) < 1: continue
        active += 1
        z = z_mad(series, year, week)
        is_elevated = (z is not None and z > MAD_K_MED)
        if is_elevated: elevated += 1
        if urban_tier_map:
            tier = urban_tier_map.get(pref)
            if tier:
                by_tier[tier]['active'] += 1
                if is_elevated: by_tier[tier]['elevated'] += 1
    if active == 0: return None
    flat_pct = elevated / active
    flat_sev = 'high' if flat_pct >= 0.5 else ('medium' if flat_pct >= SPATIAL_FLAT_THRESH else None)
    if not urban_tier_map:
        return flat_sev
    # tier-aware
    tier_sev = {}
    for tier, agg in by_tier.items():
        if agg['active'] == 0: continue
        pct = agg['elevated'] / agg['active']
        if pct >= 0.6: tier_sev[tier] = 'high'
        elif pct >= SPATIAL_TIER_THRESH: tier_sev[tier] = 'medium'
    return {
        'flat': flat_sev, 'flat_pct': flat_pct,
        'by_tier': tier_sev,
        'tier_active_counts': {t: by_tier[t]['active'] for t in by_tier},
        'tier_elevated_counts': {t: by_tier[t]['elevated'] for t in by_tier},
    }

# ── Combined detector + sustained wrapper ──────────────────────────────────
def all_detectors(disease, weekly_series, prefecture_pref, year, week, urban_tier_map=None):
    """Run all 4 detectors. Return dict of {detector_name: severity (or detail)}."""
    return {
        'D_rare':    D_rare(disease, weekly_series, prefecture_pref, year, week),
        'D_stat':    D_stat(disease, weekly_series, prefecture_pref, year, week),
        'D_growth':  D_growth(disease, weekly_series, prefecture_pref, year, week),
        'D_spatial': D_spatial(disease, weekly_series, prefecture_pref, year, week, urban_tier_map),
    }

def severity_rank(sev):
    return {'high': 2, 'medium': 1, None: 0}.get(sev, 0)

def combined_severity(per_det):
    """OR of all detectors. D_spatial returns a dict — extract its 'flat' field."""
    sevs = []
    for k, v in per_det.items():
        if k == 'D_spatial' and isinstance(v, dict):
            sevs.append(v.get('flat'))
        else:
            sevs.append(v)
    sevs = [s for s in sevs if s]
    if not sevs: return None
    if 'high' in sevs: return 'high'
    return 'medium'

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

def first_sustained_alert(detector_severity_fn, weeks_iter, k=SUSTAINED_K):
    """Walk weeks chronologically; first run of k consecutive medium+ alerts.
       detector_severity_fn(year, week) → 'high'/'medium'/None.
       Returns (start_year, start_week, severity_in_streak) or None."""
    streak = []
    for y, w in weeks_iter:
        sev = detector_severity_fn(y, w)
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

# ── Leakage audit ───────────────────────────────────────────────────────────
def test_no_future_leakage(weekly_trends, pref_ts, urban_tier_map):
    """For a fixed (disease, year, week), verify each detector returns identical
       output on full vs truncated input."""
    results = []
    test_cases = [
        ('麻しん', 2026, 5),
        ('風しん', 2018, 30),
    ]
    for disease, ty, tw in test_cases:
        if disease not in weekly_trends: continue
        full = weekly_trends[disease]
        trunc = [r for r in full if (r['year'], r['week']) <= (ty, tw)]
        pf = pref_ts.get(disease, {})
        pf_trunc = {p: [r for r in s if (r['year'], r['week']) <= (ty, tw)] for p, s in pf.items()}
        # Reset cache to avoid stale lookup
        _LUT.clear(); _ZMAD_CACHE.clear()
        full_res = all_detectors(disease, full, pf, ty, tw, urban_tier_map)
        _LUT.clear(); _ZMAD_CACHE.clear()
        trunc_res = all_detectors(disease, trunc, pf_trunc, ty, tw, urban_tier_map)
        for det in ('D_rare', 'D_stat', 'D_growth'):
            ok = full_res[det] == trunc_res[det]
            results.append((disease, ty, tw, det, full_res[det], trunc_res[det], ok))
        # D_spatial: compare flat field
        full_sp = full_res['D_spatial']
        trunc_sp = trunc_res['D_spatial']
        full_flat = full_sp.get('flat') if isinstance(full_sp, dict) else full_sp
        trunc_flat = trunc_sp.get('flat') if isinstance(trunc_sp, dict) else trunc_sp
        results.append((disease, ty, tw, 'D_spatial', full_flat, trunc_flat, full_flat == trunc_flat))
    return results

# ── Main test runner ────────────────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    print('=== detect_anomalies_v2 — leakage audit ===\n')
    DATA_FILE = Path('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json')
    PREF_TS_FILE = Path('/sessions/cool-clever-goldberg/mnt/outputs/pref_timeseries_sentinel.json')
    PREF_TS_3DIS = Path('/sessions/cool-clever-goldberg/mnt/outputs/pref_timeseries_3diseases.json')
    URBAN_TIER_FILE = Path('/sessions/cool-clever-goldberg/mnt/claude/prefecture_did_classification.json')

    with open(DATA_FILE) as f: dash = json.load(f)
    pref_ts = {}
    if PREF_TS_FILE.exists():
        with open(PREF_TS_FILE) as f: pref_ts.update(json.load(f))
    if PREF_TS_3DIS.exists():
        with open(PREF_TS_3DIS) as f: pref_ts.update(json.load(f))
    with open(URBAN_TIER_FILE) as f: did = json.load(f)
    urban_tier_map = {p: did[p]['urban_tier_did'] for p in did}

    res = test_no_future_leakage(dash['weekly_trends'], pref_ts, urban_tier_map)
    all_ok = True
    for disease, y, w, det, full_v, trunc_v, ok in res:
        marker = 'OK' if ok else '*** LEAK ***'
        print(f'  {disease:<6} {y}/W{w:<2} {det:<10}: full={full_v!s:<8} trunc={trunc_v!s:<8} {marker}')
        if not ok: all_ok = False
    print('\n' + ('PASS — all detectors at week t use only data ≤ t.' if all_ok else 'FAIL — leakage detected.'))
    if not all_ok: sys.exit(1)
