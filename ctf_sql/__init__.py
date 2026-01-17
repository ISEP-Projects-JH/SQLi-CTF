"""
Dynamic loader for selecting either the normal MySQLdb driver or the
SQLi-CTF driver depending on environment configuration.

This module determines its behavior based on the environment variable
`CTF_MODE`. When enabled, it loads the intentionally unsafe CTF driver
(`ctf_sql.fake_MySqldb`) and corresponding database constants. When disabled,
it falls back to the normal MySQLdb library and the production database config.

The purpose is to allow switching between:

- **Normal production mode**
- **SQL-Injection CTF mode**

without changing any application/business code. Only environment variables
control which backend is used.

Examples
--------
Enable CTF mode:
    ``export CTF_MODE=ctf``

    ``python app.py``

Disable CTF mode (use production DB):
    ``unset CTF_MODE``

    ``python app.py``

Developers can verify which mode is active:
    ``import ctf_sql``

    ``print(ctf_sql.SESSION_NAME)``

In CTF mode, this will show the CTF-specific session name, indicating that
all SQL operations are routed through the unsafe CTF database and the
FakeConnection–based driver.

⚠ WARNING
---------
The CTF driver is intentionally unsafe and replaces proper SQL escaping with
raw SQL concatenation. **Never use CTF mode in production environments.**
"""

import os
import builtins

if not getattr(builtins, "force_use_libmysqlclient", False):
    import pymysql
    pymysql.install_as_MySQLdb()

# Load constants from the configuration module
from . import constants

# ------------------------------------------------------------------
# Resolve CTF mode
#
# Priority:
# 1. builtins.CTF_MODE  (explicit, hard override)
# 2. environment CTF_MODE
# 3. default: production
# ------------------------------------------------------------------
if hasattr(builtins, "CTF_MODE"):
    MODE = str(getattr(builtins, "CTF_MODE", "")).lower()
else:
    MODE = os.getenv("CTF_MODE", "").lower()

if MODE in ("1", "ctf"):
    # ------------------------------------------------------------------
    # CTF Mode
    #
    # This imports the SQLi-CTF version of MySQLdb, which exposes a
    # FakeConnection and FakeCursor that allow SQL injection purposely.
    #
    # The DB_* constants are also swapped to the CTF versions, ensuring
    # all application code automatically queries the CTF database.
    # ------------------------------------------------------------------
    from . import fake_MySqldb as MySql

    DB_HOST: str = constants.CTF_DB_HOST
    DB_USER: str = constants.CTF_DB_USER
    DB_PASS: str = constants.CTF_DB_PASS
    DB_NAME: str = constants.CTF_DB_NAME
    SESSION_NAME: str = constants.CTF_SESSION_NAME

else:
    # ------------------------------------------------------------------
    # Production Mode
    #
    # Use normal MySQLdb with normal DB_* constants.
    # No code changes needed; business logic stays identical.
    # ------------------------------------------------------------------
    import MySQLdb as MySql # type: ignore

    DB_HOST: str = constants.DB_HOST
    DB_USER: str = constants.DB_USER
    DB_PASS: str = constants.DB_PASS
    DB_NAME: str = constants.DB_NAME
    SESSION_NAME: str = constants.SESSION_NAME


__all__ = [
    "MySql",
    "DB_HOST",
    "DB_USER",
    "DB_PASS",
    "DB_NAME",
    "SESSION_NAME",
]
