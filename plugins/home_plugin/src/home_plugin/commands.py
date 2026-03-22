"""Home plugin — adds a 'home' command to the CLI host."""

import click


@click.command()
def home():
    """Display the home dashboard."""
    click.echo("Welcome home!")
