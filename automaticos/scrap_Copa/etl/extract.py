import requests
from bs4 import BeautifulSoup
import os
import urllib.parse

MESES = {
    'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12,
}


def extract_ron_file(base_url, xpath_info=None, include_date=False):
    """
    Extrae el último archivo diario RON y, opcionalmente, su año y mes
    desde el texto y encabezado de la página. El nombre del XLS no siempre
    incluye la fecha (por ejemplo, septiembre 2026 es internet_diario4.xls).
    """
    print(f"Fetching page: {base_url}")
    response = requests.get(base_url, timeout=(30, 120))
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')

    for link in soup.find_all('a', href=True):
        etiqueta_mes = link.get_text(' ', strip=True).upper()[:3]
        href = link['href']
        if etiqueta_mes not in MESES or 'internet_diario' not in href.lower():
            continue

        encabezado_anio = link.find_previous(['h4', 'h5'])
        texto_anio = encabezado_anio.get_text(' ', strip=True) if encabezado_anio else ''
        year = int(texto_anio) if texto_anio.isdigit() and len(texto_anio) == 4 else None
        month = MESES[etiqueta_mes]

        if href.startswith('blank:#'):
            href = href.replace('blank:#', '', 1)
        full_url = urllib.parse.urljoin(base_url, href)
        print(f"Found latest RON: {etiqueta_mes} {year} -> {full_url}")
        return (full_url, year, month) if include_date else full_url

    return (None, None, None) if include_date else None

def download_file(url, target_path):
    print(f"Downloading: {url}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(target_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Saved to: {target_path}")

if __name__ == "__main__":
    URL = "https://www.argentina.gob.ar/economia/sechacienda/asuntosprovinciales/ron"
    # Create the directory if it doesn't exist
    os.makedirs("files/raw", exist_ok=True)
    
    file_url = extract_ron_file(URL, None)
    if file_url:
        target = os.path.join("files", "raw", "ron_raw.xls")
        download_file(file_url, target)
    else:
        print("Could not find the download link.")
