import duckdb
from pathlib import Path


def get_duckdb_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("INSTALL sqlite_scanner; LOAD sqlite_scanner")
    con.execute(f"ATTACH '{db_path}' AS db (TYPE sqlite, READ_ONLY)")
    return con
