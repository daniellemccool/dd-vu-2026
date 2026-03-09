"""
Tests for ScriptWrapper error handling in main.py.

These tests mock the `js` module (Pyodide-only) so they can run outside
Pyodide. This is safe because ScriptWrapper's error handler does not call
any js functions — it only uses pure Python props and commands.
"""
import sys
import json
from unittest.mock import MagicMock

# Mock js before importing main (file_utils.py imports js at module level)
sys.modules['js'] = MagicMock()

from port.main import ScriptWrapper, error_flow  # noqa: E402


class FakePayload:
    """Minimal payload object matching the __type__ protocol."""
    def __init__(self, type_, **kwargs):
        self.__type__ = type_
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_uncaught_exception_returns_error_page():
    """When script raises an exception, ScriptWrapper returns an error page."""
    def crashing():
        data = yield  # receive None on first call
        raise RuntimeError("test explosion")

    wrapper = ScriptWrapper(crashing(), platform="X")
    result = wrapper.send(None)

    assert result["__type__"] == "CommandUIRender"
    page = result["page"]
    assert page["__type__"] == "PropsUIPageDataSubmission"
    # Body contains a PropsUIPromptText with the traceback and a PropsUIPromptConfirm
    body_types = [item["__type__"] for item in page["body"]]
    assert "PropsUIPromptText" in body_types
    assert "PropsUIPromptConfirm" in body_types
    # Traceback text includes the exception message
    text_item = next(i for i in page["body"] if i["__type__"] == "PropsUIPromptText")
    assert "RuntimeError" in text_item["text"]["nl"]


def test_consent_true_yields_donate_command():
    """When user consents, ScriptWrapper yields a CommandSystemDonate for error-report."""
    def crashing():
        data = yield
        raise RuntimeError("test explosion")

    wrapper = ScriptWrapper(crashing(), platform="LinkedIn")
    wrapper.send(None)  # triggers error, returns consent page

    # User clicks ok (PayloadTrue)
    result = wrapper.send(FakePayload("PayloadTrue"))
    assert result["__type__"] == "CommandSystemDonate"
    assert result["key"] == "error-report"
    payload = json.loads(result["json_string"])
    assert payload["platform"] == "LinkedIn"
    assert "RuntimeError" in payload["traceback"]
    assert "timestamp" in payload


def test_consent_false_returns_exit():
    """When user declines, ScriptWrapper returns CommandSystemExit."""
    def crashing():
        data = yield
        raise RuntimeError("test explosion")

    wrapper = ScriptWrapper(crashing(), platform="X")
    wrapper.send(None)  # triggers error, returns consent page

    # User clicks cancel (PayloadFalse)
    result = wrapper.send(FakePayload("PayloadFalse"))
    assert result["__type__"] == "CommandSystemExit"


def test_after_donate_returns_exit():
    """After the error donation, the next send returns CommandSystemExit."""
    def crashing():
        data = yield
        raise RuntimeError("test explosion")

    wrapper = ScriptWrapper(crashing(), platform="X")
    wrapper.send(None)  # triggers error
    wrapper.send(FakePayload("PayloadTrue"))  # donate — returns CommandSystemDonate

    # Now send the donation response
    result = wrapper.send(FakePayload("PayloadResponse", value=MagicMock(success=True)))
    assert result["__type__"] == "CommandSystemExit"


def test_normal_flow_not_affected():
    """ScriptWrapper still works normally when no exception is raised."""
    from port.api.commands import CommandUIRender
    from port.api.props import PropsUIPageEnd

    def normal():
        yield CommandUIRender(PropsUIPageEnd())

    wrapper = ScriptWrapper(normal(), platform="X")
    result = wrapper.send(None)
    assert result["__type__"] == "CommandUIRender"
