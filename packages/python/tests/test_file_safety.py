"""Tests for file safety checks in script.py."""
import sys
from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

import pytest
from port.script import FileTooLargeError, ChunkedExportError, check_file_safety

TWO_GB = 2 * 1024 * 1024 * 1024
MAX_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


class FakeFile:
    def __init__(self, size_bytes):
        self.size = size_bytes
        self.name = "test.zip"


def test_normal_file_passes():
    f = FakeFile(500 * 1024 * 1024)  # 500 MB
    check_file_safety(f)


def test_large_file_under_limit_passes():
    f = FakeFile(MAX_BYTES - 1)  # just under 2 GB
    check_file_safety(f)


def test_file_too_large_raises():
    f = FakeFile(MAX_BYTES + 1)  # just over 2 GB
    with pytest.raises(FileTooLargeError) as exc_info:
        check_file_safety(f)
    assert "2 GB" in str(exc_info.value)


def test_file_too_large_message_mentions_size():
    size = 3 * 1024 * 1024 * 1024  # 3 GB
    f = FakeFile(size)
    with pytest.raises(FileTooLargeError) as exc_info:
        check_file_safety(f)
    assert "3" in str(exc_info.value)


def test_chunked_export_raises():
    f = FakeFile(TWO_GB)  # exactly 2 GB
    with pytest.raises(ChunkedExportError) as exc_info:
        check_file_safety(f)
    assert "2 GB" in str(exc_info.value)


def test_file_just_under_two_gb_passes():
    f = FakeFile(TWO_GB - 1)
    check_file_safety(f)
