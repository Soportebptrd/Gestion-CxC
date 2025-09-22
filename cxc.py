import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import io
from datetime import datetime

# --------------------------
# LOGIN
# --------------------------
st.title("📞 Seguimiento de Clientes - CxC")

usuario_input = st.text_input("Usuario")
contrasena_input = st.text_input("Contraseña", type="password")

if st.button("Ingresar"):
    if usuario_input == st.secrets["login"]["usuario"] and contrasena_input == st.secrets["login"]["contrasena"]:
        st.success(f"Bienvenido {usuario_input}")
        st.session_state['logged_in'] = True
    else:
        st.error("Usuario o contraseña incorrectos")

if not st.session_state.get('logged_in'):
    st.stop()

# --------------------------
# CONEXIÓN A GOOGLE SHEET
# --------------------------
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds_dict = dict(st.secrets["google_sheet"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# URLs de tus Google Sheets
SHEET_URL_CLIENTES = "TU_SHEET_BASECLIENTES_URL"
SHEET_URL_RESPUESTAS = "TU_SHEET_RESPUESTAS_URL"

sheet_clientes = client.open_by_url(SHEET_URL_CLIENTES).worksheet("BaseClientes")
sheet_respuestas = client.open_by_url(SHEET_URL_RESPUESTAS).worksheet("sheet1")

# --------------------------
# LEER DATOS
# --------------------------
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())

# Limpiar espacios
df_clientes['Código del cliente'] = df_clientes['Código del cliente'].astype(str).str.strip()
df_respuestas['Código del cliente'] = df_respuestas['Código del cliente'].astype(str).str.strip()

# --------------------------
# FILTRAR POR FECHAS
# --------------------------
fecha_inicio = st.date_input("Fecha inicio", datetime(2025, 9, 1))
fecha_fin = st.date_input("Fecha fin", datetime.now())

df_respuestas['Marca temporal'] = pd.to_datetime(df_respuestas['Marca temporal'], dayfirst=True)
df_filtrado = df_respuestas[(df_respuestas['Marca temporal'] >= pd.to_datetime(fecha_inicio)) &
                             (df_respuestas['Marca temporal'] <= pd.to_datetime(fecha_fin))]

# --------------------------
# MERGE CON CLIENTES
# --------------------------
df_final = df_filtrado.merge(df_clientes, left_on="Código del cliente", right_on="Código del cliente", how="left")

# Reordenar columnas
df_final = df_final[['Marca temporal', 'Código del cliente', 'Nombre Cliente', 'Llamado', 'Monto', 'Notas', 'Usuario']]

# --------------------------
# COLORES SEGÚN LLAMADO
# --------------------------
def color_llamado(val):
    if str(val).lower() == "si":
        return 'background-color: lightgreen'
    else:
        return 'background-color: lightcoral'

styled_df = df_final.style.applymap(color_llamado, subset=['Llamado'])

# --------------------------
# MOSTRAR TABLA
# --------------------------
st.dataframe(styled_df, height=800, width='stretch')

# --------------------------
# EXPORTAR PDF
# --------------------------
def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for i, row in df.iterrows():
        pdf.cell(0, 10, txt=f"{row['Código del cliente']} - {row['Nombre Cliente']} - {row['Llamado']} - {row['Monto']}", ln=True)

    pdf_output = io.BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output.write(pdf_bytes)
    pdf_output.seek(0)
    return pdf_output

pdf_file = export_pdf(df_final)
st.download_button("📄 Descargar PDF", data=pdf_file, file_name="reporte.pdf", mime="application/pdf")
