"""Live demo: simulate the 4-detector framework on 2026 麻しん week-by-week.

For each ISO week t in [2026-W01 .. 2026-W16], evaluate each detector using
ONLY data with (year, week) ≤ t. Apply sustained-alert k=3 wrapper.

Output:
  measles_2026_weekly_simulation.csv
  figures_v3/fig6_measles_2026_live_demo.png — line + Gantt
  figures_v3/fig7_measles_2026_prefecture_heatmap.png — prefecture cumulative × tier
  measles_2026_live_demo.md — narrative
"""
import csv, json, os
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, '/sessions/cool-clever-goldberg/mnt/outputs')
import detect_anomalies_v3 as v3

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import matplotlib.patches as mpatches
import numpy as np

# CJK font setup (same pattern as render_figures_v3)
def setup_cjk_font():
    candidates_macos = ['Hiragino Sans','Hiragino Maru Gothic Pro','Apple SD Gothic Neo','Arial Unicode MS','Noto Sans CJK JP']
    candidates_linux = ['/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf']
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates_macos if c in available), None)
    if chosen:
        plt.rcParams['font.family'] = chosen; return chosen
    for path in candidates_linux:
        if os.path.exists(path):
            font_manager.fontManager.addfont(path)
            family = font_manager.FontProperties(fname=path).get_name()
            plt.rcParams['font.family'] = family; plt.rcParams['axes.unicode_minus'] = False
            return family
    raise RuntimeError('No CJK font available')

CJK = setup_cjk_font()
print(f'CJK font: {CJK}')

OUT = Path('/sessions/cool-clever-goldberg/mnt/outputs')
FIG = OUT / 'figures_v3'

# ── Load data ──────────────────────────────────────────────────────────────
DASH = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json'))
DID = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_did_classification.json'))
URBAN = {p: DID[p]['urban_tier_did'] for p in DID}

# Build prefecture series for 麻しん
pref_2d_measles = defaultdict(list)
with open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_week_timeseries.csv') as f:
    for r in csv.DictReader(f):
        if r['disease'] == '麻しん':
            pref_2d_measles[r['prefecture']].append({
                'year': int(r['year']), 'week': int(r['iso_week']), 'total': int(r['cases'])
            })
pref_dict = dict(pref_2d_measles)
print(f'Prefecture data loaded: {len(pref_dict)} prefectures')

# National weekly_trends for 麻しん
national_full = DASH['weekly_trends']['麻しん']
print(f'National weekly_trends: {len(national_full)} records')

# ── Week-by-week simulation: 2026 W01..W16 ────────────────────────────────
WEEKS_TO_SIM = [(2026, w) for w in range(1, 17)]
DISEASE = '麻しん'

# Helper: severity → numeric for sustained tracking and color mapping
SEV_RANK = {None: 0, 'medium': 1, 'high': 2}
def sev_to_state(sev):
    if sev == 'high': return 'high'
    if sev == 'medium': return 'medium'
    return 'silent'

print('\n=== Week-by-week simulation ===\n')
print(f'{"ISO Week":<10} {"Cases":>6} {"D_rare":<7} {"D_stat":<7} {"D_growth":<9} {"D_spatial":<10} {"Combined":<10} {"sustained?":<11}')
print('-' * 90)
rows = []
sevs_history = {'D_rare':[], 'D_stat':[], 'D_growth':[], 'D_spatial':[], 'Combined':[]}
sustained_active_first_week = None

for ty, tw in WEEKS_TO_SIM:
    # Truncate national series to (year, week) ≤ (ty, tw) — strict purity
    nat_trunc = [r for r in national_full if (r['year'], r['week']) <= (ty, tw)]
    pref_trunc = {p: [r for r in s if (r['year'], r['week']) <= (ty, tw)] for p, s in pref_dict.items()}
    v3.reset_caches()
    sev_rare    = v3.D_rare(DISEASE, nat_trunc, pref_trunc, ty, tw)
    sev_stat    = v3.D_stat(DISEASE, nat_trunc, pref_trunc, ty, tw)
    sev_growth  = v3.D_growth(DISEASE, nat_trunc, pref_trunc, ty, tw)
    sp = v3.D_spatial(DISEASE, nat_trunc, pref_trunc, ty, tw, URBAN)
    sev_spatial = sp.get('flat') if isinstance(sp, dict) else sp
    sev_leader  = sp.get('leader_tier') if isinstance(sp, dict) else None

    sevs_now = [s for s in (sev_rare, sev_stat, sev_growth, sev_spatial) if s]
    if not sevs_now: combined = None
    elif 'high' in sevs_now: combined = 'high'
    else: combined = 'medium'

    cases = v3.value_at(nat_trunc, ty, tw) or 0

    # Track histories for sustained
    for det_name, sev in [('D_rare', sev_rare), ('D_stat', sev_stat), ('D_growth', sev_growth),
                           ('D_spatial', sev_spatial), ('Combined', combined)]:
        sevs_history[det_name].append(sev)

    # sustained = last 3 weeks all medium+
    sustained = (len(sevs_history['Combined']) >= 3 and
                 all(s in ('medium', 'high') for s in sevs_history['Combined'][-3:]))
    if sustained and sustained_active_first_week is None:
        # First week the run becomes 3-long is `tw` (current); but the streak STARTED at tw-2
        sustained_active_first_week = (sevs_history['Combined'][-3:],
                                        ty, tw - 2 if tw > 2 else tw)

    print(f'2026-W{tw:<2}     {cases:>6} '
          f'{sev_to_state(sev_rare):<7} {sev_to_state(sev_stat):<7} '
          f'{sev_to_state(sev_growth):<9} {sev_to_state(sev_spatial):<10} '
          f'{sev_to_state(combined):<10} {"✓" if sustained else "":<11}')

    rows.append({
        'iso_week': f'2026-W{tw:02d}',
        'weekly_count_national': cases,
        'D_rare_state': sev_to_state(sev_rare),
        'D_stat_state': sev_to_state(sev_stat),
        'D_growth_state': sev_to_state(sev_growth),
        'D_spatial_state': sev_to_state(sev_spatial),
        'D_spatial_leader_tier': sev_leader or '',
        'Combined_state': sev_to_state(combined),
        'sustained_alert_active': 'Y' if sustained else 'N',
    })

# Save CSV
with open(OUT/'measles_2026_weekly_simulation.csv', 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f'\nSaved measles_2026_weekly_simulation.csv ({len(rows)} rows)')

# ── Milestones ─────────────────────────────────────────────────────────────
def first_week_meeting(rows, predicate):
    for r in rows:
        if predicate(r): return r['iso_week']
    return None

first_watch    = first_week_meeting(rows, lambda r: any(r[d+'_state'] in ('medium','high') for d in ('D_rare','D_stat','D_growth','D_spatial')))
first_medium   = first_week_meeting(rows, lambda r: r['Combined_state'] in ('medium','high'))
first_sustained = first_week_meeting(rows, lambda r: r['sustained_alert_active'] == 'Y')
jihs_official  = '2026-W16'  # JIHS Featured 2026/06 — known anchor
data_derived_anchor = '2026-W04'

print(f'\n=== Milestones ===')
print(f'  First watch (any detector ≥ medium):   {first_watch}')
print(f'  First Combined alert:                   {first_medium}')
print(f'  First SUSTAINED (k=3 consecutive):      {first_sustained}')
print(f'  Data-derived anchor (v3.1):             {data_derived_anchor}')
print(f'  JIHS Featured 2026/06 official:         {jihs_official}')

# Lead time calc
def w_int(s): return int(s.split('-W')[1])
lead_vs_anchor = w_int(data_derived_anchor) - w_int(first_sustained) if first_sustained else None
lead_vs_jihs   = w_int(jihs_official) - w_int(first_sustained) if first_sustained else None
print(f'\n  Lead vs data-derived anchor:  {f"+{lead_vs_anchor}w" if lead_vs_anchor and lead_vs_anchor > 0 else (f"{lead_vs_anchor}w" if lead_vs_anchor is not None else "-")}')
print(f'  Lead vs JIHS official W16:    +{lead_vs_jihs}w' if lead_vs_jihs else '  Lead vs JIHS: -')

# ── Figure 6: line + Gantt ─────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), gridspec_kw={'height_ratios': [1.5, 1.2]}, sharex=True)

x = list(range(1, 17))
y = [r['weekly_count_national'] for r in rows]
ax1.plot(x, y, '-o', color='#C96342', lw=2, ms=6, label='麻しん weekly cases (national)')
ax1.fill_between(x, 0, y, alpha=0.15, color='#C96342')
ax1.set_ylabel('Weekly reported cases', fontsize=10)
ax1.set_title(f'Real-time simulation: 2026 麻しん (measles) outbreak surveillance — 4-detector framework',
              fontsize=12, pad=10)
# Vertical reference lines
if first_sustained:
    ax1.axvline(w_int(first_sustained), color='#3F8194', lw=1.4, ls='--', alpha=0.7, label=f'First sustained alert ({first_sustained})')
ax1.axvline(w_int(data_derived_anchor), color='gray', lw=1.0, ls=':', alpha=0.7, label=f'Data-derived anchor ({data_derived_anchor})')
ax1.axvline(w_int(jihs_official), color='red', lw=1.4, ls='--', alpha=0.7, label=f'JIHS Featured 2026/06 ({jihs_official})')
ax1.legend(loc='upper left', fontsize=8)
ax1.grid(alpha=0.3)
ax1.tick_params(labelsize=9)

# Gantt-style detector states
DETECTORS_DISP = ['D_rare', 'D_stat', 'D_growth', 'D_spatial', 'Combined']
COLOR_MAP = {'silent': '#EEEEEE', 'medium': '#F4C430', 'high': '#D85563'}
for i, det in enumerate(DETECTORS_DISP):
    states = [r[det+'_state'] for r in rows]
    for wi, s in enumerate(states, start=1):
        ax2.barh(i, 1, left=wi-0.5, height=0.7, color=COLOR_MAP[s], edgecolor='white', lw=0.4)
ax2.set_yticks(range(len(DETECTORS_DISP)))
ax2.set_yticklabels(DETECTORS_DISP, fontsize=9)
ax2.set_xticks(x)
ax2.set_xticklabels([f'W{w}' for w in x], fontsize=8)
ax2.set_xlabel('2026 ISO Week', fontsize=10)
ax2.set_title('Detector state (silent / medium / high) per week', fontsize=10)
ax2.set_xlim(0.5, 16.5)
# Vertical refs on bottom panel too
if first_sustained:
    ax2.axvline(w_int(first_sustained), color='#3F8194', lw=1.4, ls='--', alpha=0.7)
ax2.axvline(w_int(data_derived_anchor), color='gray', lw=1.0, ls=':', alpha=0.7)
ax2.axvline(w_int(jihs_official), color='red', lw=1.4, ls='--', alpha=0.7)
# Legend for state colors
state_handles = [mpatches.Patch(color=COLOR_MAP[s], label=s) for s in ['silent', 'medium', 'high']]
ax2.legend(handles=state_handles, loc='upper left', fontsize=8, title='State')
ax2.grid(axis='x', alpha=0.3)

plt.tight_layout()
plt.savefig(FIG/'fig6_measles_2026_live_demo.png', dpi=140, bbox_inches='tight')
plt.close()
print(f'Saved fig6_measles_2026_live_demo.png')

# ── Figure 7: prefecture heatmap (by tier) ────────────────────────────────
# Cumulative 2026 cases per prefecture, grouped by tier
pref_cum_2026 = {}
for pref, series in pref_dict.items():
    cum = sum(r['total'] for r in series if r['year'] == 2026)
    pref_cum_2026[pref] = cum

# Sort: by tier order (high_urban, mixed, rural) then by cum desc within tier
TIER_ORDER = ['high_urban', 'mixed', 'rural_leaning']
TIER_COLORS = {'high_urban': '#3F8194', 'mixed': '#5C8A4F', 'rural_leaning': '#9C7FCF'}
sorted_prefs = []
for tier in TIER_ORDER:
    tier_prefs = [(p, c) for p, c in pref_cum_2026.items() if URBAN.get(p) == tier]
    tier_prefs.sort(key=lambda x: -x[1])
    sorted_prefs.extend([(p, c, tier) for p, c in tier_prefs])

fig, ax = plt.subplots(figsize=(8.5, 9))
y_pos = np.arange(len(sorted_prefs))
vals = [item[1] for item in sorted_prefs]
colors = [TIER_COLORS[item[2]] for item in sorted_prefs]
ax.barh(y_pos, vals, color=colors, edgecolor='white')
ax.set_yticks(y_pos)
ax.set_yticklabels([f"{p} ({c})" for p, c, t in sorted_prefs], fontsize=8)
ax.invert_yaxis()
ax.set_xlabel('2026 cumulative measles cases (W01-W16)', fontsize=10)
ax.set_title('2026 麻しん 都道府県別 累計報告数 — by DID urban tier', fontsize=11)
# Tier legend
handles = [mpatches.Patch(color=TIER_COLORS[t], label=t) for t in TIER_ORDER]
ax.legend(handles=handles, loc='lower right', fontsize=9)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(FIG/'fig7_measles_2026_prefecture_heatmap.png', dpi=140, bbox_inches='tight')
plt.close()
print(f'Saved fig7_measles_2026_prefecture_heatmap.png')

# Aggregate by tier for narrative
tier_totals = defaultdict(int)
tier_active_prefs = defaultdict(int)
for pref, cum in pref_cum_2026.items():
    t = URBAN.get(pref)
    if t:
        tier_totals[t] += cum
        if cum > 0: tier_active_prefs[t] += 1

print('\n=== Tier totals (2026 cumulative cases through W16) ===')
for t in TIER_ORDER:
    n_total_in_tier = sum(1 for p in URBAN if URBAN[p] == t)
    print(f'  {t}: {tier_totals[t]:,} cases across {tier_active_prefs[t]}/{n_total_in_tier} active prefectures')

# Top 5 prefectures by 2026 cum
top5 = sorted(pref_cum_2026.items(), key=lambda x: -x[1])[:5]
print(f'\n  Top 5 prefectures: {[(p, c, URBAN.get(p)) for p, c in top5]}')
