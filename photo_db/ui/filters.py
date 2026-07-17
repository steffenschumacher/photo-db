from datetime import datetime


def trim_path(path: str) -> str:
    if not path:
        return ""
    if not isinstance(path, str):
        raise ValueError(f"path {path} ({type(path)}) cannot be trimmed?")
    cut = 74
    if len(path) < cut:
        return path
    cut1 = int(cut / 2 - 2)
    cut2 = cut1 * -1
    try:
        return path[:cut1] + ".." + path[cut2:]
    except TypeError as te:
        print(te)
        return path


def mpixel(pixels: int) -> str:
    mpix = float(pixels) / 1024.0 / 1024.0
    if mpix < 3.0:
        return f"{mpix:.1f} MP"
    return f"{mpix:.0f} MP"


def taken_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")
