"""Report detached Japanese clauses, mistranslated notices, and MIB formatting regressions."""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import subprocess

from lint_translation import BULLET_RE, collect_paths, update_reference_section_state


JAPANESE_FRAGMENT = re.compile(r"(?:^|(?<=[。！？]))[^。！？]*(?:ため|場合)。")
NOMINAL_FRAGMENT = re.compile(
    r"(?:^|(?<=[。！？]))[^。！？]*(?P<ending>方法|方式|手法|手順|処理|形式|値|場合|ため|条件|"
    r"結果|要件|仕様|実装|情報|理由|例|一部|もの|こと|必要性|可能性|範囲|機能|動作|設定|使用|利用|サポート)。"
)
NOMINAL_LABELS = {"Examples.": "例。", "Requirement.": "要件。"}
INLINE_NOMINAL_LABELS = {
    ("Published specification: This specification.", "公開された仕様：この仕様。"),
    ("Type value: A single text value.", "タイプ値：単一のテキスト値。"),
    ("Type value: A single URI value.", "タイプ値：単一のURI値。"),
    ("Value type: A single text value.", "値のタイプ：単一のテキスト値。"),
    ("Value type: A single text value.", "値タイプ：単一のテキスト値。"),
    ("Value type: A single URI value.", "値タイプ：単一のURI値。"),
    ("Value type: A single uri value.", "値タイプ：単一のURI値。"),
}
CARDINALITY_LABELS = {"1", "*", "1*", "*1"}
LIST_OR_LABEL = re.compile(
    r"^(?:[•–—]|\([0-9A-Za-z]+\)|[0-9]+\))\s+"
    r"|^(?:[\w.]*Exception\s+-\s+|[\w-]+:\s+because\b)"
    r"|^(?:Figure|Table)\s+\d+\s*[:.]",
    re.IGNORECASE,
)
DOT_BULLET = re.compile(r"(?:^|\s)\.\s+")
ENUM_ENTRY = re.compile(r"\b\w+\(\d+\),?\s+when\b", re.IGNORECASE)
FIELD_LABEL = re.compile(r"^[^.!?\n]{1,70}:\s*(?:\d+\s+(?:bits?|bytes?|octets?))?$", re.I)
COPYRIGHT = re.compile(r"provided that the above copyright notice and this paragraph", re.I)
WARRANTY_SOURCE = re.compile(r"\bdisclaims? all warranties\b", re.I)
WARRANTY_ERROR = re.compile(
    r"(?:商品性|適合性)[^。！？]{0,32}権利または(?:黙示|暗黙)"
    r"|明示(?:的)?または明示(?:的)?"
)
IPR_NOTICE = "The IETF takes no position regarding the validity or scope"
LICENSE_FRAGMENT = re.compile(r"(?<=。)\s*利用(?:可能(?:であること|になります|です)。|できる;)")
BOILERPLATE_KINDS = {"copyright", "warranty-disclaimer", "ipr-notice"}
EN_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
CONDITION = re.compile(r"\b(?:if|when|unless|provided that|in (?:the|this|that) case)\b", re.I)
PURPOSE = re.compile(r"\b(?:in order to|so as to|so that|to|because|due to|for)\b", re.I)
# Evidence of a main clause. Ambiguous English remains outside the CI warning.
FINITE_VERB = re.compile(
    r"\b(?:is|are|was|were|has|have|had|can|could|will|would|should|must|may|might|"
    r"shall|does|do|did|allows?|uses?|requires?|provides?|supports?|sends?|returns?|"
    r"contains?|includes?|shows?|indicates?|starts?|ends?|occurs?)\b",
    re.I,
)
INCOMPLETE_SOURCE = re.compile(r"^(?:if|when|unless|(?:in order |so as )?to|because|for)\b", re.I)
MIB_START = re.compile(r"^[ \t]*[A-Z][A-Z0-9-]*-MIB[ \t]+DEFINITIONS[ \t]+::=[ \t]+BEGIN[ \t]*$", re.M)
MIB_END = re.compile(r"^[ \t]*END[ \t]*$", re.M)
CODE_HEADING_JOIN = re.compile(
    r"\bEND\x07{3}(?:(?:\d+\.)*\d+\.?[ \t]+[A-Z]|(?:Annex|Appendix) [A-Z]\b|Full Copyright Statement)"
)
CI_WARNING_KINDS = BOILERPLATE_KINDS | {"detached-clause", "mib-prose", "code-heading-join"}


@dataclass(frozen=True)
class Finding:
    index: int
    kind: str
    ending: str
    source: str
    fragment: str

    def key(self):
        # A preceding paragraph may be inserted without introducing a defect.
        return self.kind, self.ending, " ".join(self.source.split()), " ".join(self.fragment.split())


def source_has_main_clause(en, ending):
    cue = CONDITION if ending == "場合" else PURPOSE
    for sentence in EN_SENTENCE_BREAK.split(en):
        for match in cue.finditer(sentence):
            if FINITE_VERB.search(sentence[:match.start()]):
                return True
            # In a fronted clause such as “If X, the receiver MUST …”,
            # inspect the part after the delimiter for the main predicate.
            if match.start() == 0:
                _, comma, main = sentence.partition(",")
                if comma and FINITE_VERB.search(main):
                    return True
    return False


def is_inline_nominal_label(en, ja):
    if (en, ja) in INLINE_NOMINAL_LABELS:
        return True
    source_label, _, source_count = en.partition(" Cardinality: ")
    translated_label, _, translated_count = ja.partition("カーディナリティ：")
    return (source_count in CARDINALITY_LABELS and source_count == translated_count.strip()
            and source_label.startswith("Value type: ")
            and (source_label, translated_label.rstrip()) in INLINE_NOMINAL_LABELS)


def is_contextual_nominal_label(en, ja, row, preceding):
    prior_text = preceding.get("text", "").strip()
    if preceding.get("raw") and not preceding.get("toc"):
        return ((en, ja) == ("How the decision for isAccessAllowed is made.", "isAccessAllowedの決定方法。")
                and prior_text.startswith("+--"))
    if row.get("indent", 0) <= preceding.get("indent", 0):
        return False
    if prior_text == "Value" and en == "The value of the TLV.":
        return ja in {"TLVの値。", "TLV の値。"}
    if re.fullmatch(r"(?:Exclude-Any|Include-Any|Include-All) EAG:", prior_text):
        return (en, ja) == ("The EAG value, as defined in [RFC9350].", "[RFC9350]で定義されているEAG値。")
    return prior_text.endswith(":") and (en, ja) == ("Part of L2.", "L2の一部。")


def mib_prose_indices(rows):
    """Find prose rows in a MIB module whose start and end are both visible."""
    pending = None
    for index, row in enumerate(rows):
        en = row["text"]
        if row.get("section_title") or row.get("toc"):
            pending = None
            continue
        if "DEFINITIONS" in en and MIB_START.search(en):
            pending = []
        if pending is None:
            continue
        if en.strip() and not row.get("raw"):
            pending.append(index)
        if MIB_END.search(en):
            yield from pending
            pending = None


def inspect(obj, include_nominal=False):
    references = False
    previous = None
    rows = obj["contents"]
    mib_prose = set(mib_prose_indices(rows))
    for index, row in enumerate(rows):
        en = row["text"].strip()
        ja = row.get("ja", "")
        heading = row.get("section_title", False)
        references = update_reference_section_state(references, en, heading)
        prior = previous
        previous = en if en and not (heading or row.get("raw") or row.get("toc")) else None
        if "\x07" in en and CODE_HEADING_JOIN.search(en):
            yield Finding(index, "code-heading-join", "", en, "")
            previous = None
            continue
        if index in mib_prose:
            yield Finding(index, "mib-prose", "", en, "")
            previous = None
            continue
        warranty = WARRANTY_ERROR.search(ja) if WARRANTY_SOURCE.search(en) else None
        ipr = LICENSE_FRAGMENT.search(ja) if (
            en.startswith(IPR_NOTICE) and "might or might not be available" in en
        ) else None
        if not include_nominal and "ため。" not in ja and "場合。" not in ja and not (warranty or ipr):
            continue
        if (references or heading or row.get("raw") or row.get("toc")
                or row.get("list_continuation") or BULLET_RE.match(en)
                or LIST_OR_LABEL.match(en) or len(ENUM_ENTRY.findall(en)) >= 2
                or (DOT_BULLET.match(en) and len(DOT_BULLET.findall(en)) == 1)
                or (prior and FIELD_LABEL.fullmatch(prior) and INCOMPLETE_SOURCE.match(en))):
            continue

        if warranty:
            yield Finding(index, "warranty-disclaimer", "", en, warranty[0])
        reported = set()
        if ipr:
            yield Finding(index, "ipr-notice", "", en, ipr[0].strip())
            reported.add(ipr.span())
        for match in JAPANESE_FRAGMENT.finditer(ja):
            fragment = match[0].strip()
            ending = "場合" if fragment.endswith("場合。") else "ため"
            if ending == "場合" and COPYRIGHT.search(en) and "著作権通知" in fragment:
                kind = "copyright"
            elif source_has_main_clause(en, ending):
                kind = "detached-clause"
            elif (prior and INCOMPLETE_SOURCE.match(en)
                    and not prior.rstrip("\"'”’»)]").endswith((".", "?", "!", ":", ";"))
                    and FINITE_VERB.search(prior)):
                kind = "paragraph-split"
            else:
                continue
            yield Finding(index, kind, ending, en, fragment)
            reported.add(match.span())
        if include_nominal:
            preceding = rows[index - 1] if index else {}
            following = rows[index + 1] if index + 1 < len(rows) else {}
            translated = ja.strip()
            is_label = (is_inline_nominal_label(en, translated)
                        or is_contextual_nominal_label(en, translated, row, preceding)
                        or (NOMINAL_LABELS.get(en) == translated
                            and following.get("indent", 0) > row.get("indent", 0)))
            for match in NOMINAL_FRAGMENT.finditer(ja):
                if match.span() not in reported:
                    kind = "nominal-label" if is_label else "nominal-fragment"
                    yield Finding(index, kind, match["ending"], en, match[0].strip())


def introduced(before, after):
    counts = Counter(f.key() for f in before)
    for finding in after:
        key = finding.key()
        if counts[key]:
            counts[key] -= 1
        else:
            yield finding


def git(*args):
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8")


def changed_findings(base):
    base = git("merge-base", base, "HEAD").strip()
    # Compare committed blobs, including on GitHub's synthetic PR merge commit.
    paths = git("diff", "--name-only", "--no-renames", "--diff-filter=AM", "-z", base, "HEAD",
                "--", "data/*/rfc*-trans.json").split("\0")
    existing = set(git("ls-tree", "-r", "--name-only", "-z", base, "--", "data").split("\0"))
    for path in filter(None, paths):
        before = inspect(json.loads(git("show", f"{base}:{path}"))) if path in existing else ()
        after = inspect(json.loads(git("show", f"HEAD:{path}")))
        for finding in introduced(before, after):
            yield path, finding


def escape_annotation(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-base", help="report only findings introduced since the merge base")
    parser.add_argument("--include-nominal", action="store_true",
                        help="include noun-ending candidates for manual review")
    parser.add_argument("--rfc", nargs="+", help="RFC numbers to audit in the working tree")
    parser.add_argument("--format", choices=("text", "json", "github"), default="text")
    args = parser.parse_args()
    if args.compare_base and (args.rfc or args.include_nominal):
        parser.error("--compare-base cannot be combined with --rfc or --include-nominal")

    if args.compare_base:
        results = list(changed_findings(args.compare_base))
    else:
        paths = collect_paths(args.rfc)
        results = [(path, item) for path in paths
                   for item in inspect(json.loads(Path(path).read_text(encoding="utf-8")),
                                       include_nominal=args.include_nominal)]
    counts = dict(Counter(f.kind for _, f in results))
    if args.format == "json":
        print(json.dumps({"counts": counts, "findings": [
            {"file": path, **asdict(f)} for path, f in results
        ]}, ensure_ascii=False, indent=2))
        return

    seen_boilerplate = set()
    for path, finding in results:
        if finding.kind in BOILERPLATE_KINDS:
            if finding.key() in seen_boilerplate:
                continue
            seen_boilerplate.add(finding.key())
        subject = {
            "warranty-disclaimer": "保証の否認",
            "ipr-notice": "知的財産権に関する声明",
            "nominal-fragment": "文末の名詞句",
        }.get(finding.kind, "条件・目的句")
        if finding.kind == "nominal-label":
            print(f"{path} {finding.kind} 段落 {finding.index + 1} は項目の説明またはキャプションです。「{finding.fragment}」")
            continue
        message = (f"{finding.kind} 段落 {finding.index + 1} の{subject}を原文と照合してください。"
                   f"「{finding.fragment}」")
        if finding.kind == "mib-prose":
            message = f"MIB定義内の段落 {finding.index + 1} が本文として表示されています。"
        if finding.kind == "code-heading-join":
            message = f"段落 {finding.index + 1} にコードの終了行と次の見出しが混在しています。"
        if args.format == "github" and finding.kind in CI_WARNING_KINDS:
            print(f"::warning file={escape_annotation(path)}::{escape_annotation(message)}")
        else:
            print(f"{path} {message}")
    print("候補件数 " + json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
