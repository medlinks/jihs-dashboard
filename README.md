# JIHS 感染症サーベイランスダッシュボード

国立健康危機管理研究機構（JIHS）の感染症発生動向調査（IDWR）データを基にした
リアルタイム監視ダッシュボード。

## 機能

- 速報データ（過去4週）・週報データ（2013–2026）・年報（NESID 2024）
- 都道府県別ヒートマップ
- 統計的異常検知（Historic Limits / log変換 + 過去5年同週±2週との比較）
- AI 自動週報解説（Claude による要約）
- JIHS 公式更新情報の自動取得

## 公開URL

GitHub Pages デプロイ後にここに記載:
`https://<username>.github.io/<repo>/`

## ローカル動作

`dashboard.html` をブラウザで直接開けば動きます（追加の HTTP サーバ不要）。

## 自動更新の仕組み

毎日 10:09 に Cowork のスケジュール経由で:
1. JIHS から最新の速報・週報 PDF を取得
2. データを抽出して JSON に集計
3. 異常検知アルゴリズムを実行
4. AI による週報解説を生成
5. `dashboard.html` に再埋め込み
6. （オプション）GitHub に push してネット公開を更新

## ファイル構成

ルート直下にはダッシュボード本体のみ表示。スキルが参照する必須データフォルダは
そのまま残し、それ以外は `archive/` 配下にカテゴリ別整理されている。

```
dashboard.html             # メインのダッシュボード（編集対象、git 非追跡）
index.html                 # パスワード暗号化済み公開版（GitHub Pages 配信）
README.md

# === スキル必須（jihs-update / nndss-update が参照、移動不可） ===
scripts/                   # 抽出・集計・注入スクリプト群 + full_dashboard_data.json
tests/                     # PDF ヘッダ検査・参考値検証
us/                        # 米国 NNDSS / CDC AVI データ（raw / processed）
weekly_extracted/          # JIHS 週報 PDF → Excel
population/                # 都道府県人口（build_annual_incidence.py 用）
2013/ … 2026/              # JIHS 週報 PDF 年別フォルダ

# === archive/（補助ファイル群、用途別） ===
archive/
├── skills/                # スキルパッケージ・ドラフト（.skill / SKILL.md）
├── alerts/                # アラート収集パイプライン（collect_alerts.py 等）
├── pilot/                 # パイロット研究スクリプト・結果
├── did_classification/    # DID 都市分類（urban tier / metro 関連）
├── weekly_processing/     # 週次処理スクリプト（process_w15/w16 等）
├── research/              # 研究ドキュメント・PMID 一覧・短報
├── tools/                 # encrypt_dashboard.py / deploy.sh
├── backups/               # dashboard.html.bak* 等
├── legacy/                # 旧 NESID / 旧 IDWR ワークスペース等
└── misc/                  # その他
```

### 暗号化＆デプロイの呼び出し方

```bash
# 暗号化のみ:
python3 archive/tools/encrypt_dashboard.py <パスワード> dashboard.html index.html

# 暗号化 → commit → push を一括:
./archive/tools/deploy.sh "コミットメッセージ"
```

### 週次データ更新の呼び出し方（変更なし）

スキルは `--project-root` にプロジェクトルート（このフォルダ）を指定して呼ぶ。
内部で `scripts/`, `tests/`, `us/`, `weekly_extracted/`, `2013/`–`2026/` を参照する。

```bash
python3 <skill-dir>/scripts/run_us_pipeline.py --project-root /path/to/this/folder
python3 <skill-dir>/scripts/run_pipeline.py    --project-root /path/to/this/folder
```

## ライセンス・データ出典

データ出典: [JIHS 感染症発生動向調査](https://id-info.jihs.go.jp/)
本ダッシュボードは個人学習目的の非公式集計です。
