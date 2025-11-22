# SQLi-CTF README

This project provides a small framework for designing simple SQL injection Capture‑the‑Flag challenges. It reuses business logic that behaves similarly to a real `MySqldb` implementation, while isolating data into a dedicated CTF database.

## Purpose

The goal is to let you create SQLi challenges that feel realistic while remaining safe and reproducible. The simulation replicates common database access patterns, including insufficient input sanitization that leads to SQL injection. The vulnerability modeled corresponds to **CVE‑2019‑12989**.

## File Overview

This package automatically selects between a real `MySQLdb` driver and the intentionally unsafe SQLi-CTF driver based on the environment variable `CTF_MODE`.

### Module Behavior Summary

* `ctf_sql.__init__` dynamically loads either:

  * **Production mode:** real `MySQLdb`
  * **CTF mode:** `ctf_sql.fake_MySqldb` (unsafe, injectable)

* `constants.py` defines two full sets of DB configuration values:

  * Normal DB: `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`
  * CTF DB: `CTF_DB_HOST`, `CTF_DB_USER`, `CTF_DB_PASS`, `CTF_DB_NAME`

You may **override any of these by environment variable**, e.g.

```bash
export DB_USER=myuser
export CTF_DB_NAME=my_ctf_db
```

These override the defaults automatically used by the package.

## Designing Simple SQLi Challenges

You design all challenges exactly as you normally would when writing business logic that connects to MySQL — **but you always import and use `ctf_sql.MySql` instead of a direct MySQL driver.**

Because `ctf_sql.__init__` dynamically switches drivers, you do *not* manually choose a driver in your code. Your application code stays identical in both normal mode and CTF mode.

Example pattern for writing challenge logic:

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

All injection behavior (unsafe SQL concatenation) is automatically enabled only when the environment variable enables CTF mode.

## Resetting the CTF Database

There is **no built‑in database initializer**. `fake_MySqldb` does **not** provide an init function, reset helper, or mode switch API. All initialization logic is entirely up to the challenge author, exactly like a real MySQL environment.

## Running in CTF Mode vs Normal Mode in CTF Mode vs Normal Mode

`ctf_sql` selects the correct backend **entirely through an environment variable**. Your application code never changes.

### Enable CTF Mode

```bash
export CTF_MODE=ctf
```

This causes `ctf_sql.__init__` to load:

* `ctf_sql.fake_MySqldb` (unsafe driver)
* `CTF_DB_*` database credentials
* `CTF_SESSION_NAME`

### Disable CTF Mode

```bash
unset CTF_MODE
```

This causes `ctf_sql` to load:

* real `MySQLdb`
* normal `DB_*` credentials
* `SESSION_NAME`

### Using the database

Your code never changes between modes. The only difference comes from the environment variable `CTF_MODE`.

Example:

```python
import ctf_sql

print(ctf_sql.SESSION_NAME)  # Shows which backend is active

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

## Dependencies

This package depends on **MySQLdb**, meaning you must install the `mysqlclient` library:

```bash
pip install mysqlclient
```

No other third-party dependencies are required.

In **CTF mode**, the fake driver (`fake_MySqldb`) behaves like a vulnerable MySQL wrapper. It performs *no input validation* and inserts raw query strings directly, allowing SQL injection exactly as the challenge intends.

This means you can write your business logic **exactly the same way you normally would**, without adding any additional injection logic. The unsafe behavior is automatically enabled only when `CTF_MODE=ctf` is set.

---

## Important Note for Developers

This project also serves as a reminder for real-world development:

Even if your application code follows good practices, **your product is not automatically safe**.
Security still requires rigorous testing — including explicit SQL injection testing.

The vulnerability modeled here (CVE-2019-12989) was caused not by application code, but by a flaw in a **third-party dependency**. If a library you rely on introduces a critical security issue, your system becomes vulnerable as well.

Therefore:

* Always keep dependencies updated.
* Monitor security advisories for the libraries you use.
* Apply patches or upgrade promptly when a vulnerability is discovered.

This framework demonstrates how dangerous a dependency-level SQL injection flaw can be — and why continuous security maintenance is essential.
