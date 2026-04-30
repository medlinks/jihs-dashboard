"""
2層方式の異常検知

レイヤー1: 全数把握疾患（感染症法 1類〜5類全数）
  - 1例で警戒（cut-off line = 1）。最新週に1例以上で severity=high。
  - 厚生労働省 感染症法に基づく医師の届出: 直ちに〜7日以内の届出が義務付けられている疾患群。
  - 参考:
      https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/kenkou/kekkaku-kansenshou/kekkaku-kansenshou11/01.html
      https://idsc.tmiph.metro.tokyo.lg.jp/survey/kobetsu/

レイヤー2: 統計的異常検知（Historic Limits / Farrington 簡易版）
  - 過去5年の同週±2週を参照し、log変換後 mean+kσ を上回る週を異常として抽出。
  - 全数把握では 1例検出で既にレイヤー1が発火するため、補完的に「過去比上昇」を可視化する目的で残す。

Output: anomalies.json
"""
import json
import math
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # /Users/.../Desktop/claude
DATA_FILE = ROOT / "scripts" / "full_dashboard_data.json"
OUTPUT_FILE = ROOT / "scripts" / "anomalies.json"

# 感染症法 1類〜5類全数把握 = 1例で警戒対象の疾患
# 出典: 厚生労働省「感染症法における感染症の分類」
FULL_REPORT_DISEASES = {
    # 1類
    'エボラ出血熱','クリミア・コンゴ出血熱','痘そう','南米出血熱','ペスト','マールブルグ病','ラッサ熱',
    # 2類
    '急性灰白髄炎','結核','ジフテリア','重症急性呼吸器症候群','中東呼吸器症候群',
    '鳥インフルエンザ（Ｈ５Ｎ１）','鳥インフルエンザ（Ｈ７Ｎ９）',
    # 3類
    'コレラ','細菌性赤痢','腸管出血性大腸菌感染症','腸チフス','パラチフス',
    # 4類
    'Ｅ型肝炎','ウエストナイル熱','Ａ型肝炎','エキノコックス症','エムポックス','黄熱','オウム病',
    'オムスク出血熱','回帰熱','キャサヌル森林病','Ｑ熱','狂犬病','コクシジオイデス症',
    'ジカウイルス感染症','重症熱性血小板減少症候群','腎症候性出血熱','西部ウマ脳炎','ダニ媒介脳炎',
    '炭疽','チクングニア熱','つつが虫病','デング熱','東部ウマ脳炎','鳥インフルエンザ(Ｈ５Ｎ１を除く）',
    'ニパウイルス感染症','日本紅斑熱','日本脳炎','ハンタウイルス肺症候群','Ｂウイルス病','鼻疽',
    'ブルセラ症','ベネズエラウマ脳炎','ヘンドラウイルス感染症','発しんチフス','ボツリヌス症',
    'マラリア','野兎病','ライム病','リッサウイルス感染症','リフトバレー熱','類鼻疽','レジオネラ症',
    'レプトスピラ症','ロッキー山紅斑熱',
    # 5類全数把握
    'アメーバ赤痢','ウイルス性肝炎','カルバペネム耐性腸内細菌目細菌感染症','急性弛緩性麻痺','急性脳炎',
    'クリプトスポリジウム症','クロイツフェルト・ヤコブ病','劇症型溶血性レンサ球菌感染症',
    '後天性免疫不全症候群','ジアルジア症','侵襲性インフルエンザ菌感染症','侵襲性髄膜炎菌感染症',
    '侵襲性肺炎球菌感染症','水痘（入院例）','水痘（入院例に限る）','先天性風しん症候群',
    '多剤耐性緑膿菌感染症','梅毒','播種性クリプトコックス症','破傷風',
    'バンコマイシン耐性黄色ブドウ球菌感染症','バンコマイシン耐性腸球菌感染症','百日咳',
    '風しん','麻しん','薬剤耐性アシネトバクター感染症',
}

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


RARE_BASELINE_THRESHOLD = 5  # 過去5年中央値 < 5件/週 を「希少」とみなす


def detect_one_case_alert(name, series):
    """全数把握疾患の1例検出アラート（cut-off line = 1）

    感染症法上は全数把握疾患すべてが1例で届出義務を負うが、
    結核・梅毒・百日咳など endemic な疾患は毎週多数の届出があり
    1例アラートとしては実用的でない。
    そこで「過去5年同週±2週の中央値が RARE_BASELINE_THRESHOLD 件未満」の
    希少疾病に限定して 1-case alert を発火する。
    （endemic 疾患はレイヤー2の統計的異常検知で別途モニタリングされる）
    """
    if name not in FULL_REPORT_DISEASES:
        return None
    if not series:
        return None
    sorted_series = sorted(series, key=lambda r: (r.get('year', 0), r.get('week', 0)))
    latest = sorted_series[-1]
    y, w, current = latest.get('year'), latest.get('week'), latest.get('total')
    if y is None or w is None or current is None or current < 1:
        return None
    # ベースライン（過去5年の中央値）を確認 → 希少疾病のみ1例アラートを発火
    refs = collect_reference(series, y, w)
    if refs:
        sorted_refs = sorted(refs)
        median = sorted_refs[len(sorted_refs) // 2]
    else:
        median = 0
    if median >= RARE_BASELINE_THRESHOLD:
        return None  # endemic disease - use statistical detection instead
    # 希少疾病で報告あり → 1例で警戒
    severity = "high" if current >= 1 else "medium"
    return {
        "disease": name,
        "year": y,
        "week": w,
        "current": current,
        "expected_mean": median,
        "upper_95": 0.0,
        "upper_99": 0.0,
        "z_score": None,
        "ratio_to_baseline": None,
        "n_reference": len(refs),
        "severity": severity,
        "baseline_median": median,
        "trigger": "full_report_1case",
        "rule": f"感染症法 全数把握疾患（過去5年同週中央値 {median} 件/週、希少基準 < {RARE_BASELINE_THRESHOLD}）→ 1例で警戒",
        "source": "厚生労働省 感染症法に基づく医師の届出のお願い",
    }


def main():
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    weekly_trends = data.get('weekly_trends', {})

    # Layer 1: 全数把握 → 1例で警戒
    one_case_alerts = []
    for disease, series in weekly_trends.items():
        a = detect_one_case_alert(disease, series)
        if a is not None:
            one_case_alerts.append(a)

    # Layer 2: 統計的異常検知（過去比上昇トレンド）
    statistical = []
    for disease, series in weekly_trends.items():
        result = detect_for_disease(disease, series)
        if result is not None:
            result["trigger"] = "statistical"
            result["rule"] = f"log変換後 mean+{Z_MED}σ 以上を医療警戒、+{Z_HIGH}σ 以上を高警戒"
            statistical.append(result)

    # 結合 & ソート（1-case alertを上位、その中でcurrent降順）
    anomalies = []
    one_case_diseases = {a["disease"] for a in one_case_alerts}
    one_case_alerts.sort(key=lambda a: -a["current"])
    anomalies.extend(one_case_alerts)
    # 統計的異常で1-caseに含まれない or 高severity の場合は別途追加
    for a in statistical:
        if a["disease"] in one_case_diseases:
            # Already covered by 1-case alert; skip duplicate listing
            continue
        anomalies.append(a)
    anomalies.sort(key=lambda a: (
        0 if a['severity'] == 'high' else 1,
        -(a.get('current') or 0),
        -(a.get('z_score') or 0),
    ))

    output = {
        "generated_at": datetime.datetime.now().isoformat(),
        "method": "two_layer_full_report_plus_statistical_v2",
        "params": {
            "layer1": "1-case alert for 感染症法 1類〜5類全数把握",
            "layer2_lookback_years": LOOKBACK_YEARS,
            "layer2_week_window": WEEK_WINDOW,
            "layer2_z_high": Z_HIGH,
            "layer2_z_medium": Z_MED,
        },
        "references": [
            "https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/kenkou/kekkaku-kansenshou/sagasu_ruikei.html",
            "https://idsc.tmiph.metro.tokyo.lg.jp/survey/kobetsu/",
            "https://www.pref.toyama.jp/1279/kansen/ref.html",
        ],
        "n_diseases_checked": len(weekly_trends),
        "n_anomalies": len(anomalies),
        "n_one_case_alerts": len(one_case_alerts),
        "n_statistical": len([a for a in anomalies if a.get('trigger') == 'statistical']),
        "anomalies": anomalies,
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"=== 2層異常検知結果 ===")
    print(f"対象疾病数: {len(weekly_trends)}")
    print(f"  Layer1 (全数把握 1例警戒): {len(one_case_alerts)} 件")
    print(f"  Layer2 (統計的異常):       {len([a for a in anomalies if a.get('trigger') == 'statistical'])} 件")
    print(f"  合計:                      {len(anomalies)} 件")
    for a in anomalies:
        trig = a.get('trigger', '?')
        if trig == 'full_report_1case':
            print(f"  [{a['severity']:6s}] [1例警戒] {a['disease']:25s} W{a['week']:2d}: {a['current']:>5} 件")
        else:
            z = a.get('z_score', 0) or 0
            r = a.get('ratio_to_baseline', 0) or 0
            print(f"  [{a['severity']:6s}] [統計]   {a['disease']:25s} W{a['week']:2d}: {a['current']:>5} 件 "
                  f"(期待値 {a['expected_mean']:.1f}, z={z:.1f}, x{r:.1f})")
    print(f"\n出力: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
