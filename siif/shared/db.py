"""Conexión Postgres y UPSERT para los ETL SIIF."""
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
import io


def repo_root():
    return Path(__file__).resolve().parents[2]


def connect():
    load_dotenv(repo_root() / ".env")
    host = os.getenv("HOST_DBB2")
    dbname = os.getenv("NAME_DB_DATOS_TABLERO")
    print(f"Connecting to DB {dbname} on {host}...")
    return psycopg2.connect(
        host=host,
        port=os.getenv("PORT_DBB2", "5432"),
        user=os.getenv("USER_DBB2"),
        password=os.getenv("PASSWORD_DBB2"),
        dbname=dbname,
    )


def ensure_unique_index(cur, table, columns, index_name):
    cur.execute(
        "SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND indexname = %s",
        (index_name,),
    )
    if cur.fetchone():
        return
    cols_sql = ", ".join(columns)
    print(f"Creando índice único {index_name} en {table}...")
    cur.execute(f"CREATE UNIQUE INDEX {index_name} ON {table} ({cols_sql})")


def ensure_table(cur, table, columns_sql):
    cur.execute(
        """
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    if cur.fetchone():
        return
    print(f"Creando tabla {table}...")
    cur.execute(f"CREATE TABLE {table} ({columns_sql})")


def upsert_dataframe(conn, table, df, columns, key_cols, index_name):
    """COPY a temp + INSERT ON CONFLICT DO UPDATE."""
    if df is None or df.empty:
        print("No hay filas para upsert.")
        return 0

    df = df[columns].drop_duplicates(subset=key_cols, keep="last")
    update_cols = [c for c in columns if c not in key_cols]
    tmp = f"tmp_{table}"

    cur = conn.cursor()
    ensure_unique_index(cur, table, key_cols, index_name)
    cur.execute(f"DROP TABLE IF EXISTS {tmp}")
    cur.execute(f"CREATE TEMP TABLE {tmp} (LIKE {table} INCLUDING DEFAULTS)")

    buf = io.StringIO()
    df.to_csv(buf, sep="\t", header=False, index=False)
    buf.seek(0)
    cur.copy_from(buf, tmp, sep="\t", columns=columns)

    cols_sql = ", ".join(columns)
    keys_sql = ", ".join(key_cols)
    set_sql = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_cols)
    insert_sql = (
        f"INSERT INTO {table} ({cols_sql}) SELECT {cols_sql} FROM {tmp} "
        f"ON CONFLICT ({keys_sql}) DO UPDATE SET {set_sql}"
    )
    cur.execute(insert_sql)
    n = cur.rowcount
    conn.commit()
    cur.close()
    print(f"UPSERT {table}: {len(df)} filas procesadas ({n} afectadas).")
    return len(df)
