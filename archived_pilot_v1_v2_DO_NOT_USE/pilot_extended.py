"""Extended pilot: add sustained-alert variant (k=3 consecutive medium+ weeks)
and a secondary measles anchor at 2026 W16 (the user-identified surge week).
Wider ±52w window to expose true first-alert past the saturation boundary."""
import sys, json
from pathlib import Path
sys.path.insert(0, '/sessions/cool-clever-goldberg/mnt/outputs')
from pilot_lead_time import (load_data, DETECTORS, GROUND_TRUTH,
                              DISEASE_KEY_MAP, weeks_in_window, lead_time_weeks)

# Add a secondary measles anchor — the surge week the user originally cited.
GT_EXT = dict(GROUND_TRUTH)
GT_EXT["麻しん_W16"] = {
    "year": 2026, "week": 16,
    "tier": "internal-strong",
    "source_url": "internal — 57 cases vs 5y same-week median 0",
    "source_type": "data-driven anchor (sensitivity check)",
    "justification": "Secondary anchor at the user-identified W16 surge (57 cases, 5y same-week median = 0). Lead time against this anchor measures how early each detector fires before the visible surge, not before a regulatory bulletin.",
    "caveat": "This anchor is partially IDWR-derived; included only as sensitivity check against the b-tier W5 anchor.",
}

WINDOW = 52  # widen to ±1y to expose true first-alert
SUSTAINED_K = 3  # require 3 consecutive medium+ weeks

def first_alert_with_sustained(detector_fn, disease, weekly_series, weekly_pref,
                                ref_y, ref_w, window, k):
    """Return first week where k consecutive medium+ alerts occur,
       indexed by FIRST week of the streak."""
    weeks = weeks_in_window(weekly_series, ref_y, ref_w, window)
    streak_start = None
    streak_len = 0
    streak_severities = []
    for y, w in weeks:
        sev = detector_fn(disease, weekly_series, weekly_pref, y, w)
        if sev in ('medium', 'high'):
            if streak_len == 0:
                streak_start = (y, w)
            streak_len += 1
            streak_severities.append(sev)
            if streak_len >= k:
                # streak start is (y_first, w_first); look up worst severity in streak
                worst = 'high' if 'high' in streak_severities else 'medium'
                return (streak_start[0], streak_start[1], worst)
        else:
            streak_start = None
            streak_len = 0
            streak_severities = []
    return None

def first_alert_raw(detector_fn, disease, weekly_series, weekly_pref,
                     ref_y, ref_w, window):
    for y, w in weeks_in_window(weekly_series, ref_y, ref_w, window):
        sev = detector_fn(disease, weekly_series, weekly_pref, y, w)
        if sev in ('medium', 'high'):
            return (y, w, sev)
    return None

def main():
    data = load_data()
    wt = data['weekly_trends']
    pref_ts = data['pref_ts']
    rows = []
    for label, gt in GT_EXT.items():
        idwr_disease = label.split('_')[0] if '_' in label else label
        idwr_key = DISEASE_KEY_MAP.get(idwr_disease, idwr_disease)
        if idwr_key not in wt: continue
        ref_y, ref_w = gt['year'], gt['week']
        ws = wt[idwr_key]
        ps = pref_ts.get(idwr_key, {})
        for det_name, det_fn in DETECTORS.items():
            raw = first_alert_raw(det_fn, idwr_key, ws, ps, ref_y, ref_w, WINDOW)
            sustained = first_alert_with_sustained(det_fn, idwr_key, ws, ps,
                                                    ref_y, ref_w, WINDOW, SUSTAINED_K)
            row = {
                'outbreak': label,
                'disease': idwr_key,
                'tier': gt['tier'],
                'detector': det_name,
                'ref_year': ref_y, 'ref_week': ref_w,
            }
            if raw:
                ay, aw, sev = raw
                row['raw_alert'] = f"{ay}/W{aw}"
                row['raw_severity'] = sev
                row['raw_lead'] = lead_time_weeks(ref_y, ref_w, ay, aw)
            else:
                row['raw_alert'] = '-'; row['raw_severity'] = '-'; row['raw_lead'] = None
            if sustained:
                ay, aw, sev = sustained
                row['sustained_alert'] = f"{ay}/W{aw}"
                row['sustained_severity'] = sev
                row['sustained_lead'] = lead_time_weeks(ref_y, ref_w, ay, aw)
            else:
                row['sustained_alert'] = '-'; row['sustained_severity'] = '-'; row['sustained_lead'] = None
            rows.append(row)

    print(f"\n=== Extended pilot — ±{WINDOW}w window, sustained k={SUSTAINED_K} ===\n")
    hdr = f"{'Outbreak':<14} {'Det':<3} {'Ref':<10} {'RawAlert':<10} {'RawLd':>5} {'SustAlert':<10} {'SustLd':>6}"
    print(hdr); print('-' * len(hdr))
    for r in rows:
        ref = f"{r['ref_year']}/W{r['ref_week']}"
        rl = f"{r['raw_lead']:+d}" if r['raw_lead'] is not None else '-'
        sl = f"{r['sustained_lead']:+d}" if r['sustained_lead'] is not None else '-'
        print(f"{r['outbreak']:<14} {r['detector']:<3} {ref:<10} {r['raw_alert']:<10} {rl:>5} {r['sustained_alert']:<10} {sl:>6}")

    # Summary stats: D2 - D1 lead delta on acute outbreaks (exclude chronic syphilis)
    # Use SUSTAINED leads (raw is too saturated)
    print("\n=== Decision rule ===")
    pairs = []
    for outbreak in ['麻しん', '麻しん_W16', '風疹']:  # acute only
        d1 = next((r for r in rows if r['outbreak']==outbreak and r['detector']=='D1'), None)
        d2 = next((r for r in rows if r['outbreak']==outbreak and r['detector']=='D2'), None)
        if d1 and d2 and d1['sustained_lead'] is not None and d2['sustained_lead'] is not None:
            delta = d2['sustained_lead'] - d1['sustained_lead']
            pairs.append((outbreak, d1['sustained_lead'], d2['sustained_lead'], delta))
            print(f"  {outbreak}: D1_lead={d1['sustained_lead']:+d}w, D2_lead={d2['sustained_lead']:+d}w, Δ(D2-D1)={delta:+d}w")
    if pairs:
        avg_delta = sum(p[3] for p in pairs) / len(pairs)
        print(f"  AVG Δ(D2-D1) over acute outbreaks: {avg_delta:+.1f}w  ⇒ {'GO (≥+2w)' if avg_delta >= 2 else 'REFINE (<+2w)'}")

    out = Path('/sessions/cool-clever-goldberg/mnt/outputs/pilot_extended_results.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'rows': rows, 'window': WINDOW, 'sustained_k': SUSTAINED_K,
                   'pairs': pairs, 'avg_delta': avg_delta if pairs else None},
                  f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {out}")

if __name__ == '__main__':
    main()
