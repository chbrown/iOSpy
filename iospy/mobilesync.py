from pathlib import Path
from typing import Iterator, Optional, Tuple, Union
import logging
import os
import shutil
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


def iter_domains(manifest: Union[bytes, str, os.PathLike]) -> Iterator[str]:
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
    manifest: Union[bytes, str, os.PathLike], domain: str = None
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


def rebuild(
    manifest: Union[bytes, str, os.PathLike],
    domain: str = None,
    target: Union[bytes, str, os.PathLike] = ".",
):
    """
    Rebuild the deep structure (creating directories as needed) specified in the
    manifest by copying the sha1-named files in the backup directory into filepaths
    like $target/$domain/path/to/file.txt
    """
    src_base = Path(manifest).parent
    dst_base = Path(target)
    for fileID, domain, relativePath in iter_files(manifest, domain):
        src = src_base / fileID[:2] / fileID
        # if original exists, copy it over to destination, otherwise do nothing
        if src.exists():
            dst = dst_base / domain / relativePath
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            logger.info("Copied %s -> %s", fileID, dst)
        else:
            logger.debug("Skipping missing file %s -> %s", fileID, relativePath)
