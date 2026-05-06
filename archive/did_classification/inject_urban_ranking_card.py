"""Insert card ⑧ Urban-Rural Ratio Ranking into the analysis-section of dashboard.html.

Sits AFTER card ⑦ Urban-Rural Distribution (which is itself just before
'<!-- ==================== END ANALYSIS SECTION HTML ==================== -->').

Renders a horizontal-bar table sorted by urban/rural rate ratio, color-coded:
  ratio > 1.5 → urban-concentrated (青 #3F8194)
  0.7 ≤ ratio ≤ 1.5 → neutral (灰)
  ratio < 0.7 → rural-concentrated (紫 #9C7FCF)

Filters: minimum total cases threshold (default 50) to avoid noisy ratios on rare diseases.
Re-runnable: marker comments allow in-place replacement.
"""
import sys
from pathlib import Path

DASH = Path('/sessions/cool-clever-goldberg/mnt/claude/dashboard.html')
HTML_MARKER_START = '<!-- BEGIN URBAN-RANKING CARD ⑧ (auto-injected) -->'
HTML_MARKER_END   = '<!-- END URBAN-RANKING CARD ⑧ -->'
JS_MARKER_START   = '/* BEGIN URBAN-RANKING renderUrbanRanking() (auto-injected) */'
JS_MARKER_END     = '/* END URBAN-RANKING renderUrbanRanking() */'

NEW_HTML = '''<!-- BEGIN URBAN-RANKING CARD ⑧ (auto-injected) -->
<!-- ⑧ Urban-Rural Ratio Ranking -->
<div class="card" style="margin-bottom:18px">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <div>
      <div class="card-title">⑧ 都市/地方比 ランキング（Urban-Rural Ratio Ranking）</div>
      <div class="card-sub">全疾病横断 · 都市集中度ランキング · 都市/地方発病率比</div>
    </div>
    <span style="font-size:10px;padding:3px 8px;border-radius:10px;background:rgba(63,129,148,0.15);color:#3F8194;border:1px solid rgba(63,129,148,0.3)">All Diseases</span>
  </div>
  <div style="font-size:11px;color:var(--text2);background:var(--bg3);border-radius:6px;padding:10px 12px;margin-bottom:12px;line-height:1.7">
    <strong style="color:var(--text)">手法：</strong>NESID都道府県年報データを用いて、各疾病について<strong style="color:#3F8194">high_urban階層の発病率</strong>と<strong style="color:#9C7FCF">rural_leaning階層の発病率</strong>の比（Urban/Rural Ratio）を算出します。
    1.5×以上は都市集中型（性感染症・輸入性疾病など）、0.7×以下は地方集中型（マダニ媒介疾病・農作業関連など）、その間は地理的均一型に分類されます。
    各疾病の最新利用可能年を使用、合計件数 < <strong>50件</strong>の希少疾病はランキング除外（比率が不安定なため）。
  </div>
  <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px">
    <div>
      <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:3px">最低合計件数（カットオフ）</label>
      <select id="urbanRankMinCases" onchange="renderUrbanRanking()"
        style="padding:4px 8px;border-radius:5px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:12px">
        <option value="20">20件以上</option>
        <option value="50" selected>50件以上（推奨）</option>
        <option value="100">100件以上</option>
        <option value="500">500件以上</option>
      </select>
    </div>
    <div>
      <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:3px">並び順</label>
      <select id="urbanRankSort" onchange="renderUrbanRanking()"
        style="padding:4px 8px;border-radius:5px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:12px">
        <option value="urban_first" selected>都市集中型から順に</option>
        <option value="rural_first">地方集中型から順に</option>
      </select>
    </div>
  </div>
  <div id="urbanRankSummary" style="font-size:11px;color:var(--text2);margin-bottom:8px"></div>
  <div id="urbanRankTable" style="font-size:11px"></div>
</div>
<!-- END URBAN-RANKING CARD ⑧ -->'''

NEW_JS = '''/* BEGIN URBAN-RANKING renderUrbanRanking() (auto-injected) */
function _computeUrbanRanking(minCases) {
  if (!DATA.urban_tier || !DATA.nesid_pref_data) return [];
  var tierMap = {};
  Object.keys(DATA.urban_tier).forEach(function(p) {
    tierMap[p] = DATA.urban_tier[p].urban_tier_did;
  });
  var TIERS = ['high_urban','mixed','rural_leaning'];
  var rows = [];
  Object.keys(DATA.nesid_pref_data).forEach(function(disease) {
    var byYear = DATA.nesid_pref_data[disease];
    if (!byYear) return;
    var years = Object.keys(byYear).map(function(y){return parseInt(y,10);}).filter(function(y){return !isNaN(y);}).sort(function(a,b){return b-a;});
    if (!years.length) return;
    var latestYear = years[0];
    var ydata = byYear[latestYear];
    if (!ydata) return;
    var agg = {};
    TIERS.forEach(function(t){ agg[t] = {cases:0, pop_k:0}; });
    Object.keys(ydata).forEach(function(pref) {
      if (pref === '全国' || pref === '総数') return;
      var info = ydata[pref];
      if (!info) return;
      var t = tierMap[pref];
      if (!agg[t]) return;
      agg[t].cases += (info.cases || 0);
      agg[t].pop_k += (info.pop_k || 0);
    });
    var totalCases = agg.high_urban.cases + agg.mixed.cases + agg.rural_leaning.cases;
    if (totalCases < minCases) return;
    var rates = {};
    TIERS.forEach(function(t){ rates[t] = agg[t].pop_k > 0 ? (agg[t].cases / (agg[t].pop_k * 1000) * 1e5) : 0; });
    var ratio;
    if (rates.rural_leaning > 0) {
      ratio = rates.high_urban / rates.rural_leaning;
    } else if (rates.high_urban > 0) {
      ratio = Infinity;
    } else {
      ratio = null;
    }
    if (ratio === null) return;
    rows.push({
      disease: disease, year: latestYear, total_cases: totalCases,
      rate_high_urban: rates.high_urban, rate_mixed: rates.mixed, rate_rural: rates.rural_leaning,
      ratio: ratio
    });
  });
  return rows;
}
function renderUrbanRanking() {
  if (!DATA.urban_tier || !DATA.nesid_pref_data) {
    var s = document.getElementById('urbanRankSummary');
    if (s) s.innerHTML = '<span style="color:#D85563">データ未ロード</span>';
    return;
  }
  var minCases = parseInt(document.getElementById('urbanRankMinCases').value, 10);
  var sortMode = document.getElementById('urbanRankSort').value;
  var rows = _computeUrbanRanking(minCases);
  // sort: infinite first if urban_first, last if rural_first
  rows.sort(function(a, b) {
    var ar = a.ratio === Infinity ? 1e9 : a.ratio;
    var br = b.ratio === Infinity ? 1e9 : b.ratio;
    return sortMode === 'urban_first' ? (br - ar) : (ar - br);
  });
  var nUrban = rows.filter(function(r){return r.ratio === Infinity || r.ratio > 1.5;}).length;
  var nNeutral = rows.filter(function(r){return r.ratio !== Infinity && r.ratio >= 0.7 && r.ratio <= 1.5;}).length;
  var nRural = rows.filter(function(r){return r.ratio !== Infinity && r.ratio < 0.7;}).length;
  var sum = document.getElementById('urbanRankSummary');
  if (sum) {
    sum.innerHTML = '<strong>解析対象 ' + rows.length + ' 疾病</strong> （' + minCases + '件未満は除外）<br>'
      + '<span style="color:#3F8194;font-weight:700">都市集中型 (>1.5×)</span>: ' + nUrban + ' 疾病  ／  '
      + '<span style="color:var(--text2)">均一 (0.7-1.5×)</span>: ' + nNeutral + ' 疾病  ／  '
      + '<span style="color:#9C7FCF;font-weight:700">地方集中型 (<0.7×)</span>: ' + nRural + ' 疾病';
  }
  var tbl = document.getElementById('urbanRankTable');
  if (!tbl) return;
  // build horizontal-bar table
  var maxRatio = 4; // x-axis max for visualization (anything above shows as full bar with label)
  var html = ['<table style="width:100%;border-collapse:collapse">',
    '<thead><tr style="border-bottom:1px solid var(--border);font-size:10px;color:var(--text2)">',
    '<th style="text-align:left;padding:4px 6px">疾病</th>',
    '<th style="text-align:right;padding:4px 6px">最新年</th>',
    '<th style="text-align:right;padding:4px 6px">合計件数</th>',
    '<th style="text-align:right;padding:4px 6px">都市率</th>',
    '<th style="text-align:right;padding:4px 6px">中間</th>',
    '<th style="text-align:right;padding:4px 6px">地方率</th>',
    '<th style="text-align:left;padding:4px 6px;width:30%">都市/地方比 ←地方｜都市→</th>',
    '<th style="text-align:right;padding:4px 6px">比</th>',
    '</tr></thead><tbody>'];
  rows.forEach(function(r) {
    var color, badge;
    if (r.ratio === Infinity) { color = '#3F8194'; badge = '∞'; }
    else if (r.ratio > 1.5)   { color = '#3F8194'; badge = r.ratio.toFixed(2) + '×'; }
    else if (r.ratio < 0.7)   { color = '#9C7FCF'; badge = r.ratio.toFixed(2) + '×'; }
    else                       { color = 'var(--text2)'; badge = r.ratio.toFixed(2) + '×'; }
    // Bar: log-scale-ish around 1.0 → 50% center
    // map ratio to a 0..100% horizontal position. Center of axis = 1.0 (50%).
    // Use log scale: pos = 50 + 50 * log2(ratio)/log2(maxRatio)
    var pos;
    if (r.ratio === Infinity) pos = 100;
    else {
      var lg = Math.log(r.ratio) / Math.log(maxRatio);
      pos = Math.max(0, Math.min(100, 50 + 50 * lg));
    }
    var barHtml = '<div style="position:relative;height:14px;background:var(--bg3);border-radius:3px;overflow:hidden">'
      + '<div style="position:absolute;left:50%;top:0;bottom:0;width:1px;background:var(--border)"></div>';
    if (pos >= 50) {
      barHtml += '<div style="position:absolute;left:50%;top:0;bottom:0;width:' + (pos-50) + '%;background:'+color+';opacity:0.7"></div>';
    } else {
      barHtml += '<div style="position:absolute;left:'+pos+'%;top:0;bottom:0;width:' + (50-pos) + '%;background:'+color+';opacity:0.7"></div>';
    }
    barHtml += '</div>';
    html.push('<tr style="border-bottom:1px solid var(--border)">'
      + '<td style="padding:4px 6px;font-weight:700">'+r.disease+'</td>'
      + '<td style="text-align:right;padding:4px 6px;color:var(--text2)">'+r.year+'</td>'
      + '<td style="text-align:right;padding:4px 6px">'+r.total_cases.toLocaleString()+'</td>'
      + '<td style="text-align:right;padding:4px 6px;color:#3F8194">'+r.rate_high_urban.toFixed(2)+'</td>'
      + '<td style="text-align:right;padding:4px 6px;color:#5C8A4F">'+r.rate_mixed.toFixed(2)+'</td>'
      + '<td style="text-align:right;padding:4px 6px;color:#9C7FCF">'+r.rate_rural.toFixed(2)+'</td>'
      + '<td style="padding:4px 6px">'+barHtml+'</td>'
      + '<td style="text-align:right;padding:4px 6px;color:'+color+';font-weight:700">'+badge+'</td>'
      + '</tr>');
  });
  html.push('</tbody></table>');
  tbl.innerHTML = html.join('');
}
/* END URBAN-RANKING renderUrbanRanking() */'''

def main():
    html = DASH.read_text(encoding='utf-8')
    orig = len(html)

    # ── HTML: insert just BEFORE the END ANALYSIS marker, AFTER card ⑦ ────
    end_marker = '<!-- ==================== END ANALYSIS SECTION HTML ==================== -->'
    if HTML_MARKER_START in html and HTML_MARKER_END in html:
        i0 = html.index(HTML_MARKER_START)
        i1 = html.index(HTML_MARKER_END) + len(HTML_MARKER_END)
        html = html[:i0] + NEW_HTML + html[i1:]
        print('HTML block REPLACED in place')
    elif end_marker in html:
        i = html.index(end_marker)
        html = html[:i] + NEW_HTML + '\n\n' + html[i:]
        print(f'HTML block INSERTED before END ANALYSIS marker (position {i})')
    else:
        sys.exit('END ANALYSIS marker not found.')

    # ── JS: insert near other render functions; reuse anchor renderEARS ───
    if JS_MARKER_START in html and JS_MARKER_END in html:
        i0 = html.index(JS_MARKER_START)
        i1 = html.index(JS_MARKER_END) + len(JS_MARKER_END)
        html = html[:i0] + NEW_JS + html[i1:]
        print('JS block REPLACED in place')
    else:
        anchor = 'function renderEARS'
        if anchor not in html:
            sys.exit('JS anchor function renderEARS not found.')
        i = html.index(anchor)
        html = html[:i] + NEW_JS + '\n\n' + html[i:]
        print(f'JS block INSERTED before "{anchor}" (position {i})')

    # ── Wire renderUrbanRanking() to btn-analysis click ──────────────────
    wire = '''
/* URBAN-RANKING: auto-render when analysis tab opens */
(function(){
  var btn = document.getElementById('btn-analysis');
  if (btn && !btn._urbanRankWired) {
    btn._urbanRankWired = true;
    btn.addEventListener('click', function(){ try { renderUrbanRanking(); } catch(e) {} });
  }
  document.addEventListener('DOMContentLoaded', function(){
    var sec = document.getElementById('analysis-section');
    if (sec && sec.style.display !== 'none') { try { renderUrbanRanking(); } catch(e) {} }
  });
})();'''
    if 'btn._urbanRankWired' not in html:
        html = html.replace(JS_MARKER_END, JS_MARKER_END + wire)
        print('Auto-render hook added')

    DASH.write_text(html, encoding='utf-8')
    print(f'Original size: {orig:,} bytes')
    print(f'New size:      {len(html):,} bytes')
    print(f'Delta:         +{len(html) - orig:,} bytes')

if __name__ == '__main__':
    main()
