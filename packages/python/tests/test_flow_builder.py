"""
Tests for FlowBuilder.start_flow() generator behaviour and retry prompt UX.

sys.modules['js'] mock required for Pyodide-only import in file_utils.
"""
import sys
import io
import zipfile

from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

from port.platforms.flow_builder import FlowBuilder
from port.helpers import validate as validate_mod
from port.helpers.port_helpers import generate_retry_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _P:
    """Minimal stand-in for a JS payload object."""
    def __init__(self, type_str, value=None):
        self.__type__ = type_str
        self.value = value


def _make_zip_buf(entries: list[str] | None = None) -> io.BytesIO:
    """Return an in-memory zip BytesIO (default: one JSON file)."""
    if entries is None:
        entries = ["data/test.json"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for e in entries:
            zf.writestr(e, "{}")
    buf.seek(0)
    return buf


def _make_invalid_validator():
    """Return a ValidateInput that reports status_code=1 (invalid)."""
    v = MagicMock(spec=validate_mod.ValidateInput)
    v.get_status_code_id.return_value = 1
    return v


class _InvalidFlow(FlowBuilder):
    """Concrete FlowBuilder whose validate_file always returns invalid."""
    def validate_file(self, file):  # pyright: ignore[reportUnusedParameter]
        return _make_invalid_validator()

    def extract_data(self, file, validation):  # pyright: ignore[reportUnusedParameter]
        return []


def _drive(gen, *payloads):
    """Drive a generator: first next(), then send() for each payload.

    Returns a list of command dicts in the order they were yielded.
    """
    cmds = []
    cmd = next(gen)
    cmds.append(cmd.toDict())
    for p in payloads:
        cmd = gen.send(p)
        cmds.append(cmd.toDict())
    return cmds


# ---------------------------------------------------------------------------
# Bug 1: Skip on retry → error report consent → EXIT (no data review screen)
# ---------------------------------------------------------------------------

def test_skip_retry_shows_error_report_consent():
    """After Skip on retry prompt, the error report consent screen is shown."""
    flow = _InvalidFlow("sess1", "TestPlatform")
    gen = flow.start_flow()

    cmds = _drive(
        gen,
        _P("PayloadFile", _make_zip_buf()),   # file submitted (invalid)
        _P("PayloadFalse"),                    # Skip on retry prompt
    )

    # cmds[0] = file prompt, cmds[1] = retry prompt, cmds[2] = error report consent
    assert len(cmds) == 3, f"Expected 3 renders, got {len(cmds)}: {[c['__type__'] for c in cmds]}"
    assert cmds[2]["__type__"] == "CommandUIRender"
    # Error report header contains "error" or "fout" (Dutch)
    page = cmds[2]["page"]
    header_title = page["header"]["title"]["translations"]
    assert (
        "error" in header_title.get("en", "").lower()
        or "fout" in header_title.get("nl", "").lower()
    ), f"Expected error report header, got: {header_title}"


def test_skip_retry_no_data_review_after_error_consent():
    """After Skip → error report consent → decline, flow exits without data review."""
    flow = _InvalidFlow("sess1", "TestPlatform")
    gen = flow.start_flow()

    cmds = _drive(
        gen,
        _P("PayloadFile", _make_zip_buf()),   # invalid file
        _P("PayloadFalse"),                    # Skip on retry
        _P("PayloadFalse"),                    # Decline error report consent
    )

    # After declining error consent, next command must be CommandSystemExit
    # (not another CommandUIRender for data review)
    last = cmds[-1]
    assert last["__type__"] == "CommandSystemExit", (
        f"Expected CommandSystemExit after error consent decline, got {last['__type__']}"
    )


def test_skip_retry_donate_error_report_then_exit():
    """After Skip → error report consent → donate, flow donates then exits (no data review)."""
    flow = _InvalidFlow("sess1", "TestPlatform")
    gen = flow.start_flow()

    # After yielding the donate command the generator needs one more send(None)
    # to resume past the yield and reach exit. Pass None as the 4th payload.
    cmds = _drive(
        gen,
        _P("PayloadFile", _make_zip_buf()),   # invalid file
        _P("PayloadFalse"),                    # Skip on retry
        _P("PayloadTrue"),                     # Accept error report donation
        None,                                  # resume past donate → should yield exit
    )

    # Should see: file prompt, retry prompt, error consent, donate, exit
    types = [c["__type__"] for c in cmds]
    assert "CommandSystemDonate" in types, f"Expected a donate command, got: {types}"
    assert types[-1] == "CommandSystemExit", f"Expected exit as last command, got: {types[-1]}"


# ---------------------------------------------------------------------------
# Bug 2: Retry prompt text must match the two-button layout
# ---------------------------------------------------------------------------

def test_retry_prompt_text_does_not_say_continue():
    """'Continue' is not a button; text should not instruct the user to 'Continue'."""
    prompt = generate_retry_prompt("Facebook")
    text_en = prompt.text.translations["en"]
    assert "Continue, if you are sure" not in text_en, (
        f"Retry prompt EN text still says 'Continue, if you are sure': {text_en!r}"
    )


def test_retry_prompt_text_mentions_try_again_or_skip():
    """Text should describe both actions available: try again and skip."""
    prompt = generate_retry_prompt("Facebook")
    text_en = prompt.text.translations["en"].lower()
    assert "try again" in text_en or "select a different" in text_en, (
        f"Retry prompt EN text does not mention retrying: {prompt.text.translations['en']!r}"
    )
    assert "skip" in text_en or "skip this step" in text_en, (
        f"Retry prompt EN text does not mention skipping: {prompt.text.translations['en']!r}"
    )
