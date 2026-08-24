"""Copa Gastos rf604m via SIIF. Solo corre en la red local autorizada (login.jspx)."""
import os
import sys
from etl.extract import login_and_extract
from etl.transform import transform_all_files
from etl.load import load_to_db

def main():
    print("--- Starting Copa Gastos rf604m ETL Process ---")
    
    # Configuration
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RAW_DIR = os.path.join(BASE_DIR, "files/raw")
    PROCESSED_DIR = os.path.join(BASE_DIR, "files/processed")
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    RAW_FILE = os.path.join(RAW_DIR, "raw_data.xls")
    PROCESSED_FILE = os.path.join(PROCESSED_DIR, "processed_data.csv")
    
    try:
        # 1. Extract
        print("[1/3] Extraction phase...")
        driver = login_and_extract()
        
        # Keep driver open for inspection if needed, or close it
        # driver.quit()
        
        # 2. Transform
        print("[2/3] Transformation phase...")
        transform_all_files()
        
        # 3. Load
        print("[3/3] Load phase...")
        load_to_db()
        
        print("--- ETL Process Finished ---")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
