"""
EXTRACT - Módulo de extracción de datos ANAC
Responsabilidad: Descargar y extraer archivos desde la fuente

NOTA: Actualmente usa requests (no requiere Selenium).
Si en el futuro se necesita Selenium, usar modo headless para Linux.
"""
import requests
import os
import re
import urllib3
import zipfile
import shutil
import logging
import time

logger = logging.getLogger(__name__)

class ExtractANAC:
    """Clase para extraer datos de ANAC"""

    MAX_EDAD_CACHE_SEGUNDOS = 45 * 24 * 60 * 60
    MAX_EDAD_ZIP_PREDESCARGADO_SEGUNDOS = 2 * 60 * 60
    
    def __init__(self, use_selenium=False, headless=True):
        """
        Inicializa la clase para descargar archivos de ANAC
        
        Args:
            use_selenium: Si True, usa Selenium (por defecto False, usa requests)
            headless: Si True y use_selenium=True, ejecuta en modo headless (para Linux)
        """
        self.url_base = 'https://datos.anac.gob.ar/estadisticas/'
        self.url_descarga = 'https://docs.anac.gob.ar/index.php/s/4ptegdXanm2rWJG/download'
        # Directorio del módulo (etl/) y carpeta files en el directorio padre
        self.directorio_actual = os.path.dirname(os.path.abspath(__file__))
        self.directorio_proyecto = os.path.dirname(self.directorio_actual)  # Directorio scrap_ANAC
        self.carpeta_files = os.path.join(self.directorio_proyecto, 'files')
        self.nombre_archivo_zip = 'anac_estadisticas.zip'
        self.nombre_archivo_excel = 'anac.xlsx'
        self.use_selenium = use_selenium
        self.headless = headless
        self.driver = None

    def extract(self, archivo_historico=False):
        """
        Descarga el archivo comprimido de estadísticas de la ANAC y lo descomprime
        
        Returns:
            str: Ruta completa al archivo Excel extraído
        """
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Crear carpeta files si no existe
            if not os.path.exists(self.carpeta_files):
                os.makedirs(self.carpeta_files)
                logger.info(f"Carpeta creada: {self.carpeta_files}")

            ruta_zip = os.path.join(self.carpeta_files, self.nombre_archivo_zip)
            ruta_excel = os.path.join(self.carpeta_files, self.nombre_archivo_excel)

            # Verificar espacio libre antes de descargar
            self._verificar_espacio_disco()
            
            # Verificar si el archivo Excel ya existe y es reciente (menos de 1 hora)
            if os.path.exists(ruta_excel):
                tiempo_archivo = os.path.getmtime(ruta_excel)
                tiempo_actual = time.time()
                if (tiempo_actual - tiempo_archivo) < 3600:  # 1 hora
                    logger.info(f"[OK] Usando archivo Excel existente (descargado hace menos de 1 hora)")
                    return ruta_excel

            # GitHub Actions puede dejar un ZIP reciente cuando Donweb no tiene
            # conectividad directa con docs.anac.gob.ar.
            if self._zip_predescargado_reutilizable(ruta_zip):
                logger.info("[OK] Usando ZIP de ANAC predescargado por GitHub Actions.")
            else:
                logger.info(f"Descargando archivo comprimido desde: {self.url_descarga}")
                try:
                    self._descargar_zip(ruta_zip)
                except Exception:
                    if self._cache_excel_reutilizable(ruta_excel):
                        edad_dias = (time.time() - os.path.getmtime(ruta_excel)) / 86400
                        logger.warning(
                            "[FALLBACK] ANAC no respondió. Se reutiliza el último Excel "
                            "válido disponible (antigüedad: %.1f días).",
                            edad_dias,
                        )
                        self._limpiar_archivos_temporales(ruta_zip)
                        return ruta_excel
                    raise

            # Extraer archivo Excel
            logger.info("Descomprimiendo archivo...")
            self._extraer_excel(ruta_zip, ruta_excel, archivo_historico)

            # Limpiar archivos temporales
            self._limpiar_archivos_temporales(ruta_zip)
            
            logger.info(f"[OK] Archivo Excel extraído exitosamente: {ruta_excel}")
            return ruta_excel

        except Exception as e:
            logger.error(f"Error en extracción: {e}")
            raise
        finally:
            # Cerrar driver de Selenium si se usó
            if self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                except:
                    pass

    def _cache_excel_reutilizable(self, ruta_excel):
        """Acepta como reserva solamente un XLSX válido y con menos de 45 días."""
        if not os.path.isfile(ruta_excel):
            return False

        edad = time.time() - os.path.getmtime(ruta_excel)
        if edad > self.MAX_EDAD_CACHE_SEGUNDOS:
            logger.error(
                "[FALLBACK] El Excel disponible tiene %.1f días; supera el máximo de 45 días.",
                edad / 86400,
            )
            return False

        if not zipfile.is_zipfile(ruta_excel):
            logger.error("[FALLBACK] El archivo disponible no es un XLSX válido: %s", ruta_excel)
            return False

        return True

    def _zip_predescargado_reutilizable(self, ruta_zip):
        """Detecta el ZIP fresco que el workflow copia al servidor antes del DAG."""
        if not os.path.isfile(ruta_zip):
            return False

        edad = time.time() - os.path.getmtime(ruta_zip)
        return (
            edad <= self.MAX_EDAD_ZIP_PREDESCARGADO_SEGUNDOS
            and zipfile.is_zipfile(ruta_zip)
        )

    def _descargar_zip(self, ruta_zip):
        """
        Descarga el archivo ZIP con reintentos
        
        Si use_selenium=True, usa Selenium (útil si la descarga requiere JavaScript).
        Si use_selenium=False, usa requests (más rápido, funciona en Linux sin problemas).
        """
        if self.use_selenium:
            return self._descargar_zip_selenium(ruta_zip)
        else:
            return self._descargar_zip_requests(ruta_zip)
    
    def _descargar_zip_requests(self, ruta_zip):
        """Descarga el archivo ZIP usando requests (método actual, funciona en Linux)"""
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                response = requests.get(
                    self.url_descarga,
                    verify=False,
                    timeout=60,
                    headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'},
                )
                if response.status_code == 200:
                    with open(ruta_zip, 'wb') as file:
                        file.write(response.content)
                    logger.info(f"[OK] Archivo comprimido descargado: {ruta_zip} ({len(response.content)} bytes)")
                    return
                else:
                    raise Exception(f"Error HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                if intento < max_intentos - 1:
                    logger.warning(f"Intento {intento + 1} falló: {e}. Reintentando...")
                    continue
                else:
                    raise Exception(f"Error después de {max_intentos} intentos: {e}")
    
    def _descargar_zip_selenium(self, ruta_zip):
        """
        Descarga el archivo ZIP usando Selenium (para casos que requieren JavaScript)
        Configurado para funcionar en Linux con modo headless
        """
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
            
            # Configurar Chrome para Linux (headless)
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')  # Sin ventana (para Linux)
                chrome_options.add_argument('--no-sandbox')  # Necesario para Linux
                chrome_options.add_argument('--disable-dev-shm-usage')  # Evita problemas de memoria en Linux
                chrome_options.add_argument('--disable-gpu')  # No necesita GPU en servidor
                logger.info("Configurando Selenium en modo headless (para Linux)")
            
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
            
            # Buscar chromedriver (puede estar en la carpeta selenium del proyecto)
            chromedriver_path = None
            possible_paths = [
                os.path.join(self.directorio_actual, 'selenium', 'chromedriver'),
                os.path.join(self.directorio_actual, '..', '..', 'selenium', 'chromedriver'),
                '/usr/local/bin/chromedriver',
                '/usr/bin/chromedriver',
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    break
            
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # Intentar usar chromedriver del PATH
                self.driver = webdriver.Chrome(options=chrome_options)
            
            logger.info(f"Descargando con Selenium desde: {self.url_descarga}")
            self.driver.get(self.url_descarga)
            
            # Esperar a que se descargue (ajustar según sea necesario)
            time.sleep(5)
            
            # Si hay un botón de descarga, hacer clic
            try:
                download_button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "a"))
                )
                download_button.click()
                time.sleep(10)  # Esperar descarga
            except:
                pass
            
            # Buscar el archivo descargado en la carpeta de descargas
            # (implementar lógica según sea necesario)
            logger.warning("[WARNING] Descarga con Selenium no completamente implementada")
            logger.info("💡 Considera usar requests (use_selenium=False) que funciona mejor en Linux")
            
            # Por ahora, lanzar excepción indicando que se debe usar requests
            raise NotImplementedError(
                "Descarga con Selenium no está completamente implementada. "
                "Usa use_selenium=False para usar requests (recomendado para Linux)."
            )
            
        except ImportError:
            logger.error("Selenium no está instalado. Instala con: pip install selenium")
            raise
        except Exception as e:
            logger.error(f"Error en descarga con Selenium: {e}")
            raise

    def _extraer_excel(self, ruta_zip, ruta_excel_final, archivo_historico=False):
        """Extrae el Excel de series históricas del ZIP (sin hardcodear el año de cierre)."""
        try:
            with zipfile.ZipFile(ruta_zip, 'r') as zf:
                contenidos = zf.namelist()
                logger.debug(f"Archivos en el ZIP: {contenidos}")

                exceles = [
                    n for n in contenidos
                    if n.lower().endswith(('.xlsx', '.xls')) and 'series-historicas' in n.lower()
                ]
                if archivo_historico:
                    candidatos = [n for n in exceles if '2001-2022' in n]
                    archivo_objetivo = candidatos[0] if candidatos else None
                else:
                    vigentes = [n for n in exceles if '2001-2022' not in n]
                    if not vigentes:
                        vigentes = exceles
                    # Preferir el rango con año de cierre más alto (2023-2026, 2023-2027, ...)
                    def anio_cierre(nombre):
                        nums = re.findall(r'(\d{4})', os.path.basename(nombre))
                        return int(nums[-1]) if nums else 0
                    archivo_objetivo = max(vigentes, key=anio_cierre) if vigentes else None
                
                if not archivo_objetivo:
                    raise Exception(
                        f"No se encontró Excel de series históricas en el ZIP. Contenido: {contenidos}"
                    )
                
                logger.info(f"Archivo Excel detectado para extraer: {archivo_objetivo}")
                
                # Extraer el archivo seleccionado
                zf.extract(archivo_objetivo, self.carpeta_files)
                
                # Ruta donde quedó extraído
                ruta_extraida = os.path.join(self.carpeta_files, archivo_objetivo)
                
                # Si el archivo estaba dentro de una subcarpeta en el ZIP, hay que moverlo
                if not os.path.exists(ruta_extraida):
                    # Esto maneja casos donde el ZIP tiene carpetas internas
                    nombre_base = os.path.basename(archivo_objetivo)
                    ruta_extraida = os.path.join(self.carpeta_files, archivo_objetivo)

                # Renombrar/Mover al nombre final esperado por el resto del script
                if os.path.exists(ruta_extraida):
                    shutil.move(ruta_extraida, ruta_excel_final)
                    logger.info(f"[OK] Archivo renombrado a: {ruta_excel_final}")
                else:
                    raise Exception(f"No se pudo localizar el archivo extraído en: {ruta_extraida}")
                    
        except zipfile.BadZipFile as e:
            logger.error(f"Error: El archivo descargado no es un ZIP válido: {e}")
            raise

    def _limpiar_archivos_temporales(self, ruta_zip):
        """Limpia archivos temporales y directorios extraídos"""
        archivos_eliminados = 0
        espacio_liberado = 0
        
        try:
            # Eliminar ZIP temporal
            if os.path.exists(ruta_zip):
                size = os.path.getsize(ruta_zip)
                os.remove(ruta_zip)
                espacio_liberado += size
                archivos_eliminados += 1
                logger.info(f"[OK] ZIP temporal eliminado ({size/1024/1024:.1f}MB)")
            
            # Eliminar directorio de extracción temporal
            directorio_temporal = os.path.join(self.carpeta_files, "tablas de movimientos y pasajeros")
            if os.path.exists(directorio_temporal):
                for root, dirs, files in os.walk(directorio_temporal):
                    for file in files:
                        filepath = os.path.join(root, file)
                        if os.path.exists(filepath):
                            espacio_liberado += os.path.getsize(filepath)
                            archivos_eliminados += 1
                shutil.rmtree(directorio_temporal)
                logger.info(f"[OK] Directorio temporal eliminado")
            
            if archivos_eliminados > 0:
                logger.info(f"[OK] Limpieza completada: {archivos_eliminados} archivos, {espacio_liberado/1024/1024:.1f}MB liberados")
                
        except PermissionError:
            logger.warning("[WARNING] No se pudieron eliminar algunos archivos temporales (en uso)")
        except Exception as e:
            logger.warning(f"[WARNING] Advertencia limpiando temporales: {e}")

    def _verificar_espacio_disco(self):
        """Verifica espacio libre en disco"""
        try:
            stat = shutil.disk_usage(self.carpeta_files)
            espacio_libre_gb = stat.free / (1024**3)
            porcentaje_libre = (stat.free / stat.total) * 100
            
            logger.info(f"[DISCO] Espacio libre: {espacio_libre_gb:.1f}GB ({porcentaje_libre:.1f}%)")
            
            if espacio_libre_gb < 1.0 or porcentaje_libre < 10:
                logger.warning(f"[WARNING] ADVERTENCIA: Poco espacio en disco ({espacio_libre_gb:.1f}GB libre)")
                
        except Exception as e:
            logger.warning(f"[WARNING] No se pudo verificar espacio en disco: {e}")

