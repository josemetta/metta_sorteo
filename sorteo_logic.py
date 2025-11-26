import pandas as pd
import io
import random
import streamlit as st # solo para usar session_state; no pinta UI

# -------- Estado (en st.session_state) --------
def init_state():
    """Inicializa todas las variables de la sesión si no existen."""
    s = st.session_state
    s.setdefault("df", pd.DataFrame())
    s.setdefault("field1", "")
    s.setdefault("field2", "")
    s.setdefault("num_winners", 3) 
    # Lista de dicts: {"prize": n, "row": {...}, "original_index": int}
    s.setdefault("winners", [])
    s.setdefault("current_index", 0) 
    s.setdefault("candidate", None) 
    s.setdefault("rng_seed", None)
    s.setdefault("last_uploaded_file", None)

def reset_round():
    """Limpia el candidato actual para permitir un nuevo sorteo."""
    st.session_state.candidate = None

# -------- Utilidades puras --------
def remaining_participants(df: pd.DataFrame, winners: list) -> pd.DataFrame:
    """
    Devuelve los participantes no confirmados aún, basándose en el índice 
    original de la fila almacenado en la lista de ganadores.
    """
    if df.empty:
        return df
        
    # Obtener una lista de los índices originales de las filas ganadoras
    confirmed_indices = [w["original_index"] for w in winners]
    
    # Devolver el DataFrame excluyendo esos índices
    return df.drop(confirmed_indices, errors='ignore')

def export_winners_xlsx(winners: list, field1: str, field2: str) -> io.BytesIO | None:
    """Convierte la lista de ganadores en un XLSX (Premio #1 primero)."""
    if not winners:
        return None
        
    # Ordenar por el número de premio
    w_sorted = sorted(winners, key=lambda x: x["prize"])
    rows = []
    
    for w in w_sorted:
        row = {
            "Premio": f"Premio #{w['prize']}",
            field1: w["row"].get(field1, ""),
            field2: w["row"].get(field2, "")
        }
        rows.append(row)
    dfw = pd.DataFrame(rows)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        dfw.to_excel(writer, index=False, sheet_name="Ganadores")
    buf.seek(0)
    return buf.getvalue() # Devuelve el valor binario del buffer

def pick_candidate(df_left: pd.DataFrame, total: int, current_index: int, rng_seed: int | None):
    """Devuelve (candidate_data_dict, prize_value) para el siguiente premio."""
    if df_left.empty:
        return None, None
        
    # 1. Configurar y usar la semilla
    rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
    
    # 2. Seleccionar el índice aleatorio (basado en el índice *interno* del df_left)
    idx_in_left = rng.randrange(len(df_left))
    
    # 3. Obtener la fila (dict) y el índice original (crucial para tracking)
    row_series = df_left.iloc[idx_in_left]
    row = row_series.to_dict()
    original_index = row_series.name # Obtiene el índice de la fila original en el df completo
    
    # 4. Determinar el número de premio (siempre es el siguiente)
    prize_value = current_index + 1
    
    # 5. Estructura de datos del candidato
    candidate_data = {
        "row": row,
        "prize": prize_value,
        "original_index": original_index # <-- Campo crucial para remaining_participants
    }
    
    # Retorna el diccionario completo de datos del candidato y el valor del premio
    return candidate_data, prize_value

# -------- Carga y normalización de datos --------
def load_excel_3cols(file) -> pd.DataFrame:
    """
    Lee Excel, normaliza columnas, toma solo 3 primeras,
    elimina filas totalmente vacías.
    """
    df = pd.read_excel(file)
    df = df.dropna(how="all")
    df.columns = [str(c).strip() for c in df.columns]
    if df.shape[1] < 3:
        raise ValueError("El Excel debe tener al menos 3 columnas.")
        
    # Aseguramos que el índice original se mantenga para el tracking
    df_clean = df.iloc[:, :3].copy()
    
    return df_clean