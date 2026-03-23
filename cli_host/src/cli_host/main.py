"""CLI host application that dynamically discovers and loads plugin commands."""

import importlib.metadata

import click


def load_plugins(group: click.Group) -> None:
    """Discover installed plugins via the 'cli_host.plugins' entry point group
    and attach each one as a subcommand."""
    for ep in importlib.metadata.entry_points(group="cli_host.plugins"):
        try:
            command = ep.load()
            group.add_command(command, ep.name)
        except Exception as exc:
            click.echo(f"Warning: failed to load plugin {ep.name!r}: {exc}", err=True)


@click.group()
def cli():
    """A pluggable CLI — install plugins to add new commands."""


@cli.command("plugins")
@click.option(
    "--source",
    type=click.Choice(["github", "pip"]),
    default="github",
    help="Where to look for plugins.",
)
@click.option("--tag", default="latest", help="GitHub Release tag (github source only).")
@click.option("--index-url", default=None, help="Pip registry URL (pip source only).")
def browse_plugins(source: str, tag: str, index_url: str | None):
    """Browse and install available plugins."""
    from cli_host.tui import browse_and_install

    browse_and_install(source=source, tag=tag, index_url=index_url)


load_plugins(cli)

if __name__ == "__main__":
    cli()
