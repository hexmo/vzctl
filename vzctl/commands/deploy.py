from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, List, Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from vzctl import api, config
from vzctl.config import EnvironmentConfig, NodeConfig

app = typer.Typer(help="Redeploy nodes with the latest (or specified) image tag.")
console = Console()
err_console = Console(stderr=True)


@dataclass
class NodeResult:
    node: NodeConfig
    tag: str
    success: bool
    message: str
    duration: float


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


def _deploy_node(env_cfg: EnvironmentConfig, node: NodeConfig, tag: str) -> NodeResult:
    console.log(f"[cyan]{node.nickname}[/cyan] ({node.id}) — pulling image [yellow]{tag}[/yellow]…")
    t0 = time.perf_counter()
    try:
        api.redeploy_node(env_cfg, node, tag)
        duration = time.perf_counter() - t0
        console.log(f"[cyan]{node.nickname}[/cyan] ({node.id}) — [green]done[/green] in {duration:.1f}s")
        return NodeResult(node=node, tag=tag, success=True, message="✓ Deployed", duration=duration)
    except Exception as exc:
        duration = time.perf_counter() - t0
        console.log(f"[cyan]{node.nickname}[/cyan] ({node.id}) — [red]failed[/red] after {duration:.1f}s: {exc}")
        return NodeResult(node=node, tag=tag, success=False, message=f"✗ {exc}", duration=duration)


def _build_table(results: list[NodeResult], env_name: str, tag: str) -> Table:
    table = Table(title=f"Deploy [{tag}] → {env_name}", show_lines=True)
    table.add_column("Node", style="cyan")
    table.add_column("ID", style="dim")
    table.add_column("Tag", style="yellow")
    table.add_column("Status")
    table.add_column("Time", style="dim", justify="right")
    for r in results:
        status = f"[green]{r.message}[/green]" if r.success else f"[red]{r.message}[/red]"
        table.add_row(r.node.nickname, str(r.node.id), r.tag, status, f"{r.duration:.1f}s")
    return table


@app.callback(invoke_without_command=True)
def deploy(
    env: Annotated[str, typer.Option("--env", "-e", help="Environment key from config.yaml")],
    node: Annotated[
        Optional[List[str]],
        typer.Option("--node", "-n", help="Node nickname or ID to redeploy (repeatable). Omit for all nodes."),
    ] = None,
    tag: Annotated[str, typer.Option("--tag", "-t", help="Image tag to deploy")] = "latest",
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
    config_path: Annotated[Path, typer.Option("--config", "-c", help="Path to config.yaml")] = Path("config.yaml"),
) -> None:
    """Redeploy nodes in parallel by pulling the latest (or specified) image tag."""
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
            f"Redeploy {len(target_nodes)} node(s) in '{env_cfg.name}' ({node_names}) with tag '{tag}'?",
            abort=True,
        )

    console.log(f"Starting parallel redeploy of {len(target_nodes)} node(s) with tag [yellow]{tag}[/yellow]")

    results: list[NodeResult] = []
    with ThreadPoolExecutor(max_workers=len(target_nodes)) as pool:
        futures = {pool.submit(_deploy_node, env_cfg, n, tag): n for n in target_nodes}
        for future in as_completed(futures):
            results.append(future.result())

    # Sort results to match original node order
    order = {n.id: i for i, n in enumerate(target_nodes)}
    results.sort(key=lambda r: order[r.node.id])

    console.print(_build_table(results, env_cfg.name, tag))

    failed = sum(1 for r in results if not r.success)
    if failed:
        err_console.print(f"[red]{failed} of {len(target_nodes)} node(s) failed.[/red]")
        raise typer.Exit(1)
