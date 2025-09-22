import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
from fpdf import FPDF

# ==========================
# LOGIN
# ==========================
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("🔒 Iniciar sesión")
    usuario_input = st.text_input("Usuario")
    password_input = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        users = st.secrets["APP_USERS"]
        if usuario_input in users and password_input == users[usuario_input]:
            st.success(f"¡Bienvenido {usuario_input}!")
            st.session_state['authenticated'] = True
            st.session_state['usuario'] = usuario_input
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

# ==========================
# GOOGLE SHEET
# ==========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = dict(st.secrets["GOOGLE_SHEET"])
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1z-BExCxP_rNEz-Ee0Xot6XwInlBfQ5icSgyxmu7mGMY/edit"

sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("Sheet1")
df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())

sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

# ==========================
# CRUCE Y FORMATO
# ==========================
df_respuestas['Código del cliente'] = df_respuestas['Código del cliente'].astype(str).str.strip()
df_clientes['Código del cliente'] = df_clientes['Código del cliente'].astype(str).str.strip()

df_final = df_respuestas.merge(df_clientes, on="Código del cliente", how="left")

# Reordenar columnas
df_final = df_final[['Marca temporal', 'Código del cliente', 'Nombre Cliente', 'Llamado', 'Monto', 'Notas', 'Usuario']]

# Colorear filas según "Llamado"
def color_llamado(val):
    color = 'background-color: #d4edda' if str(val).lower() == 'si' else 'background-color: #f8d7da'
    return color

styled_df = df_final.style.applymap(color_llamado, subset=['Llamado'])

# ==========================
# STREAMLIT
# ==========================
st.title(f"📞 Seguimiento de Clientes - CxC (Usuario: {st.session_state['usuario']})")

# Filtro por fecha
fecha_inicio = st.date_input("Fecha inicio", pd.to_datetime("2025-09-01"))
fecha_fin = st.date_input("Fecha fin", pd.to_datetime("2025-09-21"))

df_final['Marca temporal'] = pd.to_datetime(df_final['Marca temporal'])
df_filtrado = df_final[(df_final['Marca temporal'] >= pd.to_datetime(fecha_inicio)) &
                       (df_final['Marca temporal'] <= pd.to_datetime(fecha_fin))]

# Mostrar tabla grande
st.dataframe(styled_df.loc[df_filtrado.index], height=900, width='stretch')

# ==========================
# EXPORTAR PDF
# ==========================
def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    for i in range(len(df)):
        row = df.iloc[i]
        pdf.cell(0, 6, f"{row['Marca temporal']} | {row['Código del cliente']} | {row['Nombre Cliente']} | "
                        f"{row['Llamado']} | {row['Monto']} | {row['Notas']} | {row['Usuario']}", ln=True)
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

if st.button("Exportar PDF"):
    pdf_file = export_pdf(df_filtrado)
    st.download_button(label="Descargar PDF", data=pdf_file, file_name="reporte_cxc.pdf", mime="application/pdf")
