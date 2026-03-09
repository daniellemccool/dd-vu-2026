"""Tests for PayloadResponse handling in script.py."""
import sys
from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

from port.script import handle_donate_result


class FakeResponse:
    def __init__(self, success, status=200, error=None):
        self.__type__ = "PayloadResponse"
        self.value = MagicMock(success=success, status=status, error=error)


def test_none_result_is_success():
    """None (fire-and-forget mode) is treated as success."""
    assert handle_donate_result(None) is True


def test_payload_void_is_success():
    """Non-PayloadResponse result is treated as success."""
    other = MagicMock()
    other.__type__ = "PayloadVoid"
    assert handle_donate_result(other) is True


def test_payload_response_success():
    """PayloadResponse with success=True returns True."""
    assert handle_donate_result(FakeResponse(success=True)) is True


def test_payload_response_failure():
    """PayloadResponse with success=False returns False."""
    assert handle_donate_result(FakeResponse(success=False, status=500)) is False
