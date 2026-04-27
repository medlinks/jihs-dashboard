"""
Historic Limits 異常検知（Farrington/EARS の簡易版）

各疾病の最新週について、過去5年の同じカレンダー週±2の参照値と比較し、
log変換後のmean+2σを上回る場合に「異常」とフラグする。

Output: anomalies.json
"""
import json
import math
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # /Users/.../Desktop/claude
DATA_FILE = ROOT / "scripts" / "full_dashboard_data.json"
OUTPUT_FILE = ROOT / "scripts" / "anomalies.json"

# パラメタ
LOOKBACK_YEARS = 5      # 過去何年を参照するか
WEEK_WINDOW = 2         # 同じ週の前後 ±N 週も参照に含める（季節性緩和）
Z_HIGH = 3.0            # 厳しい閾値（severity: high）
Z_MED = 2.0             # 注意閾値（severity: medium）
MIN_REFERENCE_OBS = 8   # 参照値が少なすぎる疾病はスキップ
MIN_CURRENT_VALUE = 3   # 報告数が極端に少ない場合は誤報多いのでスキップ


def collect_reference(series, target_year, target_week, lookback=LOOKBACK_YEARS, window=WEEK_WINDOW):
    """target_year-1 から target_year-lookback の範囲で、target_week±window の値を集める"""
    refs = []
    for r in series:
        y = r.get('year')
        w = r.get('week')
        v = r.get('total')
        if y is None or w is None or v is None:
            continue
        if not (target_year - lookback <= y <= target_year - 1):
            continue
        # 週はISO週なので、12月末/1月初の境界をまたがないよう単純比較
        if abs(w - target_week) <= window:
            refs.append(v)
    return refs


def detect_for_disease(name, series):
    """1疾病について最新週の異常判定"""
    if not series or len(series) < 10:
        return None
    # 直近を見つける（year, week 降順）
    sorted_series = sorted(series, key=lambda r: (r.get('year', 0), r.get('week', 0)))
    latest = sorted_series[-1]
    y, w, current = latest.get('year'), latest.get('week'), latest.get('total')
    if y is None or w is None or current is None:
        return None
    if current < MIN_CURRENT_VALUE:
        return None  # 数が少なすぎ、ノイズ判定回避

    refs = collect_reference(series, y, w)
    if len(refs) < MIN_REFERENCE_OBS:
        return None

    # log(x+1) 変換で対称性を改善
    logs = [math.log(v + 1) for v in refs]
    mean = sum(logs) / len(logs)
    if len(logs) > 1:
        var = sum((x - mean) ** 2 for x in logs) / (len(logs) - 1)
        std = math.sqrt(var) if var > 0 else 0.01
    else:
        std = 0.01

    log_current = math.log(current + 1)
    z = (log_current - mean) / std if std > 0 else 0

    expected_mean = math.exp(mean) - 1
    upper_med = math.exp(mean + Z_MED * std) - 1
    upper_high = math.exp(mean + Z_HIGH * std) - 1

    if z >= Z_HIGH:
        severity = "high"
    elif z >= Z_MED:
        severity = "medium"
    else:
        return None  # 異常なし

    ratio = current / max(expected_mean, 0.5)
    return {
        "disease": name,
        "year": y,
        "week": w,
        "current": current,
        "expected_mean": round(expected_mean, 1),
        "upper_95": round(upper_med, 1),
        "upper_99": round(upper_high, 1),
        "z_score": round(z, 2),
        "ratio_to_baseline": round(ratio, 2),
        "n_reference": len(refs),
        "severity": severity,
    }


def main():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    weekly_trends = data.get('weekly_trends', {})
    anomalies = []
    skipped_low_data = 0
    skipped_low_count = 0

    for disease, series in weekly_trends.items():
        result = detect_for_disease(disease, series)
        if result is not None:
            anomalies.append(result)

    # severity → z_score 降順
    anomalies.sort(key=lambda a: (
        0 if a['severity'] == 'high' else 1,
        -a['z_score']
    ))

    output = {
        "generated_at": datetime.datetime.now().isoformat(),
        "method": "historic_limits_log_v1",
        "params": {
            "lookback_years": LOOKBACK_YEARS,
            "week_window": WEEK_WINDOW,
            "z_high": Z_HIGH,
            "z_medium": Z_MED,
        },
        "n_diseases_checked": len(weekly_trends),
        "n_anomalies": len(anomalies),
        "anomalies": anomalies,
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"=== 異常検知結果 ===")
    print(f"対象疾病数: {len(weekly_trends)}")
    print(f"異常検出: {len(anomalies)} 件")
    for a in anomalies:
        print(f"  [{a['severity']:6s}] {a['disease']:25s} W{a['week']:2d}: {a['current']:>5} 件 "
              f"(期待値 {a['expected_mean']:.1f}, z={a['z_score']:.1f}, x{a['ratio_to_baseline']:.1f})")
    print(f"\n出力: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
