import pandas as pd
import logging
import re
from unidecode import unidecode

logger = logging.getLogger(__name__)

class TransformANAC:
    def __init__(self, target_value="TABLA 11"):
        self.target_value = target_value
        self.column_mapping = {
            'Aeroparque': 'aeroparque', 'Bahía Blanca': 'bahia_blanca', 'Bariloche': 'bariloche',
            'Base Marambio': 'base_marambio', 'Catamarca': 'catamarca', 'Chapelco': 'chapelco',
            'Comod. Rivadavia': 'comod_rivadavia', 'Concordia': 'concordia', 'Córdoba': 'cordoba',
            'Corrientes': 'corrientes', 'El Calafate': 'el_calafate', 'El Palomar': 'el_palomar',
            'Esquel': 'esquel', 'Ezeiza': 'ezeiza', 'Formosa': 'formosa', 'General Pico': 'general_pico',
            'Goya': 'goya', 'Gualeguaychú': 'gualeguaychu', 'Iguazú': 'iguazu', 'Jujuy': 'jujuy',
            'Junín': 'junin', 'La Plata': 'la_plata', 'La Rioja': 'la_rioja', 'Malargüe': 'malargue',
            'Mar del Plata': 'mar_del_plata', 'Mendoza': 'mendoza', 'Moreno': 'moreno',
            'Morón': 'moron', 'Neuquén': 'neuquen', 'Paraná': 'parana', 'Paso de los Libres': 'paso_de_los_libres',
            'Posadas': 'posadas', 'Puerto Madryn': 'puerto_madryn', 'Reconquista': 'reconquista',
            'Resistencia': 'resistencia', 'Río Cuarto': 'rio_cuarto', 'Río Gallegos': 'rio_gallegos',
            'Río Grande': 'rio_grande', 'Rosario': 'rosario', 'Salta': 'salta', 'San Fernando': 'san_fernando',
            'San Juan': 'san_juan', 'San Luis': 'san_luis', 'San Rafael': 'san_rafael', 'Santa Fe': 'santa_fe',
            'Santa Rosa': 'santa_rosa', 'Santa Rosa de Conlara': 'santa_rosa_de_conlara',
            'Santiago del Estero': 'santiago_del_estero', 'Tandil': 'tandil', 'Termas Río Hondo': 'termas_rio_hondo',
            'Trelew': 'trelew', 'Tucumán': 'tucuman', 'Ushuaia': 'ushuaia', 'Viedma': 'viedma',
            'Villa Gesell': 'villa_gesell', 'Villa Reynolds': 'villa_reynolds', 'Otros': 'otros'
        }
        self._mapping_norm = {self._norm_txt(k): v for k, v in self.column_mapping.items()}

    @staticmethod
    def _norm_txt(valor):
        return unidecode(str(valor).lower()).strip()

    def _elegir_hoja(self, file_path):
        xl = pd.ExcelFile(file_path)
        vigentes = [
            s for s in xl.sheet_names
            if s.upper().startswith('OUT')
            and 'CONTROL' not in s.upper()
            and 'PROPUESTA' not in s.upper()
        ]
        hoja = vigentes[-1] if vigentes else xl.sheet_names[0]
        logger.info("Hoja ANAC seleccionada: %s (disponibles: %s)", hoja, xl.sheet_names)
        return hoja

    def _nombre_aeropuerto(self, row):
        for cell in row.values:
            if pd.isna(cell):
                continue
            clave = self._norm_txt(cell)
            if clave in self._mapping_norm:
                return self._mapping_norm[clave]
        return None

    def transform(self, file_path):
        logger.info(f"Leyendo archivo Excel: {file_path}")
        hoja = self._elegir_hoja(file_path)
        df_raw = pd.read_excel(file_path, sheet_name=hoja, header=None, dtype=str)
        
        start_row = None
        for i, row in df_raw.iterrows():
            fila_texto = [str(cell).strip().upper() for cell in row.values if pd.notna(cell)]
            if "TABLA 11" in fila_texto:
                if i + 1 < len(df_raw):
                    fila_siguiente = str(df_raw.iloc[i+1].values).upper()
                    if "PASAJEROS" in fila_siguiente:
                        start_row = i + 2
                        logger.info(f"TABLA 11 detectada en fila {i}, datos inician en {start_row}")
                        break

        if start_row is None:
            raise ValueError("No se encontró el bloque TABLA 11 + Pasajeros")

        end_row = len(df_raw)
        for i in range(start_row, len(df_raw)):
            fila_texto = str(df_raw.iloc[i].values).upper()
            if "TABLA" in fila_texto and i > start_row + 5:
                end_row = i
                logger.info(f"Fin de Tabla 11 detectado en fila {end_row}")
                break
        
        fila_años = df_raw.iloc[start_row - 2]
        fila_meses = df_raw.iloc[start_row - 1]
        en_miles = '[000]' in str(fila_meses.values).upper()
        
        meses_map = {'ene':1, 'feb':2, 'mar':3, 'abr':4, 'may':5, 'jun':6, 
                     'jul':7, 'ago':8, 'sep':9, 'oct':10, 'nov':11, 'dic':12}
        
        fechas_dict = {}
        ultimo_anio = None
        for col_idx in range(1, len(fila_meses)):
            anio_raw = str(fila_años.iloc[col_idx]).strip()
            mes_raw = str(fila_meses.iloc[col_idx]).strip().replace('.', '')[:3].lower()
            
            if anio_raw.isdigit():
                ultimo_anio = int(anio_raw)
            
            mes_num = meses_map.get(mes_raw)
            if ultimo_anio and mes_num:
                fechas_dict[col_idx] = pd.Timestamp(year=ultimo_anio, month=mes_num, day=1)

        if not fechas_dict:
            raise ValueError("[TRANSFORM] No se pudieron armar fechas de TABLA 11.")

        df_datos = df_raw.iloc[start_row:end_row].reset_index(drop=True)
        resultados = []

        for _, row in df_datos.iterrows():
            nombre_mapeado = self._nombre_aeropuerto(row)
            if not nombre_mapeado:
                continue
            
            for col_idx, fecha_obj in fechas_dict.items():
                val = row[col_idx]
                if pd.isna(val) or str(val).strip() in ['nan', '-', '']:
                    continue
                cantidad = self._parse_cantidad(val, en_miles)
                if cantidad is None:
                    continue
                resultados.append({
                    'fecha': fecha_obj,
                    'aeropuerto': nombre_mapeado,
                    'cantidad': cantidad
                })
        
        df_final = pd.DataFrame(resultados)
        if df_final.empty:
            raise ValueError("[TRANSFORM] TABLA 11 no produjo filas. Revisar hoja/estructura del Excel ANAC.")
        df_final = df_final.groupby(['fecha', 'aeropuerto'], as_index=False)['cantidad'].sum()
        
        logger.info(f"[OK] Transformación lista. Filas: {len(df_final)}")
        return df_final

    @staticmethod
    def _parse_cantidad(val, en_miles):
        s_val = str(val).strip().replace(' ', '')
        try:
            if en_miles:
                valor_num = float(s_val.replace(',', '.'))
                return int(round(valor_num * 1000))
            # Formato viejo argentino: 18.578 = 18578
            s_val = s_val.replace('.', '').replace(',', '.')
            return int(float(s_val))
        except ValueError:
            return None

    def _parse_fecha_anac(self, valor):
        """Convierte 'ene-24' o similar en una fecha de Python"""
        meses = {'ene':1, 'feb':2, 'mar':3, 'abr':4, 'may':5, 'jun':6, 
                 'jul':7, 'ago':8, 'sep':9, 'oct':10, 'nov':11, 'dic':12}
        try:
            s = str(valor).lower().strip()
            match = re.search(r'([a-z]{3})-(\d{2})', s)
            if match:
                m_str, a_str = match.groups()
                mes = meses.get(m_str)
                anio = 2000 + int(a_str)
                if mes: return pd.Timestamp(year=anio, month=mes, day=1)
            return None
        except: return None

    def _aplicar_correcciones(self, df):
        if 'aeropuerto' not in df.columns: return df
        mask = df['aeropuerto'] == 'corrientes'
        correcciones = {32200.000000000004: 19646, 39478: 18555, 40395: 19648}
        for v_err, v_ok in correcciones.items():
            df.loc[mask & (df['cantidad'] == v_err), 'cantidad'] = v_ok
        return df

    def _convertir_a_formato_long(self, df):
        """Convierte el DataFrame de ancho (columnas aeropuertos) a largo (una fila por dato)."""
        columnas_aeropuertos = [c for c in df.columns if c != "fecha"]
        
        df_long = df.melt(
            id_vars="fecha",
            value_vars=columnas_aeropuertos,
            var_name="aeropuerto",
            value_name="cantidad"
        )
        
        # Asegurar que cantidad sea numérico y rellenar nulos
        df_long["cantidad"] = pd.to_numeric(df_long["cantidad"], errors="coerce").fillna(0)
        return df_long

    def _buscar_fila_por_valor(self, df, target_value):
        """Busca el índice de la fila que contiene el texto objetivo."""
        target_norm = target_value.lower().strip().replace(" ", "")
        for index, row in df.iterrows():
            for cell in row:
                if isinstance(cell, str) and cell.lower().strip().replace(" ", "") == target_norm:
                    return index
        return None

   