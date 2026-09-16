import re
from importlib.metadata import version
from pathlib import Path

from blocket_toolkit import __version__


def test_version_matches_installed_metadata():
    assert __version__ == version("blocket-toolkit")


def test_pyproject_version_matches_installed_metadata():
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE).group(1)
    assert declared == version("blocket-toolkit"), (
        "pyproject version and the installed distribution disagree; "
        "reinstall the project after bumping the version"
    )
