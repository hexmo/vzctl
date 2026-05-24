import typer

from vzctl.commands import delete, deploy, list_vars, logs, restart, sync

app = typer.Typer(
    name="vzctl",
    help="Manage environment variables and nodes on Virtuozzo-based PaaS platforms.",
    no_args_is_help=True,
)

app.add_typer(sync.app, name="sync")
app.add_typer(list_vars.app, name="list")
app.add_typer(delete.app, name="delete")
app.add_typer(restart.app, name="restart")
app.add_typer(deploy.app, name="deploy")
app.add_typer(logs.app, name="logs")

if __name__ == "__main__":
    app()
