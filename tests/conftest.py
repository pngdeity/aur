import pytest
from pathlib import Path

@pytest.fixture
def sample_pkgbuild_file(tmp_path: Path) -> Path:
    """Create a minimal PKGBUILD file for integration tests."""
    pkgbuild = tmp_path / "PKGBUILD"
    pkgbuild.write_text("""\
# Maintainer: Test Dev <test@example.com>
# Contributor: Old Contributor <old@example.com>
pkgname=testpkg
pkgver=1.0
pkgrel=1
arch=(any)
pkgdesc="A test package"
""")
    return pkgbuild

@pytest.fixture
def sample_declare_p_output() -> str:
    """Return realistic declare -p output."""
    return '\n'.join([
        'declare -- pkgname="testpkg"',
        'declare -- pkgver="1.0"',
        'declare -- pkgrel="1"',
        'declare -a arch=([0]="any")',
        'declare -- pkgdesc="A test package"',
    ])
