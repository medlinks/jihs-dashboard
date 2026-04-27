"""
Regression verifier for JIHS dashboard data.

Reads tests/reference_values.yaml (curated known-good values) and compares
against tests/full_dashboard_data.json.

Usage:
  python tests/verify_references.py                      # check 総数 entries only (fast)
  python tests/verify_references.py --full              # also verify prefecture entries by re-extracting from PDFs
  python tests/verify_references.py --yaml <path>       # use a different reference file

Exit code:
  0 if all references match, 1 if any mismatch.
"""
import argparse, json, sys, os, re, yaml
from pathlib import Path
from collections import defaultdict


def load_references(yaml_path):
    with open(yaml_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('references', [])


def check_totals(refs, dash_json_path):
    """Fast path: check 総数 references against weekly_trends in the dashboard JSON."""
    with open(dash_json_path, encoding='utf-8') as f:
        dash = json.load(f)
    trends = dash.get('weekly_trends', {})
    passed, failed, skipped = 0, [], 0
    for r in refs:
        if r['prefecture'] != '総数':
            skipped += 1
            continue
        disease = r['disease']
        if disease not in trends:
            failed.append((r, None, f'disease not in dashboard'))
            continue
        entries = trends[disease]
        match = next((e for e in entries if e['year'] == r['year'] and e['week'] == r['week']), None)
        if match is None:
            failed.append((r, None, f'no entry for year={r["year"]} week={r["week"]}'))
        elif match['total'] != r['value']:
            failed.append((r, match['total'], 'value mismatch'))
        else:
            passed += 1
    return passed, failed, skipped


def check_prefecture_from_pdfs(refs, pdf_root, script_dir):
    """Slow path: re-extract specific (year, week, disease, prefecture) from PDFs."""
    sys.path.insert(0, script_dir)
    import pdfplumber
    from extract_jihs_fixed import extract_page, should_skip_page

    # Group refs by (year, week) to minimize PDF loads
    by_yw = defaultdict(list)
    for r in refs:
        if r['prefecture'] == '総数':
            continue
        by_yw[(r['year'], r['week'])].append(r)

    passed, failed = 0, []
    pdf_root = Path(pdf_root)

    # For each (year, week), find the PDF (single or merged) and extract
    loaded_cache = {}  # {pdf_path: {disease: {pref: value}}} keyed by week resolved
    for (year, week), batch in sorted(by_yw.items()):
        year_dir = pdf_root / str(year)
        if not year_dir.exists():
            for r in batch:
                failed.append((r, None, f'year dir missing: {year_dir}'))
            continue
        # Find matching PDF: idwr{year}-{week}.pdf OR a merged idwr{year}-{w1}-{w2}.pdf
        # containing this week
        matched_pdf = None
        for pdf in year_dir.glob(f'idwr{year}-*.pdf'):
            m = re.match(rf'idwr{year}-(\d+)(?:-(\d+))?\.pdf', pdf.name)
            if not m:
                continue
            w1 = int(m.group(1))
            w2 = int(m.group(2)) if m.group(2) else w1
            if w1 <= week <= w2:
                matched_pdf = (pdf, w1, w2)
                break
        if matched_pdf is None:
            for r in batch:
                failed.append((r, None, f'no PDF found for {year} wk{week}'))
            continue

        pdf, w1, w2 = matched_pdf
        cache_key = str(pdf)
        if cache_key not in loaded_cache:
            per_week = {w1: defaultdict(dict)} if w1 == w2 else {w1: defaultdict(dict), w2: defaultdict(dict)}
            with pdfplumber.open(pdf) as pdfdoc:
                current_wk = w1 if w1 == w2 else None
                for page in pdfdoc.pages:
                    words = page.extract_words(x_tolerance=3, y_tolerance=3)
                    page_text = ''.join(wd['text'] for wd in words)
                    if w1 != w2:
                        if f'{w2}週のデータ' in page_text:
                            current_wk = w2
                        elif f'{w1}週のデータ' in page_text:
                            current_wk = w1
                    if current_wk is None:
                        continue
                    if '報告数' not in page_text or '北海道' not in page_text:
                        continue
                    if should_skip_page(page_text):
                        continue
                    result = extract_page(page)
                    for d, pd in result.items():
                        for p, v in pd.items():
                            per_week[current_wk][d][p] = v
            loaded_cache[cache_key] = per_week

        per_week = loaded_cache[cache_key]
        for r in batch:
            data = per_week.get(r['week'], {})
            got = data.get(r['disease'], {}).get(r['prefecture'])
            if got is None:
                failed.append((r, None, 'not found in PDF extraction'))
            elif int(got) != int(r['value']):
                failed.append((r, got, 'value mismatch'))
            else:
                passed += 1

    return passed, failed


def main():
    ap = argparse.ArgumentParser()
    default_yaml = Path(__file__).parent / 'reference_values.yaml'
    default_json = Path(__file__).parent.parent / 'scripts' / 'full_dashboard_data.json'
    default_pdf_root = Path(__file__).parent.parent
    default_scripts = Path(__file__).parent.parent / 'scripts'
    ap.add_argument('--yaml', default=str(default_yaml))
    ap.add_argument('--dash-json', default=str(default_json))
    ap.add_argument('--pdf-root', default=str(default_pdf_root))
    ap.add_argument('--scripts-dir', default=str(default_scripts))
    ap.add_argument('--full', action='store_true',
                    help='Also re-extract prefecture-level values from PDFs (slow)')
    args = ap.parse_args()

    refs = load_references(args.yaml)
    print(f'Loaded {len(refs)} reference values from {args.yaml}')

    # Phase 1: totals
    p1, f1, skip1 = check_totals(refs, args.dash_json)
    print(f'\n[Phase 1] Totals check vs {args.dash_json}')
    print(f'  passed: {p1}, failed: {len(f1)}, skipped (non-total): {skip1}')
    for r, got, reason in f1[:20]:
        print(f'  ✗ {r["year"]} wk{r["week"]} {r["disease"]}/{r["prefecture"]}: expected={r["value"]}, got={got} ({reason})')

    p2, f2 = 0, []
    if args.full:
        print(f'\n[Phase 2] Prefecture-level check by re-extracting PDFs (slow)')
        p2, f2 = check_prefecture_from_pdfs(refs, args.pdf_root, args.scripts_dir)
        print(f'  passed: {p2}, failed: {len(f2)}')
        for r, got, reason in f2[:20]:
            print(f'  ✗ {r["year"]} wk{r["week"]} {r["disease"]}/{r["prefecture"]}: expected={r["value"]}, got={got} ({reason})')

    total_failed = len(f1) + len(f2)
    print(f'\n--- SUMMARY ---')
    print(f'  Total passed: {p1 + p2}')
    print(f'  Total failed: {total_failed}')
    if not args.full:
        print(f'  Prefecture checks skipped ({skip1}). Use --full to include.')
    sys.exit(1 if total_failed else 0)


if __name__ == '__main__':
    main()
