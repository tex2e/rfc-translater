# ------------------------------------------------------------------------------
# 翻訳の機械的修正
#
# lint_translation.py が検出した欠陥のうち、判断を要さず決定的に直せるものだけを
# 自動修正する。曖昧なケースは「直さずに残す」方針で、誤修正を出さないことを優先する。
#
#   E001: 訳文中の識別子の表記を、原文の表記に戻す
#         例) Smlaunchowner -> smLaunchOwner
#   W006: 見出しのですます調を体言止めに変換する
#         例) `hello'コマンドを処理します -> `hello'コマンドの処理
#         サ変動詞の見出しのみ対象。それ以外は変換せず残す。
#
# 使い方:
#   python3 tools/fix_translation.py --check E001 --dry-run           # 変更内容の確認
#   python3 tools/fix_translation.py --check E001 --dir 3000          # 帯を指定して適用
#   python3 tools/fix_translation.py --check E001 W006 --rfc 3179     # RFC指定で適用
#
# JSONは json.dump(ensure_ascii=False, indent=2) で書き戻すため、
# src/domain/services/rfcfile.py の出力形式と完全に一致する。
# ------------------------------------------------------------------------------

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lint_translation import (  # noqa: E402
    CAMEL_RE, CAMEL_STOPWORDS, URL_RE, ambiguous_lowers, BULLET_RE,
)

# --- W006: 体言止めへの変換パターン ---
# サ変名詞 (漢字2〜6文字) + します/する で終わる見出しのみを対象にする。
# 「明らかにします」のようにひらがなを含む語尾は対象外（誤変換を避ける）。
SAHEN = r"[一-龠々]{2,6}"
TAIGEN_PATTERNS = [
    # 「Xを処理します」 -> 「Xの処理」
    (re.compile(rf"^(.*?)を({SAHEN})(?:します|する|しています)$"), r"\1の\2"),
    # 「Xについて説明します」 -> 「Xの説明」
    (re.compile(rf"^(.*?)について({SAHEN})(?:します|する)$"), r"\1の\2"),
    # 「Xに対する処理を行います」 -> 「Xに対する処理」
    (re.compile(r"^(.*?)を行(?:います|う)$"), r"\1"),
    # 「Xに更新されます」「Xに署名しています」 -> 「Xに更新」「Xに署名」
    # サ変名詞が語尾に直接続く形。助詞「を」を伴わないため「の」は挿入しない。
    (re.compile(rf"^(.*?)({SAHEN})(?:されています|されます|しています|します|する)$"), r"\1\2"),
]

# 変換結果が「〜が<名詞>」で終わるものを弾くための判定
DANGLING_GA_RE = re.compile(r"が[一-龠々]{2,6}$")

# --- W005: である調 -> ですます調 ---
# 文末(「。」の直前)のみを対象にする。「〜であるため」のような文中の用法は
# 「。」が続かないため影響を受けない。
DESU_PATTERNS = [
    (re.compile(r"であった。"), "でした。"),
    (re.compile(r"していた。"), "していました。"),
    (re.compile(r"である。"), "です。"),
    (re.compile(r"だった。"), "でした。"),
]

# 見出し先頭の番号 (「6.1.1. 」「付録A. 」など) は変換対象から外して温存する
HEADING_NUM_RE = re.compile(r"^((?:付録)?[A-Z0-9]+(?:\.[0-9]+)*\.?\s+)(.*)$", re.S)


def fix_identifier_case(en, ja):
    """E001: 訳文中の識別子表記を原文の表記に戻す。
    原文内で同じ綴りが複数の表記で現れる場合は、どちらに合わせるべきか決まらないため
    修正せずスキップする。"""
    en_clean = URL_RE.sub(" ", en)
    tokens = CAMEL_RE.findall(en_clean)

    # 原文内で表記が揺れている綴りを調べる。
    # CamelCaseトークンだけでなく全トークンを見ないと、全小文字版・全大文字版の
    # 併存を見落とす (例: CMSG_DATA と cmsg_data)。
    ambiguous = ambiguous_lowers(en_clean)

    new_ja = ja
    fixed = []
    for tok in dict.fromkeys(tokens):
        if tok in CAMEL_STOPWORDS or len(tok) < 4:
            continue
        if tok.lower() in ambiguous:
            continue  # 原文内で表記が揺れている -> 曖昧なので触らない

        pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(tok) + r"(?![A-Za-z0-9_])",
                         re.IGNORECASE)

        # URL部分は保護する (URL内の大小文字は変えてはいけない)
        segments = []
        last = 0
        for m in URL_RE.finditer(new_ja):
            segments.append((new_ja[last:m.start()], True))
            segments.append((m.group(0), False))
            last = m.end()
        segments.append((new_ja[last:], True))

        rebuilt = []
        changed_here = False
        for seg, editable in segments:
            if not editable:
                rebuilt.append(seg)
                continue

            def _sub(m):
                nonlocal changed_here
                if m.group(0) == tok:
                    return m.group(0)
                changed_here = True
                return tok

            rebuilt.append(pat.sub(_sub, seg))
        if changed_here:
            new_ja = "".join(rebuilt)
            fixed.append(tok)

    return new_ja, fixed


def fix_taigendome(ja):
    """W006: 見出しのですます調を体言止めに変換する。
    変換できないものは None を返し、元の訳文を維持する。"""
    m = HEADING_NUM_RE.match(ja)
    prefix, body = (m.group(1), m.group(2)) if m else ("", ja)
    body = body.strip()
    if not body:
        return None
    # 主題の「は」を含む見出しは名詞句ではなく文。体言止めにすると
    # 「Xは〜の消費」のように非文になるため、機械変換の対象外とする。
    if "は" in body:
        return None
    for pat, repl in TAIGEN_PATTERNS:
        if pat.match(body):
            new_body = pat.sub(repl, body)
            if new_body == body or not new_body.strip():
                continue
            # 主語マーカー「が」が述語を失う変換は行わない。
            # 「同等のアルゴリズムが許可されています」->「同等のアルゴリズムが許可」は
            # 体言止めではなく係り先のない断片になり、元より読みにくい。
            if DANGLING_GA_RE.search(new_body):
                return None
            return prefix + new_body
    return None


def fix_desumasu(ja):
    """W005: 文末のである調をですます調に変換する。
    段落内の全ての文末を変換し、最後の文だけ直す中途半端な状態を作らない。"""
    new = ja
    for pat, repl in DESU_PATTERNS:
        new = pat.sub(repl, new)
    return new if new != ja else None


def process_file(path, checks, dry_run, samples, stats):
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except Exception as e:
        print(f"[-] {path}: JSON読み込み失敗 {e}", file=sys.stderr)
        stats["read_error"] += 1
        return False

    contents = obj.get("contents")
    if not isinstance(contents, list):
        return False

    changed = False

    # --- E007: title.ja の "RFC XXXX - " prefix ---
    if "E007" in checks and isinstance(obj.get("title"), dict):
        num = re.sub(r"\D", "", os.path.basename(path))
        ja_title = obj["title"].get("ja") or ""
        if ja_title and not ja_title.startswith(f"RFC {num} - "):
            new_title = f"RFC {num} - {ja_title}"
            if len(samples["E007"]) < 12:
                samples["E007"].append((os.path.basename(path), None, ja_title[:90], new_title[:90]))
            obj["title"]["ja"] = new_title
            stats["E007"] += 1
            changed = True

    for c in contents:
        if not isinstance(c, dict):
            continue

        # --- E004: raw段落に翻訳が入っている ---
        if c.get("raw") is True:
            if "E004" in checks and (c.get("ja") or "").strip():
                if len(samples["E004"]) < 12:
                    samples["E004"].append((os.path.basename(path), None,
                                            (c.get("ja") or "")[:90], "(空文字)"))
                c["ja"] = ""
                stats["E004"] += 1
                changed = True
            continue

        en = c.get("text", "") or ""
        ja = c.get("ja", "") or ""
        if not en or not ja:
            continue

        if "E001" in checks:
            new_ja, fixed = fix_identifier_case(en, ja)
            if new_ja != ja:
                if len(samples["E001"]) < 12:
                    samples["E001"].append((os.path.basename(path), fixed, ja[:90], new_ja[:90]))
                stats["E001"] += len(fixed)
                c["ja"] = new_ja
                ja = new_ja
                changed = True

        if "W006" in checks and c.get("section_title") is True:
            new_ja = fix_taigendome(ja)
            if new_ja and new_ja != ja:
                if len(samples["W006"]) < 12:
                    samples["W006"].append((os.path.basename(path), None, ja[:90], new_ja[:90]))
                stats["W006"] += 1
                c["ja"] = new_ja
                changed = True
            elif new_ja is None and re.search(r"(ます|です)。?$", ja):
                stats["W006_skipped"] += 1

        # --- W005: 本文のである調 -> ですます調 ---
        # 見出しは体言止めが正しいので対象外。箇条書きも規約上ですます調の対象外。
        if ("W005" in checks and not c.get("section_title")
                and not BULLET_RE.match(en) and not BULLET_RE.match(ja)):
            new_ja = fix_desumasu(ja)
            if new_ja:
                if len(samples["W005"]) < 12:
                    samples["W005"].append((os.path.basename(path), None, ja[-90:], new_ja[-90:]))
                stats["W005"] += 1
                c["ja"] = new_ja
                changed = True

    if changed and not dry_run:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    return changed


def collect_paths(rfcs, dirs):
    if dirs:
        paths = []
        for d in dirs:
            paths.extend(glob.glob(f"data/{d}/rfc*-trans.json"))
        return sorted(paths)
    if rfcs:
        paths = []
        for n in rfcs:
            paths.extend(glob.glob(f"data/*/rfc{n}-trans.json"))
        return sorted(paths)
    return sorted(glob.glob("data/*/rfc*-trans.json"))


def main():
    p = argparse.ArgumentParser(description="翻訳の機械的修正")
    p.add_argument("--check", nargs="+", required=True,
                   choices=["E001", "E004", "E007", "W005", "W006"])
    p.add_argument("--rfc", nargs="*")
    p.add_argument("--dir", nargs="*")
    p.add_argument("--dry-run", action="store_true", help="ファイルを書き換えずに結果だけ表示")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    paths = collect_paths(args.rfc, args.dir)
    if not paths:
        print("[-] 対象ファイルがありません", file=sys.stderr)
        return 2

    checks = set(args.check)
    stats = Counter()
    samples = {k: [] for k in ("E001", "E004", "E007", "W005", "W006")}
    files_changed = 0

    for path in paths:
        if process_file(path, checks, args.dry_run, samples, stats):
            files_changed += 1

    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"{mode}対象ファイル: {len(paths)}  変更ファイル: {files_changed}")
    if "E001" in checks:
        print(f"  E001 識別子を修正: {stats['E001']} 箇所")
    if "E004" in checks:
        print(f"  E004 raw段落のjaを空に: {stats['E004']} 件")
    if "E007" in checks:
        print(f"  E007 タイトルprefixを付与: {stats['E007']} 件")
    if "W005" in checks:
        print(f"  W005 ですます調に変換: {stats['W005']} 段落")
    if "W006" in checks:
        print(f"  W006 体言止めに変換: {stats['W006']} 件")
        print(f"  W006 変換できず据え置き: {stats['W006_skipped']} 件 (要人手/AI対応)")
    if stats["read_error"]:
        print(f"  読み込み失敗: {stats['read_error']} 件")

    if not args.quiet:
        for code in ("E001", "E004", "E007", "W005", "W006"):
            if code in checks and samples[code]:
                print(f"\n== {code} 変換例 ==")
                for name, toks, before, after in samples[code]:
                    extra = f" {toks}" if toks else ""
                    print(f"  {name}{extra}")
                    print(f"    before: {before}")
                    print(f"    after : {after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
