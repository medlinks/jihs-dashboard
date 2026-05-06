#!/bin/bash
# GitHub Pages 自動デプロイスクリプト
# 使い方: ./archive/tools/deploy.sh "コミットメッセージ（省略可）"
#
# 注: スクリプトは archive/tools/ にあるが、cd でプロジェクトルートに移動して実行する。

set -e
# Resolve project root: this script lives at <project-root>/archive/tools/deploy.sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
ENCRYPT_PY="$SCRIPT_DIR/encrypt_dashboard.py"

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
STALE=(.git/index.lock .git/HEAD.lock .git/refs/remotes/origin/main.lock .git/index.lock.bak .git/index.lock.bak2 .git/index.lock.stale .git/__test__)
for f in "${STALE[@]}"; do
  if [ -e "$f" ]; then
    # サンドボックスで unlink 不可でも rename は可能なので、退避するだけで OK
    if rm -f "$f" 2>/dev/null; then
      echo "🧹 stale ファイル削除: $f"
    else
      mv "$f" "${f}.stale.$(date +%s%N)" 2>/dev/null && echo "🧹 stale ファイル退避: $f" || true
    fi
  fi
done
# tmp_obj_* と stale.* 系も同様
find .git -maxdepth 4 -name "*.lock.stale.*" -mmin +60 2>/dev/null | head -20 | while read f; do
  rm -f "$f" 2>/dev/null || true
done
# テンポラリオブジェクト（サンドボックスがunlink失敗で残したもの）を掃除
TMP_OBJS=$(find .git/objects -name "tmp_obj_*" 2>/dev/null)
if [ -n "$TMP_OBJS" ]; then
  echo "🧹 stale tmp_obj_* を削除します"
  echo "$TMP_OBJS" | xargs rm -f 2>/dev/null || true
fi

# リモートが設定されているか
if ! git remote get-url origin > /dev/null 2>&1; then
  echo "❌ リモート 'origin' が設定されていません。"
  echo "   git remote add origin https://github.com/<USER>/<REPO>.git"
  exit 1
fi

# ── パスワード付き暗号化（index.html を暗号化版として生成） ──
# 環境変数 JIHS_PW があれば使用、無ければ既定値（要本番では変更）
DASHBOARD_PW="${JIHS_PW:-juntendo}"
if [ -f dashboard.html ] && [ -f "$ENCRYPT_PY" ]; then
  echo "🔒 dashboard.html を暗号化して index.html に出力中..."
  python3 "$ENCRYPT_PY" "$DASHBOARD_PW" dashboard.html index.html
fi

# lock を再退避（git コマンドが生成した可能性があるもの）
cleanup_locks() {
  for lock_f in .git/index.lock .git/HEAD.lock .git/refs/remotes/origin/main.lock; do
    if [ -f "$lock_f" ]; then
      rm -f "$lock_f" 2>/dev/null || mv "$lock_f" "${lock_f}.stale.$(date +%s%N)" 2>/dev/null || true
    fi
  done
}

# 変更があるかチェック
cleanup_locks
if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
  echo "✓ 変更なし。push スキップ。"
  exit 0
fi

# dashboard.html は git に含めない（パスワード保護のため）。index.html だけ push する。
cleanup_locks
git add index.html scripts/anomalies.json scripts/full_dashboard_data.json README.md 2>/dev/null || true
cleanup_locks
git add -u
cleanup_locks
# dashboard.html が誤って add されていたら除外
git rm --cached -f dashboard.html 2>/dev/null || true
cleanup_locks
git commit -m "$MSG"
cleanup_locks
git push origin main

echo ""
echo "✅ デプロイ完了"
echo "   GitHub Pages の反映には 1〜2 分かかります"
