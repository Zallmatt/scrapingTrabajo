import os
import sys

import pandas as pd

SIIF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if SIIF_DIR not in sys.path:
    sys.path.insert(0, SIIF_DIR)

from shared.db import connect, ensure_table, upsert_dataframe

TABLE = "copa_gastos_fte"
COLS = [
    "mes",
    "anio",
    "jurisdiccion",
    "codigo_fuente",
    "programa",
    "sub_prof",
    "py",
    "a_obra",
    "partid",
    "sub_partid",
    "tipo_de_g",
    "val",
]
KEYS = [c for c in COLS if c != "val"]
CREATE_SQL = """
    mes integer,
    anio integer,
    jurisdiccion integer,
    codigo_fuente integer,
    programa integer,
    sub_prof integer,
    py integer,
    a_obra integer,
    partid integer,
    sub_partid integer,
    tipo_de_g character varying,
    val numeric
"""


def load_to_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_file = os.path.join(base_dir, "files/processed/consolidado_gastos.csv")
    if not os.path.exists(processed_file):
        print(f"File not found: {processed_file}")
        return

    df = pd.read_csv(processed_file)
    conn = connect()
    try:
        cur = conn.cursor()
        ensure_table(cur, TABLE, CREATE_SQL)
        conn.commit()
        cur.close()
        upsert_dataframe(conn, TABLE, df, COLS, KEYS, "ux_copa_gastos_fte_nk")
    except Exception as exc:
        conn.rollback()
        print(f"Error during load: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    load_to_db()
