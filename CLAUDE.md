# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

`vzctl` is a Python CLI tool for managing environment variables and nodes on [Virtuozzo Application Platform](https://www.virtuozzo.com/application-management-docs/) (formerly Jelastic). It is provider-agnostic — any PaaS running on Virtuozzo is supported. The tool is open-source.

## Setup & Running

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                              # install dependencies
cp example-config.yaml config.yaml   # fill in real values
uv run vzctl --help
```

## Commands

```bash
uv run vzctl sync   --env <key>                    # push vars from config.yaml to all nodes
uv run vzctl list   --env <key> [--output out.csv] # list vars in pivoted table; optional CSV export
uv run vzctl delete --env <key> --key VAR_NAME     # delete a var from all nodes (confirms first)
```

All commands accept `--config <path>` to point at a non-default config file.

## Configuration

All config lives in a single `config.yaml` (gitignored). `example-config.yaml` is the committed template with no real values. There are no `.env` files.

```yaml
api_url: "https://app.your-paas-provider.cloud"   # global default
api_token: "your-session-token"                    # global default

environments:
  staging:
    name: my-app-staging
    # api_url / api_token can be overridden per-environment
    nodes:
      - id: 10001
        nickname: api
      - id: 10002
        nickname: celery
      - id: 10003
        nickname: beat
    variables:
      DEBUG: "True"
      DJANGO_ENV: "staging"
```

`config.py:load()` merges global and per-environment `api_url`/`api_token`, with per-environment values winning.

## Architecture

```text
vzctl/
├── main.py          # Typer app; registers sync/list/delete sub-apps
├── config.py        # Loads config.yaml; resolves per-env api_url/api_token overrides
├── api.py           # httpx-based Virtuozzo REST API client (sync_vars, list_vars, delete_var)
└── commands/
    ├── sync.py      # vzctl sync — iterates nodes, calls api.sync_vars, prints per-node status table
    ├── list_vars.py # vzctl list — fetches vars per node, pivots into S.N./KEY/node-column table
    └── delete.py    # vzctl delete — confirms, iterates nodes, calls api.delete_var
```

**API pattern:** Each command iterates `env_cfg.nodes` and calls the relevant `api.py` function per node. `APIError` is raised when HTTP is 200 but `result != 0` (Virtuozzo's success indicator). All output uses Rich tables.

**`list` output format:** Pivoted — one row per variable key, one column per node headed `nickname(node_id)`. Missing values shown as `—`. CSV export follows the same layout with headers `S.N., KEY, nickname(node_id), ...`.

**Node nicknames:** Set in `config.yaml` under each node (`nickname: api`). Used in all output. Falls back to the numeric ID string if omitted.

## Adding a New Command

1. Create `vzctl/commands/<name>.py` with `app = typer.Typer(...)` and a `@app.callback(invoke_without_command=True)` function.
2. Register it in `vzctl/main.py` with `app.add_typer(<name>.app, name="<name>")`.
3. Load config with `config.load()` + `config.get_env()`, iterate `env_cfg.nodes`, call functions from `api.py`.

## Virtuozzo API Reference

Base URL comes from `api_url` in config. All endpoints are POST:

```text
POST <api_url>/1.0/environment/control/rest/<action>
```

| Action                   | Used by        |
| ------------------------ | -------------- |
| `addcontainerenvvars`    | `vzctl sync`   |
| `getcontainerenvvars`    | `vzctl list`   |
| `removecontainerenvvars` | `vzctl delete` |

Common parameters: `session` (token), `envName`, `nodeId`, `vars` (JSON). A `result` of `0` in the response body means success.
