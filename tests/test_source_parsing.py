import sys
sys.path.insert(0, "scripts")
from pkgbuild_loader import parse_source_entries, parse_optdepends

def test_source_rename_syntax():
    result = parse_source_entries(["local::https://example.com"])
    assert result == [{"filename": "local", "url": "https://example.com"}]

def test_source_multiple_colons_only_first_split():
    result = parse_source_entries(["f::a::b::c"])
    assert result == [{"filename": "f", "url": "a::b::c"}]

def test_source_local_file():
    result = parse_source_entries(["change-PATH.patch"])
    assert result == [{"filename": "change-PATH.patch", "url": "change-PATH.patch"}]

def test_source_mixed():
    result = parse_source_entries(["local", "a::url"])
    assert result == [
        {"filename": "local", "url": "local"},
        {"filename": "a", "url": "url"},
    ]

def test_source_empty():
    assert parse_source_entries([]) == []

def test_source_vcs_fragment_preserved():
    result = parse_source_entries(["pkg::git+https://host#tag=v1"])
    assert result[0]["url"] == "git+https://host#tag=v1"

def test_optdepends_with_description():
    result = parse_optdepends(["python: for bindings"])
    assert result == [{"name": "python", "desc": "for bindings"}]

def test_optdepends_no_description():
    result = parse_optdepends(["python"])
    assert result == [{"name": "python", "desc": ""}]

def test_optdepends_colon_in_description():
    result = parse_optdepends(["wl-clipboard: clipboard: experimental"])
    assert result == [{"name": "wl-clipboard", "desc": "clipboard: experimental"}]

def test_optdepends_multiple():
    result = parse_optdepends(["a: desc1", "b: desc2"])
    assert len(result) == 2
    assert result[0]["name"] == "a"
    assert result[1]["name"] == "b"

def test_optdepends_empty():
    assert parse_optdepends([]) == []

def test_optdepends_colon_no_space_falls_to_name():
    result = parse_optdepends(["python:no space"])
    assert result == [{"name": "python:no space", "desc": ""}]
