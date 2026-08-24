import logging
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

TABLA = "srt"

class LoadSRT:
    """Carga los datos del SRT a MySQL (v1) o PostgreSQL (v2) reemplazando los períodos entrantes."""

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.version = str(version)
        self.port = int(port) if port else (3306 if self.version == "1" else 5432)
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            driver = "mysql+pymysql" if self.version == "1" else "postgresql+psycopg2"
            conn_str = f"{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self._engine = create_engine(conn_str)
        return self._engine

    def load(self, df: pd.DataFrame):
        if df is None or df.empty:
            logger.warning("[LOAD] El DataFrame está vacío. No se realizaron cambios.")
            return

        engine = self._get_engine()
        schema_prefix = "public." if self.version == "2" else ""
        full_table = f"{schema_prefix}{TABLA}"

        # Obtener lista de fechas únicas a recargar
        fechas_str = [d.strftime('%Y-%m-%d') for d in pd.to_datetime(df['fecha'].unique())]
        fechas_sql = ", ".join([f"'{f}'" for f in fechas_str])

        df_to_load = df.copy()
        df_to_load['fecha'] = pd.to_datetime(df_to_load['fecha']).dt.date
        df_to_load['updated_at'] = pd.Timestamp.now()

        logger.info(f"[LOAD] Borrando y recargando datos para las fechas: {fechas_str} en {full_table}...")

        with engine.begin() as conn:
            # 1. Borrar solo los meses que se van a recargar
            delete_query = f"DELETE FROM {full_table} WHERE fecha IN ({fechas_sql})"
            conn.execute(text(delete_query))

            # 2. Insertar los nuevos registros corregidos
            df_to_load.to_sql(
                name=TABLA,
                con=conn,
                schema="public" if self.version == "2" else None,
                if_exists='append',
                index=False,
                chunksize=2000
            )

        logger.info(f"[LOAD] Se recargaron exitosamente {len(df_to_load)} registros.")

    def close(self):
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Conexión a BD cerrada.")