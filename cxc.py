import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from fpdf import FPDF

# ==========================
# CONFIGURACIÓN GOOGLE SHEET
# ==========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

# Credenciales desde Streamlit Secrets
creds_dict = json.loads(st.secrets["GOOGLE_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)

# IDs de las hojas
SHEET_KEY = "1z-BExCxP_rNEz-Ee0Xot6XwInlBfQ5icSgyxmu7mGMY"

sheet_respuestas = client.open_by_key(SHEET_KEY).worksheet("Sheet1")
sheet_clientes = client.open_by_key(SHEET_KEY).worksheet("BaseClientes")

# ==========================
# CARGA DE DATOS
# ==========================
df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

# Limpieza de nombres de columnas
df_respuestas.columns = df_respuestas.columns.str.strip().str.lower().str.replace(" ", "_")
df_clientes.columns = df_clientes.columns.str.strip().str.lower().str.replace(" ", "_")

# Merge para agregar nombre del cliente
df_final = df_respuestas.merge(df_clientes, on="codigo_del_cliente", how="left")

# Conversión de fecha
df_final["marca_temporal"] = pd.to_datetime(df_final["marca_temporal"], dayfirst=True)

# ==========================
# STREAMLIT INTERFAZ
# ==========================
st.title("📞 Seguimiento de Clientes - CxC")

# Rango de fechas
fecha_inicio = st.date_input("Fecha inicio:", datetime(2025, 9, 1))
fecha_fin = st.date_input("Fecha fin:", datetime(2025, 9, 21))

df_filtrado = df_final[(df_final["marca_temporal"].dt.date >= fecha_inicio) &
                       (df_final["marca_temporal"].dt.date <= fecha_fin)]

# ==========================
# FUNCIONES DE ESTILO
# ==========================
def style_llamado(val):
    if val.lower() == "si":
        color = "green"
    else:
        color = "red"
    return f"color: {color}; font-weight: bold"

# Reordenar columnas
df_filtrado = df_filtrado[
    ["marca_temporal", "codigo_del_cliente", "nombre_cliente", "llamado", "monto", "notas", "usuario"]
]

styled_df = df_filtrado.style.applymap(style_llamado, subset=["llamado"])

# Mostrar tabla grande y estilizada
st.dataframe(styled_df, height=900, width="stretch")

# ==========================
# EXPORTAR A PDF
# ==========================
def export_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Reporte de Seguimiento de Clientes CxC ({fecha_inicio} - {fecha_fin})", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 10)
    col_widths = [30, 30, 50, 20, 20, 40, 30]  # ajustar anchos
    
    # Encabezado
    for i, col in enumerate(df.columns):
        pdf.cell(col_widths[i], 8, col, 1, 0, "C")
    pdf.ln()
    
    # Filas
    for idx, row in df.iterrows():
        for i, col in enumerate(df.columns):
            pdf.cell(col_widths[i], 8, str(row[col]), 1, 0, "C")
        pdf.ln()
    
    return pdf

if st.button("📄 Exportar PDF"):
    pdf_file = export_pdf(df_filtrado)
    pdf_output = f"reporte_cxc_{fecha_inicio}_{fecha_fin}.pdf"
    pdf_file.output(pdf_output)
    with open(pdf_output, "rb") as f:
        st.download_button("Descargar PDF", f, file_name=pdf_output, mime="application/pdf")
