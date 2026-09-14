import os
import pandas as pd
import re
import warnings

# Suppress warnings
warnings.simplefilter(action='ignore', category=UserWarning)

# Configuration
# Configuration (These can be overridden by main.py)
RAW_FILE = os.path.join('files', 'raw', 'ron_raw.xls')
OUTPUT_DIR = os.path.join('files', 'processed')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'consolidado_copa.csv')

# Indices of columns to keep (0-based) based on file inspection
# 0-9: Date + 9 data cols
# 13-22: 10 data cols
# 24: 1 data col
# 28: 1 data col
KEEP_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 28]

TARGET_COLUMNS = [
    "Fecha",
    "CFI (Neta de Ley 26075)",
    "Financ. Educativo (Ley 26075)",
    "SUBTOTAL",
    "Transferencia de Servicios - Educacion",
    "Transferencia de Servicios - Posoco",
    "Transferencia de Servicios - Prosonu",
    "Transferencia de Servicios - Hospitales",
    "Transferencia de Servicios - Minoridad",
    "Transferencia de Servicios - TOTAL",
    "Imp. Bienes Personales (Ley 24.699)",
    "Imp. Bienes Personales (Ley 23.966 Art. 30)",
    "Imp. s/ los Activos Fdo. Educativo (Ley 23.906)",
    "I.V.A. (Ley 23.966 Art. 5 Pto. 2)",
    "Imp. Combustibles (Ley N.23966 Obras de Infraestructura)",
    "Imp. Combustibles (Ley N.23966 Vialidad Provincial)",
    "Imp. Combustibles (FO.NA.VI.)",
    "Fondo Compensador Deseq.Fisc. Provinciales",
    "Reg.Simplif. p/Pequenos Contribuyentes (Ley N.24.977)",
    "TOTAL Recursos Origen Nacional (1)",
    "Compensacion Consenso Fiscal (2)",
    "Total - (1)+(2)",
    "Punto Estadistico"
]

MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
    'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def parse_date_from_filename(filename, year_hint=None):
    """
    Tries to extract month and year from filename.
    """
    filename_lower = filename.lower()
    month_map = {
        'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
    }
    
    # Try Month + Year
    match = re.search(r'_?([a-z]+)_?(\d{2})', filename_lower)
    if match:
        month_str = match.group(1)[:3]
        year_short = match.group(2)
        month = month_map.get(month_str)
        if month:
            return 2000 + int(year_short), month
            
    # Try only Year
    match2 = re.search(r'_?(\d{2})', filename_lower)
    if match2:
        year = 2000 + int(match2.group(1))
        # Search for month abbreviation anywhere
        for k, v in month_map.items():
            if k in filename_lower:
                return year, v
        return year, None

    return year_hint, None

def process_file(filepath, year=None, month=None):
    try:
        if year is None or month is None:
            # Try to infer if not provided
            year, month = parse_date_from_filename(filepath, year_hint=year)
            
        if year is None or month is None:
            print(f"Error: Could not determine date for {filepath}")
            return None
            
        # Read Excel, sheet 'w', no header
        df = pd.read_excel(filepath, sheet_name='w', header=None, engine='xlrd')
        
        # Filter rows where Column A is numeric
        df[0] = pd.to_numeric(df[0], errors='coerce')
        df = df[df[0].notna()].copy()
        
        # Select specific columns BY INDEX
        # Check if file has enough columns
        max_idx = max(KEEP_INDICES)
        if len(df.columns) <= max_idx:
            print(f"Skipping {filepath}: Not enough columns ({len(df.columns)})")
            return None
            
        df = df.iloc[:, KEEP_INDICES].copy()
        
        # Assign Names immediately
        if len(df.columns) == len(TARGET_COLUMNS) - 1:
            df.columns = TARGET_COLUMNS[:-1]
        else:
            print(f"Error: Selected {len(df.columns)} columns, expected {len(TARGET_COLUMNS)-1}")
            return None

        # Extract Day
        day = df['Fecha'].astype(int)
        
        # Extract Punto Estadistico
        if year >= 2024:
            try:
                df_stats_raw = pd.read_excel(filepath, sheet_name='Punto I.c Ley 27429', header=None, engine='xlrd')
                df_stats_raw[0] = pd.to_numeric(df_stats_raw[0], errors='coerce')
                df_stats_raw = df_stats_raw[df_stats_raw[0].notna()].copy()
                if len(df_stats_raw.columns) > 3:
                    stats_map = dict(zip(df_stats_raw[0].astype(int), df_stats_raw[3]))
                    df['Punto Estadistico'] = day.map(stats_map).fillna(0.0)
                else:
                    df['Punto Estadistico'] = 0.0
            except Exception as e:
                print(f"Warning: Could not read 'Punto I.c Ley 27429' in {filepath}: {e}")
                df['Punto Estadistico'] = 0.0
        else:
            df['Punto Estadistico'] = 0.0
            
        # Construct Date
        dates = pd.to_datetime(
            dict(year=year, month=month, day=day),
            errors='coerce'
        )
        
        # Remove invalid dates
        valid_date_mask = dates.notna()
        df = df[valid_date_mask]
        dates = dates[valid_date_mask]
        
        # Format Date
        df['Fecha'] = dates.dt.strftime('%d/%m/%Y')
        
        # Process Values (Multiply by 1M)
        def clean_currency(x):
            if isinstance(x, str):
                x = x.replace('.', '').replace(',', '.')
            try:
                return float(x)
            except:
                return 0.0

        multiplier = 1_000 if year <= 2023 else 1_000_000
        for col in TARGET_COLUMNS[1:]: # Skip Fecha
            df[col] = df[col].apply(clean_currency) * multiplier
            
        return df
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return None

def main(input_path=None, year=None, month=None):
    all_dfs = []
    
    target_file = input_path if input_path else RAW_FILE
    
    if not os.path.exists(target_file):
        print(f"Error: File not found at {target_file}")
        return False

    print(f"Processing file: {target_file} (Year: {year}, Month: {month})")
    df = process_file(target_file, year=year, month=month)
    
    if df is not None and not df.empty:
        all_dfs.append(df)
                    
    if not all_dfs:
        print("No data processed.")
        return False

    print(f"Consolidating results...")
    consolidated = pd.concat(all_dfs, ignore_index=True)
    
    # Sort by Date
    consolidated['_dt'] = pd.to_datetime(consolidated['Fecha'], format='%d/%m/%Y')
    consolidated = consolidated.sort_values('_dt')
    consolidated.drop(columns=['_dt'], inplace=True)

    # sum check
    cols_to_drop = []
    for col in TARGET_COLUMNS[1:]:
        if col in consolidated.columns and consolidated[col].sum() == 0:
            cols_to_drop.append(col)
            
    if cols_to_drop:
        print(f"Dropping {len(cols_to_drop)} zero-sum columns")
        consolidated.drop(columns=cols_to_drop, inplace=True)
    
    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    consolidated.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved to {OUTPUT_FILE}")
    print(f"Final Shape: {consolidated.shape}")
    return True

if __name__ == "__main__":
    # If run directly, use defaults
    main()
