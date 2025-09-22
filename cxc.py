import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
from fpdf import FPDF
from datetime import datetime, timedelta

# ===== CONFIGURACIÓN =====
st.set_page_config(page_title="Seguimiento CxC - IDEMEFA", layout="wide")

# ===== LOGIN SIMPLIFICADO =====
st.title("📞 Seguimiento de Clientes - CxC")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    usuario_input = st.text_input("Usuario")
    contrasena_input = st.text_input("Contraseña", type="password")

    # Obtener login desde secrets
    LOGIN_USUARIO = st.secrets["login"]["usuario"]
    LOGIN_CONTRASENA = st.secrets["login"]["contrasena"]

    if st.button("Iniciar sesión"):
        if usuario_input == LOGIN_USUARIO and contrasena_input == LOGIN_CONTRASENA:
            st.session_state.logged_in = True
            st.session_state.username = usuario_input
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# ===== CONEXIÓN GOOGLE SHEETS =====
SHEET_URL = "https://docs.google.com/spreadsheets/d/1z-BExCxP_rNEz-Ee0Xot6XwInlBfQ5icSgyxmu7mGMY/edit"

creds_dict = dict(st.secrets["GOOGLE_SHEET"])
creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("sheet1")
    sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")

    df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())
    df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
except Exception as e:
    st.error(f"❌ Error de conexión: {str(e)}")
    st.stop()

# ===== PROCESAMIENTO DE DATOS =====
df_respuestas.rename(columns={
    "Código del cliente": "codigo_cliente",
    "Usuario": "usuario",
    "Notas": "notas",
    "Llamado": "llamado",
    "Monto": "monto"
}, inplace=True)

df_clientes.rename(columns={
    "Código del cliente": "codigo_cliente",
    "Nombre Cliente": "nombre_cliente"
}, inplace=True)

df_respuestas["codigo_cliente"] = df_respuestas["codigo_cliente"].astype(str).str.strip()
df_clientes["codigo_cliente"] = df_clientes["codigo_cliente"].astype(str).str.strip()

df_final = df_respuestas.merge(df_clientes, on="codigo_cliente", how="left")

if "Marca temporal" in df_final.columns:
    df_final["Marca temporal"] = pd.to_datetime(df_final["Marca temporal"], errors='coerce')
    df_final["fecha"] = df_final["Marca temporal"].dt.date
    df_final = df_final.sort_values("Marca temporal", ascending=False)

# ===== FILTROS EN SIDEBAR =====
st.sidebar.header("🔍 Filtros")

if "fecha" in df_final.columns and not df_final["fecha"].isnull().all():
    min_date = df_final["fecha"].min()
    max_date = df_final["fecha"].max()
    default_start = max(min_date, max_date - timedelta(days=7))

    fecha_inicio = st.sidebar.date_input(
        "Fecha inicio:",
        value=default_start,
        min_value=min_date,
        max_value=max_date
    )
    fecha_fin = st.sidebar.date_input(
        "Fecha fin:",
        value=max_date,
        min_value=min_date,
        max_value=max_date
    )

    df_filtrado = df_final[
        (df_final["fecha"] >= fecha_inicio) &
        (df_final["fecha"] <= fecha_fin)
    ]
else:
    df_filtrado = df_final

if "usuario" in df_filtrado.columns:
    usuarios = sorted(df_filtrado["usuario"].dropna().unique())
    usuarios_seleccionados = st.sidebar.multiselect(
        "Usuarios:",
        options=usuarios,
        default=usuarios
    )
    df_filtrado = df_filtrado[df_filtrado["usuario"].isin(usuarios_seleccionados)]

# ===== INTERFAZ PRINCIPAL =====
st.header(f"📋 Registro de Llamadas - {st.session_state.username}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📞 Total llamadas", len(df_filtrado))
with col2:
    st.metric("👥 Usuarios", df_filtrado["usuario"].nunique() if "usuario" in df_filtrado.columns else 0)
with col3:
    st.metric("🏢 Clientes", df_filtrado["codigo_cliente"].nunique())
with col4:
    if "llamado" in df_filtrado.columns:
        llamados_si = df_filtrado["llamado"].str.upper().isin(["SI", "SÍ"]).sum()
        st.metric("✅ Llamados exitosos", llamados_si)

def estilo_llamados(val):
    if str(val).upper() in ["SÍ", "SI", "YES"]:
        return 'background-color: #d4edda; color: #155724;'
    elif str(val).upper() in ["NO", "NOT"]:
        return 'background-color: #f8d7da; color: #721c24;'
    return ''

if not df_filtrado.empty:
    columnas_mostrar = ["fecha", "codigo_cliente", "nombre_cliente", "usuario", "llamado", "monto", "notas"]
    columnas_disponibles = [col for col in columnas_mostrar if col in df_filtrado.columns]
    df_mostrar = df_filtrado[columnas_disponibles]
    styled_df = df_mostrar.style.applymap(estilo_llamados, subset=["llamado"])
    st.dataframe(styled_df, height=600, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ No hay datos para el rango seleccionado")

# ===== EXPORTAR PDF =====
def export_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Reporte CxC", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)

    # Encabezados
    for col in df.columns:
        pdf.cell(28, 8, str(col), border=1)
    pdf.ln()

    # Filas
    for _, row in df.iterrows():
        for col in df.columns:
            text = str(row[col])
            pdf.cell(28, 8, text[:15], border=1)  # cortar si es largo
        pdf.ln()

    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

if not df_filtrado.empty:
    pdf_bytes = export_pdf(df_filtrado[columnas_disponibles])
    st.download_button(
        "📥 Descargar PDF",
        data=pdf_bytes,
        file_name=f"reporte_cxc_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

# ===== CERRAR SESIÓN =====
if st.sidebar.button("🚪 Cerrar sesión"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

