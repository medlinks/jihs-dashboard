"""
Pilot retrospective: lead-time evaluation for D0 / D1 / D2 detectors
on three Japanese IDWR outbreaks.

Strict as-of-week-t purity: every signal at time t uses only data with
(year, week) <= (t.year, t.week). The value AT week t is the
"first reported value the system would see at the close of that week";
we have no historical revision logs, so we use the snapshot value
(noted as limitation L1 in the report).

Detectors:
  D0 = single-signal z (log-transformed historic limits, z>=2 medium, z>=3 high)
  D1 = existing two-layer from detect_anomalies.py
       Layer 1: 1-case alert for 感染症法 全数把握 with 5y same-week median < 5
       Layer 2: same z-rule as D0
  D2 = 4-signal composite
       Score = 0.35 * Z + 0.20 * Growth + 0.20 * Persistence + 0.25 * Spatial
       AlertScore >= 0.7 high; >= 0.5 medium

Usage:
  python3 pilot_lead_time.py
"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

# ── Paths ───────────────────────────────────────────────────────────────────
DATA_FILE = Path('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json')
PREF_TS_FILE = Path('/sessions/cool-clever-goldberg/mnt/outputs/pref_timeseries_3diseases.json')
OUT_DIR   = Path('/sessions/cool-clever-goldberg/mnt/outputs')

# IDWR sheet names — note 風疹 is officially 風しん in IDWR
DISEASE_KEY_MAP = {
    "梅毒": "梅毒",
    "麻しん": "麻しん",
    "風疹": "風しん",  # ground truth uses 風疹, IDWR uses 風しん
}

# ── Constants from existing repo ────────────────────────────────────────────
# Copied verbatim from scripts/detect_anomalies.py
FULL_REPORT_DISEASES = {
    # 1類
    'エボラ出血熱','クリミア・コンゴ出血熱','痘そう','南米出血熱','ペスト','マールブルグ病','ラッサ熱',
    # 2類
    '急性灰白髄炎','結核','ジフテリア','重症急性呼吸器症候群','中東呼吸器症候群',
    '鳥インフルエンザ（Ｈ５Ｎ１）','鳥インフルエンザ（Ｈ７Ｎ９）',
    # 3類
    'コレラ','細菌性赤痢','腸管出血性大腸菌感染症','腸チフス','パラチフス',
    # 4類 (truncated for brevity — match repo)
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

LOOKBACK_YEARS = 5
WEEK_WINDOW    = 2     # ±2 weeks
RARE_BASELINE  = 5     # 5y same-week median < 5 → "rare"
Z_MED, Z_HIGH  = 2.0, 3.0
MIN_REF_OBS    = 8

# ── Ground truth (curated by research agent — see pilot report Section 1) ──
GROUND_TRUTH = {
    "梅毒": {
        "year": 2024, "week": 1,
        "tier": "silver",
        "source_url": "https://id-info.jihs.go.jp/ (NIID IASR annual review proxy)",
        "source_type": "baseline anchor (chronic endemic, no discrete onset)",
        "justification": "Syphilis is a multi-year rising endemic; no discrete outbreak start. Anchor at 2024 W1 represents the start of the surveillance year; lead time on this anchor measures whether each detector flags the 2024 surge before mid-year.",
        "caveat": "Lead-time semantics for chronic outbreaks are weaker than for acute. The detector that 'fires earliest in 2024' is not necessarily superior; we report it for completeness but exclude it from the D2-vs-D1 ≥2-week decision rule.",
    },
    "麻しん": {
        "year": 2026, "week": 5,
        "tier": "b",
        "source_url": "https://id-info.jihs.go.jp/en/surveillance/idwr/featured/2026/06/index.html",
        "source_type": "JIHS featured bulletin (genotype-based confirmation, week 5 = 15 cases first cluster)",
        "justification": "Week 5 (Feb 3–9, 2026) is the first week JIHS featured measles in a special bulletin citing genotype B3/D8 imported-case clusters; before W5 the country had only sporadic single cases.",
        "caveat": "JIHS bulletin is partly IDWR-derived; we accept it because it adds independent genotype confirmation as the trigger for the bulletin (not raw count threshold).",
    },
    "風疹": {
        "year": 2018, "week": 30,
        "tier": "c",
        "source_url": "https://www.niid.go.jp/niid/ja/typhi-m/iasr-reference/2538-related-articles/related-articles-465/8463-465r05.html",
        "source_type": "peer-reviewed retrospective (IASR Vol.40 No.8, May 2019; Sugishita et al.)",
        "justification": "IASR retrospective analysis defines W30 (Jul 23–29, 2018) as the inflection week in south Kanto: 19 cases, marking start of 2018-19 nationwide outbreak. NIID issued public alert at W33 (Aug 15) but post-hoc epi assigned start to W30.",
        "caveat": None,
    },
}

# ── Load data ───────────────────────────────────────────────────────────────
def load_data():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        d = json.load(f)
    with open(PREF_TS_FILE, 'r', encoding='utf-8') as f:
        pref_ts = json.load(f)  # {disease_idwr: {pref: [{year, week, total}]}}
    d['pref_ts'] = pref_ts
    return d

# ── Helpers (purity-respecting) ────────────────────────────────────────────
def history_before(series, year, week):
    """Strictly < (year, week) — no leakage."""
    return [r for r in series if (r.get('year', 0), r.get('week', 0)) < (year, week)]

def value_at(series, year, week):
    for r in series:
        if r.get('year') == year and r.get('week') == week:
            return r.get('total')
    return None

def collect_reference(history, target_year, target_week,
                      lookback=LOOKBACK_YEARS, window=WEEK_WINDOW):
    refs = []
    for r in history:
        y, w, v = r.get('year'), r.get('week'), r.get('total')
        if y is None or w is None or v is None: continue
        if not (target_year - lookback <= y <= target_year - 1): continue
        if abs(w - target_week) <= window:
            refs.append(v)
    return refs

# ── Signals ─────────────────────────────────────────────────────────────────
def z_seasonal(series, year, week):
    """Log-transformed historic-limits z-score using past 5y same-week ±2w."""
    current = value_at(series, year, week)
    if current is None: return None
    history = history_before(series, year, week)
    refs = collect_reference(history, year, week)
    if len(refs) < MIN_REF_OBS: return None
    logs = [math.log(v + 1) for v in refs]
    m = sum(logs) / len(logs)
    if len(logs) > 1:
        var = sum((x - m) ** 2 for x in logs) / (len(logs) - 1)
        s = math.sqrt(var) if var > 0 else 0.01
    else:
        s = 0.01
    return (math.log(current + 1) - m) / max(s, 0.01)

def step_back(year, week, n=1):
    """Walk back n ISO-week steps. Crude (52w year, ignores ISO 53)."""
    for _ in range(n):
        if week == 1:
            year -= 1; week = 52
        else:
            week -= 1
    return year, week

def growth_signal(series, year, week):
    """(current - median(t-4..t-1)) / max(median, 0.5)."""
    current = value_at(series, year, week)
    if current is None: return None
    last4 = []
    y, w = year, week
    for _ in range(4):
        y, w = step_back(y, w)
        v = value_at(series, y, w)
        if v is not None: last4.append(v)
    if len(last4) < 4: return None
    sorted4 = sorted(last4)
    median4 = (sorted4[1] + sorted4[2]) / 2
    return (current - median4) / max(median4, 0.5)

def persistence_signal(series, year, week):
    """Count of past 4 weeks (incl. current) with z_seasonal > 2."""
    cnt = 0
    y, w = year, week
    for _ in range(4):
        z = z_seasonal(series, y, w)
        if z is not None and z > 2: cnt += 1
        y, w = step_back(y, w)
    return cnt

def spatial_signal(weekly_pref_dict, year, week):
    """Fraction of ACTIVE prefectures (past-5y same-week ±2 sum >= 1)
       with z_seasonal > 2 in current week."""
    if not weekly_pref_dict: return 0.0
    active = 0; elevated = 0
    for pref, series in weekly_pref_dict.items():
        if pref == '総数': continue
        history = history_before(series, year, week)
        refs = collect_reference(history, year, week)
        if sum(refs) < 1: continue  # not active
        active += 1
        z = z_seasonal(series, year, week)
        if z is not None and z > 2: elevated += 1
    return elevated / active if active else 0.0

# ── Detectors ───────────────────────────────────────────────────────────────
def D0(disease, weekly_series, weekly_pref, year, week):
    z = z_seasonal(weekly_series, year, week)
    if z is None: return None
    if z >= Z_HIGH: return 'high'
    if z >= Z_MED:  return 'medium'
    return None

def D1(disease, weekly_series, weekly_pref, year, week):
    """Two-layer matching detect_anomalies.py."""
    current = value_at(weekly_series, year, week)
    if current is None: return None
    # Layer 1: 1-case alert for rare 全数把握
    if disease in FULL_REPORT_DISEASES and current >= 1:
        history = history_before(weekly_series, year, week)
        refs = collect_reference(history, year, week)
        if refs:
            srt = sorted(refs)
            med = srt[len(srt)//2]
        else:
            med = 0
        if med < RARE_BASELINE:
            return 'high'
    # Layer 2: z-rule (skip MIN_CURRENT_VALUE filter to detect early)
    return D0(disease, weekly_series, weekly_pref, year, week)

def D2(disease, weekly_series, weekly_pref, year, week):
    """4-signal composite."""
    z = z_seasonal(weekly_series, year, week)
    g = growth_signal(weekly_series, year, week)
    p = persistence_signal(weekly_series, year, week)
    s = spatial_signal(weekly_pref or {}, year, week)
    if z is None or g is None: return None
    z_n = max(0, min(1, z / 4.0))
    g_n = max(0, min(1, g / 3.0))
    p_n = (p or 0) / 4.0
    s_n = max(0, min(1, s / 0.3))
    score = 0.35*z_n + 0.20*g_n + 0.20*p_n + 0.25*s_n
    if score >= 0.7: return 'high'
    if score >= 0.5: return 'medium'
    return None

DETECTORS = {'D0': D0, 'D1': D1, 'D2': D2}

# ── Lead-time evaluation ───────────────────────────────────────────────────
def weeks_in_window(weekly_series, ref_year, ref_week, window=26):
    """Return chronologically-sorted (year, week) tuples within ±window of ref."""
    target = ref_year * 100 + ref_week  # crude ordinal (works for ISO week numbers)
    out = []
    for r in weekly_series:
        y, w = r.get('year'), r.get('week')
        if y is None or w is None: continue
        # crude week distance via 52-week year approximation
        dist = (y - ref_year) * 52 + (w - ref_week)
        if -window <= dist <= window:
            out.append((dist, y, w))
    out.sort()
    return [(y, w) for d, y, w in out]

def first_alert_week(detector_fn, disease, weekly_series, weekly_pref,
                     ref_year, ref_week, window=26):
    """Walk weeks ref-26..ref+26 in order; return first (year, week) producing
       'medium' or 'high'. None if never alerts in window."""
    for y, w in weeks_in_window(weekly_series, ref_year, ref_week, window):
        sev = detector_fn(disease, weekly_series, weekly_pref, y, w)
        if sev in ('medium', 'high'):
            return (y, w, sev)
    return None

def lead_time_weeks(ref_year, ref_week, alert_year, alert_week):
    """ref - alert in weeks. Positive = detector fires BEFORE reference (good)."""
    return (ref_year - alert_year) * 52 + (ref_week - alert_week)

# ── Leakage unit test ──────────────────────────────────────────────────────
def test_no_future_leakage():
    """Verify that detectors at (year, week) produce identical results
       whether or not future data is present (truncation invariance)."""
    print("\n=== Leakage audit ===")
    data = load_data()
    wt = data['weekly_trends']
    pref_ts = data['pref_ts']
    disease = '麻しん'
    test_year, test_week = 2026, 5
    series_full = wt[disease]
    pref_full = pref_ts.get(disease, {})

    series_truncated = [r for r in series_full
                        if (r['year'], r['week']) <= (test_year, test_week)]
    pref_truncated = {p: [r for r in s if (r['year'], r['week']) <= (test_year, test_week)]
                      for p, s in pref_full.items()}
    for name, fn in DETECTORS.items():
        r_full = fn(disease, series_full, pref_full, test_year, test_week)
        r_trunc = fn(disease, series_truncated, pref_truncated, test_year, test_week)
        match = r_full == r_trunc
        print(f"  {name}({disease} W{test_week}/{test_year}): full={r_full!s:8} truncated={r_trunc!s:8} {'OK' if match else 'LEAKAGE'}")
        if not match:
            return False
    print("  PASS: detectors at week t use only data ≤ t (truncation invariance).")
    return True

# ── Main pilot ──────────────────────────────────────────────────────────────
def run_pilot():
    data = load_data()
    wt = data['weekly_trends']
    pref_ts = data['pref_ts']

    rows = []
    for disease, gt in GROUND_TRUTH.items():
        idwr_key = DISEASE_KEY_MAP.get(disease, disease)
        if idwr_key not in wt:
            print(f"WARN: {idwr_key} not in weekly_trends; skipping")
            continue
        ref_y, ref_w = gt['year'], gt['week']
        weekly_series = wt[idwr_key]
        weekly_pref   = pref_ts.get(idwr_key, {})
        for det_name, det_fn in DETECTORS.items():
            res = first_alert_week(det_fn, idwr_key, weekly_series, weekly_pref,
                                   ref_y, ref_w, window=26)
            if res is None:
                rows.append({
                    'disease': disease, 'detector': det_name,
                    'ref_year': ref_y, 'ref_week': ref_w,
                    'alert_year': None, 'alert_week': None, 'severity': None,
                    'lead_weeks': None, 'note': 'no alert in ±26w window',
                })
            else:
                a_y, a_w, sev = res
                lt = lead_time_weeks(ref_y, ref_w, a_y, a_w)
                rows.append({
                    'disease': disease, 'detector': det_name,
                    'ref_year': ref_y, 'ref_week': ref_w,
                    'alert_year': a_y, 'alert_week': a_w, 'severity': sev,
                    'lead_weeks': lt, 'note': '',
                })
    return rows

if __name__ == '__main__':
    if not test_no_future_leakage():
        print("LEAKAGE DETECTED — abort.")
        sys.exit(1)

    rows = run_pilot()

    print("\n=== Pilot Lead-Time Matrix ===")
    print(f"{'Disease':<10} {'Detector':<5} {'RefY/W':<10} {'AlertY/W':<10} {'Sev':<7} {'Lead(w)':<8} Note")
    for r in rows:
        a = f"{r['alert_year']}/{r['alert_week']}" if r['alert_year'] else '-'
        ref = f"{r['ref_year']}/{r['ref_week']}"
        lt = f"{r['lead_weeks']:+d}" if r['lead_weeks'] is not None else '-'
        print(f"{r['disease']:<10} {r['detector']:<5} {ref:<10} {a:<10} {r['severity'] or '-':<7} {lt:<8} {r['note']}")

    # Save JSON for the report
    out_json = OUT_DIR / 'pilot_lead_time_results.json'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump({
            'ground_truth': GROUND_TRUTH,
            'rows': rows,
            'detector_specs': {
                'D0': 'z-only (log-transformed historic limits, z>=2 medium / z>=3 high)',
                'D1': 'two-layer (1-case rare 全数把握 + z-rule layer-2)',
                'D2': '4-signal composite (0.35Z + 0.20G + 0.20P + 0.25S; >=0.7 high, >=0.5 medium)',
            },
            'params': {
                'lookback_years': LOOKBACK_YEARS,
                'week_window': WEEK_WINDOW,
                'rare_baseline_threshold': RARE_BASELINE,
                'z_med': Z_MED, 'z_high': Z_HIGH,
                'd2_weights': {'Z': 0.35, 'Growth': 0.20, 'Persistence': 0.20, 'Spatial': 0.25},
                'd2_thresholds': {'medium': 0.5, 'high': 0.7},
                'lead_window_weeks': 26,
            },
        }, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {out_json}")
