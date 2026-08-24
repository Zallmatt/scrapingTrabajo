import os
import pandas as pd
import re
import glob

def transform_all_files():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAW_DIR = os.path.join(BASE_DIR, "files/raw")
    PROCESSED_DIR = os.path.join(BASE_DIR, "files/processed")
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    excel_files = glob.glob(os.path.join(RAW_DIR, "**/*.xls"), recursive=True)
    if not excel_files:
        print("No Excel files found.")
        return

    all_data = []

    for file_path in excel_files:
        filename = os.path.basename(file_path)
        match = re.match(r"(\d{4})(\d{2})_", filename)
        if not match: continue
        anio, mes = int(match.group(1)), int(match.group(2))

        try:
            # Note: xlrd is needed for .xls files
            df = pd.read_excel(file_path, header=None)
            
            # 1. Dynamic Header Detection (to handle potential variations)
            col_map = {}
            for r_idx in range(15, 25):
                if r_idx >= len(df): break
                row = df.iloc[r_idx]
                for c_idx, val in enumerate(row):
                    val_str = str(val).strip().lower()
                    if "credito original" in val_str: col_map["Cred Ori"] = c_idx
                    elif "credito vigente" in val_str: col_map["Cred Vig"] = c_idx
                    elif "comprometido" in val_str: col_map["Comprometido"] = c_idx
                    elif "devengado" in val_str: col_map["Devengado"] = c_idx

            if not col_map:
                continue

            # 2. Extract Jurisdiccion (Row 17, Col 12 usually)
            juris_val = df.iloc[17, 12] if len(df) > 17 else None
            try:
                jurisdiccion = int(str(juris_val).split()[0])
            except:
                jurisdiccion = 0

            # 3. Hierarchy Tracking
            programa, sub_prof, py, a_obra, partid = 0, 0, 0, 0, 0
            
            for idx, row in df.iloc[30:].iterrows():
                def get_code(val):
                    try:
                        s = str(val).strip()
                        if not s or s == "nan": return None
                        # Extract the first number found in strings like "1  ACTIVIDADES..."
                        return int(re.search(r'\d+', s).group())
                    except: return None

                # Hierarchy updates (using fixed indices found in debug)
                p_val = get_code(row[5])
                if p_val is not None: programa = p_val
                
                sp_val = get_code(row[7])
                if sp_val is not None: sub_prof = sp_val
                
                py_val = get_code(row[8]) # Found in Col 8 in debug
                if py_val is not None: py = py_val
                
                ao_val = get_code(row[11])
                if ao_val is not None: a_obra = ao_val
                
                part_val = get_code(row[13])
                if part_val is not None: partid = part_val
                
                # Data Row (Sub Partid is in Col 16)
                sub_part_val = get_code(row[16])
                if sub_part_val is not None and sub_part_val > 10: # Avoid false positives
                    sub_partid = sub_part_val
                    
                    # Extract values based on headers and offsets
                    for label, h_idx in col_map.items():
                        # Applied verified offsets: -1 for Ori/Vig, -2 for Comprometido
                        offset = -1
                        if "Comprometido" in label or "Devengado" in label:
                            offset = -2
                        
                        d_idx = h_idx + offset
                        if d_idx >= 0 and d_idx < len(row):
                            val = pd.to_numeric(row[d_idx], errors='coerce')
                            if not pd.isna(val) and val != 0:
                                # Standardize label for DB
                                db_label = label
                                if label == "Cred Vig": db_label = "Cred Vig"
                                elif label == "Cred Ori": db_label = "Cred Ori"
                                
                                all_data.append({
                                    "mes": mes, "anio": anio, "jurisdiccion": jurisdiccion,
                                    "programa": programa, "sub_prof": sub_prof, "py": py, "a_obra": a_obra,
                                    "partid": partid, "sub_partid": sub_partid,
                                    "tipo_de_g": db_label, "val": val
                                })

        except Exception as e:
            pass # Skip corrupted files

    if all_data:
        consolidated_df = pd.DataFrame(all_data)
        output_file = os.path.join(PROCESSED_DIR, "consolidado_gastos.csv")
        consolidated_df.to_csv(output_file, index=False)
        print(f"Transformed {len(all_data)} rows into {output_file}")
    else:
        print("No data transformed. Check Excel structure.")

if __name__ == "__main__":
    transform_all_files()
