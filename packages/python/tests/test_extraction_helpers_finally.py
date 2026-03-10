"""
Tests that extraction_helpers functions do not swallow exceptions silently.

These tests verify that errors are logged and that the function returns the
empty default value — not that exceptions propagate (the functions are
intentionally exception-safe). The key behaviour we're checking is that
a `return` inside `finally` does not mask the exception from the logger.

sys.modules['js'] mock is required because file_utils.py imports js at
module level (Pyodide-only).
"""
import sys
import io
import zipfile
from unittest.mock import MagicMock, patch

sys.modules['js'] = MagicMock()

from port.helpers.extraction_helpers import extract_file_from_zip, read_csv_from_bytes


def make_zip_bytes(filename: str, content: bytes) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, content)
    buf.seek(0)
    return buf


def test_extract_file_from_zip_logs_on_bad_zip():
    """A corrupted zip logs an error and returns an empty BytesIO."""
    bad_zip = io.BytesIO(b"not a zip file")
    with patch("port.helpers.extraction_helpers.logger") as mock_log:
        result = extract_file_from_zip(bad_zip, "any.json")
    mock_log.error.assert_called_once()
    assert isinstance(result, io.BytesIO)


def test_extract_file_from_zip_logs_when_file_missing():
    """A valid zip with no matching file logs an error and returns empty BytesIO."""
    buf = make_zip_bytes("other.json", b"{}")
    with patch("port.helpers.extraction_helpers.logger") as mock_log:
        result = extract_file_from_zip(buf, "missing.json")
    mock_log.error.assert_called_once()
    assert isinstance(result, io.BytesIO)


def test_extract_file_from_zip_success():
    """Happy path: returns BytesIO with the file contents."""
    content = b'{"key": "value"}'
    buf = make_zip_bytes("data.json", content)
    result = extract_file_from_zip(buf, "data.json")
    assert result.read() == content


def test_read_csv_from_bytes_logs_on_bad_input():
    """Invalid CSV input logs an error and returns an empty list."""
    bad_input = io.BytesIO(b"\xff\xfe invalid utf-8 \x00\x01")
    with patch("port.helpers.extraction_helpers.logger") as mock_log:
        result = read_csv_from_bytes(bad_input)
    mock_log.error.assert_called_once()
    assert result == []


def test_read_csv_from_bytes_success():
    """Valid CSV input returns a list of dicts."""
    csv_bytes = io.BytesIO(b"name,age\nAlice,30\nBob,25")
    result = read_csv_from_bytes(csv_bytes)
    assert result == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
