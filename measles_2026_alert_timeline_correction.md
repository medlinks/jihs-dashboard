# 2026 Measles Alert Timeline — Correction Notice

**Issued: 2026-05-07.**
**Severity: HIGH — affects headline lead-time number cited in `phase_b_decision_report_v3.md`, `measles_2026_live_demo.md`, and `main_paper_draft_v1_1.docx`.**

## What was wrong

Previously, the framework's "first sustained alert" at 2026-W05 was compared against `JIHS Featured 2026/06` cited as **2026-W16**, yielding a "+11 week lead" headline.

**This was incorrect.** The URL `id-info.jihs.go.jp/surveillance/idwr/featured/2026/06/index.html` is **IDWR Issue No. 6 of 2026** — i.e., published in **ISO Week 6** (Feb 12, 2026), NOT Week 16. The `06` in the URL slug refers to the issue number, not the week.

Page title verifies: *「IDWR 2026年第6号＜注目すべき感染症＞ 麻しん」* and content header *「麻しん 2026年第1～6週（2026年2月12日現在）」*.

## Correct timeline of 2026 measles official Japanese-government notices

| Notice | ISO Week | Date | Source |
|---|---|---|---|
| Framework's first sustained alert (Combined OR k=3) | **2026-W05** | Feb 5 (sim) | this study |
| **JIHS IDWR 2026 Issue 6 — Featured Article: Measles** | **2026-W06** | Feb 12 | https://id-info.jihs.go.jp/surveillance/idwr/featured/2026/06/index.html |
| MHLW office note to medical institutions ("協力依頼") | 2026-W07 | Feb 13 | https://www.mhlw.go.jp/content/001655886.pdf |
| JIHS Measles Risk Assessment 2026 (1st edition) PDF | 2026-W12 | Mar 19 | https://id-info.jihs.go.jp/risk-assessment/measles/measles_ra_2026_1.pdf |
| JIHS IDWR 2026 Issue 14 — Featured Article: Measles (second) | 2026-W14 | early Apr | https://id-info.jihs.go.jp/surveillance/idwr/featured/2026/14/index.html |
| JIHS situation update page (20260420) | 2026-W16 | Apr 20 | https://id-info.jihs.go.jp/relevant-information/measles/20260420-about-situation/index.html |

## Corrected lead-time

**Sustained alert (W05) vs JIHS first official notice (Featured 2026 Issue 6, W06) = +1 week.**

NOT +11 weeks as previously stated.

## Affected files / sections

| File | Section | Old number | **Corrected number** | Status |
|---|---|---|---|---|
| `figures_v3/fig6_measles_2026_live_demo.png` | JIHS marker line | W16 | **W06** + W07 + W12 + W16 multi-marker | ✓ Re-rendered with corrected markers |
| `measles_2026_live_demo.md` | Headline & milestones | "+11 weeks before W16 official" | **"+1 week before JIHS Issue 6 (W06)"** | needs revision |
| `phase_b_decision_report_v3.md` | §B-rerun discussion of measles | "11 weeks ahead of JIHS official" | **"1 week ahead of JIHS first notice"** | needs revision |
| `main_paper_draft_v1_1.docx` | Abstract Results, §3.5 Live demo, §4.1 Principal findings, §4.3 Public health implications, §5 Conclusions | Multiple "+11 weeks" statements | **"+1 week ahead of first JIHS notice; +9 weeks ahead of MHLW office note; ~14 weeks ahead of comprehensive JIHS situation update"** | needs revision |

## Revised paper narrative for §3.5 / Discussion

**Suggested replacement text** (preserve sustained-alert finding; reframe lead-time as "ahead of first official notice and ahead of subsequent escalations"):

> "Real-time week-by-week simulation of the framework on 2026 measles weekly counts (W01–W16) shows the following trajectory. First D_rare and D_stat alerts triggered at W01 (a single case: count = 1, against 5-year same-week median of 0). After a brief silence at W02 (zero cases), continuous medium-or-high alerts resumed at W03 (3 cases), enabling a sustained alert (k=3) at W05. The first JIHS official Featured Article (IDWR 2026 Issue 6) was published in W06 — placing the framework's sustained alert just **1 week ahead of the first JIHS public notice**. The MHLW office note to medical institutions (`協力依頼`) followed at W07, the JIHS comprehensive risk assessment PDF (1st edition) at W12, and the JIHS situation update page at W16. The framework therefore led the first official notice by 1 week and the comprehensive risk assessment by ~7 weeks. The cumulative case trajectory through W16 reached 322 reported cases nationally, with 80.1% (258 cases) concentrated in the high_urban tier (10 prefectures) and 44% (142 cases) in Tokyo alone. While the +1-week lead over the first JIHS notice is modest in absolute terms, the framework provides a more granular signal: the specific tier-leading prefecture (Tokyo, Kanagawa, Chiba, Aichi, Saitama in descending order) and the disease-class detector pattern (D_rare + D_stat dominance, characteristic of full-report rare-event outbreaks) are surfaced at W05, before any official aggregate notice."

## Revised paper Abstract / Conclusions

**Suggested replacement** for the headline statement:

> "...the framework anticipated the first JIHS official notice (Featured Article 2026 Issue 6, published 2026-W06) for the ongoing 2026 measles outbreak by 1 week, and the comprehensive JIHS Risk Assessment PDF (1st edition, 2026-W12) by 7 weeks."

## Comparison: previous incorrect vs corrected statement

| Statement | Previous | **Corrected** |
|---|---|---|
| Lead vs first JIHS official | +11 weeks | **+1 week** |
| Lead vs MHLW office note | (not tracked) | **+2 weeks** |
| Lead vs JIHS Risk Assessment PDF | (not tracked) | **+7 weeks** |
| Lead vs JIHS situation update page | (was the "JIHS official") | **+11 weeks** (this is W16, the SECONDARY situation update) |

## Why the original error was missed

I incorrectly equated the URL slug "2026/06" with the user-identified W16 surge because in earlier (now-archived) pilot v2 work the analytical anchor was at W16 (when 57 cases peaked). I conflated the **outbreak surge week** with the **JIHS publication week** and never independently verified that the URL refers to issue number, not week number. The user spot-checked the timeline and surfaced the discrepancy.

**Lesson**: every JIHS Featured Article URL must have its publication week independently verified before being used as a "lead time vs. official notice" comparator. The URL slug uses sequential issue numbers (`/featured/2026/06/`, `/featured/2026/14/`, etc.) which approximately correspond to ISO weeks 6 and 14 respectively but should never be assumed without checking the article header.

## Recommended next action

1. Apply text corrections to `main_paper_draft_v1_1.docx` (5 spots: Abstract Results, §3.5, §4.1, §4.3, §5)
2. Update `measles_2026_live_demo.md` headline + lead-time table
3. Update `phase_b_decision_report_v3.md` if it cites "+11 weeks"
4. Add this correction notice to supplementary materials

I will execute (1)-(3) automatically in the next pass; (4) is documentation that lives at `outputs/measles_2026_alert_timeline_correction.md`.
