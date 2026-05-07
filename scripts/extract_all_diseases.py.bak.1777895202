import openpyxl, json
from collections import defaultdict

SKIP = {'疾病@240','疾病@342','疾病@393','疾病@444','疾病@495','疾病@87',
        '疾病@447','疾病@192','疾病@243','疾病@294','疾病@396',
        '感染症','感染症（疑い例を含む）','結核サル','大腸菌感染症',
        # This sheet name is produced by the combined human/animal MERS+bird-flu page
        # (ヒトコブラクダ page). The data is animal surveillance, not human cases.
        # The extract_jihs_fixed.py skip is now in place for future extractions.
        '鳥インフルエンザ（H5N1又はH7N9）中東呼吸器症候群（ME',
        'バクター感染症','回帰熱1','急性呼吸器感染症',
        'エキノコックス症犬','腸球菌感染症','髄膜炎菌性髄膜炎',
        '急性灰白髄炎','Ｂウイルス病','野兎病','狂犬病','サル痘',
        'バンコマイシン耐性黄色ブドウ球菌感染症',
        # Animal surveillance disease names (should never appear after fix, but kept for safety)
        '新型コロナウイルス感染者等情報把握・管理支援システム（HER-SYS）のみへの届出情',
        '鳥インフルエンザ（H5N1又はH7N9）中東呼吸器症候群（MERS）鳥類',
        '鳥インフルエンザ/MERS（合算）',
        }

ALIASES = {
    'カルバペネム耐性腸内細菌科細菌感染症': 'カルバペネム耐性腸内細菌目細菌感染症',
    'Ａ群溶血性レンサ球菌咽頭炎': 'レンサ球菌咽頭炎',
}

PREFECTURES = ['北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県',
               '茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県',
               '新潟県','富山県','石川県','福井県','山梨県','長野県','岐阜県',
               '静岡県','愛知県','三重県','滋賀県','京都府','大阪府','兵庫県',
               '奈良県','和歌山県','鳥取県','島根県','岡山県','広島県','山口県',
               '徳島県','香川県','愛媛県','高知県','福岡県','佐賀県','長崎県',
               '熊本県','大分県','宮崎県','鹿児島県','沖縄県']

trends  = defaultdict(list)
pref_latest = {}        # disease -> {pref: count}  latest data available
pref_year   = {}        # disease -> which year the pref data came from

for year in range(2013, 2027):
    path = f'/sessions/zealous-nifty-brahmagupta/mnt/claude/weekly_extracted/IDWR{year}.xlsx'
    try:
        wb = openpyxl.load_workbook(path, read_only=True)
    except Exception as e:
        print(f'{year}: SKIP ({e})')
        continue

    for sheet_name in wb.sheetnames:
        if sheet_name in SKIP:
            continue
        canonical = ALIASES.get(sheet_name, sheet_name)
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            continue
        header   = rows[0]
        total_row = rows[1]

        # --- weekly totals ---
        for col_idx in range(1, len(header)):
            cell = header[col_idx]
            if cell is None:
                continue
            try:
                week_num = int(str(cell).replace('第','').replace('週','').strip())
            except:
                continue
            if col_idx < len(total_row):
                val = total_row[col_idx]
                trends[canonical].append({
                    'year': year, 'week': week_num,
                    'total': int(val) if val is not None else 0
                })

        # --- latest prefecture data (keep updating so last year wins) ---
        last_col = 0
        for ci in range(1, len(header)):
            if header[ci] is not None:
                last_col = ci
        if last_col > 0:
            pref_map = {}
            for row in rows[2:]:
                if not row or row[0] is None:
                    continue
                pref_name = str(row[0]).strip()
                if pref_name in PREFECTURES and last_col < len(row):
                    v = row[last_col]
                    pref_map[pref_name] = int(v) if v is not None else 0
            if pref_map:
                pref_latest[canonical] = pref_map
                pref_year[canonical]   = year

    wb.close()
    print(f'{year}: OK')

# Sort & deduplicate
for d in trends:
    trends[d].sort(key=lambda p: (p['year'], p['week']))
    seen = set(); deduped = []
    for p in trends[d]:
        k = (p['year'], p['week'])
        if k not in seen:
            seen.add(k); deduped.append(p)
    trends[d] = deduped

# ── Zero-fill rare Class 1/2 diseases ──────────────────────────────────────────
# These diseases are on the 全数報告 page in every weekly report but historically
# have zero human cases in Japan. They must still appear in the dashboard so that
# any future outbreak is immediately visible. We use a reference disease to obtain
# the full week list and fill in zeros.
#
# Note: The non-zero entries in older Excel files for the truncated merged sheet
# name come from animal (avian/primate) surveillance — NOT human cases. Those are
# correctly skipped via the SKIP set above.
RARE_CLASS1 = [
    'ジフテリア',
    '重症急性呼吸器症候群',
    '中東呼吸器症候群',
    '鳥インフルエンザ（H5N1)',
    '鳥インフルエンザ（H7N9)',
]
# Use インフルエンザ as the reference week-list (covers 2013-present)
ref_key = 'インフルエンザ'
if ref_key in trends:
    ref_weeks = trends[ref_key]
    for disease in RARE_CLASS1:
        if disease not in trends:
            print(f'  Zero-filling: {disease} ({len(ref_weeks)} weeks)')
            trends[disease] = [{'year': p['year'], 'week': p['week'], 'total': 0}
                               for p in ref_weeks]
        else:
            print(f'  Already present: {disease} ({len(trends[disease])} weeks)')
else:
    print('WARNING: reference disease not found, skipping zero-fill')

print(f'\nExtracted {len(trends)} diseases')

# Load existing speed data
with open('/sessions/zealous-nifty-brahmagupta/mnt/claude/scripts/full_dashboard_data.json') as f:
    existing = json.load(f)

# Replace weekly data with full set
existing['weekly_trends'] = dict(trends)
existing['weekly_pref']   = pref_latest

with open('/sessions/zealous-nifty-brahmagupta/mnt/claude/scripts/full_dashboard_data.json', 'w', encoding='utf-8') as f:
    json.dump(existing, f, ensure_ascii=False)

print('Saved full_dashboard_data.json')
import os
size = os.path.getsize('/sessions/zealous-nifty-brahmagupta/mnt/claude/scripts/full_dashboard_data.json')
print(f'File size: {size/1024:.0f} KB')
