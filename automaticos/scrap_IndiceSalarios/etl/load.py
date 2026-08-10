"""
LOAD - Módulo de carga de datos Índice de Salarios
Responsabilidad: Cargar solo filas nuevas a MySQL (append incremental)
"""
import logging
import pandas as pd
import psycopg2
import pymysql
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class LoadIndiceSalarios:
    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version)
        self.engine = None
        self.tabla = "indice_salario"

    def _conectar(self):
        """Crea el motor de conexión según versión (MySQL o PostgreSQL)."""
        if self.engine is None:
            if self.version == "1":
                puerto = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else:
                puerto = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            
            self.engine = create_engine(url, echo=False)
            logger.info(f"[OK] Motor conectado a '{self.database}' (v{self.version})")

    def load(self, df: pd.DataFrame) -> bool:
        self._conectar()
        schema = self._get_schema()
        full_table = f"{schema}.{self.tabla}" if schema else self.tabla
        
        # 1. Asegurar formato de fecha
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date

        if df.empty:
            logger.info("[LOAD] No hay datos en el DataFrame para procesar.")
            return False

        fecha_max_extract = df['fecha'].max()
        fechas_nuevas = df['fecha'].unique().tolist()

        # Obtener fecha máxima de la BDD para logging
        try:
            with self.engine.connect() as conn:
                res_date = conn.execute(text(f"SELECT MAX(fecha) FROM {full_table}"))
                fecha_max_db = res_date.scalar()
        except Exception:
            fecha_max_db = None

        fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
        fecha_ext_str = fecha_max_extract.strftime('%Y-%m-%d') if hasattr(fecha_max_extract, 'strftime') else 'Ninguna (DF vacío)'
        
        logger.info(f"[LOAD] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")
        logger.info(f"[LOAD] Refrescando/insertando datos para {len(fechas_nuevas)} meses. Se subirán {len(df)} registros.")
        
        # 2. Lógica incremental: Borrar fechas existentes para evitar duplicados
        with self.engine.begin() as conn:
            if fechas_nuevas:
                conn.execute(text(f"DELETE FROM {full_table} WHERE fecha IN :fechas"), {"fechas": tuple(fechas_nuevas)})
            
            # 3. Insertar nuevos datos (o re-insertar actualizados)
            df.to_sql(
                name=self.tabla, con=conn, schema=schema, 
                if_exists='append', index=False, method='multi'
            )
            try:
                alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
            
        logger.info(f"[LOAD] Carga a la base completada. Se subieron {len(df)} registros a la tabla '{self.tabla}'.")
        return True

    def _get_schema(self):
        return "public" if self.version == "2" else None

    def close(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None