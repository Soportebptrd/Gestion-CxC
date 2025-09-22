import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO
from fpdf import FPDF
import json

# ===== CONFIGURACIÓN =====
st.set_page_config(page_title="Seguimiento CxC - IDEMEFA", layout="wide")

# ===== LOGIN =====
st.title("📞 Seguimiento de Clientes - CxC")

# Inicializar estado de sesión
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    usuario_input = st.text_input("Usuario")
    contrasena_input = st.text_input("Contraseña", type="password")
    
    # Configuración de usuarios
    USERS = {
        "idemefa": "idemefa",
        "admin": "admin123",
        "erick": "erick123"
    }
    
    if st.button("Iniciar sesión"):
        if usuario_input in USERS and contrasena_input == USERS[usuario_input]:
            st.session_state.logged_in = True
            st.session_state.username = usuario_input
            st.success(f"✅ Bienvenido {usuario_input}")
            st.rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# Usuario ya logueado
st.success(f"👋 Bienvenido, {st.session_state.username}!")

# ===== CONFIGURACIÓN GOOGLE SHEETS =====
SHEET_URL = "https://docs.google.com/spreadsheets/d/1z-BExCxP_rNEz-Ee0Xot6XwInlBfQ5icSgyxmu7mGMY/edit"

# Crear diccionario de credenciales desde secrets
creds_dict = {
    "type": "service_account",
    "project_id": "gestion-cxc-idemefa",
    "private_key_id": "b0435d5ab60ea63f179087c1bbf1d050cfcd77ae",
    "private_key": st.secrets["GOOGLE_SHEET"]["private_key"],
    "client_email": "gestion-cxc-idemefa@gestion-cxc-idemefa.iam.gserviceaccount.com",
    "client_id": "100177103439146822848",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/gestion-cxc-idemefa%40gestion-cxc-idemefa.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    st.sidebar.success("✅ Conectado a Google Sheets")
except Exception as e:
    st.error(f"❌ Error de conexión: {str(e)}")
    st.stop()

# ===== CARGA DE DATOS =====
try:
    # Cargar datos
    sheet_respuestas = client.open_by_url(SHEET_URL).worksheet("sheet1")
    sheet_clientes = client.open_by_url(SHEET_URL).worksheet("BaseClientes")
    
    df_respuestas = pd.DataFrame(sheet_respuestas.get_all_records())
    df_clientes = pd.DataFrame(sheet_clientes.get_all_records())
    
    # Mostrar info de carga
    st.sidebar.info(f"📊 Sheet1: {len(df_respuestas)} registros")
    st.sidebar.info(f"📊 BaseClientes: {len(df_clientes)} clientes")
    
    # Verificar columnas
    st.sidebar.write("**Columnas Sheet1:**", df_respuestas.columns.tolist())
    st.sidebar.write("**Columnas BaseClientes:**", df_clientes.columns.tolist())
    
except Exception as e:
    st.error(f"❌ Error cargando datos: {str(e)}")
    st.stop()

# ===== PROCESAMIENTO DE DATOS =====
# Renombrar columnas para consistencia
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

# Limpiar y estandarizar datos
df_respuestas["codigo_cliente"] = df_respuestas["codigo_cliente"].astype(str).str.strip()
df_clientes["codigo_cliente"] = df_clientes["codigo_cliente"].astype(str).str.strip()

# Merge de datos
df_final = df_respuestas.merge(df_clientes, on="codigo_cliente", how="left")

# Convertir marca temporal
if "Marca temporal" in df_final.columns:
    df_final["Marca temporal"] = pd.to_datetime(df_final["Marca temporal"], errors='coerce')
    df_final["fecha"] = df_final["Marca temporal"].dt.date
    df_final["hora"] = df_final["Marca temporal"].dt.time

# Ordenar por fecha
if "Marca temporal" in df_final.columns:
    df_final = df_final.sort_values("Marca temporal", ascending=False)

# ===== INTERFAZ PRINCIPAL =====
st.header("📋 Registro de Llamadas a Clientes")

# Filtros en sidebar
st.sidebar.header("🔍 Filtros")

# Filtro por fecha
if "fecha" in df_final.columns:
    fechas = sorted(df_final["fecha"].unique(), reverse=True)
    fecha_seleccionada = st.sidebar.selectbox("Filtrar por fecha:", options=fechas)
    df_filtrado = df_final[df_final["fecha"] == fecha_seleccionada]
else:
    df_filtrado = df_final

# Filtro por usuario
if "usuario" in df_filtrado.columns:
    usuarios = sorted(df_filtrado["usuario"].dropna().unique())
    usuarios_seleccionados = st.sidebar.multiselect(
        "Filtrar por usuario:", 
        options=usuarios,
        default=usuarios
    )
    df_filtrado = df_filtrado[df_filtrado["usuario"].isin(usuarios_seleccionados)]

# Filtro por llamado
if "llamado" in df_filtrado.columns:
    estado_llamado = st.sidebar.selectbox(
        "Filtrar por llamado:",
        options=["Todos", "Sí", "No"]
    )
    if estado_llamado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["llamado"].str.upper() == estado_llamado.upper()]

# ===== MOSTRAR DATOS =====
# Estadísticas
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📞 Total llamadas", len(df_filtrado))
with col2:
    st.metric("👥 Usuarios", df_filtrado["usuario"].nunique() if "usuario" in df_filtrado.columns else 0)
with col3:
    st.metric("🏢 Clientes", df_filtrado["codigo_cliente"].nunique())
with col4:
    if "llamado" in df_filtrado.columns:
        llamados_exitosos = (df_filtrado["llamado"].str.upper() == "SÍ").sum()
        st.metric("✅ Llamados exitosos", llamados_exitosos)

# Función para colorear el dataframe
def estilo_llamados(val):
    if str(val).upper() in ["SÍ", "SI", "YES"]:
        return 'background-color: #d4edda; color: #155724;'
    elif str(val).upper() in ["NO", "NOT"]:
        return 'background-color: #f8d7da; color: #721c24;'
    return ''

# Aplicar estilo
if not df_filtrado.empty:
    columnas_mostrar = [
        "fecha", "hora", "codigo_cliente", "nombre_cliente", 
        "usuario", "llamado", "monto", "notas"
    ]
    columnas_disponibles = [col for col in columnas_mostrar if col in df_filtrado.columns]
    
    df_mostrar = df_filtrado[columnas_disponibles]
    
    # Aplicar estilo
    styled_df = df_mostrar.style.applymap(estilo_llamados, subset=["llamado"])
    
    # Mostrar dataframe
    st.dataframe(
        styled_df,
        height=600,
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados")

# ===== EXPORTAR DATOS =====
st.sidebar.header("💾 Exportar datos")

if not df_filtrado.empty:
    # Exportar CSV
    csv = df_filtrado.to_csv(index=False)
    st.sidebar.download_button(
        "📥 Descargar CSV",
        csv,
        f"reporte_cxc_{pd.Timestamp.today().strftime('%Y%m%d')}.csv",
        "text/csv"
    )

    # Exportar PDF
    def generar_pdf(df):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Reporte de Seguimiento CxC - IDEMEFA", 0, 1, 'C')
        pdf.ln(5)
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, f"Generado el: {pd.Timestamp.today().strftime('%Y-%m-%d %H:%M')}", 0, 1)
        pdf.cell(0, 8, f"Total registros: {len(df)}", 0, 1)
        pdf.ln(5)
        
        # Encabezados de tabla
        pdf.set_font("Arial", 'B', 8)
        columnas = df.columns.tolist()
        for col in columnas:
            pdf.cell(40, 6, str(col)[:15], 1)
        pdf.ln()
        
        # Datos de tabla
        pdf.set_font("Arial", '', 7)
        for _, row in df.head(50).iterrows():  # Limitar a 50 filas
            for col in columnas:
                pdf.cell(40, 6, str(row[col])[:20], 1)  # Truncar texto largo
            pdf.ln()
        
        return pdf.output(dest='S').encode('latin1')

    pdf_bytes = generar_pdf(df_filtrado)
    st.sidebar.download_button(
        "📄 Descargar PDF",
        pdf_bytes,
        f"reporte_cxc_{pd.Timestamp.today().strftime('%Y%m%d')}.pdf",
        "application/pdf"
    )

# ===== CERRAR SESIÓN =====
if st.sidebar.button("🚪 Cerrar sesión"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

