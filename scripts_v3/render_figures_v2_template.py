"""Phase D figures:
  Figure 1: Lead-time matrix (6 outbreak × 5 detector grid, color-coded heatmap)
  Figure 2: Urban-tier weekly incidence traces (small multiples for 6 outbreaks × 3 tiers)
"""
import json, csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUT = Path('/sessions/cool-clever-goldberg/mnt/outputs')

# Load sensitivity_evaluation.csv
sens = []
with open(OUT/'sensitivity_evaluation.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        sens.append(r)

OUTBREAKS = ['梅毒_2024','麻しん_2026','風疹_2018','RSV_2024','HFMD_2018','Influenza_2022']
DETECTORS = ['D_rare','D_stat','D_growth','D_spatial','combined']

# ── Figure 1: Lead-time matrix heatmap ─────────────────────────────────────
matrix = np.full((len(OUTBREAKS), len(DETECTORS)), np.nan)
labels = np.empty((len(OUTBREAKS), len(DETECTORS)), dtype=object)
for r in sens:
    if r['outbreak'] not in OUTBREAKS or r['detector'] not in DETECTORS: continue
    i = OUTBREAKS.index(r['outbreak'])
    j = DETECTORS.index(r['detector'])
    if r['detected'] == 'True' and r['lead_weeks']:
        try:
            lt = int(r['lead_weeks'])
            matrix[i,j] = lt
            labels[i,j] = f"{lt:+d}"
        except (ValueError, TypeError):
            labels[i,j] = '-'
    else:
        labels[i,j] = '–'

# Plot
fig, ax = plt.subplots(figsize=(9, 5.5))
# Color: red = late (negative), green = early (positive), saturating at +/-26
cmap = plt.cm.RdYlGn
norm = matplotlib.colors.Normalize(vmin=-26, vmax=26)
masked = np.ma.masked_invalid(matrix)
im = ax.imshow(masked, cmap=cmap, norm=norm, aspect='auto')
# Cells without alert → diagonal stripes pattern
for i in range(len(OUTBREAKS)):
    for j in range(len(DETECTORS)):
        if np.isnan(matrix[i,j]):
            ax.add_patch(plt.Rectangle((j-0.5, i-0.5), 1, 1, fill=True, color='#EEEEEE'))
        ax.text(j, i, labels[i,j], ha='center', va='center',
                fontsize=11, fontweight='bold', color='black')
ax.set_xticks(range(len(DETECTORS)))
ax.set_xticklabels(DETECTORS, rotation=20, ha='right', fontsize=10)
ax.set_yticks(range(len(OUTBREAKS)))
ax.set_yticklabels(OUTBREAKS, fontsize=10)
ax.set_xlabel('Detector', fontsize=11)
ax.set_ylabel('Outbreak (anchor)', fontsize=11)
ax.set_title('Lead-time matrix (weeks before reference outbreak start)\nGreen = earlier detection · Red = late · Grey = no alert in ±26w window',
             fontsize=11)
cbar = plt.colorbar(im, ax=ax, label='Lead time (weeks)')
plt.tight_layout()
plt.savefig(OUT/'fig1_leadtime_matrix.png', dpi=150, bbox_inches='tight')
print(f'Saved: fig1_leadtime_matrix.png')
plt.close()

# ── Figure 2: Urban-tier weekly incidence small multiples ──────────────────
with open(OUT/'outbreak_urban_tier_dynamics.json') as f:
    dyn = json.load(f)

fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=False)
TIER_COLORS = {'high_urban': '#3F8194', 'mixed': '#5C8A4F', 'rural_leaning': '#9C7FCF'}
for idx, label in enumerate(OUTBREAKS):
    ax = axes[idx // 3, idx % 3]
    if label not in dyn:
        ax.set_title(f'{label}\n(no data)', fontsize=10)
        continue
    d = dyn[label]
    ref_y, ref_w = d['ref_year'], d['ref_week']
    for tier in ('high_urban','mixed','rural_leaning'):
        trace = d['traces'][tier]
        xs = [(r['year'] - ref_y) * 52 + (r['week'] - ref_w) for r in trace]
        ys = [r['cases'] for r in trace]
        # Normalize per-tier per # active prefectures (incidence proxy)
        n_active = [r['n_active_pref'] for r in trace]
        ys_norm = [(c / max(1, n)) for c, n in zip(ys, n_active)]
        n_total_pref = len(d['tier_prefs'][tier])
        ax.plot(xs, ys_norm, color=TIER_COLORS[tier], linewidth=1.3,
                label=f"{tier} (n={n_total_pref})", alpha=0.85)
    ax.axvline(0, color='red', linewidth=0.8, linestyle='--', alpha=0.6)
    ax.text(0, ax.get_ylim()[1] * 0.9, ' anchor', fontsize=8, color='red')
    ax.set_title(label.replace('_', ' '), fontsize=10)
    ax.set_xlabel('Weeks relative to anchor', fontsize=8)
    ax.set_ylabel('Mean cases per active pref', fontsize=8)
    ax.tick_params(labelsize=8)
    if idx == 0:
        ax.legend(fontsize=7, loc='upper left')
plt.tight_layout()
plt.savefig(OUT/'fig2_urban_tier_dynamics.png', dpi=150, bbox_inches='tight')
print(f'Saved: fig2_urban_tier_dynamics.png')
plt.close()

# Also compute "which tier triggers first" summary
print('\n=== Tier-leading-onset analysis (first week each tier exceeds 50% of its eventual peak) ===')
print(f'{"Outbreak":<18} {"high_urban":>10} {"mixed":>8} {"rural":>8} {"Leader":>10}')
print('-'*60)
tier_leadership = {}
for label, d in dyn.items():
    leaders = {}
    for tier in ('high_urban','mixed','rural_leaning'):
        trace = d['traces'][tier]
        ys_norm = [(r['cases'] / max(1, r['n_active_pref'])) for r in trace]
        if not ys_norm: continue
        peak = max(ys_norm) if ys_norm else 0
        if peak == 0: continue
        # find first week incidence ≥ 50% of peak
        for i, y in enumerate(ys_norm):
            if y >= peak * 0.5:
                wks = (trace[i]['year'] - d['ref_year']) * 52 + (trace[i]['week'] - d['ref_week'])
                leaders[tier] = wks
                break
    if not leaders: continue
    leader_tier = min(leaders.items(), key=lambda kv: kv[1])
    tier_leadership[label] = {'leaders': leaders, 'leader_tier': leader_tier[0],
                              'leader_offset': leader_tier[1]}
    h = leaders.get('high_urban'); m = leaders.get('mixed'); r = leaders.get('rural_leaning')
    print(f'{label:<18} {(h if h is not None else "-"):>10} {(m if m is not None else "-"):>8} '
          f'{(r if r is not None else "-"):>8} {leader_tier[0]:>10}')

with open(OUT/'tier_leadership_summary.json', 'w', encoding='utf-8') as f:
    json.dump(tier_leadership, f, ensure_ascii=False, indent=2)
print(f'\nSaved: tier_leadership_summary.json')
