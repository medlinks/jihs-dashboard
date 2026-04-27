"""
JIHS アラート収集・キーワードスクリーニングスクリプト

処理フロー:
1. updates.html をスキャンして対象記事を特定
2. 初掲載日 vs 更新日を区別（古い記事の更新はスキップ）
3. キーワード一次スクリーニング
4. 記事本文を取得してテキスト抽出
5. alerts_pending.json に候補を保存（AI判定待ち）
"""

import json
import re
import ssl
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from html.parser import HTMLParser

# ============================================================
# パス設定
# ============================================================
BASE_DIR          = Path(__file__).parent
ALERT_STATE_FILE  = BASE_DIR / 'alert_state.json'
ALERTS_PENDING    = BASE_DIR / 'alerts_pending.json'
ALERTS_FINAL      = BASE_DIR / 'alerts.json'
LOG_FILE          = BASE_DIR / 'collect_log.txt'

UPDATES_URL = 'https://id-info.jihs.go.jp/updates.html'
SITE_BASE   = 'https://id-info.jihs.go.jp'

# ============================================================
# SSL・フェッチ
# ============================================================
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=15) as r:
        return r.read().decode('utf-8', errors='replace')

def log(msg: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] [ALERT] {msg}'
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

# ============================================================
# キーワード定義
# ============================================================

# 一次スクリーニング：タイトルにこれらがあれば候補
ALERT_KEYWORDS_PRIMARY = [
    '初確認', '初例', '初めて確認', '初報告', '初発例',
    '集積', 'クラスター', 'アウトブレイク', '多発',
    '耐性', 'マクロライド耐性', '薬剤耐性', '抗菌薬耐性',
    '重症', '死亡', '致死', '重篤',
    '拡大', '急増', '増加傾向', '異常増加',
    '新型', '新興', '変異',
    'リスク評価', 'リスクアセスメント',
]

# 対象外キーワード（これがタイトルにあればスキップ）
SKIP_KEYWORDS = [
    'ワクチン接種状況', '予防接種状況', '抗体保有状況',
    '接種スケジュール', '外部精度管理',
    '速報グラフ', 'ダウンロード', '採用', '調達',
    '研修会', 'シンポジウム', '公開講座',
]

# アラート種別分類キーワード
ALERT_TYPE_KEYWORDS = {
    '地理的拡大':   ['初確認', '初例', '初めて確認', '初報告', '初発例', '初めて'],
    '集積発生':     ['集積', 'クラスター', 'アウトブレイク', '多発'],
    '薬剤耐性':     ['耐性', 'マクロライド耐性', '薬剤耐性', '抗菌薬耐性'],
    '重症化':       ['重症', '死亡', '致死', '重篤', 'ICU', '人工呼吸'],
    'リスク評価':   ['リスク評価', 'リスクアセスメント'],
    '新規病原体':   ['新型', '新興', '変異', '新規'],
    '感染拡大':     ['拡大', '急増', '増加傾向', '異常増加'],
}

# 対象URLパターン（これらのパスを含むURLが対象）
TARGET_URL_PATTERNS = [
    r'/iasr/pathogens/',       # IASR 症例報告・病原体情報
    r'/risk-assessment/',      # リスクアセスメント
    r'/infectious-diseases/',  # 疾患情報更新
]

# 除外URLパターン（速報・定点・グラフ等）
SKIP_URL_PATTERNS = [
    r'/provisional/',          # IDWR速報データ（collect_idwr.pyで処理済み）
    r'/graph/',                # グラフ更新
    r'/schedule/',             # スケジュール
    r'/immunization/',         # 予防接種
    r'/nesvpd/',               # 流行予測
    r'/idwr/index',            # IDWR トップ
    r'/idss/',                 # サーベイランスまとめ
]

# ============================================================
# 状態管理
# ============================================================
def load_alert_state() -> dict:
    if ALERT_STATE_FILE.exists():
        with open(ALERT_STATE_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {'processed_urls': [], 'last_run': None}

def save_alert_state(state: dict):
    with open(ALERT_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_pending() -> list:
    if ALERTS_PENDING.exists():
        with open(ALERTS_PENDING, encoding='utf-8') as f:
            return json.load(f)
    return []

def save_pending(items: list):
    with open(ALERTS_PENDING, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

# ============================================================
# HTML本文抽出
# ============================================================
class ArticleExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = False
        self.paragraphs = []
        self.current = []
        self.pub_date = None

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag in {'script', 'style', 'nav', 'header', 'footer'}:
            self.skip = True
        if tag in {'p', 'h1', 'h2', 'h3', 'li'}:
            self.current = []

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'nav', 'header', 'footer'}:
            self.skip = False
        if tag in {'p', 'h1', 'h2', 'h3', 'li'}:
            text = ' '.join(self.current).strip()
            if text and len(text) > 10:
                self.paragraphs.append(text)
            self.current = []

    def handle_data(self, data):
        if not self.skip:
            s = data.strip()
            if s:
                self.current.append(s)
                # 公開日を探す
                m = re.search(r'公開日[：:]\s*(\d{4}年\d+月\d+日)', s)
                if m and not self.pub_date:
                    self.pub_date = m.group(1)


def extract_article(url: str) -> dict:
    """記事本文・公開日・タイトルを抽出"""
    try:
        html = fetch(url)
        parser = ArticleExtractor()
        parser.feed(html)

        # タイトル抽出
        title_m = re.search(r'<title>(.*?)</title>', html)
        title = title_m.group(1).split('｜')[0].strip() if title_m else ''

        # 本文（最初の1500文字）
        body = '\n'.join(parser.paragraphs)[:1500]

        return {
            'title': title,
            'pub_date': parser.pub_date,
            'body': body,
        }
    except Exception as e:
        log(f'    WARNING 記事取得失敗: {e}')
        return {'title': '', 'pub_date': None, 'body': ''}

# ============================================================
# updates.html のスキャン
# ============================================================
def scan_updates(state: dict) -> list:
    """
    updates.html をスキャンして未処理の対象記事を返す
    """
    log('updates.html をスキャン中...')
    html = fetch(UPDATES_URL)

    # 全アップデートアイテムを抽出
    items_raw = re.findall(
        r'<a[^>]+href="([^"]+)"[^>]*>.*?'
        r'<time[^>]*>([^<]+)</time>.*?'
        r'<h3[^>]*>(.*?)</h3>.*?</a>',
        html, re.DOTALL
    )

    candidates = []

    for href, date_str, title_raw in items_raw:
        title = re.sub(r'<[^>]+>', '', title_raw).strip()
        date_str = date_str.strip()

        # 絶対URLに変換
        if href.startswith('./'):
            url = SITE_BASE + href[1:]
        elif href.startswith('/'):
            url = SITE_BASE + href
        else:
            url = href

        # 除外URLパターンチェック
        if any(re.search(p, url) for p in SKIP_URL_PATTERNS):
            continue

        # 対象URLパターンチェック
        if not any(re.search(p, url) for p in TARGET_URL_PATTERNS):
            continue

        # タイトルの除外キーワードチェック
        if any(kw in title for kw in SKIP_KEYWORDS):
            log(f'  スキップ（除外KW）: {title[:50]}')
            continue

        # 処理済みURLチェック
        if url in state['processed_urls']:
            continue

        candidates.append({
            'url': url,
            'update_date': date_str,
            'title': title,
        })

    log(f'  未処理の対象記事: {len(candidates)}件')
    return candidates

# ============================================================
# キーワードスクリーニング
# ============================================================
def keyword_screen(title: str, body: str) -> dict:
    """
    タイトル＋本文でキーワードスクリーニング
    戻り値: {
        'pass': bool,
        'matched_keywords': [],
        'alert_types': [],
        'score': int
    }
    """
    text = title + ' ' + body[:500]
    matched = []
    score = 0

    # 一次スクリーニング
    for kw in ALERT_KEYWORDS_PRIMARY:
        if kw in text:
            matched.append(kw)
            # タイトルにあれば高スコア
            score += 3 if kw in title else 1

    # アラート種別
    types = []
    for atype, keywords in ALERT_TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            types.append(atype)

    return {
        'pass': score > 0,
        'matched_keywords': matched,
        'alert_types': types,
        'score': score,
    }

# ============================================================
# メイン処理
# ============================================================
def main():
    log('=' * 50)
    log('アラート収集スクリプト 開始')

    state = load_alert_state()
    candidates = scan_updates(state)

    if not candidates:
        log('新しい対象記事なし。終了。')
        return

    pending = load_pending()
    new_count = 0

    for item in candidates:
        url   = item['url']
        title = item['title']
        log(f'\n  処理中: {title[:60]}')

        # 記事本文・公開日を取得
        article = extract_article(url)
        pub_date = article['pub_date']

        # 初掲載日 vs 更新日の判定
        # 公開日が取得できた場合: 更新日と比較
        is_new_article = True
        if pub_date:
            # 更新日と公開日が違う = 以前の記事の更新
            update_date_str = item['update_date']  # 例: '2026年4月14日'
            # 公開日が1年以上前なら古い記事の更新と見なす
            try:
                pub_year = int(re.search(r'(\d{4})年', pub_date).group(1))
                upd_year = int(re.search(r'(\d{4})年', update_date_str).group(1))
                if upd_year - pub_year >= 1:
                    is_new_article = False
                    log(f'    古い記事の更新（公開:{pub_date}）→ スキップ')
            except:
                pass

        # キーワードスクリーニング
        screen = keyword_screen(title, article['body'])

        if not screen['pass']:
            log(f'    キーワード不一致 → スキップ')
            # 処理済みとして記録（次回もスキップ）
            state['processed_urls'].append(url)
            continue

        log(f'    スクリーニング通過: キーワード={screen["matched_keywords"]}, '
            f'種別={screen["alert_types"]}, スコア={screen["score"]}')

        # pending に追加
        alert_id = f'{item["update_date"].replace("年","").replace("月","").replace("日","")}-{len(pending)+1:03d}'
        pending_item = {
            'id': alert_id,
            'status': 'pending_ai',         # AI判定待ち
            'update_date': item['update_date'],
            'pub_date': pub_date,
            'is_new_article': is_new_article,
            'title': title,
            'url': url,
            'body_excerpt': article['body'][:800],
            'keyword_screen': screen,
            'ai_judgment': None,             # AI判定後に埋まる
        }
        pending.append(pending_item)
        state['processed_urls'].append(url)
        new_count += 1
        log(f'    → alerts_pending.json に追加')

    save_pending(pending)
    state['last_run'] = datetime.now().isoformat()
    save_alert_state(state)

    log(f'\n完了: {new_count}件をalerts_pending.jsonに追加')
    log('=' * 50)

if __name__ == '__main__':
    main()
