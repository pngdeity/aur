import sys
import os
import tempfile
import json
import pytest
from pathlib import Path

sys.path.insert(0, "scripts")
from merge_policy_exceptions import merge_exceptions


def test_single_yaml_file():
    import yaml
    # Create temp manifest
    m_fd, manifest_path = tempfile.mkstemp(suffix='.json')
    os.close(m_fd)
    # Create temp packages dir
    pkg_dir = tempfile.mkdtemp()
    pkg_subdir = os.path.join(pkg_dir, "testpkg")
    os.makedirs(pkg_subdir)
    yaml_path = os.path.join(pkg_subdir, "policy_exceptions.yaml")
    
    with open(yaml_path, 'w') as f:
        yaml.dump({"exceptions": [{"rule": "rule1", "reason": "test reason"}]}, f)
    
    with open(manifest_path, 'w') as f:
        json.dump({"packages": {}}, f)
    
    try:
        merge_exceptions(manifest_path, pkg_dir)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "exceptions" in manifest
        assert "testpkg" in manifest["exceptions"]
        assert manifest["exceptions"]["testpkg"]["rule1"] == "test reason"
    finally:
        os.unlink(manifest_path)
        import shutil
        shutil.rmtree(pkg_dir)


def test_no_yaml_files():
    m_fd, manifest_path = tempfile.mkstemp(suffix='.json')
    os.close(m_fd)
    pkg_dir = tempfile.mkdtemp()
    
    with open(manifest_path, 'w') as f:
        json.dump({"packages": {}}, f)
    
    try:
        merge_exceptions(manifest_path, pkg_dir)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest.get("exceptions", {}) == {}
    finally:
        os.unlink(manifest_path)
        import shutil
        shutil.rmtree(pkg_dir)


def test_merges_alongside_existing():
    import yaml
    m_fd, manifest_path = tempfile.mkstemp(suffix='.json')
    os.close(m_fd)
    pkg_dir = tempfile.mkdtemp()
    pkg_subdir = os.path.join(pkg_dir, "testpkg")
    os.makedirs(pkg_subdir)
    yaml_path = os.path.join(pkg_subdir, "policy_exceptions.yaml")
    
    with open(yaml_path, 'w') as f:
        yaml.dump({"exceptions": [{"rule": "new_rule", "reason": "new"}]}, f)
    
    with open(manifest_path, 'w') as f:
        json.dump({"packages": {}, "exceptions": {"existing_pkg": {"old_rule": "old"}}}, f)
    
    try:
        merge_exceptions(manifest_path, pkg_dir)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "existing_pkg" in manifest["exceptions"]
        assert "testpkg" in manifest["exceptions"]
    finally:
        os.unlink(manifest_path)
        import shutil
        shutil.rmtree(pkg_dir)


def test_yaml_without_exceptions_key():
    import yaml
    m_fd, manifest_path = tempfile.mkstemp(suffix='.json')
    os.close(m_fd)
    pkg_dir = tempfile.mkdtemp()
    pkg_subdir = os.path.join(pkg_dir, "testpkg")
    os.makedirs(pkg_subdir)
    yaml_path = os.path.join(pkg_subdir, "policy_exceptions.yaml")
    
    with open(yaml_path, 'w') as f:
        yaml.dump({"other_key": "value"}, f)
    
    with open(manifest_path, 'w') as f:
        json.dump({"packages": {}}, f)
    
    try:
        merge_exceptions(manifest_path, pkg_dir)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest.get("exceptions", {}) == {}
    finally:
        os.unlink(manifest_path)
        import shutil
        shutil.rmtree(pkg_dir)


def test_missing_reason_gets_empty():
    import yaml
    m_fd, manifest_path = tempfile.mkstemp(suffix='.json')
    os.close(m_fd)
    pkg_dir = tempfile.mkdtemp()
    pkg_subdir = os.path.join(pkg_dir, "testpkg")
    os.makedirs(pkg_subdir)
    yaml_path = os.path.join(pkg_subdir, "policy_exceptions.yaml")
    
    with open(yaml_path, 'w') as f:
        yaml.dump({"exceptions": [{"rule": "norule"}]}, f)
    
    with open(manifest_path, 'w') as f:
        json.dump({"packages": {}}, f)
    
    try:
        merge_exceptions(manifest_path, pkg_dir)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["exceptions"]["testpkg"]["norule"] == ""
    finally:
        os.unlink(manifest_path)
        import shutil
        shutil.rmtree(pkg_dir)


def test_multiple_packages():
    import yaml
    m_fd, manifest_path = tempfile.mkstemp(suffix='.json')
    os.close(m_fd)
    pkg_dir = tempfile.mkdtemp()
    
    for pkg_name in ["pkg1", "pkg2"]:
        pkg_subdir = os.path.join(pkg_dir, pkg_name)
        os.makedirs(pkg_subdir)
        yaml_path = os.path.join(pkg_subdir, "policy_exceptions.yaml")
        with open(yaml_path, 'w') as f:
            yaml.dump({"exceptions": [{"rule": f"rule_{pkg_name}", "reason": f"reason_{pkg_name}"}]}, f)
    
    with open(manifest_path, 'w') as f:
        json.dump({"packages": {}}, f)
    
    try:
        merge_exceptions(manifest_path, pkg_dir)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert "pkg1" in manifest["exceptions"]
        assert "pkg2" in manifest["exceptions"]
    finally:
        os.unlink(manifest_path)
        import shutil
        shutil.rmtree(pkg_dir)
