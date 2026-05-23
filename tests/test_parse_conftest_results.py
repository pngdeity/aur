import sys
import json
import tempfile
import os

sys.path.insert(0, "scripts")
from parse_conftest_results import parse_results


def test_all_pass():
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    with open(path, 'w') as f:
        json.dump([{"failures": [], "warnings": []}], f)
    try:
        assert parse_results(path) == 0
    finally:
        os.unlink(path)


def test_one_failure():
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    with open(path, 'w') as f:
        json.dump([{"failures": [{"msg": "deny: test"}], "warnings": []}], f)
    try:
        assert parse_results(path) == 1
    finally:
        os.unlink(path)


def test_one_warning():
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    with open(path, 'w') as f:
        json.dump([{"failures": [], "warnings": [{"msg": "warn: test"}]}], f)
    try:
        assert parse_results(path) == 0
    finally:
        os.unlink(path)


def test_both_failure_and_warning():
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    with open(path, 'w') as f:
        json.dump([{"failures": [{"msg": "f"}], "warnings": [{"msg": "w"}]}], f)
    try:
        assert parse_results(path) == 1
    finally:
        os.unlink(path)


def test_missing_file_returns_error():
    assert parse_results("/nonexistent/path/file.json") == 1
