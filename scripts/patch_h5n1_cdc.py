"""
Patch the H5N1 entries in us/processed/* with real CDC AVI data.

Background
==========
NNDSS (`Novel Influenza A virus infections`) under-reports H5N1 by ~10x
because most cases are captured by CDC's H5 monitoring program (HAN/EOC
channels) rather than the MMWR notifiable-disease system. CDC publishes
the real per-state cumulative human detection counts at:

  https://www.cdc.gov/wcms/vizdata/NCIRD_FLU/H5Viz/states.json

`fetch_cdc_h5n1.py` saves that into `us/raw/cdc_h5/states_latest.json`.

This script patches the aggregator output before injection, so the
inject_us_data.py + state-block injector pick up the CDC numbers
automatically. It is idempotent — running it twice produces the same
result.

What it patches
===============
1. us/processed/us_state_latest.json
     -> 鳥インフルエンザ（Ｈ５Ｎ１）: real per-state cumulative human cases
2. us/processed/us_state_latest_en.json
     -> Novel Influenza A: same data
3. us/processed/us_full_data.json
     -> us_annual_totals['鳥インフルエンザ（Ｈ５Ｎ１）'][2024..present]:
        replace with CDC cumulative (split heuristically 2024:64 / 2025:7 /
        2026: remainder, since CDC doesn't publish a per-year split — see
        `references/h5n1-year-split.md` if you want to refine this).

Weekly_trends_jp is intentionally left untouched: CDC AVI data is
cumulative-since-Feb-2024 and we don't have weekly granularity from this
endpoint. NNDSS m1 weekly data (sparse zeros + a few non-zeros) is at
least chronologically honest. A future iteration can derive weekly new
cases by diffing consecutive snapshots in `us/raw/cdc_h5/states_*.json`.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Disease keys (must match what aggregate_us.py / aggregate_us_states.py emit)
JP_KEY = "鳥インフルエンザ（Ｈ５Ｎ１）"
EN_KEY = "Novel Influenza A"

# Heuristic year split (sums must equal total CDC cumulative). Update in
# this single dict when CDC publishes additional cases. The split is
# documented public knowledge:
#   2024: ~64 (mostly the Sep-Dec California dairy outbreak)
#   2025: ~7  (additional cases in WA/OH/WY/NV)
#   2026: residual = total - 2024 - 2025 (zero or near-zero so far)
YEAR_FLOOR = {2024: 64, 2025: 7}


def load_cdc(root: Path) -> dict:
    """Return {state: human_count} for the 'All Animals' rows."""
    snap = root / "us" / "raw" / "cdc_h5" / "states_latest.json"
    if not snap.exists():
        print(f"  ! {snap} not found — run fetch_cdc_h5n1.py first", file=sys.stderr)
        sys.exit(2)
    payload = json.loads(snap.read_text())
    rows = payload["rows"] if isinstance(payload, dict) and "rows" in payload else payload
    out = {}
    epi = None
    for r in rows:
        if r.get("animal_category") != "All Animals":
            continue
        epi = epi or r.get("epi_week")
        out[r["state"]] = int(r.get("total_human_detections", 0) or 0)
    return out, epi


def patch_state_file(path: Path, key: str, cdc_states: dict, latest_week: int, latest_year: int):
    if not path.exists():
        print(f"  ! {path} not found, skipping")
        return
    obj = json.loads(path.read_text())
    if key not in obj:
        # Some EN files may not have the key yet — create it.
        obj[key] = {}
    # Take whatever states already exist in this disease's entry as the
    # canonical state list (preserves territory naming, NYC split, etc.)
    existing_states = set(obj[key].keys())
    # Add any CDC states the file doesn't know about (rare)
    for s in cdc_states:
        existing_states.add(s)

    new_entry = {}
    for s in existing_states:
        cum = cdc_states.get(s, 0)
        new_entry[s] = {
            "current": 0,           # CDC doesn't publish a per-week new field
            "cumulative_ytd": cum,  # Cumulative since Feb 2024 (NOT YTD — see footnote)
            "year": latest_year,
            "week": latest_week,
            "_source": "cdc_avi",   # marker so debugging knows where this came from
        }
    obj[key] = new_entry
    path.write_text(json.dumps(obj, ensure_ascii=False))
    total = sum(v["cumulative_ytd"] for v in new_entry.values())
    print(f"  ✓ {path.name}: H5N1 ({key}) → {total} cumulative human cases across {len(new_entry)} states")


def patch_annual_totals(path: Path, total_human: int):
    if not path.exists():
        print(f"  ! {path} not found, skipping")
        return
    obj = json.loads(path.read_text())
    annual = obj.get("us_annual_totals", {})
    if JP_KEY not in annual:
        annual[JP_KEY] = {}
    cur = annual[JP_KEY]
    # Apply heuristic split, then put residual into latest year (2026)
    used = sum(YEAR_FLOOR.values())
    residual = max(total_human - used, 0)
    final = dict(YEAR_FLOOR)
    # latest year = highest year already present in cur, or 2026
    latest_year = max([int(y) for y in cur.keys()] + [2026])
    final[latest_year] = final.get(latest_year, 0) + residual
    cur.update({str(y): v for y, v in final.items()})
    annual[JP_KEY] = cur
    obj["us_annual_totals"] = annual
    path.write_text(json.dumps(obj, ensure_ascii=False))
    print(f"  ✓ {path.name}: annual_totals[{JP_KEY}] = {final} (sum={sum(final.values())})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=os.environ.get("JIHS_PROJECT_ROOT", "."))
    args = ap.parse_args()
    root = Path(args.project_root).resolve()

    print("=== H5N1 CDC AVI patch ===")
    cdc_states, epi = load_cdc(root)
    total_h = sum(cdc_states.values())
    print(f"  CDC AVI snapshot: {epi}, {total_h} total US human cases across {len([s for s,n in cdc_states.items() if n>0])} states with cases")

    # Determine latest year/week from epi_week (MM/DD/YYYY)
    latest_year = 2026
    latest_week = 16
    if epi and "/" in epi:
        try:
            mm, dd, yy = epi.split("/")
            latest_year = int(yy)
            # rough MMWR week from date
            import datetime
            dt = datetime.date(latest_year, int(mm), int(dd))
            latest_week = dt.isocalendar()[1]
        except Exception:
            pass

    proc = root / "us" / "processed"
    patch_state_file(proc / "us_state_latest.json", JP_KEY, cdc_states, latest_week, latest_year)
    patch_state_file(proc / "us_state_latest_en.json", EN_KEY, cdc_states, latest_week, latest_year)
    patch_annual_totals(proc / "us_full_data.json", total_h)
    print("=== done ===")


if __name__ == "__main__":
    main()
