import hashlib


def compute_file_hash(contents: bytes) -> str:
    """Compute SHA-256 hash of file contents for deduplication."""
    return hashlib.sha256(contents).hexdigest()
