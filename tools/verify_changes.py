# ------------------------------------------------------------------------------
# 一括修正の検証
#
# fix_translation.py などで data/*/rfc*-trans.json を一括変更したあと、
# その変更が意図した範囲に収まっているかを HEAD と比較して検証する。
#
# 目視サンプリングでは9万件規模の変更を検証しきれないため、
# 「全件に対して成り立つべき不変条件」を機械的に確認する方針をとる。
#
# 使い方:
#   python3 tools/verify_changes.py            # 検証サマリを表示
#   python3 tools/verify_changes.py --samples 20   # 変換例も表示
# ------------------------------------------------------------------------------

import argparse
import json
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict

JP_RE = re.compile(r"[ぁ-んァ-ヶ一-龠、。（）「」]")
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
HEADING_NUM_RE = re.compile(r"^((?:付録)?[A-Z0-9]+(?:\.[0-9]+)*\.?\s+)")
DANGLING_RE = re.compile(r"[がはをにでとやへも][一-龠々]{0,6}$")


def collect():
    """変更のあった全段落を (種別, ファイル, EN, 旧JA, 新JA) で返す"""
    out = subprocess.run(["git", "status", "--porcelain", "--", "data/"],
                         capture_output=True, text=True).stdout.splitlines()
    files = [l[3:].strip() for l in out if l.strip().endswith("-trans.json")]
    p = subprocess.Popen(["git", "cat-file", "--batch"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    rows, skipped = [], 0
    for f in files:
        try:
            cur = json.load(open(f, encoding="utf-8"))
        except Exception:
            skipped += 1
            continue
        p.stdin.write(f"HEAD:{f}\n".encode())
        p.stdin.flush()
        head = p.stdout.readline().decode().strip()
        if "missing" in head:
            skipped += 1
            continue
        size = int(head.split()[2])
        data = p.stdout.read(size)
        p.stdout.read(1)
        old = json.loads(data.decode("utf-8"))
        oc, cc = old.get("contents", []), cur.get("contents", [])
        if len(oc) != len(cc):
            skipped += 1
            continue
        for a, b in zip(oc, cc):
            oj = a.get("ja", "") or ""
            nj = b.get("ja", "") or ""
            if oj == nj:
                continue
            if b.get("raw") is True:
                kind = "raw"          # raw段落の ja 空化 (E004) は意図的な変更
            elif oj.lower() == nj.lower():
                kind = "case"
            elif b.get("section_title"):
                kind = "heading"      # 見出しの体言止め変換 (W006)
            else:
                kind = "body"         # 本文の文体変換 (W005)
            rows.append((kind, f.split("/")[-1], b.get("text", "") or "", oj, nj,
                         bool(b.get("section_title"))))
    p.stdin.close()
    p.wait()
    return rows, len(files), skipped


def main():
    ap = argparse.ArgumentParser(description="一括修正の検証")
    ap.add_argument("--samples", type=int, default=0, help="表示する変換例の件数")
    args = ap.parse_args()

    rows, n_files, skipped = collect()
    case = [r for r in rows if r[0] == "case"]
    rew = [r for r in rows if r[0] == "heading"]
    body = [r for r in rows if r[0] == "body"]
    raws = [r for r in rows if r[0] == "raw"]

    print(f"変更ファイル: {n_files}  (比較不能: {skipped})")
    print(f"変更段落: {len(rows):,}")
    print(f"  大小文字のみ {len(case):,} / 見出し書き換え {len(rew):,} / "
          f"本文文体 {len(body):,} / raw空化 {len(raws):,}")

    fail = 0

    # --- 大小文字のみの変更に対する不変条件 ---
    print("\n== 大小文字変更の不変条件 ==")
    checks = [
        ("小文字化して不一致(文字自体が変化)", [r for r in case if r[3].lower() != r[4].lower()]),
        ("長さが変化", [r for r in case if len(r[3]) != len(r[4])]),
        ("日本語部分が変化", [r for r in case
                              if "".join(JP_RE.findall(r[3])) != "".join(JP_RE.findall(r[4]))]),
        ("原文にないトークンを導入",
         [r for r in case
          if (set(TOKEN_RE.findall(r[4])) - set(TOKEN_RE.findall(r[3])))
          - set(TOKEN_RE.findall(r[2]))]),
    ]
    for name, bad in checks:
        mark = "OK" if not bad else "NG"
        print(f"  [{mark}] {name}: {len(bad)}")
        fail += len(bad)
        for r in bad[:3]:
            print(f"        {r[1]}\n          旧: {r[3][:70]}\n          新: {r[4][:70]}")

    # --- 書き換え(体言止め変換)に対する不変条件 ---
    print("\n== 書き換えの不変条件 ==")

    def prefix(s):
        m = HEADING_NUM_RE.match(s)
        return m.group(1) if m else ""

    bad_pre = [r for r in rew if prefix(r[3]) != prefix(r[4])]
    print(f"  [{'OK' if not bad_pre else 'NG'}] 見出し番号が変化: {len(bad_pre)}")
    fail += len(bad_pre)

    bad_tail = [r for r in rew if DANGLING_RE.search(
        HEADING_NUM_RE.sub("", r[4]).rstrip()) and
        not re.search(r"[一-龠々ァ-ヶー]$", r[4].rstrip())]
    print(f"  [{'OK' if not bad_tail else 'NG'}] 助詞で終わる断片: {len(bad_tail)}")
    fail += len(bad_tail)
    for r in bad_tail[:5]:
        print(f"        {r[1]}\n          旧: {r[3][:60]}\n          新: {r[4][:60]}")

    empty = [r for r in rew if not HEADING_NUM_RE.sub("", r[4]).strip()]
    print(f"  [{'OK' if not empty else 'NG'}] 変換後が空: {len(empty)}")
    fail += len(empty)

    # --- 本文の文体変換 (W005) ---
    if body:
        print("\n== 本文の文体変換の不変条件 ==")
        # 文体変換は語尾のみを変える。文の数(「。」の数)が変わってはいけない。
        bad_sent = [r for r in body if r[3].count("。") != r[4].count("。")]
        print(f"  [{'OK' if not bad_sent else 'NG'}] 文の数が変化: {len(bad_sent)}")
        fail += len(bad_sent)
        # 変更箇所が語尾表現に限られているか
        allowed = [("である。", "です。"), ("であった。", "でした。"),
                   ("だった。", "でした。"), ("していた。", "していました。")]
        # 同じ段落に識別子の大小文字修正(E001)も入ることがあるため、
        # 語尾変換を適用したあとは大小文字を無視して比較する。
        bad_other = []
        for r in body:
            t = r[3]
            for a, bl in allowed:
                t = t.replace(a, bl)
            if t.lower() != r[4].lower():
                bad_other.append(r)
        print(f"  [{'OK' if not bad_other else 'NG'}] 語尾以外が変化: {len(bad_other)}")
        fail += len(bad_other)
        for r in bad_other[:3]:
            print(f"        {r[1]}\n          旧: {r[3][-70:]}\n          新: {r[4][-70:]}")

    # --- raw段落 (E004) ---
    if raws:
        print("\n== raw段落の不変条件 ==")
        bad_raw = [r for r in raws if r[4].strip()]
        print(f"  [{'OK' if not bad_raw else 'NG'}] ja が空文字になっていない: {len(bad_raw)}")
        fail += len(bad_raw)

    # 参考情報 (欠陥ではない)
    ends = Counter()
    for r in rew:
        t = r[4].rstrip()
        c = t[-1] if t else ""
        if re.match(r"[一-龠々]", c):
            ends["漢字"] += 1
        elif re.match(r"[ァ-ヶー]", c):
            ends["カタカナ"] += 1
        elif re.match(r"[ぁ-ん]", c):
            ends["ひらがな"] += 1
        else:
            ends["その他"] += 1
    print("\n  参考: 書き換え結果の末尾  " +
          " / ".join(f"{k} {v:,}" for k, v in ends.most_common()))
    drop = max((len(r[3]) - len(r[4]) for r in rew), default=0)
    print(f"  参考: 最大の文字数減      {drop} 文字")

    if args.samples:
        random.seed(0)
        print(f"\n== 書き換えの例 {args.samples} 件 ==")
        for r in random.sample(rew, min(args.samples, len(rew))):
            print(f"  EN: {r[2][:60]}\n   旧: {r[3][:56]}\n   新: {r[4][:56]}")

    print(f"\n{'検証NG: ' + str(fail) + ' 件' if fail else '検証OK: 不変条件違反なし'}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
