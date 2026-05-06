あなたはJIHS（国立感染症研究所）感染症サーベイランスダッシュボードの自動更新タスクです。以下の手順でデータを確認・更新してください。

## ステップ0: ダッシュボードのマウントパスを自動検出（必須・最初に必ず実行）

セッションごとに `/sessions/<random-name>/mnt/claude/` のパスは変化するため、毎回最初に動的に検出する。Bashで以下を実行し、`DASHBOARD_ROOT` を取得すること:

```bash
DASHBOARD_ROOT=$(find /sessions -maxdepth 4 -name "dashboard.html" 2>/dev/null | grep -v outputs | head -1 | xargs -r dirname)
echo "DASHBOARD_ROOT=$DASHBOARD_ROOT"
ls -la "$DASHBOARD_ROOT/state.json"
```

- 取得できなかった場合は `request_cowork_directory` ツールでユーザに作業フォルダ選択を促し、再検出する
- 以降のすべてのBashコマンドで `$DASHBOARD_ROOT` を使うこと（直接 `/sessions/...` を書かない）
- Read/Write/Edit ツールを使う場合は、env セクションに記載されている Mac/Windows パス（例: `/Users/.../Desktop/claude/...`）を使う

以降の各ステップでは:
- `{ROOT}` = `$DASHBOARD_ROOT`（Bash内）または env から導出した OS パス（Read/Write/Edit）
- `{year}` = 対象年度（通常は今年）
- `{week}` = ISO週番号

---

## ステップ1: 速報データの更新（毎週）

### 未処理週の確認:
1. `{ROOT}/state.json` を読んで `processed_weeks` リストを確認する
2. 現在のISO週番号を計算（Bashで `python3 -c "import datetime; print(datetime.date.today().isocalendar()[:2])"` を実行）
3. `processed_weeks` にない週があれば処理が必要

### 速報取得手順（Chrome ブラウザ使用）:
**注意**: `id-info.jihs.go.jp` はサンドボックスから直接アクセスできません（403エラー）。データ取得にはChrome ブラウザツール（mcp__Claude_in_Chrome）を使う必要があります。

1. Chrome ブラウザで `https://id-info.jihs.go.jp/surveillance/idwr/provisional/{year}/{week}/index.html` を開く
2. ページからCSVダウンロードリンクを探す（`zensu` を含むURL）
3. `https://id-info.jihs.go.jp/surveillance/idwr/provisional/{year}/{week}/data/zensu.csv` のCSVをJavaScriptで取得
4. CSVデータをパースし、各疾病・都道府県のデータを抽出
5. `{ROOT}/diseases/{disease_name}/{disease_name}.xlsx` の疾病Excelファイル「速報データ」シートに新週の行を追記
6. `{ROOT}/state.json` の `processed_weeks` に今週のキー（例: `"2026-W15"`）を追加して保存

**Chromeでのデータ転送方法**（セキュリティフィルター対策）:
- CSVの各行を `"都道府県名 数値1 数値2 ..."` のスペース区切り形式でJavaScriptから返す
- 一度に2行ずつ取得する（JavaScriptの出力が約1200文字に切り詰められるため）
- `{ROOT}/process_w{week}.py` スクリプトを動的生成して実行する

### ステップ1.5: 速報集計 → dashboard 反映（必須・毎回）

⚠️ **重要**: 速報データを xlsx に追記しただけでは dashboard には反映されない。
xlsx → speed_trends の集約と const DATA への再埋め込みを必ず実行する:

```bash
# diseases/*/*.xlsx の速報シートを集計して full_dashboard_data.json の speed_trends を更新
python3 "$DASHBOARD_ROOT/scripts/aggregate_speed.py"

# const DATA = {...} を新データで置き換える
python3 "$DASHBOARD_ROOT/update_pipeline.py" embed
```

新しい速報週が追加されていなくても毎回実行して問題ない（冪等）。

---

## ステップ2: 週報PDFの確認・処理（毎週）

1. 状態確認:
```bash
python3 "$DASHBOARD_ROOT/update_pipeline.py" report
```

2. 「週報更新必要: YES」が表示された場合:
   - Chrome ブラウザで `https://id-info.jihs.go.jp/surveillance/idwr/idwr/{year}/` を開く（注意: URLパスは `idwr/{year}/`）
   - 最新週のPDFリンクを探す（例: `idwr2026-15.pdf`）
   - PDFをダウンロードして `{ROOT}/{year}/idwr{year}-{week}.pdf` に保存
   - 抽出スクリプトを実行:
   ```bash
   python3 "$DASHBOARD_ROOT/scripts/extract_jihs_fixed.py" --year {year} --dir "$DASHBOARD_ROOT/{year}/"
   ```
   - JSONを再生成:
   ```bash
   python3 "$DASHBOARD_ROOT/scripts/extract_all_diseases.py"
   ```
   - ダッシュボードに再埋め込み:
   ```bash
   python3 "$DASHBOARD_ROOT/update_pipeline.py" embed
   ```

3. 週報PDFが未公開の場合は「更新不要（未公開）」として記録

---

## ステップ3: 年報データの確認（4〜6月頃）

`update_pipeline.py report` の出力で前年NESID未取得が示された場合（4〜6月のみ確認）:
1. Chrome ブラウザで `https://id-info.jihs.go.jp/surveillance/nesid/annual/{year}/syulist/Syu_04_1.xlsx` を試みる（`{year}` = 前年）
2. ファイルが存在すれば `{ROOT}/nesid_historical/{year}_Syu_04_1.xlsx` として保存
3. 保存後、`extract_nesid_age.py` スクリプトを再実行して年齢データを更新
4. 404の場合は「年報未公開」として記録

---

## ステップ4: JIHSニュース更新 + 古いニュース削除

### 4a: 新着ニュースをALERTSに追加

1. Chrome ブラウザで `https://id-info.jihs.go.jp/updates.html` を開く
2. ページテキストを取得し、直近2週間の新着記事タイトル・URL・日付を抽出する
3. `{ROOT}/dashboard.html` の `const ALERTS = [...]` を読んで現在のエントリIDをすべてリストアップ
4. 既存エントリにないものを「新規」とみなす
5. 新規ニュース各件に対してAI判定を行う:
   - **重要度判定**（severity）:
     - `🔴` = 緊急アラート: 新規感染症・未知病原体・致死率高・大規模アウトブレイク
     - `🟡` = 注意: 麻疹・風疹・百日咳など感染拡大中の感染症、リスク評価更新
     - `🔵` = 定期情報: 速報・週報・月報などの定期更新、通常のサーベイランス情報
   - **alert_type**: 「緊急アラート」「感染動向」「定期情報」「リスク評価」「薬剤耐性」「新規病原体」など
   - **one_liner**: 30文字以内の簡潔な日本語要約
   - **reasoning**: 判断根拠（100文字程度）
6. 新規エントリを配列の先頭に追加する（最新が先頭）

ALERTSエントリのフォーマット（必ずこの形式を守る）:
```json
{
  "id": "{YYYYMMDD}-{3桁連番}",
  "status": "judged",
  "update_date": "{YYYY}年{M}月{D}日",
  "pub_date": "{YYYY}年{M}月{D}日",
  "is_new_article": true,
  "title": "「{タイトル}」の記事を更新しました",
  "url": "https://id-info.jihs.go.jp/...",
  "keyword_screen": {
    "matched_keywords": [...],
    "alert_types": [...],
    "score": 数値
  },
  "ai_judgment": {
    "is_alert": true,
    "severity": "🔵 or 🟡 or 🔴",
    "alert_type": "...",
    "one_liner": "...",
    "reasoning": "...",
    "judged_at": "YYYY-MM-DD"
  }
}
```

### 4b: 1週間以上前のニュースを削除

Pythonで以下を実行して古いエントリを削除する（`DASHBOARD_ROOT` 環境変数を渡してから実行すること）:
```bash
DASHBOARD_ROOT="$DASHBOARD_ROOT" python3 << 'PYEOF'
import os, re, json, datetime

root = os.environ['DASHBOARD_ROOT']
path = f'{root}/dashboard.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'(const ALERTS = )(\[.*?\]);', content, re.DOTALL)
alerts = json.loads(m.group(2))

today = datetime.datetime.today()
cutoff = today - datetime.timedelta(days=7)

def parse_date(s):
    nums = re.findall(r'\d+', s)
    if len(nums) >= 3:
        return datetime.datetime(int(nums[0]), int(nums[1]), int(nums[2]))
    return None

kept = [a for a in alerts if (d := parse_date(a['update_date'])) and d >= cutoff]

alerts_json = json.dumps(kept, ensure_ascii=False, separators=(',', ':'))
new_content = content[:m.start(2)] + alerts_json + content[m.end(2):]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"保持: {len(kept)}件, 削除: {len(alerts)-len(kept)}件")
PYEOF
```

---

## ステップ5: 異常検知（毎日）

統計的異常検知（過去5年同週比 + log変換 + 2σ/3σ閾値）を走らせて結果を dashboard に注入する。

```bash
python3 "$DASHBOARD_ROOT/update_pipeline.py" detect
```

これにより `scripts/anomalies.json` が生成され、dashboard.html の `DATA.anomalies` が自動で更新される。

実行後、`scripts/anomalies.json` の `anomalies` 配列の中身を確認して次のステップ6で使う。具体的には:
```bash
python3 -c "import json; d=json.load(open('$DASHBOARD_ROOT/scripts/anomalies.json')); print(json.dumps(d['anomalies'], ensure_ascii=False, indent=2))"
```

---

## ステップ6: AI 解説の生成（毎日）

ステップ5の異常検知結果と最新の疾病動向を元に、200〜400字の日本語週報コメントを生成する。

### 6a: 解説本文を作成

以下の情報を統合して日本語の解説テキストを書く:
- ステップ5で得た `anomalies` 配列の各疾病（disease, current, expected_mean, ratio_to_baseline, severity）
- 現在のISO週（`state.json` の `processed_weeks` の最新）
- 必要なら `state.json` の `last_run_result` も参照

**解説の構成（推奨）**:
1. 今週の総括（1文）
2. 最も重要な異常（high severity）の詳細解説
3. その他の medium severity 異常の簡潔な紹介
4. 新規データなしの場合: 主要疾病（インフル・コロナ・RSなど）の現状を簡潔に

**注意**:
- 観察事実のみを述べ、診断・治療助言・予測は書かない
- 数値は anomalies.json の値をそのまま引用する（捏造禁止）
- 改行は `\n\n` で段落分け
- 250〜400字程度

### 6b: 解説を dashboard に注入

生成したテキストをファイルに保存して inject_insights.py に渡す:

```bash
cat > /tmp/commentary.txt << 'TXT_EOF'
（ここに生成した解説本文をそのまま貼り付け）
TXT_EOF
python3 "$DASHBOARD_ROOT/scripts/inject_insights.py" --commentary-file /tmp/commentary.txt
```

これで dashboard.html の `DATA.ai_commentary` が更新される。

---

## ステップ7: GitHub Pages へのデプロイ（毎回・新規追加）

dashboard.html を含む差分を GitHub に push して、公開ページ（GitHub Pages）を更新する。

```bash
bash "$DASHBOARD_ROOT/deploy.sh" "Auto update $(date +%Y-%m-%d)"
```

deploy.sh は内部で次を行う:
- 差分がなければ `✓ 変更なし。push スキップ。` で終了（冪等）
- 差分があれば `dashboard.html` / `scripts/anomalies.json` / `scripts/full_dashboard_data.json` / `state.json` / `README.md` などを `git add → git commit → git push origin main`
- GitHub Pages の反映には1〜2分かかる
- 認証は Mac の Keychain に保存された Personal Access Token / SSH キーで自動的に行われる（対話プロンプトは出ない）

**サンドボックス制約に関する注意**:
- 一部の Cowork セッションでは `.git/index.lock` を unlink できないために git 操作が失敗することがある
- その場合は失敗を記録した上で他のステップを続行し、サマリー欄に「デプロイ失敗: {理由}」と明記する
- 失敗時はユーザに「Mac の Terminal から `cd ~/Desktop/claude && bash deploy.sh` を実行してください」と案内する

エラー時の扱い:
- `❌ リモート 'origin' が設定されていません` → 設定不備として記録、その他のステップは継続
- 認証失敗（`could not read Username` / `Permission denied`）→ Keychain 切れの可能性、ユーザに手動 push を依頼
- マージコンフリクト → `git pull --rebase` を提案するメッセージを残し、自動マージは行わない

---

## ステップ8: 実行結果のサマリーを出力

以下の形式で結果を報告:
```
=== JIHS 自動更新 実行結果 ===
日時: {実行日時}
速報: {新しい週を処理した場合は「{year}年第{week}週 処理完了（{n}疾病更新）」/ なければ「新しい速報なし」}
速報集計: {speed_trends 末尾週: {y}-W{w} / 全{n}疾病}
週報PDF: {ダウンロード・処理した場合は詳細 / なければ「更新不要（未公開）」}
年報: {利用可能になった場合は詳細 / なければ「変化なし」or「未公開」}
ニュース: {新規{n}件追加, 古いニュース{m}件削除}
異常検知: {high {x}件 / medium {y}件 検出 / 主要シグナル: {top1疾病} ×{ratio}}
AI解説: {生成済 ({文字数}字)}
ダッシュボード: {更新した場合「dashboard.html 更新済み」/ なければ「更新なし」}
GitHub Pages: {デプロイ成功時「{commit_sha} push 完了 / {変更ファイル数} 件」/ なければ「変更なし」/ 失敗時「失敗: {理由}」}
```

---

## 移行に関する注意（参考）

このタスクを別の PC に移す場合:
1. `{ROOT}` 配下のファイル（`dashboard.html`, `state.json`, `scripts/`, `2013/`〜`2026/`, `diseases/`, `nesid_historical/` など）を新 PC の任意のフォルダにコピーする
2. 新 PC の Cowork でそのフォルダを mount する（フォルダ名は `claude` のままでも別名でも可。本タスクは `dashboard.html` の存在で自動検出する）
3. 新 PC の Cowork で `/schedule` 経由で本タスクを再作成する（このプロンプトをそのまま貼ればよい）
4. 新 PC に Chrome ブラウザ拡張をインストールし、Claude アカウントに接続する
5. 新 PC に Git と GitHub 認証（SSH キーまたは Personal Access Token + Keychain）をセットアップする
