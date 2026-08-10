"""
LOAD - Módulo de carga de datos SIPA
Responsabilidad: Cargar a PostgreSQL con TRUNCATE + INSERT si hay datos nuevos, y calcular analytics
"""
import logging
import pandas as pd
import numpy as np
import psycopg2
import pymysql
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class LoadSIPA:
    """Carga los datos de SIPA a PostgreSQL (truncate + replace incremental)."""

    def __init__(self, host, user, password, db_datalake, db_dwh, port, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.db_datalake = db_datalake
        self.db_dwh = db_dwh
        self.port = port
        self.version = str(version)
        self.tabla = 'sipa'
        self.engines = {}

    def _get_engine(self, db_name):
        """Crea o retorna el motor de conexión dinámico."""
        if db_name not in self.engines:
            if self.version == "1":
                port = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{port}/{db_name}"
            else:
                port = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{port}/{db_name}"
            
            self.engines[db_name] = create_engine(url, echo=False)
            logger.info(f"[OK] Motor conectado a base '{db_name}' (v{self.version})")
        return self.engines[db_name]
    
    def _get_schema(self):
        return "public" if self.version == "2" else None

    def load(self, df: pd.DataFrame) -> bool:
        engine = self._get_engine(self.db_datalake)
        schema = self._get_schema()
        full_table = f"{schema}.{self.tabla}" if schema else self.tabla
        
        # 1. Validación de fechas
        with engine.connect() as conn:
            try:
                res = conn.execute(text(f"SELECT MAX(fecha) FROM {full_table}"))
                fecha_bdd = res.scalar()
            except Exception:
                fecha_bdd = None
        
        fecha_df = pd.to_datetime(df['fecha']).max()
        fecha_bdd_dt = pd.to_datetime(fecha_bdd) if fecha_bdd else None
        
        fecha_db_str = fecha_bdd_dt.strftime('%Y-%m-%d') if fecha_bdd_dt else 'Ninguna (Tabla vacía)'
        fecha_ext_str = fecha_df.strftime('%Y-%m-%d') if hasattr(fecha_df, 'strftime') else str(fecha_df)

        logger.info(f"[LOAD] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")

        if fecha_bdd_dt and fecha_bdd_dt.date() >= fecha_df.date():
            logger.info(f"[LOAD] No hay datos nuevos. La base llega hasta {fecha_db_str} y se extrajo hasta {fecha_ext_str}. No se sube a la base ni al Sheets.")
            return False

        logger.info("[LOAD] ¡Datos nuevos detectados! Se reemplazarán los registros actuales.")

        # 2. Carga limpia
        with engine.begin() as conn:
            # Truncate seguro según motor
            if self.version == "2":
                conn.execute(text(f"TRUNCATE TABLE {full_table} CASCADE"))
            else:
                conn.execute(text(f"TRUNCATE TABLE {full_table}"))
            
            df.to_sql(name=self.tabla, con=conn, schema=schema, if_exists='append', index=False, method='multi')
            try:
                alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
        
        logger.info("[LOAD] Carga a la base completada. %d filas cargadas. Iniciando Analytics...", len(df))
        self._run_analytics()
        return True
    
    def _run_analytics(self):
        """Ejecuta los cálculos y guarda en el DWH."""
        engine_datalake = self._get_engine(self.db_datalake)
        engine_dwh = self._get_engine(self.db_dwh)
        schema_dwh = self._get_schema()

        # Analytics Nacionales
        df_ana = pd.DataFrame()
        self._get_percentages(df_ana, engine_datalake)
        self._get_variances_nation(df_ana)
        df_ana['fecha'] = pd.to_datetime(df_ana['fecha']).dt.date
        df_ana.to_sql(name="empleo_nacional_porcentajes_variaciones", con=engine_dwh, schema=schema_dwh, if_exists='replace', index=False)
        try:
            with engine_dwh.begin() as conn_alter:
                full_table_ana = f"{schema_dwh}.empleo_nacional_porcentajes_variaciones" if schema_dwh else "empleo_nacional_porcentajes_variaciones"
                alter_query = f"ALTER TABLE {full_table_ana} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table_ana} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn_alter.execute(text(alter_query))
        except Exception as e:
            logger.warning(f"[LOAD] No se pudo agregar la columna updated_at a empleo_nacional_porcentajes_variaciones: {e}")
        
        # Analytics NEA
        df_nea = pd.DataFrame()
        self._get_variances_nea(df_nea, engine_datalake)
        df_nea['fecha'] = pd.to_datetime(df_nea['fecha']).dt.date
        df_nea.to_sql(name="empleo_nea_variaciones", con=engine_dwh, schema=schema_dwh, if_exists='replace', index=False)
        try:
            with engine_dwh.begin() as conn_alter:
                full_table_nea = f"{schema_dwh}.empleo_nea_variaciones" if schema_dwh else "empleo_nea_variaciones"
                alter_query = f"ALTER TABLE {full_table_nea} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table_nea} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn_alter.execute(text(alter_query))
        except Exception as e:
            logger.warning(f"[LOAD] No se pudo agregar la columna updated_at a empleo_nea_variaciones: {e}")
        
        logger.info("[LOAD] Analytics actualizados en DWH.")

    def _table_analytics_sipa(self):
        # Usamos los engines configurados en la clase
        engine_datalake = self._get_engine(self.db_datalake)
        engine_dwh = self._get_engine(self.db_dwh)
        schema = self._get_schema()
        
        df_ana = pd.DataFrame()
        self._get_percentages(df_ana, engine_datalake)
        self._get_variances_nation(df_ana)
        
        df_ana['fecha'] = pd.to_datetime(df_ana['fecha']).dt.date
        
        # Guardamos en DWH con el esquema correspondiente
        df_ana.to_sql(name="empleo_nacional_porcentajes_variaciones", con=engine_dwh, schema=schema, if_exists='replace', index=False)
        try:
            with engine_dwh.begin() as conn_alter:
                full_table_ana = f"{schema}.empleo_nacional_porcentajes_variaciones" if schema else "empleo_nacional_porcentajes_variaciones"
                alter_query = f"ALTER TABLE {full_table_ana} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table_ana} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn_alter.execute(text(alter_query))
        except Exception as e:
            logger.warning(f"[LOAD] No se pudo agregar la columna updated_at a empleo_nacional_porcentajes_variaciones: {e}")
        logger.info("[LOAD] Analytics nacionales actualizados en DWH.")

    def _get_percentages(self, df, engine_datalake):
        # Usamos self.tabla y engine_datalake
        query = f"SELECT * FROM {self.tabla} WHERE id_provincia = 1"
        df_bdd = pd.read_sql(query, con=engine_datalake)
        
        # Filtramos por id_registro 8 (Total)
        df['fecha'] = list(df_bdd['fecha'][df_bdd['id_registro'] == 8])
        df['empleo_total'] = list(df_bdd['cantidad_con_estacionalidad'][df_bdd['id_registro'] == 8])
        
        # Truncamiento a 3 decimales
        df['empleo_total'] = df['empleo_total'].apply(lambda x: np.trunc(x * 1000) / 1000)
        
        mapping = [
            ('empleo_privado', 2), ('empleo_publico', 3), ('empleo_casas_particulares', 4),
            ('empleo_independiente_autonomo', 5), ('empleo_independiente_monotributo', 6), 
            ('empleo_monotributo_social', 7)
        ]
        
        for col, tipo in mapping:
            df[col] = list(df_bdd['cantidad_con_estacionalidad'][df_bdd['id_registro'] == tipo])
            df[f'p_{col}'] = (df[col] * 100) / df['empleo_total']

    def _get_variances_nation(self, df):
        df['fecha'] = pd.to_datetime(df['fecha'])
        for col in ['empleo_total', 'empleo_privado']:
            df[f'vmensual_{col}'] = ((df[col] / df[col].shift(1)) - 1) * 100
            df[f'vinter_{col}']   = ((df[col] / df[col].shift(12)) - 1) * 100
            df[f'vacum_{col}']    = np.nan
            
        for anio in sorted(df['fecha'].dt.year.unique()):
            dic = df[(df['fecha'].dt.year == anio - 1) & (df['fecha'].dt.month == 12)]
            if not dic.empty:
                for col in ['empleo_total', 'empleo_privado']:
                    base = dic[col].values[0]
                    mask = df['fecha'].dt.year == anio
                    df.loc[mask, f'vacum_{col}'] = ((df[col][mask] / base) - 1) * 100

    def _table_analytics_sipa_nea(self):
        engine_datalake = self._get_engine(self.db_datalake)
        engine_dwh = self._get_engine(self.db_dwh)
        schema = self._get_schema()

        df_nea = pd.DataFrame()
        self._get_variances_nea(df_nea, engine_datalake)
        df_nea['fecha'] = pd.to_datetime(df_nea['fecha']).dt.date
        
        # Guardamos en DWH con el esquema correspondiente
        df_nea.to_sql(name="empleo_nea_variaciones", con=engine_dwh, schema=schema, if_exists='replace', index=False)
        try:
            with engine_dwh.begin() as conn_alter:
                full_table_nea = f"{schema}.empleo_nea_variaciones" if schema else "empleo_nea_variaciones"
                alter_query = f"ALTER TABLE {full_table_nea} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table_nea} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn_alter.execute(text(alter_query))
        except Exception as e:
            logger.warning(f"[LOAD] No se pudo agregar la columna updated_at a empleo_nea_variaciones: {e}")
        logger.info("[LOAD] Analytics NEA actualizados en DWH.")

    def _get_variances_nea(self, df, engine_datalake):
        provincias = {18: 'corrientes', 54: 'misiones', 22: 'chaco', 34: 'formosa'}
        ids_nea = tuple(provincias.keys())
        
        # Usamos self.tabla y engine_datalake
        query = f"SELECT fecha, id_provincia, cantidad_con_estacionalidad FROM {self.tabla} WHERE id_provincia IN {ids_nea}"
        df_bdd = pd.read_sql(query, con=engine_datalake)
        
        df['fecha'] = sorted(set(pd.to_datetime(df_bdd['fecha'])))
        
        for idp, nombre in provincias.items():
            df[f'total_{nombre}'] = list(df_bdd['cantidad_con_estacionalidad'][df_bdd['id_provincia'] == idp] * 1000)
            
        df['total_nea'] = df[[f'total_{p}' for p in provincias.values()]].sum(axis=1)
        
        for prov in list(provincias.values()) + ['nea']:
            df[f'vmensual_{prov}'] = (df[f'total_{prov}'] / df[f'total_{prov}'].shift(1) - 1) * 100
            df[f'vinter_{prov}']   = (df[f'total_{prov}'] / df[f'total_{prov}'].shift(12) - 1) * 100
            df[f'vacum_{prov}']    = np.nan
            
        for anio in sorted(df['fecha'].dt.year.unique()):
            dic = df[(df['fecha'].dt.year == anio - 1) & (df['fecha'].dt.month == 12)]
            if not dic.empty:
                for prov in list(provincias.values()) + ['nea']:
                    base = dic[f'total_{prov}'].values[0]
                    mask = df['fecha'].dt.year == anio
                    df.loc[mask, f'vacum_{prov}'] = ((df[f'total_{prov}'][mask] / base) - 1) * 100

    def close(self):
        """Cierra todos los motores de conexión abiertos."""
        for db_name, engine in self.engines.items():
            if engine:
                engine.dispose()
                logger.info(f"[LOAD] Conexión a '{db_name}' cerrada.")
        self.engines = {}