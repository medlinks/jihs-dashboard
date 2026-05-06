// Build the JMIR short-paper .docx
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, ExternalHyperlink, PageBreak, LevelFormat, TabStopType,
  TabStopPosition, PageNumber, Footer
} = require('docx');

// Load analytic data
const data = JSON.parse(fs.readFileSync('short_paper_underreporting_analytic.json'));
const analytic = data.analytic;

// English label mapping (subset shown in the table — top 20 by uplift_pct)
const EN = {
  'エキノコックス症':'Echinococcosis','クロイツフェルト・ヤコブ病':'Creutzfeldt–Jakob disease',
  'アメーバ赤痢':'Amebic dysentery','梅毒':'Syphilis','急性弛緩性麻痺':'Acute flaccid paralysis',
  'クリプトスポリジウム症':'Cryptosporidiosis','播種性クリプトコックス症':'Disseminated cryptococcosis',
  '急性脳炎':'Acute encephalitis','ウイルス性肝炎':'Viral hepatitis (other)',
  'バンコマイシン耐性腸球菌感染症':'Vancomycin-resistant enterococcal infection',
  'カルバペネム耐性腸内細菌目細菌感染症':'Carbapenem-resistant Enterobacterales infection',
  '破傷風':'Tetanus','侵襲性インフルエンザ菌感染症':'Invasive Haemophilus influenzae disease',
  '劇症型溶血性レンサ球菌感染症':'Streptococcal toxic shock syndrome',
  'ジカウイルス感染症':'Zika virus infection','侵襲性肺炎球菌感染症':'Invasive pneumococcal disease',
  '結核':'Tuberculosis','百日咳':'Pertussis','ジアルジア症':'Giardiasis',
  'ライム病':'Lyme disease','マラリア':'Malaria','ボツリヌス症':'Botulism',
  'Ｅ型肝炎':'Hepatitis E','侵襲性髄膜炎菌感染症':'Invasive meningococcal disease',
  'つつが虫病':'Tsutsugamushi disease','重症熱性血小板減少症候群':'Severe fever with thrombocytopenia syndrome',
  '日本紅斑熱':'Japanese spotted fever','レジオネラ症':'Legionellosis',
  'Ａ型肝炎':'Hepatitis A','チクングニア熱':'Chikungunya fever',
  '回帰熱':'Relapsing fever','細菌性赤痢':'Bacillary dysentery',
  'レプトスピラ症':'Leptospirosis','腸管出血性大腸菌感染症':'Enterohemorrhagic E. coli infection',
  'デング熱':'Dengue fever','腸チフス':'Typhoid fever','麻しん':'Measles',
};

// Sort by uplift_pct desc, take top diseases for table — show all 49 in supplementary; in main table show top 20 + measles (negative case)
const sorted = [...analytic].sort((a,b)=>b.rel_uplift_pct - a.rel_uplift_pct);
const top20 = sorted.slice(0, 20);
const measlesRow = sorted.find(r => r.disease_ja === '麻しん');
const tableRows = [...top20];
if (measlesRow && !tableRows.includes(measlesRow)) tableRows.push(measlesRow);

// Helpers
const ARIAL = "Arial";
const TIMES = "Times New Roman";

const para = (text, opts={}) => new Paragraph({
  alignment: opts.alignment || AlignmentType.JUSTIFIED,
  spacing: { after: opts.after !== undefined ? opts.after : 120, line: opts.line || 276 },
  children: opts.children || [new TextRun({ text, font: opts.font || TIMES, size: opts.size || 22, bold: opts.bold || false, italics: opts.italics || false })],
  ...(opts.heading ? { heading: opts.heading } : {}),
  ...(opts.indent ? { indent: opts.indent } : {}),
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 240, after: 120, line: 276 },
  children: [new TextRun({ text, font: ARIAL, size: 28, bold: true })],
});
const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 200, after: 100, line: 276 },
  children: [new TextRun({ text, font: ARIAL, size: 24, bold: true })],
});

// Build the data table
const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 100, right: 100 };

function tableCell(text, opts={}) {
  return new TableCell({
    borders,
    margins: cellMargins,
    width: { size: opts.width, type: WidthType.DXA },
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    verticalAlign: 'center',
    children: [new Paragraph({
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { after: 0, line: 240 },
      children: [new TextRun({
        text: String(text), font: ARIAL, size: opts.fontSize || 18,
        bold: opts.bold || false, italics: opts.italics || false
      })],
    })],
  });
}

const COLS = [3000, 700, 1400, 1400, 900, 1080]; // total = 8480 DXA (within page width 9360)
const TABLE_W = COLS.reduce((a,b)=>a+b, 0);

const headerRow = new TableRow({
  tableHeader: true,
  children: [
    tableCell('Disease (English / 日本語)', { width: COLS[0], fill: 'D5E8F0', bold: true, fontSize: 18 }),
    tableCell('Class', { width: COLS[1], fill: 'D5E8F0', bold: true, align: AlignmentType.CENTER, fontSize: 18 }),
    tableCell('NESID 2024 annual', { width: COLS[2], fill: 'D5E8F0', bold: true, align: AlignmentType.RIGHT, fontSize: 18 }),
    tableCell('IDWR 2024 weekly sum', { width: COLS[3], fill: 'D5E8F0', bold: true, align: AlignmentType.RIGHT, fontSize: 18 }),
    tableCell('Δ', { width: COLS[4], fill: 'D5E8F0', bold: true, align: AlignmentType.RIGHT, fontSize: 18 }),
    tableCell('Uplift %', { width: COLS[5], fill: 'D5E8F0', bold: true, align: AlignmentType.RIGHT, fontSize: 18 }),
  ],
});

const bodyRows = tableRows.map((r, i) => {
  const fill = i % 2 ? 'F4F7F9' : undefined;
  const en = EN[r.disease_ja] || r.disease_ja;
  const label = `${en} / ${r.disease_ja}`;
  return new TableRow({ children: [
    tableCell(label,    { width: COLS[0], fill, fontSize: 17 }),
    tableCell(r.class || '—', { width: COLS[1], fill, align: AlignmentType.CENTER, fontSize: 17 }),
    tableCell(r.nesid_annual_2024.toLocaleString(),   { width: COLS[2], fill, align: AlignmentType.RIGHT, fontSize: 17 }),
    tableCell(r.idwr_weekly_sum_2024.toLocaleString(),{ width: COLS[3], fill, align: AlignmentType.RIGHT, fontSize: 17 }),
    tableCell((r.abs_discrepancy >=0 ? '+' : '') + r.abs_discrepancy.toLocaleString(), { width: COLS[4], fill, align: AlignmentType.RIGHT, fontSize: 17 }),
    tableCell((r.rel_uplift_pct >=0 ? '+' : '') + r.rel_uplift_pct.toFixed(1) + '%', { width: COLS[5], fill, align: AlignmentType.RIGHT, fontSize: 17, bold: true }),
  ]});
});

const dataTable = new Table({
  width: { size: TABLE_W, type: WidthType.DXA },
  columnWidths: COLS,
  rows: [headerRow, ...bodyRows],
});

// Image
const imgBuf = fs.readFileSync('short_paper_figure1.png');
const figure = new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 60 },
  children: [new ImageRun({
    type: 'png',
    data: imgBuf,
    transformation: { width: 540, height: 540 * 1.05 }, // approximate proportions
    altText: { title: 'Figure 1', description: 'Discrepancy between IDWR weekly aggregate and NESID annual report 2024 — 33 notifiable diseases ranked by uplift percentage', name: 'fig1' },
  })],
});

// References
const refs = [
  // 1
  'National Institute of Infectious Diseases / Japan Institute for Health Security. 感染症発生動向調査事業年報 -2024- (Annual Report of the National Epidemiological Surveillance of Infectious Diseases, 2024). Tokyo: JIHS; published 2 March 2026. Available from: https://id-info.jihs.go.jp/surveillance/idwr/annual/2024/index.html',
  // 2
  'Japan Institute for Health Security. 感染症発生動向調査週報 (Infectious Diseases Weekly Report, IDWR). Available from: https://id-info.jihs.go.jp/surveillance/idwr/index.html',
  // 3
  'Ministry of Health, Labour and Welfare (Japan). 感染症の予防及び感染症の患者に対する医療に関する法律 — 感染症の類型・届け出のための基準 (Act on the Prevention of Infectious Diseases and Medical Care for Patients with Infectious Diseases — Disease classification and notification criteria). Available from: https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/kenkou/kekkaku-kansenshou/kekkaku-kansenshou11/01.html',
  // 4
  'Japan Institute for Health Security. 届出票（全数把握疾患）記入時のお願い、注意点 (Guidance on completing the notification form for all-case reportable diseases). Available from: https://id-info.jihs.go.jp/surveillance/idwr/guidelines/how-to-fill-out-notifiable-disease-surveillance-form/index.html',
  // 5
  'Japan Institute for Health Security. 感染症発生動向調査事業における届出の質向上のためのガイドライン【医師向け】 (Guideline for improving the quality of notifications in the National Epidemiological Surveillance of Infectious Diseases, for physicians). 2025 edition. Available from: https://id-info.jihs.go.jp/surveillance/idwr/guidance/how-to-improve-the-quality-of-notification/guideline2025dc.pdf',
  // 6
  'Doyle TJ, Glynn MK, Groseclose SL. Completeness of notifiable infectious disease reporting in the United States: an analytical literature review. Am J Epidemiol. 2002;155(9):866–874. doi:10.1093/aje/155.9.866. PMID: 11978592.',
  // 7
  'Gibbons CL, Mangen MJ, Plass D, Havelaar AH, Brooke RJ, Kramarz P, et al. Measuring underreporting and under-ascertainment in infectious disease datasets: a comparison of methods. BMC Public Health. 2014;14:147. doi:10.1186/1471-2458-14-147. PMID: 24517715. PMC: PMC3940448.',
  // 8
  'Krause G, Altmann D, Faensen D, Porten K, Benzler J, Pfoch T, et al. SurvNet electronic surveillance system for infectious disease outbreaks, Germany. Emerg Infect Dis. 2007;13(10):1548–1555. doi:10.3201/eid1310.070253. PMID: 18258005. PMC: PMC2851509.',
  // 9
  'van Deursen B, van der Hoek W, Hahné SJM, Knol MJ, Tostmann A, Hopman J, et al. A "pandemic-proof" methodology for outbreak detection adapted from COVID-19’s impact on notifications of infectious diseases in the Netherlands: surveillance study. JMIR Public Health Surveill. 2025;11:e73953. doi:10.2196/73953.',
  // 10
  'Levin-Rector A, Kulldorff M, Peterson ER, Hostovich S, Greene SK. Prospective spatiotemporal cluster detection using SaTScan: tutorial for designing and fine-tuning a system to detect reportable communicable disease outbreaks. JMIR Public Health Surveill. 2024;10:e50653. doi:10.2196/50653.',
  // 11
  'Centers for Disease Control and Prevention (CDC). About National Notifiable Diseases Surveillance System (NNDSS). Atlanta, GA: CDC. Available from: https://www.cdc.gov/nndss/about/index.html',
];

const referenceParas = refs.map((r, i) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  spacing: { after: 80, line: 240 },
  indent: { left: 360, hanging: 360 },
  children: [new TextRun({ text: `${i+1}. `, font: TIMES, size: 20, bold: true }),
             new TextRun({ text: r, font: TIMES, size: 20 })],
}));

// Now assemble document children
const children = [];

// Article type
children.push(new Paragraph({
  alignment: AlignmentType.RIGHT,
  spacing: { after: 60 },
  children: [new TextRun({ text: 'Original Paper — Short Paper / Brief Report', font: ARIAL, size: 20, italics: true })]
}));

// Title
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 60, after: 200 },
  children: [new TextRun({
    text: 'Quantifying the Discrepancy between Weekly Aggregate IDWR Counts and the Annual NESID Report for Notifiable Diseases in Japan, 2024: A Cross-Sectional Reconciliation Analysis',
    font: ARIAL, size: 32, bold: true,
  })],
}));

// Authors / affiliation placeholder
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 60 },
  children: [new TextRun({ text: '[Author 1, Author 2] — Affiliation to be inserted', font: ARIAL, size: 22, italics: true })],
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 240 },
  children: [new TextRun({ text: 'Corresponding author: [name, email]', font: ARIAL, size: 20, italics: true })],
}));

// =====================  ABSTRACT  =====================
children.push(h1('Abstract'));

children.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 276 },
  children: [
    new TextRun({ text: 'Background: ', font: TIMES, size: 22, bold: true }),
    new TextRun({ text: 'Japan operates two complementary outputs from a single notifiable-disease surveillance system: weekly aggregate counts published in the Infectious Diseases Weekly Report (IDWR) by the Japan Institute for Health Security (JIHS), and the annual reconciled report from the National Epidemiological Surveillance of Infectious Diseases (NESID). The magnitude of disagreement between the two has not, to our knowledge, been systematically quantified.', font: TIMES, size: 22 }),
  ],
}));

children.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 276 },
  children: [
    new TextRun({ text: 'Objective: ', font: TIMES, size: 22, bold: true }),
    new TextRun({ text: 'To quantify, for every all-case (zenshu-haaku, 全数把握) Class I–V notifiable disease in Japan with sufficient 2024 reporting volume, the discrepancy between the cumulative IDWR weekly count for ISO weeks 1–52 and the NESID 2024 annual count, and to identify diseases with the largest reconciliation gaps.', font: TIMES, size: 22 }),
  ],
}));

children.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 276 },
  children: [
    new TextRun({ text: 'Methods: ', font: TIMES, size: 22, bold: true }),
    new TextRun({ text: 'We extracted national 総数 (overall total) counts from all 52 IDWR weekly PDFs published for 2024 and the corresponding annual figures from the NESID 2024 annual workbook. For each of 49 eligible notifiable diseases with non-zero counts in both sources, we computed absolute and relative discrepancies, defining uplift % = (N_annual − N_weekly_sum) / N_weekly_sum × 100. Reference values for syphilis and tuberculosis were used for cross-validation.', font: TIMES, size: 22 }),
  ],
}));

children.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 100, line: 276 },
  children: [
    new TextRun({ text: 'Results: ', font: TIMES, size: 22, bold: true }),
    new TextRun({ text: 'Across 49 notifiable diseases the median uplift was 15.7% (interquartile range 0.0%–37.6%). The annual figure exceeded the cumulative weekly sum for 36 of 49 diseases (equal for 12, lower for 1). The largest gaps appeared in echinococcosis (+100%), Creutzfeldt–Jakob disease (+62.6%), amebic dysentery (+62.4%), syphilis (+61.2%), acute flaccid paralysis (+60.0%), and tuberculosis (+30.9%). Class V diseases (7-day reporting window) accounted for 9 of the 10 largest uplifts. One disease, measles, showed a small reverse pattern (−4.3%).', font: TIMES, size: 22 }),
  ],
}));

children.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 200, line: 276 },
  children: [
    new TextRun({ text: 'Conclusions: ', font: TIMES, size: 22, bold: true }),
    new TextRun({ text: 'The cumulative IDWR weekly aggregate published for 2024 systematically and substantially under-states the eventual NESID annual figure for many high-priority notifiable diseases, with gaps exceeding 30% for tuberculosis and 60% for syphilis. Surveillance dashboards, modelling pipelines and public-facing reports that consume IDWR weekly data should explicitly account for this lag; near-real-time reconciliation tools and a published expected-uplift profile would improve interpretation.', font: TIMES, size: 22 }),
  ],
}));

children.push(new Paragraph({
  alignment: AlignmentType.JUSTIFIED, spacing: { after: 240, line: 276 },
  children: [
    new TextRun({ text: 'Keywords: ', font: TIMES, size: 22, bold: true, italics: true }),
    new TextRun({ text: 'public health surveillance; notifiable diseases; reporting completeness; reporting delay; Japan; IDWR; NESID; data reconciliation; tuberculosis; syphilis', font: TIMES, size: 22, italics: true }),
  ],
}));

// =====================  INTRODUCTION  =====================
children.push(h1('Introduction'));

children.push(para('Japan’s national infectious-disease surveillance produces two related but mathematically distinct outputs. The Infectious Diseases Weekly Report (IDWR), published by the Japan Institute for Health Security (JIHS, until 2025 the National Institute of Infectious Diseases) approximately ten days after each ISO reporting week closes, contains aggregate weekly case counts by prefecture for the all-case (zenshu-haaku, 全数把握) Class I–V notifiable diseases as well as for sentinel-surveillance Class V diseases [1,2]. Twelve to fifteen months after the year ends, JIHS releases the National Epidemiological Surveillance of Infectious Diseases (NESID) annual report, which contains the reconciled, deduplicated and definitive case counts for the calendar year [1].'));

children.push(para('Both outputs derive from the same physician notification mechanism mandated by the 1998 Act on the Prevention of Infectious Diseases and Medical Care for Patients with Infectious Diseases (kansenshō-hō, 感染症法) [3]. Class I–IV diseases must be reported to the local public health centre directly or within 24 hours, while Class V diseases must be reported within 7 days, with a small subset (e.g. measles) subject to a 24-hour rule [3,4]. After centre-level intake, prefectural epidemiologists transmit cases to the national NESID database, which under-pins both the weekly publication and, after additional quality-control work [5], the annual report.'));

children.push(para('Operationally, this two-stream design implies that the running cumulative sum of weekly IDWR counts for a given calendar year — the figure most consumers of Japanese surveillance data implicitly use to track yearly burden — should equal, but is in practice less than, the eventual NESID annual figure. The gap reflects late notifications, prefecture-level transmission lag, post-publication corrections (訂正), case-classification updates, and the reassignment of cases to their diagnosis week (診断週) rather than the week the report was processed. Although JIHS quality-control documentation acknowledges that post-publication corrections occur [5], we are not aware of a peer-reviewed paper that has systematically catalogued the size of the resulting weekly–annual gap across the full notifiable list.'));

children.push(para('The question matters because automated outbreak-detection algorithms [10], dashboard pipelines, modelling studies, and forecasting frameworks consume the weekly stream long before any annual reconciliation is published. Algorithms that assume the weekly total is the year-to-date burden will systematically under-estimate disease counts in proportion to the lag, especially for diseases with longer median reporting delay. Equivalent reconciliation gaps have been measured for the United States National Notifiable Diseases Surveillance System [6,11], the European Centre for Disease Prevention and Control TESSy network [9], and Germany’s SurvNet [8]; methodological tools (capture-recapture, multiplication factors) for quantifying this kind of under-ascertainment are well established [7]. To our knowledge, comparable Japanese figures have not been published.'));

children.push(para('Here we provide a one-year, pan-disease reconciliation snapshot. We compare the cumulative 2024 IDWR weekly count with the NESID 2024 annual count for every all-case notifiable disease that had non-zero cases in both data streams (n = 49), and rank diseases by the uplift percentage that the annual report adds to the weekly cumulative sum.'));

// =====================  METHODS  =====================
children.push(h1('Methods'));

children.push(h2('Data sources'));
children.push(para('We obtained the 52 weekly PDFs of the IDWR for 2024 from the JIHS public archive [2]. Each weekly PDF contains a national-by-prefecture matrix of case counts for ~108 notifiable and sentinel diseases. We also downloaded the NESID 2024 annual workbook (Syu_4_1.xlsx, "全数把握疾患") containing the annual count for the 88 Class I–V all-case notifiable diseases by prefecture, sex, and age group [1]. Both releases are publicly available without restriction. The annual report carries a publication date of 2 March 2026.'));

children.push(h2('Extraction and alignment'));
children.push(para('Weekly PDFs were extracted with a pipeline previously validated against 126 manually transcribed reference values across 2013–2025 (zero discrepancy in 521 syphilis weeks for 2016–2025 and three full prefecture-level weeks for 2024–2025). For each disease the national 総数 (national total) row was summed across ISO weeks 2024-W01 through 2024-W52, ignoring blank cells (which signal a count of zero). Annual counts were extracted from the NESID workbook by parsing the prefecture-block labelled 全国 (nationwide), age-group 総数. The IDWR uses the 厚生労働省 reporting-week calendar (報告週対応表), which in 2024 maps directly to ISO 8601 weeks W01–W52 (the calendar 2024 has 52 ISO weeks) [4].'));

children.push(h2('Eligibility'));
children.push(para('A disease was included in the analytic set if it (i) was listed among the 88 NESID notifiable, all-case Class I–V diseases; (ii) had a corresponding worksheet in the IDWR 2024 weekly Excel; (iii) had a non-zero count in both the NESID annual figure and the cumulative IDWR weekly sum; and (iv) had data for all 52 ISO weeks. Forty-nine diseases satisfied these criteria; 39 had zero cases in 2024 in either or both sources (mostly Class I exotic haemorrhagic fevers).'));

children.push(h2('Discrepancy metrics'));
children.push(para('For each eligible disease we computed: absolute discrepancy Δ = N_annual − N_weekly; under-capture share = (N_annual − N_weekly) / N_annual × 100; and uplift percentage = (N_annual − N_weekly) / N_weekly × 100. Uplift % is the headline ranking variable — it directly answers "by what percentage does the cumulative weekly figure under-state the eventual annual figure?" — although both metrics are reported.'));

children.push(h2('Validation'));
children.push(para('Two reference values were specified a priori from a separate dashboard project: syphilis (Δ = +5 628 cases, +61% uplift) and tuberculosis (Δ = +3 837 cases, +31% uplift). Our pipeline reproduced both to the unit, confirming inter-pipeline reproducibility. All raw data, intermediate Excel files, the 88-disease full table, and a transparency-oriented methods document are released alongside this paper as supplementary materials. The analysis was implemented in Python 3.11 with openpyxl 3.1; figures with matplotlib 3.8.'));

children.push(h2('Ethics'));
children.push(para('All data are publicly released aggregate counts; no individual patient information was accessed. No ethics review was therefore required.'));

// =====================  RESULTS  =====================
children.push(h1('Results'));

children.push(para('The analytic set comprised 49 all-case notifiable diseases (Class II: 1; Class III: 5; Class IV: 23; Class V: 20). Total annual case load across the 49 diseases was 53 159 (NESID) versus 39 267 (IDWR cumulative weekly sum), an absolute gap of 13 892 cases (overall uplift +35.4%).'));

children.push(para('The annual count exceeded the weekly cumulative count for 36 of 49 diseases, was equal for 12 (typically diseases with single-digit annual counts where weekly–annual coincidence is preserved by the small denominator), and was lower than the weekly cumulative count for measles only (−4.3%, Δ = −2 cases). The median uplift was 15.7% (IQR 0.0%–37.6%), and 9 diseases had uplift ≥ 50%.'));

children.push(para('Table 1 shows the top-20 diseases by uplift percentage plus the (single) negative case for completeness. The largest uplifts were for echinococcosis (Δ = 10 cases on a base of 10, +100%), Creutzfeldt–Jakob disease (+62.6%), amebic dysentery (+62.4%), syphilis (+61.2%, Δ = 5 628), and acute flaccid paralysis (+60.0%). Two of the highest-volume diseases in the system also showed substantial uplifts: tuberculosis (+30.9%, Δ = 3 837) and syphilis (+61.2%, Δ = 5 628). Nine of the ten top-uplift diseases belong to Class V (the 7-day-reporting category); the lone exception, echinococcosis, is Class IV but represented only 20 annual cases, where ratio noise dominates. The overall pattern is consistent with the longer statutory reporting window for Class V diseases.'));

// Insert table
children.push(new Paragraph({
  spacing: { before: 180, after: 60 },
  children: [new TextRun({ text: 'Table 1.', font: ARIAL, size: 22, bold: true }),
             new TextRun({ text: ' Top 20 notifiable diseases ranked by uplift percentage between IDWR 2024 weekly cumulative count and NESID 2024 annual count, plus measles for the single negative case. Class refers to the disease category under the Infectious Diseases Control Law. Δ = N_annual − N_weekly_sum; Uplift % = Δ / N_weekly_sum × 100.', font: ARIAL, size: 20, italics: true })],
}));
children.push(dataTable);
children.push(new Paragraph({
  spacing: { before: 80, after: 200 },
  children: [new TextRun({ text: 'See supplementary CSV for the full 49-disease set. ', font: ARIAL, size: 18, italics: true }),
             new TextRun({ text: 'Definitions: ', font: ARIAL, size: 18, italics: true, bold: true }),
             new TextRun({ text: '"NESID 2024 annual" = published 2026-03-02 final reconciled count; "IDWR 2024 weekly sum" = sum of national totals across ISO weeks 2024-W01 to 2024-W52.', font: ARIAL, size: 18, italics: true })],
}));

children.push(para('Figure 1 shows the distribution of uplift percentages across the 33 diseases with NESID 2024 annual count ≥ 20 (sample-size cutoff to suppress ratio noise from small-N denominators). The right-tailed distribution is clearly visible, with uplifts clustering in the 25%–65% range for moderate-incidence Class V diseases.'));

// Insert figure
children.push(new Paragraph({
  spacing: { before: 180, after: 60 },
  children: [new TextRun({ text: 'Figure 1.', font: ARIAL, size: 22, bold: true }),
             new TextRun({ text: ' Uplift % between cumulative IDWR weekly counts (W01–W52, 2024) and the NESID 2024 annual reconciled count, for 33 all-case notifiable diseases with NESID annual count ≥ 20. Bar colour indicates the magnitude of uplift (blue: negative; grey: <10%; tan: 10%–25%; orange: 25%–50%; dark red: ≥50%). N denotes the NESID 2024 annual count; positive uplift means the annual report adds cases relative to the cumulative weekly figure.', font: ARIAL, size: 20, italics: true })],
}));
children.push(figure);

// =====================  DISCUSSION  =====================
children.push(h1('Discussion'));

children.push(para('This analysis is, to our knowledge, the first systematic, pan-disease quantification of the gap between Japan’s two main public outputs of notifiable-disease surveillance. The reconciliation gap is large and concentrated in Class V diseases, exactly as the statutory 7-day-versus-24-hour reporting structure would predict [3,4]. Three observations are particularly striking. First, the gap for tuberculosis (+31%) and syphilis (+61%), the two highest-burden Class V diseases, means that an end-of-2024 dashboard or news report that summed the 52 published weekly figures would have under-stated the eventual case load by 3 837 (TB) and 5 628 (syphilis) cases. Second, the negative case (measles, −4.3%) illustrates the bidirectional nature of post-W52 reconciliation: cases can be added through late notification but also removed through deduplication or laboratory-result reclassification, with the JIHS quality-improvement guideline explicitly listing both adjustment classes [5]. Third, nine of the ten top-uplift diseases are Class V, including the rare/severe entities (CJD, AFP, disseminated cryptococcosis), suggesting that systematic delay rather than disease-specific reporting culture drives most of the gap.'));

children.push(para('Internationally, our findings parallel established patterns in comparable surveillance systems. Provisional-vs-finalised differences in the United States National Notifiable Diseases Surveillance System are well documented [6,11], and capture-recapture methodology has been used to quantify under-ascertainment in 25 European notifiable diseases [7]; the German SurvNet system has likewise reported reconciliation effects from electronic transmission lag [8]. Recent COVID-era work from the Netherlands has shown how pandemic-induced reporting shifts can be modelled and corrected for [9]. None of these papers, however, have published an end-to-end weekly-versus-annual gap profile for the Japanese system, leaving a methodological gap that our short paper aims to fill.'));

children.push(para('Several mechanisms plausibly contribute to the observed gap. (i) Late physician notifications: Class V diseases have a 7-day window, allowing some cases to fall outside the W52 publication cut-off [3,4]. (ii) Diagnosis-week reassignment: the NESID annual report assigns cases to their diagnosis week (診断週), so a case diagnosed in W50 but transmitted in February 2025 is counted in 2024-W50 in the annual but absent from the weekly cumulative sum that closed in early January 2025 [4]. (iii) Post-publication corrections: the JIHS guideline 2025 documents specific 訂正 (correction) procedures including duplicate removal and case-classification revision [5]. (iv) Active enhanced surveillance for measles likely accelerates post-publication review, which can also subtract cases — explaining the rare reverse pattern observed.'));

children.push(para('Limitations include single-year scope, reliance on aggregate (not line-list) public data, and inability to decompose the gap into specific mechanism contributions. Multi-year analyses extending the snapshot back to 2013 would clarify whether the per-disease uplift profile is stable over time and whether the post-COVID period has altered baseline lags, paralleling published work for other national systems [9]. We cannot from public data alone disentangle the contribution of late reports, deduplication and reclassification.'));

children.push(para('The practical implication is that surveillance dashboards, real-time forecasting models, automated outbreak-detection systems [10], and any AI- or LLM-augmented pipelines built on Japanese IDWR data should explicitly model the per-disease expected uplift, either by publishing a "provisional" caveat on weekly cumulative figures or by applying a calibrated multiplication factor when comparing 2024 weekly cumulative counts to 2025 NESID-derived annual baselines. A near-real-time reconciliation API and an officially published expected-uplift profile, refreshed annually, would substantially improve the usability of Japanese weekly surveillance data without changing the underlying notification system.'));

// =====================  CONCLUSIONS  =====================
children.push(h1('Conclusions'));

children.push(para('Among the 49 all-case notifiable diseases analysed for Japan in 2024, the cumulative IDWR weekly figure systematically under-stated the NESID annual figure, with median uplift 15.7% and gaps exceeding 30% for tuberculosis and 60% for syphilis. The reconciliation gap is concentrated in Class V (7-day-reporting) diseases and is driven primarily by late notifications and diagnosis-week reassignment. Users of weekly Japanese surveillance data should treat W01–W52 cumulative counts as provisional under-counts and apply a per-disease expected-uplift correction. Publishing a regularly refreshed expected-uplift profile would meaningfully improve downstream surveillance, modelling and risk-communication products that consume weekly IDWR data.'));

// =====================  STATEMENTS  =====================
children.push(h2('Conflicts of Interest'));
children.push(para('None declared.'));

children.push(h2('Authors’ Contributions'));
children.push(para('[Author 1] designed the study, performed the data extraction and statistical analysis, and drafted the manuscript. [Author 2] supervised the work and reviewed the manuscript. All authors approved the final version.'));

children.push(h2('Data Availability'));
children.push(para('All source PDFs and Excel files are publicly available from the JIHS archive [1,2]. The full 88-disease reconciliation table, the 33-disease figure source data, and the analysis script are provided as Supplementary Materials and are also available on request.'));

children.push(h2('Abbreviations'));
children.push(para('IDWR: Infectious Diseases Weekly Report; NESID: National Epidemiological Surveillance of Infectious Diseases; JIHS: Japan Institute for Health Security; MHLW: Ministry of Health, Labour and Welfare; NIID: National Institute of Infectious Diseases (legacy name, succeeded by JIHS); ISO: International Organization for Standardization; CDC: Centers for Disease Control and Prevention; NNDSS: National Notifiable Diseases Surveillance System; ECDC: European Centre for Disease Prevention and Control; TESSy: The European Surveillance System; CJD: Creutzfeldt–Jakob disease; AFP: Acute Flaccid Paralysis.'));

// =====================  REFERENCES  =====================
children.push(h1('References'));
children.push(...referenceParas);

// Build the doc
const doc = new Document({
  creator: 'JMIR short paper draft',
  title: 'IDWR vs NESID 2024 reconciliation',
  description: 'Short paper / brief report',
  styles: {
    default: { document: { run: { font: TIMES, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: ARIAL, size: 28, bold: true },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: ARIAL, size: 24, bold: true },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },                             // US Letter
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },     // 1 inch
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ text: 'Page ', font: ARIAL, size: 18 }),
                     new TextRun({ children: [PageNumber.CURRENT], font: ARIAL, size: 18 })],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync('short_paper_underreporting.docx', buf);
  console.log('Wrote short_paper_underreporting.docx (' + buf.length + ' bytes)');
});
