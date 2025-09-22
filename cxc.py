import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF

# ---------------------------
# Login seguro
# ---------------------------
st.set_page_config(page_title="Seguimiento Clientes - CxC", layout="wide")
st.title("📞 Seguimiento de Clientes - CxC")

usuario_input = st.text_input("Usuario")
contrasena_input = st.text_input("Contraseña", type="password")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if st.button("Ingresar"):
    login_info = st.secrets["login"]
    if usuario_input == login_info["usuario"] and contrasena_input == login_info["contrasena"]:
        st.session_state["logged_in"] = True
        st.success(f"Bienvenido {usuario_input}")
    else:
        st.error("Usuario o contraseña incorrectos")

if not st.session_state["logged_in"]:
    st.stop()

# ---------------------------
# Conexión Google Sheets
# ---------------------------
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = st.secrets["google_sheet"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

SHEET_URL = "TU_LINK_DE_GOOGLE_SHEET"  # <- Pon aquí tu link
sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("sheet1")
sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")

# ---------------------------
# Cargar datos
# ---------------------------
df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

# Limpiar nombres de columnas
df_respuestas.columns = [c.strip().lower().replace(" ", "_") for c in df_respuestas.columns]
df_clientes.columns = [c.strip().lower().replace(" ", "_") for c in df_clientes.columns]

# Unir nombres de clientes
df_final = pd.merge(df_respuestas, df_clientes, on="codigo_del_cliente", how="left")

# Reordenar columnas
df_final = df_final[["marca_temporal","codigo_del_cliente","nombre_cliente","llamado","monto","notas","usuario"]]

# ---------------------------
# Función para colorear llamado
# ---------------------------
def color_llamado(val):
    color = "green" if str(val).lower() == "si" else "red"
    return f"background-color: {color}; color: white; font-weight: bold;"

styled_df = df_final.style.applymap(color_llamado, subset=["llamado"])

# Mostrar tabla
st.dataframe(styled_df, height=900, width="stretch")

# ---------------------------
# Exportar PDF
# ---------------------------
def export_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Seguimiento Clientes - CxC", 0, 1, "C")
    pdf.set_font("Arial", "", 12)
    
    # Tabla
    col_width = pdf.w / (len(df.columns)+1)
    row_height = pdf.font_size * 1.5
    for i, row in df.iterrows():
        for item in row:
            pdf.cell(col_width, row_height, str(item), border=1)
        pdf.ln(row_height)
    
    pdf_output = "Seguimiento_CxC.pdf"
    pdf.output(pdf_output)
    return pdf_output

if st.button("📄 Exportar PDF"):
    pdf_file = export_pdf(df_final)
    st.success("PDF generado correctamente")
    st.download_button("Descargar PDF", pdf_file, file_name="Seguimiento_CxC.pdf")

