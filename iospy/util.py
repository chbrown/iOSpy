from typing import Any, Iterator, Union
import hashlib
import logging
import os
import plistlib
import sqlite3

import magic

logger = logging.getLogger(__name__)

DEFAULT_FILE_MAGIC = magic.FileMagic("application/octet-stream", "binary", "data")


def sha1(data: Union[bytes, str]) -> str:
    """
    Generate hexdigest representation of SHA-1 hash of `data`.

    This can be used to compute the "fileID" for a given `domain` and `relativePath`:
        fileID = sha1(f"{domain}-{relativePath}")
    """
    if isinstance(data, str):
        data = data.encode()
    hashobj = hashlib.sha1()
    hashobj.update(data)
    return hashobj.hexdigest()


def _normalize_plist(value: Any) -> Any:
    """
    Convert any UID instances in `value` data structure to plain dicts (recursively).
    """
    if isinstance(value, plistlib.UID):
        return {"CF$UID": value.data}
    if isinstance(value, dict):
        return {k: _normalize_plist(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_plist(v) for v in value]
    return value


def convert_plist(
    source: Union[bytes, str, os.PathLike],
    target: Union[bytes, str, os.PathLike] = None,
    fmt: plistlib.PlistFormat = plistlib.PlistFormat.FMT_XML,
):
    """
    Read plist from `source` file and write to `target` file in specified format.

    If `target` is omitted, defaults to `source` (i.e., convert in-place).
    """
    if target is None:
        target = source
    with open(source, "rb") as fp:
        root = plistlib.load(fp)
    # plutil can convert UIDs to XML no problem, but Python chokes :(
    root = _normalize_plist(root)
    with open(target, "wb") as fp:
        plistlib.dump(root, fp, fmt=fmt, sort_keys=False)


def query(
    database: Union[bytes, str, os.PathLike, sqlite3.Connection],
    sql: str,
    parameters: Union[tuple, dict] = (),
) -> Iterator[dict]:
    """
    Execute `sql` along with `parameters` on a new cursor in the given SQLite database,
    iterating over the resulting rows as dicts.

    Creates new connection to `database` if needed, and closes any created connections
    when all rows have been exhausted.
    """
    if isinstance(database, sqlite3.Connection):
        cursor = database.cursor()
        cursor.execute(sql, parameters)
        columns = tuple(column for column, *_ in cursor.description)
        for row in cursor:
            yield dict(zip(columns, row))
        cursor.close()
    else:
        with sqlite3.connect(database) as conn:
            yield from query(conn, sql, parameters=parameters)


def read_magic(path: Union[bytes, str, os.PathLike]) -> magic.FileMagic:
    """
    Detect file type using 'file-magic' library.

    Work around 'file-magic' bug by returning default FileMagic instance.
    """
    try:
        return magic.detect_from_filename(path)
    except UnicodeDecodeError as exc:
        logger.warning("Failed to perform magic: %s; using fallback", exc)
        return DEFAULT_FILE_MAGIC
