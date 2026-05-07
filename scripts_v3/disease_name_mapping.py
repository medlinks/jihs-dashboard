"""Centralized JP→EN translations for figure rendering.

All figure scripts must import from here — no ad-hoc translations.
Every string passed to matplotlib's set_title/set_label/legend must be ASCII-only
(or limited to ASCII + Latin-1 punctuation) before figure save.
"""

DISEASE_NAME_EN = {
    "麻しん":                  "Measles",
    "風しん":                  "Rubella",
    "手足口病":                "HFMD",
    "インフルエンザ":          "Influenza",
    "RSウイルス感染症":        "RSV",
    "感染性胃腸炎":            "Gastroenteritis",
    "流行性耳下腺炎":          "Mumps",
    "咽頭結膜熱":              "PCF",
    "マイコプラズマ肺炎":      "Mycoplasma pneumonia",
    "A群溶血性レンサ球菌咽頭炎": "GAS pharyngitis",
    "Ａ群溶血性レンサ球菌咽頭炎": "GAS pharyngitis",  # full-width A variant
    "レンサ球菌咽頭炎":        "GAS pharyngitis",     # dashboard alias
    "梅毒":                    "Syphilis",
    "ヘルパンギーナ":          "Herpangina",
}

AXIS_LABELS_EN = {
    "週": "Week",
    "ISO週": "ISO week",
    "都道府県": "Prefecture",
    "件数": "Cases",
    "週報告数": "Weekly reports",
    "累計件数": "Cumulative cases",
    "発生数": "Incidence",
    "報告週": "Report week",
    "報告数": "Reports",
}

URBAN_TIER_EN = {
    "high_urban":    "High urban (DID >=70%)",
    "mixed":         "Mixed (DID 40-70%)",
    "rural_leaning": "Rural-leaning (DID <40%)",
}

# 47 prefectures in standard romanization, no macrons
PREFECTURE_NAME_EN = {
    "北海道":   "Hokkaido",
    "青森県":   "Aomori",
    "岩手県":   "Iwate",
    "宮城県":   "Miyagi",
    "秋田県":   "Akita",
    "山形県":   "Yamagata",
    "福島県":   "Fukushima",
    "茨城県":   "Ibaraki",
    "栃木県":   "Tochigi",
    "群馬県":   "Gunma",
    "埼玉県":   "Saitama",
    "千葉県":   "Chiba",
    "東京都":   "Tokyo",
    "神奈川県": "Kanagawa",
    "新潟県":   "Niigata",
    "富山県":   "Toyama",
    "石川県":   "Ishikawa",
    "福井県":   "Fukui",
    "山梨県":   "Yamanashi",
    "長野県":   "Nagano",
    "岐阜県":   "Gifu",
    "静岡県":   "Shizuoka",
    "愛知県":   "Aichi",
    "三重県":   "Mie",
    "滋賀県":   "Shiga",
    "京都府":   "Kyoto",
    "大阪府":   "Osaka",
    "兵庫県":   "Hyogo",
    "奈良県":   "Nara",
    "和歌山県": "Wakayama",
    "鳥取県":   "Tottori",
    "島根県":   "Shimane",
    "岡山県":   "Okayama",
    "広島県":   "Hiroshima",
    "山口県":   "Yamaguchi",
    "徳島県":   "Tokushima",
    "香川県":   "Kagawa",
    "愛媛県":   "Ehime",
    "高知県":   "Kochi",
    "福岡県":   "Fukuoka",
    "佐賀県":   "Saga",
    "長崎県":   "Nagasaki",
    "熊本県":   "Kumamoto",
    "大分県":   "Oita",
    "宮崎県":   "Miyazaki",
    "鹿児島県": "Kagoshima",
    "沖縄県":   "Okinawa",
}

def en_disease(jp): return DISEASE_NAME_EN.get(jp, jp)
def en_pref(jp):    return PREFECTURE_NAME_EN.get(jp, jp)
def en_tier(t):     return URBAN_TIER_EN.get(t, t)

def assert_ascii_safe(s, context=''):
    """Assert string is ASCII-printable + common punctuation only.
    Latin-1 dashes/quotes allowed; any CJK char raises."""
    for ch in s:
        if ord(ch) > 0x2122:  # allow basic Latin-1 + general punct
            raise AssertionError(
                f'Non-ASCII character {ch!r} (U+{ord(ch):04X}) in {context!r}: {s!r}')
