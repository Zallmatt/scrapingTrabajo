"""
VALIDATE - Módulo de validación de datos IPC
"""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class ValidateIPC:
    def validate(self, df: pd.DataFrame):
        if df is None or df.empty:
            raise ValueError("[VALIDATE] DataFrame IPC vacío.")

        requeridas = ['fecha', 'id_region', 'id_subdivision', 'valor']
        faltantes = [c for c in requeridas if c not in df.columns]
        if faltantes:
            raise ValueError(f"[VALIDATE] Columnas faltantes: {faltantes}")

        fechas = pd.to_datetime(df['fecha'])
        dias_raros = fechas[fechas.dt.day != 1]
        if len(dias_raros):
            # Tras normalizar en transform no deberían quedar; si aparecen, alertar.
            unicas = sorted({d.date().isoformat() for d in dias_raros})
            logger.warning(
                "[VALIDATE] Hay fechas con día distinto de 1 (%d filas): %s. "
                "Revisar normalización / Excel INDEC (caso abril 2026).",
                len(dias_raros),
                unicas[:10],
            )

        if 'var_mensual' in df.columns:
            nulos = int(df['var_mensual'].isna().sum())
            if nulos:
                por_fecha = (
                    df.loc[df['var_mensual'].isna(), 'fecha']
                    .pipe(pd.to_datetime)
                    .dt.date
                    .value_counts()
                    .sort_index()
                )
                resumen = ", ".join(f"{f}: {c}" for f, c in por_fecha.items())
                logger.warning(
                    "[VALIDATE] %d filas con var_mensual NULL (se carga igual; "
                    "el valor/índice es prioritario). Por fecha: %s",
                    nulos,
                    resumen,
                )

        valores_nulos = df['valor'].isna()
        fechas_mes = fechas.dt.to_period('M')
        regiones_sin_relevamiento = df['id_region'].isin(range(2, 8))
        faltantes_historicos_abril = (
            (fechas_mes == pd.Period('2020-04', freq='M'))
            & regiones_sin_relevamiento
            & df['id_subdivision'].isin([18, 19, 43])
        )
        faltantes_historicos_mayo_julio = (
            fechas_mes.isin(pd.period_range('2020-05', '2020-07', freq='M'))
            & regiones_sin_relevamiento
            & (df['id_subdivision'] == 43)
        )
        faltantes_historicos = valores_nulos & (
            faltantes_historicos_abril | faltantes_historicos_mayo_julio
        )

        nulos_historicos = int(faltantes_historicos.sum())
        if nulos_historicos:
            logger.warning(
                "[VALIDATE] Se aceptan %d valores NULL históricos informados como "
                "/// por INDEC durante abril-julio de 2020.",
                nulos_historicos,
            )

        nulos_inesperados = int((valores_nulos & ~faltantes_historicos).sum())
        if nulos_inesperados:
            raise ValueError(
                f"[VALIDATE] {nulos_inesperados} filas inesperadas con valor "
                "(índice IPC) NULL. "
                "No se puede continuar sin el dato principal."
            )

        fecha_max = fechas.max()
        logger.info(
            "[VALIDATE] OK — IPC: %d filas. Último mes: %s.",
            len(df),
            fecha_max.date(),
        )
