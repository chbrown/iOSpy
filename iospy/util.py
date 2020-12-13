from typing import Iterator, Union
import os
import sqlite3


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
