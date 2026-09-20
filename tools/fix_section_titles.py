#!/usr/bin/env python3
"""RFC 8650 未満の欠落した section_title を保守的に修正する。

自動修正するのは、次のいずれかを満たす段落だけである。

1. 同じ RFC の目次項目と本文が一致する。
2. 変更前から section_title だった前後の見出しに対して、章番号が連続する。

番号で始まる手順を見出しに変えてしまわないよう、上記で確定できない候補は
変更せず TSV レポートへ出力する。
"""

import argparse
import csv
import glob
import json
import os
import re
from collections import Counter


TOC_LEADER_RE = re.compile(r"\.{3,}\s*\d+\s*$")
STRUCTURAL_RE = re.compile(
    r"^(?:(?:\d{1,2}\.)+(?:\d{1,2})? "
    r"|[A-Z]\.(?:\d{1,2}\.)+(?:\d{1,2})? "
    r"|[A-Z]\.\d{1,2} "
    r"|Appendix [A-Z])"
)
SECTION_ID_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+")
NUMERIC_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")
JA_NUMERIC_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)([.。]?)(\s*)(.*)$", re.S)


def canonical_heading(text):
    """目次と本文の表記差（箇条書き、空白、末尾ドット）を正規化する。"""
    text = text.strip()
    text = re.sub(r"^(?:[*+o-]\s+)+", "", text)
    text = TOC_LEADER_RE.sub("", text).strip()
    text = re.sub(r"\s+", " ", text)
    match = re.match(r"^((?:\d+\.)*\d+\.?|[A-Z](?:\.\d+)*\.?)\s+(.*)$", text)
    if match:
        return match.group(1).rstrip(".") + " " + match.group(2)
    return text


def toc_headings(contents):
    headings = set()
    for content in contents:
        text = content.get("text", "") or ""
        is_toc = content.get("toc") is True
        looks_like_raw_toc = content.get("raw") is True and TOC_LEADER_RE.search(text)
        if not (is_toc or looks_like_raw_toc):
            continue
        for line in text.splitlines():
            if TOC_LEADER_RE.search(line):
                heading = canonical_heading(line)
                if len(heading) >= 3:
                    headings.add(heading)
    return headings


def section_id(text):
    match = SECTION_ID_RE.match(text)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def normalize_numeric_heading(en, ja):
    """訳文の章番号を原文と同じ表記にし、本文との間を半角空白1個にする。

    訳文先頭から同じ章番号を復元できない場合は、誤修正を避けるため None を返す。
    """
    en_match = NUMERIC_HEADING_RE.match(en)
    if not en_match:
        return None
    ja_match = JA_NUMERIC_HEADING_RE.match(ja)
    if (not ja_match
            or ja_match.group(1) != en_match.group(1).rstrip(".")
            or not ja_match.group(4)):
        return None
    return en_match.group(1) + " " + ja_match.group(4)


def structural_candidate(content):
    text = content.get("text", "") or ""
    return (
        content.get("section_title") is not True
        and content.get("raw") is not True
        and content.get("toc") is not True
        and content.get("indent", 0) <= 2
        and bool(STRUCTURAL_RE.match(text))
        and not text.endswith((".", ":", ","))
    )


def find_fixes(contents):
    """(目次一致index, 番号連続index, 残余候補index) を返す。"""
    toc = toc_headings(contents)
    original_titles = [
        i for i, content in enumerate(contents)
        if content.get("section_title") is True and section_id(content.get("text", ""))
    ]

    toc_matches = set()
    for i, content in enumerate(contents):
        if (content.get("section_title") is True
                or content.get("raw") is True
                or content.get("toc") is True
                or content.get("indent", 0) > 2):
            continue
        if canonical_heading(content.get("text", "")) in toc:
            toc_matches.add(i)

    sequence_matches = set()
    for i, content in enumerate(contents):
        if i in toc_matches or not structural_candidate(content):
            continue
        current = section_id(content.get("text", ""))
        if not current:
            continue
        previous = next((
            j for j in reversed(original_titles)
            if j < i
            and len(section_id(contents[j]["text"])) == len(current)
            and section_id(contents[j]["text"])[:-1] == current[:-1]
        ), None)
        following = next((
            j for j in original_titles
            if j > i
            and len(section_id(contents[j]["text"])) == len(current)
            and section_id(contents[j]["text"])[:-1] == current[:-1]
        ), None)
        if previous is None or following is None:
            continue
        previous_id = section_id(contents[previous]["text"])
        following_id = section_id(contents[following]["text"])
        if previous_id[-1] + 1 == current[-1] and current[-1] + 1 == following_id[-1]:
            sequence_matches.add(i)

    fixed = toc_matches | sequence_matches
    residual = [
        i for i, content in enumerate(contents)
        if i not in fixed and structural_candidate(content)
    ]
    return sorted(toc_matches), sorted(sequence_matches), residual


def collect_paths(max_rfc):
    paths = []
    for path in glob.glob("data/[0-9]000/rfc*-trans.json"):
        match = re.fullmatch(r"rfc(\d+)-trans.json", os.path.basename(path))
        if match and int(match.group(1)) <= max_rfc:
            paths.append((int(match.group(1)), path))
    return sorted(paths)


def reviewed_exclusions(path):
    """文脈レビューで見出しではないと確定した (RFC, index) を読み込む。"""
    if not path or not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8", newline="") as file:
        return {
            (int(row["rfc"]), int(row["index"]))
            for row in csv.DictReader(file, delimiter="\t")
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-rfc", type=int, default=8649)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--report",
        default="reports/rfc-below-8650-section-title-candidates.tsv",
        help="自動確定できなかった候補のTSV出力先",
    )
    parser.add_argument(
        "--number-report",
        default="reports/rfc-below-8650-section-title-number-mismatches.tsv",
        help="訳文先頭から章番号を復元できなかった見出しのTSV出力先",
    )
    parser.add_argument(
        "--reviewed-exclusions",
        default="tools/section_title_reviewed_exclusions.tsv",
        help="文脈レビュー済みの非見出し候補TSV",
    )
    args = parser.parse_args()

    stats = Counter()
    residual_rows = []
    number_mismatch_rows = []
    exclusions = reviewed_exclusions(args.reviewed_exclusions)
    for number, path in collect_paths(args.max_rfc):
        with open(path, encoding="utf-8") as file:
            obj = json.load(file)
        contents = obj.get("contents", [])
        toc_matches, sequence_matches, residual = find_fixes(contents)
        reviewed_matches = {
            index for index in residual
            if (number, index) not in exclusions
        }
        residual = [
            index for index in residual
            if (number, index) in exclusions
        ]
        fixes = set(toc_matches) | set(sequence_matches) | reviewed_matches
        file_changed = bool(fixes)
        stats["toc_matches"] += len(toc_matches)
        stats["sequence_matches"] += len(sequence_matches)
        stats["reviewed_matches"] += len(reviewed_matches)
        for index in fixes:
            contents[index]["section_title"] = True
        for index, content in enumerate(contents):
            if content.get("section_title") is not True or content.get("raw") is True:
                continue
            en = content.get("text", "") or ""
            ja = content.get("ja", "") or ""
            if not NUMERIC_HEADING_RE.match(en):
                continue
            normalized = normalize_numeric_heading(en, ja)
            if normalized is None:
                number_mismatch_rows.append((
                    number,
                    index,
                    en.replace("\t", " ").replace("\n", "\\n"),
                    ja.replace("\t", " ").replace("\n", "\\n"),
                ))
            elif normalized != ja:
                content["ja"] = normalized
                stats["number_spacing"] += 1
                file_changed = True
        # residual は除外台帳で非見出しと確認済みなので、未処理レポートへ戻さない。
        if file_changed:
            stats["changed_files"] += 1
        if file_changed and not args.dry_run:
            with open(path, "w", encoding="utf-8", newline="\n") as file:
                json.dump(obj, file, ensure_ascii=False, indent=2)

    stats["residual"] = len(residual_rows)
    if not args.dry_run:
        report_dir = os.path.dirname(args.report)
        if report_dir:
            os.makedirs(report_dir, exist_ok=True)
        with open(args.report, "w", encoding="utf-8", newline="\n") as file:
            file.write("rfc\tindex\tindent\ttext\tja\treason\n")
            for row in residual_rows:
                file.write("\t".join(map(str, row)) + "\trequires-context-review\n")
        number_report_dir = os.path.dirname(args.number_report)
        if number_report_dir:
            os.makedirs(number_report_dir, exist_ok=True)
        with open(args.number_report, "w", encoding="utf-8", newline="\n") as file:
            file.write("rfc\tindex\ttext\tja\treason\n")
            for row in number_mismatch_rows:
                file.write("\t".join(map(str, row)) + "\tsection-number-not-at-ja-start\n")

    mode = "[DRY-RUN] " if args.dry_run else ""
    print(f"{mode}対象RFC: {len(collect_paths(args.max_rfc))}")
    print(f"  目次一致: {stats['toc_matches']} 段落")
    print(f"  章番号の連続: {stats['sequence_matches']} 段落")
    print(f"  文脈レビューで見出し確定: {stats['reviewed_matches']} 段落")
    print(f"  見出し番号後の空白を正規化: {stats['number_spacing']} 段落")
    print(f"  変更RFC: {stats['changed_files']} 件")
    print(f"  要文脈レビュー: {stats['residual']} 段落")
    print(f"  章番号を自動復元できない見出し: {len(number_mismatch_rows)} 段落")
    if not args.dry_run:
        print(f"  レポート: {args.report}")
        print(f"  章番号レポート: {args.number_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
