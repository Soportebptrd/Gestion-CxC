import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF

# -----------------------------
# Login
# -----------------------------
st.title("📞 Seguimiento de Clientes - CxC")

usuario_input = st.text_input("Usuario")
contrasena_input = st.text_input("Contraseña", type="password")

if usuario_input != st.secrets["login"]["usuario"] or contrasena_input != st.secrets["login"]["contrasena"]:
    st.warning("Usuario o contraseña incorrectos")
    st.stop()

st.success(f"Bienvenido {usuario_input}")

# -----------------------------
# Conexión a Google Sheets
# -----------------------------
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

creds_dict = st.secrets["google_sheet"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPE)
client = gspread.authorize(creds)

# -----------------------------
# Cargar hojas
# -----------------------------
SHEET_URL = "TU_URL_DE_GOOGLE_SHEET"
sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("Sheet1")
sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")

data_respuestas = sheet_respuestas.get_all_records()
data_clientes = sheet_clientes.get_all_records()

df_respuestas = pd.DataFrame(data_respuestas)
df_clientes = pd.DataFrame(data_clientes)

# -----------------------------
# Merge con clientes
# -----------------------------
df_respuestas['Código del cliente'] = df_respuestas['Código del cliente'].astype(str).str.strip()
df_clientes['Código del cliente'] = df_clientes['Código del cliente'].astype(str).str.strip()

df_final = df_respuestas.merge(df_clientes, on="Código del cliente", how="left")

# -----------------------------
# Reordenar columnas
# -----------------------------
df_final = df_final[[
    "Marca temporal",
    "Código del cliente",
    "Nombre Cliente",
    "Llamado",
    "Monto",
    "Notas",
    "Usuario"
]]

# -----------------------------
# Colorear tabla
# -----------------------------
def color_llamado(val):
    color = 'background-color: #d4edda' if str(val).lower() == "si" else 'background-color: #f8d7da'
    return color

styled_df = df_final.style.applymap(color_llamado, subset=['Llamado'])

# -----------------------------
# Mostrar tabla grande
# -----------------------------
st.dataframe(styled_df, height=900, width='stretch')

# -----------------------------
# Exportar PDF
# -----------------------------
def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for i in range(len(df)):
        row = df.iloc[i]
        line = f"{row['Marca temporal']} | {row['Código del cliente']} | {row['Nombre Cliente']} | {row['Llamado']} | {row['Monto']} | {row['Notas']} | {row['Usuario']}"
        pdf.multi_cell(0, 8, line)

    pdf_output = "seguimiento_clientes.pdf"
    pdf.output(pdf_output)
    return pdf_output

if st.button("Exportar PDF"):
    pdf_file = export_pdf(df_final)
    st.success("PDF generado")
    with open(pdf_file, "rb") as f:
        st.download_button("Descargar PDF", f, file_name=pdf_file)
