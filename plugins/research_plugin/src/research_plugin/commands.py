"""Research plugin — adds a 'research' command to the CLI host."""

import click


@click.command()
@click.argument("topic")
def research(topic: str):
    """Look up a topic and display research results."""
    click.echo(f"Researching: {topic}")
