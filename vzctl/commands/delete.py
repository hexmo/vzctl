from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from vzctl import api, config

app = typer.Typer(help="Delete an environment variable from all nodes.")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def delete(
    env: Annotated[str, typer.Option("--env", "-e", help="Environment key from config.yaml")],
    key: Annotated[str, typer.Option("--key", "-k", help="Variable name to delete")],
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to config.yaml")] = Path("config.yaml"),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Delete a single environment variable from every node in the environment."""
    try:
        cfg = config.load(config_path)
        env_cfg = config.get_env(cfg, env)
    except (FileNotFoundError, KeyError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if not yes:
        typer.confirm(
            f"Delete '{key}' from all {len(env_cfg.nodes)} node(s) in '{env_cfg.name}'?",
            abort=True,
        )

    table = Table(title=f"Delete '{key}' → {env_cfg.name}", show_lines=True)
    table.add_column("Node", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Status")

    failed = 0

    for node in env_cfg.nodes:
        try:
            api.delete_var(env_cfg, node, key)
            table.add_row(node.nickname, str(node.id), "[green]✓ Deleted[/green]")
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
