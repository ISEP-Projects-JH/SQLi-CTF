"""
This module provides intentionally unsafe MySQL wrappers designed for
SQL-Injection Capture-the-Flag (SQLi-CTF) challenges.

The goal is to enable raw, unescaped SQL construction **without modifying
existing business code**, by exposing a drop-in replacement for
`MySQLdb.connect()`.

⚠ WARNING
---------
This module is deliberately vulnerable by design.
It performs **no escaping**, **no quoting**, and allows **arbitrary SQL injection**.

**DO NOT USE IN PRODUCTION.**
Use strictly for controlled CTF environments.
"""

import re
import MySQLdb
from typing import Any, Iterable, Optional, Sequence


class FakeCursor:
    """
    A cursor wrapper that disables escaping and performs raw string
    concatenation for SQL queries, enabling deliberate SQL injection for CTF use.
    """

    def __init__(self, real_cursor: MySQLdb.cursors.Cursor):
        self._cur: MySQLdb.cursors.Cursor = real_cursor

    def __getattr__(self, name: str) -> Any:
        """
        Forward attribute access to the underlying real cursor.
        """
        return getattr(self._cur, name)

    @staticmethod
    def _raw_value(v: Any) -> str:
        """
        Convert a Python value into raw SQL form without escaping.

        - None → "NULL"
        - Everything else → str(v) verbatim

        Parameters
        ----------
        v : Any
            Arbitrary value passed to SQL query.

        Returns
        -------
        str
            Raw SQL representation.
        """
        if v is None:
            return "NULL"
        return str(v)

    @staticmethod
    def _build_sql(query: str, params: Sequence[Any]) -> str:
        """
        Build an SQL string by naive `%s` substitution without escaping.

        Parameters
        ----------
        query : str
            SQL query string possibly containing `%s` placeholders.
        params : Sequence[Any]
            Values to be inserted.

        Returns
        -------
        str
            Final SQL string with raw insertions.

        Raises
        ------
        ValueError
            If the number of placeholders does not match the number of params.
        """
        placeholders = len(re.findall(r'(?<!%)%s', query))

        if placeholders != len(params):
            raise ValueError(
                f"placeholder count mismatch: {placeholders} != {len(params)}"
            )

        parts = query.split("%s")
        sql = ""
        for i in range(placeholders):
            sql += parts[i] + FakeCursor._raw_value(params[i])
        sql += parts[-1]
        return sql

    def execute(self, query: str, params: Optional[Sequence[Any]] = None) -> int:
        """
        Execute a raw SQL query. If parameters are provided, the query is
        constructed with `_build_sql()` to allow SQL injection.

        Parameters
        ----------
        query : str
            SQL statement.
        params : Sequence[Any] or None
            Inserted without escaping.

        Returns
        -------
        int
            Number of affected rows (as returned by the real cursor).
        """
        if params is None:
            return self._cur.execute(query)

        sql = FakeCursor._build_sql(query, params)
        return self._cur.execute(sql)

    def executemany(
            self, query: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> int:
        """
        Execute a query multiple times with raw SQL concatenation,
        preserving injection behavior.

        Parameters
        ----------
        query : str
            SQL template containing `%s` placeholders.
        seq_of_params : Iterable[Sequence[Any]]
            Parameter sequences; each entry is executed separately.

        Returns
        -------
        int
            Total affected row count across all executions.
        """
        count = 0
        for params in seq_of_params:
            sql = FakeCursor._build_sql(query, params)
            count += self._cur.execute(sql)
        return count


class FakeConnection:
    """
    A drop-in connection wrapper that returns `FakeCursor` instead of a real cursor,
    enabling unsafe SQL execution for CTF environments.
    """

    def __init__(self, *a, **kw):
        self._conn: MySQLdb.connections.Connection = MySQLdb.connect(*a, **kw)

    def cursor(self) -> FakeCursor:
        """
        Return a `FakeCursor` wrapping the underlying connection's cursor.

        Returns
        -------
        FakeCursor
            Injection-friendly cursor wrapper.
        """
        return FakeCursor(self._conn.cursor())

    def __getattr__(self, name: str) -> Any:
        """
        Forward attribute access to the underlying real connection.
        """
        return getattr(self._conn, name)


def connect(*args, **kwargs) -> FakeConnection:
    """
    Replacement for MySQLdb.connect() that returns a FakeConnection.

    Returns
    -------
    FakeConnection
        Connection object whose cursors allow SQL injection.
    """
    return FakeConnection(*args, **kwargs)
