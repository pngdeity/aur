"""Tests for bash-string unescaping functions in scripts.pkgbuild_to_pkl."""

import sys
sys.path.insert(0, "scripts")
from pkgbuild_loader import unescape_bash_string, _unescape_double_quoted, _unescape_ansi_c


def test_double_quoted_simple():
    assert unescape_bash_string('"hello"') == "hello"


def test_double_quoted_escaped_quote():
    assert unescape_bash_string('"foo\\"bar"') == 'foo"bar'


def test_double_quoted_backslash():
    assert unescape_bash_string('"a\\\\b"') == "a\\b"


def test_double_quoted_dollar():
    assert unescape_bash_string('"\\$pkgver"') == "$pkgver"


def test_double_quoted_backtick():
    assert unescape_bash_string('"\\`cmd`"') == "`cmd`"


def test_double_quoted_bang():
    assert unescape_bash_string('"\\!bang"') == "!bang"


def test_double_quoted_line_continuation():
    assert unescape_bash_string('"line1\\\nline2"') == "line1line2"


def test_ansi_c_newline():
    assert unescape_bash_string("$'foo\\nbar'") == "foo\nbar"


def test_ansi_c_tab():
    assert unescape_bash_string("$'a\\tb'") == "a\tb"


def test_ansi_c_hex():
    assert unescape_bash_string("$'\\x41'") == "A"


def test_ansi_c_octal():
    assert unescape_bash_string("$'\\0101'") == "A"


def test_ansi_c_escape():
    assert unescape_bash_string("$'\\e[1m'") == "\x1b[1m"


def test_ansi_c_invalid_hex_passes_through():
    result = unescape_bash_string("$'\\xZZ'")
    assert "\\xZZ" in result or "\\\\xZZ" in result


def test_bare_unquoted():
    assert unescape_bash_string("hello") == "hello"


def test_empty_double_quoted():
    assert unescape_bash_string('""') == ""


def test_strips_whitespace():
    assert unescape_bash_string('  "hi"  ') == "hi"


def test_dq_unknown_backslash_passes_through():
    assert _unescape_double_quoted("a\\zb") == "a\\zb"


def test_dq_trailing_backslash():
    assert _unescape_double_quoted("a\\") == "a\\"


def test_dq_no_backslash():
    assert _unescape_double_quoted("abc") == "abc"


def test_ansi_c_all_base_escapes():
    assert _unescape_ansi_c("\\a\\b\\f\\n\\r\\t\\v") == "\a\b\f\n\r\t\v"


def test_ansi_c_single_and_double_quote():
    assert _unescape_ansi_c("\\'\\\"") == "'" + '"'


def test_ansi_c_backslash():
    assert _unescape_ansi_c("\\\\") == "\\"


def test_ansi_c_truncated_hex():
    result = _unescape_ansi_c("\\x4")
    assert "\\x4" in result or "\\\\x4" in result


def test_ansi_c_octal_zero():
    assert _unescape_ansi_c("\\0") == "\0"


def test_ansi_c_non_escape_passes_through():
    result = _unescape_ansi_c("\\z")
    assert "\\z" in result or "\\\\z" in result
