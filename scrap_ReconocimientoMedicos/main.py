import os
import sys
from loadDataBaseMedicos import LoadDataBaseMedicos


#Configuracion de la ruta de credenciales
# Obtiene la ruta absoluta al directorio donde reside el script actual.
script_dir = os.path.dirname(os.path.abspath(__file__))
# Crea una ruta al directorio 'Credenciales_folder' que se supone está un nivel arriba en la jerarquía de directorios.
credenciales_dir = os.path.join(script_dir, '..', 'Credenciales_folder')
# Agregar la ruta al sys.path
sys.path.append(credenciales_dir)

# Ahora puedes importar tus credenciales
from credenciales_bdd import Credenciales
# Después puedes crear una instancia de Credenciales
credenciales = Credenciales('reconocimientos_medicos')

if __name__ == "__main__":
    print("Las credenciales son", credenciales.host,credenciales.user,credenciales.password,credenciales.database)
    conexion = LoadDataBaseMedicos(credenciales.host, credenciales.user, credenciales.password, credenciales.database).conectar_bdd()
    df = conexion.loadDataBaseMedicos()
    print(df)
    