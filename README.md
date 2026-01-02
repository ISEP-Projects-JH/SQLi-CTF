# SQLi-CTF README

This project provides a small framework for designing simple SQL injection Capture-the-Flag challenges. It reuses
business logic that behaves similarly to a real MySQL environment, while isolating data into a dedicated CTF database.

## Purpose

The goal is to let you create SQLi challenges that feel realistic while remaining safe and reproducible. The framework
replicates common database access patterns, including intentionally insufficient input sanitization that leads to SQL
injection.

The vulnerability model demonstrated by this framework corresponds to **CVE-2019-12989**, where a flaw existed at the
dependency level rather than in application logic itself.

## Background: Why MySQLdb Was Replaced

Traditionally, Python applications use **MySQLdb** (the `mysqlclient` package) as a wrapper around the native *
*libmysqlclient** C library.

However, in practice:

* `libmysqlclient` **does not guarantee ABI compatibility across versions**
* System-installed MySQL (via `brew`, `apt`, etc.) often provides a `libmysqlclient` version that **does not match** the
  one expected by the Python `mysqlclient` wheel
* This frequently leads to runtime errors caused by missing or mismatched dynamic library symbols

For a CTF framework—where portability, reproducibility, and ease of setup are critical—this instability is undesirable.

## Design Decision: Use PyMySQL by Default

To eliminate native dependency issues, this project **defaults to using PyMySQL**, a pure-Python MySQL implementation.

PyMySQL implements the MySQL protocol entirely in Python and does **not depend on `libmysqlclient`**, making it:

* Cross-platform
* Stable across environments
* Free from system-level MySQL version mismatches

To preserve compatibility with existing code written against `MySQLdb`, PyMySQL is installed as a drop-in replacement.

### How This Works Internally

Unless explicitly overridden, the package performs the following at import time:

```python
import pymysql

pymysql.install_as_MySQLdb()
import MySQLdb  # type: ignore
```

In **CTF mode**, the framework does **not** expose a full or arbitrary `MySQLdb` interface.

Instead, `ctf_sql.MySql` is a **controlled compatibility layer** backed by `fake_MySqldb`, with a **strictly defined
public surface**.

#### FakeMySQLdb Public Interface

`fake_MySqldb` explicitly defines:

```python
__all__ = ['connect', 'FakeConnection', 'FakeCursor', 'MySQLError']
```

Behavior guarantees:

* `MySQLError` is **re-exported from the real backend** (`pymysql` or `MySQLdb`)
* `connect`, `FakeConnection`, and `FakeCursor` are **fully overridden implementations**
* All SQL execution paths in CTF mode are routed through `FakeConnection` / `FakeCursor`
* No additional MySQLdb APIs are implicitly exposed or relied upon

This guarantees that:

* Application code interacts only with the **minimal, intentional API surface**
* SQL injection behavior is **deterministic and fully controlled**
* The CTF backend does not accidentally depend on undocumented MySQLdb behavior

#### Dynamic Loader Contract

The `ctf_sql.MySql` symbol is **always present**, but what it resolves to depends on `CTF_MODE`.

The loader logic behaves as follows:

* **CTF mode**

    * `ctf_sql.MySql` → `ctf_sql.fake_MySqldb`
    * Uses `FakeConnection` / `FakeCursor`
    * Exposes exactly:

      ```python
      ['connect', 'FakeConnection', 'FakeCursor', 'MySQLError']
      ```

* **Production mode**

    * `ctf_sql.MySql` → real `MySQLdb` module
    * Uses normal DB constants
    * Business logic remains unchanged

The loader implementation (simplified) is:

```python
if MODE in ("1", "ctf"):
    from . import fake_MySqldb as MySql
    # DB_* swapped to CTF_DB_*
else:
    import MySQLdb as MySql
    # DB_* normal
```

#### Key Design Guarantee

> **Application code must only rely on `ctf_sql.MySql`, not on MySQLdb directly.**

The framework guarantees that `ctf_sql.MySql` always exposes the required symbols for CTF challenges, regardless of
backend, while preventing accidental dependency on unsupported MySQLdb APIs.

This constraint is intentional and is what makes the SQLi behavior reproducible, auditable, and safe for CTF usage.

## Forcing the Use of the Real MySQLdb (Optional)

Some users may require specific `libmysqlclient` features or APIs that PyMySQL does not fully implement.

To support this, the framework allows **explicit opt-in** to the real MySQLdb driver.

### How to Force libmysqlclient

Before importing `ctf_sql`, set the following flag:

```python
import builtins

builtins.force_use_libmysqlclient = True
```

When this flag is set:

* PyMySQL will **not** be installed as `MySQLdb`
* The real `mysqlclient` / `libmysqlclient` backend will be used instead

This option exists primarily for advanced users.
For most CTF challenges, PyMySQL provides more than enough compatibility.

## File Overview

This package automatically selects between a real MySQL backend and the intentionally unsafe SQLi-CTF backend based on
the environment variable `CTF_MODE`.

### Module Behavior Summary

* `ctf_sql.__init__` dynamically loads either:

    * **Production mode:** MySQLdb interface (via PyMySQL by default, or real MySQLdb if forced)
    * **CTF mode:** `ctf_sql.fake_MySqldb` (intentionally unsafe, injectable)

* `constants.py` defines two full sets of DB configuration values:

    * Normal DB: `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`
    * CTF DB: `CTF_DB_HOST`, `CTF_DB_USER`, `CTF_DB_PASS`, `CTF_DB_NAME`

All values can be overridden via environment variables:

```bash
export DB_USER=myuser
export CTF_DB_NAME=my_ctf_db
```

## Designing Simple SQLi Challenges

Challenge authors write business logic exactly as they would in a normal MySQL-backed application—**with one rule**:

> Always import and use `ctf_sql.MySql`, never a driver directly.

Example:

```python
import ctf_sql

conn = ctf_sql.MySql.connect(
    host=ctf_sql.DB_HOST,
    user=ctf_sql.DB_USER,
    passwd=ctf_sql.DB_PASS,
    db=ctf_sql.DB_NAME,
)

cur = conn.cursor()
cur.execute("SELECT * FROM users WHERE id = 1")
print(cur.fetchone())
```

Driver selection, unsafe behavior, and database isolation are handled entirely by the framework.

## Running in CTF Mode vs Normal Mode

Backend selection is controlled **only** by an environment variable.
Your application code never changes.

### Enable CTF Mode

```bash
export CTF_MODE=ctf
```

This activates:

* `ctf_sql.fake_MySqldb`
* `CTF_DB_*` credentials
* `CTF_SESSION_NAME`

### Disable CTF Mode

```bash
unset CTF_MODE
```

This activates:

* MySQLdb interface (PyMySQL by default)
* Normal `DB_*` credentials
* `SESSION_NAME`

### Verifying the Active Backend

```python
import ctf_sql

print(ctf_sql.SESSION_NAME)

conn = ctf_sql.MySql.connect(
    host=ctf_sql.DB_HOST,
    user=ctf_sql.DB_USER,
    passwd=ctf_sql.DB_PASS,
    db=ctf_sql.DB_NAME,
)

cur = conn.cursor()
cur.execute("SELECT 1")
print(cur.fetchone())
```

## Resetting the CTF Database

There is **no built-in initializer or reset mechanism**.

This is intentional.

* `fake_MySqldb` does not provide helpers, reset APIs, or schema loaders
* All database initialization is the responsibility of the challenge author
* This mirrors real-world MySQL usage and keeps challenges explicit

## Dependencies

Only **PyMySQL** is required by default:

```bash
pip install pymysql
```

If you choose to force the real MySQLdb backend, you must also install:

```bash
pip install mysqlclient
```

## Important Note for Developers

This framework exists to demonstrate a critical security lesson:

> **Your application can be vulnerable even if your code is correct.**

The vulnerability modeled here (CVE-2019-12989) originated from a **third-party dependency**, not application logic.

Therefore:

* Keep dependencies updated
* Monitor security advisories
* Treat database drivers and native libraries as part of your attack surface

This project shows how dependency-level flaws can silently compromise otherwise well-written systems—and why continuous
security maintenance is essential.
