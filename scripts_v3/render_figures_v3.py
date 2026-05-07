"""Phase B5 figures: 5 PNGs to outputs/figures_v3/"""
import csv, json, os
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from collections import defaultdict

# ── CJK font setup ────────────────────────────────────────────────────────
# macOS-first, Linux-fallback; explicitly register fonts that matplotlib
# doesn't auto-discover (Droid Sans Fallback ships with most Linux but
# matplotlib.font_manager often misses it).
def setup_cjk_font():
    candidates_macos = [
        'Hiragino Sans', 'Hiragino Maru Gothic Pro',
        'Apple SD Gothic Neo', 'Arial Unicode MS', 'Noto Sans CJK JP',
    ]
    candidates_linux_paths = [
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf',
    ]
    available_names = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in candidates_macos if c in available_names), None)
    if chosen:
        plt.rcParams['font.family'] = chosen
        plt.rcParams['axes.unicode_minus'] = False
        print(f'CJK font (macOS): {chosen}')
        return chosen
    # Linux: explicit register
    for path in candidates_linux_paths:
        if os.path.exists(path):
            font_manager.fontManager.addfont(path)
            family = font_manager.FontProperties(fname=path).get_name()
            plt.rcParams['font.family'] = family
            plt.rcParams['axes.unicode_minus'] = False
            print(f'CJK font (Linux, registered): {family}  ({path})')
            return family
    raise RuntimeError(
        'No CJK-compatible font found. macOS users: should be auto-detected. '
        'Linux users: install via `apt install fonts-droid-fallback` or '
        '`brew install --cask font-noto-sans-cjk-jp`.'
    )

CJK_FONT = setup_cjk_font()

OUT = Path('/sessions/cool-clever-goldberg/mnt/outputs')
FIG = OUT / 'figures_v3'; FIG.mkdir(exist_ok=True)

# Load retrospective results
rows = []
with open(OUT/'retrospective_results_v3.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f): rows.append(r)

OUTBREAKS = sorted(set(int(r['outbreak_id']) for r in rows))
DISEASES = {int(r['outbreak_id']): r['disease'] for r in rows}
DETECTORS = ['D_rare', 'D_stat', 'D_growth', 'D_spatial', 'Combined_OR']

# ── Fig 1: lead-time heatmap ──────────────────────────────────────────────
M = np.full((len(OUTBREAKS), len(DETECTORS)), np.nan)
labels = np.empty(M.shape, dtype=object)
for r in rows:
    i = OUTBREAKS.index(int(r['outbreak_id']))
    j = DETECTORS.index(r['detector'])
    if r['lead_weeks'] != '':
        try:
            v = int(r['lead_weeks'])
            M[i, j] = v
            labels[i, j] = f'{v:+d}'
        except ValueError: labels[i, j] = '-'
    else:
        labels[i, j] = '–'

fig, ax = plt.subplots(figsize=(8.5, 6.5))
cmap = plt.cm.RdYlGn
norm = matplotlib.colors.Normalize(vmin=-26, vmax=26)
masked = np.ma.masked_invalid(M)
im = ax.imshow(masked, cmap=cmap, norm=norm, aspect='auto')
for i in range(len(OUTBREAKS)):
    for j in range(len(DETECTORS)):
        if np.isnan(M[i, j]):
            ax.add_patch(plt.Rectangle((j-0.5, i-0.5), 1, 1, fill=True, color='#EEEEEE'))
        ax.text(j, i, labels[i, j], ha='center', va='center', fontsize=10, fontweight='bold')
ax.set_xticks(range(len(DETECTORS)))
ax.set_xticklabels(DETECTORS, rotation=15, ha='right', fontsize=10)
ax.set_yticks(range(len(OUTBREAKS)))
ax.set_yticklabels([f'#{i} {DISEASES[i][:14]}' for i in OUTBREAKS], fontsize=9)
ax.set_xlabel('Detector', fontsize=11)
ax.set_ylabel('Outbreak (v3.1 curation)', fontsize=11)
ax.set_title('Phase B Figure 1 — Lead-time matrix (weeks before reference outbreak start)\nGreen=earlier · Red=late · Grey=no alert in ±52w', fontsize=11)
plt.colorbar(im, ax=ax, label='Lead time (weeks)')
plt.tight_layout(); plt.savefig(FIG/'fig1_leadtime_heatmap.png', dpi=140, bbox_inches='tight'); plt.close()
print('Saved fig1_leadtime_heatmap.png')

# ── Fig 3: detector necessity (which detector saved which outbreak) ───────
# Stacked bar: per outbreak how many detectors fired within ±26w
TOL = 26
det_fired = defaultdict(set)
for r in rows:
    if r['detector'] == 'Combined_OR': continue
    if r['lead_weeks'] != '' and abs(int(r['lead_weeks'])) <= TOL:
        det_fired[int(r['outbreak_id'])].add(r['detector'])

fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(OUTBREAKS))
det_colors = {'D_rare':'#C96342', 'D_stat':'#3F8194', 'D_growth':'#5C8A4F', 'D_spatial':'#9C7FCF'}
bottom = np.zeros(len(OUTBREAKS))
for det in ['D_rare', 'D_stat', 'D_growth', 'D_spatial']:
    h = np.array([1 if det in det_fired[i] else 0 for i in OUTBREAKS])
    ax.bar(x, h, bottom=bottom, color=det_colors[det], label=det, edgecolor='white')
    bottom += h
ax.set_xticks(x)
ax.set_xticklabels([f'#{i}\n{DISEASES[i][:8]}' for i in OUTBREAKS], fontsize=8, rotation=0)
ax.set_ylabel('Number of detectors firing within ±26w', fontsize=10)
ax.set_title('Phase B Figure 3 — Detector necessity per outbreak (±26w detection tolerance)', fontsize=11)
ax.legend(loc='upper right', fontsize=9)
ax.set_ylim(0, 4.5)
plt.tight_layout(); plt.savefig(FIG/'fig3_detector_necessity.png', dpi=140, bbox_inches='tight'); plt.close()
print('Saved fig3_detector_necessity.png')

# ── Fig 4: false alert rates ──────────────────────────────────────────────
fa_data = defaultdict(lambda: {'sentinel': [], 'full-report': []})
with open(OUT/'false_alert_characterization_v3.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        fa_data[r['detector']][r['class']].append(float(r['alerts_per_year']))

fig, ax = plt.subplots(figsize=(8, 4.5))
dets = ['D_rare', 'D_stat', 'D_growth', 'D_spatial']
sentinel_means = [np.mean(fa_data[d]['sentinel']) if fa_data[d]['sentinel'] else 0 for d in dets]
full_means = [np.mean(fa_data[d]['full-report']) if fa_data[d]['full-report'] else 0 for d in dets]
x = np.arange(len(dets)); w = 0.35
ax.bar(x - w/2, sentinel_means, w, color='#5C8A4F', label='Sentinel (定点)')
ax.bar(x + w/2, full_means, w, color='#C96342', label='Full-report (全数把握)')
ax.set_xticks(x); ax.set_xticklabels(dets, fontsize=10)
ax.set_ylabel('Sustained alerts / year / disease (outside outbreak windows)', fontsize=10)
ax.set_title('Phase B Figure 4 — False-alert rate by detector & disease class', fontsize=11)
ax.legend(); plt.tight_layout()
plt.savefig(FIG/'fig4_false_alert_rate.png', dpi=140, bbox_inches='tight'); plt.close()
print('Saved fig4_false_alert_rate.png')

# ── Fig 2: urban-tier dynamics small multiples (per-tier weekly traces) ─
with open(OUT/'outbreak_urban_tier_dynamics_v3.json', encoding='utf-8') as f:
    dyn = json.load(f)

# Show 6 most-relevant outbreaks (those where we have good prefecture data)
SHOW = ['手足口病', 'RSウイルス感染症', 'インフルエンザ', '麻しん', '梅毒', '咽頭結膜熱']
fig, axes = plt.subplots(2, 3, figsize=(14, 7))
TIER_C = {'high_urban': '#3F8194', 'mixed': '#5C8A4F', 'rural_leaning': '#9C7FCF'}
shown = 0
for i, dn in enumerate(SHOW):
    if dn not in dyn: continue
    ax = axes[shown // 3, shown % 3]
    d = dyn[dn]
    ref_y, ref_w = d['ref_year'], d['ref_week']
    for tier in ('high_urban', 'mixed', 'rural_leaning'):
        tr = d['traces'][tier]
        xs = [(r['year'] - ref_y) * 52 + (r['week'] - ref_w) for r in tr]
        ys = [r['cases'] for r in tr]
        n_total_pref = len(d['tier_prefs'][tier])
        ax.plot(xs, ys, color=TIER_C[tier], lw=1.2, alpha=0.85,
                label=f'{tier} (n={n_total_pref})')
    ax.axvline(0, color='red', lw=0.8, ls='--', alpha=0.6)
    ax.set_title(f'#{d["outbreak_id"]} {dn}', fontsize=10)
    ax.set_xlabel('Weeks rel. anchor', fontsize=8)
    ax.set_ylabel('Cases (tier sum)', fontsize=8)
    ax.tick_params(labelsize=7)
    if shown == 0: ax.legend(fontsize=7, loc='upper left')
    shown += 1
plt.tight_layout(); plt.savefig(FIG/'fig2_urban_tier_dynamics.png', dpi=140, bbox_inches='tight'); plt.close()
print('Saved fig2_urban_tier_dynamics.png')

# ── Fig 5: NESID annual urban/rural ratio (where data exists) ──────────
nesid_ratios = [(d['outbreak_id'], k, d['nesid_annual_urban_rural_ratio'])
                for k, d in dyn.items() if d.get('nesid_annual_urban_rural_ratio') is not None]
fig, ax = plt.subplots(figsize=(7, 3.5))
if nesid_ratios:
    nesid_ratios.sort(key=lambda r: -r[2])
    labels_x = [f"#{r[0]} {r[1][:10]}" for r in nesid_ratios]
    vals = [r[2] for r in nesid_ratios]
    colors = ['#3F8194' if v >= 1.5 else ('#9C7FCF' if v < 0.7 else '#888') for v in vals]
    ax.bar(range(len(vals)), vals, color=colors)
    ax.axhline(1.0, color='black', lw=0.6, ls='--')
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(labels_x, rotation=20, ha='right', fontsize=9)
    ax.set_ylabel('NESID annual urban/rural rate ratio', fontsize=9)
    ax.set_title('Phase B Figure 5 — NESID annual urban-tier ratio (full-report only; granularity comparison)', fontsize=10)
else:
    ax.text(0.5, 0.5, 'No NESID-annual data for v3.1 sentinel outbreaks\n(NESID covers full-report only — by design)',
            ha='center', va='center', transform=ax.transAxes, fontsize=11, color='#666')
    ax.set_axis_off()
plt.tight_layout(); plt.savefig(FIG/'fig5_urban_tier_dual_granularity.png', dpi=140, bbox_inches='tight'); plt.close()
print('Saved fig5_urban_tier_dual_granularity.png')
print(f'\n5 figures saved to {FIG}')
