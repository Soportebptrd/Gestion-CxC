import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Seguimiento de Clientes - CxC", layout="wide")

# --- LOGIN ---
usuario_input = st.text_input("Usuario")
contrasena_input = st.text_input("Contraseña", type="password")

if usuario_input != st.secrets["login"]["usuario"] or contrasena_input != st.secrets["login"]["contrasena"]:
    st.warning("Usuario o contraseña incorrectos")
    st.stop()

st.success(f"Bienvenido {usuario_input}")

# --- GOOGLE SHEET ---
SHEET_URL = st.secrets["google"]["SHEET_URL"]

scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

# Convierte el secreto a diccionario
creds_dict = dict(st.secrets["google"])
# Reemplaza saltos de línea de la private_key
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# --- LEER HOJAS ---
sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("Sheet1")
sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")

df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

# --- UNIR DATOS ---
df_final = pd.merge(df_respuestas, df_clientes, left_on="Código del cliente", right_on="Código del cliente", how="left")
df_final = df_final.rename(columns={
    "Marca temporal": "marca_temporal",
    "Código del cliente": "codigo_cliente",
    "Nombre Cliente": "nombre_cliente",
    "Llamado": "llamado",
    "Notas": "notas",
    "Usuario": "usuario",
    "Monto": "monto"
})

df_final = df_final[["marca_temporal","codigo_cliente","nombre_cliente","llamado","monto","notas","usuario"]]

# --- ESTILO DE TABLA ---
def highlight_llamado(val):
    color = 'background-color: #d4edda' if str(val).lower() == "si" else 'background-color: #f8d7da'
    return color

styled_df = df_final.style.applymap(highlight_llamado, subset=["llamado"])

st.dataframe(styled_df, height=900, width='stretch')

# --- EXPORTAR PDF ---
def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    col_widths = [35, 30, 50, 20, 25, 50, 25]

    # Header
    for i, col in enumerate(df.columns):
        pdf.cell(col_widths[i], 8, col, border=1)
    pdf.ln()

    # Rows
    for idx, row in df.iterrows():
        for i, col in enumerate(df.columns):
            pdf.cell(col_widths[i], 8, str(row[col]), border=1)
        pdf.ln()

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

if st.button("Exportar PDF"):
    pdf_file = export_pdf(df_final)
    st.download_button("Descargar PDF", data=pdf_file, file_name="seguimiento_clientes.pdf", mime="application/pdf")
