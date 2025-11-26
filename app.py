import streamlit as st
import pandas as pd
from sorteo_logic import (
    init_state, reset_round, remaining_participants,
    export_winners_xlsx, pick_candidate, load_excel_3cols
)

# --- Configuración Inicial ---
st.set_page_config(page_title="Sorteo Mettatec", page_icon="🎉", layout="centered")
init_state()
s = st.session_state

st.title("🎉 Sorteo Digital – Mettatec")
st.caption("Sube un archivo Excel de *3 columnas* (por ejemplo: ID, Nombre, Email).")

# ----------------------------------
# ===== 1) Entrada de datos =====
# ----------------------------------
up = st.file_uploader("Archivo Excel (.xlsx)", type=["xlsx"])
colA, colB = st.columns(2)
with colA:
    seed_opt = st.toggle("Usar semilla (reproducible)", value=False)
with colB:
    s.rng_seed = st.number_input("Semilla", min_value=0, value=0, step=1) if seed_opt else None

if up is not None:
    try:
        # Solo cargar si el archivo es diferente al último cargado para evitar bucles
        if up != s.get('last_uploaded_file'):
            df = load_excel_3cols(up)
            s.df = df
            s.last_uploaded_file = up # Guardar referencia al archivo cargado

            # Reiniciar sorteo si se sube un archivo nuevo
            s.winners, s.current_index, s.candidate = [], 0, None
            
            # Campos por defecto (2da y 3ra col, ya aseguradas por load_excel_3cols)
            s.field1 = s.df.columns[1] if len(s.df.columns) > 1 else s.df.columns[0]
            s.field2 = s.df.columns[2] if len(s.df.columns) > 2 else s.df.columns[0]
            st.success(f"Datos cargados: {s.df.shape[0]} participantes, {s.df.shape[1]} columnas.")
            st.rerun() # Forzar re-ejecución para limpiar el uploader
    except Exception as e:
        st.error(f"No se pudo leer el archivo: {e}")

if s.df.empty:
    st.info("Aún no hay datos. Carga un Excel para continuar.")
    st.stop()

st.divider()

# ----------------------------------
# ===== 2) Configuración =====
# ----------------------------------
st.subheader("Configuración")
c1, c2, c3 = st.columns([1,1,1])
with c1:
    # Usamos la columna por defecto establecida al cargar
    default_index_f1 = s.df.columns.tolist().index(s.field1) if s.field1 in s.df.columns else 1 if len(s.df.columns)>1 else 0
    s.field1 = st.selectbox("Campo 1 (principal)", s.df.columns.tolist(), index=default_index_f1)
with c2:
    # Usamos la columna por defecto establecida al cargar
    default_index_f2 = s.df.columns.tolist().index(s.field2) if s.field2 in s.df.columns else 2 if len(s.df.columns)>2 else 0
    s.field2 = st.selectbox("Campo 2 (detalle)", s.df.columns.tolist(), index=default_index_f2)
with c3:
    s.num_winners = st.number_input("Cantidad de premios", min_value=1, max_value=len(s.df), 
                                    value=int(s.num_winners), step=1)

st.caption(f"Participantes cargados: *{len(s.df)}*")

# ----------------------------------
# ===== 3) Estado del sorteo =====
# ----------------------------------
st.subheader("Sorteo")
st.write(f"Ganadores confirmados: *{s.current_index} / {s.num_winners}*")


if s.candidate is not None:
    # --- MODO: CANDIDATO EN ESPERA DE CONFIRMACIÓN ---
    cand_data, prize_val = s.candidate # cand_data es el dict completo: {'row':{...}, 'prize':x, 'original_index':y}
    cand_row = cand_data['row'] 
    
    st.success(f"🎯 Candidato para *Premio #{prize_val}*")
    
    # Muestra los campos seleccionados en Configuración
    st.markdown(f"**{s.field1}:** `{cand_row.get(s.field1,'')}`")
    st.markdown(f"**{s.field2}:** `{cand_row.get(s.field2,'')}`")
    
    cA, cB = st.columns(2)
    with cA:
        if st.button("✅ Confirmar ganador"):
            # Almacenar el diccionario de datos del candidato completo
            s.winners.append(cand_data) 
            s.current_index += 1
            s.candidate = None
            st.rerun() 
    with cB:
        if st.button("🔄 Volver a sortear"):
            reset_round() # Pone s.candidate = None
            st.rerun() 
else:
    # --- MODO: LISTO PARA SORTEAR ---
    if s.current_index >= s.num_winners:
        st.info("¡Sorteo completo! Revisa la lista de ganadores abajo.")
    else:
        left = remaining_participants(s.df, s.winners)
        if left.empty:
            st.warning("No quedan participantes disponibles.")
        else:
            if st.button("🎲 ¡Sortear siguiente!"): 
                cand_data, prize_val = pick_candidate(left, s.num_winners, s.current_index, s.rng_seed)
                if cand_data is None:
                    st.warning("No se pudo seleccionar un candidato.")
                else:
                    # Almacenar el resultado de pick_candidate (datos y valor del premio)
                    s.candidate = (cand_data, prize_val) 
                    st.rerun() 

st.divider()

# ----------------------------------------------------
# ===== 4) Lista de ganadores y exportación =====
# ----------------------------------------------------
st.subheader("Lista de ganadores")
if not s.winners:
    st.info("Aún no hay ganadores confirmados.")
else:
    winners_sorted = sorted(s.winners, key=lambda x: x["prize"]) 
    out_rows = []
    
    # Reconstruir la tabla de ganadores
    for w in winners_sorted:
        out_rows.append({
            "Premio": f"Premio #{w['prize']}",
            s.field1: w["row"].get(s.field1, ""),
            s.field2: w["row"].get(s.field2, ""),
        })
    dfw = pd.DataFrame(out_rows)
    st.dataframe(dfw, use_container_width=True, hide_index=True)

    xls_bytes = export_winners_xlsx(s.winners, s.field1, s.field2)
    if xls_bytes:
        st.download_button(
            "⬇️ Exportar a Excel",
            data=xls_bytes,
            file_name="GANADORES.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ----------------------------------
# ===== 5) Controles de Limpieza =====
# ----------------------------------
st.divider()
cR1, cR2 = st.columns(2)
with cR1:
    if st.button("🔁 Reiniciar sorteo (mantener datos)"):
        s.winners, s.current_index, s.candidate = [], 0, None
        st.rerun()
with cR2:
    if st.button("🧹 Limpiar todo"):
        # Limpia todas las variables de sesión, incluyendo los datos cargados
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()