import typer

from vzctl.commands import delete, list_vars, sync

app = typer.Typer(
    name="vzctl",
    help="Manage environment variables and nodes on Virtuozzo-based PaaS platforms.",
    no_args_is_help=True,
)

app.add_typer(sync.app, name="sync")
app.add_typer(list_vars.app, name="list")
app.add_typer(delete.app, name="delete")

if __name__ == "__main__":
    app()
