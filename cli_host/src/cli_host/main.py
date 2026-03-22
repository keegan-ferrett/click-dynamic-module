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


load_plugins(cli)

if __name__ == "__main__":
    cli()
