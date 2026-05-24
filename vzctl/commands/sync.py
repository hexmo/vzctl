from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from vzctl import api, config

app = typer.Typer(help="Sync environment variables from config to all nodes.")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def sync(
    env: Annotated[str, typer.Option("--env", "-e", help="Environment key from config.yaml")],
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to config.yaml")] = Path("config.yaml"),
) -> None:
    """Push all variables defined under the environment in config.yaml to every node."""
    try:
        cfg = config.load(config_path)
        env_cfg = config.get_env(cfg, env)
    except (FileNotFoundError, KeyError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    table = Table(title=f"Sync → {env_cfg.name}", show_lines=True)
    table.add_column("Node", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Status")

    var_count = len(env_cfg.variables)
    failed = 0

    for node in env_cfg.nodes:
        try:
            api.sync_vars(env_cfg, node, env_cfg.variables)
            table.add_row(node.nickname, str(node.id), f"[green]✓ {var_count} var(s) synced[/green]")
        except api.APIError as exc:
            table.add_row(node.nickname, str(node.id), f"[red]✗ {exc}[/red]")
            failed += 1
        except Exception as exc:
            table.add_row(node.nickname, str(node.id), f"[red]✗ {exc}[/red]")
            failed += 1

    console.print(table)

    if failed:
        err_console.print(f"[red]{failed} of {len(env_cfg.nodes)} node(s) failed.[/red]")
        raise typer.Exit(1)
