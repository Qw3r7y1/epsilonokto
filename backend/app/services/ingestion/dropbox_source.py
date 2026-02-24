"""
Dropbox source — lists and downloads invoice files from a Dropbox folder.

Cursor-based tracking ensures we only process *new* files on each poll,
not everything in the folder every time.

Usage:
    source = DropboxSource()
    async for filename, file_bytes in source.new_files():
        # feed into the ingestion pipeline
"""

import json
from pathlib import Path

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import FileMetadata

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("services.ingestion.dropbox_source")
settings = get_settings()

# Cursor is stored here so it survives restarts (kept out of git via .gitignore)
_CURSOR_FILE = Path("./data/dropbox_cursor.json")

_SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}


class DropboxSource:
    """Connects to Dropbox and yields new files from the configured folder."""

    def __init__(self) -> None:
        if not settings.dropbox_access_token:
            raise RuntimeError(
                "DROPBOX_ACCESS_TOKEN is not set. "
                "Add it to your .env file to enable Dropbox sync."
            )
        self._dbx = dropbox.Dropbox(settings.dropbox_access_token)
        self._folder = settings.dropbox_folder.rstrip("/")

    def _verify_auth(self) -> None:
        """Raise a clear error if the token is invalid."""
        try:
            self._dbx.users_get_current_account()
        except AuthError as exc:
            raise RuntimeError(
                f"Dropbox authentication failed. Check your DROPBOX_ACCESS_TOKEN. "
                f"Details: {exc}"
            ) from exc

    # ── Cursor persistence ─────────────────────────────────────────────────

    def _load_cursor(self) -> str | None:
        if _CURSOR_FILE.exists():
            try:
                data = json.loads(_CURSOR_FILE.read_text())
                return data.get("cursor")
            except Exception:
                return None
        return None

    def _save_cursor(self, cursor: str) -> None:
        _CURSOR_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CURSOR_FILE.write_text(json.dumps({"cursor": cursor}))

    # ── Core listing logic ─────────────────────────────────────────────────

    def _list_new_entries(self) -> list[FileMetadata]:
        """Return FileMetadata for files added since the last cursor."""
        cursor = self._load_cursor()
        new_entries: list[FileMetadata] = []

        if cursor is None:
            # First run — get a fresh cursor without downloading every existing file.
            # We list the folder once just to establish the cursor position.
            log.info(
                "No Dropbox cursor found — initialising from current folder state. "
                "Only files added AFTER this run will be processed."
            )
            result = self._dbx.files_list_folder(self._folder, recursive=False)
            while result.has_more:
                result = self._dbx.files_list_folder_continue(result.cursor)
            self._save_cursor(result.cursor)
            return []

        # Subsequent runs — get only changes since the last cursor.
        result = self._dbx.files_list_folder_continue(cursor)
        while True:
            for entry in result.entries:
                if isinstance(entry, FileMetadata):
                    ext = Path(entry.name).suffix.lower()
                    if ext in _SUPPORTED_EXTENSIONS:
                        new_entries.append(entry)
                        log.info("New file detected in Dropbox: %s", entry.path_display)
            if not result.has_more:
                break
            result = self._dbx.files_list_folder_continue(result.cursor)

        self._save_cursor(result.cursor)
        return new_entries

    def _download(self, entry: FileMetadata) -> bytes:
        """Download a file and return its raw bytes."""
        _, response = self._dbx.files_download(entry.path_display)
        return response.content

    # ── Public API ─────────────────────────────────────────────────────────

    def new_files(self) -> list[tuple[str, bytes]]:
        """
        Return a list of (filename, file_bytes) for every new file
        found in the Dropbox folder since the last poll.

        This is synchronous because the Dropbox SDK is blocking;
        call it inside asyncio.run_in_executor() from async code.
        """
        try:
            entries = self._list_new_entries()
        except ApiError as exc:
            log.error("Dropbox API error while listing folder: %s", exc)
            return []

        results: list[tuple[str, bytes]] = []
        for entry in entries:
            try:
                file_bytes = self._download(entry)
                results.append((entry.name, file_bytes))
                log.info("Downloaded %s (%d bytes)", entry.name, len(file_bytes))
            except ApiError as exc:
                log.error("Failed to download %s: %s", entry.path_display, exc)

        return results
