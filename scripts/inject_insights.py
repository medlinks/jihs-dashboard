"""
異常検知結果と AI 解説を dashboard.html に注入する。

使い方:
  # 異常検知だけ更新（detect_anomalies.py を先に実行）
  python3 scripts/inject_insights.py --anomalies-only

  # AI 解説も同時に更新
  python3 scripts/inject_insights.py --commentary "ここに本週の解説本文..."

  # ファイルから読む
  python3 scripts/inject_insights.py --commentary-file path/to/commentary.txt
"""
import argparse
import json
import re
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / 'dashboard.html'
ANOMALIES_JSON = ROOT / 'scripts' / 'anomalies.json'


def _safe_replace(html: str, pattern: str, replacement: str, flags=0) -> str:
    """re.sub の replacement は \\1 等を解釈するので、index ベースで置換する"""
    m = re.search(pattern, html, flags)
    if not m:
        return html
    return html[:m.start()] + replacement + html[m.end():]


def inject_anomalies(html: str) -> tuple[str, int]:
    if not ANOMALIES_JSON.exists():
        return html, 0
    with open(ANOMALIES_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)
    anoms = data.get('anomalies', [])
    ts = data.get('generated_at', datetime.datetime.now().isoformat())
    payload = json.dumps(anoms, ensure_ascii=False, separators=(',', ':'))
    html = _safe_replace(html, r'DATA\.anomalies = \[[^\]]*\];',
                         'DATA.anomalies = ' + payload + ';')
    html = _safe_replace(html, r'DATA\.anomaly_check_at = [^;]+;',
                         f'DATA.anomaly_check_at = "{ts}";')
    return html, len(anoms)


def inject_commentary(html: str, text: str) -> str:
    if not text:
        return html
    now = datetime.datetime.now().isoformat()
    payload = json.dumps(text, ensure_ascii=False)
    html = _safe_replace(html, r'DATA\.ai_commentary = "[^"]*";',
                         f'DATA.ai_commentary = {payload};')
    html = _safe_replace(html, r'DATA\.ai_commentary_at = [^;]+;',
                         f'DATA.ai_commentary_at = "{now}";')
    return html


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--anomalies-only', action='store_true')
    p.add_argument('--commentary', type=str, default=None,
                   help='AI 解説の本文（直接渡す）')
    p.add_argument('--commentary-file', type=str, default=None,
                   help='AI 解説の本文をファイルから読む')
    args = p.parse_args()

    if not DASHBOARD.exists():
        raise SystemExit(f'dashboard.html が見つかりません: {DASHBOARD}')

    with open(DASHBOARD, 'r', encoding='utf-8') as f:
        html = f.read()

    html, n_anom = inject_anomalies(html)
    print(f'異常注入: {n_anom} 件')

    if not args.anomalies_only:
        text = args.commentary
        if args.commentary_file:
            with open(args.commentary_file, 'r', encoding='utf-8') as f:
                text = f.read().strip()
        if text:
            html = inject_commentary(html, text)
            print(f'AI 解説注入: {len(text)} 文字')
        else:
            print('AI 解説 未指定（既存の解説は維持）')

    with open(DASHBOARD, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'dashboard.html 更新完了: {DASHBOARD}')


if __name__ == '__main__':
    main()
