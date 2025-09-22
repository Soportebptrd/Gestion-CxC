import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from datetime import datetime

# ======================================
# Configuración de la app
# ======================================
st.set_page_config(page_title="📞 Seguimiento de Clientes - CxC", layout="wide")

# ======================================
# Login seguro
# ======================================
st.title("🔒 Iniciar sesión")

username = st.text_input("Usuario")
password = st.text_input("Contraseña", type="password")

if username in st.secrets["APP_USERS"] and password == st.secrets["APP_USERS"][username]:
    st.success(f"Conectado como: {username}")
else:
    if username or password:
        st.error("Usuario o contraseña incorrectos")
    st.stop()

# ======================================
# Conexión a Google Sheets
# ======================================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = dict(st.secrets["GOOGLE_SHEET"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# IDs de tus hojas
SHEET_ID = "1z-BExCxP_rNEz-Ee0Xot6XwInlBfQ5icSgyxmu7mGMY"
SHEET1_NAME = "Sheet1"
BASE_CLIENTES = "BaseClientes"

# ======================================
# Carga de datos
# ======================================
sheet_respuestas = client.open_by_key(SHEET_ID).worksheet(SHEET1_NAME)
data_respuestas = sheet_respuestas.get_all_records()
df_respuestas = pd.DataFrame(data_respuestas)

sheet_clientes = client.open_by_key(SHEET_ID).worksheet(BASE_CLIENTES)
data_clientes = sheet_clientes.get_all_records()
df_clientes = pd.DataFrame(data_clientes)

# Ajuste de nombres de columnas
df_respuestas.columns = [col.strip().lower().replace(" ", "_") for col in df_respuestas.columns]
df_clientes.columns = [col.strip().lower().replace(" ", "_") for col in df_clientes.columns]

# Merge para agregar nombre del cliente
df_final = df_respuestas.merge(df_clientes, on="codigo_del_cliente", how="left")

# ======================================
# Filtros de fecha
# ======================================
st.sidebar.header("Filtrar por fecha")
fecha_inicio = st.sidebar.date_input("Fecha inicio", value=datetime.today())
fecha_fin = st.sidebar.date_input("Fecha fin", value=datetime.today())

df_final["marca_temporal"] = pd.to_datetime(df_final["marca_temporal"])
mask = (df_final["marca_temporal"] >= pd.to_datetime(fecha_inicio)) & (df_final["marca_temporal"] <= pd.to_datetime(fecha_fin))
df_filtrado = df_final.loc[mask].copy()

# ======================================
# Reordenar columnas
# ======================================
df_filtrado = df_filtrado[[
    "marca_temporal",
    "codigo_del_cliente",
    "nombre_cliente",
    "llamado",
    "monto",
    "notas",
    "usuario"
]]

# ======================================
# Colorear tabla
# ======================================
def color_llamado(val):
    if str(val).strip().lower() == "si":
        return 'background-color: #b6d7a8'  # verde
    else:
        return 'background-color: #f4cccc'  # rojo

styled_df = df_filtrado.style.applymap(color_llamado, subset=["llamado"])

# ======================================
# Mostrar tabla
# ======================================
st.subheader("📋 Seguimiento de clientes")
st.dataframe(styled_df, height=900, width="stretch")

# ======================================
# Exportar PDF
# ======================================
def export_pdf(df):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Título
    pdf.cell(0, 10, f"Seguimiento de Clientes - {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(5)
    
    # Tabla
    col_widths = [35, 35, 50, 20, 25, 50, 25]
    headers = df.columns.tolist()
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 8, str(header), 1, 0, "C")
    pdf.ln()
    
    for _, row in df.iterrows():
        for i, col in enumerate(headers):
            pdf.cell(col_widths[i], 8, str(row[col]), 1, 0, "C")
        pdf.ln()
    
    return pdf

if st.button("📄 Exportar PDF"):
    pdf_file = export_pdf(df_filtrado)
    pdf_output = f"SeguimientoClientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_file.output(pdf_output)
    with open(pdf_output, "rb") as f:
        st.download_button("Descargar PDF", data=f, file_name=pdf_output, mime="application/pdf")
