"""Hello plugin — adds a 'hello' command to the CLI host."""

import click


@click.command()
@click.option("--name", default="world", help="Who to greet.")
def hello(name: str):
    """Say hello from an independently installed plugin."""
    click.echo(f"Hello, {name}! (from hello-plugin)")
