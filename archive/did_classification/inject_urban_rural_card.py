"""Insert card ⑦ Urban-Rural Distribution into the analysis-section of dashboard.html.

Target file: ~/Desktop/claude/dashboard.html
Insertion point: just before the line containing
    <!-- ==================== END ANALYSIS SECTION HTML ==================== -->

JS function: renderUrbanRural() — added near other render* functions; populates
disease + year dropdowns from DATA.nesid_pref_data, aggregates by
DATA.urban_tier[pref].urban_tier_did, renders bar chart + summary table.

Re-runnable: detects existing block via marker comments and replaces in place.
"""
import sys, re
from pathlib import Path

DASH = Path('/sessions/cool-clever-goldberg/mnt/claude/dashboard.html')
HTML_MARKER_START = '<!-- BEGIN URBAN-RURAL CARD ⑦ (auto-injected) -->'
HTML_MARKER_END   = '<!-- END URBAN-RURAL CARD ⑦ -->'
JS_MARKER_START   = '/* BEGIN URBAN-RURAL renderUrbanRural() (auto-injected) */'
JS_MARKER_END     = '/* END URBAN-RURAL renderUrbanRural() */'

NEW_HTML = '''<!-- BEGIN URBAN-RURAL CARD ⑦ (auto-injected) -->
<!-- ⑦ Urban-Rural Distribution -->
<div class="card" style="margin-bottom:18px">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:10px">
    <div>
      <div class="card-title">⑦ 都市・地方分布分析（Urban-Rural Distribution）</div>
      <div class="card-sub">DID人口比率3階層 × 都道府県別NESID年報 · 発病率比較</div>
    </div>
    <span style="font-size:10px;padding:3px 8px;border-radius:10px;background:rgba(63,129,148,0.15);color:#3F8194;border:1px solid rgba(63,129,148,0.3)">DID 2020 Census</span>
  </div>
  <div style="font-size:11px;color:var(--text2);background:var(--bg3);border-radius:6px;padding:10px 12px;margin-bottom:12px;line-height:1.7">
    <strong style="color:var(--text)">手法：</strong>2020年国勢調査の<strong style="color:#B8860B">人口集中地区（DID）人口比率</strong>に基づき、47都道府県を3階層に分類します：
    <strong style="color:#3F8194">high_urban</strong>（DID≥70%、10県）／<strong style="color:#5C8A4F">mixed</strong>（40〜70%、27県）／<strong style="color:#9C7FCF">rural_leaning</strong>（&lt;40%、10県）。
    各階層内の都道府県のNESID年報データを集計し、報告数・人口・人口10万人当たり発病率を計算して都市型／地方型の疾患動態を可視化します。
    出典: 統計でみる都道府県のすがた2024（統計コード00200502, 指標A01401）/ NESID年報（都道府県別）。
  </div>
  <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px">
    <div>
      <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:3px">疾患</label>
      <select id="urbanDisease" onchange="renderUrbanRural()"
        style="padding:4px 8px;border-radius:5px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:12px;min-width:200px"></select>
    </div>
    <div>
      <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:3px">対象年</label>
      <select id="urbanYear" onchange="renderUrbanRural()"
        style="padding:4px 8px;border-radius:5px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:12px"></select>
    </div>
    <div>
      <label style="font-size:11px;color:var(--text2);display:block;margin-bottom:3px">指標</label>
      <select id="urbanMetric" onchange="renderUrbanRural()"
        style="padding:4px 8px;border-radius:5px;border:1px solid var(--border);background:var(--bg3);color:var(--text);font-size:12px">
        <option value="rate" selected>発病率（人口10万人当たり）</option>
        <option value="cases">報告数（実数）</option>
      </select>
    </div>
  </div>
  <div style="display:flex;gap:14px;flex-wrap:wrap">
    <div style="flex:2;min-width:280px">
      <canvas id="urbanRuralChart" height="180"></canvas>
    </div>
    <div style="flex:1;min-width:220px;font-size:11px;color:var(--text2)">
      <div id="urbanRuralStats" style="line-height:1.7"></div>
    </div>
  </div>
  <div id="urbanRuralTable" style="margin-top:12px;font-size:11px"></div>
</div>
<!-- END URBAN-RURAL CARD ⑦ -->'''

NEW_JS = '''/* BEGIN URBAN-RURAL renderUrbanRural() (auto-injected) */
var _urbanRuralChart = null;
function _populateUrbanSelectors() {
  if (!DATA.urban_tier || !DATA.nesid_pref_data) return;
  var dSel = document.getElementById('urbanDisease');
  var ySel = document.getElementById('urbanYear');
  if (!dSel || !ySel) return;
  if (dSel.options.length > 0) return; // already populated
  var diseases = Object.keys(DATA.nesid_pref_data).sort();
  diseases.forEach(function(d) {
    var opt = document.createElement('option');
    opt.value = d; opt.textContent = d;
    dSel.appendChild(opt);
  });
  // pick a sensible default
  ['結核','梅毒','麻しん','後天性免疫不全症候群','百日咳'].forEach(function(d) {
    if (diseases.indexOf(d) >= 0 && !dSel._defaultPicked) { dSel.value = d; dSel._defaultPicked = true; }
  });
  // years: union across diseases
  var years = new Set();
  Object.values(DATA.nesid_pref_data).forEach(function(byYear) {
    Object.keys(byYear || {}).forEach(function(y) { years.add(parseInt(y, 10)); });
  });
  Array.from(years).sort(function(a,b){return b-a;}).forEach(function(y) {
    var opt = document.createElement('option');
    opt.value = y; opt.textContent = y + '年';
    ySel.appendChild(opt);
  });
}
function renderUrbanRural() {
  _populateUrbanSelectors();
  if (!DATA.urban_tier || !DATA.nesid_pref_data) {
    var st = document.getElementById('urbanRuralStats');
    if (st) st.innerHTML = '<span style="color:#D85563">データ未ロード</span>';
    return;
  }
  var disease = document.getElementById('urbanDisease').value;
  var year = parseInt(document.getElementById('urbanYear').value, 10);
  var metric = document.getElementById('urbanMetric').value;
  var byYear = DATA.nesid_pref_data[disease];
  var ydata = byYear ? byYear[year] : null;
  if (!ydata) {
    var st2 = document.getElementById('urbanRuralStats');
    if (st2) st2.innerHTML = '<span style="color:#D85563">該当データなし</span>';
    if (_urbanRuralChart) { _urbanRuralChart.destroy(); _urbanRuralChart = null; }
    return;
  }
  // Aggregate by tier
  var tiers = ['high_urban','mixed','rural_leaning'];
  var agg = {};
  tiers.forEach(function(t) { agg[t] = {cases: 0, pop_k: 0, prefs: []}; });
  Object.keys(ydata).forEach(function(pref) {
    if (pref === '総数' || pref === '全国') return;
    var info = ydata[pref];
    if (!info) return;
    var ut = DATA.urban_tier[pref];
    if (!ut) return;
    var t = ut.urban_tier_did;
    if (!agg[t]) return;
    agg[t].cases += (info.cases || 0);
    agg[t].pop_k += (info.pop_k || 0);
    agg[t].prefs.push(pref);
  });
  tiers.forEach(function(t) {
    agg[t].rate_100k = agg[t].pop_k > 0 ? (agg[t].cases / (agg[t].pop_k * 1000)) * 1e5 : 0;
  });
  // Bar chart
  var canvas = document.getElementById('urbanRuralChart');
  if (canvas && typeof Chart !== 'undefined') {
    if (_urbanRuralChart) _urbanRuralChart.destroy();
    var labels = ['high_urban (DID≥70%)', 'mixed (40-70%)', 'rural_leaning (<40%)'];
    var values = tiers.map(function(t) { return metric === 'rate' ? agg[t].rate_100k : agg[t].cases; });
    var colors = ['#3F8194', '#5C8A4F', '#9C7FCF'];
    var unit = metric === 'rate' ? '/10万人' : '件';
    _urbanRuralChart = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: { labels: labels, datasets: [{ label: disease + ' ' + year + '年', data: values, backgroundColor: colors, borderColor: colors, borderWidth: 1 }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: function(ctx) {
            var t = tiers[ctx.dataIndex];
            return ctx.parsed.y.toFixed(metric === 'rate' ? 2 : 0) + ' ' + unit
                 + '   (' + agg[t].prefs.length + ' 県)';
          }}}
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: metric === 'rate' ? '発病率（10万人当たり）' : '報告数（件）', font:{size:11} } },
          x: { ticks: { font:{size:11} } }
        }
      }
    });
  }
  // Stats panel
  var stats = document.getElementById('urbanRuralStats');
  if (stats) {
    var lines = ['<strong>' + disease + ' / ' + year + '年</strong><br>'];
    tiers.forEach(function(t) {
      var color = t==='high_urban'?'#3F8194':(t==='mixed'?'#5C8A4F':'#9C7FCF');
      lines.push('<div style="margin-top:6px"><span style="color:'+color+';font-weight:700">'+t+'</span>: '
                +agg[t].cases.toLocaleString()+' 件 / '
                +(agg[t].pop_k*1000).toLocaleString()+' 人<br>'
                +'<span style="font-size:10px;color:var(--text2)">' + agg[t].prefs.length + ' 県</span> '
                +'<span style="float:right;font-weight:700">' + agg[t].rate_100k.toFixed(2) + '/10万人</span></div>');
    });
    // Ratio high_urban vs rural_leaning
    if (agg.rural_leaning.rate_100k > 0) {
      var ratio = agg.high_urban.rate_100k / agg.rural_leaning.rate_100k;
      lines.push('<hr style="opacity:0.3;margin:8px 0">');
      lines.push('<div>都市/地方比 (rate): <strong>' + ratio.toFixed(2) + '×</strong></div>');
    }
    stats.innerHTML = lines.join('');
  }
  // Detail table — list prefectures per tier with their individual rates
  var tbl = document.getElementById('urbanRuralTable');
  if (tbl) {
    var rows = ['<table style="width:100%;border-collapse:collapse"><thead><tr style="border-bottom:1px solid var(--border)"><th style="text-align:left;padding:4px 6px">階層</th><th style="text-align:left;padding:4px 6px">都道府県（DID%）</th><th style="text-align:right;padding:4px 6px">合計件数</th><th style="text-align:right;padding:4px 6px">合計人口</th><th style="text-align:right;padding:4px 6px">発病率/10万人</th></tr></thead><tbody>'];
    tiers.forEach(function(t) {
      var color = t==='high_urban'?'#3F8194':(t==='mixed'?'#5C8A4F':'#9C7FCF');
      var prefList = agg[t].prefs.map(function(p) {
        var pct = (DATA.urban_tier[p] && DATA.urban_tier[p].did_population_ratio) || 0;
        return p + '<span style="color:var(--text2);font-size:10px">(' + pct.toFixed(0) + ')</span>';
      }).join('・');
      rows.push('<tr style="border-bottom:1px solid var(--border)"><td style="padding:4px 6px;color:'+color+';font-weight:700;vertical-align:top">'+t+'</td><td style="padding:4px 6px;font-size:10px;line-height:1.6">'+prefList+'</td><td style="text-align:right;padding:4px 6px">'+agg[t].cases.toLocaleString()+'</td><td style="text-align:right;padding:4px 6px">'+(agg[t].pop_k*1000).toLocaleString()+'</td><td style="text-align:right;padding:4px 6px;font-weight:700">'+agg[t].rate_100k.toFixed(2)+'</td></tr>');
    });
    rows.push('</tbody></table>');
    tbl.innerHTML = rows.join('');
  }
}
/* END URBAN-RURAL renderUrbanRural() */'''

# ── Insert HTML before </analysis-section> end marker ──────────────────────
def main():
    html = DASH.read_text(encoding='utf-8')
    orig_size = len(html)

    # ── HTML: insert before END ANALYSIS SECTION HTML comment ──────────────
    html_marker = '<!-- ==================== END ANALYSIS SECTION HTML ==================== -->'
    if HTML_MARKER_START in html and HTML_MARKER_END in html:
        # replace existing block in place
        i0 = html.index(HTML_MARKER_START)
        i1 = html.index(HTML_MARKER_END) + len(HTML_MARKER_END)
        html = html[:i0] + NEW_HTML + html[i1:]
        print(f'HTML block REPLACED in place ({i1-i0} → {len(NEW_HTML)} chars)')
    elif html_marker in html:
        i = html.index(html_marker)
        html = html[:i] + NEW_HTML + '\n\n' + html[i:]
        print(f'HTML block INSERTED before END ANALYSIS marker (position {i})')
    else:
        sys.exit('Could not locate END ANALYSIS SECTION HTML marker — abort.')

    # ── JS: insert before the first invocation site's closing </script> ───
    # We'll insert the renderUrbanRural() definition inside the existing analysis JS block.
    # Strategy: add as a sibling to renderEARS / renderSeason.
    # Anchor: 'function renderEARS' — insert NEW_JS just before it.
    if JS_MARKER_START in html and JS_MARKER_END in html:
        i0 = html.index(JS_MARKER_START)
        i1 = html.index(JS_MARKER_END) + len(JS_MARKER_END)
        html = html[:i0] + NEW_JS + html[i1:]
        print(f'JS block REPLACED in place')
    else:
        anchor = 'function renderEARS'
        if anchor not in html:
            sys.exit(f'Could not locate JS anchor "{anchor}" — abort.')
        i = html.index(anchor)
        html = html[:i] + NEW_JS + '\n\n' + html[i:]
        print(f'JS block INSERTED before "{anchor}" (position {i})')

    # ── Wire renderUrbanRural() into setMode('analysis') if not yet ────────
    # Find setMode('analysis') and ensure renderUrbanRural() is called when active.
    # The simplest hook: append a call near where renderEARS() is invoked from setMode.
    # We won't hard-modify setMode; instead, we ensure renderUrbanRural runs whenever
    # mode === 'analysis' by adding a small dispatcher in setMode if not present.
    setmode_anchor = "if (mode === 'analysis')"
    if 'renderUrbanRural()' not in html:
        # Hook: after renderEARS() call inside setMode or similar; safer approach:
        # add an event hook that runs renderUrbanRural when btn-analysis is clicked.
        # Actually the simplest: add renderUrbanRural() call right after JS block defines it.
        # We insert a one-liner that runs on btn-analysis click.
        wire = '''
/* URBAN-RURAL: auto-render when analysis tab opens */
(function(){
  var btn = document.getElementById('btn-analysis');
  if (btn && !btn._urbanWired) {
    btn._urbanWired = true;
    btn.addEventListener('click', function(){ try { renderUrbanRural(); } catch(e) {} });
  }
  // Also render on initial page load if analysis is already active
  document.addEventListener('DOMContentLoaded', function(){
    var sec = document.getElementById('analysis-section');
    if (sec && sec.style.display !== 'none') { try { renderUrbanRural(); } catch(e) {} }
  });
})();'''
        html = html.replace(JS_MARKER_END, JS_MARKER_END + wire)
        print('Auto-render hook on btn-analysis click added')

    DASH.write_text(html, encoding='utf-8')
    print(f'Original size: {orig_size:,} bytes')
    print(f'New size:      {len(html):,} bytes')
    print(f'Delta:         +{len(html) - orig_size:,} bytes')

if __name__ == '__main__':
    main()
