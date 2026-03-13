# CLAUDE.md — dd-vu-2026

- **Never commit to `master`** — use `feat/*` / `fix/*` / `chore/*` + PR
- Use `superpowers:using-git-worktrees` before executing any plan

## Tests
```bash
cd packages/python && poetry run pytest -v
cd packages/data-collector && pnpm build   # TypeScript check
```

## Forbidden
- **Never commit** `.zip`, DDP files, or anything in `tests/data/`, `tests/fixtures/`, `received_files/`
- Real DDPs: `~/data/d3i/test_packages/port-vu/` — outside repo, never in tests

## Rules
- DataFrame columns shown in consent UI must be **Dutch**
- `release.sh` builds all 7 platforms: LinkedIn, Instagram, Chrome, Facebook, YouTube, TikTok, X
- `sys.modules['js'] = MagicMock()` must precede all `from port...` imports in tests
- `Translatable.toDict()` → `{"translations": {"nl": ...}}` not `{"text": {"nl": ...}}`

## Commands
```bash
pnpm run start                  # dev server at localhost:3000
bash release.sh                 # build all 7 platforms → releases/*.zip
```

## Packages
- `packages/python` — Python extraction scripts (per-platform, script.py)
- `packages/feldspar` — workflow UI framework (React/TypeScript)
- `packages/data-collector` — host app / dev server

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for package responsibilities, dependency rules,
and where new code belongs. Key points:
- `feldspar/` is upstream infrastructure — almost never modify it
- Custom UI components go in `data-collector/`, not `feldspar/`
- `script.py` calls helpers — it never builds pages from raw props
- Python dependency direction: `script.py → helpers/ → api/` (never reverse)
