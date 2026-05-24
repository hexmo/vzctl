from __future__ import annotations

import csv
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from vzctl import api, config

app = typer.Typer(help="List environment variables currently set on nodes.")
console = Console()
err_console = Console(stderr=True)


@app.callback(invoke_without_command=True)
def list_vars(
    env: Annotated[
        str, typer.Option("--env", "-e", help="Environment key from config.yaml")
    ],
    config_path: Annotated[
        Path, typer.Option("--config", "-c", help="Path to config.yaml")
    ] = Path("config.yaml"),
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Write results to a CSV file"),
    ] = None,
) -> None:
    """Fetch and display environment variables from all nodes. Optionally export to CSV."""
    try:
        cfg = config.load(config_path)
        env_cfg = config.get_env(cfg, env)
    except (FileNotFoundError, KeyError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    # Fetch vars per node: {node: {key: value}}
    node_vars: dict[str, dict[str, str]] = {}
    failed = 0

    for node in env_cfg.nodes:
        col = f"{node.nickname}({node.id})"
        try:
            node_vars[col] = api.list_vars(env_cfg, node)
        except (api.APIError, Exception) as exc:
            err_console.print(f"[red]✗ Node {node.nickname} [{node.id}]: {exc}[/red]")
            node_vars[col] = {}
            failed += 1

    # Collect all unique keys across every node, sorted
    all_keys = sorted({key for vars in node_vars.values() for key in vars})
    node_cols = list(node_vars.keys())

    # Rich table
    table = Table(title=f"Variables in {env_cfg.name}", show_lines=True)
    table.add_column("S.N.", style="dim", justify="right")
    table.add_column("KEY", style="bold")
    for col in node_cols:
        table.add_column(col, style="cyan")

    for sn, key in enumerate(all_keys, start=1):
        table.add_row(str(sn), key, *[node_vars[col].get(key, "[dim]—[/dim]") for col in node_cols])

    console.print(table)

    # CSV export
    if output:
        with output.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["S.N.", "KEY", *node_cols])
            for sn, key in enumerate(all_keys, start=1):
                writer.writerow([sn, key, *[node_vars[col].get(key, "") for col in node_cols]])
        console.print(f"[green]Exported {len(all_keys)} variable(s) to {output}[/green]")

    if failed:
        raise typer.Exit(1)
