"""Tests for declare -p parsing functions in scripts.pkgbuild_to_pkl."""

import sys
sys.path.insert(0, "scripts")
from pkgbuild_loader import parse_declare, _parse_array_elements, _parse_assoc_elements


def test_scalar():
    result = parse_declare(['declare -- pkgname="foo"'])
    assert result == {"pkgname": "foo"}


def test_scalar_readonly():
    result = parse_declare(['declare -r pkgver="1.0"'])
    assert result == {"pkgver": "1.0"}


def test_scalar_empty_skipped():
    result = parse_declare(['declare -- desc=""'])
    assert result == {}


def test_array():
    result = parse_declare(['declare -a arch=([0]="x86_64" [1]="aarch64")'])
    assert result == {"arch": ["x86_64", "aarch64"]}


def test_array_single():
    result = parse_declare(['declare -a depends=([0]="glibc")'])
    assert result == {"depends": ["glibc"]}


def test_array_empty_skipped():
    result = parse_declare(['declare -a depends=()'])
    assert result == {}


def test_array_escaped_quote():
    result = parse_declare(['declare -a src=([0]="foo\\"bar")'])
    assert result == {"src": ['foo"bar']}


def test_mixed_types():
    result = parse_declare([
        'declare -- pkgname="foo"',
        'declare -a arch=([0]="x86_64")',
    ])
    assert result == {"pkgname": "foo", "arch": ["x86_64"]}


def test_blank_lines_skipped():
    result = parse_declare([
        'declare -- pkgname="foo"',
        '',
        'declare -- pkgver="1"',
    ])
    assert result == {"pkgname": "foo", "pkgver": "1"}


def test_unknown_format_silently_skipped():
    result = parse_declare(['some junk line'])
    assert result == {}


def test_parse_array_elements_string_key_extracted():
    result = _parse_array_elements('["key"]="val"')
    assert result == ["val"]


def test_parse_array_elements_sparse():
    result = _parse_array_elements('[0]="a" [2]="c"')
    assert result == ["a", "c"]


def test_parse_array_elements_empty():
    result = _parse_array_elements("")
    assert result == []


def test_parse_assoc_elements_flat():
    result = _parse_assoc_elements('["k1"]="v1" ["k2"]="v2"')
    assert result == ["k1", "v1", "k2", "v2"]


def test_parse_assoc_elements_numeric_key():
    result = _parse_assoc_elements('[0]="v0"')
    assert result == ["0", "v0"]


def test_parse_assoc_elements_empty():
    result = _parse_assoc_elements("")
    assert result == []


def test_scalar_underscore_name():
    result = parse_declare(['declare -- _myvar="val"'])
    assert result == {"_myvar": "val"}


def test_array_escaped_backslash():
    result = parse_declare(['declare -a src=([0]="a\\\\b")'])
    assert result == {"src": ["a\\b"]}
