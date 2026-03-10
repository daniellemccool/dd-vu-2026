# Pyright Bug Triage — Design Document

**Date:** 2026-03-10
**Branch:** `fix/pyright-real-bugs`
**Goal:** Identify and fix runtime-risky bugs surfaced by Pyright; upstream confirmed fixes to Eyra's feldspar.

---

## Background

Running `pyright port/` reveals 69 errors across 8 categories. Most are type-annotation mismatches that work fine at runtime. A subset represent genuine Python bugs — code that would raise an exception or silently produce wrong output. This document defines how to triage and fix those bugs.

Eyra's own Python package has 47 Pyright errors and no CI enforcement, so a zero-error target is out of scope here. The scope is: **find real bugs, fix them the way Eyra would, PR the shared-file fixes upstream.**

---

## Triage Categories

| Category | Count | Verdict | Rationale |
|----------|-------|---------|-----------|
| `return` in `finally` block | 4 | **Fix** | Silently suppresses exceptions — confirmed Python anti-pattern. Eyra's feldspar does not use this pattern; implement their approach. |
| `list[str]` → `str` in `_get` (TikTok) | 12 | **Investigate** | Depends on what `_get` does with its argument at runtime. Our TikTok rewrite — stays in fork. |
| `.seek` on `str` | 2 | **Investigate** | Would raise `AttributeError` at runtime if a string reaches that codepath. |
| `PropsUIPromptRetry` not in union | 3 | **Annotate** | Union type is incomplete; duck typing works at runtime. |
| `str` → `int` for `session_id` | 7 | **Annotate** | Annotation is wrong; session IDs are strings at runtime. |
| `extract_data` override mismatch | 8 | **Annotate** | Signature diverged from base class; duck typing works. |
| `dict[str,str]` → `Translations` | 22 | **Annotate** | Type alias resolution issue; runtime unaffected. |
| `js` import, pandas/numpy inference | ~11 | **Skip** | Unfixable without Pyodide stubs or pandas-stubs. |

---

## Workflow Per "Fix" Item

1. Read the code to confirm the runtime risk is real.
2. Check Eyra's `feldspar/develop` (or relevant feature branch) for how they handle the same code.
3. Implement Eyra's solution where one exists — this makes the upstream PR easy to justify.
4. If Eyra hasn't fixed it: write a failing test first, then fix, then verify.
5. Confirm full test suite still passes.

## Workflow Per "Annotate" Item

1. Fix the type signature only — no behavior change, no test required.
2. These stay in our fork; they are not submitted to Eyra.

## Workflow Per "Skip" Item

Leave as-is. Do not add `# type: ignore` unless a future CI requirement forces it.

---

## Branch and Commit Structure

**Our fork:** `fix/pyright-real-bugs`
- One commit per bug category (e.g. `fix: return-in-finally suppresses exceptions`)
- Each "Fix" commit includes a test demonstrating the bug and its resolution
- "Annotate" commits contain only type signature changes

**Eyra PR:** cherry-pick only the "Fix" commits that touch files shared with upstream (`extraction_helpers.py`, `validate.py`, `x.py`, `whatsapp.py`, etc.). Platform files that are our additions (TikTok rewrite) stay in our fork only.

---

## Files in Scope

**Confirmed "Fix" targets (shared with Eyra):**
- `port/helpers/extraction_helpers.py` — `return` in `finally` (lines 319, 498); `.seek` on `str` (line 297)
- `port/helpers/validate.py` — `.seek` on `str` (line 233)
- `port/platforms/x.py` — `return` in `finally` (line 72)
- `port/platforms/whatsapp.py` — `return` in `finally` (line 293)

**Confirmed "Fix" targets (our fork only):**
- `port/platforms/tiktok.py` — `_get` signature investigation (lines 86–310)

**"Annotate" targets:**
- `port/api/props.py` — `Translations` type alias
- `port/script.py` — `session_id: int` annotation
- `port/helpers/port_helpers.py` — `RadioItem` list
- `port/platforms/*/flow_builder.py` — `extract_data` override signatures
- `port/platforms/*/script.py` — `PropsUIPromptRetry` union

---

## Eyra Alignment Principle

Before writing any fix, check `eyra/feldspar develop`. If Eyra's code does not exhibit the bug (e.g. they removed `return`-in-`finally`), implement their exact pattern. This serves two purposes:

1. Our fix is immediately recognisable to Eyra reviewers.
2. Future upstream syncs won't reintroduce the bug.
