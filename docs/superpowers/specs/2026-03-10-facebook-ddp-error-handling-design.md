# Facebook DDP Error Handling — Design Spec

**Date:** 2026-03-10
**Status:** Approved

## Problem

Three Facebook DDPs fail silently or badly:

1. **Unrecognised format** (`data_logs/…` JSON structure) — validation correctly rejects it, but the retry loop has no escape hatch. `PropsUIPromptRetry` has no TypeScript factory, so the page crashes with `TypeError: No factory found for body item`.
2. **HTML export (large)** — passes validation as a false-positive because `no-data.txt` files inflate the score. All extraction functions fail silently; `last_28_days_to_df` emits a spurious 1-row empty table.
3. **HTML export (few JSON files)** — validation correctly rejects it, same dead-end retry loop as case 1.

User expectation: the file loads, or the participant can submit an error report and move on.

## Root Cause Summary

| Bug | Root cause |
|-----|-----------|
| "Probeer opnieuw" dead-end | `PropsUIPromptRetry` has no TypeScript factory; our fork also dropped the cancel button from `Confirm.tsx` (regression from Eyra upstream) |
| HTML export false-positive | `no-data.txt` in `known_files` three times; HTML exports have many such files, inflating the validation score past the 5% threshold |
| Spurious empty table | `last_28_days_to_df`: `dict_denester({})` + `find_item` returns `""` → `datapoints.append(("",))` → non-empty DataFrame |

## Fixes

### Fix A — Retry UX (align with Eyra + skip→error report path)

**Eyra's pattern:** `PropsUIPromptConfirm` (two buttons: ok=try again, cancel=continue) — no `PropsUIPromptRetry` exists upstream. Our fork regressed by (a) introducing `PropsUIPromptRetry` with no TypeScript handler, and (b) dropping the cancel button from `Confirm.tsx`.

**TypeScript — `confirm.tsx`:**
Restore the cancel button (align with Eyra). `handleCancel` resolves `PayloadFalse`.

**Python — `port_helpers.generate_retry_prompt()`:**
Replace `PropsUIPromptRetry` with `PropsUIPromptConfirm`:
- `ok` = "Probeer opnieuw" / "Try again"
- `cancel` = "Overslaan" / "Skip"

**Python — `flow_builder.start_flow()`:**
Capture retry result. `PayloadTrue` → continue loop. `PayloadFalse` → enter error report consent flow:

1. Call `_build_error_payload(zip_path, platform_name)` which opens the zip once and returns:
   ```json
   {
     "status": "file_format_not_supported",
     "platform": "<platform_name>",
     "detected_format": "<html_export|data_logs_json|unknown>",
     "zip_size_bytes": 1234567,
     "top_level_folders": ["meta-2026-Mar-02-17-05-58"]
   }
   ```
   Format detection rules (applied to zip namelist):
   - >50% of files end in `.html` → `"html_export"`
   - Any entry starts with `data_logs/` → `"data_logs_json"`
   - Otherwise → `"unknown"`

2. Show `PropsUIPromptConfirm` with:
   - `text` = the JSON payload string (participant sees exactly what would be donated)
   - `ok` = "Doneer" / "Donate"
   - `cancel` = "Sla over" / "Skip"

3. `PayloadTrue` → `yield ph.donate(session_id, json_payload)` then exit
   `PayloadFalse` → exit without donating

`PropsUIPromptRetry` in `d3i_props.py` is left in place as dead code (removal is a separate cleanup).

---

### Fix B — Validation false-positive (`no-data.txt` in `known_files`)

**Deferred.** Removing `no-data.txt` from `known_files` may break valid exports. Needs separate investigation.

---

### Fix C — `last_28_days_to_df` spurious row

In `last_28_days_to_df`, add `if not d: return out` immediately after `d = eh.read_json_from_bytes(b)`.

This is the only extraction function affected — all others use `d["key"]` which raises `KeyError` on an empty dict, caught by the existing `except` block.

## Files Changed

| File | Change |
|------|--------|
| `packages/feldspar/src/framework/visualization/react/ui/prompts/confirm.tsx` | Restore cancel button (align with Eyra) |
| `packages/python/port/helpers/port_helpers.py` | `generate_retry_prompt()` → use `PropsUIPromptConfirm` with cancel text |
| `packages/python/port/platforms/flow_builder.py` | Capture retry result; add `_build_error_payload()`; add error consent flow |
| `packages/python/port/platforms/facebook.py` | Fix `last_28_days_to_df` guard |

## Testing

- Unit test: `_build_error_payload` returns correct `detected_format` for HTML zip, `data_logs` zip, and unknown zip
- Unit test: `last_28_days_to_df` returns empty DataFrame when zip has no matching file
- Manual: upload each of the three failing DDPs; verify retry prompt renders with two buttons; verify skip path shows payload and donate/skip buttons
