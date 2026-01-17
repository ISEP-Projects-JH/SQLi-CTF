from typing import Any, Iterable, Optional, Sequence, Callable
import re
import builtins

if not getattr(builtins, "force_use_libmysqlclient", False):
    import pymysql
    pymysql.install_as_MySQLdb()

import MySQLdb  # type: ignore
from pymysql import MySQLError as MySQLError

__all__ = ['connect', 'FakeConnection', 'FakeCursor', 'MySQLError']


class FakeCursor:
    """
    A cursor wrapper that disables escaping and performs raw string
    concatenation for SQL queries, enabling deliberate SQL injection for CTF use.

    Optionally applies a user-provided sanitizer to string parameters
    before SQL construction.
    """

    def __init__(
        self,
        real_cursor: MySQLdb.cursors.Cursor,
        sanitizer: Optional[Callable[[str], str]] = None,
    ):
        self._cur: MySQLdb.cursors.Cursor = real_cursor
        self._sanitizer = sanitizer

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cur, name)

    def _apply_sanitizer(self, v: str) -> str:
        """
        Apply sanitizer to string values if provided.
        Translate ValueError into MySQLError.
        """
        if self._sanitizer is None or not isinstance(v, str):
            return v

        try:
            return self._sanitizer(v)
        except ValueError as e:
            raise MySQLError(str(e)) from e

    def _raw_value(self, v: Any) -> str:
        """
        Convert a Python value into raw SQL form without escaping.
        """

        is_str = False

        if v is None:
            return "NULL"

        if isinstance(v, str):
            is_str = True

        v = self._apply_sanitizer(str(v))

        if is_str:
            return f"'{v}'"  # intentionally unsafe

        return str(v)

    def _build_sql(self, query: str, params: Sequence[Any]) -> str:
        placeholders = len(re.findall(r'(?<!%)%s', query))

        if placeholders != len(params):
            raise ValueError(
                f"placeholder count mismatch: {placeholders} != {len(params)}"
            )

        parts = query.split("%s")
        sql = ""
        for i in range(placeholders):
            sql += parts[i] + self._raw_value(params[i])
        sql += parts[-1]
        return sql

    def execute(self, query: str, params: Optional[Sequence[Any]] = None) -> int:
        if params is None:
            return self._cur.execute(query)

        sql = self._build_sql(query, params)
        return self._cur.execute(sql)

    def executemany(
        self, query: str, seq_of_params: Iterable[Sequence[Any]]
    ) -> int:
        count = 0
        for params in seq_of_params:
            sql = self._build_sql(query, params)
            count += self._cur.execute(sql)
        return count


class FakeConnection:
    """
    Drop-in connection wrapper that returns FakeCursor.
    """

    def __init__(self, *a, sanitizer=None, **kw):
        self._sanitizer = sanitizer
        self._conn: MySQLdb.connections.Connection = MySQLdb.connect(*a, **kw)

    def cursor(self) -> FakeCursor:
        return FakeCursor(self._conn.cursor(), sanitizer=self._sanitizer)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def connect(*args, sanitizer=None, **kwargs) -> FakeConnection:
    """
    Replacement for MySQLdb.connect() that returns a FakeConnection.

    sanitizer: Optional[Callable[[str], str]]
        User-defined preprocessing hook for string parameters.
    """
    return FakeConnection(*args, sanitizer=sanitizer, **kwargs)
