import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from fix_translation import fix_compound_identifier_format, fix_recoverable_mime_identifiers  # noqa: E402
from lint_translation import (  # noqa: E402
    check_compound_identifier_format,
    missing_mime_context_identifiers,
    recoverable_mime_context_identifiers,
)


def test_detects_spacing_and_case_damage():
    en = "Use Text/Plain, S/MIME, application/geo+json-seq, and a=rtpmap."
    ja = "text / plain、S / MIME、application / geo + json-seq、A = RTPMAPを使用します。"

    assert check_compound_identifier_format(en, ja) == [
        ("Text/Plain", "text / plain"),
        ("S/MIME", "S / MIME"),
        ("application/geo+json-seq", "application / geo + json-seq"),
        ("a=rtpmap", "A = RTPMAP"),
    ]


def test_fixes_spacing_and_case_damage():
    en = "Use Text/Plain, foo_bar, and a=rtpmap."
    ja = "text / plain、Foo_bar、A = RTPMAPを使用します。"

    fixed, changes = fix_compound_identifier_format(en, ja)

    assert fixed == "Text/Plain、foo_bar、a=rtpmapを使用します。"
    assert changes == [
        ("Text/Plain", "text / plain"),
        ("foo_bar", "Foo_bar"),
        ("a=rtpmap", "A = RTPMAP"),
    ]


def test_ignores_hyphen_only_tokens():
    assert check_compound_identifier_format("Use sub-TLV.", "Sub-TLVを使用します。") == []


def test_ignores_ambiguous_source_spelling():
    en = "Text/Plain and text/plain are mentioned together."
    ja = "TEXT / PLAINについて説明します。"

    assert check_compound_identifier_format(en, ja) == []
    assert fix_compound_identifier_format(en, ja) == (ja, [])


def test_preserves_urls_and_raw_url_text():
    en = "See https://example.com/Text/Plain and use Text/Plain."
    ja = "https://example.com/text/plain を参照し、text / plainを使用します。"

    fixed, changes = fix_compound_identifier_format(en, ja)

    assert fixed == "https://example.com/text/plain を参照し、Text/Plainを使用します。"
    assert changes == [("Text/Plain", "text / plain")]


def test_directly_recovers_translated_mime_top_level():
    en = "The payload uses the image/png media type."
    ja = "ペイロードは画像/ PNG添付ファイルを使用します。"

    recovered = recoverable_mime_context_identifiers(en, ja)
    assert [(token, actual) for token, actual, _ in recovered] == [("image/png", "画像/ PNG")]
    assert fix_recoverable_mime_identifiers(en, ja) == (
        "ペイロードはimage/png添付ファイルを使用します。",
        [("image/png", "画像/ PNG")],
    )


def test_does_not_guess_fully_translated_mime_subtype():
    en = "The Text/Enriched MIME media type is described here."
    ja = "テキスト/富化型MIMEメディアタイプについて説明します。"

    assert missing_mime_context_identifiers(en, ja) == ["Text/Enriched"]
    assert recoverable_mime_context_identifiers(en, ja) == []
    assert fix_recoverable_mime_identifiers(en, ja) == (ja, [])
