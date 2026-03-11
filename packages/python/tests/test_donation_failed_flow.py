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


def _drive_flow(gen, *payloads):
    """Drive generator: next() then send() for each payload.

    Returns command dicts. StopIteration is treated as a normal end.
    """
    cmds = []
    cmd = next(gen)
    cmds.append(cmd.toDict())
    for p in payloads:
        try:
            cmd = gen.send(p)
            cmds.append(cmd.toDict())
        except StopIteration:
            break
    return cmds


# ---------------------------------------------------------------------------
# The upload-failed screen must NOT have two identical buttons
# ---------------------------------------------------------------------------

def test_donation_failed_shows_error_consent_not_two_close_buttons():
    """Upload failed screen offers error report consent — ok ≠ cancel."""
    gen = donation_failed_flow("Facebook", "sess42")
    cmd = next(gen).toDict()

    assert cmd["__type__"] == "CommandUIRender"
    body = cmd["page"]["body"]
    confirm = next(
        (item for item in (body if isinstance(body, list) else [body])
         if item["__type__"] == "PropsUIPromptConfirm"),
        None,
    )
    assert confirm is not None, "Expected PropsUIPromptConfirm in body"
    ok_en = confirm["ok"]["translations"]["en"]
    cancel_en = confirm["cancel"]["translations"]["en"]
    assert ok_en != cancel_en, (
        f"ok and cancel labels must differ; both are {ok_en!r}"
    )


def test_donation_failed_consent_true_donates_error_report():
    """If participant consents, a donation with status=donation_failed is made."""
    gen = donation_failed_flow("Facebook", "sess42")
    cmds = _drive_flow(gen, _P("PayloadTrue"))

    types = [c["__type__"] for c in cmds]
    assert "CommandSystemDonate" in types, f"Expected donate command, got: {types}"

    donate_cmd = next(c for c in cmds if c["__type__"] == "CommandSystemDonate")
    payload = json.loads(donate_cmd["json_string"])
    assert payload["status"] == "donation_failed"
    assert payload["platform"] == "Facebook"
    assert donate_cmd["key"] == "error-report"


def test_donation_failed_consent_false_no_donation():
    """If participant declines, no donation is made and the generator ends."""
    gen = donation_failed_flow("Facebook", "sess42")
    cmds = _drive_flow(gen, _P("PayloadFalse"))

    types = [c["__type__"] for c in cmds]
    assert "CommandSystemDonate" not in types, (
        f"Should not donate when consent declined, got: {types}"
    )


def test_donation_failed_payload_includes_session_id():
    """Error report payload includes the session_id."""
    gen = donation_failed_flow("LinkedIn", "session-xyz")
    cmds = _drive_flow(gen, _P("PayloadTrue"))

    donate_cmd = next(c for c in cmds if c["__type__"] == "CommandSystemDonate")
    payload = json.loads(donate_cmd["json_string"])
    assert payload["session_id"] == "session-xyz"
    assert payload["platform"] == "LinkedIn"
