import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fpdf import FPDF
import hashlib
from unidecode import unidecode

# ==========================
# CONFIGURAR PÁGINA STREAMLIT
# ==========================
st.set_page_config(page_title="Seguimiento de Clientes - CxC",
                   layout="wide")  # pantalla completa

# ==========================
# CONFIGURACIÓN GOOGLE SHEET
# ==========================
SERVICE_ACCOUNT_FILE = r"D:\Desktop2\TRABAJO BD\PROYECTOS_DB\IDEMEFA\MOROSIDAD\service_account.json"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1z-BExCxP_rNEz-Ee0Xot6XwInlBfQ5icSgyxmu7mGMY/edit#gid=0"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)

# ==========================
# CARGAR DATOS
# ==========================
sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("sheet1")
df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())

sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")
df_clientes = pd.DataFrame(sheet_clientes.get_all_records())

# ==========================
# NORMALIZAR COLUMNAS
# ==========================
def normalize_columns(df):
    df.columns = df.columns.str.strip()
    df.columns = df.columns.str.lower()
    df.columns = [unidecode(c) for c in df.columns]
    df.columns = [c.replace(' ', '_') for c in df.columns]
    return df

df_respuestas = normalize_columns(df_respuestas)
df_clientes = normalize_columns(df_clientes)

# ==========================
# NORMALIZAR DATOS CLAVE
# ==========================
df_respuestas['codigo_del_cliente'] = df_respuestas['codigo_del_cliente'].astype(str).str.strip()
df_clientes['codigo_del_cliente'] = df_clientes['codigo_del_cliente'].astype(str).str.strip()

# ==========================
# MERGE Y AVISO DE CÓDIGOS NO COINCIDENTES
# ==========================
df_final = df_respuestas.merge(df_clientes, on="codigo_del_cliente", how="left")

codigos_no_encontrados = df_respuestas[~df_respuestas['codigo_del_cliente'].isin(df_clientes['codigo_del_cliente'])]
if not codigos_no_encontrados.empty:
    st.warning("⚠ Los siguientes códigos no están en BaseClientes y aparecerán vacíos:")
    st.dataframe(codigos_no_encontrados[['codigo_del_cliente', 'usuario']])

# ==========================
# CONVERTIR FECHAS
# ==========================
if 'marca_temporal' in df_final.columns:
    df_final['marca_temporal'] = pd.to_datetime(df_final['marca_temporal'], dayfirst=True, errors='coerce')
else:
    df_final['marca_temporal'] = pd.Timestamp.today()

# ==========================
# LOGIN BÁSICO
# ==========================
USERS = {
    "erick": hashlib.sha256("1234".encode()).hexdigest(),
    "admin": hashlib.sha256("admin".encode()).hexdigest()
}

def login(username, password):
    return USERS.get(username) == hashlib.sha256(password.encode()).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# ==========================
# FLUJO DE LOGIN
# ==========================
if not st.session_state.logged_in:
    st.title("🔒 Iniciar sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if login(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success("¡Login correcto!")
        else:
            st.error("Usuario o contraseña incorrectos")
else:
    st.title(f"📞 Seguimiento de Clientes - CxC (Usuario: {st.session_state.username})")

    # ==========================
    # FILTRO SOLO POR FECHAS (IGNORANDO HORA)
    # ==========================
    fecha_inicio = st.date_input("Fecha inicio:", value=df_final['marca_temporal'].min())
    fecha_fin = st.date_input("Fecha fin:", value=df_final['marca_temporal'].max())

    fecha_inicio_ts = pd.Timestamp(fecha_inicio)
    fecha_fin_ts = pd.Timestamp(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    df_filtrado = df_final[(df_final['marca_temporal'] >= fecha_inicio_ts) &
                           (df_final['marca_temporal'] <= fecha_fin_ts)]

    # ==========================
    # REORDENAR COLUMNAS
    # ==========================
    column_order = ['marca_temporal', 'codigo_del_cliente', 'nombre_cliente', 'llamado', 'monto', 'notas', 'usuario']
    df_filtrado = df_filtrado[column_order]

    # ==========================
    # FUNCION PARA COLORES
    # ==========================
    def color_llamado(val):
        if str(val).strip().lower() == 'si':
            color = 'background-color: #b6fcb6'  # verde claro
        elif str(val).strip().lower() == 'no':
            color = 'background-color: #fcb6b6'  # rojo claro
        else:
            color = ''
        return color

    styled_df = df_filtrado.style.applymap(color_llamado, subset=['llamado'])

    # ==========================
    # MOSTRAR TABLA GRANDE
    # ==========================
    st.dataframe(styled_df, height=900, width="stretch")  # ancho completo y tabla alta

    # ==========================
    # EXPORTAR PDF
    # ==========================
    def export_pdf(df):
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Reporte CxC - Seguimiento de Clientes", 0, 1, 'C')
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 10)
        col_width = pdf.w / (len(df.columns) + 1)
        for col in df.columns:
            pdf.cell(col_width, 8, str(col), border=1, align='C')
        pdf.ln()

        pdf.set_font("Arial", '', 9)
        for i in range(len(df)):
            for col in df.columns:
                text = str(df.iloc[i][col])
                pdf.cell(col_width, 8, text[:20], border=1, align='C')
            pdf.ln()

        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return pdf_bytes

    if st.button("📄 Exportar tabla a PDF"):
        pdf_bytes = export_pdf(df_filtrado)
        st.download_button(
            label="Descargar PDF",
            data=pdf_bytes,
            file_name="Reporte_CxC.pdf",
            mime="application/pdf"
        )
