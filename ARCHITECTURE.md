# Architecture — dd-vu-2026

This repo is a pnpm monorepo forked from [eyra/feldspar](https://github.com/eyra/feldspar).
Eyra's architecture is the reference — follow it unless there is a documented reason not to.

## Package Responsibilities

| Package | Role | Modify when… |
|---------|------|--------------|
| `packages/feldspar` | **Framework library.** Shared UI components, type system, bridge, worker engine. | Almost never. Only for changes that Eyra upstream would also want. |
| `packages/data-collector` | **Host app + researcher customizations.** Custom UI components, custom factories, App.tsx composition. | Adding new UI component types (prompts, visualizations). |
| `packages/python` | **Python processing.** Workflow logic, data extraction, platform-specific code. | Adding/changing donation flow behavior, extraction logic, new platforms. |

**The key rule:** `feldspar` is infrastructure; `data-collector` is where researcher UI customizations go;
`python` is where workflow and extraction logic go. Features should not require modifying `feldspar`
unless the change is genuinely framework-level (and upstreamable to Eyra).

## Python Layer Structure (`packages/python/port/`)

```
port/
├── main.py              ← Entry point. Generator wrapper, error recovery.
│                          DO NOT add business logic here.
│
├── script.py            ← Workflow orchestrator. The "what happens" file.
│                          Calls helpers; NEVER builds pages from raw props.
│
├── api/                 ← Protocol layer. Serializable types for Python↔TS bridge.
│   ├── commands.py      ← Command classes (Render, Donate, Exit, Log)
│   ├── props.py         ← Upstream UI prop classes (mirror TS types)
│   ├── d3i_props.py     ← D3I-custom prop classes (keeps upstream props clean)
│   ├── file_utils.py    ← AsyncFileAdapter (browser File → Python file-like)
│   ├── logging.py       ← Log forwarding handler
│   └── assets.py        ← Static asset access
│
├── helpers/             ← Shared logic used across platforms and script.py.
│   ├── port_helpers.py  ← UI builders: render_page(), donate(), prompt generators.
│   │                      ALL page construction goes through here.
│   ├── extraction_helpers.py ← Data utilities: JSON/CSV parsing, denesting, encoding.
│   ├── validate.py      ← DDP file validation (DDPCategory, StatusCode)
│   └── emoji_pattern.py ← Data file (emoji regex patterns, not executable logic)
│
└── platforms/           ← Per-platform extraction + flow. One file per platform.
    ├── flow_builder.py  ← Abstract base: file→validate→extract→consent→donate template.
    ├── facebook.py      ← DDP_CATEGORIES + *_to_df() extractors + FacebookFlow subclass
    ├── instagram.py
    └── ...              ← (7 active platforms)
```

## Dependency Direction (Python)

```
script.py  →  helpers/*  →  api/*
                  ↑
platforms/*  ────┘
```

- `script.py` may import from `helpers/` and `api/`. It may call `platform.process()`.
- `platforms/*` may import from `helpers/` and `api/`. They MUST NOT import from `script.py`.
- `helpers/*` may import from `api/`. They MUST NOT import from `platforms/` or `script.py`.
- `api/*` imports nothing from this project (only stdlib/third-party).
- **Never import private functions (`_`-prefixed) across layers.**

## Where Code Belongs (Python)

| You need to… | Put it in… | NOT in… |
|---|---|---|
| Build/render a page or prompt | `helpers/port_helpers.py` (a `generate_*()` function) | `script.py` (no raw `props.*` construction) |
| Add a new UI prop class matching a TS type | `api/props.py` (upstream-compatible) or `api/d3i_props.py` (D3I-specific) | Inline in script or helpers |
| Parse/transform data from a DDP file | `helpers/extraction_helpers.py` or per-platform `platforms/*.py` | `script.py` |
| Add per-platform extraction logic | `platforms/<platform>.py` (as `*_to_df()` functions) | `helpers/` |
| Add a reusable flow pattern | `platforms/flow_builder.py` (if it's a template step) or `helpers/port_helpers.py` (if it's a UI builder) | `script.py` |
| Add zip/file diagnostic utilities | `helpers/extraction_helpers.py` | `platforms/flow_builder.py` |
| Orchestrate the multi-platform loop | `script.py` (calling helpers, not building UI) | Anywhere else |

## Where Code Belongs (TypeScript)

| You need to… | Put it in… | NOT in… |
|---|---|---|
| Add a new custom prompt component | `data-collector/src/components/<name>/` (types.ts + component.tsx) | `feldspar/` |
| Add a factory for a custom component | `data-collector/src/factories/<name>.tsx`, register in `App.tsx` | `feldspar/src/.../prompts/factory.ts` |
| Modify an existing feldspar component | **Don't** — wrap or extend it in `data-collector/` instead | Directly editing `feldspar/` source |
| Add a new shared element (button, text variant) | Only if Eyra upstream would want it: `feldspar/src/.../ui/elements/` | — |

## Anti-Patterns to Avoid

1. **Raw page construction in `script.py`.**
   Bad: `body = [props.PropsUIPromptText(...), props.PropsUIPromptTextArea(...)]` in script.py.
   Good: `ph.generate_error_consent_prompt(error_text)` in port_helpers.py, called from script.py.

2. **Modifying `feldspar/` for app-level features.**
   Bad: Adding `TextAreaFactory` to feldspar's default factory list for one feature.
   Good: Adding `TextAreaFactory` in `data-collector/src/factories/`, registered in `App.tsx`.

3. **Cross-layer private imports.**
   Bad: `from port.platforms.flow_builder import _build_error_payload` in script.py.
   Good: Move the function to `helpers/` with a public name, import from there.

4. **Duplicating patterns instead of sharing them.**
   Bad: Error-consent logic written differently in script.py and flow_builder.py.
   Good: Single `generate_error_consent_prompt()` in port_helpers.py used by both.

5. **Modifying shared components without considering all callers.**
   Bad: Adding a cancel button to `Confirm` that shows for every existing usage.
   Good: New component, or make the addition conditional (only render if prop provided).
