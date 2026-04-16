---
name: spec-skill
description: Use when the user asks to sync specs, pull upper-tier specs from GitHub, update spec lock, run spec check, or initialise openspec. Triggers the spec sync/check/init workflow directly via bundled Python scripts without requiring the spec CLI to be installed.
---

# spec-skill

## Overview

Runs spec commands (`sync`, `check`, `init`) directly via bundled Python scripts located at:

```
C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py
```

No `pip install` required — scripts are self-contained and loaded via `sys.path`.

## When to Use

- User says "sync specs", "run spec sync", "pull specs", or "update specs"
- User says "check specs", "run spec check", or "verify compliance"
- User says "init specs" or "initialise openspec"
- User wants to refresh the `openspec/merged/` artifacts

## Script Location

```
C:\Users\cmk\.claude\skills\spec-skill\scripts\
├── run_spec.py          ← entry point (run this)
└── spec_cli\
    ├── __init__.py
    ├── cli.py
    ├── config.py
    ├── github.py
    ├── merger.py
    ├── parser.py
    └── checker.py
```

## Project Root Detection

The script lives in C:\ but the project may be on any drive.
**Always use `$(pwd)` as the `--root` value** — Claude Code's Bash tool runs
commands from the session's working directory (i.e. the project root), so
`$(pwd)` automatically expands to the correct project path at runtime.

```
--root $(pwd)   Passes the current shell directory as project root.
                Works regardless of which drive the script lives on.
```

## Commands

### sync — Pull upper-tier specs from GitHub and write artifacts

```bash
# Basic (GITHUB_TOKEN from env)
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync

# With explicit token
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync --token <YOUR_TOKEN>

# With explicit config path (overrides --root search)
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync --config openspec/config.yaml
```

### check — Verify must-field compliance

```bash
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" check

# JSON output
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" check --json
```

### init — Scaffold openspec/ directory

```bash
python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" init
```

## Steps for sync

1. Ensure `GITHUB_TOKEN` is set:
   ```bash
   export GITHUB_TOKEN=<your-token>
   # or pass --token flag
   ```

2. Run — `$(pwd)` is resolved by the shell to the project root automatically:
   ```bash
   python "C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py" --root "$(pwd)" sync
   ```

4. Commit the generated files:
   ```
   openspec/merged/effective-spec.md
   openspec/merged/.spec-compliance.yaml
   openspec/.spec-lock.yaml
   ```

## What sync Does

`cli.py sync()`:
- Reads `openspec/config.yaml` for `spec_sources`
- Resolves each source version tag via GitHub API
- Downloads spec files and parses requirements/overrides
- Merges tiers and writes compliance artifacts
- Reports must-requirement counts and missing justifications

## Dependencies

Required Python packages (install if missing):
```bash
pip install click requests pyyaml
```

## Common Issues

| Issue | Fix |
|-------|-----|
| `GITHUB_TOKEN` missing | Set env var or use `--token` flag |
| `config.yaml` not found | Run `init` command first or check `--root` path |
| No `spec_sources` declared | Edit `openspec/config.yaml` and add sources |
| `ModuleNotFoundError: click` | Run `pip install click requests pyyaml` |
| Wrong directory used | Always pass `--root "$(pwd)"` — never hardcode a path |
| Script not found | Verify path: `C:\Users\cmk\.claude\skills\spec-skill\scripts\run_spec.py` |
