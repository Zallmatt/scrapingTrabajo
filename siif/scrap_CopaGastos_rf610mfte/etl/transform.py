import glob
import os
import re

import pandas as pd

CODIGO_FUENTE_DEFAULT = 10

# Layout observado en rf610mfte (desplazado vs rf610m).
COL_PROGRAMA = 5
COL_SUB_PROF = 8
COL_PY = 12
COL_A_OBRA = 15
COL_PARTID = 18
COL_SUB_PARTID = 13


def _get_code(val):
    try:
        text = str(val).strip()
        if not text or text == "nan":
            return None
        return int(re.search(r"\d+", text).group())
    except Exception:
        return None


def _detect_amount_headers(df):
    col_map = {}
    for r_idx in range(15, 25):
        if r_idx >= len(df):
            break
        row = df.iloc[r_idx]
        for c_idx, val in enumerate(row):
            val_str = str(val).strip().lower()
            if "credito original" in val_str:
                col_map["Cred Ori"] = c_idx
            elif "credito vigente" in val_str:
                col_map["Cred Vig"] = c_idx
            elif "comprometido" in val_str:
                col_map["Comprometido"] = c_idx
            elif "devengado" in val_str:
                col_map["Devengado"] = c_idx
    return col_map


def _extract_jurisdiccion(df):
    for r_idx in range(min(25, len(df))):
        row = df.iloc[r_idx]
        for c_idx, val in enumerate(row):
            if pd.isna(val):
                continue
            text = str(val)
            if "Entidad" not in text:
                continue
            match = re.search(r"(\d+)", text)
            if match and "Entidad" in text and len(text) > 12:
                return int(match.group(1))
            for nxt in row.iloc[c_idx + 1 :]:
                if pd.isna(nxt):
                    continue
                match = re.search(r"(\d+)", str(nxt))
                if match:
                    return int(match.group(1))
    return 0


def _extract_fuente(df, filename):
    match = re.search(r"_FTE(\d+)_", filename, re.I)
    if match:
        return int(match.group(1))
    for r_idx in range(min(25, len(df))):
        row_str = " ".join(str(v) for v in df.iloc[r_idx].values if pd.notna(v))
        found = re.search(r"Fuente Financiamiento:\s*(\d+)", row_str, re.I)
        if found:
            return int(found.group(1))
    return CODIGO_FUENTE_DEFAULT


def process_file(file_path):
    filename = os.path.basename(file_path)
    match = re.match(r"(\d{4})(\d{2})_", filename)
    if not match:
        return []
    anio, mes = int(match.group(1)), int(match.group(2))

    df = pd.read_excel(file_path, header=None)
    col_map = _detect_amount_headers(df)
    if not col_map:
        return []

    jurisdiccion = _extract_jurisdiccion(df)
    codigo_fuente = _extract_fuente(df, filename)
    programa = sub_prof = py = a_obra = partid = 0
    rows = []

    for _, row in df.iloc[25:].iterrows():
        p_val = _get_code(row[COL_PROGRAMA] if COL_PROGRAMA < len(row) else None)
        if p_val is not None:
            programa = p_val
        sp_val = _get_code(row[COL_SUB_PROF] if COL_SUB_PROF < len(row) else None)
        if sp_val is not None:
            sub_prof = sp_val
        py_val = _get_code(row[COL_PY] if COL_PY < len(row) else None)
        if py_val is not None:
            py = py_val
        ao_val = _get_code(row[COL_A_OBRA] if COL_A_OBRA < len(row) else None)
        if ao_val is not None:
            a_obra = ao_val
        part_val = _get_code(row[COL_PARTID] if COL_PARTID < len(row) else None)
        if part_val is not None:
            partid = part_val

        sub_part_val = _get_code(row[COL_SUB_PARTID] if COL_SUB_PARTID < len(row) else None)
        if sub_part_val is None or sub_part_val <= 10:
            continue

        for label, h_idx in col_map.items():
            offset = -2 if label in ("Comprometido", "Devengado") else -1
            d_idx = h_idx + offset
            if d_idx < 0 or d_idx >= len(row):
                continue
            val = pd.to_numeric(row[d_idx], errors="coerce")
            if pd.isna(val) or val == 0:
                continue
            rows.append(
                {
                    "mes": mes,
                    "anio": anio,
                    "jurisdiccion": jurisdiccion,
                    "codigo_fuente": codigo_fuente,
                    "programa": programa,
                    "sub_prof": sub_prof,
                    "py": py,
                    "a_obra": a_obra,
                    "partid": partid,
                    "sub_partid": sub_part_val,
                    "tipo_de_g": label,
                    "val": val,
                }
            )
    return rows


def transform_all_files():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_dir = os.path.join(base_dir, "files/raw")
    processed_dir = os.path.join(base_dir, "files/processed")
    os.makedirs(processed_dir, exist_ok=True)

    excel_files = glob.glob(os.path.join(raw_dir, "**/*.xls"), recursive=True)
    if not excel_files:
        print("No Excel files found.")
        return

    all_data = []
    ok = 0
    for file_path in excel_files:
        try:
            rows = process_file(file_path)
        except Exception as exc:
            print(f"  - Skip {os.path.basename(file_path)}: {exc}")
            continue
        if rows:
            all_data.extend(rows)
            ok += 1

    if not all_data:
        print("No data transformed. Check Excel structure.")
        return

    consolidated = pd.DataFrame(all_data)
    output_file = os.path.join(processed_dir, "consolidado_gastos.csv")
    consolidated.to_csv(output_file, index=False)
    print(f"Transformed {ok} files / {len(all_data)} rows into {output_file}")


if __name__ == "__main__":
    transform_all_files()
