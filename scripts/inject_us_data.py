"""
us_full_data.json を dashboard.html に注入
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard.html"
US_JSON = ROOT / "us" / "processed" / "us_full_data.json"
MAPPING = ROOT / "us" / "disease_mapping.json"


def safe_replace(html: str, pattern: str, replacement: str, flags=re.DOTALL) -> tuple[str, bool]:
    m = re.search(pattern, html, flags)
    if not m:
        return html, False
    return html[:m.start()] + replacement + html[m.end():], True


def main():
    with open(US_JSON, encoding="utf-8") as f:
        us = json.load(f)
    with open(MAPPING, encoding="utf-8") as f:
        mapping = json.load(f)

    with open(DASHBOARD, encoding="utf-8") as f:
        html = f.read()

    # 米国データを 1 つの const にまとめる
    payload = {
        "us_weekly_trends": us["us_weekly_trends"],          # English keys (週次 m1 sum)
        "us_weekly_trends_jp": us["us_weekly_trends_jp"],    # 日本疾病名（週次 m1 sum）
        "us_annual_totals": us.get("us_annual_totals", {}),  # raw label 年累計 (m3 max)
        "us_annual_totals_en": us.get("us_annual_totals_en", {}),  # EN 合併 年累計（米国版年報棒図）
        "us_annual_totals_jp": us.get("us_annual_totals_jp", {}),  # JP 合併 年累計（国家対比年報）
        "us_population": us["us_population"],
        "us_years_covered": us["years_covered"],
        "disease_mapping": mapping["mapping"],
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    # マーカ: 既存の "DATA.ai_commentary_at = ..." の直後に挿入
    marker_start = "// === ↑ schedule で更新される ↑ ==="
    if marker_start not in html:
        raise SystemExit("marker not found")

    # 既に挿入済みかチェック → 上書き
    block_start = "// === 米国データ（aggregate_us.py が生成） ==="
    block_end = "// === 米国データ ↑ ==="

    new_block = (
        f"{block_start}\n"
        f"DATA.us_weekly_trends = {json.dumps(payload['us_weekly_trends'], ensure_ascii=False, separators=(',', ':'))};\n"
        f"DATA.us_weekly_trends_jp = {json.dumps(payload['us_weekly_trends_jp'], ensure_ascii=False, separators=(',', ':'))};\n"
        f"DATA.us_annual_totals = {json.dumps(payload['us_annual_totals'], ensure_ascii=False, separators=(',', ':'))};\n"
        f"DATA.us_annual_totals_en = {json.dumps(payload['us_annual_totals_en'], ensure_ascii=False, separators=(',', ':'))};\n"
        f"DATA.us_annual_totals_jp = {json.dumps(payload['us_annual_totals_jp'], ensure_ascii=False, separators=(',', ':'))};\n"
        f"DATA.us_population = {json.dumps(payload['us_population'])};\n"
        f"DATA.us_years_covered = {json.dumps(payload['us_years_covered'])};\n"
        f"DATA.disease_mapping = {json.dumps(payload['disease_mapping'], ensure_ascii=False, separators=(',', ':'))};\n"
        f"{block_end}"
    )

    # 既存のブロックがあれば置換
    pattern = re.escape(block_start) + r".*?" + re.escape(block_end)
    if re.search(pattern, html, re.DOTALL):
        html = re.sub(pattern, lambda m: new_block, html, flags=re.DOTALL)
        print("既存の米国データブロックを更新")
    else:
        # marker_start の直後に挿入
        html = html.replace(marker_start, marker_start + "\n\n" + new_block)
        print("米国データブロックを新規挿入")

    with open(DASHBOARD, "w", encoding="utf-8") as f:
        f.write(html)

    # 統計
    print(f"  EN 疾病: {len(payload['us_weekly_trends'])}")
    print(f"  JP マッチ疾病: {len(payload['us_weekly_trends_jp'])}")
    print(f"  人口データ: {len(payload['us_population'])} 年")
    print(f"  マッピング: {len(payload['disease_mapping'])} エントリ")
    print(f"  → dashboard.html: {DASHBOARD.stat().st_size/1024/1024:.1f} MB")


if __name__ == "__main__":
    main()
