from __future__ import annotations

from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.rule import Rule

from vzctl import api, config
from vzctl.config import NodeConfig

app = typer.Typer(help="Fetch and display log files from nodes.")
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
def logs(
    env: Annotated[str, typer.Option("--env", "-e", help="Environment key from config.yaml")],
    node: Annotated[
        Optional[List[str]],
        typer.Option("--node", "-n", help="Node nickname or ID (repeatable). Omit for all nodes."),
    ] = None,
    path: Annotated[str, typer.Option("--path", "-p", help="Log file path on the container")] = "/var/log/run.log",
    count: Annotated[Optional[int], typer.Option("--count", help="Number of lines to fetch")] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Directory to save log files (<nickname>_<id>.log per node)"),
    ] = None,
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to config.yaml")] = Path("config.yaml"),
) -> None:
    """Fetch and display log files from all nodes or specific nodes."""
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

    if output:
        output.mkdir(parents=True, exist_ok=True)

    failed = 0

    for n in target_nodes:
        label = f"{n.nickname} ({n.id})"
        console.print(Rule(f"[cyan]{label}[/cyan]"))
        try:
            content = api.read_log(env_cfg, n, path, count)
            console.print(content if content else "[dim](empty)[/dim]")
            if output:
                log_file = output / f"{n.nickname}_{n.id}.log"
                log_file.write_text(content)
                console.print(f"[dim]Saved → {log_file}[/dim]")
        except api.APIError as exc:
            err_console.print(f"[red]✗ {exc}[/red]")
            failed += 1
        except Exception as exc:
            err_console.print(f"[red]✗ {exc}[/red]")
            failed += 1

    if failed:
        err_console.print(f"[red]{failed} of {len(target_nodes)} node(s) failed.[/red]")
        raise typer.Exit(1)
