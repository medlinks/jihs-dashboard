"""Re-render all 9 figures in English using disease_name_mapping module.

Overwrites figures_v3/fig{1..9}*.png. Asserts ASCII-only labels before save.
"""
import csv, json, os, sys
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, '/sessions/cool-clever-goldberg/mnt/outputs')
from disease_name_mapping import (DISEASE_NAME_EN, AXIS_LABELS_EN, URBAN_TIER_EN,
                                   PREFECTURE_NAME_EN, en_disease, en_pref, en_tier,
                                   assert_ascii_safe)
import detect_anomalies_v3 as v3

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Use Arial / sans-serif (no CJK needed); falls back to DejaVu Sans on Linux
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUT  = Path('/sessions/cool-clever-goldberg/mnt/outputs')
FIG  = OUT / 'figures_v3'
DASH = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/scripts/full_dashboard_data.json'))
DID  = json.load(open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_did_classification.json'))
URBAN = {p: DID[p]['urban_tier_did'] for p in DID}

# ── Load retrospective + complementarity ─────────────────────────────────
retro = list(csv.DictReader(open(OUT/'retrospective_results_v3.csv')))
TIER_C = {'high_urban': '#3F8194', 'mixed': '#5C8A4F', 'rural_leaning': '#9C7FCF'}

# ── Fig 1: Lead-time heatmap ─────────────────────────────────────────────
OUTBREAKS = sorted(set(int(r['outbreak_id']) for r in retro))
DISEASES_JP = {int(r['outbreak_id']): r['disease'] for r in retro}
DETECTORS = ['D_rare', 'D_stat', 'D_growth', 'D_spatial', 'Combined_OR']

M = np.full((len(OUTBREAKS), len(DETECTORS)), np.nan)
labels = np.empty(M.shape, dtype=object)
for r in retro:
    i = OUTBREAKS.index(int(r['outbreak_id']))
    j = DETECTORS.index(r['detector'])
    if r['lead_weeks'] != '':
        try:
            v = int(r['lead_weeks']); M[i, j] = v
            labels[i, j] = f'{v:+d}'
        except ValueError: labels[i, j] = '-'
    else:
        labels[i, j] = '-'

fig, ax = plt.subplots(figsize=(8.5, 6.5))
import matplotlib.colors as mcolors
cmap = plt.cm.RdYlGn
norm = mcolors.Normalize(vmin=-26, vmax=26)
masked = np.ma.masked_invalid(M)
im = ax.imshow(masked, cmap=cmap, norm=norm, aspect='auto')
for i in range(len(OUTBREAKS)):
    for j in range(len(DETECTORS)):
        if np.isnan(M[i, j]):
            ax.add_patch(plt.Rectangle((j-0.5, i-0.5), 1, 1, fill=True, color='#EEEEEE'))
        ax.text(j, i, labels[i, j], ha='center', va='center', fontsize=10, fontweight='bold')
ax.set_xticks(range(len(DETECTORS)))
ax.set_xticklabels(DETECTORS, rotation=15, ha='right', fontsize=10)
y_lbls = [f'#{i} {en_disease(DISEASES_JP[i])}' for i in OUTBREAKS]
for s in y_lbls: assert_ascii_safe(s, 'fig1 ylabel')
ax.set_yticks(range(len(OUTBREAKS)))
ax.set_yticklabels(y_lbls, fontsize=9)
ax.set_xlabel('Detector', fontsize=11)
ax.set_ylabel('Outbreak (v3.1 curation)', fontsize=11)
ax.set_title('Figure 1 — Lead-time matrix (weeks before reference outbreak start)\n'
             'Green = earlier  |  Red = late  |  Grey = no alert in detection window',
             fontsize=11)
plt.colorbar(im, ax=ax, label='Lead time (weeks)')
plt.tight_layout(); plt.savefig(FIG/'fig1_leadtime_heatmap.png', dpi=140, bbox_inches='tight'); plt.close()
print('fig1: saved')

# ── Fig 3: detector necessity ─────────────────────────────────────────────
TOL = 26
det_fired = defaultdict(set)
for r in retro:
    if r['detector'] == 'Combined_OR': continue
    if r['lead_weeks'] != '' and abs(int(r['lead_weeks'])) <= TOL:
        det_fired[int(r['outbreak_id'])].add(r['detector'])
fig, ax = plt.subplots(figsize=(11, 5))
x = np.arange(len(OUTBREAKS))
det_colors = {'D_rare':'#C96342','D_stat':'#3F8194','D_growth':'#5C8A4F','D_spatial':'#9C7FCF'}
bottom = np.zeros(len(OUTBREAKS))
for det in ['D_rare','D_stat','D_growth','D_spatial']:
    h = np.array([1 if det in det_fired[i] else 0 for i in OUTBREAKS])
    ax.bar(x, h, bottom=bottom, color=det_colors[det], label=det, edgecolor='white')
    bottom += h
xtl = [f'#{i}\n{en_disease(DISEASES_JP[i])[:10]}' for i in OUTBREAKS]
for s in xtl: assert_ascii_safe(s, 'fig3 xlabel')
ax.set_xticks(x); ax.set_xticklabels(xtl, fontsize=8, rotation=0)
ax.set_ylabel('Number of detectors firing within +/-26 weeks', fontsize=10)
ax.set_title('Figure 3 — Detector necessity per outbreak (+/-26-week detection tolerance)', fontsize=11)
ax.legend(loc='upper right', fontsize=9)
ax.set_ylim(0, 4.5)
plt.tight_layout(); plt.savefig(FIG/'fig3_detector_necessity.png', dpi=140, bbox_inches='tight'); plt.close()
print('fig3: saved')

# ── Fig 4: false alert ────────────────────────────────────────────────────
fa = list(csv.DictReader(open(OUT/'false_alert_characterization_v3.csv')))
fa_summary = defaultdict(lambda: {'sentinel': [], 'full-report': []})
for r in fa:
    fa_summary[r['detector']][r['class']].append(float(r['alerts_per_year']))
fig, ax = plt.subplots(figsize=(8, 4.5))
dets = ['D_rare','D_stat','D_growth','D_spatial']
sentinel_means = [np.mean(fa_summary[d]['sentinel']) if fa_summary[d]['sentinel'] else 0 for d in dets]
full_means = [np.mean(fa_summary[d]['full-report']) if fa_summary[d]['full-report'] else 0 for d in dets]
x = np.arange(len(dets)); w = 0.35
ax.bar(x - w/2, sentinel_means, w, color='#5C8A4F', label='Sentinel (teiten)')
ax.bar(x + w/2, full_means, w, color='#C96342', label='Full-report (zensu)')
ax.set_xticks(x); ax.set_xticklabels(dets, fontsize=10)
ax.set_ylabel('Sustained alerts / year / disease (outside outbreak windows)', fontsize=10)
ax.set_title('Figure 4 — False-alert rate by detector and disease class', fontsize=11)
ax.legend(); plt.tight_layout()
plt.savefig(FIG/'fig4_false_alert_rate.png', dpi=140, bbox_inches='tight'); plt.close()
print('fig4: saved')

# ── Fig 2: urban-tier dynamics small multiples (6 outbreaks) ─────────────
with open(OUT/'outbreak_urban_tier_dynamics_v3.json', encoding='utf-8') as f:
    dyn = json.load(f)
SHOW = ['手足口病','RSウイルス感染症','インフルエンザ','麻しん','梅毒','咽頭結膜熱']
fig, axes = plt.subplots(2, 3, figsize=(14, 7))
shown = 0
for dn in SHOW:
    if dn not in dyn: continue
    ax = axes[shown // 3, shown % 3]
    d = dyn[dn]
    ref_y, ref_w = d['ref_year'], d['ref_week']
    for tier in ('high_urban','mixed','rural_leaning'):
        tr = d['traces'][tier]
        xs = [(r['year']-ref_y)*52 + (r['week']-ref_w) for r in tr]
        ys = [r['cases'] for r in tr]
        n_total = len(d['tier_prefs'][tier])
        ax.plot(xs, ys, color=TIER_C[tier], lw=1.2, alpha=0.85,
                label=f'{tier} (n={n_total})')
    ax.axvline(0, color='red', lw=0.8, ls='--', alpha=0.6)
    title = f'#{d["outbreak_id"]} {en_disease(dn)}'
    assert_ascii_safe(title, 'fig2 title')
    ax.set_title(title, fontsize=10)
    ax.set_xlabel('Weeks rel. anchor', fontsize=8)
    ax.set_ylabel('Cases (tier sum)', fontsize=8)
    ax.tick_params(labelsize=7)
    if shown == 0: ax.legend(fontsize=7, loc='upper left')
    shown += 1
plt.tight_layout(); plt.savefig(FIG/'fig2_urban_tier_dynamics.png', dpi=140, bbox_inches='tight'); plt.close()
print('fig2: saved')

# ── Fig 5: NESID urban/rural ratio ────────────────────────────────────────
nesid_ratios = [(d['outbreak_id'], k, d.get('nesid_annual_urban_rural_ratio'))
                for k, d in dyn.items() if d.get('nesid_annual_urban_rural_ratio') is not None]
fig, ax = plt.subplots(figsize=(7, 3.5))
if nesid_ratios:
    nesid_ratios.sort(key=lambda r: -r[2])
    labels_x = [f'#{r[0]} {en_disease(r[1])}' for r in nesid_ratios]
    for s in labels_x: assert_ascii_safe(s, 'fig5 xlabel')
    vals = [r[2] for r in nesid_ratios]
    colors = ['#3F8194' if v >= 1.5 else ('#9C7FCF' if v < 0.7 else '#888') for v in vals]
    ax.bar(range(len(vals)), vals, color=colors)
    ax.axhline(1.0, color='black', lw=0.6, ls='--')
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(labels_x, rotation=20, ha='right', fontsize=9)
    ax.set_ylabel('NESID annual urban/rural rate ratio', fontsize=9)
    ax.set_title('Figure 5 — NESID annual urban-tier ratio (full-report only)', fontsize=10)
else:
    ax.text(0.5, 0.5, 'No NESID-annual data for v3.1 sentinel outbreaks',
            ha='center', va='center', transform=ax.transAxes, fontsize=11)
    ax.set_axis_off()
plt.tight_layout(); plt.savefig(FIG/'fig5_urban_tier_dual_granularity.png', dpi=140, bbox_inches='tight'); plt.close()
print('fig5: saved')

# ── Helpers shared by fig6/fig8 ──────────────────────────────────────────
def render_live_demo(disease_jp, weeks_range, sim_csv_path, jihs_label_week, data_anchor_week,
                     fig_name, color, title_text):
    rows = list(csv.DictReader(open(sim_csv_path)))
    DISP = ['D_rare','D_stat','D_growth','D_spatial','Combined']
    COLOR = {'silent':'#EEEEEE','medium':'#F4C430','high':'#D85563'}
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7),
                                    gridspec_kw={'height_ratios':[1.5,1.2]}, sharex=True)
    x = list(weeks_range); y = [int(r['weekly_count_national']) for r in rows]
    ax1.plot(x, y, '-o', color=color, lw=2, ms=5, label=f'{en_disease(disease_jp)} weekly cases (national)')
    ax1.fill_between(x, 0, y, alpha=0.15, color=color)
    ax1.set_ylabel('Weekly reported cases', fontsize=10)
    assert_ascii_safe(title_text, 'live demo title')
    ax1.set_title(title_text, fontsize=11)
    # Find first sustained from rows
    first_sust = next((r['iso_week'] for r in rows if r['sustained_alert_active']=='Y'), None)
    def w_int(s): return int(s.split('-W')[1])
    if first_sust:
        ax1.axvline(w_int(first_sust), color=color, lw=1.4, ls='--', alpha=0.7,
                    label=f'First sustained alert ({first_sust})')
    ax1.axvline(jihs_label_week[1], color='red', lw=1.4, ls='--', alpha=0.7,
                label=f'JIHS {jihs_label_week[0]} ({jihs_label_week[2]})')
    ax1.axvline(data_anchor_week[0], color='gray', lw=1.0, ls=':', alpha=0.7,
                label=f'Data-derived anchor ({data_anchor_week[1]})')
    ax1.legend(loc='upper left', fontsize=8); ax1.grid(alpha=0.3); ax1.tick_params(labelsize=8)

    for i, det in enumerate(DISP):
        states = [r[det+'_state'] for r in rows]
        for wi, s in enumerate(states, start=1):
            ax2.barh(i, 1, left=wi-0.5, height=0.7, color=COLOR[s], edgecolor='white', lw=0.4)
    ax2.set_yticks(range(len(DISP))); ax2.set_yticklabels(DISP, fontsize=9)
    ax2.set_xticks(x); ax2.set_xticklabels([f'W{w}' for w in x], fontsize=7)
    yr = rows[0]['iso_week'].split('-')[0]
    ax2.set_xlim(0.5, max(x)+0.5); ax2.set_xlabel(f'{yr} ISO week', fontsize=10)
    ax2.set_title('Detector state per week (silent / medium / high)', fontsize=10)
    if first_sust: ax2.axvline(w_int(first_sust), color=color, lw=1.4, ls='--', alpha=0.7)
    ax2.axvline(jihs_label_week[1], color='red', lw=1.4, ls='--', alpha=0.7)
    ax2.axvline(data_anchor_week[0], color='gray', lw=1.0, ls=':', alpha=0.7)
    ax2.legend(handles=[mpatches.Patch(color=COLOR[s], label=s) for s in ['silent','medium','high']],
               loc='upper left', fontsize=8)
    ax2.grid(axis='x', alpha=0.3)
    plt.tight_layout(); plt.savefig(FIG/fig_name, dpi=140, bbox_inches='tight'); plt.close()
    print(f'{fig_name}: saved')

# ── Fig 6: 2026 measles live demo (W01-W16) ──────────────────────────────
render_live_demo(
    disease_jp='麻しん', weeks_range=range(1, 17),
    sim_csv_path=OUT/'measles_2026_weekly_simulation.csv',
    jihs_label_week=('Featured 2026/06', 16, '2026-W16'),
    data_anchor_week=(4, '2026-W04'),
    fig_name='fig6_measles_2026_live_demo.png',
    color='#C96342',
    title_text='Figure 6 — Real-time simulation: 2026 Measles outbreak (4-detector framework, full-report disease)'
)

# ── Fig 8: 2024 RSV live demo (W01-W30) ──────────────────────────────────
render_live_demo(
    disease_jp='RSウイルス感染症', weeks_range=range(1, 31),
    sim_csv_path=OUT/'rsv_2024_weekly_simulation.csv',
    jihs_label_week=('Featured 2024/15', 15, '2024-W15'),
    data_anchor_week=(19, '2024-W19'),
    fig_name='fig8_rsv_2024_live_demo.png',
    color='#3F8194',
    title_text='Figure 8 — Real-time simulation: 2024 RSV summer surge (4-detector framework, sentinel disease)'
)

# ── Fig 7 & Fig 9: prefecture heatmaps ───────────────────────────────────
def render_pref_heatmap(disease_jp, year_filter, week_max, fig_name, title_text):
    pref_dict = defaultdict(list)
    with open('/sessions/cool-clever-goldberg/mnt/claude/prefecture_week_timeseries.csv') as f:
        for r in csv.DictReader(f):
            if r['disease'] == disease_jp:
                pref_dict[r['prefecture']].append({
                    'year': int(r['year']), 'week': int(r['iso_week']), 'total': int(r['cases'])
                })
    pref_cum = {p: sum(r['total'] for r in s if r['year']==year_filter and r['week']<=week_max)
                for p, s in pref_dict.items()}
    TIER_ORDER = ['high_urban','mixed','rural_leaning']
    sorted_p = []
    for t in TIER_ORDER:
        tp = sorted([(p,c) for p,c in pref_cum.items() if URBAN.get(p)==t], key=lambda x: -x[1])
        sorted_p.extend([(p,c,t) for p,c in tp])
    fig, ax = plt.subplots(figsize=(8.5, 9))
    y_pos = np.arange(len(sorted_p))
    pref_labels = [f'{en_pref(p)} ({c})' for p, c, t in sorted_p]
    for s in pref_labels: assert_ascii_safe(s, 'pref heatmap label')
    ax.barh(y_pos, [item[1] for item in sorted_p],
            color=[TIER_C[item[2]] for item in sorted_p], edgecolor='white')
    ax.set_yticks(y_pos); ax.set_yticklabels(pref_labels, fontsize=8); ax.invert_yaxis()
    ax.set_xlabel(f'{year_filter} cumulative cases (W01-W{week_max})', fontsize=10)
    assert_ascii_safe(title_text, 'pref heatmap title')
    ax.set_title(title_text, fontsize=11)
    ax.legend(handles=[mpatches.Patch(color=TIER_C[t], label=en_tier(t)) for t in TIER_ORDER],
              loc='lower right', fontsize=9)
    ax.grid(axis='x', alpha=0.3); plt.tight_layout()
    plt.savefig(FIG/fig_name, dpi=140, bbox_inches='tight'); plt.close()
    print(f'{fig_name}: saved')

render_pref_heatmap('麻しん', 2026, 16, 'fig7_measles_2026_prefecture_heatmap.png',
    'Figure 7 — 2026 Measles cumulative cases by prefecture, grouped by DID urban tier')
render_pref_heatmap('RSウイルス感染症', 2024, 30, 'fig9_rsv_2024_prefecture_heatmap.png',
    'Figure 9 — 2024 RSV cumulative cases by prefecture, grouped by DID urban tier')

print('\n=== ALL 9 FIGURES RE-RENDERED IN ENGLISH ===')
