import sys
sys.path.insert(0, "scripts")
from pkgbuild_loader import parse_maintainer_contributor

def test_basic_maintainer():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("# Maintainer: Alice <alice@example.com>\n")
        f.write("pkgname=foo\n")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {"maintainer": "Alice <alice@example.com>"}
    finally:
        os.unlink(path)

def test_with_contributors():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("# Maintainer: M <m@x>\n")
        f.write("# Contributor: C1 <c1@x>\n")
        f.write("# Contributor: C2 <c2@x>\n")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {
            "maintainer": "M <m@x>",
            "contributor": ["C1 <c1@x>", "C2 <c2@x>"],
        }
    finally:
        os.unlink(path)

def test_last_maintainer_wins():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("# Maintainer: Old <old@x>\n")
        f.write("# Maintainer: New <new@x>\n")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {"maintainer": "New <new@x>"}
    finally:
        os.unlink(path)

def test_no_maintainer():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("pkgname=foo\n")
        f.write("pkgver=1\n")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {}
    finally:
        os.unlink(path)

def test_whitespace_handling():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("#  Maintainer:   Alice <alice@x>  \n")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {"maintainer": "Alice <alice@x>"}
    finally:
        os.unlink(path)

def test_only_contributors():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("# Contributor: C <c@x>\n")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {"contributor": ["C <c@x>"]}
    finally:
        os.unlink(path)

def test_empty_file():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {}
    finally:
        os.unlink(path)

def test_maintainer_middle_of_file():
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.PKGBUILD', delete=False) as f:
        f.write("pkgname=x\n")
        f.write("# Maintainer: M <m@x>\n")
        f.write("pkgver=1\n")
        f.flush()
        path = f.name
    try:
        result = parse_maintainer_contributor(path)
        assert result == {"maintainer": "M <m@x>"}
    finally:
        os.unlink(path)
