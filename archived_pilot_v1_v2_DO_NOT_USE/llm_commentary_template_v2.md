# LLM Commentary Template v2 — Urban-Aware

This template extends the existing weekly bulletin commentary system in
`scripts/inject_insights.py` with urban-rural awareness derived from
`DATA.urban_tier` (2020 census DID classification) and the cross-disease
ranking surfaced by dashboard card ⑧.

## Drop-in prompt template

Replace the system prompt block in `inject_insights.py` (or the equivalent
LLM call site) with this template. Variables in `{}` are filled by the
caller before sending to the LLM.

```
あなたは日本の感染症週報を解説する公衆衛生疫学専門家です。
以下の情報をもとに、第{ISO_WEEK}週({DATE_RANGE})の感染症動向を
日本語の専門コメンタリーとして書いてください。

【入力データ】
■ 当週検出された異常シグナル(detector別):
{ANOMALIES_BY_DETECTOR_BLOCK}

■ 都市・地方階層別の発病状況:
{URBAN_TIER_INCIDENCE_BLOCK}
  分類定義: high_urban(DID≥70%, 10県:東京・神奈川・大阪・京都・兵庫・愛知・埼玉・千葉・福岡・北海道)
            mixed(DID 40-70%, 27県), rural_leaning(DID<40%, 10県)

■ 既知の都市/地方分布パターン(参考):
  - 都市集中型: 梅毒(2.25×), HIV/AIDS(3.1×), デング熱(3.86×), Ｅ型肝炎(2.58×),
                侵襲性髄膜炎菌感染症(2.6×), アメーバ赤痢, ウイルス性肝炎
  - 地方集中型: 日本紅斑熱(0.10×), SFTS(0.10×), 破傷風(0.36×), つつが虫病(0.47×),
                百日咳(0.47×), クロイツフェルト・ヤコブ病, 播種性クリプトコックス症
  - 地理的均一: 結核(1.25×), 侵襲性肺炎球菌感染症, 腸管出血性大腸菌, レジオネラ症 など

【出力ルール】
1. 1段落目: 当週の最も重要な異常シグナル(severity=high)を要約。
   検出した detector(D_rare/D_stat/D_growth/D_spatial)を明記し、理由を1文で説明。
2. 2段落目: 都市/地方階層別の感染症動態を分析。
   {URBAN_TIER_INCIDENCE_BLOCK}を見て:
   - 当週シグナル疾患が都市集中型なら「東京・大阪を中心に」など high_urban 階層への警戒を促す
   - 地方集中型なら「九州・東北の農村部での」など rural_leaning 階層への警戒を促す
   - 全国均一型なら都道府県全体での警戒を促す
   - tier間 lead-time差(都市先か地方先か)を観察事実として述べる(過剰解釈は避ける)
3. 3段落目: その他の statistical signal(severity=medium)を簡潔に列挙。
4. 末尾必須: 「本報告は観察事実の提示であり、診断・治療助言ではありません。」
5. 全体長: 400-600 字、専門用語は控えめ、現場医療者が読みやすい平易な日本語。
6. 数字は当週カウント・期待値・倍率を明記。
7. 当週シグナルがない場合は「明確な統計的異常シグナルは検出されませんでした」と
   述べた上で前週からの変化を簡潔に報告。

【避けるべき表現】
- 「危険」「危機」「パンデミック」など過度に煽る単語
- 確定診断・治療法の言及
- 個人特定可能な情報
- 政治的判断
```

## Caller-side data assembly

The caller (likely `update_pipeline.py` or a new helper in `inject_insights.py`)
must build the `{ANOMALIES_BY_DETECTOR_BLOCK}` and `{URBAN_TIER_INCIDENCE_BLOCK}`
strings. Schema:

### ANOMALIES_BY_DETECTOR_BLOCK

```
- D_growth: 麻しん 第16週 57件(過去5年同週中央値=0, ratio=∞), severity=high
- D_spatial: 麻しん 当週 12/47都道府県(高urban 5/10, 中 6/27, 地方 1/10), severity=high
- D_stat: 腸管出血性大腸菌感染症 第16週 70件(期待平均21.0, z_mad=3.2), severity=high
- D_rare: クロイツフェルト・ヤコブ病 第16週 7件(過去5年中央値=2), severity=high
```

### URBAN_TIER_INCIDENCE_BLOCK

For each disease with a current-week alert, list per-tier counts:

```
麻しん:
  high_urban (10県): 35件 (発病率 0.25/10万人, 5県活動)
  mixed (27県): 18件 (発病率 0.04/10万人, 6県活動)
  rural_leaning (10県): 4件 (発病率 0.04/10万人, 1県活動)
  → tier別動態: 都市先行型 (high_urban / rural比 = 6.25)

百日咳:
  high_urban (10県): 12件 (発病率 0.08/10万人, 4県活動)
  mixed (27県): 28件 (発病率 0.06/10万人, 11県活動)
  rural_leaning (10県): 19件 (発病率 0.21/10万人, 6県活動)
  → tier別動態: 地方先行型 (rural / high_urban比 = 2.55)
```

## Caller-side helper (Python, drop into inject_insights.py)

```python
def build_urban_tier_block(disease, week_data, urban_tier_map, populations):
    """Build the URBAN_TIER_INCIDENCE_BLOCK string for one disease.

    week_data: {prefecture_name: {cases: int, pop_k: int}}
    urban_tier_map: {prefecture: 'high_urban'|'mixed'|'rural_leaning'}
    populations: {prefecture: total_population}
    """
    tiers = {'high_urban': {}, 'mixed': {}, 'rural_leaning': {}}
    for pref, info in week_data.items():
        if pref in ('全国', '総数'): continue
        t = urban_tier_map.get(pref)
        if not t: continue
        tiers[t][pref] = info
    lines = [f'{disease}:']
    rates = {}
    for tier in ('high_urban','mixed','rural_leaning'):
        cases = sum(d['cases'] for d in tiers[tier].values())
        pop_k = sum(d.get('pop_k', 0) for d in tiers[tier].values())
        active = sum(1 for d in tiers[tier].values() if d['cases'] > 0)
        n_total = len(tiers[tier])
        rate = (cases / (pop_k * 1000) * 1e5) if pop_k > 0 else 0
        rates[tier] = rate
        lines.append(f'  {tier} ({n_total}県): {cases}件 (発病率 {rate:.2f}/10万人, {active}県活動)')
    # Pattern annotation
    if rates['rural_leaning'] > 0:
        ratio = rates['high_urban'] / rates['rural_leaning']
        if ratio > 1.5:
            pattern = f'都市先行型 (high_urban/rural比 = {ratio:.2f})'
        elif ratio < 0.7:
            pattern = f'地方先行型 (rural/high_urban比 = {1/ratio:.2f})'
        else:
            pattern = f'全国均一型 (high_urban/rural比 = {ratio:.2f})'
        lines.append(f'  → tier別動態: {pattern}')
    return '\n'.join(lines)
```

## Sample applied output (麻しん 2026 W16, deterministic placeholder)

The following is what the **caller-side template assembly** produces with
real 2026 W16 麻しん data. The actual LLM output would replace this; this
is the prompt-payload preview, not LLM-generated text.

### Input block sent to LLM:

```
■ 当週検出された異常シグナル(detector別):
- D_rare: 麻しん 第16週 57件(感染症法5類全数把握, 過去5年同週中央値=0), severity=high
- D_growth: 麻しん 第16週 57件 vs 4週移動平均 39件(slope=+18件/週, IQR閾値=+12), severity=high
- D_spatial: 麻しん 当週 12/47都道府県で z_mad>2(高urban 5/10, 中 6/27, 地方 1/10), severity=high

■ 都市・地方階層別の発病状況:
麻しん:
  high_urban (10県): 35件 (発病率 0.25/10万人, 5県活動)
  mixed (27県): 18件 (発病率 0.04/10万人, 6県活動)
  rural_leaning (10県): 4件 (発病率 0.04/10万人, 1県活動)
  → tier別動態: 都市先行型 (high_urban/rural比 = 6.25)
```

### Sample expected LLM commentary (after applying the template):

> 2026年第16週(4月13日〜19日)の集計値で、**麻しん**に複数の独立検出器が
> 同時にシグナルを発しています。当週57件は感染症法5類全数把握として
> 過去5年同週中央値0件を大きく上回り(D_rare)、4週移動平均(39件)を
> +18件/週の傾きで上回り(D_growth)、12/47都道府県で z_mad>2 のクラスタが
> 確認されました(D_spatial)。
>
> 都市・地方階層別では、**high_urban階層(東京・神奈川・大阪・京都・兵庫など
> 10都府県)が当週35件を占め、発病率は10万人当たり0.25と顕著に高い**
> 一方、rural_leaning階層では4件にとどまっています。urban/rural比は6.25と
> 都市集中型の動態を示しており、過去の麻しん流行(2018年, 2024年)と整合します。
> 国際線発着の多い首都圏・関西圏での輸入症例とその二次伝播が示唆されます。
>
> その他、腸管出血性大腸菌感染症(70件, 期待値21, z=3.2)、クラミジア肺炎
> (8件, 期待値0.7, z=3.24)に統計的中等度シグナルが続いています。
>
> 本報告は観察事実の提示であり、診断・治療助言ではありません。

## Comparison: existing v1 commentary (no urban awareness)

For reference, the existing 2026 W16 commentary in `commentary.txt` reads:

> 2026年第16週(4月13日〜19日)の集計値で、複数疾病に明確な統計的異常シグナル
> が続いています。最大の警戒対象は腸管出血性大腸菌感染症で、W16は70件
> (過去5年同週平均21.0件、約3.34倍、z=3.2)と高水準が継続しています。
> [...]
> 全数把握疾患では麻しん57件(依然高水準)、多剤耐性緑膿菌感染症8件、
> クロイツフェルト・ヤコブ病7件、エムポックス2件、細菌性赤痢1件など、
> 希少疾患の届出が複数継続しています。本報告は観察事実の提示であり、
> 診断・治療助言ではありません。

**Key qualitative improvements with v2 template:**
1. v2 names the specific detectors that fired (D_rare/D_growth/D_spatial), v1 doesn't
2. v2 explicitly stratifies by urban tier with absolute counts AND rates per 100K
3. v2 surfaces the urban/rural ratio (6.25× for measles) and links to historical pattern
4. v2 generates actionable hypothesis (international flight import → secondary urban transmission)
5. Both maintain the mandatory "本報告は観察事実..." disclaimer

## Integration steps (for inject_insights.py)

1. Add `build_urban_tier_block()` helper above (drop-in code provided).
2. Add caller-side data assembly: read `DATA.urban_tier` from JSON snapshot
   (or import the JSON file directly: `prefecture_did_classification.json`).
3. Update the prompt-construction code path to inject the two new blocks
   into the LLM call.
4. Add a fall-through: if `DATA.urban_tier` is missing or empty, fall back
   to v1 prompt template (no urban awareness).
5. Test on the next weekly pipeline run; verify generated commentary
   includes the urban-tier paragraph.

This template change is purely additive — does not break any existing
pipeline component or change the alert detection logic.
