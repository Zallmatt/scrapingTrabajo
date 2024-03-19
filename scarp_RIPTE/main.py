from extract import HomePage
import os
import pandas as pd
from ripte_cargaHistorico import ripte_cargaHistorico
from ripte_cargaUltimoDato import ripte_cargaUltimoDato
import sys
import os

# Obtener la ruta al directorio actual del script
script_dir = os.path.dirname(os.path.abspath(__file__))
credenciales_dir = os.path.join(script_dir, '..', 'Credenciales_folder')
# Agregar la ruta al sys.path
sys.path.append(credenciales_dir)
# Ahora puedes importar tus credenciales
from credenciales_bdd import Credenciales
# Después puedes crear una instancia de Credenciales
credenciales_datalake_economico = Credenciales('datalake_economico')
credenciales_ipecd_economico = Credenciales('ipecd_economico')


#Instancia encargada 

if __name__ == '__main__':
    #Obtencion del archivo
    #home_page = HomePage()
    #home_page.descargar_archivo()
    #ripte_cargaHistorico().loadInDataBase(credenciales_datalake_economico.host, credenciales_datalake_economico.user, credenciales_datalake_economico.password, credenciales_datalake_economico.database)
    #↓↓↓↓↓↓↓↓↓↓↓↓CARGA DEL TABLERO ↓↓↓↓↓↓↓↓↓↓↓↓
    #ripte_cargaHistorico().loadInDataBase(credenciales_ipecd_economico.host, credenciales_ipecd_economico.user, credenciales_ipecd_economico.password, credenciales_ipecd_economico.database)

    ultimo_valor_ripte = HomePage().extract_last_date()
    print(ultimo_valor_ripte)
    instancia = ripte_cargaUltimoDato(credenciales_datalake_economico.host, credenciales_datalake_economico.user, credenciales_datalake_economico.password, credenciales_datalake_economico.database)
    instancia.loadInDataBaseDatalakeEconomico()

    #↓↓↓↓↓↓↓↓↓↓↓↓CARGA DEL TABLERO ↓↓↓↓↓↓↓↓↓↓↓↓
    instancia = ripte_cargaUltimoDato(credenciales_ipecd_economico.host, credenciales_ipecd_economico.user, credenciales_ipecd_economico.password, credenciales_ipecd_economico.database)
    instancia.loadInDataBaseIPECD_Economico()