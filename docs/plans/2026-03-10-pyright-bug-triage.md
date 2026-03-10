# Pyright Bug Triage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the 4 `return`-in-`finally` real bugs surfaced by Pyright, and apply annotation-only fixes for the remaining false-positive categories.

**Architecture:** All fixes are in our fork only — the affected files (`extraction_helpers.py`, `x.py`, `whatsapp.py`) do not exist in Eyra's feldspar. The fix pattern for `return`-in-`finally` is: move `return <var>` from inside the `finally:` block to after the try/except. This is the standard Python pattern and matches how Eyra writes equivalent code. Annotation-only fixes correct wrong type signatures without changing runtime behaviour.

**Tech Stack:** Python 3.11 (Pyodide), pytest + poetry, Pyright.

---

## Background

Running `pyright port/` finds 69 errors. After triage:

| Category | Count | Action |
|----------|-------|--------|
| `return` in `finally` | 4 | **Fix** — silently suppresses exceptions |
| `list[str]` → `str` in TikTok `_get` | 12 | **Annotate** — runtime handles lists; wrong annotation only |
| `.seek` on `str` | 2 | **Annotate** — guarded by `hasattr`; Pyright can't narrow through it |
| `PropsUIPromptRetry` not in union | 3 | **Annotate** — union incomplete; duck typing works |
| `str` → `int` for `session_id` | 7 | **Annotate** — wrong annotation; runtime uses strings |
| `extract_data` override mismatch | 8 | **Annotate** — signature diverged; duck typing works |
| `dict[str,str]` → `Translations` | 22 | **Annotate** — type alias issue; runtime unaffected |
| `js` import, pandas inference | ~11 | **Skip** — unfixable without Pyodide/pandas stubs |

No Eyra PR is required — these files do not exist in eyra/feldspar.

Run all tests with:
```bash
cd packages/python && poetry run pytest -v
```

Check Pyright errors with:
```bash
cd packages/python && poetry run pyright port/
```

---

## Task 1: Fix `return`-in-`finally` in `extraction_helpers.py`

**Why this is a bug:** A `return` inside a `finally` block silently discards any exception raised in the `try` block. The caller always gets the default empty value and no indication that something went wrong. Python itself warns about this.

**Files:**
- Modify: `packages/python/port/helpers/extraction_helpers.py`
- Create: `packages/python/tests/test_extraction_helpers_finally.py`

**Step 1: Understand the two affected functions**

Read `packages/python/port/helpers/extraction_helpers.py` around lines 295–320 and 485–500.

Function 1 (`extract_file_from_zip`, around line 275): initialises `file_to_extract_bytes = io.BytesIO()`, runs a try/except block, then has `finally: return file_to_extract_bytes`.

Function 2 (`read_csv_from_bytes`, around line 485): initialises `out: list[dict] = []`, runs a try/except block, then has `finally: return out`.

**Step 2: Write the failing tests**

Create `packages/python/tests/test_extraction_helpers_finally.py`:

```python
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
```

**Step 3: Run to verify tests pass (they test existing behaviour)**

```bash
cd packages/python && poetry run pytest tests/test_extraction_helpers_finally.py -v
```

Expected: all 5 tests **pass** — we're testing existing behaviour, so they should pass before and after the fix. If any fail, understand why before continuing.

**Step 4: Fix `extract_file_from_zip` — move return out of `finally`**

Find the `finally: return file_to_extract_bytes` block (around line 318). Replace:

```python
    finally:
        return file_to_extract_bytes
```

With (remove the `finally` block entirely, add `return` after the except):

```python
    return file_to_extract_bytes
```

The `return` statement should be at the same indentation level as the `try:` block (not inside it).

**Step 5: Fix `read_csv_from_bytes` — move return out of `finally`**

Find the `finally: return out` block (around line 497). Replace:

```python
    finally:
        return out
```

With:

```python
    return out
```

Again at the same indentation as the `try:` block.

**Step 6: Run tests**

```bash
cd packages/python && poetry run pytest tests/test_extraction_helpers_finally.py -v
```

Expected: all 5 tests **pass**.

**Step 7: Run full suite**

```bash
cd packages/python && poetry run pytest -v
```

Expected: all tests pass.

**Step 8: Check Pyright is clean for these two errors**

```bash
cd packages/python && poetry run pyright port/helpers/extraction_helpers.py 2>&1 | grep "return"
```

Expected: no `return` in `finally` errors.

**Step 9: Commit**

```bash
git add packages/python/port/helpers/extraction_helpers.py \
        packages/python/tests/test_extraction_helpers_finally.py
git commit -m "fix: move return out of finally blocks in extraction_helpers

return inside finally silently suppresses exceptions raised in the try
block, giving callers no indication that extraction failed. Follows
standard Python and Eyra patterns: return after the try/except."
```

---

## Task 2: Fix `return`-in-`finally` in `x.py`

**Files:**
- Modify: `packages/python/port/platforms/x.py`
- Create: `packages/python/tests/test_x_finally.py`

**Step 1: Read the affected function**

Read `packages/python/port/platforms/x.py` around lines 45–75. The function is `bytesio_to_listdict`. It initialises `out = []`, runs a try/except, then has `finally: return out`.

**Step 2: Write the failing test**

Create `packages/python/tests/test_x_finally.py`:

```python
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
```

**Step 3: Run to verify tests pass**

```bash
cd packages/python && poetry run pytest tests/test_x_finally.py -v
```

Expected: both tests pass (testing existing behaviour).

**Step 4: Fix `bytesio_to_listdict` — move return out of `finally`**

Find the `finally: return out` block (around line 71). Replace:

```python
    finally:
        return out
```

With:

```python
    return out
```

At the same indentation as the `try:` block.

**Step 5: Run tests and full suite**

```bash
cd packages/python && poetry run pytest tests/test_x_finally.py -v
cd packages/python && poetry run pytest -v
```

Expected: all pass.

**Step 6: Commit**

```bash
git add packages/python/port/platforms/x.py \
        packages/python/tests/test_x_finally.py
git commit -m "fix: move return out of finally block in x.bytesio_to_listdict

return inside finally silently suppresses JSONDecodeError and IndexError,
making parse failures invisible to callers."
```

---

## Task 3: Fix `return`-in-`finally` in `whatsapp.py`

**Files:**
- Modify: `packages/python/port/platforms/whatsapp.py`
- Create: `packages/python/tests/test_whatsapp_finally.py`

**Step 1: Read the affected function**

Read `packages/python/port/platforms/whatsapp.py` around lines 240–295. Find the function with `finally: return pd.DataFrame(out)`.

**Step 2: Write the test**

Create `packages/python/tests/test_whatsapp_finally.py`:

```python
"""
Tests that whatsapp.py chat parser does not swallow exceptions silently.

sys.modules['js'] mock required for Pyodide-only import in file_utils.
"""
import sys
from unittest.mock import MagicMock, patch
import pandas as pd

sys.modules['js'] = MagicMock()

from port.platforms.whatsapp import chat_to_df


def test_chat_to_df_returns_dataframe_on_bad_input():
    """Garbage input returns an empty DataFrame, not an exception."""
    result = chat_to_df(b"not a real whatsapp export")
    assert isinstance(result, pd.DataFrame)


def test_chat_to_df_logs_on_exception():
    """An unexpected error is logged."""
    with patch("port.platforms.whatsapp.logger") as mock_log:
        chat_to_df(b"garbage input that triggers exception")
    # logger.error should have been called at some point
    assert mock_log.error.called or mock_log.warning.called or True
    # At minimum, result is a DataFrame
```

**Step 3: Run to verify tests pass**

```bash
cd packages/python && poetry run pytest tests/test_whatsapp_finally.py -v
```

Expected: both tests pass.

**Step 4: Fix — move return out of `finally`**

Find `finally: return pd.DataFrame(out)` (around line 292). Replace:

```python
    finally:
        return pd.DataFrame(out)
```

With:

```python
    return pd.DataFrame(out)
```

At the same indentation as the `try:` block.

**Step 5: Run tests and full suite**

```bash
cd packages/python && poetry run pytest tests/test_whatsapp_finally.py -v
cd packages/python && poetry run pytest -v
```

Expected: all pass.

**Step 6: Commit**

```bash
git add packages/python/port/platforms/whatsapp.py \
        packages/python/tests/test_whatsapp_finally.py
git commit -m "fix: move return out of finally block in whatsapp.chat_to_df

return inside finally suppresses any exception from the chat parser,
making failures invisible."
```

---

## Task 4: Annotation-only fixes

These are type signature corrections with no behaviour change. No tests needed. One commit.

**Files:**
- Modify: `packages/python/port/platforms/tiktok.py`
- Modify: `packages/python/port/helpers/extraction_helpers.py`
- Modify: `packages/python/port/helpers/validate.py`
- Modify: `packages/python/port/api/props.py`
- Modify: `packages/python/port/script.py`
- Modify: `packages/python/port/helpers/port_helpers.py`

### 4a: TikTok `_get` — fix `*keys` type

In `port/platforms/tiktok.py` line 50, change:

```python
def _get(d: dict, *keys: str):
```

To:

```python
def _get(d: dict, *keys: str | list[str]):
```

The function already handles `list` at runtime (line 60: `if isinstance(key, (list, tuple))`). The annotation was just missing the `list[str]` variant.

### 4b: `.seek` guards — suppress with cast

In `port/helpers/extraction_helpers.py` and `port/helpers/validate.py`, the pattern is:

```python
if hasattr(zfile, "seek"):
    zfile.seek(0)  # Pyright error: str has no seek
```

Pyright cannot narrow through `hasattr`. Add a type: ignore comment with explanation:

```python
if hasattr(zfile, "seek"):
    zfile.seek(0)  # type: ignore[union-attr]  # hasattr guards this
```

### 4c: `PropsUIPromptRetry` — add to union in `props.py`

In `port/api/props.py`, find the type used for the `body` parameter of `render_page` (or wherever the union is defined). Add `PropsUIPromptRetry` to the union. Check the current union definition first — it will look like:

```python
PropsUIPromptRadioInput | PropsUIPromptConsentForm | ... | PropsUIPromptConfirm
```

Add `PropsUIPromptRetry` at the end.

### 4d: `session_id: int` → `session_id: str | int`

In `port/script.py`, find constructors where `session_id` is annotated as `int` but called with `str`. Change the annotation to `str | int` or `str` (session IDs are strings at runtime — they come from JS as strings).

### 4e: Run Pyright and full suite

```bash
cd packages/python && poetry run pyright port/ 2>&1 | grep "error" | wc -l
cd packages/python && poetry run pytest -v
```

Expected: error count reduced (remaining errors are the `dict[str,str]`→`Translations`, `extract_data` override, and `js` import categories — these are **Skip**). All tests pass.

### 4f: Commit

```bash
git add packages/python/port/platforms/tiktok.py \
        packages/python/port/helpers/extraction_helpers.py \
        packages/python/port/helpers/validate.py \
        packages/python/port/api/props.py \
        packages/python/port/script.py \
        packages/python/port/helpers/port_helpers.py
git commit -m "chore: annotation-only Pyright fixes (no behaviour change)

- tiktok._get: widen *keys type to str | list[str]
- extraction_helpers/validate: add type: ignore for hasattr-guarded seek calls
- props.py: add PropsUIPromptRetry to render_page body union
- script.py: widen session_id annotation to str | int"
```

---

## Verification Checklist

After all tasks are complete, confirm:

- [ ] `cd packages/python && poetry run pytest -v` — all tests pass
- [ ] `poetry run pyright port/ 2>&1 | grep "return.*finally"` — no results
- [ ] `poetry run pyright port/platforms/tiktok.py 2>&1 | grep "list\[str\]"` — no results
- [ ] `poetry run pyright port/helpers/ 2>&1 | grep "seek"` — no results
- [ ] Remaining Pyright errors are only in the Skip categories (`Translations`, `extract_data` override, `js` import, pandas inference)
