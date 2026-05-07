"""
CDC NNDSS 州別データ取得（マッピング済み 24 疾病に限定）

データソース: data.cdc.gov dataset x9gk-5huc
Filter: 米国 50 州 + DC + 領土 × 直近 2 年（2025, 2026）× マッピング 24 疾病

出力: us/raw/nndss/states_{year}.json
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "us" / "raw" / "nndss"
MAPPING_FILE = ROOT / "us" / "disease_mapping.json"
DATASET_ID = "x9gk-5huc"
BASE = f"https://data.cdc.gov/resource/{DATASET_ID}.json"

PAGE_SIZE = 10000


def load_target_labels():
    with open(MAPPING_FILE, encoding="utf-8") as f:
        m = json.load(f)
    labels = []
    for entry in m["mapping"]:
        for lab in entry.get("nndss_labels", []):
            labels.append(lab)
    return list(set(labels))


def fetch_page(year: int, labels: list, offset: int) -> list:
    # labels が空なら全疾病
    if labels:
        quoted = ",".join("'" + lab.replace("'", "''") + "'" for lab in labels)
        where = f"year='{year}' AND label IN ({quoted})"
    else:
        where = f"year='{year}'"
    qs = urllib.parse.urlencode({
        "$where": where,
        "$order": "sort_order",
        "$limit": str(PAGE_SIZE),
        "$offset": str(offset),
    })
    url = f"{BASE}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "JIHS-Dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--all", action="store_true", help="マッピング外を含む全 NNDSS 疾病を取得")
    args = p.parse_args()

    years = [args.year] if args.year else [2025, 2026]
    labels = [] if args.all else load_target_labels()
    print(f"対象疾病ラベル: {'全件 (フィルタなし)' if args.all else str(len(labels))+'件'}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for y in years:
        print(f"\n{y} 取得中...")
        all_rows = []
        offset = 0
        while True:
            page = fetch_page(y, labels, offset)
            if not page:
                break
            all_rows.extend(page)
            print(f"  offset={offset}: +{len(page)} (累計 {len(all_rows)})")
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            time.sleep(0.3)

        out = RAW_DIR / f"states_{y}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, separators=(",", ":"))
        print(f"  → {out.name}: {os.path.getsize(out)/1024:.0f} KB ({len(all_rows)} 件)")


if __name__ == "__main__":
    main()
