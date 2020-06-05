from pathlib import Path
from typing import Iterator, Optional, Tuple, Union
import hashlib
import logging
import sqlite3

import appdirs

logger = logging.getLogger(__name__)


def iter_manifests() -> Iterator[Path]:
    """
    Find all manifests in known location(s).
    """
    mobilesync_path = Path(appdirs.user_data_dir("MobileSync"))
    # on macOS, mobilesync_path would be ~/Library/Application Support/MobileSync
    backup_path = mobilesync_path / "Backup"
    return backup_path.glob("*/Manifest.db")


def latest_manifest() -> Optional[Path]:
    """
    Find the latest (by modified time) manifest in known location(s), if any.
    """
    return max(iter_manifests(), default=None, key=lambda p: p.stat().st_mtime)


def iter_domains(manifest: Union[Path, str]) -> Iterator[str]:
    """
    Select unique domains from the 'Files' table in the manifest database.
    """
    with sqlite3.connect(manifest) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT domain
            FROM Files
            GROUP BY domain
            ORDER BY domain ASC
            """
        )
        for row in cur:
            yield row[0]


def iter_files(
    manifest: Union[Path, str], domain: str = None
) -> Iterator[Tuple[str, str, str]]:
    """
    Select fileID, domain, and relativePath from the 'Files' table in the manifest,
    limiting to those where domain == `domain`, if specified.
    """
    with sqlite3.connect(manifest) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT fileID, domain, relativePath
            FROM Files
            WHERE :domain IS NULL OR domain = :domain
            ORDER BY domain, relativePath ASC
            """,
            {"domain": domain},
        )
        yield from cur


def sha1(data: Union[bytes, str]) -> str:
    """
    Generate hexdigest representation of SHA-1 hash of `data`.

    This can be used to compute the "fileID" for a given `domain` and `relativePath`:
        fileID = sha1(f"{domain}-{relativePath}")
    """
    if isinstance(data, str):
        data = data.encode("ascii")
    hashobj = hashlib.sha1()
    hashobj.update(data)
    return hashobj.hexdigest()
