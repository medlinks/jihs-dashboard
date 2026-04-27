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

```
dashboard.html              # メインのダッシュボード（自己完結 HTML）
update_pipeline.py          # 更新パイプラインのオーケストレータ
collect_idwr.py             # 速報データ収集
collect_alerts.py           # JIHS ニュース収集
scripts/
  ├── extract_jihs_fixed.py     # 週報PDF → JSON 抽出
  ├── extract_all_diseases.py   # 全疾病集計
  ├── detect_anomalies.py       # 統計的異常検知
  ├── inject_insights.py        # 異常 + AI 解説の dashboard 注入
  └── full_dashboard_data.json  # 集計データ
```

## ライセンス・データ出典

データ出典: [JIHS 感染症発生動向調査](https://id-info.jihs.go.jp/)
本ダッシュボードは個人学習目的の非公式集計です。
