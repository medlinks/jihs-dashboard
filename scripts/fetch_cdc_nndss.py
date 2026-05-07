"""
CDC NNDSS 週次データ fetcher

データソース: data.cdc.gov dataset x9gk-5huc
  Name: NNDSS Weekly Data
  Coverage: 2022-2026 (5年)
  Columns:
    states  - 報告地域 (50 州 + 地域 + 全国総計)
    year    - MMWR Year (文字列)
    week    - MMWR Week
    label   - 疾病名
    m1      - 当週件数 (Current week)
    m2      - 過去52週最大値 (Previous 52-week max)
    m3      - 年累積 YTD (Cumulative YTD current year)
    m4      - 前年同期累積 (Cumulative YTD previous year)
    m1_flag .. m4_flag  - データなしの理由（'-' = 報告なし）

注意: 全国合計の "states" 名は年によって変動
  - 2022, 2024: "US RESIDENTS"
  - 2023:        "U.S. RESIDENTS" / "US RESIDENTS"
  - 2025-2026:   "U.S. Residents" / "Total"
  → aggregate_us.py 側で normalize する

使い方:
  python3 scripts/fetch_cdc_nndss.py             # 2022-2026 全年取得
  python3 scripts/fetch_cdc_nndss.py --year 2026 # 指定年のみ
  python3 scripts/fetch_cdc_nndss.py --year 2026 --refresh  # 既存ファイル上書き
"""
import argparse
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "us" / "raw" / "nndss"
DATASET_ID = "x9gk-5huc"
BASE_URL = f"https://data.cdc.gov/resource/{DATASET_ID}.json"

YEARS = [2022, 2023, 2024, 2025, 2026]
PAGE_SIZE = 50000  # SODA API 推奨ページサイズ


def fetch_page(year: int, offset: int) -> list:
    """1 ページ分取得"""
    qs = urllib.parse.urlencode({
        "$where": f"year='{year}'",
        "$order": "sort_order",
        "$limit": str(PAGE_SIZE),
        "$offset": str(offset),
    })
    url = f"{BASE_URL}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "JIHS-Dashboard/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < 2:
                print(f"    retry {attempt+1}: {e}")
                time.sleep(2 ** attempt)
            else:
                raise


def fetch_year(year: int) -> list:
    """指定年の全レコードを取得（ページング自動）"""
    all_rows = []
    offset = 0
    while True:
        page = fetch_page(year, offset)
        if not page:
            break
        all_rows.extend(page)
        print(f"    page offset={offset}: +{len(page)}件 (累計 {len(all_rows)})")
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def save_year(year: int, rows: list):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{year}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"  → {path.name}: {size_mb:.1f} MB ({len(rows)} 件)")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--refresh", action="store_true",
                   help="既存ファイルを上書き（既定はスキップ）")
    args = p.parse_args()

    years = [args.year] if args.year else YEARS
    print(f"=== CDC NNDSS Fetch (dataset {DATASET_ID}) ===")
    print(f"対象年: {years}\n")

    for y in years:
        out = RAW_DIR / f"{y}.json"
        if out.exists() and not args.refresh:
            size_mb = os.path.getsize(out) / (1024 * 1024)
            print(f"{y}: 既存ファイル {out.name} ({size_mb:.1f} MB) スキップ（--refresh で再取得）")
            continue
        print(f"{y}: 取得中...")
        rows = fetch_year(y)
        save_year(y, rows)
        time.sleep(1)  # レート抑制

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
