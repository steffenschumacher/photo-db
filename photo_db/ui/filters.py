"""Small, framework-agnostic display formatting helpers shared by the UI's
table/list views. Kept free of Qt imports so they're trivially unit-testable.
"""

from datetime import datetime


def trim_path(path: str) -> str:
    """Shorten a long path for display, keeping the start and end."""
    if not path:
        return ""
    if not isinstance(path, str):
        raise ValueError(f"path {path} ({type(path)}) cannot be trimmed?")
    cut = 74
    if len(path) < cut:
        return path
    cut1 = int(cut / 2 - 2)
    cut2 = cut1 * -1
    return path[:cut1] + ".." + path[cut2:]


def mpixel(pixels: int) -> str:
    """Format a raw pixel count as megapixels, e.g. ``12.3 MP``."""
    mpix = float(pixels) / 1024.0 / 1024.0
    if mpix < 3.0:
        return f"{mpix:.1f} MP"
    return f"{mpix:.0f} MP"


def taken_date(dt: datetime) -> str:
    """Format a capture datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def month_label(year: int, month: int) -> str:
    """Format a (year, month) pair for the thumbnail grid's period picker."""
    return datetime(year, month, 1).strftime("%Y-%m (%B)")
