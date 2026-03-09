# Infrastructure Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the dd-vu-2026 workflow production-ready on Eyra's mono: visible errors with participant consent to donate error logs, async donation feedback, file safety checks, and alignment with Eyra upstream conventions.

**Architecture:** A single coordinated migration across three layers — the JS worker (`py_worker.js`), the Python bridge (`main.py`), and the Python script/extractor layer (`script.py`). The worker uses AsyncFileAdapter + PayloadFile (Eyra upstream since Nov 2025 — do NOT regress to WORKERFS). The bridge catches all Python exceptions via a state-machine error handler. The script captures donation results and checks file sizes before extraction.

**Tech Stack:** Python 3.11 (Pyodide), pytest + poetry, TypeScript/React, Vite.

---

## Background: Key Files

Before starting, read the design document at `docs/plans/2026-03-09-infrastructure-migration-design.md`. Also orient yourself with:

- `packages/python/port/main.py` — ScriptWrapper (bridge between JS and Python script)
- `packages/python/port/script.py` — main donation flow generator
- `packages/python/port/helpers/port_helpers.py` — `ph.donate()`, `ph.render_page()` helpers
- `packages/python/port/api/props.py` — all UI component dataclasses
- `packages/python/port/api/commands.py` — CommandUIRender, CommandSystemDonate, CommandSystemExit
- `packages/data-collector/public/py_worker.js` — Pyodide web worker (AsyncFileAdapter)
- `packages/data-collector/src/components/error_page/types.ts` — PropsUIPageError TS type
- `packages/data-collector/src/components/error_page/error_page.tsx` — error page React component

Run tests with: `cd packages/python && poetry run pytest -v`
Build with: `cd packages/data-collector && pnpm build` (or `pnpm dev` to check in browser)

---

## Task 1: Fix PropsUIPageError field and py_worker.js (atomic commit)

These three changes must land together because `generateErrorMessage()` uses `"message"` and the TypeScript type must match.

**Files:**
- Modify: `packages/data-collector/src/components/error_page/types.ts`
- Modify: `packages/data-collector/src/components/error_page/error_page.tsx`
- Modify: `packages/data-collector/public/py_worker.js`
- Delete: `packages/data-collector/public/d3i_py_worker.js`

### Step 1: Fix types.ts

In `packages/data-collector/src/components/error_page/types.ts`, change `stacktrace` to `message`:

```typescript
export interface PropsUIPageError {
  __type__: 'PropsUIPageError'
  message: string
}
```

### Step 2: Fix error_page.tsx

In `packages/data-collector/src/components/error_page/error_page.tsx`, find the destructure of `stacktrace` and rename to `message`. It will look something like:

```tsx
// Before:
const { stacktrace } = props
// ...
<BodyLarge text={stacktrace} />

// After:
const { message } = props
// ...
<BodyLarge text={message} />
```

### Step 3: Update py_worker.js — add try/catch and generateErrorMessage

In `packages/data-collector/public/py_worker.js`, replace the `runCycle` function with:

```javascript
function runCycle(payload) {
  console.log("[ProcessingWorker] runCycle " + JSON.stringify(payload));
  try {
    scriptEvent = pyScript.send(payload);
    self.postMessage({
      eventType: "runCycleDone",
      scriptEvent: scriptEvent.toJs({
        create_proxies: false,
        dict_converter: Object.fromEntries,
      }),
    });
  } catch (error) {
    self.postMessage({
      eventType: "runCycleDone",
      scriptEvent: generateErrorMessage(error.toString()),
    });
  }
}
```

Add `generateErrorMessage` at the bottom of `py_worker.js` (before the final newline):

```javascript
function generateErrorMessage(message) {
  return {
    __type__: "CommandUIRender",
    page: {
      __type__: "PropsUIPageDataSubmission",
      platform: "error",
      header: {
        __type__: "PropsUIHeader",
        title: { translations: { nl: "Er is iets misgegaan", en: "Something went wrong" } },
      },
      body: [
        {
          __type__: "PropsUIPageError",
          message: message,
        },
      ],
    },
  };
}
```

### Step 4: Fix platform string in py_worker.js

In `py_worker.js`, find the `firstRunCycle` case. It currently reads:

```javascript
pyScript = self.pyodide.runPython(`port.start(${event.data.sessionId}, "${event.data.platform}")`);
```

Replace with:

```javascript
const platform = event.data.platform;
const pyPlatform = (platform && platform !== "undefined") ? `"${platform}"` : "None";
pyScript = self.pyodide.runPython(`port.start(${event.data.sessionId}, ${pyPlatform})`);
```

### Step 5: Delete d3i_py_worker.js

```bash
git rm packages/data-collector/public/d3i_py_worker.js
```

### Step 6: Verify build

```bash
cd packages/data-collector && pnpm build
```

Expected: build succeeds with no TypeScript errors.

### Step 7: Commit

```bash
git add packages/data-collector/public/py_worker.js \
        packages/data-collector/src/components/error_page/types.ts \
        packages/data-collector/src/components/error_page/error_page.tsx
git rm packages/data-collector/public/d3i_py_worker.js
git commit -m "fix: align PropsUIPageError to message field, add worker error handling"
```

---

## Task 2: Python error handler in main.py

**Files:**
- Modify: `packages/python/port/main.py`
- Create: `packages/python/tests/test_error_handler.py`

### Step 1: Write the failing tests

Create `packages/python/tests/test_error_handler.py`:

```python
"""
Tests for ScriptWrapper error handling in main.py.

These tests mock the `js` module (Pyodide-only) so they can run outside
Pyodide. This is safe because ScriptWrapper's error handler does not call
any js functions — it only uses pure Python props and commands.
"""
import sys
import json
from unittest.mock import MagicMock, patch

# Mock js before importing main (file_utils.py imports js at module level)
sys.modules['js'] = MagicMock()

from port.main import ScriptWrapper, error_flow  # noqa: E402


class FakePayload:
    """Minimal payload object matching the __type__ protocol."""
    def __init__(self, type_, **kwargs):
        self.__type__ = type_
        for k, v in kwargs.items():
            setattr(self, k, v)


def make_crashing_script():
    """Generator that raises RuntimeError on first send."""
    yield  # needed so it's a generator
    raise RuntimeError("test explosion")


def make_consent_script(consent: bool):
    """Generator that raises RuntimeError, then handles consent."""
    data = yield  # first send (None)
    raise RuntimeError("deliberate error")


def drive_wrapper(wrapper, *payloads):
    """Drive the wrapper through a sequence of send() calls, return all results."""
    results = []
    results.append(wrapper.send(None))
    for p in payloads:
        results.append(wrapper.send(p))
    return results


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
```

### Step 2: Run to verify they fail

```bash
cd packages/python && poetry run pytest tests/test_error_handler.py -v
```

Expected: ImportError or AttributeError because `error_flow` doesn't exist yet and `ScriptWrapper` doesn't accept `platform`.

### Step 3: Implement the error handler in main.py

Replace `packages/python/port/main.py` with:

```python
import traceback
import json
import datetime
from collections.abc import Generator

from port.script import process
from port.script import process as process_example
from port.api.commands import CommandSystemExit, CommandUIRender, CommandSystemDonate
from port.api.file_utils import AsyncFileAdapter
import port.api.props as props


def error_flow(platform: str, tb: str):
    """
    Generator that handles a Python exception in the donation flow.

    Yields an error consent page, then optionally donates the error log
    if the participant consents.

    Args:
        platform: Name of the active platform when the error occurred.
        tb: Full traceback string from traceback.format_exc().
    """
    header = props.PropsUIHeader(
        props.Translatable({"nl": "Er is iets misgegaan", "en": "Something went wrong"})
    )
    body = [
        props.PropsUIPromptText(
            text=props.Translatable({"nl": tb, "en": tb})
        ),
        props.PropsUIPromptConfirm(
            text=props.Translatable({
                "nl": "Wilt u de fout rapporteren zodat we het probleem kunnen oplossen?",
                "en": "Would you like to report this error so we can fix the problem?",
            }),
            ok=props.Translatable({"nl": "Fout rapporteren", "en": "Report error"}),
            cancel=props.Translatable({"nl": "Overslaan", "en": "Skip"}),
        ),
    ]
    page = props.PropsUIPageDataSubmission(platform or "error", header, body)
    consent_result = yield CommandUIRender(page)

    if consent_result is not None and getattr(consent_result, "__type__", None) == "PayloadTrue":
        error_data = json.dumps({
            "platform": platform,
            "traceback": tb,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        yield CommandSystemDonate("error-report", error_data)


class ScriptWrapper(Generator):
    def __init__(self, script, platform: str = None):
        self.script = script
        self.platform = platform or "unknown"
        self._error_handler = None

    def send(self, data):
        if self._error_handler is not None:
            try:
                command = self._error_handler.send(data)
                return command.toDict()
            except StopIteration:
                return CommandSystemExit(0, "End of script").toDict()

        # Automatically wrap JS file readers with AsyncFileAdapter
        if data and getattr(data, "__type__", None) == "PayloadFile":
            data.value = AsyncFileAdapter(data.value)

        try:
            command = self.script.send(data)
        except StopIteration:
            return CommandSystemExit(0, "End of script").toDict()
        except Exception:
            tb = traceback.format_exc()
            self._error_handler = error_flow(self.platform, tb)
            command = next(self._error_handler)
            return command.toDict()
        else:
            return command.toDict()

    def throw(self, type=None, value=None, traceback=None):
        raise StopIteration


def start(sessionId, platform=None):
    script = process(sessionId, platform)
    return ScriptWrapper(script, platform=platform)


def start_example(sessionId):
    script = process_example(sessionId)
    return ScriptWrapper(script)
```

### Step 4: Run tests to verify they pass

```bash
cd packages/python && poetry run pytest tests/test_error_handler.py -v
```

Expected: all 5 tests pass.

### Step 5: Run full test suite to check nothing broke

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 6: Commit

```bash
git add packages/python/port/main.py packages/python/tests/test_error_handler.py
git commit -m "feat: add exception handler with error consent flow to ScriptWrapper"
```

---

## Task 3: File safety checks

**Files:**
- Modify: `packages/python/port/script.py` (add exception classes + size checks)
- Create: `packages/python/tests/test_file_safety.py`

### Step 1: Write the failing tests

Create `packages/python/tests/test_file_safety.py`:

```python
"""Tests for file safety checks in script.py."""
import sys
from unittest.mock import MagicMock

sys.modules['js'] = MagicMock()

import pytest
from port.script import FileTooLargeError, ChunkedExportError, check_file_safety

TWO_GB = 2 * 1024 * 1024 * 1024
MAX_BYTES = 200 * 1024 * 1024  # 200 MB


class FakeFile:
    """Minimal file-like object with a size attribute."""
    def __init__(self, size_bytes):
        self.size = size_bytes
        self.name = "test.zip"


def test_normal_file_passes():
    """A file within the size limit passes without raising."""
    f = FakeFile(50 * 1024 * 1024)  # 50 MB
    check_file_safety(f)  # should not raise


def test_file_too_large_raises():
    """A file over the limit raises FileTooLargeError."""
    f = FakeFile(MAX_BYTES + 1)
    with pytest.raises(FileTooLargeError) as exc_info:
        check_file_safety(f)
    assert "200 MB" in str(exc_info.value)


def test_file_too_large_message_mentions_size():
    """FileTooLargeError message includes the actual file size in MB."""
    size = 312 * 1024 * 1024
    f = FakeFile(size)
    with pytest.raises(FileTooLargeError) as exc_info:
        check_file_safety(f)
    assert "312" in str(exc_info.value)


def test_chunked_export_raises():
    """A file at exactly 2 GB raises ChunkedExportError."""
    f = FakeFile(TWO_GB)
    with pytest.raises(ChunkedExportError) as exc_info:
        check_file_safety(f)
    assert "2 GB" in str(exc_info.value)


def test_file_just_under_limit_passes():
    """A file at MAX_BYTES exactly passes (limit is exclusive)."""
    f = FakeFile(MAX_BYTES)
    check_file_safety(f)  # should not raise


def test_file_just_under_two_gb_passes():
    """A file just under 2 GB is not flagged as chunked."""
    f = FakeFile(TWO_GB - 1)
    check_file_safety(f)  # should not raise
```

### Step 2: Run to verify they fail

```bash
cd packages/python && poetry run pytest tests/test_file_safety.py -v
```

Expected: ImportError because `FileTooLargeError`, `ChunkedExportError`, and `check_file_safety` don't exist yet.

### Step 3: Add exception classes and check_file_safety to script.py

At the top of `packages/python/port/script.py`, after the existing imports, add:

```python
# File safety constants and exceptions
_MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB — adjust per-deployment if needed
_CHUNKED_EXPORT_BYTES = 2 * 1024 * 1024 * 1024  # exactly 2 GB


class FileTooLargeError(Exception):
    """Raised when the donated file exceeds the maximum processable size."""


class ChunkedExportError(Exception):
    """
    Raised when the file is exactly 2 GB, indicating a split export.

    Google Takeout and some other platforms split exports at 2 GB boundaries.
    A file at exactly this size is almost certainly an incomplete chunk.
    """


def check_file_safety(file_obj):
    """
    Check file size before extraction.

    Args:
        file_obj: An object with a .size attribute (bytes). This is the
                  AsyncFileAdapter or any file-like with .size.

    Raises:
        ChunkedExportError: If size is exactly 2 GB.
        FileTooLargeError: If size exceeds _MAX_FILE_BYTES.
    """
    size = file_obj.size

    if size == _CHUNKED_EXPORT_BYTES:
        raise ChunkedExportError(
            f"Dit bestand is precies 2 GB groot. Exportbestanden worden soms "
            f"gesplitst bij 2 GB. Dit bestand is waarschijnlijk onvolledig. "
            f"Controleer of u alle exportbestanden heeft. "
            f"(This file is exactly 2 GB. Exports are sometimes split at 2 GB "
            f"boundaries — this file may be incomplete.)"
        )

    size_mb = size // (1024 * 1024)
    max_mb = _MAX_FILE_BYTES // (1024 * 1024)
    if size > _MAX_FILE_BYTES:
        raise FileTooLargeError(
            f"Bestand te groot: {size_mb} MB (maximum: {max_mb} MB). "
            f"Probeer een kleinere export. "
            f"(File too large: {size_mb} MB, maximum: {max_mb} MB.)"
        )
```

### Step 4: Add the check to the script.py flow

In `script.py`, inside the `if file_result.__type__ == "PayloadFile":` block, add the safety check immediately after receiving the file and before calling `flow.validate_file()`:

```python
if file_result.__type__ == "PayloadFile":
    check_file_safety(file_result.value)  # raises FileTooLargeError or ChunkedExportError
    validation = flow.validate_file(file_result.value)
    # ... rest unchanged
```

The exceptions propagate to `ScriptWrapper`'s `except Exception` handler automatically.

### Step 5: Run tests

```bash
cd packages/python && poetry run pytest tests/test_file_safety.py -v
```

Expected: all 6 tests pass.

### Step 6: Run full suite

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 7: Commit

```bash
git add packages/python/port/script.py packages/python/tests/test_file_safety.py
git commit -m "feat: add file size and chunked export safety checks"
```

---

## Task 4: Capture PayloadResponse from donations

**Files:**
- Modify: `packages/python/port/script.py`
- Modify: `packages/data-collector/.env.example`
- Create: `packages/python/tests/test_donation_response.py`

### Background

`ph.donate(key, json_str)` returns a `CommandSystemDonate`. When yielded with `VITE_ASYNC_DONATIONS=true`, the JS bridge awaits the HTTP response and sends back a `PayloadResponse` object with:
- `__type__`: `"PayloadResponse"`
- `value.success`: bool
- `value.key`: str
- `value.status`: HTTP status code
- `value.error`: str (on failure only)

When `VITE_ASYNC_DONATIONS=false` (D3I's mono, fire-and-forget), the yield returns `None` or a `PayloadVoid`. The check must handle both cases.

### Step 1: Write the failing tests

Create `packages/python/tests/test_donation_response.py`:

```python
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
```

### Step 2: Run to verify they fail

```bash
cd packages/python && poetry run pytest tests/test_donation_response.py -v
```

Expected: ImportError because `handle_donate_result` doesn't exist.

### Step 3: Add handle_donate_result to script.py

Add this function near the top of `script.py` (after the exception classes, before `process()`):

```python
def handle_donate_result(result) -> bool:
    """
    Inspect the result of a yield ph.donate() call.

    Returns True (success) if:
    - result is None (VITE_ASYNC_DONATIONS=false, fire-and-forget)
    - result is not a PayloadResponse (unexpected type, treat as success)
    - result is PayloadResponse with success=True

    Returns False (failure) if:
    - result is PayloadResponse with success=False
    """
    if result is None:
        return True
    if getattr(result, "__type__", None) != "PayloadResponse":
        return True
    return bool(result.value.success)
```

### Step 4: Use handle_donate_result in the donation loop

In `script.py`, in the consent and donation section, update the donate calls to capture and check the result. Find this block:

```python
if consent_result.__type__ == "PayloadJSON":
    logger.info("Data donated for %s", platform_name)
    yield ph.donate(f"{session_id}-{platform_name.lower()}", consent_result.value)
elif consent_result.__type__ == "PayloadFalse":
    yield ph.donate(
        f"{session_id}-{platform_name.lower()}",
        json.dumps({"status": "donation declined"}),
    )
```

Replace with:

```python
if consent_result.__type__ == "PayloadJSON":
    logger.info("Data donated for %s", platform_name)
    donate_result = yield ph.donate(
        f"{session_id}-{platform_name.lower()}", consent_result.value
    )
    if not handle_donate_result(donate_result):
        logger.error("Donation failed for %s: %s", platform_name, donate_result)
        yield ph.render_page(
            props.Translatable({
                "nl": "Verzenden mislukt",
                "en": "Upload failed",
            }),
            props.PropsUIPromptConfirm(
                text=props.Translatable({
                    "nl": "Uw gegevens konden niet worden opgestuurd. "
                          "Neem contact op met de onderzoekers.",
                    "en": "Your data could not be sent. "
                          "Please contact the research team.",
                }),
                ok=props.Translatable({"nl": "Sluiten", "en": "Close"}),
                cancel=props.Translatable({"nl": "Sluiten", "en": "Close"}),
            ),
        )
        return
elif consent_result.__type__ == "PayloadFalse":
    donate_result = yield ph.donate(
        f"{session_id}-{platform_name.lower()}",
        json.dumps({"status": "donation declined"}),
    )
    # decline donations are fire-and-forget; ignore result
```

Note: `return` inside a generator raises `StopIteration`, which `ScriptWrapper` converts to `CommandSystemExit`. The participant sees the failure message then the session ends.

### Step 5: Run tests

```bash
cd packages/python && poetry run pytest tests/test_donation_response.py -v
```

Expected: all 4 tests pass.

### Step 6: Run full suite

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 7: Update .env.example

In `packages/data-collector/.env.example`, ensure the `VITE_ASYNC_DONATIONS` section reads:

```
# VITE_ASYNC_DONATIONS: controls whether the bridge awaits donation confirmation.
#
# true  — for Eyra's mono: donations go via HTTP POST; bridge awaits
#          DonateSuccess/DonateError response; script.py receives PayloadResponse.
#          Use this for VU 2026 and all Eyra platform deployments.
#
# false — for D3I's mono: donations go via WebSocket (fire-and-forget);
#          no response is sent; script.py receives None.
#          Use this if deploying to d3i-infra/mono.
#
VITE_ASYNC_DONATIONS=true
```

(Change from commented-out to active `=true`.)

### Step 8: Commit

```bash
git add packages/python/port/script.py \
        packages/python/tests/test_donation_response.py \
        packages/data-collector/.env.example
git commit -m "feat: capture PayloadResponse from donations, enable VITE_ASYNC_DONATIONS"
```

---

## Task 5: Dead code cleanup

**Files:**
- Modify: `packages/python/port/helpers/extraction_helpers.py`

### Step 1: Find and delete json_dumper

In `packages/python/port/helpers/extraction_helpers.py`, find the `json_dumper` function. It references `unzipddp` which does not exist anywhere in the codebase. Delete the entire function (and any imports that are only used by it).

To confirm it's unused:
```bash
grep -r "json_dumper" packages/python/
```

Expected: only the definition itself — no callers.

### Step 2: Run full suite to confirm nothing broke

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

### Step 3: Commit

```bash
git add packages/python/port/helpers/extraction_helpers.py
git commit -m "chore: remove dead json_dumper function"
```

---

## Verification Checklist

After all tasks are complete:

- [ ] `cd packages/python && poetry run pytest -v` — all tests pass
- [ ] `cd packages/data-collector && pnpm build` — build succeeds, no TypeScript errors
- [ ] `d3i_py_worker.js` is deleted (`git status` shows it gone)
- [ ] `json_dumper` is gone from `extraction_helpers.py`
- [ ] `VITE_ASYNC_DONATIONS=true` is uncommented in `.env.example`
- [ ] `PropsUIPageError` TypeScript type uses `message`, not `stacktrace`
- [ ] `py_worker.js` has `try/catch` in `runCycle()` and `generateErrorMessage()` using `"message"`
- [ ] `main.py` has `error_flow` generator and `ScriptWrapper._error_handler` state machine
- [ ] `script.py` has `check_file_safety()`, `FileTooLargeError`, `ChunkedExportError`, `handle_donate_result()`

## D3I Compatibility Note

`VITE_ASYNC_DONATIONS=true` is set for Eyra deployments. If this repo later becomes
the basis for `d3i-infra/data-donation-task`, set `VITE_ASYNC_DONATIONS=false` for
D3I builds (D3I's mono has no HTTP endpoint and never sends donation responses).
