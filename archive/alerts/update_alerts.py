"""Update ALERTS in dashboard.html: add new news items, remove old (>7 days)."""
import re, json, os, datetime

ROOT = '/sessions/eager-laughing-sagan/mnt/claude'
path = f'{ROOT}/dashboard.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

m = re.search(r'(const ALERTS = )(\[.*?\]);', content, re.DOTALL)
alerts = json.loads(m.group(2))

# Existing IDs to detect duplicates
existing_urls = {a.get('url') for a in alerts}

today = datetime.datetime(2026, 4, 29)
cutoff = today - datetime.timedelta(days=7)

# New news items from 2026-04-28
NEW_NEWS = [
    {
        "title_text": "風疹に関する疫学情報",
        "url": "https://id-info.jihs.go.jp/surveillance/idss/target-diseases/rubella/epidemiological-status/index.html",
        "update_date": "2026年4月28日",
        "id": "20260428-001",
        "severity": "🔵",
        "alert_type": "感染動向",
        "one_liner": "風疹疫学情報の月次更新",
        "reasoning": "風疹の月次疫学情報の定期更新。例年通りのサーベイランス情報",
        "matched_keywords": ["風疹", "疫学"],
        "alert_types": ["定期情報", "感染動向"],
        "score": 30
    },
    {
        "title_text": "麻疹 発生動向調査",
        "url": "https://id-info.jihs.go.jp/surveillance/idwr/diseases/measles/graph/index.html",
        "update_date": "2026年4月28日",
        "id": "20260428-002",
        "severity": "🟡",
        "alert_type": "感染動向",
        "one_liner": "麻疹発生動向の最新更新（流行継続中）",
        "reasoning": "麻しんは異常検知でhigh重要度。W15で56件、過去5年同週比×73.8の異常水準が継続中",
        "matched_keywords": ["麻疹", "発生動向"],
        "alert_types": ["感染動向", "リスク評価"],
        "score": 75
    },
    {
        "title_text": "風疹 発生動向調査",
        "url": "https://id-info.jihs.go.jp/surveillance/idwr/diseases/rubella/graph/index.html",
        "update_date": "2026年4月28日",
        "id": "20260428-003",
        "severity": "🔵",
        "alert_type": "感染動向",
        "one_liner": "風疹発生動向の週次更新",
        "reasoning": "風疹発生動向の週次更新。現状は低水準で推移",
        "matched_keywords": ["風疹", "発生動向"],
        "alert_types": ["定期情報", "感染動向"],
        "score": 30
    },
    {
        "title_text": "IDWR速報データ 2026年第16週",
        "url": "https://id-info.jihs.go.jp/surveillance/idwr/provisional/2026/16/index.html",
        "update_date": "2026年4月28日",
        "id": "20260428-004",
        "severity": "🔵",
        "alert_type": "定期情報",
        "one_liner": "IDWR第16週速報データ公開",
        "reasoning": "毎週の感染症発生動向調査速報の定期公開。第16週（4/13-4/19）データ",
        "matched_keywords": ["IDWR", "速報"],
        "alert_types": ["定期情報"],
        "score": 25
    },
    {
        "title_text": "感染症発生動向調査で届け出られた淋菌感染症の動向について",
        "url": "https://id-info.jihs.go.jp/surveillance/idss/target-diseases/gonorrhoea/index.html",
        "update_date": "2026年4月28日",
        "id": "20260428-005",
        "severity": "🔵",
        "alert_type": "感染動向",
        "one_liner": "淋菌感染症の動向情報を更新",
        "reasoning": "性感染症（STI）の定期動向情報の更新。継続モニタリング対象",
        "matched_keywords": ["淋菌", "感染動向"],
        "alert_types": ["定期情報", "感染動向"],
        "score": 35
    },
    {
        "title_text": "感染症発生動向調査で届け出られた性器クラミジア感染症の動向について",
        "url": "https://id-info.jihs.go.jp/surveillance/idss/target-diseases/chlamydia-std/index.html",
        "update_date": "2026年4月28日",
        "id": "20260428-006",
        "severity": "🔵",
        "alert_type": "感染動向",
        "one_liner": "クラミジア感染症の動向情報を更新",
        "reasoning": "STI動向情報の定期更新。継続モニタリング対象",
        "matched_keywords": ["クラミジア", "感染動向"],
        "alert_types": ["定期情報", "感染動向"],
        "score": 35
    },
]

# Build new entries
new_entries = []
for n in NEW_NEWS:
    if n['url'] in existing_urls:
        continue
    entry = {
        "id": n['id'],
        "status": "judged",
        "update_date": n['update_date'],
        "pub_date": n['update_date'],
        "is_new_article": True,
        "title": f"「{n['title_text']}」の記事を更新しました",
        "url": n['url'],
        "keyword_screen": {
            "matched_keywords": n['matched_keywords'],
            "alert_types": n['alert_types'],
            "score": n['score']
        },
        "ai_judgment": {
            "is_alert": True,
            "severity": n['severity'],
            "alert_type": n['alert_type'],
            "one_liner": n['one_liner'],
            "reasoning": n['reasoning'],
            "judged_at": "2026-04-29"
        }
    }
    new_entries.append(entry)

# Insert new entries at front, then keep old ones that are within 7 days
def parse_date(s):
    nums = re.findall(r'\d+', s)
    if len(nums) >= 3:
        return datetime.datetime(int(nums[0]), int(nums[1]), int(nums[2]))
    return None

old_kept = [a for a in alerts if (d := parse_date(a['update_date'])) and d >= cutoff]
old_deleted = len(alerts) - len(old_kept)

merged = new_entries + old_kept
print(f"Added: {len(new_entries)} new alerts")
print(f"Kept: {len(old_kept)} alerts (within 7 days)")
print(f"Deleted: {old_deleted} alerts (older than 7 days)")
print(f"Total: {len(merged)}")

alerts_json = json.dumps(merged, ensure_ascii=False, separators=(',', ':'))
new_content = content[:m.start(2)] + alerts_json + content[m.end(2):]

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

# Save summary for later use
import json
with open(f'{ROOT}/.alerts_run_summary.json', 'w') as f:
    json.dump({
        "added": len(new_entries),
        "deleted": old_deleted,
        "total": len(merged)
    }, f)
