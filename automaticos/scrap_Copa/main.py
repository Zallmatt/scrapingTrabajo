import os
import sys
import re
from etl.extract import extract_ron_file, download_file
from etl.transform import main as transform_main
from etl.load import load_to_postgres

def extract_date_from_url(url):
    import requests
    from bs4 import BeautifulSoup
    import datetime

    url_lower = url.lower()
    month_map = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
    }
    
    # Pattern 1: internet_diario_?([a-z]+)_?(\d{2,4})
    # Handles: internet_diario_abr26, internet_diario_abril26, internet_diarioabril26, internet_diario_abril_26, internet_diario_abril_2026
    match = re.search(r'internet_diario_?([a-z]+)_?(\d{2,4})', url_lower)
    if match:
        month_str = match.group(1)[:3]
        year_val = int(match.group(2))
        if year_val < 100: year_val += 2000
        month = month_map.get(month_str)
        if month:
            return year_val, month
            
    # Pattern 2: internet_diario_?(\d{2,4})
    # Handles: internet_diario26, internet_diario_26, internet_diario_2026
    match2 = re.search(r'internet_diario_?(\d{2,4})', url_lower)
    if match2:
        year_val = int(match2.group(1))
        if year_val < 100: year_val += 2000
        
        # If we have year but no month from URL, try to find month by scraping or searching elsewhere
        # Try to find abbreviation anywhere in the URL (not just after diario)
        for k, v in month_map.items():
            if k in url_lower:
                return year, v

        # Try to find the month by scraping the index page and finding the link text
        try:
            r = requests.get("https://www.argentina.gob.ar/economia/sechacienda/asuntosprovinciales/ron")
            soup = BeautifulSoup(r.content, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href'].replace('blank:#', '')
                if href in url or url.endswith(href):
                    t = a.text.strip().upper()
                    m_map = {k.upper(): v for k, v in month_map.items()}
                    if t in m_map:
                        return year_val, m_map[t]
        except Exception as e:
            print("Warning: Could not fetch page to deduce month:", e)
            
        # Fallback to current month if we couldn't find the link
        return year_val, datetime.datetime.now().month

    return None, None

def main():
    print("--- Starting RON ETL Process ---")
    
    # Configuration
    URL = "https://www.argentina.gob.ar/economia/sechacienda/asuntosprovinciales/ron"
    RAW_DIR = os.path.join("files", "raw")
    TARGET_PATH = os.path.join(RAW_DIR, "ron_raw.xls")
    PROCESSED_CSV = os.path.join("files", "processed", "consolidado_copa.csv")
    
    # Ensure directories exist
    os.makedirs(RAW_DIR, exist_ok=True)
    
    try:
        # 1. Extract
        print("[1/3] Extraction phase...")
        file_url, year, month = extract_ron_file(URL, include_date=True)
        
        if not file_url:
            print("Error: Could not find the download link on the page.")
            sys.exit(1)
            
        download_file(file_url, TARGET_PATH)
        print(f"Extraction successful: {TARGET_PATH}")
        
        # Respaldo para páginas antiguas cuyos enlaces no tengan metadatos visibles.
        if year is None or month is None:
            year, month = extract_date_from_url(file_url)
        
        # 2. Transform
        print(f"[2/3] Transformation phase (Year: {year}, Month: {month})...")
        transform_ok = transform_main(input_path=TARGET_PATH, year=year, month=month)
        if not transform_ok:
            raise RuntimeError("La transformación RON no generó datos para cargar.")
        
        # 3. Load
        print("[3/3] Load phase...")
        success = load_to_postgres(PROCESSED_CSV)
        
        if success:
            print("--- ETL Process Finished Successfully ---")
            # Cleanup: Remove files directory and its contents to avoid leaving residues on the server
            import shutil
            if os.path.exists("files"):
                print("Cleaning up temporary files...")
                shutil.rmtree("files")
                print("Cleanup complete.")
        else:
            print("--- ETL Process Finished with Load Errors ---")
            sys.exit(1)
            
    except Exception as e:
        print(f"An error occurred during the ETL process: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
