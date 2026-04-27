"""
JIHS Dashboard 自動更新パイプライン
====================================
このスクリプトはスケジュールタスクから呼ばれるのではなく、
スケジュールタスクのプロンプトが Claude に指示する処理手順を
定義するユーティリティです。

直接実行する場合: python3 update_pipeline.py [check|embed|report]
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE     = Path(__file__).parent
SCRIPTS  = BASE / 'scripts'
STATE    = BASE / 'state.json'
LOG      = BASE / 'pipeline_log.txt'
DASH     = BASE / 'dashboard.html'
NESID_HIST = BASE / 'nesid_historical'


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


# ── 1. 最新週番号チェック ──────────────────────────────────
def get_latest_local_week(year=None):
    """現在のローカルフォルダにある最新のPDFの週番号を返す"""
    if year is None:
        year = datetime.now().year
    folder = BASE / str(year)
    if not folder.exists():
        return 0
    pdfs = sorted(folder.glob(f'idwr{year}-*.pdf'))
    if not pdfs:
        return 0
    # idwr2026-13.pdf or idwr2026-01-02.pdf
    weeks = []
    for p in pdfs:
        m = re.search(r'idwr\d{4}-(\d+)(?:-\d+)?\.pdf', p.name)
        if m:
            weeks.append(int(m.group(1)))
    return max(weeks) if weeks else 0


def get_current_iso_week():
    """現在のISO週番号を返す"""
    return datetime.now().isocalendar()[1]


def check_status():
    """更新が必要かどうかを確認してレポートを返す"""
    year = datetime.now().year
    latest_local = get_latest_local_week(year)
    current_week = get_current_iso_week()
    # JIHS は通常、2週遅れで公開（例：第14週のPDFは第16週頃に公開）
    expected_latest = max(1, current_week - 2)

    state = {}
    if STATE.exists():
        with open(STATE, encoding='utf-8') as f:
            state = json.load(f)

    last_run = state.get('last_run', 'never')

    status = {
        'year': year,
        'latest_local_pdf_week': latest_local,
        'current_iso_week': current_week,
        'expected_latest_pdf': expected_latest,
        'weekly_pdf_needs_update': latest_local < expected_latest,
        'speed_last_processed': state.get('processed_weeks', [])[-1] if state.get('processed_weeks') else 'none',
        'last_pipeline_run': last_run,
    }

    # 年報チェック（前年のNESIDデータが nesid_historical/ にあるか）
    prev_year = year - 1
    nesid_path = NESID_HIST / f'{prev_year}_Syu_04_1.xlsx'
    status['nesid_annual_available'] = nesid_path.exists()
    status['nesid_annual_year'] = prev_year

    return status


# ── 2. 週報PDF抽出 ────────────────────────────────────────
def extract_weekly_pdf(pdf_path: str):
    """新しいPDFからデータを抽出してExcelに出力"""
    log(f'週報PDF抽出開始: {pdf_path}')
    pdf = Path(pdf_path)
    year = int(re.search(r'idwr(\d{4})', pdf.name).group(1))
    year_dir = BASE / str(year)

    script = SCRIPTS / 'extract_jihs_fixed.py'
    result = subprocess.run(
        [sys.executable, str(script), '--year', str(year), '--dir', str(year_dir)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        log(f'ERROR 抽出失敗: {result.stderr[:200]}')
        return False
    log(f'抽出完了: {result.stdout[-200:]}')
    return True


def rebuild_dashboard_json():
    """全年データを集約してfull_dashboard_data.jsonを再生成"""
    log('full_dashboard_data.json 再生成中...')
    script = SCRIPTS / 'extract_all_diseases.py'
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, cwd=str(SCRIPTS)
    )
    if result.returncode != 0:
        log(f'ERROR JSON再生成失敗: {result.stderr[:200]}')
        return False
    log('JSON再生成完了')
    return True


# ── 3. dashboard.html へ再埋め込み ────────────────────────
def embed_into_dashboard():
    """更新されたJSONをdashboard.htmlに再埋め込み"""
    log('dashboard.html 再埋め込み開始...')

    if not DASH.exists():
        log('ERROR dashboard.html が見つかりません')
        return False

    with open(DASH, 'r', encoding='utf-8') as f:
        html = f.read()

    updated_sections = []

    # ── full_dashboard_data (weekly_trends, annual_incidence etc.) ──
    json_path = SCRIPTS / 'full_dashboard_data.json'
    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        compact = json.dumps(new_data, ensure_ascii=False, separators=(',', ':'))

        # annual_incidence
        ai_marker = 'DATA.annual_incidence = '
        ai_idx = html.find(ai_marker)
        if ai_idx != -1:
            end = html.find(';\n', ai_idx)
            if end != -1 and 'annual_incidence' in new_data:
                ai_json = json.dumps(new_data['annual_incidence'], ensure_ascii=False, separators=(',', ':'))
                html = html[:ai_idx] + ai_marker + ai_json + html[end:]
                updated_sections.append('annual_incidence')

        # weekly_trends / speed_trends etc. - full replace via DATA= block
        # Find the combined DATA object initialization
        for key in ['weekly_trends', 'speed_trends', 'weekly_pref', 'speed_pref']:
            marker = f'DATA.{key} = '
            idx = html.find(marker)
            if idx != -1 and key in new_data:
                end = html.find(';\n', idx)
                if end != -1:
                    val_json = json.dumps(new_data[key], ensure_ascii=False, separators=(',', ':'))
                    html = html[:idx] + marker + val_json + html[end:]
                    updated_sections.append(key)

    # ── NESID all_years ──
    nesid_ay_path = Path(__file__).parent.parent.parent / 'nesid_all_years.json'
    # Try common locations
    for p in [
        BASE / 'nesid_all_years.json',
        Path('/sessions/zealous-nifty-brahmagupta/mnt/claude/nesid_all_years.json')
    ]:
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                ay_json = f.read()
            marker = 'DATA.nesid_all_years = '
            idx = html.find(marker)
            if idx != -1:
                end = html.find(';\n', idx)
                if end != -1:
                    html = html[:idx] + marker + ay_json + html[end:]
                    updated_sections.append('nesid_all_years')
            break

    with open(DASH, 'w', encoding='utf-8') as f:
        f.write(html)

    log(f'再埋め込み完了: {", ".join(updated_sections)}')
    return True


# ── 4. 速報処理 ───────────────────────────────────────────
def run_speed_update():
    """collect_idwr.py を実行して速報データを更新"""
    log('速報データ更新開始...')
    script = BASE / 'collect_idwr.py'
    if not script.exists():
        log('WARNING collect_idwr.py が見つかりません')
        return False
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True
    )
    log(f'速報更新結果: returncode={result.returncode}')
    if result.stdout:
        log(result.stdout[-500:])
    if result.returncode != 0 and result.stderr:
        log(f'STDERR: {result.stderr[:200]}')
    return result.returncode == 0


# ── メイン ────────────────────────────────────────────────
if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'check'

    if cmd == 'check':
        status = check_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))

    elif cmd == 'embed':
        embed_into_dashboard()

    elif cmd == 'speed':
        run_speed_update()

    elif cmd == 'detect':
        # 異常検知だけ走らせて dashboard に注入
        log('異常検知開始...')
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / 'detect_anomalies.py')],
            capture_output=True, text=True
        )
        if result.stdout:
            log(result.stdout[-400:])
        if result.returncode == 0:
            inject = subprocess.run(
                [sys.executable, str(SCRIPTS / 'inject_insights.py'), '--anomalies-only'],
                capture_output=True, text=True
            )
            if inject.stdout:
                log(inject.stdout[-200:])
            log('異常検知 完了')
        else:
            log(f'異常検知 失敗: {result.stderr[:200]}')

    elif cmd == 'report':
        status = check_status()
        print('=== JIHS Dashboard 更新ステータス ===')
        print(f'年度: {status["year"]}')
        print(f'ローカル最新PDF週: 第{status["latest_local_pdf_week"]}週')
        print(f'現在のISO週: 第{status["current_iso_week"]}週')
        print(f'週報更新必要: {"YES ⚠" if status["weekly_pdf_needs_update"] else "NO ✓"}')
        print(f'速報最終処理: {status["speed_last_processed"]}')
        print(f'前年NESID ({status["nesid_annual_year"]}): {"利用可能 ✓" if status["nesid_annual_available"] else "未取得"}')
        print(f'最終パイプライン実行: {status["last_pipeline_run"]}')
