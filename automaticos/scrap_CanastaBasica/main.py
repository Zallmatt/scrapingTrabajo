"""
MAIN - Orquestador ETL para CanastaBasica
Responsabilidad: Coordinar Extract (DB) → Transform → Validate → Load (DB)
"""
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from etl.extract import ExtractCanastaBasica
from etl.transform import TransformCanastaBasica
from etl.load import LoadCanastaBasica
from etl.validate import ValidateCanastaBasica
from etl.report import ReportCanastaBasica
from utils.logger import setup_logger
from utils.optimization import cleanup_environment
import pandas as pd



def aplicar_padding(df_raw: pd.DataFrame, logger) -> pd.DataFrame:
    from sqlalchemy import text
    from utils.utils_db import ConexionBaseDatos
    
    target_count = 2000
    date_today = datetime.now().strftime('%Y-%m-%d')
    
    # Identificar productos válidos en df_raw
    precio_normal_numeric = pd.to_numeric(df_raw['precio_normal'], errors='coerce').fillna(0)
    precio_desc_numeric = pd.to_numeric(df_raw['precio_descuento'], errors='coerce').fillna(0)
    
    valid_hoy_mask = (precio_normal_numeric > 0) | (precio_desc_numeric > 0)
    valid_hoy_ids = set(df_raw[valid_hoy_mask]['id_link_producto'].tolist())
    valid_count = len(valid_hoy_ids)
    
    logger.info(f"[PADDING] Productos válidos actuales: {valid_count}. Objetivo: {target_count}")
    
    if valid_count >= target_count:
        logger.info("[PADDING] No se requiere padding.")
        return df_raw
        
    needed = target_count - valid_count
    logger.info(f"[PADDING] Se necesitan {needed} productos adicionales.")
    
    # Conectar a Postgres para obtener los datos de ayer
    host = os.getenv('HOST_DBB2')
    user = os.getenv('USER_DBB2')
    pw = os.getenv('PASSWORD_DBB2')
    db = os.getenv('NAME_DB_CANASTA', 'canasta_basica_super')
    port = os.getenv('PORT_DBB2', 5432)
    
    db_conn = ConexionBaseDatos(host=host, user=user, password=pw, database=db, port=port)
    if not db_conn.connect_db():
        logger.error("[PADDING] No se pudo conectar a la base Postgres para el padding.")
        return df_raw
        
    try:
        # Encontrar la última fecha anterior a hoy
        query_fecha = "SELECT MAX(fecha_extraccion) FROM precios_productos WHERE fecha_extraccion < :hoy"
        with db_conn.engine.connect() as conn:
            last_date = conn.execute(text(query_fecha), {"hoy": date_today}).scalar()
            
        if not last_date:
            logger.warning("[PADDING] No se encontró ninguna fecha anterior para el relleno.")
            return df_raw
            
        logger.info(f"[PADDING] Recuperando datos de respaldo de la fecha: {last_date}")
        
        query_productos = """
            SELECT * FROM precios_productos 
            WHERE fecha_extraccion = :last_date
        """
        with db_conn.engine.connect() as conn:
            df_yesterday = pd.read_sql(text(query_productos), conn, params={"last_date": last_date})
            
        if df_yesterday.empty:
            logger.warning("[PADDING] No se encontraron productos para la fecha anterior.")
            return df_raw
            
        # Filtrar ítems válidos de ayer que no están en los válidos de hoy
        df_missing = df_yesterday[~df_yesterday['id_link_producto'].isin(valid_hoy_ids)].copy()
        df_missing = df_missing[(df_missing['precio_normal'] > 0) | (df_missing['precio_descuento'] > 0)]
        
        if len(df_missing) < needed:
            logger.warning(f"[PADDING] Solo hay {len(df_missing)} productos disponibles ayer para copiar (se necesitaban {needed}).")
            needed = len(df_missing)
            
        df_pad_db = df_missing.head(needed).copy()
        
        # Convertir formato de base de datos a formato crudo de df_raw
        df_pad_raw = pd.DataFrame()
        df_pad_raw['nombre'] = df_pad_db['nombre_producto']
        df_pad_raw['precio_normal'] = df_pad_db['precio_normal']
        df_pad_raw['precio_descuento'] = df_pad_db['precio_descuento']
        df_pad_raw['precio_por_unidad'] = df_pad_db['precio_por_unidad']
        df_pad_raw['unidad'] = df_pad_db['unidad_medida']
        df_pad_raw['descuentos'] = '[]'
        df_pad_raw['fecha'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df_pad_raw['supermercado'] = 'Relleno'
        df_pad_raw['url'] = 'Relleno'
        df_pad_raw['id_link_producto'] = df_pad_db['id_link_producto']
        df_pad_raw['peso'] = df_pad_db['peso']
        df_pad_raw['error_type'] = None
        df_pad_raw['titulo'] = None
        df_pad_raw['producto_nombre'] = None
        df_pad_raw['origen_dato'] = 'relleno'
        df_pad_raw['fecha_extraccion'] = date_today
        
        # Eliminar las contrapartes inválidas de hoy para evitar duplicados de id_link_producto
        df_final_raw = df_raw[~df_raw['id_link_producto'].isin(df_pad_raw['id_link_producto'])].copy()
        df_final_raw = pd.concat([df_final_raw, df_pad_raw], ignore_index=True)
        
        logger.info(f"[PADDING] Agregados {len(df_pad_raw)} productos de relleno. Total filas df_raw: {len(df_final_raw)}")
        return df_final_raw
        
    except Exception as e:
        logger.error(f"[PADDING] Error aplicando padding: {e}", exc_info=True)
        return df_raw
    finally:
        db_conn.close_connections()


def main():
    setup_logger("canasta_basica_scraper")
    logger = logging.getLogger(__name__)

    # Limpieza inicial de procesos huérfanos
    cleanup_environment(force=True)

    load_dotenv()
    inicio = datetime.now()
    logger.info("=" * 80)
    logger.info("=== INICIO ETL CANASTA BÁSICA - %s ===", inicio.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 80)

    extractor = None
    loader    = None

    try:

        # EXTRACT
        logger.info("1. [EXTRACT] Inicializando extractor...")
        extractor = ExtractCanastaBasica(enable_parallel=True, max_workers=2)  # 2 workers para no saturar RAM del servidor
        links_list = extractor.read_links_from_db()

        if not links_list:
            logger.error("[ERROR] No se encontraron links activos en la base de datos.")
            return

        # MODO PRUEBA: Si se pasa --test, limitamos la cantidad de links a procesar
        import sys
        if "--test" in sys.argv:
            logger.info("[TEST MODE] Limitando a un subset de links para prueba rápida.")
            df_temp = pd.DataFrame(links_list)
            # Tomar hasta 2 links de cada supermercado
            df_temp = df_temp.groupby('nombre_super').head(2)
            links_list = df_temp.to_dict('records')
            logger.info(f"[TEST MODE] Links a procesar ({len(links_list)}): {links_list}")

        df_raw = extractor.extract(links_list)
        if df_raw.empty:
            logger.error("[ERROR] La extracción no generó datos. Abortando.")
            return
        logger.info("[OK] Extracción finalizada: %d filas.", len(df_raw))

        # --- GENERAR REPORTE DE LINKS FALLIDOS ---
        try:
            report_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
            reporter = ReportCanastaBasica(report_dir)
            report_file = reporter.generate_broken_links_report(df_raw)
            if report_file:
                logger.warning(f"!!! ATENCIÓN: Se detectaron links con problemas. Reporte generado en: {report_file}")
            reporter.clean_old_reports()
        except Exception as e:
            logger.error(f"Error generando reporte de links fallidos: {e}")

        # Backup
        backup_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'files',
            f'BACKUP_RAW_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
        )
        os.makedirs(os.path.dirname(backup_file), exist_ok=True)
        try:
            df_raw.to_csv(backup_file, index=False, quoting=1, encoding='utf-8-sig') # QUOTE_ALL (1) para evitar errores de comas
            logger.info("BACKUP guardado: %s", backup_file)
        except Exception as e:
            logger.warning("No se pudo crear backup: %s", e)

        # Limpieza de backups: conservar solo los últimos 3
        try:
            archivos_backup = sorted(
                [f for f in os.listdir(os.path.dirname(backup_file)) if f.startswith('BACKUP_RAW_')],
                reverse=True
            )
            for viejo in archivos_backup[3:]:
                os.remove(os.path.join(os.path.dirname(backup_file), viejo))
                logger.info("Backup antiguo eliminado: %s", viejo)
        except Exception as e:
            logger.warning("No se pudo limpiar backups: %s", e)

        # TRANSFORM
        logger.info("2. [TRANSFORM] Normalizando datos...")
        df = TransformCanastaBasica().transform(df_raw)
        if df.empty:
            logger.error("[ERROR] DataFrame vacío tras transformación.")
            return

        # VALIDATE
        logger.info("3. [VALIDATE] Validando datos...")
        try:
            ValidateCanastaBasica().validate(df)
        except ValueError as ve:
            if "Insuficientes productos" in str(ve):
                logger.warning(f"[VALIDATE WARNING] La validación falló por falta de productos: {ve}")
                logger.info("Aplicando padding automático con datos del último día disponible...")
                df_raw = aplicar_padding(df_raw, logger)
                
                # Guardar backup del padded
                padded_backup_file = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), 'files',
                    f'BACKUP_PADDED_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
                )
                try:
                    df_raw.to_csv(padded_backup_file, index=False, quoting=1, encoding='utf-8-sig')
                    logger.info("BACKUP PADDED guardado: %s", padded_backup_file)
                except Exception as ex_back:
                    logger.warning("No se pudo crear backup padded: %s", ex_back)
                
                logger.info("Re-transformando datos con el padding aplicado...")
                df = TransformCanastaBasica().transform(df_raw)
                logger.info("Re-validando datos...")
                ValidateCanastaBasica().validate(df)
            else:
                raise

        # LOAD
        logger.info("4. [LOAD] Cargando a base de datos...")
        loader = LoadCanastaBasica()
        exito = loader.load(df)

        if exito:
            logger.info("=== Proceso ETL completado EXITOSAMENTE ===")
        else:
            logger.error("=== El proceso ETL finalizó con ERRORES en la etapa de carga ===")

    except Exception as e:
        logger.error("[ERROR CRÍTICO] %s", e, exc_info=True)
        raise
    finally:
        if extractor and hasattr(extractor, 'db') and extractor.db:
            extractor.db.close_connections()
        if loader:
            if hasattr(loader, 'db_v1') and loader.db_v1:
                loader.db_v1.close_connections()
            if hasattr(loader, 'db_v2') and loader.db_v2:
                loader.db_v2.close_connections()
        duracion = (datetime.now() - inicio).total_seconds()
        logger.info("=== FIN EJECUCIÓN - Duración total: %.2f segundos ===", duracion)
        logger.info("=" * 80)


if __name__ == "__main__":
    main()