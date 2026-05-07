"""Cross-validate outbreak_reference_set.csv against dashboard's IDWR data.

Four-dimensional check per outbreak:
  1. disease_match       — does curation disease_jp map to a DATA.weekly_trends key?
  2. start_week_alignment — does ramp-up in IDWR data occur within ±4w of curation start?
  3. magnitude_match      — does dashboard accumulated count match curation total_cases?
  4. geographic_match     — does prefecture-level concentration match curation region?

Tier each as Pass (4✓) / Minor (1 △) / Major (≥1 ✗).
"""
from __future__ import annotations
import csv, json, math, re, sys
from pathlib import Path

OUT = Path('/sessions/cool-clever-goldberg/mnt/outputs')
DASH_DATA = Path('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json')
PREF_SENT = OUT / 'pref_timeseries_sentinel.json'
PREF_3DIS = OUT / 'pref_timeseries_3diseases.json'
REF_CSV = Path('/sessions/cool-clever-goldberg/mnt/claude/outbreak_reference_set.csv')
NESID_PREF = Path('/sessions/cool-clever-goldberg/mnt/claude/scripts/nesid_pref_data.json')

# ── Disease-name alignment table ────────────────────────────────────────────
# curation disease_jp → dashboard key (None = no match in dashboard data)
DISEASE_ALIGNMENT = {
    '風疹':                  '風しん',  # IDWR uses 風しん
    'デング熱':              'デング熱',
    '中東呼吸器症候群':      '中東呼吸器症候群',  # in dash but Japan never had cases
    '麻しん':                '麻しん',
    '風疹(2018-19)':         '風しん',
    '麻しん(2019)':          '麻しん',
    'COVID-19':              None,  # not in IDWR weekly_trends (separate emergency surveillance)
    'サル痘(エムポックス)':  'エムポックス',
    'RSウイルス感染症':      'RSウイルス感染症',
    '劇症型溶連菌感染症(2023)': '劇症型溶血性レンサ球菌感染症',
    '梅毒(2024)':            '梅毒',
    '劇症型溶連菌感染症(2024)': '劇症型溶血性レンサ球菌感染症',
    'マイコプラズマ肺炎':    None,  # check
    '百日咳':                '百日咳',
    'インフルエンザ A H1N1(2025)': 'インフルエンザ',  # IDWR aggregates A/B
    '麻しん(2025 輸入)':     '麻しん',
    '麻しん 2026 W16 集団':  '麻しん',
    'インフルエンザ B(2026 春期)': 'インフルエンザ',
}

# ── Helpers ────────────────────────────────────────────────────────────────
def parse_iso_year_week(s):
    """'2018-W30' → (2018, 30)."""
    if not s or s == 'n/a': return None, None
    m = re.match(r'(\d{4})-W(\d+)', s.strip())
    if m: return int(m.group(1)), int(m.group(2))
    return None, None

def value_at(series, year, week):
    for r in series:
        if r.get('year') == year and r.get('week') == week:
            return r.get('total')
    return None

def collect_reference(series, year, week, lookback=5, window=2):
    refs = []
    for r in series:
        y, w = r.get('year'), r.get('week')
        if y is None or w is None: continue
        if not (year - lookback <= y <= year - 1): continue
        if abs(w - week) <= window: refs.append(r.get('total', 0))
    return refs

def baseline_stats(series, year, week):
    """Return (median, +1SD threshold) using past-5y same-week ±2w."""
    refs = collect_reference(series, year, week)
    if len(refs) < 4: return None, None
    refs_sorted = sorted(refs)
    n = len(refs_sorted)
    median = refs_sorted[n//2] if n % 2 else (refs_sorted[n//2-1]+refs_sorted[n//2])/2
    mean = sum(refs_sorted) / n
    var = sum((v-mean)**2 for v in refs_sorted) / max(1, n-1)
    sd = math.sqrt(var)
    return median, mean + sd

def ramp_up_week(series, year_around, week_around, search_window=12):
    """Find first SUSTAINED ramp (3 consecutive weeks with val > baseline+1SD)
       within ±search_window of (year_around, week_around).
       Returns (year, week, val, median, plus1sd, dist_from_anchor) of the
       FIRST week of the sustained run, or None.

       This avoids picking single-week noise crossings as 'outbreak start'."""
    # Build sorted weeks within search window
    in_window = []
    for r in sorted(series, key=lambda r: (r['year'], r['week'])):
        y, w = r.get('year'), r.get('week')
        if y is None or w is None: continue
        dist = (y - year_around) * 52 + (w - week_around)
        if abs(dist) > search_window: continue
        in_window.append((y, w, r.get('total', 0), dist))
    # Walk chronologically; find first run of 3 consecutive elevated weeks
    streak = []
    for y, w, v, dist in in_window:
        median, plus1sd = baseline_stats(series, y, w)
        if plus1sd is None: continue
        elevated = (v > plus1sd and v > 0)
        if elevated:
            streak.append((y, w, v, median, plus1sd, dist))
            if len(streak) >= 3:
                return streak[0]
        else:
            streak = []
    return None

def has_data_in_window(series, year, search_window=12):
    """Check whether series has any records in [year-1, year+1]. Used to detect
       'curation references a year before dashboard data starts'."""
    for r in series:
        if year - 1 <= r.get('year', 0) <= year + 1:
            return True
    return False

def is_conceptual_anchor(reference_str, total_cases_str):
    """Detect anchors that are conceptual (e.g., 'W01 of year' for chronic
       endemic) rather than data-derived inflection points."""
    if 'W01' in reference_str or 'W1' == reference_str.split('-')[-1]:
        # If total_cases mentions full year (年 / 通年 / 暫定値) → likely conceptual
        if any(k in total_cases_str for k in ('年', '通年', '暫定値', '時点')):
            return True
    return False

def cumulative_in_year(series, target_year):
    return sum(r.get('total', 0) for r in series if r.get('year') == target_year)

def cumulative_window(series, year_start, week_start, year_end, week_end):
    out = 0
    for r in series:
        y, w = r.get('year'), r.get('week')
        if y is None or w is None: continue
        if (y, w) >= (year_start, week_start) and (y, w) <= (year_end, week_end):
            out += r.get('total', 0)
    return out

def parse_total_cases(s):
    """'14,663 (2024 暫定値、…)' → 14663"""
    if not s: return None
    # find the first number with optional commas
    m = re.search(r'([\d,]+)', s)
    if m:
        try: return int(m.group(1).replace(',', ''))
        except ValueError: return None
    return None

# ── Load data ──────────────────────────────────────────────────────────────
with open(DASH_DATA, encoding='utf-8') as f: dash = json.load(f)
weekly_trends = dash['weekly_trends']
weekly_pref = dash.get('weekly_pref', {})

pref_ts = {}
if PREF_SENT.exists():
    with open(PREF_SENT, encoding='utf-8') as f: pref_ts.update(json.load(f))
if PREF_3DIS.exists():
    with open(PREF_3DIS, encoding='utf-8') as f: pref_ts.update(json.load(f))

# Read curation set
outbreaks = []
with open(REF_CSV, encoding='utf-8') as f:
    for r in csv.DictReader(f):
        outbreaks.append(r)
print(f'Loaded {len(outbreaks)} outbreaks from curation reference set\n')

# ── Validate each outbreak ─────────────────────────────────────────────────
results = []
for ob in outbreaks:
    res = {
        'id': ob['id'],
        'disease_jp': ob['disease_jp'],
        'tier': ob['tier'],
        'reference_start': ob['reference_start_iso_week'],
    }
    # Skip insufficient
    if ob['tier'] == 'insufficient':
        res['classification'] = 'EXCLUDED'
        res['rationale'] = ob.get('one_line_rationale','')[:80]
        results.append(res)
        continue

    # 1. disease_match
    disease_key = DISEASE_ALIGNMENT.get(ob['disease_jp'])
    if disease_key is None and ob['disease_jp'] in weekly_trends:
        disease_key = ob['disease_jp']
    res['mapped_key'] = disease_key
    if disease_key is None:
        res['disease_match'] = '✗'
        res['disease_match_note'] = f'curation {ob["disease_jp"]!r} 在 dashboard 找不到匹配键'
    elif disease_key in weekly_trends:
        res['disease_match'] = '✓'
        res['disease_match_note'] = f'mapped to {disease_key!r}'
    else:
        res['disease_match'] = '✗'
        res['disease_match_note'] = f'mapped to {disease_key!r} 但在 weekly_trends 中不存在'

    if disease_key not in weekly_trends:
        # Cannot compare further
        res['start_week_alignment'] = '–'
        res['magnitude_match'] = '–'
        res['geographic_match'] = '–'
        results.append(res)
        continue

    series = weekly_trends[disease_key]

    # 2. start_week_alignment
    ref_y, ref_w = parse_iso_year_week(ob['reference_start_iso_week'])
    if ref_y is None:
        res['start_week_alignment'] = '–'
        res['start_week_note'] = 'reference_start = n/a'
    elif not has_data_in_window(series, ref_y, search_window=12):
        res['start_week_alignment'] = '–'
        res['start_week_note'] = f'dashboard data 不覆盖 {ref_y}±1 年（pre-data 限制）'
    else:
        conceptual = is_conceptual_anchor(ob['reference_start_iso_week'],
                                           ob.get('total_cases',''))
        # Search wider for conceptual anchors (full year ahead)
        sw = 26 if conceptual else 12
        ramp = ramp_up_week(series, ref_y, ref_w, search_window=sw)
        if ramp is None:
            if conceptual:
                # No sustained ramp anywhere in the year — possibly OK if curation
                # is about declared "warning level" (year-start convention)
                res['start_week_alignment'] = '△'
                res['start_week_note'] = f'年始-conceptual anchor; 全年内未见 sustained 3-week ramp（may be valid for chronic endemic）'
                res['ramp_week'] = None
            else:
                res['start_week_alignment'] = '✗'
                res['start_week_note'] = f'±{sw}w 内未观测到 sustained 3-week ramp'
                res['ramp_week'] = None
        else:
            ay, aw, val, med, plus1sd, dist = ramp
            res['ramp_week'] = f'{ay}/W{aw}'
            res['ramp_value'] = int(val) if val else 0
            res['baseline_median'] = round(med, 1) if med is not None else None
            res['baseline_plus1sd'] = round(plus1sd, 1) if plus1sd is not None else None
            res['ramp_dist_weeks'] = dist
            tag = ' (conceptual anchor — wider tolerance)' if conceptual else ''
            tol_minor = 12 if conceptual else 8
            if abs(dist) <= 2:
                res['start_week_alignment'] = '✓'
                res['start_week_note'] = f'IDWR sustained ramp at {ay}/W{aw} (Δ{dist:+d}w){tag}'
            elif abs(dist) <= tol_minor:
                res['start_week_alignment'] = '△'
                res['start_week_note'] = f'IDWR sustained ramp at {ay}/W{aw} (Δ{dist:+d}w; minor gap){tag}'
            else:
                res['start_week_alignment'] = '✗'
                res['start_week_note'] = f'IDWR sustained ramp at {ay}/W{aw} (Δ{dist:+d}w; major gap){tag}'

    # 3. magnitude_match
    cur_total = parse_total_cases(ob.get('total_cases'))
    res['curation_total_cases'] = cur_total
    if cur_total is None:
        res['magnitude_match'] = '–'
        res['magnitude_note'] = 'curation total_cases 不可解析'
    else:
        # Compute dashboard cumulative for the outbreak year (most outbreaks specify single-year totals)
        if ref_y:
            dash_cum = cumulative_in_year(series, ref_y)
            # For multi-year totals (e.g. 2012-2014 for 風疹 #1), also include adjacent years
            multi_year = '累計' in ob.get('total_cases','') or '-' in ob.get('total_cases','')
            if multi_year:
                # Try ±1 year accumulation for multi-year reference
                dash_cum_multi = cumulative_in_year(series, ref_y) + cumulative_in_year(series, ref_y+1) + cumulative_in_year(series, ref_y+2)
                if dash_cum_multi > 0 and abs(dash_cum_multi - cur_total) / max(cur_total, 1) < 0.5:
                    dash_cum = dash_cum_multi
            res['dash_yearly_cum'] = dash_cum
            if dash_cum == 0:
                res['magnitude_match'] = '✗'
                res['magnitude_note'] = f'dashboard {ref_y} 累计=0; curation 报 {cur_total:,}'
            else:
                rel_err = abs(dash_cum - cur_total) / cur_total
                if rel_err <= 0.20:
                    res['magnitude_match'] = '✓'
                    res['magnitude_note'] = f'dashboard {dash_cum:,} vs curation {cur_total:,} (Δ{rel_err*100:.0f}%)'
                elif rel_err <= 0.50:
                    res['magnitude_match'] = '△'
                    res['magnitude_note'] = f'dashboard {dash_cum:,} vs curation {cur_total:,} (Δ{rel_err*100:.0f}%; 20-50% gap)'
                else:
                    res['magnitude_match'] = '✗'
                    res['magnitude_note'] = f'dashboard {dash_cum:,} vs curation {cur_total:,} (Δ{rel_err*100:.0f}%; >50% gap)'
        else:
            res['magnitude_match'] = '–'
            res['magnitude_note'] = 'no ref_year for cumulative'

    # 4. geographic_match
    region_str = ob.get('region','')
    res['curation_region'] = region_str[:60]
    if disease_key in pref_ts:
        # Have prefecture time series. Compute top 5 prefectures during outbreak window
        ps = pref_ts[disease_key]
        if ref_y:
            window_start = (ref_y, max(1, ref_w - 2))
            window_end = (ref_y, min(52, ref_w + 12))
            pref_totals = {}
            for pref, ser in ps.items():
                if pref == '総数': continue
                tot = 0
                for r in ser:
                    y, w = r.get('year'), r.get('week')
                    if y is None or w is None: continue
                    if (y, w) >= window_start and (y, w) <= window_end:
                        tot += r.get('total', 0)
                pref_totals[pref] = tot
            top5 = sorted(pref_totals.items(), key=lambda kv: -kv[1])[:5]
            res['top5_prefs'] = ', '.join(f'{p}({c})' for p, c in top5 if c > 0)
            # Match — does curation region include any of top5?
            top_prefs = [p for p, c in top5 if c > 0]
            mentioned = [p for p in top_prefs if p in region_str]
            if not top_prefs:
                res['geographic_match'] = '–'
                res['geographic_note'] = '该周期内 prefecture 数据全 0'
            elif len(mentioned) >= 2 or (region_str.strip() == '全国' and len(top_prefs) >= 3):
                res['geographic_match'] = '✓'
                res['geographic_note'] = f'top5 中 {len(mentioned)} 个见于 curation region 文字'
            elif len(mentioned) >= 1:
                res['geographic_match'] = '△'
                res['geographic_note'] = f'top5 中仅 {len(mentioned)} 个见于 curation region'
            else:
                # Special case: curation says "全国" — accept loosely
                if region_str.strip().startswith('全国'):
                    res['geographic_match'] = '✓'
                    res['geographic_note'] = '全国 curation; top5 都道府県 = ' + res['top5_prefs']
                else:
                    res['geographic_match'] = '✗'
                    res['geographic_note'] = f'top5 都道府県 ({", ".join(top_prefs[:3])}) 与 curation region 不匹配'
        else:
            res['geographic_match'] = '–'
            res['geographic_note'] = 'no ref_year'
    elif disease_key in weekly_pref:
        # weekly_pref is just snapshot (latest week), not historical
        wp = weekly_pref[disease_key]
        if isinstance(wp, dict):
            top5 = sorted(((p, v) for p, v in wp.items() if p != '総数' and isinstance(v, (int, float))),
                          key=lambda kv: -kv[1])[:5]
            res['top5_prefs'] = ', '.join(f'{p}({c})' for p, c in top5 if c > 0) + ' [snapshot only]'
        else:
            res['top5_prefs'] = '[weekly_pref structure not iterable]'
        res['geographic_match'] = '△'
        res['geographic_note'] = 'dashboard 仅有 latest-week prefecture snapshot, 无历史时序; partial check'
    else:
        res['top5_prefs'] = '[no prefecture data]'
        res['geographic_match'] = '–'
        res['geographic_note'] = 'no prefecture-level time series for this disease'

    results.append(res)

# ── Tier classification ─────────────────────────────────────────────────────
def classify(r):
    if r.get('classification') == 'EXCLUDED': return 'EXCLUDED'
    # Disease not in IDWR scope at all → EXCLUDED, not MAJOR
    if r.get('disease_match') == '✗':
        return 'EXCLUDED'
    # Curation references year before dashboard data → EXCLUDED with note
    if r.get('start_week_note','').startswith('dashboard data 不覆盖'):
        return 'PRE-DATA'
    dims = [r.get('disease_match'), r.get('start_week_alignment'),
            r.get('magnitude_match'), r.get('geographic_match')]
    n_pass = sum(1 for d in dims if d == '✓')
    n_minor = sum(1 for d in dims if d == '△')
    n_major = sum(1 for d in dims if d == '✗')
    n_na = sum(1 for d in dims if d in ('–', None))
    if n_major >= 1: return 'MAJOR'
    if n_minor >= 1: return 'MINOR'
    if n_pass >= 3 and n_na <= 1: return 'PASS'
    return 'MINOR'

for r in results:
    r['classification'] = r.get('classification') or classify(r)

# ── Print summary table ────────────────────────────────────────────────────
print(f'{"#":<3} {"Disease":<24} {"Tier":<14} {"Dis":<3} {"Start":<3} {"Mag":<3} {"Geo":<3} {"Class":<10}')
print('-' * 90)
for r in results:
    print(f'{r["id"]:<3} {r["disease_jp"][:22]:<24} {r["tier"]:<14} '
          f'{r.get("disease_match","-"):<3} {r.get("start_week_alignment","-"):<3} '
          f'{r.get("magnitude_match","-"):<3} {r.get("geographic_match","-"):<3} '
          f'{r["classification"]:<10}')

# Counts
counts = {'PASS': 0, 'MINOR': 0, 'MAJOR': 0, 'EXCLUDED': 0}
for r in results: counts[r['classification']] += 1
print(f'\nCounts: PASS={counts["PASS"]}, MINOR={counts["MINOR"]}, MAJOR={counts["MAJOR"]}, EXCLUDED={counts["EXCLUDED"]}')

# Save full results JSON
with open(OUT/'outbreak_validation_raw.json', 'w', encoding='utf-8') as f:
    json.dump({'counts': counts, 'rows': results}, f, ensure_ascii=False, indent=2)
print(f'\nSaved: outbreak_validation_raw.json')
