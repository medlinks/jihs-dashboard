"""
PDF column-header scanner.

Scans every JIHS PDF in the project and reports any page that contains
tabular data (北海道 + prefecture rows) but lacks the expected column
headers — this flags format shifts (e.g., 報告数 renamed to 新規報告).

Usage:
  python tests/check_pdf_headers.py                        # scan all years
  python tests/check_pdf_headers.py --years 2025,2026      # scan specific years
  python tests/check_pdf_headers.py --threshold 3          # warn if >=N pages missing headers per PDF

This is a **read-only** analysis — does not modify any file.
"""
import argparse, re, sys, json
from pathlib import Path
from collections import defaultdict


# Known expected column header texts — update when JIHS adds legitimate new headers
KNOWN_HEADERS = {'報告数', '累積', '定点当り', '定点当たり'}


def scan_pdf(pdf_path, verbose=False):
    """
    Returns dict with:
      total_pages, pages_with_prefecture_data, pages_with_known_header,
      pages_tabular_but_unknown_header, unknown_header_samples
    """
    import pdfplumber
    result = {
        'pdf': pdf_path.name,
        'total_pages': 0,
        'pages_with_pref_data': 0,
        'pages_with_known_header': 0,
        'pages_tabular_but_unknown': 0,
        'unknown_header_samples': [],
        'known_headers_found': set(),
    }
    with pdfplumber.open(pdf_path) as pdf:
        result['total_pages'] = len(pdf.pages)
        for i, page in enumerate(pdf.pages):
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue
            page_text = ''.join(w['text'] for w in words)
            has_pref = '北海道' in page_text and '青森県' in page_text
            if not has_pref:
                continue
            result['pages_with_pref_data'] += 1

            # Look for any known header on this page
            found_any = any(h in page_text for h in KNOWN_HEADERS)
            if found_any:
                result['pages_with_known_header'] += 1
                for h in KNOWN_HEADERS:
                    if h in page_text:
                        result['known_headers_found'].add(h)
            else:
                result['pages_tabular_but_unknown'] += 1
                # Sample nearby words for diagnostics (take top 30 chars context)
                if len(result['unknown_header_samples']) < 5:
                    # Find a snippet around '北海道'
                    idx = page_text.find('北海道')
                    snippet = page_text[max(0, idx-80): idx+20].strip()
                    result['unknown_header_samples'].append({
                        'page': i + 1,
                        'snippet': snippet,
                    })
    result['known_headers_found'] = sorted(result['known_headers_found'])
    return result


def main():
    ap = argparse.ArgumentParser()
    default_root = Path(__file__).parent.parent
    ap.add_argument('--pdf-root', default=str(default_root))
    ap.add_argument('--years', default='', help='Comma-separated years to scan (default: all)')
    ap.add_argument('--threshold', type=int, default=3,
                    help='Flag PDFs with >=N tabular-but-unknown-header pages')
    ap.add_argument('--out', default=None, help='Save JSON report to this path')
    args = ap.parse_args()

    root = Path(args.pdf_root)
    year_filter = set(args.years.split(',')) if args.years else None

    pdfs = []
    for y_dir in sorted(root.iterdir()):
        if not y_dir.is_dir() or not re.match(r'^\d{4}$', y_dir.name):
            continue
        if year_filter and y_dir.name not in year_filter:
            continue
        for pdf in sorted(y_dir.glob('idwr*.pdf')):
            pdfs.append(pdf)

    print(f'Scanning {len(pdfs)} PDFs from {root}')
    reports = []
    flagged = []
    for idx, pdf in enumerate(pdfs, 1):
        try:
            r = scan_pdf(pdf)
        except Exception as e:
            print(f'  [{idx}/{len(pdfs)}] {pdf.name} ERROR: {e}')
            continue
        reports.append(r)
        flag = r['pages_tabular_but_unknown'] >= args.threshold
        marker = ' ⚠' if flag else ''
        print(f'  [{idx}/{len(pdfs)}] {pdf.name}: pages={r["total_pages"]}, '
              f'pref_data={r["pages_with_pref_data"]}, '
              f'known_header_pages={r["pages_with_known_header"]}, '
              f'unknown={r["pages_tabular_but_unknown"]}{marker}')
        if flag:
            flagged.append(r)

    print(f'\n--- SUMMARY ---')
    print(f'  Total PDFs scanned: {len(reports)}')
    print(f'  PDFs flagged (>={args.threshold} unknown-header pages): {len(flagged)}')
    if flagged:
        print('\n  Flagged PDFs:')
        for r in flagged:
            print(f'    {r["pdf"]}: {r["pages_tabular_but_unknown"]} unknown pages')
            for s in r['unknown_header_samples'][:3]:
                print(f'      p{s["page"]}: "{s["snippet"]}"')

    if args.out:
        # Serialize the Reports
        out_reports = [{**r, 'known_headers_found': r['known_headers_found']} for r in reports]
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'reports': out_reports, 'flagged': [r['pdf'] for r in flagged]},
                      f, ensure_ascii=False, indent=2)
        print(f'\n  Full report saved: {args.out}')

    sys.exit(1 if flagged else 0)


if __name__ == '__main__':
    main()
