import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
from fpdf import FPDF

# ===== LOGIN =====
st.title("📞 Seguimiento de Clientes - CxC")

usuario_input = st.text_input("Usuario")
contrasena_input = st.text_input("Contraseña", type="password")

users_dict = dict(st.secrets["USERS"])

if st.button("Iniciar sesión"):
    if usuario_input in users_dict and contrasena_input == users_dict[usuario_input]:
        st.success(f"Bienvenido {usuario_input}")
        st.session_state["logged_in"] = True
    else:
        st.error("Usuario o contraseña incorrectos")
        st.stop()
elif "logged_in" not in st.session_state:
    st.stop()

# ===== GOOGLE SHEETS =====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = dict(st.secrets["GOOGLE_SHEET"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ===== CARGA DE DATOS =====
SHEET_URL = "https://docs.google.com/spreadsheets/d/1z-BExCxP_rNEz-Ee0Xot6XwInlBfQ5icSgyxmu7mGMY/edit"
sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("sheet1")
sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")

df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

df_respuestas.rename(columns={"Código del cliente": "codigo_cliente"}, inplace=True)
df_clientes.rename(columns={"Código del cliente": "codigo_cliente", "Nombre Cliente": "nombre_cliente"}, inplace=True)

df_respuestas["codigo_cliente"] = df_respuestas["codigo_cliente"].astype(str).str.strip()
df_clientes["codigo_cliente"] = df_clientes["codigo_cliente"].astype(str).str.strip()

df_final = df_respuestas.merge(df_clientes, on="codigo_cliente", how="left")
df_final = df_final[["Marca temporal", "codigo_cliente", "nombre_cliente", "Llamado", "Monto", "Notas", "Usuario"]]

def color_llamado(val):
    return 'background-color: #b6fcb6' if str(val).lower() == "si" else 'background-color: #ffb6b6'

styled_df = df_final.style.applymap(color_llamado, subset=["Llamado"])
st.dataframe(styled_df, height=900, width="stretch")

# ===== EXPORTAR PDF =====
def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    col_names = df.columns.tolist()
    pdf.cell(0, 10, "Reporte Clientes CxC", ln=True, align="C")
    pdf.ln(5)
    for i, row in df.iterrows():
        for col in col_names:
            pdf.cell(0, 8, f"{col}: {row[col]}", ln=True)
        pdf.ln(5)
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

pdf_file = export_pdf(df_final)
st.download_button("📄 Descargar PDF", data=pdf_file, file_name="Reporte_CxC.pdf", mime="application/pdf")

