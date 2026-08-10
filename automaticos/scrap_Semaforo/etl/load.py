"""
LOAD - Módulo de carga de datos Semáforo
Responsabilidad: Cargar los DataFrames transformados a MySQL
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class LoadSemaforo:
    """Carga los datos del Semáforo de forma híbrida (MySQL/PostgreSQL)."""

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
            if self.version == "1": # MySQL
                puerto = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else: # PostgreSQL
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
        full_table = f"{schema}.{tabla}" if schema else tabla
        
        # 1. Validación de fechas e indicadores nuevos
        try:
            df_db = pd.read_sql(f"SELECT * FROM {full_table}", con=self.engine)
            fecha_max_db = pd.to_datetime(df_db['fecha']).max() if not df_db.empty else None
            datos_db_count = df_db.count().sum() # Cuenta total de celdas con datos no nulos
        except Exception:
            fecha_max_db = None
            datos_db_count = 0
            
        fecha_max_ext = pd.to_datetime(df['fecha']).max()
        datos_ext_count = df.count().sum()

        fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
        fecha_ext_str = fecha_max_ext.strftime('%Y-%m-%d') if hasattr(fecha_max_ext, 'strftime') else str(fecha_max_ext)

        logger.info(f"[LOAD] Comparación de fechas en '{tabla}' -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")

        if fecha_max_db and (fecha_max_db.date() == fecha_max_ext.date()) and (datos_db_count == datos_ext_count):
            logger.info(f"[LOAD] No hay datos nuevos. La base llega hasta {fecha_db_str} y se extrajo hasta {fecha_ext_str}. No se sube a la base ni al Sheets.")
            return False

        logger.info(f"[LOAD] ¡Datos nuevos detectados en '{tabla}'! Se reemplazarán los registros actuales.")

        with self.engine.begin() as conn:
            
            # Reemplazo seguro
            if self.version == "2":
                conn.execute(text(f"TRUNCATE TABLE {full_table} CASCADE"))
            else:
                conn.execute(text(f"TRUNCATE TABLE {full_table}"))
            
            df.to_sql(name=tabla, con=conn, schema=schema, if_exists='append', index=False)
            try:
                alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
            logger.info(f"[LOAD] Carga a la base completada para '{tabla}'.")
            
        return True

    def close(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None