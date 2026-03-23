"""Inline prompt for browsing and installing plugins."""

import subprocess
import sys

import click
from InquirerPy import inquirer

from cli_host.registry import fetch_github_plugins, fetch_pip_plugins


def browse_and_install(
    source: str = "github",
    tag: str = "latest",
    index_url: str | None = None,
) -> None:
    """Fetch available plugins, prompt for selection, and install chosen ones."""
    click.echo("Fetching available plugins…")
    try:
        if source == "pip":
            plugins = fetch_pip_plugins(index_url=index_url or "https://pypi.org/simple/")
        else:
            plugins = fetch_github_plugins(tag=tag)
    except Exception as exc:
        raise click.ClickException(f"Failed to fetch plugins: {exc}") from exc

    if not plugins:
        click.echo("No plugins found.")
        return

    choices = []
    for plugin in plugins:
        if plugin["installed"]:
            status = f"installed ({plugin['installed_version']})"
        else:
            status = "not installed"
        label = f"{plugin['name']} ({plugin['version']}) — {status}"
        choices.append({"name": label, "value": plugin, "enabled": False})

    selected = inquirer.checkbox(
        message="Select plugins to install:",
        choices=choices,
        cycle=True,
    ).execute()

    if not selected:
        click.echo("Nothing selected.")
        return

    install_targets = [p["install_target"] for p in selected]
    names = [p["name"] for p in selected]
    click.echo(f"Installing {', '.join(names)}…")

    cmd = [sys.executable, "-m", "pip", "install", *install_targets]
    if source == "pip" and index_url:
        cmd.extend(["--index-url", index_url])

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise click.ClickException(f"Installation failed (exit {exc.returncode})") from exc

    click.echo("Done! Restart cli-host to use new plugins.")
