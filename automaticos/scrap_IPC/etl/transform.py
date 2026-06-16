"""
TRANSFORM - Módulo de transformación de datos IPC
Responsabilidad: Procesar Excels y generar DataFrame unificado
"""
import pandas as pd
from sqlalchemy import create_engine
import os
from numpy import nan
from unidecode import unidecode
import logging

logger = logging.getLogger(__name__)

class TransformIPC:
    
    def __init__(self, host, user, password, database, port=None, version="1"):
        # Detectamos el motor según la versión para leer el diccionario
        self.version = str(version)
        if self.version == "1":
            # MySQL
            puerto = port if port else 3306
            self.connection_string = f"mysql+pymysql://{user}:{password}@{host}:{puerto}/{database}"
            logger.info(f"[TRANSFORM] Configurado para leer diccionario desde MySQL ({host})")
        else:
            # PostgreSQL
            puerto = port if port else 5432
            self.connection_string = f"postgresql+psycopg2://{user}:{password}@{host}:{puerto}/{database}"
            logger.info(f"[TRANSFORM] Configurado para leer diccionario desde PostgreSQL ({host})")
            
        self.diccionario = None

    def transform(self, rutas_archivos):
        """
        Orquesta la transformación de los archivos descargados
        Args:
            rutas_archivos (dict): Diccionario con paths 'nacional', 'aperturas', etc.
        """
        try:
            logger.info(f"Iniciando transformación de datos IPC usando base v{self.version}...")
            
            # 1. Construir diccionario desde BD
            self._construir_diccionario()
            
            path_ipc_mes_ano = rutas_archivos['nacional']
            path_ipc_apertura = rutas_archivos['aperturas']

            # 2. Obtención de VALORES (Índices)
            logger.info("Procesando valores de índices...")
            df_nacion_valores = self._construir_datos_nacionales(path_ipc_mes_ano, 2, 'valor')
            df_region_valores = self._armado_dfs(path_ipc_apertura, 2, 1, 'valor')
            
            df_valores = pd.concat([df_nacion_valores, df_region_valores])
            df_valores = df_valores.sort_values(['id_region','id_subdivision']).reset_index(drop=True)

            # 3. Obtención de VAR. MENSUAL
            logger.info("Procesando variaciones mensuales...")
            df_nacion_var = self._construir_datos_nacionales(path_ipc_mes_ano, 0, 'var_mensual')
            df_region_var = self._armado_dfs(path_ipc_apertura, 0, 2, 'var_mensual')
            
            df_variaciones = pd.concat([df_nacion_var, df_region_var])
            df_variaciones = df_variaciones.sort_values(['id_region','id_subdivision']).reset_index(drop=True)

            # 4. Obtención de VAR. INTERANUAL
            logger.info("Procesando variaciones interanuales...")
            df_nacion_inter = self._construir_datos_nacionales(path_ipc_mes_ano, 1, 'var_interanual')
            df_region_inter = self._armado_dfs(path_ipc_apertura, 1, 1, 'var_interanual')
            
            df_interanuales = pd.concat([df_nacion_inter, df_region_inter])
            df_interanuales = df_interanuales.sort_values(['id_region','id_subdivision']).reset_index(drop=True)

            # 5. Concatenación final y Cálculos
            logger.info("Unificando DataFrames y calculando acumulados...")
            df_final = self._concatenacion_final(df_valores, df_variaciones, df_interanuales)
            
            # Limpieza y conversión
            df_final[['valor','var_mensual','var_interanual']] = df_final[['valor','var_mensual','var_interanual']].replace('///', None).astype(float)
            
            # Pasar porcentajes a decimales
            df_final['var_mensual'] = df_final['var_mensual'] / 100
            df_final['var_interanual'] = df_final['var_interanual'] / 100
            
            # Cálculo acumulada
            self._calculo_var_acumulada(df_final)

            logger.info("Aplicando ordenamiento final estricto...")
        
            # Ordenamos por: Fecha -> Región -> Categoría -> División -> Subdivisión
            # Esto asegura que los datos se vean igual siempre.
            df_final = df_final.sort_values(
                by=['fecha', 'id_region', 'id_categoria', 'id_division', 'id_subdivision'],
                ascending=[True, True, True, True, True] 
            )
            
            # Reseteamos el índice para que empiece en 0, 1, 2... ordenadamente
            df_final = df_final.reset_index(drop=True)

            logger.info(f"[OK] Transformación completada. {len(df_final)} registros generados.")
            return df_final

        except Exception as e:
            logger.error(f"Error en transformación IPC: {e}")
            raise

    def _construir_diccionario(self):
        """Lee el diccionario unificado (dicc_ipc) de la base de datos activa"""
        engine = create_engine(self.connection_string)
        try:
            # Ahora lee de dicc_ipc, que es el nombre unificado que acordamos
            query = "SELECT id_categoria, id_division, id_subdivision, nombre FROM dicc_ipc"
            tabla_dicc = pd.read_sql_query(query, con=engine) 
            
            self.diccionario = {}
            for _, row in tabla_dicc.iterrows():
                key = self._formatear_key(row['nombre'])
                self.diccionario[key] = [
                    int(row['id_categoria']), 
                    int(row['id_division']), 
                    int(row['id_subdivision'])
                ]
            logger.info(f"[TRANSFORM] Diccionario cargado desde v{self.version}: {len(self.diccionario)} entradas.")
        except Exception as e:
            logger.error(f"[ERROR] No se pudo cargar el diccionario desde la base v{self.version}: {e}")
            raise
        finally:
            engine.dispose()

    def _formatear_key(self, key):
        key = unidecode(str(key).lower())
        return key.replace(',', '').replace('.', '').replace(' ', '')

    def _construir_datos_nacionales(self, path, num_hoja, nombre_col_valor):
        df_nacion = pd.read_excel(path, sheet_name=num_hoja, skiprows=5, nrows=16)
        df_nacion = df_nacion.iloc[3:]
        df_nacion.rename(columns={'Total nacional': 'claves_listas'}, inplace=True)
        
        df_nacion['claves_listas'] = df_nacion['claves_listas'].apply(self._formatear_key)
        df_nacion['claves_listas'] = df_nacion['claves_listas'].map(self.diccionario)
        
        df_nacion[['id_categoria', 'id_division', 'id_subdivision']] = pd.DataFrame(
            df_nacion['claves_listas'].tolist(), index=df_nacion.index
        )
        df_nacion = df_nacion.drop('claves_listas', axis=1)
        
        df_melted = pd.melt(
            df_nacion, 
            id_vars=['id_categoria', 'id_division', 'id_subdivision'], 
            var_name='fecha', 
            value_name=nombre_col_valor
        )
        
        df_melted['id_region'] = 1
        return df_melted[['fecha', 'id_region', 'id_categoria', 'id_division', 'id_subdivision', nombre_col_valor]]

    def _armado_dfs(self, path, num_hoja, filas_a_eliminar, nombre_col_valor):
        df_original = pd.read_excel(path, sheet_name=num_hoja, skiprows=4, nrows=295)
        
        # Índices hardcodeados según estructura del excel INDEC
        indices = {
            'GBA': (df_original[df_original.iloc[:, 0] == 'Región GBA'].index[0], 48, 2),
            'Pampeana': (df_original[df_original.iloc[:, 0] == 'Región Pampeana'].index[0], 46, 3),
            'Noroeste': (df_original[df_original.iloc[:, 0] == 'Región Noroeste'].index[0], 46, 4),
            'Noreste': (df_original[df_original.iloc[:, 0] == 'Región Noreste'].index[0], 46, 5),
            'Cuyo': (df_original[df_original.iloc[:, 0] == 'Región Cuyo'].index[0], 46, 6),
            'Patagonia': (df_original[df_original.iloc[:, 0] == 'Región Patagonia'].index[0], 46, 7)
        }
        
        df_acum = pd.DataFrame()

        for zona, (idx, offset, id_region) in indices.items():
            df_region = df_original.iloc[idx : idx + offset].copy()
            
            # Paso 1: headers
            df_region.columns = df_region.iloc[0]
            df_region = df_region.iloc[1:,]
            df_region = df_region.dropna(how='all')
            
            # Paso 2: mapeo
            nom_col = df_region.columns[0]
            # Mapear claves a IDs y guardar en una serie temporal para evitar el TypeError
            id_lists = df_region[nom_col].apply(self._formatear_key).map(self.diccionario)
            
            df_region[['id_categoria', 'id_division', 'id_subdivision']] = pd.DataFrame(
                id_lists.tolist(), index=df_region.index
            )
            df_region = df_region.drop(nom_col, axis=1)
            
            # Paso 3: melt
            df_melted = pd.melt(
                df_region, 
                id_vars=['id_categoria', 'id_division', 'id_subdivision'], 
                var_name='fecha', 
                value_name=nombre_col_valor
            )
            
            df_melted['id_region'] = id_region
            df_acum = pd.concat([df_acum, df_melted])
            
        return df_acum[['fecha', 'id_region', 'id_categoria', 'id_division', 'id_subdivision', nombre_col_valor]]

    def _concatenacion_final(self, df_val, df_var, df_inter):
        df_val['fecha'] = pd.to_datetime(df_val['fecha'])
        df_var['fecha'] = pd.to_datetime(df_var['fecha'])
        df_inter['fecha'] = pd.to_datetime(df_inter['fecha'])
        
        df_final = pd.merge(df_val, df_var[['fecha', 'id_region', 'id_subdivision', 'var_mensual']], 
                          on=['fecha', 'id_region', 'id_subdivision'], how='left')
        
        df_final = pd.merge(df_final, df_inter[['fecha', 'id_region', 'id_subdivision', 'var_interanual']], 
                          on=['fecha', 'id_region', 'id_subdivision'], how='left')
        return df_final

    def _calculo_var_acumulada(self, df):
        # Optimización: Vectorización en lugar de bucles anidados
        df.sort_values(['id_region', 'id_subdivision', 'fecha'], inplace=True)
        
        # Shift para obtener el valor de diciembre del año anterior
        # Esto requiere lógica compleja si no están todas las fechas. 
        # Mantendremos la lógica original del usuario pero optimizada si es posible, 
        # o usamos la lógica original dentro de la clase para seguridad.
        
        # Implementación iterativa original adaptada a la clase (es segura)
        subdivisiones_unicas = list(range(1, 46))
        regiones = [1, 2, 3, 4, 5, 6, 7]
        anios = pd.unique(df['fecha'].dt.year)
        
        # Mapeo rápido para busqueda
        df['year'] = df['fecha'].dt.year
        df['month'] = df['fecha'].dt.month
        
        # Crear un diccionario para acceso rápido (idx: region_sub_year_month -> valor)
        lookup = df.set_index(['id_region', 'id_subdivision', 'year', 'month'])['valor'].to_dict()
        
        def get_acumulada(row):
            try:
                valor_actual = row['valor']
                anio_actual = row['fecha'].year
                
                # Buscar valor de diciembre del año anterior
                clave_anterior = (row['id_region'], row['id_subdivision'], anio_actual - 1, 12)
                valor_anterior = lookup.get(clave_anterior)
                
                if valor_anterior:
                    return (valor_actual / valor_anterior) - 1
                return nan
            except:
                return nan

        df['var_acumulada'] = df.apply(get_acumulada, axis=1)
        df.drop(['year', 'month'], axis=1, inplace=True)