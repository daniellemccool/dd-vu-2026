# Facebook DDP Error Handling Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three bugs: broken retry loop UI, spurious empty table in Facebook extraction, and add a skip→error-report donation path when a file can't be processed.

**Architecture:** Align retry UX with Eyra upstream (`PropsUIPromptConfirm` replaces `PropsUIPromptRetry`); restore cancel button in `Confirm.tsx`; add `_build_error_payload()` helper and error-report consent flow in `FlowBuilder`; guard `last_28_days_to_df` against empty JSON response.

**Tech Stack:** Python 3.11 (poetry), React/TypeScript (pnpm), pytest, Pyodide-aware test pattern (`sys.modules['js'] = MagicMock()` before all `port.*` imports)

---

## Chunk 1: Setup and Python fixes

### Task 1: Create worktree and branch

- [ ] **Step 1.1: Create worktree**

  From the repo root:
  ```bash
  git worktree add ../dd-vu-2026-facebook-errors feat/facebook-ddp-error-handling
  cd ../dd-vu-2026-facebook-errors
  ```

- [ ] **Step 1.2: Verify clean state**

  ```bash
  git status
  # Expected: clean, on branch feat/facebook-ddp-error-handling
  cd packages/python && poetry run pytest -v
  # Expected: all tests pass
  ```

---

### Task 2: `_build_error_payload` — TDD

**Files:**
- Create: `packages/python/tests/test_facebook_error_handling.py`
- Modify: `packages/python/port/platforms/flow_builder.py`

- [ ] **Step 2.1: Write failing tests for `_build_error_payload`**

  Create `packages/python/tests/test_facebook_error_handling.py`:

  ```python
  """
  Tests for Facebook DDP error handling helpers.

  sys.modules['js'] mock required for Pyodide-only import in file_utils.
  """
  import sys
  import io
  import json
  import zipfile

  from unittest.mock import MagicMock

  sys.modules['js'] = MagicMock()

  from port.platforms.flow_builder import _build_error_payload


  def _make_zip(entries: list[str]) -> io.BytesIO:
      """Create an in-memory zip with empty files at the given paths."""
      buf = io.BytesIO()
      with zipfile.ZipFile(buf, "w") as zf:
          for entry in entries:
              zf.writestr(entry, b"")
      buf.seek(0)
      return buf


  def test_build_error_payload_html_export():
      """Zip with >50% .html files is detected as html_export."""
      entries = [f"export/file{i}.html" for i in range(8)] + ["export/readme.txt", "export/data.json"]
      buf = _make_zip(entries)
      payload = _build_error_payload(buf, "Facebook")
      assert payload["detected_format"] == "html_export"
      assert payload["status"] == "file_format_not_supported"
      assert payload["platform"] == "Facebook"
      assert payload["zip_size_bytes"] > 0
      assert "export" in payload["top_level_folders"]


  def test_build_error_payload_data_logs():
      """Zip with data_logs/ prefix is detected as data_logs_json."""
      entries = [
          "data_logs/content/0/page_1.json",
          "data_logs/content/1/page_1.json",
          "readme.txt",
      ]
      buf = _make_zip(entries)
      payload = _build_error_payload(buf, "Facebook")
      assert payload["detected_format"] == "data_logs_json"
      assert sorted(payload["top_level_folders"]) == ["data_logs", "readme.txt"]


  def test_build_error_payload_unknown():
      """Zip with mixed non-HTML files is detected as unknown."""
      entries = ["some_folder/file.json", "some_folder/other.csv"]
      buf = _make_zip(entries)
      payload = _build_error_payload(buf, "Facebook")
      assert payload["detected_format"] == "unknown"


  def test_build_error_payload_top_level_folders_deduped():
      """top_level_folders contains unique top-level entries, sorted."""
      entries = [
          "folderA/a.json",
          "folderA/b.json",
          "folderB/c.json",
          "readme.txt",
      ]
      buf = _make_zip(entries)
      payload = _build_error_payload(buf, "TestPlatform")
      assert payload["top_level_folders"] == ["folderA", "folderB", "readme.txt"]


  def test_build_error_payload_exactly_50pct_html_is_not_html_export():
      """Exactly 50% HTML does NOT trigger html_export (requires >50%)."""
      entries = ["a.html", "b.html", "c.json", "d.json"]
      buf = _make_zip(entries)
      payload = _build_error_payload(buf, "Facebook")
      assert payload["detected_format"] != "html_export"


  def test_build_error_payload_empty_zip():
      """Empty zip (zero entries) returns detected_format='unknown' and empty top_level_folders."""
      buf = _make_zip([])
      payload = _build_error_payload(buf, "Facebook")
      assert payload["detected_format"] == "unknown"
      assert payload["top_level_folders"] == []
  ```

- [ ] **Step 2.2: Run tests — verify they fail**

  ```bash
  cd packages/python
  poetry run pytest tests/test_facebook_error_handling.py -v
  # Expected: ImportError — cannot import name '_build_error_payload' from 'port.platforms.flow_builder'
  ```

- [ ] **Step 2.3: Implement `_build_error_payload` in `flow_builder.py`**

  Add `import io`, `import os`, `import zipfile`, `from pathlib import Path` to the existing imports at the top of `packages/python/port/platforms/flow_builder.py`:

  ```python
  import io
  import os
  import zipfile
  from pathlib import Path
  ```

  Then add this module-level function immediately before the `FlowBuilder` class definition:

  ```python
  def _build_error_payload(zip_path: "str | io.BinaryIO", platform_name: str) -> dict:
      """
      Inspect a zip file and return a machine-readable error payload describing
      why it was rejected. Safe to call with a file path or a seekable file-like object.
      """
      if hasattr(zip_path, "seek"):
          zip_path.seek(0, 2)
          size = zip_path.tell()
          zip_path.seek(0)
      else:
          size = os.path.getsize(zip_path)

      names: list[str] = []
      try:
          if hasattr(zip_path, "seek"):
              zip_path.seek(0)
          with zipfile.ZipFile(zip_path, "r") as zf:
              names = zf.namelist()
          if hasattr(zip_path, "seek"):
              zip_path.seek(0)
      except Exception:
          pass

      # Top-level entries: first component of each path
      top_level = sorted({Path(n).parts[0] for n in names if n})

      # Format detection
      if names and sum(1 for n in names if n.endswith(".html")) / len(names) > 0.5:
          detected = "html_export"
      elif any(n.startswith("data_logs/") for n in names):
          detected = "data_logs_json"
      else:
          detected = "unknown"

      return {
          "status": "file_format_not_supported",
          "platform": platform_name,
          "detected_format": detected,
          "zip_size_bytes": size,
          "top_level_folders": top_level,
      }
  ```

- [ ] **Step 2.4: Run tests — verify they pass**

  ```bash
  poetry run pytest tests/test_facebook_error_handling.py -v
  # Expected: 6 passed
  ```

- [ ] **Step 2.5: Commit**

  ```bash
  git add packages/python/tests/test_facebook_error_handling.py packages/python/port/platforms/flow_builder.py
  git commit -m "feat: add _build_error_payload helper for DDP format detection"
  ```

---

### Task 3: Fix `last_28_days_to_df` spurious row — TDD

**Files:**
- Modify: `packages/python/tests/test_facebook_error_handling.py`
- Modify: `packages/python/port/platforms/facebook.py`

- [ ] **Step 3.1: Write failing test**

  Append to `packages/python/tests/test_facebook_error_handling.py`:

  ```python
  from port.platforms.facebook import last_28_days_to_df


  def test_last_28_days_returns_empty_when_file_missing():
      """No spurious rows when the expected JSON file is absent from the zip."""
      # Zip with no matching file
      buf = _make_zip(["some_other_file.json"])
      result = last_28_days_to_df(buf)  # type: ignore[arg-type]  # BytesIO accepted at runtime via extract_file_from_zip
      assert result.empty, f"Expected empty DataFrame, got {len(result)} rows"
  ```

- [ ] **Step 3.2: Run test — verify it fails**

  ```bash
  poetry run pytest tests/test_facebook_error_handling.py::test_last_28_days_returns_empty_when_file_missing -v
  # Expected: FAIL — assertion error, DataFrame has 1 row with empty string
  ```

- [ ] **Step 3.3: Fix `last_28_days_to_df` in `facebook.py`**

  In `packages/python/port/platforms/facebook.py`, locate `last_28_days_to_df` (around line 166). After `d = eh.read_json_from_bytes(b)`, add an early return:

  ```python
  def last_28_days_to_df(facebook_zip: str) -> pd.DataFrame:

      b = eh.extract_file_from_zip(facebook_zip, "your_facebook_watch_activity_in_the_last_28_days.json")
      d = eh.read_json_from_bytes(b)

      out = pd.DataFrame()
      datapoints = []

      if not d:
          return out

      try:
          ...  # rest of function unchanged
  ```

  Only the `if not d: return out` guard is new — everything else stays identical.

- [ ] **Step 3.4: Run tests — verify all pass**

  ```bash
  poetry run pytest tests/test_facebook_error_handling.py -v
  # Expected: 7 passed
  ```

- [ ] **Step 3.5: Run full test suite**

  ```bash
  poetry run pytest -v
  # Expected: all tests pass
  ```

- [ ] **Step 3.6: Commit**

  ```bash
  git add packages/python/tests/test_facebook_error_handling.py packages/python/port/platforms/facebook.py
  git commit -m "fix: guard last_28_days_to_df against empty JSON response"
  ```

---

## Chunk 2: Retry UX wiring

### Task 4: Update `port_helpers.py`

**Files:**
- Modify: `packages/python/port/helpers/port_helpers.py`

No new tests needed here — this is plumbing used by `FlowBuilder`; the integration is tested via the flow.

- [ ] **Step 4.1: Replace `generate_retry_prompt` and add `generate_error_report_prompt`**

  In `packages/python/port/helpers/port_helpers.py`, replace the `generate_retry_prompt` function and add the new `generate_error_report_prompt` function. Also update the `render_page` type hint to remove the dead `PropsUIPromptRetry` union arm.

  **First, add `import json` to the top-level imports block in `port_helpers.py`** (after line 1, alongside `import port.api.props as props`):

  ```python
  import json
  ```

  **Replace `generate_retry_prompt` (lines 48–73):**

  ```python
  def generate_retry_prompt(platform_name: str) -> props.PropsUIPromptConfirm:
      """
      Generate a bilingual retry prompt for file processing errors.

      Returns a PropsUIPromptConfirm with two buttons:
        ok ("Probeer opnieuw") → PayloadTrue  → caller continues the retry loop
        cancel ("Overslaan")   → PayloadFalse → caller exits the loop

      Args:
          platform_name (str): The name of the platform.
      """
      text = props.Translatable({
          "en": f"Unfortunately, we cannot process your {platform_name} file. Continue, if you are sure that you selected the right file. Try again to select a different file.",
          "nl": f"Helaas, kunnen we uw {platform_name} bestand niet verwerken. Weet u zeker dat u het juiste bestand heeft gekozen? Ga dan verder. Probeer opnieuw als u een ander bestand wilt kiezen."
      })
      ok = props.Translatable({
          "en": "Try again",
          "nl": "Probeer opnieuw"
      })
      cancel = props.Translatable({
          "en": "Skip",
          "nl": "Overslaan"
      })
      return props.PropsUIPromptConfirm(text, ok, cancel)
  ```

  **Add `generate_error_report_prompt` immediately after `generate_retry_prompt`:**

  ```python
  def generate_error_report_prompt(payload_dict: dict) -> props.PropsUIPromptConfirm:
      """
      Generate a consent prompt showing the machine-readable error payload.

      The participant sees exactly what would be donated before deciding.

      Args:
          payload_dict: The error payload dict from _build_error_payload().

      Returns:
          PropsUIPromptConfirm with ok=Donate, cancel=Skip.
      """
      payload_text = json.dumps(payload_dict, indent=2)
      text = props.Translatable({
          "en": payload_text,
          "nl": payload_text,
      })
      ok = props.Translatable({
          "en": "Donate",
          "nl": "Doneer"
      })
      cancel = props.Translatable({
          "en": "Skip",
          "nl": "Sla over"
      })
      return props.PropsUIPromptConfirm(text, ok, cancel)
  ```

  **Update the `render_page` type hint** — remove `d3i_props.PropsUIPromptRetry` from the union (lines 13–22). The updated union:

  ```python
  def render_page(
      header_text: props.Translatable,
      body: (
          props.PropsUIPromptRadioInput
          | props.PropsUIPromptConsentForm
          | d3i_props.PropsUIPromptConsentFormViz
          | props.PropsUIPromptFileInput
          | d3i_props.PropsUIPromptFileInputMultiple
          | d3i_props.PropsUIPromptQuestionnaire
          | props.PropsUIPromptConfirm
      )
  ) -> CommandUIRender:
  ```

- [ ] **Step 4.2: Run tests — verify nothing broken**

  ```bash
  cd packages/python && poetry run pytest -v
  # Expected: all pass
  ```

- [ ] **Step 4.3: Commit**

  ```bash
  git add packages/python/port/helpers/port_helpers.py
  git commit -m "fix: replace PropsUIPromptRetry with PropsUIPromptConfirm in retry prompt, add error report prompt helper"
  ```

---

### Task 5: Update `flow_builder.py` — retry result capture and error report flow

**Files:**
- Modify: `packages/python/port/platforms/flow_builder.py`

- [ ] **Step 5.1: Add error report UI text to `_initialize_ui_text`**

  In `packages/python/port/platforms/flow_builder.py`, in `_initialize_ui_text()`, add a new entry to `self.UI_TEXT` after `"retry_header"`:

  ```python
  "error_report_header": props.Translatable({
      "en": "Error report",
      "nl": "Foutrapport"
  }),
  ```

- [ ] **Step 5.2: Modify `start_flow` retry block**

  In `start_flow()`, replace the current retry block (lines 72–76):

  ```python
  # Enter retry flow
  if validation.get_status_code_id() != 0:
      logger.info(f"Not a valid {self.platform_name} file; No payload; prompt retry_confirmation")
      retry_prompt = self.generate_retry_prompt()
      yield ph.render_page(self.UI_TEXT["retry_header"], retry_prompt)
  ```

  With:

  ```python
  # Enter retry flow
  if validation.get_status_code_id() != 0:
      logger.info(f"Not a valid {self.platform_name} file; No payload; prompt retry_confirmation")
      retry_prompt = self.generate_retry_prompt()
      retry_result = yield ph.render_page(self.UI_TEXT["retry_header"], retry_prompt)

      # PayloadTrue (try again) → falls through to next loop iteration (no else needed).
      # PayloadFalse (skip) → offer error report donation, then exit.
      if retry_result.__type__ == "PayloadFalse":
          error_payload = _build_error_payload(file_result.value, self.platform_name)
          consent_result = yield ph.render_page(
              self.UI_TEXT["error_report_header"],
              ph.generate_error_report_prompt(error_payload)
          )
          if consent_result.__type__ == "PayloadTrue":
              yield ph.donate(str(self.session_id), json.dumps(error_payload))
          break
  ```

  The `break` exits the `while True` loop after the error report path (whether donated or skipped). `PayloadTrue` (try again) falls through to the next iteration of `while True`, re-prompting for a file.

- [ ] **Step 5.3: Run tests**

  ```bash
  cd packages/python && poetry run pytest -v
  # Expected: all pass
  ```

- [ ] **Step 5.4: Commit**

  ```bash
  git add packages/python/port/platforms/flow_builder.py
  git commit -m "feat: capture retry result, add skip→error report donation path in FlowBuilder"
  ```

---

### Task 6: Fix `confirm.tsx` — restore cancel button

**Files:**
- Modify: `packages/feldspar/src/framework/visualization/react/ui/prompts/confirm.tsx`

Reference: `/home/dmm/src/d3i/eyra/feldspar/packages/feldspar/src/framework/visualization/react/ui/prompts/confirm.tsx` — the target state matches Eyra exactly.

- [ ] **Step 6.1: Replace `confirm.tsx`**

  Replace the full content of `packages/feldspar/src/framework/visualization/react/ui/prompts/confirm.tsx` with:

  ```tsx
  import { Weak } from '../../../../helpers'
  import { ReactFactoryContext } from '../../factory'
  import { PropsUIPromptConfirm } from '../../../../types/prompts'
  import { Translator } from '../../../../translator'
  import { BodyLarge } from '../elements/text'
  import { PrimaryButton } from '../elements/button'
  import { JSX } from 'react'
  import React from 'react'

  type Props = Weak<PropsUIPromptConfirm> & ReactFactoryContext

  export const Confirm = (props: Props): JSX.Element => {
    const { resolve } = props
    const { text, ok, cancel } = prepareCopy(props)

    function handleOk (): void {
      resolve?.({ __type__: 'PayloadTrue', value: true })
    }

    function handleCancel (): void {
      resolve?.({ __type__: 'PayloadFalse', value: false })
    }

    return (
      <>
        <BodyLarge text={text} margin='mb-4' />
        <div className='flex flex-row gap-4'>
          <PrimaryButton label={ok} onClick={handleOk} color='text-grey1 bg-tertiary' />
          <PrimaryButton label={cancel} onClick={handleCancel} color='text-white bg-primary' />
        </div>
      </>
    )
  }

  interface Copy {
    text: string
    ok: string
    cancel: string
  }

  function prepareCopy ({ text, ok, cancel, locale }: Props): Copy {
    return {
      text: Translator.translate(text, locale),
      ok: Translator.translate(ok, locale),
      cancel: Translator.translate(cancel, locale)
    }
  }
  ```

- [ ] **Step 6.2: TypeScript build check**

  ```bash
  cd packages/data-collector && pnpm build
  # Expected: build succeeds with no TypeScript errors
  ```

- [ ] **Step 6.3: Commit**

  ```bash
  git add packages/feldspar/src/framework/visualization/react/ui/prompts/confirm.tsx
  git commit -m "fix: restore cancel button in Confirm component (align with Eyra upstream)"
  ```

---

### Task 7: Final verification

- [ ] **Step 7.1: Full Python test suite**

  ```bash
  cd packages/python && poetry run pytest -v
  # Expected: all tests pass, no regressions
  ```

- [ ] **Step 7.2: TypeScript build**

  ```bash
  cd packages/data-collector && pnpm build
  # Expected: clean build
  ```

- [ ] **Step 7.3: Open PR**

  Use `superpowers:finishing-a-development-branch` or `commit-commands:commit-push-pr`.

  PR title: `fix: Facebook DDP error handling — retry UX, error report donation, last_28_days guard`

  PR body should reference the three bugs fixed and note the Eyra alignment for `confirm.tsx`.
