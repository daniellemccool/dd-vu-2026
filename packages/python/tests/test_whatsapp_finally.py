"""
Tests that whatsapp.py chat parser does not swallow exceptions silently.

sys.modules['js'] mock required for Pyodide-only import in file_utils.
"""
import sys
from unittest.mock import MagicMock, patch
import pandas as pd

sys.modules['js'] = MagicMock()

from port.platforms.whatsapp import parse_chat


def test_parse_chat_returns_dataframe_on_bad_input():
    """Garbage input returns an empty DataFrame, not an exception."""
    result = parse_chat("nonexistent_path.txt")
    assert isinstance(result, pd.DataFrame)


def test_parse_chat_logs_on_exception():
    """An unexpected error is logged."""
    with patch("port.platforms.whatsapp.logger") as mock_log:
        result = parse_chat("nonexistent_path.txt")
    assert mock_log.error.called
    assert isinstance(result, pd.DataFrame)
