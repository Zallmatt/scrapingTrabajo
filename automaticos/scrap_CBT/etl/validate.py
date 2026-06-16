"""
Validador de datos para el proceso ETL de CBT/CBA.
Responsabilidad: Validar consistencia de datos en minúsculas.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Validador de datos para cba, cbt y nea.
    """
    
    def __init__(self):
        self.errores = []
        self.advertencias = []
        # Estándar de nombres en minúsculas
        self.cols_criticas = ['fecha', 'cba_adulto', 'cbt_adulto', 'cba_hogar', 'cbt_hogar']
        self.cols_nea = ['cba_nea', 'cbt_nea']
        self.todas_las_cols = self.cols_criticas + self.cols_nea
    
    def validar_dataframe(self, df):
        """
        Valida el DataFrame completo.
        """
        logger.info("[VALIDATE CBT] Iniciando validación de datos de Canasta Básica.")
        
        self.errores = []
        self.advertencias = []
        
        # 1. Normalizar columnas a minúsculas por si acaso
        df.columns = [str(col).lower() for col in df.columns]
        
        # Validaciones
        self._validar_columnas_requeridas(df)
        self._validar_tipos_datos(df)
        self._validar_valores_nulos(df)
        self._validar_rangos(df)
        self._validar_coherencia_temporal(df)
        self._validar_tendencias(df)
        
        es_valido = len(self.errores) == 0
        
        if es_valido:
            logger.info(f"[VALIDATE CBT] Validación exitosa. Se encontraron {len(self.advertencias)} advertencias.")
        else:
            logger.error(f"[VALIDATE CBT] Validación fallida. Se encontraron {len(self.errores)} errores y {len(self.advertencias)} advertencias.")
        
        # Loguear detalles de errores y advertencias
        if self.errores:
            for error in self.errores:
                logger.error(f"[VALIDATE CBT]   - Error: {error}")
        
        if self.advertencias:
            for adv in self.advertencias:
                logger.warning(f"[VALIDATE CBT]   - Advertencia: {adv}")

        return es_valido, self.errores, self.advertencias
    
    def _validar_columnas_requeridas(self, df):
        """Valida que existan todas las columnas requeridas en minúsculas."""
        for col in self.todas_las_cols:
            if col not in df.columns:
                self.errores.append(f"Columna requerida '{col}' no encontrada")
    
    def _validar_tipos_datos(self, df):
        """Valida que los tipos de datos sean correctos."""
        if 'fecha' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['fecha']):
                self.errores.append("La columna 'fecha' debe ser de tipo datetime")
        
        for col in ['cba_adulto', 'cbt_adulto', 'cba_hogar', 'cbt_hogar', 'cba_nea', 'cbt_nea']:
            if col in df.columns:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    self.errores.append(f"La columna '{col}' debe ser numérica")
    
    def _validar_valores_nulos(self, df):
        """Valida la presencia de valores nulos."""
        for col in self.cols_criticas:
            if col in df.columns:
                nulos = df[col].isna().sum()
                if nulos > 0:
                    self.errores.append(f"La columna '{col}' tiene {nulos} valores nulos")
        
        # Advertir sobre nulos en NEA (es común tener muchos al principio)
        if 'cba_nea' in df.columns:
            nulos_nea = df['cba_nea'].isna().sum()
            if nulos_nea > len(df) * 0.5:
                self.advertencias.append(f"La columna 'cba_nea' tiene {nulos_nea} nulos ({nulos_nea/len(df)*100:.1f}%)")
    
    def _validar_rangos(self, df):
        """Valida que CBA < CBT y valores sean positivos."""
        if 'cba_adulto' in df.columns and 'cbt_adulto' in df.columns:
            invalidos = df[df['cba_adulto'] > df['cbt_adulto']]
            if len(invalidos) > 0:
                self.errores.append(f"Hay {len(invalidos)} filas donde cba_adulto > cbt_adulto")
        
        for col in ['cba_adulto', 'cbt_adulto', 'cba_hogar', 'cbt_hogar']:
            if col in df.columns:
                negativos = df[df[col] < 0]
                if len(negativos) > 0:
                    self.errores.append(f"La columna '{col}' tiene {len(negativos)} valores negativos")
    
    def _validar_coherencia_temporal(self, df):
        """Valida la coherencia temporal de los datos."""
        if 'fecha' not in df.columns:
            return
        
        if not df['fecha'].is_monotonic_increasing:
            self.advertencias.append("Las fechas no están ordenadas cronológicamente")
        
        duplicados = df['fecha'].duplicated().sum()
        if duplicados > 0:
            self.errores.append(f"Hay {duplicados} fechas duplicadas")
        
        df_sorted = df.sort_values('fecha')
        diff = df_sorted['fecha'].diff()
        gaps = diff[diff > pd.Timedelta(days=35)] 
        if len(gaps) > 0:
            self.advertencias.append(f"Hay {len(gaps)} gaps temporales mayores a un mes")
    
    def _validar_tendencias(self, df):
        """Valida que las variaciones no sean absurdas."""
        if 'cba_adulto' not in df.columns or len(df) < 2:
            return
        
        df_sorted = df.sort_values('fecha').copy()
        df_sorted['var_cba'] = df_sorted['cba_adulto'].pct_change()
        
        # Advertir sobre variaciones > 80% mensual (ajustado por inflación actual)
        extremas = df_sorted[abs(df_sorted['var_cba']) > 0.8]
        if len(extremas) > 0:
            self.advertencias.append(f"Variaciones mensuales extremas en cba_adulto")
    
    def generar_reporte(self):
        """Genera un reporte de validación formateado."""
        reporte = "\n" + "="*60 + "\n"
        reporte += "REPORTE DE VALIDACIÓN DE DATOS (ESTÁNDAR MINÚSCULAS)\n"
        reporte += "="*60 + "\n\n"
        
        if not self.errores and not self.advertencias:
            reporte += "✓ Todos los datos son válidos\n"
        else:
            if self.errores:
                reporte += f"ERRORES ({len(self.errores)}):\n"
                for i, error in enumerate(self.errores, 1):
                    reporte += f"  {i}. {error}\n"
                reporte += "\n"
            
            if self.advertencias:
                reporte += f"ADVERTENCIAS ({len(self.advertencias)}):\n"
                for i, adv in enumerate(self.advertencias, 1):
                    reporte += f"  {i}. {adv}\n"
        
        reporte += "="*60 + "\n"
        return reporte
