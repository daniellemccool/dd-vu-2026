"""
Tests for donation_failed_flow() in script.py.

sys.modules['js'] mock required for Pyodide-only import in file_utils.
"""
import sys
import json
from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

from port.script import donation_failed_flow  # noqa: E402


class _P:
    """Minimal payload stand-in."""
    def __init__(self, type_str, value=None):
        self.__type__ = type_str
        self.value = value


class _PayloadResponse:
    """Stand-in for PayloadResponse from the JS bridge."""
    __type__ = "PayloadResponse"
    def __init__(self, success: bool, error: str = "", status: int = 200):
        self.value = MagicMock(success=success, error=error, status=status)


def _run(gen, *payloads, stop_after=None):
    """
    Drive generator: first next(), then send() for each payload.
    StopIteration is treated as a normal end.
    Returns list of command dicts yielded.
    """
    cmds = []
    try:
        cmd = next(gen)
        cmds.append(cmd.toDict())
        for i, p in enumerate(payloads):
            if stop_after is not None and i >= stop_after:
                break
            cmd = gen.send(p)
            cmds.append(cmd.toDict())
    except StopIteration:
        pass
    return cmds


def _body_items(cmd_dict):
    """Extract list of body item dicts from a CommandUIRender dict."""
    body = cmd_dict["page"]["body"]
    return body if isinstance(body, list) else [body]


def _find_submit_buttons(cmd_dict):
    """Return the first PropsUIDataSubmissionButtons dict in the body, or None."""
    return next(
        (item for item in _body_items(cmd_dict)
         if item["__type__"] == "PropsUIDataSubmissionButtons"),
        None,
    )


def _payload_json(data: dict) -> "_P":
    """Return a PayloadJSON-like object with a JSON-encoded value."""
    return _P("PayloadJSON", json.dumps(data))


# ---------------------------------------------------------------------------
# Auto-donate metadata (no consent required)
# ---------------------------------------------------------------------------

def test_first_command_is_auto_donate():
    """First yield must be a silent metadata donate, not a render."""
    gen = donation_failed_flow("Facebook", "sess1")
    cmd = next(gen).toDict()
    assert cmd["__type__"] == "CommandSystemDonate", (
        f"Expected auto-donate as first command, got {cmd['__type__']}"
    )
    assert cmd["key"] == "error-log"


def test_auto_donate_payload_includes_platform_and_session():
    """Auto-donate payload contains platform and session_id."""
    gen = donation_failed_flow("LinkedIn", "sess-42")
    cmd = next(gen).toDict()
    payload = json.loads(cmd["json_string"])
    assert payload["platform"] == "LinkedIn"
    assert payload["session_id"] == "sess-42"
    assert payload["status"] == "donation_failed"


def test_auto_donate_includes_error_text_when_provided():
    """When an HTTP error string is provided, it appears in the auto-donated metadata."""
    gen = donation_failed_flow("Facebook", "s1", error_text="HTTP 404")
    cmd = next(gen).toDict()
    payload = json.loads(cmd["json_string"])
    assert "HTTP 404" in payload.get("error_text", ""), (
        f"Expected 'HTTP 404' in auto-donate payload, got: {payload}"
    )


# ---------------------------------------------------------------------------
# Consent screen shown after auto-donate
# ---------------------------------------------------------------------------

def test_consent_screen_shown_after_auto_donate():
    """Second yield is a CommandUIRender with the consent screen."""
    gen = donation_failed_flow("Facebook", "sess1", error_text="HTTP 404")
    cmds = _run(gen, None)  # next() → auto-donate; send(None) → consent screen
    assert len(cmds) == 2
    assert cmds[1]["__type__"] == "CommandUIRender"


def test_consent_screen_buttons_differ():
    """Consent screen donate and cancel labels must be different."""
    gen = donation_failed_flow("Facebook", "sess1")
    cmds = _run(gen, None)
    buttons = _find_submit_buttons(cmds[1])
    assert buttons is not None, "No PropsUIDataSubmissionButtons found in consent screen"
    donate_en = buttons["donateButton"]["translations"]["en"]
    cancel_en = buttons["cancelButton"]["translations"]["en"]
    assert donate_en != cancel_en, f"donate and cancel must differ; both are {donate_en!r}"


def test_consent_screen_has_donate_and_skip_buttons():
    """Consent screen donate = Donate, cancel = Skip."""
    gen = donation_failed_flow("Facebook", "sess1")
    cmds = _run(gen, None)
    buttons = _find_submit_buttons(cmds[1])
    assert buttons is not None
    donate_en = buttons["donateButton"]["translations"]["en"].lower()
    cancel_en = buttons["cancelButton"]["translations"]["en"].lower()
    assert "donate" in donate_en or "share" in donate_en, f"Expected donate button, got: {donate_en!r}"
    assert "skip" in cancel_en or "close" in cancel_en, f"Expected skip button, got: {cancel_en!r}"


def test_error_text_appears_in_consent_screen_body():
    """The error text passed in is displayed somewhere in the consent screen body."""
    gen = donation_failed_flow("Facebook", "sess1", error_text="HTTP 404 — Not Found")
    cmds = _run(gen, None)
    page_dict = cmds[1]["page"]
    body_str = json.dumps(page_dict["body"])
    assert "HTTP 404" in body_str, (
        f"Error text not found in consent screen body: {body_str[:400]}"
    )


def test_consent_screen_explanation_text_present():
    """Consent screen contains explanatory text about the error."""
    gen = donation_failed_flow("Facebook", "sess1")
    cmds = _run(gen, None)
    body_str = json.dumps(cmds[1]["page"]["body"]).lower()
    assert "error" in body_str or "fout" in body_str, (
        "Expected explanation text mentioning error"
    )


# ---------------------------------------------------------------------------
# Donate path
# ---------------------------------------------------------------------------

def test_donate_consent_yields_error_report_donation():
    """PayloadJSON on consent screen → tries to donate with key 'error-report'."""
    gen = donation_failed_flow("Facebook", "sess1", error_text="HTTP 404")
    cmds = _run(gen, None, _payload_json({"error_text": "HTTP 404"}))
    types = [c["__type__"] for c in cmds]
    assert "CommandSystemDonate" in types[1:], (  # after the auto-donate
        f"Expected error-report donate after consent, got: {types}"
    )
    donate_cmd = next(
        c for c in cmds[1:] if c["__type__"] == "CommandSystemDonate"
    )
    assert donate_cmd["key"] == "error-report"


def test_donate_consent_payload_has_error_text():
    """The error-report donation payload contains the error text."""
    gen = donation_failed_flow("LinkedIn", "s99", error_text="HTTP 503")
    cmds = _run(gen, None, _payload_json({"error_text": "HTTP 503"}))
    donate_cmd = next(c for c in cmds[1:] if c["__type__"] == "CommandSystemDonate")
    payload = json.loads(donate_cmd["json_string"])
    assert "HTTP 503" in json.dumps(payload)


def test_donate_consent_uses_edited_text():
    """If the participant edits the error text, the edited version is donated."""
    gen = donation_failed_flow("Facebook", "sess1", error_text="HTTP 404")
    cmds = _run(gen, None, _payload_json({"error_text": "HTTP 404 — edited by user"}))
    donate_cmd = next(c for c in cmds[1:] if c["__type__"] == "CommandSystemDonate")
    payload = json.loads(donate_cmd["json_string"])
    assert "edited by user" in payload.get("error_text", ""), (
        f"Donated payload should contain edited text: {payload}"
    )


# ---------------------------------------------------------------------------
# Fallback screen when error-report donation also fails
# ---------------------------------------------------------------------------

def test_donate_consent_then_donate_fails_shows_fallback():
    """If error-report donation also fails, a fallback screen is shown."""
    gen = donation_failed_flow("Facebook", "sess1", error_text="HTTP 404")
    cmds = _run(
        gen,
        None,                                                    # auto-donate → consent screen
        _payload_json({"error_text": "HTTP 404"}),              # consent → error-report donate
        _PayloadResponse(success=False, error="HTTP 404", status=404),  # donate fails
    )
    render_cmds = [c for c in cmds if c["__type__"] == "CommandUIRender"]
    assert len(render_cmds) >= 2, (
        f"Expected at least 2 render commands (consent + fallback), got {len(render_cmds)}"
    )


def test_fallback_screen_contains_error_text():
    """Fallback screen body contains the error text."""
    gen = donation_failed_flow("Facebook", "sess1", error_text="HTTP 404")
    cmds = _run(
        gen,
        None,
        _payload_json({"error_text": "HTTP 404"}),
        _PayloadResponse(success=False, error="HTTP 404", status=404),
    )
    render_cmds = [c for c in cmds if c["__type__"] == "CommandUIRender"]
    fallback = render_cmds[-1]
    body_str = json.dumps(fallback["page"]["body"])
    assert "HTTP 404" in body_str, f"Fallback body does not contain error text: {body_str[:400]}"


# ---------------------------------------------------------------------------
# Skip path
# ---------------------------------------------------------------------------

def test_skip_consent_no_error_report_donation():
    """PayloadFalse on consent screen → no error-report donate is made."""
    gen = donation_failed_flow("Facebook", "sess1")
    cmds = _run(gen, None, _P("PayloadFalse"))
    error_report_donates = [
        c for c in cmds if c["__type__"] == "CommandSystemDonate" and c.get("key") == "error-report"
    ]
    assert not error_report_donates, f"Should not donate error-report on skip, got: {cmds}"


def test_skip_consent_generator_ends():
    """After PayloadFalse on consent, generator ends (StopIteration) — caller continues."""
    gen = donation_failed_flow("Facebook", "sess1")
    next(gen)            # auto-donate
    gen.send(None)       # consent screen
    try:
        gen.send(_P("PayloadFalse"))
        # If we get here, the generator yielded something after Skip.
        # That would be wrong — it should end.
        assert False, "Generator should have stopped after Skip"
    except StopIteration:
        pass  # correct: generator ended
