from homePage_CBT import HomePageCBT
from homePage_Pobreza import HomePagePobreza

#Datos de la base de datos
host = '192.168.0.101'
user = 'Ivan'
password = 'Estadistica123'
database = 'prueba1'

if __name__ == '__main__':
    home_page_CBT = HomePageCBT()
    home_page_CBT.descargar_archivo()
    
    home_page_Pobreza= HomePagePobreza()
    home_page_Pobreza.descargar_archivo()
    