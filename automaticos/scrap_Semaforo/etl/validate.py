"""
VALIDATE - Módulo de validación de datos Semáforo
Responsabilidad: Verificar integridad de los DataFrames antes de la carga
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

COLUMNAS_REQUERIDAS = [
    'fecha',
    'combustible_vendido',
    'patentamiento_0km_auto',
    'patentamiento_0km_motocicleta',
    'pasajeros_salidos_terminal_corrientes',
    'pasajeros_aeropuerto_corrientes',
    'venta_supermercados_autoservicios_mayoristas',
    'exportaciones_aduana_corrientes_dolares',
    'exportaciones_aduana_corrientes_toneladas',
    'empleo_privado_registrado_sipa',
    'permisos_edificacion_unidades',
    'permisos_edificacion_m2'
]


class ValidateSemaforo:
    """Valida los DataFrames del Semáforo antes de cargarlos."""

    def validate(self, df_interanual: pd.DataFrame, df_intermensual: pd.DataFrame):
        logger.info("[VALIDATE] Iniciando validaciones...")
        self._validar_df(df_interanual,   "interanual")
        self._validar_df(df_intermensual, "intermensual")
        logger.info("[VALIDATE] OK — ambos DataFrames son válidos.")

    def _validar_df(self, df: pd.DataFrame, nombre: str):
        if df is None or df.empty:
            raise ValueError(f"[VALIDATE] DataFrame '{nombre}' está vacío.")

        faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
        if faltantes:
            raise ValueError(
                f"[VALIDATE] DataFrame '{nombre}' le faltan columnas: {faltantes}"
            )

        if df['fecha'].isnull().any():
            raise ValueError(
                f"[VALIDATE] DataFrame '{nombre}' tiene fechas nulas."
            )

        logger.info(
            "[VALIDATE] '%s' OK — %d filas, rango: %s → %s",
            nombre, len(df), df['fecha'].min(), df['fecha'].max()
        )