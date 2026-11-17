"""Report detached Japanese clauses, mistranslated notices, and ASN.1 formatting regressions."""

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree

from lint_translation import BULLET_RE, collect_paths, update_reference_section_state


JAPANESE_FRAGMENT = re.compile(r"(?:^|(?<=[。！？]))[^。！？]*(?:ため|場合)。")
NOMINAL_FRAGMENT = re.compile(
    r"(?:^|(?<=[。！？]))[^。！？]*(?P<ending>方法|方式|手法|手順|処理|形式|値|場合|ため|条件|"
    r"結果|要件|仕様|実装|情報|理由|例|一部|もの|こと|必要性|可能性|範囲|機能|動作|設定|使用|利用|サポート)。"
)
STANDALONE_NOMINAL = re.compile(r"(?<=。)[ \t]*(?P<ending>範囲|情報|処理|値)。(?=\s*$)")
NOMINAL_LABELS = {"Examples.": "例。", "Requirement.": "要件。"}
IANA_REGISTRY_RANGE = re.compile(r"(?P<bounds>[0-9]+-[0-9]+): [Rr]ange available to IANA for assignment in this registry\.")
INLINE_NOMINAL_LABELS = {
    ("Additional requirements: Additional requirements on the parameter value.",
     "追加要件：パラメータ値に関する追加要件。"),
    ("3GPP2 C.S0050-B, 3GPP2 File Formats for Multimedia Services.",
     "3GPP2 C.S0050-B、マルチメディアサービス用の3GPP2ファイル形式。"),
    ("Published specification: This specification.", "公開された仕様：この仕様。"),
    ("Type value: A single text value.", "タイプ値：単一のテキスト値。"),
    ("Type value: A single URI value.", "タイプ値：単一のURI値。"),
    ("Value type: A single text value.", "値のタイプ：単一のテキスト値。"),
    ("Value type: A single text value.", "値タイプ：単一のテキスト値。"),
    ("Value type: A single URI value.", "値タイプ：単一のURI値。"),
    ("Value type: A single uri value.", "値タイプ：単一のURI値。"),
    ("Value type: A single language-tag value.", "値のタイプ：単一の言語タグ値。"),
    ("Value type: A single language-tag value.", "値タイプ：単一の言語タグ値。"),
    ("Value type: A single text value (default) or a single URI value.",
     "値タイプ：単一のテキスト値（デフォルト）または単一のURI値。"),
    ("Value type: One or more text values separated by a COMMA character (U+002C).",
     "値のタイプ：COMMA文字（U+002C）で区切られた1つ以上のテキスト値。"),
    ("Value type: One or more text values separated by a COMMA character (U+002C).",
     "値タイプ：コンマ文字（U+002C）で区切られた1つ以上のテキスト値。"),
}
CARDINALITY_LABELS = {"1", "*", "1*", "*1"}
EN_CARDINALITY = re.compile(
    r"^(?:(?P<field>[A-Za-z][\w:.-]*)[ \t]+)?"
    r"(?P<count>Exactly one|One or more|Zero or one|Zero or more|One)\.(?=\s|$)"
)
EN_COUNTS = {"Exactly one": "1", "One": "1", "One or more": "1+", "Zero or one": "0–1", "Zero or more": "0+"}
JSON_INT_RANGE = "-2^53+1 <= value <= 2^53-1"
JA_JSON_INT_RANGE = re.compile(
    r"[-−]2\s*\^\s*53\s*\+\s*1\s*(?:<=|≤|≦)\s*(?:value|値)"
    r"\s*(?:<=|≤|≦)\s*2\s*\^\s*53\s*[-−]\s*1(?![0-9]|\.[0-9])"
)
IPP_STATUS = re.compile(r"(?<![\w-])(?:client|server)-error-[a-z0-9]+(?:-[a-z0-9]+)*(?![\w-])", re.I | re.ASCII)
OCT_EXP_FORMULA = re.compile(
    r"OCT_EXP\[(?:OCT_LOG\[[a-z]\]|[0-9]+)(?:\s*[+-]\s*(?:OCT_LOG\[[a-z]\]|[0-9]+))+\]"
)
DNS_QUERY_FIELD = re.compile(r"\b(QNAME|QTYPE|QCLASS)=([a-zA-Z0-9*_.-]+)", re.ASCII)
TYPE_ASSIGNMENT = re.compile(r"(?P<inline>Type:[ \t]+)?(?P<number>[0-9]+) for (?P<name>[A-Za-z][A-Za-z0-9-]+)\.", re.I)
JA_CARDINALITY = re.compile(
    r"^(?P<count>(?:ちょうど)?[1一](?:件|つ|個|項目)|(?:0|ゼロ)(?:件|つ|個)?(?:または|か)[1一](?:件|つ|個)?"
    r"|(?:[01]|ゼロ|一)(?:件|つ|個|項目)?以上)"
    r"(?:です|で(?=、型))?[。．、]"
)
LIST_OR_LABEL = re.compile(
    r"^(?:[•–—]|\([0-9A-Za-z]+\)|[0-9]+[A-Za-z]?\))\s+"
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
DANGLING_DETERMINER = re.compile(r"\b(?:the|a|an|this|that|these|those|aforementioned|following)$")
SENTENCE_TAIL = re.compile(r"^[a-z][A-Za-z-]+(?:[ \t]+[a-z][A-Za-z-]+){0,2}\.[ \t]+[A-Z]")
CITATION_WITHOUT_OBJECT = re.compile(r"\[RFC\d+\] (?:defines|describes|specifies)$")
CITATION_OBJECT = re.compile(r"^(?:the|a|an) [^.!?\n]+\.[ \t]+[A-Z]")
ASN1_BOUNDARY = re.compile(
    r"^[ \t]*(?:(?P<module>[A-Z][A-Za-z0-9-]*)[ \t]+DEFINITIONS[ \t]+::=[ \t]+BEGIN"
    r"|(?P<begin>(?:[A-Z][A-Za-z0-9-]*[ \t]+MACRO[ \t]+::=[ \t]+)?BEGIN)|(?P<end>END))[ \t]*$",
    re.M,
)
CODE_HEADING_JOIN = re.compile(
    r"\bEND\x07{3}(?:(?:\d+\.)*\d+\.?[ \t]+[A-Z]|(?:Annex|Appendix) [A-Z]\b|Full Copyright Statement)"
)
XML_DECLARATION = re.compile(r"^<\?xml[ \t]+version[ \t]*=[^?]+\?>")
XML_ROOT = re.compile(r"<([A-Za-z_][\w.:-]*)(?=[\s/>])")
CI_WARNING_KINDS = BOILERPLATE_KINDS | {
    "detached-clause", "mib-prose", "asn1-prose", "code-heading-join", "source-sentence-split", "xml-prose",
    "cardinality-mismatch", "standalone-nominal", "json-integer-range", "ipp-status-negation", "type-assignment",
    "octet-formula", "dns-query-fields",
}


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
    if registry_range := IANA_REGISTRY_RANGE.fullmatch(en):
        return ja == f"{registry_range['bounds']}：このレジストリでの割り当てにIANAが使用できる範囲。"
    source_label, _, source_count = en.partition(" Cardinality: ")
    translated_label, _, translated_count = ja.partition("カーディナリティ：")
    return (source_count in CARDINALITY_LABELS and source_count == translated_count.strip()
            and source_label.startswith("Value type: ")
            and (source_label, translated_label.rstrip()) in INLINE_NOMINAL_LABELS)


def cardinality_mismatch(en, ja, contextual_field):
    source = EN_CARDINALITY.match(en)
    if not source or not (source["field"] or contextual_field):
        return None
    field = source["field"]
    if field and ja.startswith(field):
        ja = ja[len(field):].lstrip(" ：:")
        ja = ja.removeprefix("は").lstrip()
    translated = JA_CARDINALITY.match(ja)
    if translated is None:
        return None
    phrase = translated["count"]
    if "または" in phrase or "か" in phrase:
        actual = "0–1"
    elif phrase.endswith("以上"):
        actual = "0+" if phrase.startswith(("0", "ゼロ")) else "1+"
    else:
        actual = "1"
    expected = EN_COUNTS[source["count"]]
    return (expected, actual) if expected != actual else None


def is_contextual_nominal_label(en, ja, row, preceding, following):
    prior_text = preceding.get("text", "").strip()
    if (en, ja) == ("(*2) If a listener is registered.", "（*2）リスナーが登録されている場合。"):
        return prior_text.startswith("(*1) ") and following.get("text", "").startswith("Figure 1. ")
    if prior_text.startswith("The IETF mission statement [RFC3935]") and prior_text.endswith(":"):
        return (en, ja) == (
            "to produce high quality, relevant technical and engineering documents that influence the way people "
            "design, use, and manage the Internet in such a way as to make the Internet work better.",
            "インターネットの機能を向上させるために、人々がインターネットを設計、使用、管理する方法に影響を与える、"
            "高品質で関連性の高い技術文書およびエンジニアリング文書を作成すること。",
        )
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


def module_prose_indices(rows):
    """Find prose rows in complete ASN.1 modules, including MIBs."""
    module = None
    depth = 0
    pending = []
    for index, row in enumerate(rows):
        en = row["text"]
        if row.get("section_title") or row.get("toc"):
            module = None
            continue
        if module is None and "DEFINITIONS" not in en:
            continue
        is_prose = bool(en.strip() and not row.get("raw"))
        if module is not None and is_prose:
            pending.append(index)
        for boundary in ASN1_BOUNDARY.finditer(en):
            if name := boundary["module"]:
                module, depth = name, 1
                pending = [index] if is_prose else []
            elif module is not None:
                depth += 1 if boundary["begin"] else -1
                if depth == 0:
                    kind = "mib-prose" if module.endswith("-MIB") else "asn1-prose"
                    for prose_index in pending:
                        yield prose_index, kind
                    module = None


def xml_prose_indices(rows):
    """Find translated fragments inside a complete, well-formed XML document."""
    chunks = []
    pending = []
    root = None
    for index, row in enumerate(rows):
        text = row["text"].strip()
        if row.get("section_title") or row.get("toc") or "<!DOCTYPE" in text:
            chunks = []
            continue
        if declaration := XML_DECLARATION.match(text):
            chunks, pending, root = [], [], None
            body = text[declaration.end():]
        elif chunks:
            body = text
        else:
            continue
        chunks.append(text)
        if text and not row.get("raw"):
            pending.append(index)
        if root is None and (opening := XML_ROOT.search(body)):
            root = opening[1]
        if root and text.endswith(f"</{root}>"):
            if pending:
                try:
                    ElementTree.fromstring("\n".join(chunks))
                except (ElementTree.ParseError, ValueError, LookupError):
                    pass
                else:
                    yield from pending
            chunks = []


def inspect(obj, include_nominal=False):
    references = False
    previous = None
    rows = obj["contents"]
    module_prose = dict(module_prose_indices(rows))
    markup_prose = set(xml_prose_indices(rows))
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
        if index in module_prose:
            yield Finding(index, module_prose[index], "", en, "")
            previous = None
            continue
        if index in markup_prose:
            yield Finding(index, "xml-prose", "", en, "")
            previous = None
            continue
        if (prior and previous and not references
                and not row.get("list_continuation") and not rows[index - 1].get("list_continuation")
                and rows[index - 1].get("indent") == row.get("indent")
                and ((SENTENCE_TAIL.match(en) and DANGLING_DETERMINER.search(prior))
                     or (CITATION_WITHOUT_OBJECT.search(prior) and CITATION_OBJECT.match(en)))):
            yield Finding(index, "source-sentence-split", "", f"{prior}\n{en}", "")
        if previous and not references:
            if ja and en.startswith("QNAME="):
                source_fields = dict(DNS_QUERY_FIELD.findall(en))
                if len(source_fields) == 3:
                    translated_fields = set(DNS_QUERY_FIELD.findall(ja))
                    missing = source_fields.items() - translated_fields
                    if missing:
                        expected = ", ".join(f"{key}={value}" for key, value in sorted(missing))
                        yield Finding(index, "dns-query-fields", "", en, expected)
            if ja and "OCT_EXP[" in en:
                translated = "".join(ja.replace("−", "-").split())
                for formula in OCT_EXP_FORMULA.findall(en):
                    if "".join(formula.split()) not in translated:
                        yield Finding(index, "octet-formula", "", en, formula)
            if ja and (assignment := TYPE_ASSIGNMENT.fullmatch(en)) and (
                assignment["inline"] or (
                    prior == "Type" and index + 1 < len(rows) and rows[index + 1]["text"].strip() == "Length"
                )
            ):
                name, number = assignment["name"], assignment["number"]
                name_pattern = rf"(?<![\w-]){re.escape(name)}(?![\w-])"
                if not re.search(name_pattern, ja, re.ASCII) or not re.search(
                    rf"(?<![0-9]){number}(?![0-9])", re.sub(name_pattern, "", ja, flags=re.ASCII)
                ):
                    yield Finding(index, "type-assignment", number, en, name)
            if ja and JSON_INT_RANGE in en and not JA_JSON_INT_RANGE.search(ja):
                yield Finding(index, "json-integer-range", "", en, JSON_INT_RANGE)
            if "-not-supported" in en.lower():
                source_codes = {code.lower() for code in IPP_STATUS.findall(en)}
                translated_codes = {code.lower() for code in IPP_STATUS.findall(ja)}
                for expected in sorted(source_codes - translated_codes):
                    if not expected.endswith("-not-supported"):
                        continue
                    actual = expected.removesuffix("-not-supported") + "-supported"
                    if actual in translated_codes - source_codes:
                        yield Finding(index, "ipp-status-negation", expected, en, actual)
            preceding = rows[index - 1] if index else {}
            contextual_field = bool(
                prior and row.get("indent", 0) > preceding.get("indent", 0)
                and re.fullmatch(r"[A-Za-z][\w:.-]*", prior)
            )
            if counts := cardinality_mismatch(en, ja.strip(), contextual_field):
                expected, actual = counts
                yield Finding(index, "cardinality-mismatch", expected, en, actual)
        warranty = WARRANTY_ERROR.search(ja) if WARRANTY_SOURCE.search(en) else None
        ipr = LICENSE_FRAGMENT.search(ja) if (
            en.startswith(IPR_NOTICE) and "might or might not be available" in en
        ) else None
        standalone = STANDALONE_NOMINAL.search(ja)
        if not include_nominal and "ため。" not in ja and "場合。" not in ja and not (warranty or ipr or standalone):
            continue
        collapsed_dot_list = DOT_BULLET.match(en) and len(DOT_BULLET.findall(en)) > 1
        if (references or heading or row.get("raw") or row.get("toc")
                or row.get("list_continuation") or (BULLET_RE.match(en) and not collapsed_dot_list)
                or LIST_OR_LABEL.match(en) or len(ENUM_ENTRY.findall(en)) >= 2
                or (prior and FIELD_LABEL.fullmatch(prior) and INCOMPLETE_SOURCE.match(en))):
            continue

        if warranty:
            yield Finding(index, "warranty-disclaimer", "", en, warranty[0])
        reported = set()
        if ipr:
            yield Finding(index, "ipr-notice", "", en, ipr[0].strip())
            reported.add(ipr.span())
        if standalone:
            sentences = EN_SENTENCE_BREAK.split(en)
            if len(sentences) >= 2 and en.endswith('.') and all(FINITE_VERB.search(s) for s in sentences):
                yield Finding(index, "standalone-nominal", standalone["ending"], en, standalone[0].strip())
                reported.add(standalone.span())
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
                        or is_contextual_nominal_label(en, translated, row, preceding, following)
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
            "standalone-nominal": "文末で単独になっている名詞",
        }.get(finding.kind, "条件・目的句")
        if finding.kind == "nominal-label":
            print(f"{path} {finding.kind} 段落 {finding.index + 1} は項目の説明またはキャプションです。「{finding.fragment}」")
            continue
        message = (f"{finding.kind} 段落 {finding.index + 1} の{subject}を原文と照合してください。"
                   f"「{finding.fragment}」")
        if finding.kind == "mib-prose":
            message = f"MIB定義内の段落 {finding.index + 1} が本文として表示されています。"
        if finding.kind == "asn1-prose":
            message = f"ASN.1定義内の段落 {finding.index + 1} が本文として表示されています。"
        if finding.kind == "xml-prose":
            message = f"XML文書内の段落 {finding.index + 1} が本文として表示されています。"
        if finding.kind == "code-heading-join":
            message = f"段落 {finding.index + 1} にコードの終了行と次の見出しが混在しています。"
        if finding.kind == "source-sentence-split":
            message = f"段落 {finding.index + 1} の冒頭が直前の英文の続きになっています。改ページ位置を原文と照合してください。"
        if finding.kind == "cardinality-mismatch":
            message = f"段落 {finding.index + 1} の出現回数が原文と訳文で異なります（原文 {finding.ending}、訳文 {finding.fragment}）。"
        if finding.kind == "json-integer-range":
            message = f"段落 {finding.index + 1} の訳文でJSON整数の範囲「{finding.fragment}」を確認してください。"
        if finding.kind == "ipp-status-negation":
            message = f"段落 {finding.index + 1} のIPP状態コードで原文「{finding.ending}」の否定が訳文「{finding.fragment}」から抜けています。"
        if finding.kind == "type-assignment":
            message = f"段落 {finding.index + 1} の訳文で属性タイプ「{finding.fragment}」の名前と番号 {finding.ending} を確認してください。"
        if finding.kind == "octet-formula":
            message = f"段落 {finding.index + 1} の訳文でオクテット演算の式「{finding.fragment}」を確認してください。"
        if finding.kind == "dns-query-fields":
            message = f"段落 {finding.index + 1} のDNS問い合わせ例で「{finding.fragment}」を原文と照合してください。"
        if args.format == "github" and finding.kind in CI_WARNING_KINDS:
            print(f"::warning file={escape_annotation(path)}::{escape_annotation(message)}")
        else:
            print(f"{path} {message}")
    print("候補件数 " + json.dumps(counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
