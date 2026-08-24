import os
import sys

import pandas as pd

SIIF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if SIIF_DIR not in sys.path:
    sys.path.insert(0, SIIF_DIR)

from shared.db import connect, upsert_dataframe

TABLE = "copa_gastos"
COLS = ["periodo", "jurisdiccion", "tipo_financ", "partida", "estado", "monto"]
KEYS = ["periodo", "jurisdiccion", "tipo_financ", "partida", "estado"]


def load_to_db():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processed_file = os.path.join(base_dir, "files/processed/consolidado_gastos.csv")
    if not os.path.exists(processed_file):
        print(f"File not found: {processed_file}")
        return

    df = pd.read_csv(processed_file)
    conn = connect()
    try:
        upsert_dataframe(conn, TABLE, df, COLS, KEYS, "ux_copa_gastos_nk")
    except Exception as exc:
        conn.rollback()
        print(f"Error during load: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    load_to_db()
