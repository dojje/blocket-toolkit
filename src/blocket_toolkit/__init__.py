"""blocket-toolkit: search all of Blocket.se from the terminal."""

from importlib.metadata import PackageNotFoundError, version

from .client import BlocketClient, Page

try:
    __version__ = version("blocket-toolkit")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

__all__ = ["BlocketClient", "Page", "__version__"]
