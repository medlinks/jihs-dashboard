#!/bin/bash
# GitHub Pages 自動デプロイスクリプト
# 使い方: ./deploy.sh "コミットメッセージ（省略可）"

set -e
cd "$(dirname "$0")"

MSG="${1:-Update dashboard $(date +%Y-%m-%d)}"

# Git リポジトリかチェック
if [ ! -d .git ]; then
  echo "❌ git リポジトリではありません。先に 'git init' してください。"
  echo "   詳しくは README.md を参照。"
  exit 1
fi

# サンドボックス（Cowork等）からのgit試行で残ったロック・テンポラリを掃除
# 走行中のgitプロセスがある場合のみ警告して中断する
if pgrep -x git > /dev/null 2>&1; then
  echo "⚠️  動作中のgitプロセスが検出されました。終了を待ってから再度実行してください。"
  pgrep -lx git
  exit 1
fi
# ロックファイル類を一括削除（不在ならスキップ）
STALE=(.git/index.lock .git/index.lock.bak .git/index.lock.bak2 .git/index.lock.stale .git/__test__)
for f in "${STALE[@]}"; do
  if [ -e "$f" ]; then
    rm -f "$f" && echo "🧹 stale ファイル削除: $f"
  fi
done
# テンポラリオブジェクト（サンドボックスがunlink失敗で残したもの）を掃除
TMP_OBJS=$(find .git/objects -name "tmp_obj_*" 2>/dev/null)
if [ -n "$TMP_OBJS" ]; then
  echo "🧹 stale tmp_obj_* を削除します"
  echo "$TMP_OBJS" | xargs rm -f
fi

# リモートが設定されているか
if ! git remote get-url origin > /dev/null 2>&1; then
  echo "❌ リモート 'origin' が設定されていません。"
  echo "   git remote add origin https://github.com/<USER>/<REPO>.git"
  exit 1
fi

# 変更があるかチェック
if git diff --quiet && git diff --cached --quiet; then
  echo "✓ 変更なし。push スキップ。"
  exit 0
fi

git add dashboard.html scripts/anomalies.json scripts/full_dashboard_data.json README.md 2>/dev/null || true
git add -u
git commit -m "$MSG"
git push origin main

echo ""
echo "✅ デプロイ完了"
echo "   GitHub Pages の反映には 1〜2 分かかります"
