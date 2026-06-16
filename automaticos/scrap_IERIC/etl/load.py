"""
LOAD - Módulo de carga de datos IERIC
Responsabilidad: Cargar las 3 tablas del IERIC a MySQL/PostgreSQL (Incremental)
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

TABLAS = {
    'actividad': 'ieric_actividad',
    'puestos':   'ieric_puestos_trabajo',
    'salario':   'ieric_salario',
}


class LoadIERIC:
    """Carga los 3 DataFrames del IERIC a bases de datos (borrado por fecha y append)."""

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version)
        self._engine = None

    def load(self, df_act, df_puestos, df_sal):
        """Carga las 3 tablas con lógica de refresco incremental."""
        self._cargar(df_act, 'ACTIVIDAD', TABLAS['actividad'])
        self._cargar(df_puestos, 'PUESTOS', TABLAS['puestos'])
        self._cargar(df_sal, 'SALARIOS', TABLAS['salario'])
        logger.info("[OK] Carga de datos del IERIC completada.")

    def _cargar(self, df: pd.DataFrame, key_log: str, tabla_nombre: str):
        if df is None or df.empty:
            logger.warning(f"[LOAD] [{key_log}] DataFrame vacío, omitiendo carga para tabla '{tabla_nombre}'.")
            return

        schema = "public" if self.version == "2" else None
        full_table = f"{schema}.{tabla_nombre}" if schema else tabla_nombre
        engine = self._get_engine()
        
        logger.info(f"--- Iniciando carga para: {key_log} (Tabla: {tabla_nombre}) ---")

        # Asegurar formato fecha
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        fecha_max_extract = df['fecha'].max()
        fechas_nuevas = df['fecha'].unique().tolist()

        # Obtener info de la BDD para logging
        try:
            with engine.connect() as conn:
                fecha_max_db = conn.execute(text(f"SELECT MAX(fecha) FROM {full_table}")).scalar()
        except Exception:
            fecha_max_db = None

        fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
        fecha_ext_str = fecha_max_extract.strftime('%Y-%m-%d') if hasattr(fecha_max_extract, 'strftime') else 'Ninguna (DF vacío)'
        
        logger.info(f"[LOAD] [{key_log}] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")
        logger.info(f"[LOAD] [{key_log}] Refrescando/insertando datos para {len(fechas_nuevas)} meses. Se subirán {len(df)} registros.")
        
        try:
            with engine.begin() as conn:
                if fechas_nuevas:
                    conn.execute(text(f"DELETE FROM {full_table} WHERE fecha IN :fechas"), {"fechas": tuple(fechas_nuevas)})
                
                # Usamos append para preservar la estructura de la tabla y ser más eficientes
                df.to_sql(
                    name=tabla_nombre, 
                    con=conn, 
                    schema=schema, 
                    if_exists='append', 
                    index=False,
                    method='multi'
                )
            logger.info(f"[OK] [{key_log}] Carga completada en tabla '{tabla_nombre}'.")
        except Exception as e:
            logger.error(f"[LOAD ERROR] [{key_log}] Error en la tabla {tabla_nombre}: {e}")
            raise

    def _get_engine(self):
        if self._engine is None:
            if self.version == "1":
                # MySQL
                puerto = self.port if self.port else 3306
                conn_str = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else:
                # PostgreSQL
                puerto = self.port if self.port else 5432
                conn_str = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            
            self._engine = create_engine(conn_str)
        return self._engine

    def close(self):
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Conexiones de base de datos cerradas.")
