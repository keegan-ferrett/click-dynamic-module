"""Fetch available plugins from GitHub Releases or a pip registry."""

import importlib.metadata
import re
from html.parser import HTMLParser

import httpx

# GitHub repository that hosts the releases.
GITHUB_REPO = "keegan-ferrett/click-dynamic-module"

# Naming convention: pip registry plugins must match this prefix.
PLUGIN_PREFIX = "cli-host-"

# Wheel filename pattern: {name}-{version}-{python}-{abi}-{platform}.whl
_WHEEL_RE = re.compile(r"^(?P<name>[A-Za-z0-9_]+)-(?P<version>[^-]+)-.+\.whl$")

# The host package itself — should not appear as an installable plugin.
_HOST_PACKAGE = "cli-host"

# Default Simple Repository API index.
DEFAULT_INDEX_URL = "https://pypi.org/simple/"


def _normalize(name: str) -> str:
    """Normalize a Python package name for comparison."""
    return re.sub(r"[-_.]+", "-", name).lower()


def installed_packages() -> dict[str, str]:
    """Return a mapping of normalized package name to installed version."""
    return {
        _normalize(d.metadata["Name"]): d.version
        for d in importlib.metadata.distributions()
        if d.metadata["Name"]
    }


def _build_plugin_dict(
    name: str,
    version: str,
    install_target: str,
    installed: dict[str, str],
) -> dict:
    """Build a standardised plugin info dict."""
    norm = _normalize(name)
    return {
        "name": name,
        "version": version,
        "install_target": install_target,
        "installed": norm in installed,
        "installed_version": installed.get(norm),
    }


# ---------------------------------------------------------------------------
# GitHub Release source
# ---------------------------------------------------------------------------


def fetch_github_plugins(tag: str = "latest") -> list[dict]:
    """Fetch wheel assets from a GitHub Release."""
    if tag == "latest":
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{tag}"

    resp = httpx.get(url, follow_redirects=True, timeout=15)
    resp.raise_for_status()
    release = resp.json()

    installed = installed_packages()
    plugins: list[dict] = []

    for asset in release.get("assets", []):
        match = _WHEEL_RE.match(asset["name"])
        if not match:
            continue

        pkg_name = match.group("name").replace("_", "-")
        if _normalize(pkg_name) == _normalize(_HOST_PACKAGE):
            continue

        plugins.append(
            _build_plugin_dict(
                name=pkg_name,
                version=match.group("version"),
                install_target=asset["browser_download_url"],
                installed=installed,
            )
        )

    return plugins


# ---------------------------------------------------------------------------
# Pip registry source (Simple Repository API)
# ---------------------------------------------------------------------------


class _SimpleIndexParser(HTMLParser):
    """Parse package names from a PEP 503 Simple Repository index page."""

    def __init__(self) -> None:
        super().__init__()
        self.packages: list[str] = []
        self._in_anchor = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._in_anchor = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a":
            self._in_anchor = False

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self.packages.append(data.strip())


def _fetch_package_version(index_url: str, package: str) -> str | None:
    """Fetch the latest version of a package from the JSON API.

    Falls back to scraping the simple index for the latest wheel filename.
    """
    # Try PyPI JSON API first (works for pypi.org and many mirrors).
    json_url = index_url.rstrip("/").removesuffix("/simple")
    json_url = f"{json_url}/pypi/{package}/json"
    try:
        resp = httpx.get(json_url, follow_redirects=True, timeout=10)
        if resp.status_code == 200:
            return resp.json()["info"]["version"]
    except Exception:
        pass

    # Fall back to parsing the simple index page for wheel filenames.
    detail_url = f"{index_url.rstrip('/')}/{_normalize(package)}/"
    try:
        resp = httpx.get(
            detail_url,
            follow_redirects=True,
            timeout=10,
            headers={"Accept": "text/html"},
        )
        resp.raise_for_status()
    except Exception:
        return None

    versions: list[str] = []
    for line in resp.text.splitlines():
        match = _WHEEL_RE.search(line)
        if match:
            versions.append(match.group("version"))
    return versions[-1] if versions else None


def fetch_pip_plugins(index_url: str = DEFAULT_INDEX_URL) -> list[dict]:
    """Discover plugins from a pip-compatible Simple Repository index.

    Looks for packages whose name starts with PLUGIN_PREFIX.
    """
    resp = httpx.get(
        index_url,
        follow_redirects=True,
        timeout=15,
        headers={"Accept": "text/html"},
    )
    resp.raise_for_status()

    parser = _SimpleIndexParser()
    parser.feed(resp.text)

    installed = installed_packages()
    plugins: list[dict] = []

    for pkg in parser.packages:
        if not _normalize(pkg).startswith(_normalize(PLUGIN_PREFIX)):
            continue
        if _normalize(pkg) == _normalize(_HOST_PACKAGE):
            continue

        version = _fetch_package_version(index_url, pkg) or "unknown"
        plugins.append(
            _build_plugin_dict(
                name=_normalize(pkg),
                version=version,
                install_target=pkg,
                installed=installed,
            )
        )

    return plugins
