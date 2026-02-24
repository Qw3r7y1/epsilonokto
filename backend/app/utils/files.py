from pathlib import Path


def safe_filename(filename: str) -> str:
    """Remove path separators and null bytes from filename."""
    return Path(filename).name.replace("\x00", "")


def get_extension(filename: str) -> str:
    """Get lowercase file extension without dot."""
    return Path(filename).suffix.lstrip(".").lower()
