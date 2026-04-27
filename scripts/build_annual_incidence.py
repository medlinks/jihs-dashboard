"""
Aggregate per-year annual_{year}.json files into annual_pref[disease][year][prefecture]
and join with population_data.json to produce incidence rates.

Output:
  scripts/annual_incidence.json
    = {disease: {year: {prefecture: {cases: int, pop_k: int, rate_100k: float}}}}

Only includes diseases present in at least one year AND years 2013-2024.
"""
import json, os, glob, re
from collections import defaultdict

ANNUAL_DIR = '/tmp/annual'
POP_JSON = '/sessions/confident-friendly-babbage/mnt/claude/population/population_data.json'
OUT = '/sessions/confident-friendly-babbage/mnt/claude/scripts/annual_incidence.json'

# 1. Load population data: {(year, prefecture) -> population_k}
with open(POP_JSON, encoding='utf-8') as f:
    pop_data = json.load(f)
pop = {(r['year'], r['prefecture']): r['total_all_k']
       for r in pop_data['prefecture_sex']
       if r.get('total_all_k') is not None}

# Also aggregate an "全国" fallback
# prefecture_sex already has 全国 rows

# 2. Load all annual_{year}.json and pivot to disease-first
annual = defaultdict(lambda: defaultdict(dict))  # disease -> year -> pref -> cases
for path in sorted(glob.glob(f'{ANNUAL_DIR}/annual_*.json')):
    m = re.search(r'annual_(\d{4})\.json$', path)
    if not m: continue
    year = int(m.group(1))
    if year < 2013 or year > 2024: continue  # align with population coverage
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    for disease, pref_totals in d.items():
        for pref, cases in pref_totals.items():
            annual[disease][year][pref] = cases

# Known aliases to canonicalize disease names (mirrors extract_all_diseases.py)
ALIASES = {
    'カルバペネム耐性腸内細菌科細菌感染症': 'カルバペネム耐性腸内細菌目細菌感染症',
    'Ａ群溶血性レンサ球菌咽頭炎': 'レンサ球菌咽頭炎',
    'キャサヌル森林病1': 'キャサヌル森林病',
    '回帰熱1': '回帰熱',
}
# Filter: drop animal-surveillance and spurious entries
SKIP = {
    'ウエストナイル熱鳥類', 'エキノコックス症犬',
    '新型コロナウイルス感染症（疑い例を含む）',  # 疑似例，不用于incidence rate
}
# Apply aliases + SKIP filter
canonical = defaultdict(lambda: defaultdict(dict))
for disease, y_d in annual.items():
    if disease in SKIP: continue
    canon = ALIASES.get(disease, disease)
    if canon in SKIP: continue
    for year, pref_d in y_d.items():
        for pref, cases in pref_d.items():
            prev = canonical[canon][year].get(pref, 0)
            canonical[canon][year][pref] = prev + cases

# 3. Compute incidence rate per 100k: cases / (pop_k*1000) * 100_000 = cases/pop_k * 100
output = {}
for disease, y_d in canonical.items():
    output[disease] = {}
    for year, pref_d in y_d.items():
        yr_out = {}
        for pref, cases in pref_d.items():
            # Normalize prefecture name
            p_clean = pref.replace('\u3000', '').strip()
            pop_k = pop.get((year, p_clean))
            if pop_k is None or pop_k == 0:
                # Try 全国 mismatch patterns
                if p_clean in ('総数',):
                    pop_k = pop.get((year, '全国'))
            if pop_k and pop_k > 0:
                rate = round(cases / pop_k * 100, 3)  # per 100k
            else:
                rate = None
            yr_out[p_clean] = {
                'cases': int(cases),
                'pop_k': pop_k,
                'rate_100k': rate,
            }
        if yr_out:
            output[disease][year] = yr_out

# 4. Save
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, separators=(',', ':'))

# Summary
years_covered = set()
diseases_covered = set()
for disease, y_d in output.items():
    diseases_covered.add(disease)
    years_covered.update(y_d.keys())
print(f'Diseases: {len(diseases_covered)}')
print(f'Years:    {sorted(years_covered)}')
size = os.path.getsize(OUT)
print(f'Output:   {OUT} ({size:,} bytes)')

# Spot-check
for disease in ['結核', '梅毒', 'インフルエンザ']:
    if disease in output and 2024 in output[disease]:
        e = output[disease][2024].get('東京都')
        if e:
            print(f'  {disease} 2024 東京都: cases={e["cases"]}, pop_k={e["pop_k"]}, rate={e["rate_100k"]}/100k')
