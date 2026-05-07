# Live demo: RSV 2024 異常な夏期 surge — sentinel disease companion

## 一句話叙述

**もし当系統が 2024 年初頭から稼働していたなら、第 10 週で初の watch、第 17 週で sustained alert を発し、データ派生 anchor (W19) より 2 週早く RSV の異常夏期 surge を検知していた。ただし JIHS Featured 2024/15 公式公告 (W15) には 2 週遅れた──これは sentinel 疾病の絶対計数 floor が ramp 初期に守備的に働く典型例で、Phase B retrospective で観察された false-alert 抑制との trade-off と一致する。**

## 関鍵時間軸

| Milestone | ISO Week | 説明 |
|---|---|---|
| First watch | **2024-W10** | D_growth 単独触発（cases 1171, slope+1.5IQR 突破）|
| First Combined alert | 2024-W10 | 同上 |
| **First SUSTAINED alert (k=3)** | **2024-W17** | W15-W16-W17 の連続 medium+ |
| Data-derived anchor (v3.1) | 2024-W19 | JIHS が「過去5年間と比べて最多」と判定した第13週以降の点 |
| JIHS Featured 2024/15 publication | 2024-W15 | [JIHS Featured 2024/15](https://id-info.jihs.go.jp/surveillance/idwr/featured/2024/15/index.html) |

## Lead time

| 比較対象 | Lead |
|---|---|
| Sustained (W17) vs **data-derived anchor (W19)** | **+2 週** |
| Sustained (W17) vs **JIHS official (W15)** | **−2 週** |

**麻しん 2026 (+11w vs JIHS) と RSV 2024 (−2w vs JIHS) を併せて報告する論文 narrative は**: 当系統は 全数把握 rare 疾病（麻しん・5 類届出）では JIHS bulletin より大幅に早く反応するが、定点 sentinel 疾病（RSV）では JIHS 編集判断とほぼ同時または若干遅れる。これは sentinel の絶対計数 floor (≥50) と sustained-k=3 の組み合わせがちょうどバランスしている結果。

## 各 detector の挙動（2024 RSV）

| Detector | 主要触発期 | 評価 |
|---|---|---|
| D_rare | silent 全期間 | 5 類定点なので 1 例規則対象外（設計通り）|
| D_stat | silent 全期間 | 過去 5 年同週ベースラインに 2021 RSV 異常夏期 surge が含まれ contamination、median+MAD 閾値が高く設定された結果（Phase B v2 §6.5 と同じ pathology）|
| **D_growth** | W10-W17 散発触発、W15 で high | **主力検出器** — slope > median+1.5IQR の連続 + absolute floor ≥50 が満たされた |
| D_spatial | W15-W17 medium 連続 | 補助確認 — 都道府県拡散でも同期確認 |

→ **sentinel 疾病の case では D_growth + D_spatial の組み合わせが核**、これは 麻しん の case（D_rare + D_stat 主力）と全く異なる役割分担。論文 Methods §"signal-class stratification" の重要証拠。

## 都市・地方分布（2024 W01-W30 cumulative）

| Tier | 累計 | 活動県/全 | Top 都道府県 |
|---|---|---|---|
| high_urban | 42,356 (47%) | 10/10 | 大阪 7,836 / 福岡 5,503 / 東京 5,065 / 北海道 4,528 / 兵庫 4,373 |
| mixed | 38,313 (43%) | 27/27 全活動 | — |
| rural_leaning | 7,429 (8%) | 10/10 全活動 | — |

**麻しん (80% high_urban) との対比**：RSV は urban/rural 比率が **47:43:8 と相対的に均一**、mixed tier も活発に活動。これは ⑧ ranking で「neutral」(0.7-1.5×) に分類される伝統的 sentinel 疾病動態と一致——dashboard ⑧ では RSV はランキングに入っていない（≥50 件 cutoff のため、RSV は週単位ベースで巨大なため annual ranking で上位にはならず）が、tier-uniform 動態の見本ケース。

## 麻しん 2026 と RSV 2024 を併記する論文の含意

| 軸 | 麻しん 2026 | RSV 2024 |
|---|---|---|
| 疾病分類 | 5 類全数把握 | 5 類定点把握 |
| 主力 detector | D_rare + D_stat | D_growth + D_spatial |
| Lead vs data anchor | -1w | **+2w** |
| Lead vs JIHS bulletin | **+11w** | -2w |
| Urban-tier 集中度 | 80% high_urban | 47% high_urban (均一)|
| Sustained alert week | W05 | W17 |

**論文 Discussion での framing**：「one-detector-fits-all は誤り——疾病分類により detector 主力が変わる」。両 demo を併記することで：
1. 全数把握 rare（麻しん）は detector framework が JIHS bulletin より圧倒的に早い
2. Sentinel 定点（RSV）は detector framework が JIHS と同時、若干遅れることもある
3. それぞれの detector の役割は疾病分類で予測可能

## 制限・注意点

1. JIHS Featured 2024/15 W15 vs sustained alert W17: 2 週遅れの理由は sustained-k=3 wrapper の構造的特性 + sentinel growth-floor の保守設計。減らすには k=2 緩和が選択肢だが false-alert rate trade-off あり。
2. D_stat が全期間 silent: 2021 異常 RSV 夏期 surge baseline contamination の証拠としても引用可能（Methods Limitations §"baseline contamination"）。
3. 都道府県別では D_spatial 全 47 県活動だが、tier 内 fraction-elevated 閾値の感度はまだ未調整 (Phase B Refinement 3 deferred)。

## 文件

- `rsv_2024_weekly_simulation.csv` — 30 週 detector states
- `rsv_2024_milestones.json` — milestone 数字
- `figures_v3/fig8_rsv_2024_live_demo.png` — line + Gantt
- `figures_v3/fig9_rsv_2024_prefecture_heatmap.png` — 47 都道府県 × tier
