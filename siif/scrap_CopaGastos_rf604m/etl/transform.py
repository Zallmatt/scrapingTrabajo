import os
import pandas as pd
import re
import glob

class TransformRF604M:
    def __init__(self):
        self.month_map = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }

    def parse_periodo(self, filename):
        """Extracts the period from the filename (e.g., 202501_Entity.xls)."""
        filename_lower = filename.lower()
        
        # 1. Format YYYYMM_Entity.xls (Standard in automated scripts)
        match_auto = re.search(r'^(\d{4})(\d{2})_', filename_lower)
        if match_auto:
            year = match_auto.group(1)
            month = int(match_auto.group(2))
            if 1 <= month <= 12:
                return f"{year}-{month:02d}-01"

        # 2. Support for MMYYYY.xls (e.g., 012025.xls)
        match_numeric = re.search(r'^(\d{2})(\d{4})\.xls', filename_lower)
        if match_numeric:
            month = int(match_numeric.group(1))
            year = match_numeric.group(2)
            if 1 <= month <= 12:
                return f"{year}-{month:02d}-01"

        # 3. Search for month and year with hyphen (e.g., rf604m-ene25.xls)
        match = re.search(r'-([a-z]+)(\d{2})', filename_lower)
        if match:
            month_str = match.group(1)
            year_short = match.group(2)
            month = self.month_map.get(month_str)
            if month:
                return f"20{year_short}-{month:02d}-01"
        
        return None

    def clean_monto(self, val):
        """Cleans and converts Excel values to float."""
        if pd.isna(val):
            return 0.0
        try:
            return float(val)
        except:
            return 0.0

    def process_file(self, file_path):
        """Processes an Excel file and returns a DataFrame with the DB format."""
        filename = os.path.basename(file_path)
        periodo = self.parse_periodo(filename)
        if not periodo:
            # print(f"Could not determine period for {filename}")
            return None

        try:
            # xlrd is needed for .xls files
            xl = pd.ExcelFile(file_path, engine='xlrd')
            df = xl.parse(xl.sheet_names[0], header=None)
        except Exception as e:
            # print(f"Error reading {filename}: {e}")
            return None

        records = []
        current_jurisdiccion = None
        current_tipo_financ = None

        partidas_interes = [
            'GASTOS EN PERSONAL', 'BIENES DE CONSUMO', 'SERVICIOS NO PERSONALES',
            'BIENES DE USO', 'TRANSFERENCIAS', 'ACTIVOS FINANCIEROS',
            'SERVICIO DE LA DEUDA Y DISMINUCION DE OTROS', 'GASTOS FIGURATIVOS', 'OTROS GASTOS'
        ]

        # Column mapping for amounts (from rf604m inspection)
        col_vigente = 25
        col_comprometido = 28
        col_ordenado = 32

        for _, row in df.iterrows():
            row_str = " ".join(str(val) for val in row.values if pd.notna(val))
            
            # 1. Look for Jurisdiccion
            if "Entidad:" in row_str:
                match = re.search(r'Entidad:\s+\d+\s+-\s+(.+)', row_str)
                if match:
                    current_jurisdiccion = match.group(1).strip()
                continue

            # 2. Look for Tipo Financiamiento (Fuente)
            if "Codigo Fuente:" in row_str:
                match = re.search(r'Codigo Fuente:\s+(\d+)', row_str)
                if match:
                    current_tipo_financ = int(match.group(1))
                continue

            # 3. Look for Partidas and Amounts
            for partida in partidas_interes:
                # Partida is usually in col 11
                if len(row) > 11 and pd.notna(row[11]) and partida in str(row[11]):
                    if not current_jurisdiccion or current_tipo_financ is None:
                        continue

                    v_vigente = self.clean_monto(row[col_vigente])
                    v_comprometido = self.clean_monto(row[col_comprometido])
                    v_ordenado = self.clean_monto(row[col_ordenado])

                    estados = {
                        "Credito Vigente": v_vigente,
                        "Comprometido": v_comprometido,
                        "Ordenado": v_ordenado
                    }

                    for estado, monto in estados.items():
                        if monto != 0:
                            records.append({
                                "periodo": periodo,
                                "jurisdiccion": current_jurisdiccion,
                                "tipo_financ": current_tipo_financ,
                                "partida": partida,
                                "estado": estado,
                                "monto": monto
                            })
                    break 

        return pd.DataFrame(records)

def transform_all_files():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAW_DIR = os.path.join(BASE_DIR, "files/raw")
    PROCESSED_DIR = os.path.join(BASE_DIR, "files/processed")
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    excel_files = glob.glob(os.path.join(RAW_DIR, "**/*.xls"), recursive=True)
    if not excel_files:
        print("No Excel files found.")
        return

    transformer = TransformRF604M()
    all_dfs = []

    for file_path in excel_files:
        df = transformer.process_file(file_path)
        if df is not None and not df.empty:
            all_dfs.append(df)

    if all_dfs:
        consolidated_df = pd.concat(all_dfs, ignore_index=True)
        output_file = os.path.join(PROCESSED_DIR, "consolidado_gastos.csv")
        consolidated_df.to_csv(output_file, index=False)
        print(f"Transformed {len(all_dfs)} files into {output_file}")
    else:
        print("No data transformed. Check Excel structure.")

if __name__ == "__main__":
    transform_all_files()
