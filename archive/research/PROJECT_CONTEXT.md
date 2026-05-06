# JIHS 感染症週報仪表板项目

> 新会话接手说明：请在对话开头让 Claude 读取此文件，即可快速掌握项目全貌。

---

## 项目概要

本项目从日本 JIHS（感染症疫学研究所）发布的感染症週报 PDF 中提取疾病疫情数据，整合为一个可交互的可视化仪表板。

## 核心文件

| 文件/目录 | 说明 |
|-----------|------|
| `dashboard.html` | 主仪表板（单文件，内嵌全部数据，直接用浏览器打开即可使用） |
| `scripts/extract_jihs_fixed.py` | PDF 数据提取脚本（已修复版本） |
| `scripts/extract_all_diseases.py` | 多年份数据整合脚本 |
| `scripts/full_dashboard_data.json` | 完整数据集（78种疾病 × 周趋势） |
| `scripts/parse_nesid_2024.py` | NESID 2024 年报 Excel 解析脚本（sentinel bug 已修复） |
| `scripts/nesid_2024.json` | NESID 2024 完整解析结果（10MB，全数88+定点26疾病） |
| `nesid_2024/Syu_4_1.xlsx` | NESID 全数把握疾患（88疾病） |
| `nesid_2024/Syu_4_2.xlsx` | NESID 全数把握疾患詳細（93疾病） |
| `nesid_2024/Syu_12_1.xlsx` | NESID 定点把握疾患（26疾病） |
| `2013/` ~ `2026/` | 各年份原始 PDF 文件 |
| `weekly_extracted/` | 提取后的 Excel 中间产物（如存在） |

## 已完成工作

1. **PDF 数据提取**：从 2013–2026 各年份 PDF 提取疾病数据，输出 Excel。
2. **数据整合**：将 78 种疾病的周趋势数据整合为 `full_dashboard_data.json` 并嵌入 `dashboard.html`。
3. **仪表板功能**：
   - 速報データ tab：87疾患、最新4週
   - 週報データ tab：2013-2026 全週趋势、地图
   - 発病率マップ：年度別 × 都道府县发病率（人口10万人对比）
   - **年報 tab（2026-04-17 新增）**：NESID 2024 年报 × 周报对比（见下）
4. **人口数据**：`population/` 目录，2013-2024年 47都道府县 × 男女人口
5. **NESID 2024 年报解析**：`nesid_2024/` 目录，完整解析结果（2026-04-17）

## 年報 tab 说明（2026-04-17 新增）

**入口**：dashboard.html 顶部新增第三个切换按钮「📅 年報（2024）」

**功能**：
- **年次推移チャート**：2013-2024 年间年度合计（来自周报PDF集计）+ NESID 2024 官方数字叠加对比
- **NESID 2024 サマリー**：全数疾患→ 总数/男/女/发病率；定点疾患→ 年度报告数/定点当たり
- **年齢階級別分布**：按年龄段的病例数柱状+折线混合图
- **都道府県ランキング**：2024年各都道府县报告数排名

**关键数据对比（迟报效应验证）**：
| 疾病 | 周报集计 2024 | NESID 2024 | 差分（迟报） |
|------|--------------|-----------|------------|
| 梅毒 | 9,201 件 | 14,829 件 | +5,628 件（+61%）|
| 結核 | 12,403 件 | 16,240 件 | +3,837 件（+31%）|
| インフルエンザ | 1,908,614 件 | 1,911,403 件 | +2,789 件（+0.1%）|

## 数据流

```
PDF (2013/~2026/)
   ↓ extract_jihs_fixed.py
weekly_extracted/*.xlsx
   ↓ extract_all_diseases.py
scripts/full_dashboard_data.json
   ↓ （手动/脚本嵌入）
dashboard.html

NESID Excel (nesid_2024/*.xlsx)
   ↓ parse_nesid_2024.py
scripts/nesid_2024.json (10MB)
   ↓ （精简为175KB compact JSON，嵌入）
dashboard.html (DATA.nesid_2024)
```

## 新会话快速上手

新 Claude 会话接手时请按以下步骤：

1. 读取本文件了解项目背景。
2. 用 `Read` 工具查看 `dashboard.html` 末尾的数据结构，再查看 `scripts/full_dashboard_data.json` 的字段。
3. 若需重新生成数据，先运行 `scripts/extract_jihs_fixed.py`（指定年份 PDF 目录），再运行 `scripts/extract_all_diseases.py` 聚合。
4. 确认 HTML 中数据嵌入方式后再做修改（单文件，直接编辑即可）。

## 已完成验证（2026-04-17）

- 合并周 PDF（共 35 份，2013-2026）：结构检查全部通过 ✓
- 梅毒 2016-2025（521 周）：与手动表 100% 一致 ✓
- 都道府县级抽检（2024/2025 共 3 份合并 PDF）：0 差异 ✓
- 参考值检查（インフルエンザ/結核/水痘 2013-2014）：全部通过 ✓
- Dashboard 已更新至 2026 week 13（当前最新 PDF）
- NESID 2024 梅毒：14,829 件 vs 周报集计 9,201 件（差分 +5,628 件，符合迟报预期）✓
- NESID 2024 結核：16,240 件 vs 周报集计 12,403 件（差分 +3,837 件，符合迟报预期）✓

详见 `VERIFICATION_REPORT.md`。

## 回归测试（已落地）

`tests/` 目录包含两个独立测试工具：

| 文件 | 作用 |
|------|------|
| `tests/reference_values.yaml` | 126 条 (年, 周, 疾病, 都道府县, 值) 参考值 |
| `tests/verify_references.py` | 对比 dashboard JSON + 选择性从 PDF 重抽取 |
| `tests/check_pdf_headers.py` | 扫描所有 PDF，标记"有表格数据但无已知列头"的页面（格式变动告警） |

## 人口数据（2026-04-17 新增，为发病率计算）

`population/` 目录：

| 文件 | 作用 |
|------|------|
| `population_all.xlsx` | **主文件** — 4表：national_age_sex / prefecture_sex / prefecture_age3_sex / README |
| `population_data.json` | JSON 版，直接给 Python/JS 消费 |
| `jinsui_{2021-2024}_t{1,2,3}.xlsx` | 原始下载（總務省統計局） |

**覆盖范围**：**2013-2024（12 年 × 10月1日基準）**（prefecture_sex sheet）

## 待续工作（TODO）

- [ ] 2025 年人口推計公布后按同流程下载并合入 population_all.xlsx
- [ ] 需要时补齐 2013-2020 人口数据（走 e-Stat API 或 v文件列表）
- [ ] NESID 年報 tab 可扩展：添加 2013-2023 年历年年报数据（需下载对应年份 Syu_4_1 等）
- [ ] dashboard.html 写入权限问题：当前 session 的 mnt/claude 挂载只读，新版 dashboard 需手动替换

---

*最后更新：2026-04-17（年報 tab 完成）*
