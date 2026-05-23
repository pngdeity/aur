"""Tests for function-body parsing functions in scripts.pkgbuild_to_pkl."""

import sys
sys.path.insert(0, "scripts")
from pkgbuild_loader import parse_functions, _dedent_body


def test_single_function():
    text = "=FUNC_BEGIN=build=\nbuild ()\n{\n  make\n}\n=FUNC_END=build="
    result = parse_functions(text)
    assert result == {"build": "make"}


def test_multiple_functions():
    text = (
        "=FUNC_BEGIN=build=\nbuild ()\n{\n  make\n}\n=FUNC_END=build=\n"
        "=FUNC_BEGIN=check=\ncheck ()\n{\n  test\n}\n=FUNC_END=check="
    )
    result = parse_functions(text)
    assert result == {"build": "make", "check": "test"}


def test_empty_body():
    text = "=FUNC_BEGIN=prepare=\nprepare ()\n{\n}\n=FUNC_END=prepare="
    result = parse_functions(text)
    assert result == {"prepare": ""}


def test_no_functions():
    result = parse_functions("")
    assert result == {}


def test_dedent_applied():
    text = "=FUNC_BEGIN=build=\nbuild ()\n{\n    make\n    install\n}\n=FUNC_END=build="
    result = parse_functions(text)
    assert result == {"build": "make\ninstall"}


def test_dedent_body_empty_list():
    assert _dedent_body([]) == ""


def test_dedent_body_leading_trailing_blanks():
    assert _dedent_body(["", "  a", ""]) == "a"


def test_dedent_body_consistent_indent():
    assert _dedent_body(["    a", "    b"]) == "a\nb"


def test_dedent_body_mixed_indent():
    assert _dedent_body(["  a", "    b"]) == "a\n  b"


def test_dedent_body_all_blank():
    assert _dedent_body(["  ", "  "]) == ""


def test_fallback_brace_not_found():
    text = "=FUNC_BEGIN=build=\nbuild ()\nmake\ninstall\n=FUNC_END=build="
    result = parse_functions(text)
    assert "build" in result


def test_dedent_body_trailing_whitespace_stripped():
    assert _dedent_body(["\ta"]) == "a"
