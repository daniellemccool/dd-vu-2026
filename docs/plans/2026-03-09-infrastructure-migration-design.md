# Infrastructure Migration Design

## Goal

A single coordinated migration that makes the dd-vu-2026 data donation workflow
production-ready on Eyra's mono platform: visible errors with participant consent
to donate error logs, async donation feedback, file safety checks, and alignment
with current Eyra upstream conventions.

## Context and Constraints

- **Deployment target**: Eyra's Next (mono) platform — not D3I's mono
- **D3I compatibility**: Changes that break compatibility with D3I's mono must be
  documented. This repo will eventually form the basis of a new
  `d3i-infra/data-donation-task`; incompatibilities will need reconciling then.
- **Upstream alignment**: Track Eyra's `feldspar` develop branch where possible,
  and the `feature/live_error_handling` draft (PR #612) where it represents the
  clear upstream direction.
- **File I/O**: Eyra replaced WORKERFS + PayloadString with AsyncFileAdapter +
  PayloadFile on 2025-11-03 (commit 0b2a8c9, PR #482) specifically to fix
  large-file memory crashes. The dd-vu-2026 fork already has this. Do not regress
  to WORKERFS.

---

## Architecture Overview

Three layers with clear responsibility boundaries:

**JS Worker layer** (`py_worker.js`): mounts files via AsyncFileAdapter
(FileReaderSync wrapper), sends `PayloadFile` to Python. Catches worker-level JS
crashes and renders a static error page. Handles async donation responses when
`VITE_ASYNC_DONATIONS=true`.

**Python bridge layer** (`main.py`): the boundary between JS and Python script
logic. Receives `PayloadFile`, wraps it in `AsyncFileAdapter`, passes to the
script generator. Catches all unhandled exceptions, yields an interactive error
consent page, optionally donates the error log, terminates gracefully.

**Python script/extractor layer** (`script.py` + platform extractors): pure
Python business logic. Raises typed exceptions for known bad conditions. No
try/except logic lives here — all error UX wiring lives in `main.py`.

---

## Section 1: Python Error Handler and Consent Page

### Two error paths

**JS-layer crashes** (worker crash, postMessage failure — Python cannot run):
`generateErrorMessage()` in `py_worker.js` yields a static `PropsUIPageError`
with field `message` containing the JS error string. No interactivity possible.
This is the terminal error display.

**Python-layer errors** (all exceptions during script execution):
`ScriptWrapper.send()` catches them and delegates to a stateful error flow
generator. This is the interactive path with donation consent.

### ScriptWrapper state machine

`ScriptWrapper` gains an `_error_handler` slot (initially `None`). When an
exception is caught, an `error_flow` generator is created and stored there. All
subsequent `send()` calls are routed to it until it exhausts (at which point
`ScriptWrapper` returns `CommandSystemExit`).

```
Normal:  ScriptWrapper.send() → script.send() → command dict
Error:   script raises Exception
         → capture traceback.format_exc()
         → create error_flow(platform, traceback)
         → route remaining send() calls through error_flow
```

### error_flow generator

```
yield error consent page (PropsUIPageDataSubmission)
← receive consent response (PayloadBoolean from PropsUIPromptConfirm)
if True:
    yield CommandSystemDonate("error-report", {platform, traceback, timestamp})
    ← receive PayloadResponse (if VITE_ASYNC_DONATIONS=true)
generator ends → ScriptWrapper sends CommandSystemExit
```

### Error consent page layout

Uses only existing component primitives — no new components required:

- Page type: `PropsUIPageDataSubmission`
- Header: `{"nl": "Er is iets misgegaan", "en": "Something went wrong"}`
- Body (list):
  - `PropsUIPromptText(text=traceback_string)` — raw traceback, same in both
    languages. Needs CSS treatment for monospace/scrollable rendering in the
    React component (implementation detail, not a structural change).
  - `PropsUIPromptConfirm(ok="Fout rapporteren", cancel="Overslaan")`
- Error donation key: `"error-report"`
- Error donation payload: `{"platform": str, "traceback": str, "timestamp": str}`

### PropsUIPageError field fix

`packages/data-collector/src/components/error_page/types.ts` currently has
`stacktrace: string`. Python's `props.py` sends `message`. Eyra's
`feature/live_error_handling` branch also uses `message`. Fix: rename `stacktrace`
→ `message` in the TypeScript type and the React component that destructures it.
The `generateErrorMessage()` addition to `py_worker.js` must also use `"message"`.
These must land in the same commit.

---

## Section 2: Worker Improvements

### What stays

`py_worker.js` is the correct active worker — AsyncFileAdapter + PayloadFile,
aligned with Eyra upstream since 2025-11-03. `main.py`'s AsyncFileAdapter
wrapping, `file_utils.py`, and `script.py`'s `PayloadFile` check all stay.

### What changes in py_worker.js

Three improvements ported from `d3i_py_worker.js` (which used the abandoned
WORKERFS approach and must be deleted, but contained these useful additions):

1. **try/catch in `runCycle()`** — currently crashes in `runCycle()` propagate
   silently. Wrap `pyScript.send(payload)` and postMessage in try/catch; on error,
   call `generateErrorMessage(error.toString())` and post that instead.

2. **`generateErrorMessage(message)`** — constructs a `CommandUIRender` containing
   a `PropsUIPageDataSubmission` page with `PropsUIPageError` as a body item.
   Uses field `"message"` (not `"stacktrace"`).

3. **Platform string fix** — current code: `` `port.start(${sessionId}, "${platform}")` ``
   always quotes the platform value, so an unset platform becomes the string
   `"undefined"` in Python instead of `None`. Fix: guard before quoting:
   ```js
   const pyPlatform = (platform && platform !== 'undefined')
     ? `"${platform}"`
     : 'None'
   // then: port.start(${sessionId}, ${pyPlatform})
   ```

### d3i_py_worker.js

Delete. It is an old WORKERFS prototype, was never activated, and its approach
was superseded upstream. Its three useful additions are ported into `py_worker.js`
as above.

---

## Section 3: Async Donations and Delivery Feedback

### Build configuration

`VITE_ASYNC_DONATIONS=true` is the committed default for VU 2026 (Eyra
deployment). Document in `.env.example`:
- `true`: for Eyra's mono — HTTP POST path, awaits `DonateSuccess`/`DonateError`
- `false` (default): for D3I's mono — fire-and-forget WebSocket path, no response

### script.py: capture PayloadResponse

`yield from ph.donate(key, json_str)` currently discards the return value.
Capture it. On `success: False`: yield a donation-failure page and end the flow.

### Donation failure page

Distinct from the processing error page. No traceback (network/server error, not
a code failure), no donation consent (nothing to donate). Use
`PropsUIPageDataSubmission` with `PropsUIPromptText` body:

> "Uw gegevens konden niet worden opgestuurd. Neem contact op met de onderzoekers."

Followed by end of flow. No interactive buttons beyond the implicit exit.

### Implementation note

The exact syntax for capturing `ph.donate()`'s return value depends on how the
generator helper is structured in `commands.py`. Verify before writing
implementation steps.

---

## Section 4: File Safety Checks

### Location

`script.py`, immediately after receiving the file from `ph.file_input()`, before
any extraction. `AsyncFileAdapter` exposes `.size` and `.name` — no file reading
required.

### FileTooLargeError

Raised if `file.size` exceeds a module-level threshold constant. Exception message
is written in plain Dutch + English including the actual size and limit:

> `FileTooLargeError: Bestand te groot: 312 MB (maximum: 200 MB). Probeer een kleinere export.`

Threshold is a constant, configurable per-platform if needed. Initial value TBD
during implementation (suggest 200 MB as a starting point for VU 2026 platforms).

### ChunkedExportError

Raised if `file.size == 2 * 1024 * 1024 * 1024` exactly. Google Takeout and some
platforms split exports at 2 GB boundaries; an exact 2 GB file is almost certainly
an incomplete export chunk. Exception message explains this in plain terms.

Treated as a hard stop for now, consistent with the single-error-page design.
Softening to a warning with "continue anyway" is a future refinement.

### Error routing

Both exceptions propagate to `ScriptWrapper`'s `except Exception` handler
(Section 1). No special casing — the error consent page renders with the exception
message as the displayed text. For known errors the message is participant-readable;
for unknown errors it is a technical traceback.

---

## Section 5: Code Cleanup

Three items, no architectural implications:

**Delete `json_dumper()` from `extraction_helpers.py`**: references `unzipddp`
which does not exist anywhere in the codebase. Dead code.

**Fix `stacktrace` → `message`** in `error_page/types.ts` and `error_page.tsx`.
(Covered under Section 1 — must land in same commit as `generateErrorMessage()`.)

**Delete `d3i_py_worker.js`**. (Covered under Section 2.)

**Row caps**: `PropsUIPromptConsentFormTable.__post_init__` already applies the
10,000-row cap at Python construction time — before serialization, before
donation. This is functionally at the extraction layer. `chrome.py`'s additional
`.head(10_000)` is redundant but harmless. No change needed.

---

## D3I Compatibility Notes

Changes in this migration that affect D3I's mono compatibility:

| Change | Impact on D3I's mono |
|--------|----------------------|
| `VITE_ASYNC_DONATIONS=true` | D3I's mono has no HTTP endpoint and never sends `DonateSuccess`/`DonateError`. With `true`, the bridge waits forever for a response that never comes. Must be set to `false` for D3I builds. Document in `.env.example`. |
| AsyncFileAdapter + PayloadFile | D3I's mono does not interact with the worker directly — no impact. |
| Error consent page flow | No impact — purely client-side. |

When this repo is used as the basis for a new `d3i-infra/data-donation-task`,
`VITE_ASYNC_DONATIONS` handling will need per-deployment configuration or a
different build matrix.

---

## Files Affected

| File | Change |
|------|--------|
| `packages/data-collector/public/py_worker.js` | Add try/catch in runCycle(), add generateErrorMessage() with `message` field, fix platform string |
| `packages/data-collector/public/d3i_py_worker.js` | **Delete** |
| `packages/data-collector/src/components/error_page/types.ts` | `stacktrace` → `message` |
| `packages/data-collector/src/components/error_page/error_page.tsx` | `stacktrace` → `message` |
| `packages/data-collector/.env.example` | Document VITE_ASYNC_DONATIONS=true for Eyra, false for D3I |
| `packages/python/port/main.py` | Add except Exception handler, error_flow generator, remove PayloadFile/AsyncFileAdapter import |
| `packages/python/port/api/props.py` | No change (message field already correct) |
| `packages/python/port/helpers/extraction_helpers.py` | Delete json_dumper() |
| `packages/python/port/script.py` | Add file safety checks, capture PayloadResponse from ph.donate() |
