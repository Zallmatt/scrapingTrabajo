import os
import csv
import logging
import zipfile
import io
import shutil
import requests
from tableauhyperapi import HyperProcess, Telemetry, Connection

logger = logging.getLogger(__name__)

FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files')


class ExtractSRT:
    """
    Extrae los datos de SRT.
    Primero intenta descargar automáticamente el Workbook de Tableau Public,
    extrae la base de datos Hyper y genera el CSV de los últimos 3 períodos.
    Si la descarga falla, busca archivos CSV cargados manualmente en files/.
    """

    def extract(self) -> str:
        os.makedirs(FILES_DIR, exist_ok=True)
        
        # Intentar descarga automática del workbook (.twbx)
        url = "https://public.tableau.com/workbooks/Descarga-CoberturayFinanciacinRev4.twb"
        temp_zip_path = os.path.join(FILES_DIR, "temp_workbook.zip")
        temp_extract_dir = os.path.join(FILES_DIR, "temp_extracted")
        csv_output_path = os.path.join(FILES_DIR, "descarga_auto.csv")
        
        # Eliminar archivo auto previo para evitar residuos si falla la descarga actual
        if os.path.exists(csv_output_path):
            try:
                os.remove(csv_output_path)
            except Exception as e:
                logger.warning("No se pudo eliminar csv previo: %s", e)
                
        try:
            logger.info("[EXTRACT] Intentando descargar el libro de Tableau Public...")
            res = requests.get(url, timeout=90)
            if res.status_code == 200:
                content = res.content
                logger.info("[EXTRACT] Descargado libro de %d bytes. Extrayendo extracto...", len(content))
                
                with open(temp_zip_path, 'wb') as f_zip:
                    f_zip.write(content)
                
                hyper_file = None
                with zipfile.ZipFile(temp_zip_path, 'r') as z:
                    extractos_hyper = [
                        name for name in z.namelist()
                        if name.startswith("Data/")
                        and name.lower().endswith((".hyper", ".tmp"))
                    ]
                    if extractos_hyper:
                        # Tableau actualmente publica federated.hyper; se conserva
                        # compatibilidad con los paquetes antiguos que usaban .tmp.
                        nombre_hyper = next(
                            (name for name in extractos_hyper if name.lower().endswith(".hyper")),
                            extractos_hyper[0],
                        )
                        hyper_file = z.extract(nombre_hyper, path=temp_extract_dir)
                        logger.info(
                            "[EXTRACT] Extracto Hyper encontrado (%s) y extraído a: %s",
                            nombre_hyper,
                            hyper_file,
                        )
                            
                if hyper_file:
                    logger.info("[EXTRACT] Conectando a la base de datos Hyper...")
                    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
                        with Connection(endpoint=hyper.endpoint, database=hyper_file) as connection:
                            # Obtener los últimos 3 períodos disponibles
                            query_periods = 'SELECT DISTINCT "PERIODO" FROM "Extract"."Extract" ORDER BY "PERIODO" DESC LIMIT 3'
                            with connection.execute_query(query_periods) as result_periods:
                                latest_periods = [row[0] for row in result_periods]
                            logger.info("[EXTRACT] Últimos períodos en Hyper: %s", latest_periods)
                            
                            # Consultar datos de estos períodos
                            query_data = f"""
                            SELECT 
                              "PERIODO", "PROVINCIA", "SECCION", "GRUPO", "CIIU", 
                              "CANTTRABAJADORES_D", "CANTTRABAJADORES_UP", "REMUNERACION"
                            FROM "Extract"."Extract"
                            WHERE "PERIODO" IN ({", ".join([f"'{p}'" for p in latest_periods])})
                            """
                            
                            headers = [
                                'periodo', 'jurisdiccion_desc', 'seccion', 'grupo', 'ciiu', 
                                'cant_personas_trabaj_cp', 'cant_personas_trabaj_up', 'remuneracion'
                            ]
                            
                            row_count = 0
                            with open(csv_output_path, 'w', newline='', encoding='utf-8') as csvfile:
                                writer = csv.writer(csvfile, delimiter=',')
                                writer.writerow(headers)
                                
                                with connection.execute_query(query_data) as result_data:
                                    for row in result_data:
                                        periodo = row[0]
                                        provincia = row[1]
                                        seccion = row[2]
                                        grupo = row[3]
                                        ciiu = row[4]
                                        cant_cp = int(row[5]) if row[5] is not None else 0
                                        cant_up = int(row[6]) if row[6] is not None else 0
                                        
                                        remun_val = row[7]
                                        if remun_val is None:
                                            remun_str = "0"
                                        else:
                                            remun_str = f"{remun_val:.2f}".replace('.', ',')
                                            
                                        writer.writerow([
                                            periodo, provincia, seccion, grupo, ciiu,
                                            cant_cp, cant_up, remun_str
                                        ])
                                        row_count += 1
                                        
                            logger.info("[EXTRACT] Generado CSV de %d filas para períodos %s", row_count, latest_periods)
                else:
                    logger.error(
                        "[EXTRACT] No se encontró un extracto Hyper (.hyper o .tmp) en el workbook."
                    )
            else:
                logger.error("[EXTRACT] Error de conexión HTTP al descargar workbook. Status: %d", res.status_code)
                
        except Exception as e:
            logger.error("[EXTRACT] Error durante la extracción automática: %s. Se intentará usar archivos locales...", e, exc_info=True)
            
        finally:
            # Limpieza de archivos temporales
            if os.path.exists(temp_zip_path):
                try:
                    os.remove(temp_zip_path)
                except:
                    pass
            if os.path.exists(temp_extract_dir):
                try:
                    shutil.rmtree(temp_extract_dir)
                except:
                    pass

        # Validar si tenemos algún archivo CSV listo (sea el automático o alguno manual)
        csvs = [f for f in os.listdir(FILES_DIR) if f.endswith('.csv')]
        if not csvs:
            raise FileNotFoundError(
                f"No se encontraron archivos CSV en {FILES_DIR}. "
                "La descarga automática falló y no hay archivos cargados manualmente."
            )

        logger.info("[EXTRACT] Encontrados %d archivos CSV en %s para procesamiento.", len(csvs), FILES_DIR)
        return FILES_DIR

