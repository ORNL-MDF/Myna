#!/usr/bin/env python3
"""
Reject Unicode characters that can conceal, reorder, or ambiguously separate
source text.

Designed to be called by pre-commit, which passes candidate file paths as
arguments:

    python3 scripts/check_unicode.py path/to/file1 path/to/file2
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

# Bidirectional controls implicated in Trojan Source-style attacks.
BIDI_CONTROLS = {
    0x061C,  # ARABIC LETTER MARK
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    0x202A,  # LEFT-TO-RIGHT EMBEDDING
    0x202B,  # RIGHT-TO-LEFT EMBEDDING
    0x202C,  # POP DIRECTIONAL FORMATTING
    0x202D,  # LEFT-TO-RIGHT OVERRIDE
    0x202E,  # RIGHT-TO-LEFT OVERRIDE
    0x2066,  # LEFT-TO-RIGHT ISOLATE
    0x2067,  # RIGHT-TO-LEFT ISOLATE
    0x2068,  # FIRST STRONG ISOLATE
    0x2069,  # POP DIRECTIONAL ISOLATE
}

# Other format or invisible characters that are usually unsafe in source code.
INVISIBLE_OR_FORMAT_CONTROLS = {
    0x00AD,  # SOFT HYPHEN
    0x034F,  # COMBINING GRAPHEME JOINER
    0x115F,  # HANGUL CHOSEONG FILLER
    0x1160,  # HANGUL JUNGSEONG FILLER
    0x17B4,  # KHMER VOWEL INHERENT AQ
    0x17B5,  # KHMER VOWEL INHERENT AA
    0x180B,  # MONGOLIAN FREE VARIATION SELECTOR ONE
    0x180C,  # MONGOLIAN FREE VARIATION SELECTOR TWO
    0x180D,  # MONGOLIAN FREE VARIATION SELECTOR THREE
    0x180E,  # MONGOLIAN VOWEL SEPARATOR
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0x2061,  # FUNCTION APPLICATION
    0x2062,  # INVISIBLE TIMES
    0x2063,  # INVISIBLE SEPARATOR
    0x2064,  # INVISIBLE PLUS
    0x206A,  # INHIBIT SYMMETRIC SWAPPING (deprecated)
    0x206B,  # ACTIVATE SYMMETRIC SWAPPING (deprecated)
    0x206C,  # INHIBIT ARABIC FORM SHAPING (deprecated)
    0x206D,  # ACTIVATE ARABIC FORM SHAPING (deprecated)
    0x206E,  # NATIONAL DIGIT SHAPES (deprecated)
    0x206F,  # NOMINAL DIGIT SHAPES (deprecated)
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / UTF-8 BOM
    0xFFF9,  # INTERLINEAR ANNOTATION ANCHOR
    0xFFFA,  # INTERLINEAR ANNOTATION SEPARATOR
    0xFFFB,  # INTERLINEAR ANNOTATION TERMINATOR
}

# Non-ASCII whitespace is visually ambiguous in source code. This is
# intentionally strict: normal ASCII space and normal line endings are fine.
SUSPICIOUS_WHITESPACE = {
    0x00A0,  # NO-BREAK SPACE
    0x1680,  # OGHAM SPACE MARK
    *range(0x2000, 0x200B),  # EN QUAD through HAIR SPACE
    0x202F,  # NARROW NO-BREAK SPACE
    0x205F,  # MEDIUM MATHEMATICAL SPACE
    0x3000,  # IDEOGRAPHIC SPACE
}


def describe_codepoint(codepoint: int) -> str | None:
    """Return a policy reason for a disallowed Unicode code point."""
    if codepoint in BIDI_CONTROLS:
        return "bidirectional control character"

    if codepoint in INVISIBLE_OR_FORMAT_CONTROLS:
        return "invisible or formatting control character"

    # Unicode tag characters are invisible and should not appear in source.
    if 0xE0000 <= codepoint <= 0xE007F:
        return "Unicode tag character"

    if codepoint in SUSPICIOUS_WHITESPACE:
        return "non-ASCII whitespace character"

    # Standard and supplementary-plane variation selectors can alter displayed
    # glyphs without being obvious in review.
    if 0xFE00 <= codepoint <= 0xFE0F:
        return "variation selector"
    if 0xE0100 <= codepoint <= 0xE01EF:
        return "supplementary variation selector"

    return None


def format_character(character: str) -> str:
    codepoint = ord(character)
    name = unicodedata.name(character, "UNNAMED")
    category = unicodedata.category(character)
    return f"U+{codepoint:04X} {name} (category {category})"


def check_text(label: str, text: str, allowed: set[int]) -> int:
    """
    Print findings in text.

    Columns are Unicode code-point columns, starting at 1. They are not visual
    terminal columns, which is intentional because some flagged characters have
    no visual width.
    """
    findings = 0

    for line_number, line in enumerate(text.splitlines(), start=1):
        for column_number, character in enumerate(line, start=1):
            codepoint = ord(character)

            if codepoint in allowed:
                continue

            reason = describe_codepoint(codepoint)
            if reason is None:
                continue

            print(
                f"{label}:{line_number}:{column_number}: "
                f"{reason}: {format_character(character)}",
                file=sys.stderr,
            )
            findings += 1

    # `splitlines()` does not produce a line for an empty final fragment, which
    # is fine: an empty line cannot contain a disallowed character.
    return findings


def parse_codepoint(value: str) -> int:
    value = value.strip().upper()
    if value.startswith(("U+", "0X")):
        value = value[2:]

    try:
        codepoint = int(value, 16)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid code point {value!r}; expected, for example, U+200D"
        ) from exc

    if not 0 <= codepoint <= 0x10FFFF:
        raise argparse.ArgumentTypeError(
            f"code point out of Unicode range: U+{codepoint:X}"
        )

    return codepoint


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject suspicious Unicode controls and whitespace."
    )
    parser.add_argument(
        "--allow-codepoint",
        action="append",
        default=[],
        type=parse_codepoint,
        metavar="U+XXXX",
        help="allow one otherwise-disallowed code point; may be repeated",
    )
    parser.add_argument("files", nargs="*", help="files supplied by pre-commit")
    args = parser.parse_args()

    allowed = set(args.allow_codepoint)
    findings = 0

    for filename in args.files:
        path = Path(filename)

        # Filenames can also contain bidi or invisible controls.
        findings += check_text(f"{filename} [filename]", filename, allowed)

        try:
            raw = path.read_bytes()
        except OSError as exc:
            print(f"{filename}: cannot read file: {exc}", file=sys.stderr)
            findings += 1
            continue

        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            print(
                f"{filename}:{exc.start + 1}: invalid UTF-8: {exc.reason}",
                file=sys.stderr,
            )
            findings += 1
            continue

        findings += check_text(filename, text, allowed)

    if findings:
        print(
            f"\nUnicode security check failed: {findings} finding(s).",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
