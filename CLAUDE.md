# CLAUDE.md — dd-vu-2026

Researcher fork of D3I data-donation-task for VU 2026 study.
See `docs/plans/` for design docs and implementation plans.

## Branch Workflow (REQUIRED)

**Never commit directly to `master`.** All work goes in a branch:

1. Create branch: `feat/<name>` or `fix/<name>` or `chore/<name>`
2. Use `superpowers:using-git-worktrees` before executing any implementation plan
3. Open a PR to `master` when done
4. The established pattern: fix/* branches merged via PR (see PRs #84–#89)

## Running Tests

```bash
cd packages/python && poetry run pytest -v
cd packages/data-collector && pnpm build   # TypeScript check
```

## Python / Pyodide Gotchas

- **Test isolation**: `sys.modules['js'] = MagicMock()` must come before any `from port...` import in test files (`file_utils.py` imports `js` at module level)
- **Translatable shape**: `Translatable.toDict()` returns `{"translations": {"nl": ..., "en": ...}}` — test assertions use `["translations"]["nl"]`, not `["text"]["nl"]`
- **File size limit**: `_MAX_FILE_BYTES = 2 GB` — Pyodide handles up to 2 GB in-browser

## Test Data Policy (CRITICAL)

**Never commit DDP files, received files, or any data derived from real participant data.**

- `.zip` files, `tests/data/`, `tests/fixtures/`, `received_files/` are all gitignored
- Real DDPs live at `~/data/d3i/test_packages/port-vu/` (outside repo, never committed)
- Received/donated files live at `~/data/d3i/test_packages/port-vu/received_files/<date>/`
- Tests must use synthetic/mocked data only — never real participant exports

## Column Language Policy

All DataFrame column headers shown to participants in the consent UI must be in **Dutch**. YouTube already uses Dutch; LinkedIn, X, Instagram, Chrome, TikTok, Facebook are pending migration.

## Platform Build Pattern

`release.sh` loops over platforms, sets `VITE_PLATFORM`, builds, zips.
Active platforms: LinkedIn, Instagram, Chrome, Facebook, YouTube, TikTok, X.
