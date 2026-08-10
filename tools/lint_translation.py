# ------------------------------------------------------------------------------
# 翻訳品質linter
#
# data/*/rfc*-trans.json の翻訳品質を、英語原文と照合して機械的に検査する。
# LLMを使わず決定的に判定できる欠陥のみを対象とするため、全RFCに対して
# 何度でも実行できる。判断を要する意訳の良し悪しは検査対象外。
#
# 使い方:
#   python3 tools/lint_translation.py                  # 全件検査
#   python3 tools/lint_translation.py --rfc 8446 9000  # 特定RFCのみ
#   python3 tools/lint_translation.py --check E001      # 特定チェックのみ
#   python3 tools/lint_translation.py --format summary  # 集計のみ
#   python3 tools/lint_translation.py --format json -o report.json
# ------------------------------------------------------------------------------

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

# ------------------------------------------------------------------------------
# チェック定義
# ------------------------------------------------------------------------------

CHECKS = {
    "E001": "識別子の大小文字破壊 (CamelCase識別子が原文と異なる表記になっている)",
    "E002": "RFC2119キーワードの強度不一致 (原文と異なる規範強度で訳されている)",
    "W003": "RFC2119キーワードの強度未表現 (訳文に規範強度が読み取れない)",
    "E004": "raw段落に翻訳が入っている (図表・コードは翻訳しない)",
    "W009": "識別子の表記破壊(機械判定不可) 原文内で表記が揺れており自動修正できない",
    "W005": "本文の文体違反 (ですます調でない)",
    "W006": "見出しの体言止め違反 (section_titleがですます調)",
    "E007": "タイトルのprefix違反 (title.jaが 'RFC XXXX - ' で始まらない)",
    "E008": "JSONスキーマ違反 (必須フィールドの欠落・型不正)",
}

# RFC2119キーワード -> 規範強度クラス
# 長いキーワードを先に並べる (MUST NOT を MUST より先に判定するため)
# (表示名, 正規表現, 規範強度)
# 否定語 NOT は大小文字を問わない。RFCによっては "MUST not" のように
# 小文字で書かれるが、意味は MUST NOT と同じ禁止である。
RFC2119 = [
    ("MUST NOT", r"\bMUST\s+[Nn][Oo][Tt]\b", "禁止"),
    ("SHALL NOT", r"\bSHALL\s+[Nn][Oo][Tt]\b", "禁止"),
    ("SHOULD NOT", r"\bSHOULD\s+[Nn][Oo][Tt]\b", "非推奨"),
    ("NOT RECOMMENDED", r"\bNOT\s+RECOMMENDED\b", "非推奨"),
    ("MUST", r"\bMUST\b", "必須"),
    ("SHALL", r"\bSHALL\b", "必須"),
    ("REQUIRED", r"\bREQUIRED\b", "必須"),
    ("RECOMMENDED", r"\bRECOMMENDED\b", "推奨"),
    ("SHOULD", r"\bSHOULD\b", "推奨"),
    ("OPTIONAL", r"\bOPTIONAL\b", "任意"),
    ("MAY", r"\bMAY\b", "任意"),
]

# 原文に含まれる否定表現。
# "MUST reject" / "MUST be absent" / "MUST X but not Y" のように、
# 肯定形のキーワードでも意味は禁止になる文がある。この場合に訳文が
# 「〜してはなりません」となるのは正しい訳であり、誤訳ではない。
EN_NEGATION = re.compile(
    r"\b(not|never|no longer|be no|no|absent|cannot|refrain|avoid|omit|exclude|without|"
    r"prohibit\w*|forbid\w*|reject\w*|disallow\w*|deny|denied)\b", re.IGNORECASE)

# 原文中に RFC2119キーワード以外の規範的な形容詞/副詞が含まれる場合、訳文の
# 規範語彙がその語に由来する可能性があり、キーワードとの対応を一意に断定
# できない (例: "others MAY be used" と同じ文中の "recommended")。
OTHER_NORMATIVE_WORDS = re.compile(
    r"\b(recommended|discouraged|desirable|undesirable|mandatory|preferred|advisable)\b",
    re.IGNORECASE)

# 規範強度クラス -> 日本語表現のパターン
#
# 「必要があります/がある」系は、このコーパスではMUST/SHOULDのどちらの訳にも
# 実際に使われており、語彙だけでは強度を一意に判別できない
# (W003調査で判明、2026-08-08)。両方のtierに登録し「強度不明だが規範性は
# ある」として扱う。ただし禁止/非推奨tierには入れない: 「持っている必要が
# あります」(誤訳=肯定) と「持たない必要があります」(正しい=二重否定でMUST
# NOT相当) を部分一致では区別できず、後者を許すと前者のような否定抜け誤訳を
# 隠してしまうため。禁止/非推奨側は個別レビューでE002として拾う運用とする。
_NECESSITY = [r"必要があ", r"必要です"]
# 「〜ないでください」は動詞語幹を問わず (送信し/含め/渡さ/変更し等) MUST NOT/
# SHOULD NOTの訳に広く使われるため、活用部分を含めない語尾一致にする。
_PROHIBITION_REQUEST = [r"ないでください"]
# 「ものとします」はSHALL/SHALL NOTどちらの訳にも使われる形式ばった言い回し
# だが、動詞側が既に否定形になっているケース (例:「〜されないものとします」
# =SHALL NOT) が大半のため、必要があ系と異なり両tierに登録して問題ない。
_SHALL_FORMAL = [r"ものとします"]

STRENGTH_PATTERNS = {
    "必須": [
        r"しなければなりません", r"なければなりません", r"ねばなりません",
        # 「しなければならない」は受身/他動詞語幹 (省略されなければならない 等) を
        # 拾えないため、し-プレフィックスなしの平叙形も登録する
        # (旧「しなければならない」を包含するため削除)。
        r"なければならない",
        r"必要とします",
        # 「必須」は日本語で「必須の/必須です/必須である」以外に「必須属性」
        # 「（必須）」のような名詞複合・ラベル形でも使われ、多義性が低く
        # 誤爆リスクも小さいため裸の部分一致で登録する。
        r"必須",
        *_NECESSITY, *_SHALL_FORMAL,
    ],
    # 注: 「禁止されています」「できます」は記述的な文でも多用され、規範表現の
    # 判定材料にすると誤検知が多発するため、意図的に含めない。
    "禁止": [
        r"てはなりません", r"てはいけません", r"てはならない", r"てはならず",
        # む/ぶ/ぬ語幹の動詞 (含む→含んで、読む→読んで 等) は音便でて形が
        # 「んで」になるため、「ては」パターンでは拾えない。
        r"んではなりません", r"んではいけません", r"んではならない", r"んではならず",
        r"しないものとします", *_PROHIBITION_REQUEST, *_SHALL_FORMAL,
    ],
    "推奨": [
        r"べきです", r"べきである",
        r"することが望ましい", r"のが望ましい", r"お勧めします",
        r"した方がよい", r"したほうがよい", r"はずです", r"はずである",
        # 「推奨」も「必須」と同様、名詞複合・ラベル形 (推奨値/推奨DSCP/(推奨) 等)
        # を拾うため裸の部分一致にする。
        r"推奨",
        *_NECESSITY,
    ],
    "非推奨": [
        r"べきではありません", r"べきではない", r"推奨されません",
        r"推奨されない", r"望ましくありません", *_PROHIBITION_REQUEST,
    ],
    "任意": [
        # 「し」プレフィックス限定だと受身/他動詞語幹 (共有されてもよい 等) を
        # 拾えないため、語尾のみのパターンにする。
        r"てもよい", r"てもかまいません", r"ても構いません",
        r"任意です", r"任意である", r"選択できます", r"することもできます",
        r"場合があります", r"オプションです", *_NECESSITY,
    ],
}

# 「オプションの」「任意の」はOPTIONAL/MAY自身の段落 (例: "An OPTIONAL <X>
# element") を正しく識別する分には有用だが、他のキーワードの段落で
# 「any/arbitrary」や「オプション (RFC2119のOPTIONALとは無関係の一般名詞)」
# として無関係に現れ、E002の誤検知を招くことが実証済み (2026-08-08)。
# そのため、自分の期待強度を確認する has_expected でのみ使用し、他の強度
# との不一致を断定する診断ループ (STRENGTH_PATTERNS) には含めない。
CONFIRM_ONLY_PATTERNS = {
    # 「(オプション)」のような丸括弧付きの裸ラベルは、見出しや属性一覧で
    # "(OPTIONAL)" をそのまま訳した形として頻出する。括弧で囲まれている
    # ことで一般名詞の「オプション」との衝突リスクが低いため、確認専用
    # パターンとして追加する。
    "任意": [r"オプションの", r"任意の", r"[（(]オプション[）)]"],
}

# 訳文中の明示注釈 (例: 「〜しなければなりません (MUST)」)
ANNOTATION_RE = re.compile(
    r"[（(]\s*(MUST NOT|SHALL NOT|SHOULD NOT|NOT RECOMMENDED|MUST|SHALL|REQUIRED|RECOMMENDED|SHOULD|OPTIONAL|MAY)\s*[）)]"
)

# 原文中の「非規範的な否定」表現。RFC2119の判定でノイズになるため検出したら
# その段落は E002/W003 の対象外にする (例: "Servers are not required to ...")
NON_NORMATIVE_NEGATION = re.compile(
    r"\b(not required|need not|no need|not necessary|is not mandatory|does not have to|do not have to)\b",
    re.IGNORECASE,
)

# 「a MUST」「a SHOULD NOT」のように冠詞つきで名詞的に使われるRFC2119キーワードは、
# その段落自身が発する規範的指示ではなく、他所のルールへの言及(例: "this would
# violate a SHOULD NOT in Section 3.5") であることが多い。この場合は訳文の強度と
# 比較する対象がそもそも存在しないため、検査対象から外す。
REFERENTIAL_KEYWORD_RE = re.compile(
    r"\b(?:a|an)\s+(?:MUST\s+NOT|SHALL\s+NOT|SHOULD\s+NOT|NOT\s+RECOMMENDED|"
    r"MUST|SHALL|REQUIRED|RECOMMENDED|SHOULD|OPTIONAL|MAY)\b"
)

# CamelCase識別子。
# 「2文字目以降に大文字が現れる」ことを必須にして、単に文頭が大文字なだけの
# 一般英単語 (Trust, License, Subject など) を識別子と誤認しないようにする。
#   digitalSignature / SignerInfo / smLaunchOwner / CertReqMsg -> 識別子
#   Trust / License / Subject / Password                       -> 対象外
CAMEL_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*[a-z0-9_][A-Z][A-Za-z0-9_]*\b")

# 表記ゆれ判定用。CamelCaseに限らず全ての英数字トークンを拾う。
# CAMEL_RE だけで判定すると、同じ識別子の全小文字版・全大文字版を見落とす。
#   例) "CMSG_DATA() ... the cmsg_data[] member ..."
#       CAMEL_RE は CMSG_DATA しか拾わないため、原文に小文字版が併存すること
#       に気づけず、訳文の cmsg_data を CMSG_DATA に誤変換してしまう。
ALL_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\b")

# URL・メールアドレス。この中の文字列は識別子照合の対象外にする
# (例: trustee.ietf.org/license-info が "Trust" や "License" に誤マッチする)
URL_RE = re.compile(r"(https?://\S+|\b[\w.\-]+@[\w.\-]+\b|\b[\w\-]+\.(?:ietf|org|com|net|edu)\b\S*)")

# 識別子として扱わない一般英単語 (CamelCaseだが技術識別子ではないもの)
CAMEL_STOPWORDS = {
    "IPv4", "IPv6", "IPsec", "IDs", "OKs", "NACKs", "ACKs", "URIs", "URLs",
    "RFCs", "APIs", "MTUs", "TLVs", "PDUs", "OIDs", "CAs", "RAs",
}

# 本文がですます調でないと判定するパターン (文末)
PLAIN_FORM_RE = re.compile(r"(である|であった|だった|していた|(?<!ませ)んだ)。\s*$")

# 箇条書きの先頭記号。AGENTS.mdの規約上、箇条書きはですます調の対象外。
# trans_rfc.py が翻訳時に使うパターンと同じものを用いる。
BULLET_RE = re.compile(
    r"^([\-o\*\+\$] |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |\(?[0-9a-z]\) |"
    r"\[[0-9a-z]{1,2}\] |[a-z]\. )")

# 見出しがですます調になっているパターン
TITLE_MASU_RE = re.compile(r"(ます|です|ました|ません)。?\s*$")

JP_CHAR_RE = re.compile(r"[ぁ-んァ-ヶ一-龠]")


class Finding:
    __slots__ = ("code", "path", "rfc", "index", "detail", "en", "ja")

    def __init__(self, code, path, rfc, index, detail, en="", ja=""):
        self.code = code
        self.path = path
        self.rfc = rfc
        self.index = index
        self.detail = detail
        self.en = en
        self.ja = ja

    def to_dict(self):
        return {
            "code": self.code,
            "rfc": self.rfc,
            "path": self.path,
            "index": self.index,
            "detail": self.detail,
            "en": self.en[:200],
            "ja": self.ja[:200],
        }


# ------------------------------------------------------------------------------
# 個別チェック
# ------------------------------------------------------------------------------

def ambiguous_lowers(en_clean):
    """原文内で同じ綴りが複数の表記で現れるトークンの集合(小文字化キー)。
    どちらの表記に合わせるべきか決まらないため、検出・修正の対象外にする。
    例) CMSG_DATA と cmsg_data が併存する段落"""
    by_lower = {}
    for t in ALL_TOKEN_RE.findall(en_clean):
        by_lower.setdefault(t.lower(), set()).add(t)
    return {k for k, v in by_lower.items() if len(v) > 1}


def check_identifier_case(en, ja):
    """E001: 原文のCamelCase識別子が、訳文で異なる大小文字表記になっていないか。

    誤検知を避けるため次を守る:
      - URL/メールアドレス内の文字列は照合対象から除く
      - 訳文側も語境界で一致した場合のみ「表記が壊れている」と判定する
        (例: 'Trust' が 'trustee' の一部にマッチするのを防ぐ)
      - 原文内で表記が揺れている識別子は対象外にする
        (例: CMSG_DATA と cmsg_data の併存)
    """
    en_clean = URL_RE.sub(" ", en)
    ja_clean = URL_RE.sub(" ", ja)
    ambiguous = ambiguous_lowers(en_clean)
    variants = {}
    for t in ALL_TOKEN_RE.findall(en_clean):
        variants.setdefault(t.lower(), set()).add(t)
    problems = []
    unresolvable = []
    for tok in dict.fromkeys(CAMEL_RE.findall(en_clean)):
        if tok in CAMEL_STOPWORDS or len(tok) < 4:
            continue
        if tok.lower() in ambiguous:
            # 原文内で表記が揺れているため、どの表記に直すべきか機械判定できない。
            # ただし訳文がどの表記とも一致しない場合は壊れているので別枠で報告する。
            m = re.search(
                r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])",
                ja_clean, re.IGNORECASE)
            if m and m.group(0) not in variants[tok.lower()]:
                unresolvable.append((tok, m.group(0), sorted(variants[tok.lower()])))
            continue
        # 正しい表記で存在すればOK (語境界で確認)
        if re.search(r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])", ja_clean):
            continue
        # 大小文字を無視すると語境界で一致する = 表記が壊れている
        m = re.search(
            r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])", ja_clean, re.IGNORECASE
        )
        if m:
            problems.append((tok, m.group(0)))
    return problems, unresolvable


def detect_rfc2119(en):
    """原文に含まれるRFC2119キーワードを検出し、(キーワード, 強度)のリストを返す。
    長いキーワードを優先し、重複カウントを避ける。"""
    found = []
    masked = en
    for kw, pattern, strength in RFC2119:
        for _ in re.finditer(pattern, masked):
            found.append((kw, strength))
        masked = re.sub(pattern, "_" * 4, masked)
    return found


def is_single_sentence(en):
    """原文が単文か。略語のピリオド (e.g. / i.e. / Sec. / RFC 2119.) を除いて
    文末ピリオドが1つだけなら単文とみなす。
    " -- " やセミコロンで繋がれた独立節も、キーワードと無関係な節の規範語彙
    を拾って誤検知するため単文として扱わない。"""
    if " -- " in en or ";" in en:
        return False
    s = re.sub(r"\b(?:e\.g|i\.e|etc|vs|cf|Sec|Fig|No|Dr|Mr|Ms|St|approx)\.", " ", en)
    s = re.sub(r"\b[A-Z]\.", " ", s)          # 頭文字 (J. Smith)
    s = re.sub(r"\d+\.\d+", " ", s)           # バージョン・節番号
    return len(re.findall(r"[.!?](?:\s|$)", s.strip())) <= 1


def check_rfc2119(en, ja):
    """E002/W003: 規範強度が正しく訳文に反映されているか。
    誤検知を避けるため、原文にRFC2119キーワードがちょうど1個だけの段落に限定する。"""
    if NON_NORMATIVE_NEGATION.search(en):
        return None
    if REFERENTIAL_KEYWORD_RE.search(en):
        return None
    found = detect_rfc2119(en)
    if len(found) != 1:
        return None
    kw, expected = found[0]

    # 明示注釈があれば、それが正しいか見るだけでよい
    ann = ANNOTATION_RE.search(ja)
    if ann:
        ann_kw = re.sub(r"\s+", " ", ann.group(1)).upper()
        if ann_kw == kw:
            return None
        return ("E002", f"注釈不一致: 原文 {kw} に対し訳文の注釈は ({ann_kw})")

    confirm_patterns = STRENGTH_PATTERNS[expected] + CONFIRM_ONLY_PATTERNS.get(expected, [])
    has_expected = any(re.search(p, ja) for p in confirm_patterns)
    if has_expected:
        return None

    # 「強度不一致(E002)」と断定できるのは、原文が単文で、訳文中の規範表現が
    # そのキーワードに対応すると一意に決まる場合に限る。複数文の段落や、
    # "recommended"/"discouraged" のようなRFC2119キーワード以外の規範的な語を
    # 含む段落では、別の語の訳を誤って拾うため、断定せず W003 に落とす。
    if is_single_sentence(en) and not OTHER_NORMATIVE_WORDS.search(en):
        for strength, patterns in STRENGTH_PATTERNS.items():
            if strength == expected:
                continue
            # 「必須」と「任意」は表現が重なりやすいので誤検知を避ける
            if expected == "必須" and strength == "任意":
                continue
            # 肯定形キーワード + 原文の否定表現 -> 訳文が禁止/非推奨になるのは正しい。
            # 例) "MUST be absent" -> 「存在してはいけません」
            #     "MUST signal X but not execute Y" -> 「実行してはなりません」
            # 「MAY NOT」はRFC2119上未定義の組み合わせで、"MAY"として検出されるが
            # 実質「〜しないことが許容される」という弱い禁止/非推奨に近い意味で
            # 使われることが多いため、任意(MAY)もこの許容対象に含める。
            if (expected in ("必須", "推奨", "任意") and strength in ("禁止", "非推奨")
                    and EN_NEGATION.search(en)):
                continue
            if any(re.search(p, ja) for p in patterns):
                return ("E002", f"強度不一致: 原文 {kw}({expected}) に対し訳文は{strength}相当")

    return ("W003", f"強度未表現: 原文 {kw}({expected}) の規範強度が訳文から読み取れない")


# ------------------------------------------------------------------------------
# ファイル単位の検査
# ------------------------------------------------------------------------------

def lint_file(path, enabled):
    findings = []
    rfc = os.path.basename(path).replace("-trans.json", "")
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        return [Finding("E008", path, rfc, -1, f"JSONパース失敗: {e}")]

    # --- タイトル ---
    title = obj.get("title")
    if not isinstance(title, dict):
        findings.append(Finding("E008", path, rfc, -1, "title オブジェクトがない"))
    else:
        ja_title = title.get("ja", "")
        num = re.sub(r"\D", "", rfc)
        if "E007" in enabled and ja_title and not ja_title.startswith(f"RFC {num} - "):
            findings.append(Finding("E007", path, rfc, -1,
                                    "title.ja が 'RFC %s - ' で始まらない" % num, "", ja_title))

    contents = obj.get("contents")
    if not isinstance(contents, list):
        findings.append(Finding("E008", path, rfc, -1, "contents 配列がない"))
        return findings

    for i, c in enumerate(contents):
        if not isinstance(c, dict):
            findings.append(Finding("E008", path, rfc, i, "contents要素がオブジェクトでない"))
            continue
        en = c.get("text", "") or ""
        ja = c.get("ja", "") or ""
        is_raw = c.get("raw") is True
        is_title = c.get("section_title") is True

        if "E008" in enabled and "text" not in c:
            findings.append(Finding("E008", path, rfc, i, "text フィールドがない"))

        # --- raw段落 ---
        if is_raw:
            if "E004" in enabled and ja.strip():
                findings.append(Finding("E004", path, rfc, i,
                                        "raw=true の段落に翻訳が入っている", en, ja))
            continue

        if not en or not ja:
            continue
        if not JP_CHAR_RE.search(ja):
            continue  # 参考文献・著者情報など、原文のまま残すのが正しい段落

        # --- 識別子 ---
        if "E001" in enabled or "W009" in enabled:
            problems, unresolvable = check_identifier_case(en, ja)
            if "E001" in enabled:
                for tok, actual in problems:
                    findings.append(Finding("E001", path, rfc, i,
                                            f"識別子 '{tok}' が訳文で '{actual}' になっている", en, ja))
            if "W009" in enabled:
                for tok, actual, variants in unresolvable:
                    findings.append(Finding(
                        "W009", path, rfc, i,
                        f"識別子が訳文で '{actual}' になっているが、原文に "
                        f"{variants} が併存するため自動判定不可", en, ja))

        # --- RFC2119 ---
        if "E002" in enabled or "W003" in enabled:
            r = check_rfc2119(en, ja)
            if r and r[0] in enabled:
                findings.append(Finding(r[0], path, rfc, i, r[1], en, ja))

        # --- 文体 ---
        if is_title:
            if "W006" in enabled and TITLE_MASU_RE.search(ja):
                findings.append(Finding("W006", path, rfc, i,
                                        "見出しが体言止めでない", en, ja))
        else:
            # 箇条書きは規約上ですます調の対象外なので除外する
            if ("W005" in enabled and len(ja) >= 30 and PLAIN_FORM_RE.search(ja)
                    and not BULLET_RE.match(en) and not BULLET_RE.match(ja)):
                findings.append(Finding("W005", path, rfc, i,
                                        "本文がですます調でない", en, ja))

    return findings


# ------------------------------------------------------------------------------
# エントリポイント
# ------------------------------------------------------------------------------

def collect_paths(rfcs, dirs=None):
    if dirs:
        paths = []
        for d in dirs:
            paths.extend(glob.glob(f"data/{d}/rfc*-trans.json"))
        return sorted(paths)
    if rfcs:
        paths = []
        for n in rfcs:
            n = str(n)
            hit = glob.glob(f"data/*/rfc{n}-trans.json")
            if not hit:
                print(f"[-] not found: rfc{n}", file=sys.stderr)
            paths.extend(hit)
        return sorted(paths)
    return sorted(glob.glob("data/*/rfc*-trans.json"))


def main():
    p = argparse.ArgumentParser(description="RFC翻訳品質linter")
    p.add_argument("--rfc", nargs="*", help="対象RFC番号 (省略時は全件)")
    p.add_argument("--dir", nargs="*", help="対象データディレクトリ (例: 8000 9000)")
    p.add_argument("--check", nargs="*", help="有効にするチェックコード (省略時は全件)")
    p.add_argument("--format", choices=["text", "summary", "json"], default="summary")
    p.add_argument("-o", "--output", help="出力先ファイル")
    p.add_argument("--max-examples", type=int, default=5, help="text形式で表示する件数/チェック")
    p.add_argument("--fail-on-error", action="store_true",
                   help="Eコードの検出があれば終了コード1を返す (CI用)")
    args = p.parse_args()

    enabled = set(args.check) if args.check else set(CHECKS)
    unknown = enabled - set(CHECKS)
    if unknown:
        print(f"[-] 未知のチェックコード: {sorted(unknown)}", file=sys.stderr)
        return 2

    paths = collect_paths(args.rfc, args.dir)
    if not paths:
        print("[-] 対象ファイルがありません", file=sys.stderr)
        return 2

    all_findings = []
    per_rfc = Counter()
    for path in paths:
        fs = lint_file(path, enabled)
        all_findings.extend(fs)
        if fs:
            per_rfc[os.path.basename(path).replace("-trans.json", "")] = len(fs)

    by_code = Counter(f.code for f in all_findings)
    by_bucket = defaultdict(Counter)
    for f in all_findings:
        num = re.sub(r"\D", "", f.rfc)
        if num:
            by_bucket[(int(num) // 1000) * 1000][f.code] += 1

    out = []
    if args.format == "json":
        payload = {
            "files_scanned": len(paths),
            "total_findings": len(all_findings),
            "by_code": dict(by_code),
            "findings": [f.to_dict() for f in all_findings],
        }
        out.append(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        out.append(f"検査ファイル数: {len(paths)}")
        out.append(f"検出総数: {len(all_findings)}")
        out.append("")
        out.append("== チェック別 ==")
        for code in sorted(CHECKS):
            if code in enabled:
                out.append(f"  {code} {by_code.get(code, 0):>7}  {CHECKS[code]}")
        if by_bucket:
            out.append("")
            out.append("== RFC番号帯別 ==")
            codes = [c for c in sorted(CHECKS) if by_code.get(c)]
            out.append("  " + "帯".ljust(8) + "".join(c.rjust(9) for c in codes))
            for b in sorted(by_bucket):
                row = "  " + str(b).ljust(8)
                row += "".join(str(by_bucket[b].get(c, 0)).rjust(9) for c in codes)
                out.append(row)
        if per_rfc:
            out.append("")
            out.append("== 検出件数の多いRFC (上位15) ==")
            for name, n in per_rfc.most_common(15):
                out.append(f"  {name}: {n}")

        if args.format == "text":
            out.append("")
            shown = Counter()
            for f in all_findings:
                if shown[f.code] >= args.max_examples:
                    continue
                shown[f.code] += 1
                out.append(f"[{f.code}] {f.rfc} #{f.index}: {f.detail}")
                if f.en:
                    out.append(f"    EN: {f.en[:160]}")
                if f.ja:
                    out.append(f"    JA: {f.ja[:160]}")

    text = "\n".join(out)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fp:
            fp.write(text + "\n")
        print(f"[+] wrote {args.output}")
    else:
        print(text)

    if args.fail_on_error and any(c.startswith("E") for c in by_code):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
