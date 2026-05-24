from __future__ import annotations

from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.table import Table

from vzctl import api, config
from vzctl.config import NodeConfig

app = typer.Typer(help="Restart all nodes or specific nodes in an environment.")
console = Console()
err_console = Console(stderr=True)


def _resolve_nodes(
    nodes: list[NodeConfig], targets: list[str], err_console: Console
) -> list[NodeConfig] | None:
    resolved = []
    for target in targets:
        match = next((n for n in nodes if n.nickname == target or str(n.id) == target), None)
        if match is None:
            available = ", ".join(f"{n.nickname}({n.id})" for n in nodes)
            err_console.print(f"[red]Error:[/red] Node '{target}' not found. Available: {available}")
            return None
        resolved.append(match)
    return resolved


@app.callback(invoke_without_command=True)
def restart(
    env: Annotated[str, typer.Option("--env", "-e", help="Environment key from config.yaml")],
    node: Annotated[
        Optional[List[str]],
        typer.Option("--node", "-n", help="Node nickname or ID to restart (repeatable). Omit for all nodes."),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to config.yaml")] = Path("config.yaml"),
) -> None:
    """Restart all nodes or specific nodes in an environment."""
    try:
        cfg = config.load(config_path)
        env_cfg = config.get_env(cfg, env)
    except (FileNotFoundError, KeyError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if node:
        target_nodes = _resolve_nodes(env_cfg.nodes, node, err_console)
        if target_nodes is None:
            raise typer.Exit(1)
    else:
        target_nodes = env_cfg.nodes

    node_names = ", ".join(n.nickname for n in target_nodes)
    if not yes:
        typer.confirm(
            f"Restart {len(target_nodes)} node(s) in '{env_cfg.name}' ({node_names})?",
            abort=True,
        )

    table = Table(title=f"Restart → {env_cfg.name}", show_lines=True)
    table.add_column("Node", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Status")

    failed = 0

    for n in target_nodes:
        try:
            api.restart_node(env_cfg, n)
            table.add_row(n.nickname, str(n.id), "[green]✓ Restarted[/green]")
        except api.APIError as exc:
            table.add_row(n.nickname, str(n.id), f"[red]✗ {exc}[/red]")
            failed += 1
        except Exception as exc:
            table.add_row(n.nickname, str(n.id), f"[red]✗ {exc}[/red]")
            failed += 1

    console.print(table)

    if failed:
        err_console.print(f"[red]{failed} of {len(target_nodes)} node(s) failed.[/red]")
        raise typer.Exit(1)
