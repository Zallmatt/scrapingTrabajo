"""
LOAD - Módulo de carga de datos Semáforo
Responsabilidad: Cargar los DataFrames transformados a MySQL / PostgreSQL mediante Truncate & Load.
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class LoadSemaforo:
    """Carga los datos del Semáforo de forma híbrida (MySQL/PostgreSQL) truncando siempre la tabla."""

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version)
        self.engine = None
        self.tabla_interanual = "semaforo_interanual"
        self.tabla_intermensual = "semaforo_intermensual"

    def _conectar(self):
        if self.engine is None:
            if self.version == "1":  # MySQL
                puerto = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else:  # PostgreSQL
                puerto = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            self.engine = create_engine(url)
            logger.info(f"[OK] Motor conectado a '{self.database}' (v{self.version})")

    def load(self, df_interanual, df_intermensual):
        self._conectar()
        schema = "public" if self.version == "2" else None
        
        self._cargar_tabla(df_interanual, self.tabla_interanual, schema)
        self._cargar_tabla(df_intermensual, self.tabla_intermensual, schema)

    def _cargar_tabla(self, df, tabla, schema):
        if df is None or df.empty:
            logger.warning(f"[LOAD] El DataFrame para '{tabla}' está vacío. No se realizaron cambios.")
            return False

        full_table = f"{schema}.{tabla}" if schema else tabla
        
        # Copia para no mutar el DF original y agregar timestamp de actualización
        df_to_load = df.copy()
        df_to_load["updated_at"] = pd.Timestamp.now()

        logger.info(f"[LOAD] Truncando y recargando {len(df_to_load)} registros en '{full_table}'...")

        try:
            with self.engine.begin() as conn:
                # 1. Truncar la tabla según el motor
                if self.version == "2":
                    conn.execute(text(f"TRUNCATE TABLE {full_table} CASCADE;"))
                else:
                    conn.execute(text(f"TRUNCATE TABLE {full_table};"))
                
                # 2. Insertar todos los registros
                df_to_load.to_sql(
                    name=tabla,
                    con=conn,
                    schema=schema,
                    if_exists='append',
                    index=False,
                    chunksize=1000  # Evita saturar la memoria/conexión en DataFrames grandes
                )

            logger.info(f"[LOAD] Carga completada exitosamente en '{full_table}'.")
            return True

        except Exception as e:
            logger.error(f"[LOAD] Error al recargar la tabla '{full_table}': {e}")
            raise e

    def close(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None