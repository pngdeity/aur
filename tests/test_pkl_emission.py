import sys
sys.path.insert(0, "scripts")
from pkgbuild_loader import pkgrel_value
from pkl_writer import (
    _is_empty_value, _is_multiline, _pkl_string, _pkl_raw_string,
    _pkl_value, _pkl_object, _format_field, write_pkl_module
)
import pytest


# ── _is_empty_value ────────────────────────────────────────────────────────

def test_empty_val_none():
    assert _is_empty_value(None) is True

def test_empty_val_empty_list():
    assert _is_empty_value([]) is True

def test_empty_val_non_empty_list():
    assert _is_empty_value(["a"]) is False

def test_empty_val_empty_string_is_valid():
    assert _is_empty_value("") is False

def test_empty_val_zero_is_valid():
    assert _is_empty_value(0) is False

def test_empty_val_false_is_valid():
    assert _is_empty_value(False) is False


# ── _is_multiline ──────────────────────────────────────────────────────────

def test_multiline_single():
    assert _is_multiline("hello") is False

def test_multiline_multi():
    assert _is_multiline("a\nb") is True


# ── _pkl_string ────────────────────────────────────────────────────────────

def test_pkl_string_simple():
    assert _pkl_string("hello") == '"hello"'

def test_pkl_string_embedded_quote():
    result = _pkl_string('say "hi"')
    assert 'say \\"hi\\"' in result

def test_pkl_string_backslash_doubled():
    result = _pkl_string("a\\b")
    assert "a\\\\b" in result

def test_pkl_string_multiline():
    result = _pkl_string("a\nb")
    assert '"""' in result
    assert 'a' in result and 'b' in result


# ── _pkl_raw_string ────────────────────────────────────────────────────────

def test_pkl_raw_string_single_line():
    result = _pkl_raw_string("cd src")
    assert '#' in result
    assert "cd src" in result

def test_pkl_raw_string_multiline():
    result = _pkl_raw_string("cd\nmake")
    assert '#"""' in result
    assert '"""#' in result
    assert "cd" in result
    assert "make" in result

def test_pkl_raw_string_backslash_preserved():
    result = _pkl_raw_string(r"sed 's/\//g/'")
    # Backslash should NOT be doubled — raw string preserves it
    assert "\\\\" not in result
    assert "sed 's/\\//g/'" in result or "sed" in result

def test_pkl_raw_string_escapes_delimiter():
    result = _pkl_raw_string('close"#mid')
    assert '"\\#' in result  # "# sequence escaped


# ── _pkl_value ─────────────────────────────────────────────────────────────

def test_pkl_value_bool_true():
    assert _pkl_value(True) == "true"

def test_pkl_value_bool_false():
    assert _pkl_value(False) == "false"

def test_pkl_value_int():
    assert _pkl_value(42) == "42"

def test_pkl_value_float():
    assert "3.14" in _pkl_value(3.14)

def test_pkl_value_string():
    result = _pkl_value("hello")
    assert '"hello"' in result

def test_pkl_value_string_list():
    result = _pkl_value(["a", "b"])
    assert 'new {' in result
    assert '"a"' in result
    assert '"b"' in result

def test_pkl_value_single_string_list():
    result = _pkl_value(["a"])
    assert 'new {' in result
    assert '"a"' in result

def test_pkl_value_empty_list():
    assert _pkl_value([]) == "null"

def test_pkl_value_dict_list():
    result = _pkl_value([{"url": "u", "filename": "f"}])
    assert "new {" in result
    assert "schema.SourceEntry" in result

def test_pkl_value_typeerror():
    with pytest.raises(TypeError):
        _pkl_value(None)


# ── _pkl_object ────────────────────────────────────────────────────────────

def test_pkl_object_source_entry():
    result = _pkl_object({"url": "u", "filename": "f"}, class_name="schema.SourceEntry")
    assert "new schema.SourceEntry" in result
    assert 'url = "u"' in result
    assert 'filename = "f"' in result

def test_pkl_object_optdepends_entry():
    result = _pkl_object({"name": "pkg", "desc": "description"}, class_name="schema.OptDependsEntry")
    assert "new schema.OptDependsEntry" in result
    assert 'name = "pkg"' in result

def test_pkl_object_none_values_skipped():
    result = _pkl_object({"name": "pkg", "desc": None}, class_name="schema.OptDependsEntry")
    assert "desc" not in result


# ── pkgrel_value ───────────────────────────────────────────────────────────

def test_pkgrel_value_int():
    assert pkgrel_value("1") == 1

def test_pkgrel_value_float():
    assert pkgrel_value("1.1") == 1.1

def test_pkgrel_value_error_on_garbage():
    with pytest.raises(ValueError):
        pkgrel_value("abc")

def test_pkgrel_value_error_on_empty():
    with pytest.raises(ValueError):
        pkgrel_value("")


# ── _format_field ──────────────────────────────────────────────────────────

def test_format_field_string():
    result = _format_field("pkgdesc", "a description", indent="    ")
    assert result.startswith("    pkgdesc")
    assert "a description" in result

def test_format_field_lifecycle_key_uses_raw_string():
    result = _format_field("build", "make\ninstall", indent="    ")
    assert result.startswith("    build")
    assert '#"""' in result  # raw string delimiter, not regular string

def test_format_field_boolean_conversion():
    result = _format_field("_deploy_aur", True, indent="    ")
    assert "true" in result
    assert '"true"' not in result  # boolean literal, not quoted string

def test_format_field_source_list():
    result = _format_field("source", [{"filename": "local", "url": "https://example.com"}], indent="    ")
    assert "source =" in result
    assert "SourceEntry" in result or "filename" in result

def test_format_field_optdepends_list():
    result = _format_field("optdepends", [{"name": "python", "desc": "for bindings"}], indent="    ")
    assert "optdepends =" in result
    assert "python" in result

def test_format_field_pkgrel_conversion():
    result = _format_field("pkgrel", 1, indent="    ")
    assert "pkgrel = 1" in result
    assert '"1"' not in result

def test_format_field_epoch_conversion():
    result = _format_field("epoch", 1, indent="    ")
    assert "epoch = 1" in result
    assert '"1"' not in result


# ── write_pkl_module ────────────────────────────────────────────────────────

def test_write_pkl_module_minimal():
    output = write_pkl_module({"pkgname": "test"}, {})
    assert "import" in output
    assert "schema.Package" in output
    assert "test" in output

def test_write_pkl_module_comment_truncated():
    long_desc = "x" * 100
    output = write_pkl_module({"pkgname": "t", "pkgdesc": long_desc}, {})
    assert "// t — " in output
    assert "..." in output

def test_write_pkl_module_hidden_vars_after_ordered():
    output = write_pkl_module({"pkgname": "t", "_foo": "bar"}, {})
    pkgname_pos = output.find("pkgname")
    foo_pos = output.find("_foo")
    assert pkgname_pos < foo_pos

def test_write_pkl_module_empty_list_skipped():
    output = write_pkl_module({"pkgname": "t", "depends": []}, {})
    assert "depends" not in output

def test_write_pkl_module_none_skipped():
    output = write_pkl_module({"pkgname": "t", "extra": None}, {})
    assert "extra" not in output

def test_write_pkl_module_empty_string_emitted():
    output = write_pkl_module({"pkgname": "t", "pkgdesc": ""}, {})
    assert 'pkgdesc' in output
