"""
CDC H5N1 (avian influenza A) human + animal detections fetcher.

Pulls the structured JSON behind CDC's H5 Bird Flu Surveillance and Human
Monitoring page:
  https://www.cdc.gov/bird-flu/h5-monitoring/index.html

Underlying endpoint (discovered by reading h5n1-detections-map.json on the
public site): /wcms/vizdata/NCIRD_FLU/H5Viz/states.json

This is the canonical source for US H5N1 human cases — far more accurate
than NNDSS "Novel Influenza A virus infections" which under-reports by
~10x because most H5 cases are reported via CDC HAN/EOC channels.

Output:
  us/raw/cdc_h5/states_latest.json   (always overwritten with latest)
  us/raw/cdc_h5/states_<YYYY-MM-DD>.json   (dated snapshot — kept for history)

Snapshots are kept so a future aggregator can derive "weekly new cases"
by diffing consecutive snapshots.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request
from pathlib import Path

ENDPOINT = "https://www.cdc.gov/wcms/vizdata/NCIRD_FLU/H5Viz/states.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (jihs-dashboard updater)"}


def fetch():
    req = urllib.request.Request(ENDPOINT, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=os.environ.get("JIHS_PROJECT_ROOT", "."))
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    raw_dir = root / "us" / "raw" / "cdc_h5"
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("=== CDC H5N1 (AVI) fetch ===")
    print(f"  endpoint: {ENDPOINT}")
    data = fetch()
    if not isinstance(data, list):
        print(f"  ! unexpected schema (got {type(data).__name__})", file=sys.stderr)
        sys.exit(1)

    today = datetime.date.today().isoformat()
    latest_path = raw_dir / "states_latest.json"
    snap_path = raw_dir / f"states_{today}.json"

    payload = {"fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
               "endpoint": ENDPOINT,
               "rows": data}
    latest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    if not snap_path.exists():
        snap_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    # Quick summary
    all_animals = [r for r in data if r.get("animal_category") == "All Animals"]
    total_human = sum(int(r.get("total_human_detections", 0) or 0) for r in all_animals)
    total_animal = sum(int(r.get("total_animal_detections", 0) or 0) for r in all_animals)
    epi_week = data[0].get("epi_week", "?") if data else "?"
    print(f"  rows: {len(data)} (states × animal_category combinations)")
    print(f"  epi_week: {epi_week}")
    print(f"  total US human H5 cases (cumulative since Feb 2024): {total_human}")
    print(f"  total US animal H5 detections: {total_animal}")
    print(f"  → {latest_path}")
    print(f"  → {snap_path}")


if __name__ == "__main__":
    main()
