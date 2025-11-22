"""
Configuration module for both normal and SQLi-CTF database environments.

This module loads connection parameters from environment variables and provides
two separate configurations:

1. **Production / normal environment**
2. **SQL-Injection CTF environment**, intentionally unsafe and intended only for
   controlled challenge setups.

A default empty password is used when the environment variable is not provided.

⚠ WARNING
---------
This module is designed to support SQL injection for CTF challenges.
Do **NOT** use the CTF configuration in production environments.
"""

import os


# ---------------------------------------------------------------------------
# Production / normal database configuration
# ---------------------------------------------------------------------------

#: Host for real/production database.
DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")

#: Username for real/production database.
DB_USER: str = os.getenv("DB_USER", "prod_user")

#: Password for real/production database (default is empty).
DB_PASS: str = os.getenv("DB_PASS", "")

#: Database name for real/production database.
DB_NAME: str = os.getenv("DB_NAME", "prod_db")


# ---------------------------------------------------------------------------
# SQL-Injection CTF database configuration
# ---------------------------------------------------------------------------

#: Host for CTF database environment.
CTF_DB_HOST: str = os.getenv("CTF_DB_HOST", "127.0.0.1")

#: Username for the CTF database.
CTF_DB_USER: str = os.getenv("CTF_DB_USER", "ctf_user")

#: Password for the CTF database (default is empty).
CTF_DB_PASS: str = os.getenv("CTF_DB_PASS", "")

#: Database name for the CTF environment.
CTF_DB_NAME: str = os.getenv("CTF_DB_NAME", "ctf_db")


# ---------------------------------------------------------------------------
# Session identifiers (for developers only)
# ---------------------------------------------------------------------------

#: Session name for normal SQL environment.
SESSION_NAME: str = os.getenv("SQL_SESSION_NAME", "default_session")

#: Session name for SQLi-CTF SQL environment.
CTF_SESSION_NAME: str = os.getenv("CTF_SQL_SESSION_NAME", "ctf_session")
