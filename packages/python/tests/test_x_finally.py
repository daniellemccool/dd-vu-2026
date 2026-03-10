"""
Tests that x.py functions do not swallow exceptions silently.

sys.modules['js'] mock required for Pyodide-only import in file_utils.
"""
import sys
import io
from unittest.mock import MagicMock, patch

sys.modules['js'] = MagicMock()

from port.platforms.x import bytesio_to_listdict


def test_bytesio_to_listdict_logs_on_invalid_json():
    """Invalid JSON input logs an error and returns an empty list."""
    bad = io.BytesIO(b"not valid json")
    with patch("port.platforms.x.logger") as mock_log:
        result = bytesio_to_listdict(bad)
    mock_log.error.assert_called_once()
    assert result == []


def test_bytesio_to_listdict_returns_empty_on_empty_input():
    """Empty input logs an error and returns an empty list."""
    with patch("port.platforms.x.logger") as mock_log:
        result = bytesio_to_listdict(io.BytesIO(b""))
    mock_log.error.assert_called_once()
    assert result == []
