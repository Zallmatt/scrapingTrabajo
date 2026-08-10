import logging
import pandas as pd
from sqlalchemy import create_engine, text
import pymysql
import psycopg2

logger = logging.getLogger(__name__)

TABLA = "srt"

class LoadSRT:
    """Carga los datos del SRT a MySQL (v1) o PostgreSQL (v2)."""

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.version = str(version)
        # Asignación automática de puerto si no se provee
        self.port = int(port) if port else (3306 if self.version == "1" else 5432)
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            # Determinamos el driver según la versión
            driver = "mysql+pymysql" if self.version == "1" else "postgresql+psycopg2"
            conn_str = f"{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self._engine = create_engine(conn_str)
        return self._engine

    def load(self, df: pd.DataFrame):
        engine = self._get_engine()
        
        # 1. Obtener los registros que ya existen en la BD (solo las columnas del UNIQUE)
        # Esto es mucho más rápido que intentar insertar y fallar
        query = f"SELECT fecha, id_provincia, id_ciiu FROM {TABLA}"
        existentes = pd.read_sql(query, engine)
        
        # 2. Aseguramos que los tipos coincidan para comparar
        existentes['fecha'] = pd.to_datetime(existentes['fecha']).dt.date
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        
        # 3. Filtrar el DataFrame: quedarnos solo con lo que NO está en la BD
        # Creamos una columna clave temporal para comparar fácilmente
        df['key'] = df['fecha'].astype(str) + df['id_provincia'].astype(str) + df['id_ciiu'].astype(str)
        existentes['key'] = existentes['fecha'].astype(str) + existentes['id_provincia'].astype(str) + existentes['id_ciiu'].astype(str)
        
        df_nuevo = df[~df['key'].isin(existentes['key'])].drop(columns=['key'])
        
        # 4. Insertar solo lo nuevo
        if not df_nuevo.empty:
            logger.info(f"[LOAD] Cargando {len(df_nuevo)} registros nuevos.")
            df_nuevo.to_sql(name=TABLA, con=engine, if_exists='append', index=False, method='multi')
            try:
                schema_prefix = "public." if self.version == "2" else ""
                full_table = f"{schema_prefix}{TABLA}"
                with engine.begin() as conn:
                    alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
        else:
            logger.info("[LOAD] No hay registros nuevos para cargar.")

    def close(self):
        """Cierra el engine de SQLAlchemy."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Conexión a BD cerrada.")