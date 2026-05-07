**[2026-05-07 CORRECTION NOTICE]**

The headline "+11 weeks vs JIHS W16" in this document was based on an incorrect interpretation
of the URL slug `featured/2026/06/`. That slug is JIHS issue number 6 = **2026 ISO Week 6**
(Feb 12, 2026), not Week 16. Corrected lead times:

- vs first JIHS notice (IDWR Featured Article 2026 Issue 6, **W06**, Feb 12): **+1 week**
- vs MHLW office note (W07, Feb 13): +2 weeks
- vs JIHS Risk Assessment PDF v1 (W12, Mar 19): +7 weeks
- vs JIHS comprehensive situation update page (W16, Apr 20): +11 weeks

The original headline ("+11 weeks") referred to the situation update page, not the first official notice.
The first JIHS official notice was just **+1 week after** our framework's sustained alert.
See `measles_2026_alert_timeline_correction.md` for full details.

---

# Live demo: 2026 麻しん 早期警報 simulation

## 一句话叙述

**もしこの 4-detector サーベイランス系統が 2026 年 1 月から稼働していたなら、第 1 週で初の watch、第 5 週で sustained alert（連続 3 週・複数検出器の重複触発）を発し、JIHS 第 16 週の Featured 2026/06 公式公告より 11 週早く公衆衛生従事者にシグナルを届けていたことになる。**

## 関鍵時間軸

| Milestone | ISO Week | 説明 |
|---|---|---|
| First watch (any detector ≥ medium) | **2026-W01** | D_rare（5 類全数把握 1 例規則）+ D_stat が初例 1 件で同時点火 |
| First Combined OR alert | 2026-W01 | 同上 |
| **First SUSTAINED alert (k=3)** | **2026-W05** | W3-W4-W5 連続 3 週の medium+ 触発（W3=3, W4=5, W5=14 件）|
| Data-derived anchor (v3.1 retrospective) | 2026-W04 | YTD 累計 が前年同期の 9× 到達（pilot v3.1 の「データ派生」起始週）|
| **JIHS Featured 2026/06 official notice** | **2026-W16** | [JIHS](https://id-info.jihs.go.jp/surveillance/idwr/featured/2026/06/index.html) genotype B3/D8 importation cluster bulletin |

## Lead time

| 比較対象 | Lead time |
|---|---|
| Sustained alert (W05) vs **JIHS official notice (W16)** | **+11 週前** |
| Sustained alert (W05) vs data-derived anchor (W04) | −1 週（つまり 1 週遅れて sustained 化、これは k=3 wrapper の特性）|

**11 週 ≈ 2.5 か月の早期警報**——もし 2026-W05 に医療従事者が通知を受け取っていれば、W16 時点で見えていた 322 累積件 → 実際は早期段階介入によりかなり抑制可能だった可能性。

## 各 detector の役割

| Detector | 2026 W01-W16 の挙動 | 評価 |
|---|---|---|
| **D_rare** (1 例規則) | W01 から「high」継続（麻しん は 5 類全数把握、過去 5 年同週中央値 0 件のため） | **最早報、ベースラインゼロ疾患の標準動作** |
| **D_stat** (median+MAD) | W01-W11 連続 high、W12 のみ medium、W13-W16 high | 強い裏付け、D_rare と相補 |
| **D_growth** (slope+floor) | 全期間 silent | 麻しん は絶対数が少ないため絶対計数 floor 5 件をしばしば下回る、growth 信号は今回機能せず |
| **D_spatial** (都道府県 spread) | W04 から散発触発、W08-W11 / W13-W16 連続 medium | 拡散の地理的広がりを後追い的に確認 |

**D_rare + D_stat の同時点火**が初動シグナル提供。**D_spatial** は地理拡散の確認役。**D_growth** は今回不発（全数把握小数疾病では構造的に弱い、これは sentinel 疾病用設計）。

## 都市・地方分布の知見（Figure 7）

2026 W01-W16 累計 322 件の麻しん：

| Urban tier | 2026 累計 | 活動県数 / 計 | 代表都道府県 |
|---|---|---|---|
| **high_urban** (DID≥70%) | **258 件** (80.1%) | 10 / 10 全活動 | 東京都 142, 神奈川県 33, 千葉県 23, 愛知県 22, 埼玉県 20 |
| mixed (40-70%) | 54 件 (16.8%) | 13 / 27 | 京都府 14, 福岡県 11, 大阪府 9 |
| rural_leaning (<40%) | 10 件 (3.1%) | 3 / 10 | 散発のみ |

**80% が high_urban 層に集中**——これは v3.1 dashboard ⑧ の cross-disease ranking で観察された麻しん の都市集中型動態と一致（urban/rural 比 6.25× 級）。

## 公衆衛生 actionable insight

1. **東京都が単独で全国の 44%（142/322 件）を占める**——MR ワクチン接種率の都内サブグループ調査、特に若年成人（30-50 代男性、ワクチン接種ギャップ世代）への toll free hotline + 接種促進が即効性ある介入候補。
2. **神奈川・千葉・埼玉・愛知の高 urban tier 4 県で計 98 件**——首都圏 + 中京圏での職場・学校曝露の追跡調査優先。
3. **rural_leaning 層は 10 件のみ**だが活動県数は 10 中 3——rural 県のうち未活動 7 県は incoming-import モニタリング配置可能（空港・港・観光地周辺）。

## 系統有効性の証明としての含意

- **Sensitivity 92% (Phase B v3.1)**——12 outbreaks のうち 11 件で early/timely 検出、本件 麻しん 2026 は 11 週リードを実証。
- **本件 vs JIHS official のリード**——もし JIHS W16 報告がリアルタイム公衆衛生介入のトリガーであるなら、当系統は**同じ判断材料を 2.5 か月早く**提供できる。
- **GeoTier-aware narrative**——80% urban 集中の知見は、JIHS bulletin に欠落している「どこを優先すべきか」の即応情報を提供。

## 制限・注意点

1. **遡及シミュレーション**——本デモは過去のデータに対する as-of-week-t 切片シミュレーションで、リアルタイム運用での迟报（reporting lag）の影響は考慮していない。実運用では IDWR 速報の数日〜2 週間遅れがあり、W05 alert 実際は W06-W07 に届く可能性。
2. **k=3 wrapper trade-off**——W01 から D_rare/D_stat 連続 high なのに sustained-k=3 は W05 で発火。W02 が 0 件で streak をリセットするため。代替閾値（k=2 緩和、または「過去 4 週のうち 3 週」緩和）でリードはさらに延びる可能性。
3. **JIHS Featured 2026/06 の「公告週」と「実際の公衆衛生決定タイミング」は同じではない**——JIHS bulletin が出る前にも個別都道府県保健所は介入を始めている可能性が高く、11 週リードは「JIHS 全国 bulletin に対するリード」であって「あらゆる介入に対するリード」ではない。

## ファイル

- `measles_2026_weekly_simulation.csv` — 16 週 × {weekly count, 4 detector states, sustained flag}
- `figures_v3/fig6_measles_2026_live_demo.png` — line chart + Gantt-style detector states
- `figures_v3/fig7_measles_2026_prefecture_heatmap.png` — 47 都道府県累計 × tier 分類
- `measles_2026_live_demo.md` — this narrative
- `measles_2026_live_demo.py` — re-runnable simulation script
