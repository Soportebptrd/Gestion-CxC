import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
from fpdf import FPDF

# -------------------------------
# LOGIN
# -------------------------------
st.title("📞 Seguimiento de Clientes - CxC")

usuario_input = st.text_input("Usuario")
contrasena_input = st.text_input("Contraseña", type="password")

if usuario_input != st.secrets["login"]["usuario"] or contrasena_input != st.secrets["login"]["contrasena"]:
    st.warning("Usuario o contraseña incorrectos")
    st.stop()

st.success(f"Bienvenido {usuario_input}")

# -------------------------------
# GOOGLE SHEETS
# -------------------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheet"]
# Aseguramos saltos de línea reales
creds_dict["private_key"] = creds_dict["private_key"].replace('\\n', '\n')

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# URL de la hoja de respuestas y clientes
SHEET_URL = "TU_URL_DE_GOOGLE_SHEET"  # <- reemplazar con tu URL

sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("Sheet1")
sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")

# Cargar datos
df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

# Normalizar columnas
df_respuestas.columns = [c.lower().replace(" ", "_") for c in df_respuestas.columns]
df_clientes.columns = [c.lower().replace(" ", "_") for c in df_clientes.columns]

# Merge para obtener nombre de cliente
df_final = df_respuestas.merge(df_clientes, left_on="código_del_cliente", right_on="código_del_cliente", how="left")

# -------------------------------
# FILTRO DE FECHA
# -------------------------------
df_final['marca_temporal'] = pd.to_datetime(df_final['marca_temporal'])
fecha_inicio = st.date_input("Fecha inicio", pd.to_datetime("2025-09-01"))
fecha_fin = st.date_input("Fecha fin", pd.to_datetime("2025-09-21"))

df_final = df_final[(df_final['marca_temporal'] >= pd.to_datetime(fecha_inicio)) &
                    (df_final['marca_temporal'] <= pd.to_datetime(fecha_fin))]

# -------------------------------
# TABLA
# -------------------------------
# Reordenar columnas
cols_order = ["marca_temporal", "código_del_cliente", "nombre_cliente", "llamado", "monto", "notas", "usuario"]
df_final = df_final[cols_order]

# Colorear llamado
def highlight_llamado(val):
    color = 'background-color: green' if str(val).lower() == 'si' else 'background-color: red'
    return color

styled_df = df_final.style.applymap(highlight_llamado, subset=['llamado'])

st.dataframe(styled_df, height=900, width='stretch')

# -------------------------------
# EXPORTAR PDF
# -------------------------------
def export_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Agregar encabezado
    for col in df.columns:
        pdf.cell(40, 10, col, 1, 0, 'C')
    pdf.ln()

    # Agregar filas
    for i, row in df.iterrows():
        for col in df.columns:
            pdf.cell(40, 10, str(row[col]), 1, 0, 'C')
        pdf.ln()

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

if st.button("Exportar PDF"):
    pdf_file = export_pdf(df_final)
    st.download_button("Descargar PDF", data=pdf_file, file_name="reporte.pdf")
