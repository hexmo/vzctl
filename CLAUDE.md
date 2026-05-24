# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`vzctl` is a Python CLI tool for managing environment variables and nodes on [Virtuozzo Application Platform](https://www.virtuozzo.com/application-management-docs/) (formerly Jelastic). It is provider-agnostic — any PaaS running on Virtuozzo is supported. The tool is open-source and intended to be used by anyone managing Virtuozzo-based environments.

## Setup & Running

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # install dependencies
cp example-config.yaml config.yaml   # then fill in real values
uv run vzctl --help
```

## Commands

```bash
uv run vzctl sync   --env <key>                    # push vars from config to all nodes
uv run vzctl list   --env <key> [--output out.csv] # list vars; optional CSV export
uv run vzctl delete --env <key> --key VAR_NAME     # delete a var from all nodes
```

All commands accept `--config <path>` to point at a non-default config file.

## Architecture

```text
vzctl/
├── main.py          # Typer app; registers sync/list/delete sub-apps
├── config.py        # Loads config.yaml; resolves per-env api_url/api_token overrides
├── api.py           # httpx-based Virtuozzo REST API client (sync_vars, list_vars, delete_var)
└── commands/
    ├── sync.py      # vzctl sync
    ├── list_vars.py # vzctl list
    └── delete.py    # vzctl delete
```

**Config resolution:** `api_url` and `api_token` can be set globally at the top of `config.yaml` or overridden per-environment. `config.py:load()` merges these, with per-environment values winning. `config.yaml` is gitignored; `example-config.yaml` is the committed template.

**API pattern:** Each command iterates over all nodes in the environment and calls the appropriate `api.py` function per node. `APIError` is raised when the HTTP response is 200 but `result != 0` (Virtuozzo's own error indicator). Rich tables display per-node results including nickname and numeric ID.

**Node nicknames:** Defined in `config.yaml` under each node entry (`nickname: app-1`). Used in all output for readability. Falls back to the numeric ID string if no nickname is set.

## Adding a New Command

1. Create `vzctl/commands/<name>.py` with a `app = typer.Typer(...)` and a `@app.callback(invoke_without_command=True)` function.
2. Register it in `vzctl/main.py` with `app.add_typer(<name>.app, name="<name>")`.
3. Use `config.load()` + `config.get_env()` to resolve config, then iterate `env_cfg.nodes` and call functions from `api.py`.

## Virtuozzo API Reference

Base URL comes from `api_url` in config. Endpoints follow the pattern:

```text
POST <api_url>/1.0/environment/control/rest/<action>
```

Common parameters: `session` (token), `envName`, `nodeId`, `vars` (JSON). A `result` of `0` in the response body means success.
