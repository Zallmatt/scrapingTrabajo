"""
LOAD - Módulo de carga de datos EMAE
Responsabilidad: Cargar las 2 tablas del EMAE a PostgreSQL (incremental)
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text
import pymysql
import psycopg2

logger = logging.getLogger(__name__)

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Recomendación: usa nombres en minúsculas en Postgres
TABLA_VALORES     = "emae"
TABLA_VARIACIONES = "emae_variaciones"

class LoadEMAE:
    """Carga los 2 DataFrames del EMAE a PostgreSQL."""

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = version
        self.engine = None

    def _conectar(self):
        if not self.engine:
            if self.version == "1":  # MySQL
                puerto = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else:  # PostgreSQL
                puerto = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            
            self.engine = create_engine(url, echo=False)
            logger.info(f"[OK] Motor conectado a {'MySQL' if self.version=='1' else 'PostgreSQL'} (v{self.version})")

    def _get_schema(self):
        return "public" if self.version == "2" else None

    def load(self, df_valores: pd.DataFrame, df_variaciones: pd.DataFrame) -> bool:
        self._conectar()
        b1 = self._cargar_valores(df_valores)
        b2 = self._cargar_variaciones(df_variaciones)
        return b1 or b2

    def _cargar_valores(self, df: pd.DataFrame) -> bool:
        """Carga solo fechas nuevas en la tabla emae."""
        tabla = "emae"
        schema = self._get_schema()
        full_table_name = f"{schema}.{tabla}" if schema else tabla

        logger.info("--- Iniciando carga para: VALORES (Tabla: %s) ---", tabla)

        if df is None or df.empty:
            logger.info("[LOAD] [VALORES] DataFrame vacío. Omitiendo carga.")
            return False

        df['fecha'] = pd.to_datetime(df['fecha'])
        fecha_max_extract = df['fecha'].max()

        # Leemos datos existentes para logging y para evitar duplicados
        try:
            with self.engine.connect() as conn:
                fecha_max_db = conn.execute(text(f"SELECT MAX(fecha) FROM {full_table_name}")).scalar()
            
            query_fechas = f"SELECT DISTINCT fecha FROM {full_table_name}"
            df_bdd = pd.read_sql(query_fechas, con=self.engine)
            fechas_existentes = set(pd.to_datetime(df_bdd['fecha']).dt.date)
        except Exception:
            fecha_max_db = None
            fechas_existentes = set()
        
        fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
        fecha_ext_str = fecha_max_extract.strftime('%Y-%m-%d') if hasattr(fecha_max_extract, 'strftime') else 'Ninguna (DF vacío)'

        logger.info(f"[LOAD] [VALORES] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")
        
        df['fecha_dt'] = df['fecha'].dt.date
        df_nuevos = df[~df['fecha_dt'].isin(fechas_existentes)].copy()
        df_nuevos = df_nuevos.drop(columns=['fecha_dt'])
        
        if not df_nuevos.empty:
            logger.info(f"[LOAD] [VALORES] ¡Datos nuevos detectados! Se cargarán {len(df_nuevos)} registros (para {len(df_nuevos['fecha'].unique())} meses).")
            df_nuevos.to_sql(name=tabla, con=self.engine, schema=schema, if_exists='append', index=False, method='multi')
            try:
                with self.engine.begin() as conn:
                    alter_query = f"ALTER TABLE {full_table_name} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table_name} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] [VALORES] No se pudo agregar la columna updated_at: {e}")
            logger.info("[OK] [VALORES] Carga a la base completada.")
            return True
            
        logger.info("[LOAD] [VALORES] No hay datos nuevos. La base está al día. No se sube a la base.")
        return False

    def _cargar_variaciones(self, df: pd.DataFrame) -> bool:
        tabla = "emae_variaciones"
        schema = self._get_schema()
        full_table_name = f"{schema}.{tabla}" if schema else tabla

        logger.info("--- Iniciando carga para: VARIACIONES (Tabla: %s) ---", tabla)
        
        if df is None or df.empty:
            logger.info("[LOAD] [VARIACIONES] DataFrame vacío. Omitiendo carga.")
            return False

        df['fecha'] = pd.to_datetime(df['fecha'])
        fecha_max_extract = df['fecha'].max()

        try:
            with self.engine.connect() as conn:
                fecha_max_db = conn.execute(text(f"SELECT MAX(fecha) FROM {full_table_name}")).scalar()

            query_fechas = f"SELECT DISTINCT fecha FROM {full_table_name}"
            df_bdd = pd.read_sql(query_fechas, con=self.engine)
            fechas_existentes = set(pd.to_datetime(df_bdd['fecha']).dt.date)
        except Exception:
            fecha_max_db = None
            fechas_existentes = set()

        fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
        fecha_ext_str = fecha_max_extract.strftime('%Y-%m-%d') if hasattr(fecha_max_extract, 'strftime') else 'Ninguna (DF vacío)'

        logger.info(f"[LOAD] [VARIACIONES] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")

        # Filtramos lo que REALMENTE no está en la base de datos
        df['fecha_dt'] = pd.to_datetime(df['fecha']).dt.date
        df_nuevos = df[~df['fecha_dt'].isin(fechas_existentes)].copy()
        df_nuevos = df_nuevos.drop(columns=['fecha_dt']) # Limpiamos la columna auxiliar

        if not df_nuevos.empty:
            logger.info(f"[LOAD] [VARIACIONES] ¡Datos nuevos detectados! Se cargarán {len(df_nuevos)} registros.")
            df_nuevos.to_sql(name=tabla, con=self.engine, schema=schema, if_exists='append', index=False, method='multi')
            try:
                with self.engine.begin() as conn:
                    alter_query = f"ALTER TABLE {full_table_name} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table_name} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] [VARIACIONES] No se pudo agregar la columna updated_at: {e}")
            logger.info("[OK] [VARIACIONES] Carga a la base completada.")
            return True
        
        logger.info("[LOAD] [VARIACIONES] No hay datos nuevos. La base está al día. No se sube a la base.")
        return False

    def close(self):
        if self.engine:
            self.engine.dispose()