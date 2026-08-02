# ------------------------------------------------------------------------------
# 翻訳修正の優先順位付け
#
# 「どのRFCから直すべきか」を、次の2軸を掛け合わせて決める。
#
#   重要度 : 他のRFCから何回参照されているか (コーパス内の被引用数)
#            公開サイトのアクセス数が手元にないため、その代理指標として使う。
#            RFC2119, 5280, 3261, 8446 のような基盤RFCが上位に来る。
#   深刻度 : lint_translation.py の検出結果を重み付けした合計
#            規範強度の誤り(E002)を最重視し、W003は件数が多いため軽く扱う。
#
#   優先度 = 深刻度 x (1 + log2(1 + 被引用数))
#
# 使い方:
#   python3 tools/rank_rfcs.py --scan            # 全件スキャンしてキャッシュ作成
#   python3 tools/rank_rfcs.py --scan --dir 8000 # 帯ごとに分けてスキャン (再開可)
#   python3 tools/rank_rfcs.py --report          # キャッシュから優先順リストを出力
#   python3 tools/rank_rfcs.py --report --limit 50 -o worklist.md
#
# 修正が済んだRFCは、再スキャンすると検出数が減り自動的に順位が下がる。
# 進捗管理用の状態ファイルは持たない (linterの結果そのものが進捗)。
# ------------------------------------------------------------------------------

import argparse
import glob
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lint_translation import lint_file, CHECKS  # noqa: E402

CACHE = "tools/.rank_cache.json"

# 検出コードごとの深刻度の重み
WEIGHTS = {
    "E002": 10.0,   # 規範強度の誤り。実装可否の誤判断に直結する
    "E008": 5.0,    # スキーマ破損
    "E007": 3.0,    # タイトル規約違反
    "E004": 3.0,    # raw段落の汚染
    "E001": 1.0,    # 識別子の表記破壊
    "W006": 0.5,    # 見出しの体言止め
    "W005": 0.5,    # 文体
    "W003": 0.2,    # 強度未表現。件数が膨大なため軽く扱う
}

CITE_RE = re.compile(r"\[RFC\s?(\d{3,5})\]")


def scan(dirs=None):
    """対象ファイルを走査し、被引用数と検出数をキャッシュに追記する"""
    if dirs:
        paths = []
        for d in dirs:
            paths.extend(glob.glob(f"data/{d}/rfc*-trans.json"))
    else:
        paths = glob.glob("data/*/rfc*-trans.json")
    paths = sorted(paths)
    if not paths:
        print("[-] 対象ファイルがありません", file=sys.stderr)
        return 2

    cache = load_cache()
    cites = Counter(cache.get("citations", {}))
    files = cache.get("files", {})
    enabled = set(CHECKS)

    for i, path in enumerate(paths, 1):
        m = re.search(r"rfc(\d+)-trans", path)
        if not m:
            continue
        rid = m.group(1)
        try:
            obj = json.load(open(path, encoding="utf-8"))
        except Exception:
            obj = None

        # --- 被引用数の集計 ---
        if obj:
            # 同じ参照元RFCからの重複カウントを避けるため集合にする
            seen = set()
            for c in obj.get("contents", []):
                for t in CITE_RE.findall(c.get("text", "") or ""):
                    seen.add(t)
            seen.discard(rid)
            # 再スキャン時の二重計上を防ぐため、以前の寄与を取り消す
            for old in files.get(rid, {}).get("refs", []):
                if cites[old] > 0:
                    cites[old] -= 1
            for s in seen:
                cites[s] += 1
            refs = sorted(seen)
        else:
            refs = files.get(rid, {}).get("refs", [])

        # --- 検出数の集計 ---
        counts = Counter(f.code for f in lint_file(path, enabled))
        title = ""
        if obj and isinstance(obj.get("title"), dict):
            title = obj["title"].get("ja") or obj["title"].get("text") or ""

        files[rid] = {"path": path, "title": title[:120],
                      "counts": dict(counts), "refs": refs}

        if i % 200 == 0:
            print(f"  ... {i}/{len(paths)}", file=sys.stderr)

    save_cache({"citations": dict(cites), "files": files})
    print(f"[+] {len(paths)} ファイルをスキャンし {CACHE} を更新しました")
    return 0


def load_cache():
    if os.path.exists(CACHE):
        try:
            return json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_cache(data):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def severity(counts):
    return sum(WEIGHTS.get(k, 0) * v for k, v in counts.items())


def report(args):
    cache = load_cache()
    files = cache.get("files")
    if not files:
        print(f"[-] キャッシュがありません。先に --scan を実行してください。", file=sys.stderr)
        return 2
    cites = cache.get("citations", {})

    rows = []
    for rid, info in files.items():
        counts = info.get("counts", {})
        if args.check:
            counts = {k: v for k, v in counts.items() if k in args.check}
        sev = severity(counts)
        if sev <= 0:
            continue
        n_cite = int(cites.get(rid, 0))
        imp = 1 + math.log2(1 + n_cite)
        if args.sort == "severity":
            score = sev
        elif args.sort == "importance":
            score = imp
        else:
            score = sev * imp
        rows.append((score, sev, n_cite, rid, info, counts))

    rows.sort(key=lambda r: -r[0])
    rows = rows[: args.limit]

    codes = ["E002", "E001", "E004", "E007", "E008", "W003", "W006", "W005"]
    if args.check:
        codes = [c for c in codes if c in args.check]

    out = []
    out.append(f"# 翻訳修正 優先順リスト (上位 {len(rows)} 件)")
    out.append("")
    out.append(f"- 並び順: `{args.sort}`  (優先度 = 深刻度 x (1 + log2(1 + 被引用数)))")
    out.append(f"- 深刻度の重み: " + ", ".join(f"{k}={v:g}" for k, v in WEIGHTS.items()))
    out.append("")
    out.append("| # | RFC | 被引用 | 優先度 | " + " | ".join(codes) + " | タイトル |")
    out.append("|---|---|---|---|" + "---|" * len(codes) + "---|")
    for i, (score, sev, n_cite, rid, info, counts) in enumerate(rows, 1):
        cells = " | ".join(str(counts.get(c, 0)) for c in codes)
        title = info.get("title", "").replace("|", "/")
        out.append(f"| {i} | RFC{rid} | {n_cite} | {score:.0f} | {cells} | {title} |")

    out.append("")
    out.append("## 作業コマンド")
    out.append("")
    out.append("```sh")
    for _, _, _, rid, _, _ in rows[:10]:
        out.append(f"python3 tools/lint_translation.py --rfc {rid} --format text")
    out.append("```")

    text = "\n".join(out)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"[+] wrote {args.output}")
    else:
        print(text)
    return 0


def main():
    p = argparse.ArgumentParser(description="翻訳修正の優先順位付け")
    p.add_argument("--scan", action="store_true", help="スキャンしてキャッシュを更新")
    p.add_argument("--report", action="store_true", help="キャッシュから優先順リストを出力")
    p.add_argument("--dir", nargs="*", help="スキャン対象ディレクトリ (例: 8000 9000)")
    p.add_argument("--check", nargs="*", help="対象とする検出コード (例: E002)")
    p.add_argument("--sort", choices=["priority", "severity", "importance"],
                   default="priority")
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("-o", "--output")
    args = p.parse_args()

    if args.scan:
        rc = scan(args.dir)
        if rc or not args.report:
            return rc
    if args.report:
        return report(args)
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
