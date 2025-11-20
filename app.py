import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import qrcode
from PIL import Image
import io
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(layout="wide", page_title="PRIOR-IA")

# --- 2. BARRA LATERAL CON CÓDIGO QR ---
with st.sidebar:
    st.header("📱 Pruébalo en Vivo")
    
    # TU URL REAL
    url_app = "https://prior-ia-89rpjey9zwpxd4xkriedjd.streamlit.app/"
    
    # Generación del QR
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url_app)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Mostrar QR
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    st.image(img_byte_arr, caption="Escanea aquí", use_container_width=True)
    
    st.divider()
    st.info("Desarrollado por el Equipo Hackatón Hospital Padre Hurtado")

# --- 3. CONFIGURACIÓN DEL CEREBRO (IA) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-flash-latest')
except Exception as e:
    st.error(f"Error de API Key. Verifica tus secretos en Streamlit Cloud. Error: {e}")
    st.stop()

# --- 4. FUNCIÓN MAESTRA DE LLAMADA A IA ---
def get_irc_from_ia(texto_paciente):
    prompt_template = f"""
    ACTÚA COMO: Un médico especialista senior y un ingeniero de riesgos clínicos del Hospital Padre Hurtado.
    
    TAREA: Evaluar el siguiente resumen de paciente anonimizado. Tu misión es generar un "Índice de Riesgo Clínico" (IRC) de 0 a 100 y una justificación clara.
    
    REGLAS DE EVALUACIÓN:
    - **Riesgo Crítico (90-100):** Cirugía compleja reciente (<30 días) + eventos adversos (Urgencia/MAE) + polifarmacia de riesgo. Pacientes oncológicos descompensados.
    - **Riesgo Alto (70-89):** Cirugía reciente O eventos adversos O polifarmacia de riesgo. Vulnerabilidad demográfica.
    - **Riesgo Medio (40-69):** Paciente crónico estable (DM2, HTA) o con cirugía programada pasada (> 2 meses).
    - **Riesgo Bajo (0-39):** Paciente estable, crónico controlado, o consulta de rutina.
    
    FORMATO DE SALIDA (JSON OBLIGATORIO):
    Responde ÚNICAMENTE con este JSON válido:
    {{
      "score": <número 0-100>,
      "nivel": "<Texto del nivel>",
      "justificacion": ["<Bullet 1>", "<Bullet 2>", "<Bullet 3>"]
    }}
    
    RESUMEN DEL PACIENTE:
    "{texto_paciente}"
    """
    
    # Desactivar filtros de seguridad para contenido médico
    safety = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    response = model.generate_content(prompt_template, safety_settings=safety)
    
    # Limpieza de JSON
    clean_text = re.sub(r"```json\n?|```", "", response.text.strip())
    return json.loads(clean_text)

# --- 5. INTERFAZ PRINCIPAL ---

st.title("PRIOR-IA: Índice de Riesgo Clínico (IRC)")
st.subheader("Prototipo cálculo IRC - Salud a la vanguardIA - Hospital Padre Hurtado")

# ==========================================
# MODO 1: CONSULTA INDIVIDUAL
# ==========================================
st.header("1. Herramienta de Consulta Individual (Clínico)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Describa aquí la condición y/o historial clínico del paciente:")
    resumen_paciente = st.text_area(
        "", 
        placeholder="Ej: Paciente de 82 años, hipertenso, operado del corazón hace 3 semanas. Acude por dificultad respiratoria...",
        height=300 
    )
    calcular_btn = st.button("Calcular IRC Individual", use_container_width=True)

if calcular_btn: 
    if resumen_paciente: 
        with st.spinner("Analizando paciente y calculando IRC..."):
            try:
                # Llamada a la función
                data = get_irc_from_ia(resumen_paciente)
                
                score_val = int(data["score"])
                nivel_val = data["nivel"]
                justificacion_lista = data["justificacion"]
                
                # Formato HTML para lista
                justificacion_html = "<ul>" + "".join(f"<li>{item}</li>" for item in justificacion_lista) + "</ul>"
                
                with col2:
                    st.subheader("Resultados del Análisis")
                    with st.container(border=True):
                        st.success("✅ Análisis Completado")
                        
                        if score_val >= 90:
                            st.metric(label="IRC Score", value=score_val, delta=nivel_val)
                            st.error("⚠️ RIESGO CRÍTICO - Prioridad Máxima")
                        elif score_val >= 70:
                            st.metric(label="IRC Score", value=score_val, delta=nivel_val)
                            st.warning("🟧 RIESGO ALTO - Prioridad Alta")
                        elif score_val >= 40:
                            st.metric(label="IRC Score", value=score_val, delta=nivel_val)
                            st.info("🟦 RIESGO MEDIO - Prioridad Media")
                        else:
                            st.metric(label="IRC Score", value=score_val, delta=nivel_val)
                            st.success("🟩 RIESGO BAJO - Control Rutina")
                        
                        st.divider()
                        st.markdown("**Justificación Clínica (IA):**")
                        st.markdown(justificacion_html, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error al llamar a la IA: {e}")
    else:
        st.warning("⚠️ Por favor, ingrese el resumen del paciente.")

st.divider()

# ==========================================
# MODO 2: PROCESAMIENTO MASIVO (ACTUALIZADO)
# ==========================================
st.header("2. Herramienta de Procesamiento Masivo (Gestión)")
st.info("Procesamiento por lotes con priorización inteligente.")

if st.button("Procesar Archivo Completo de Pacientes"):
    
    # Lógica de lectura de archivo robusta
    file_path_xlsx = "casos_pacientes.xlsx"
    file_path_csv = "casos_pacientes.csv"
    df = None

    try:
        df = pd.read_excel(file_path_xlsx)
        st.toast(f"Archivo '{file_path_xlsx}' cargado.", icon="📂")
    except FileNotFoundError:
        try:
            df = pd.read_csv(file_path_csv)
            st.toast(f"Archivo '{file_path_csv}' cargado.", icon="📂")
        except:
            st.error("No se encontró 'casos_pacientes.xlsx' ni .csv en la carpeta.")
            st.stop()
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        st.stop()

    df = df.fillna('N/A')
    
    # Normalización de columnas
    df.columns = df.columns.str.upper().str.strip()
    
    req_cols = ['ID', 'DEMOGRAFÍA', 'PABELLÓN', 'FARMACIA', 'EVENTOS ADVERSOS', 
                'INDICACIÓN MÉDICA', 'HOSPITALIZACIÓN', 'ATENCIÓN AMBULATORIA', 
                'LISTA DE ESPERA CONSULTA NUEVA']
    
    missing = [c for c in req_cols if c not in df.columns]
    if missing:
        st.error(f"Faltan columnas en el Excel: {missing}")
        st.stop()
    
    results_list = []
    progress_bar = st.progress(0, text="Iniciando motor de IA...")
    
    total_rows = len(df)
    
    for index, row in df.iterrows():
        # Construcción del prompt masivo
        texto_masivo = f"""
        [ID] {row['ID']}
        [DEMOGRAFÍA] {row['DEMOGRAFÍA']}
        [PABELLÓN] {row['PABELLÓN']}
        [FARMACIA] {row['FARMACIA']}
        [EVENTOS ADVERSOS] {row['EVENTOS ADVERSOS']}
        [INDICACIÓN MÉDICA] {row['INDICACIÓN MÉDICA']}
        [HOSPITALIZACIÓN] {row['HOSPITALIZACIÓN']}
        [ATENCIÓN AMBULATORIA] {row['ATENCIÓN AMBULATORIA']}
        [LISTA DE ESPERA CONSULTA NUEVA] {row['LISTA DE ESPERA CONSULTA NUEVA']}
        """
        
        try:
            data = get_irc_from_ia(texto_masivo)
            results_list.append({
                'ID': row['ID'], 
                'IRC (Score)': int(data["score"]), 
                'Nivel de Riesgo': data["nivel"],
                'Justificación (IA)': " | ".join(data["justificacion"])
            })
        except Exception as e:
            results_list.append({'ID': row['ID'], 'IRC (Score)': -1, 'Nivel de Riesgo': 'Error', 'Justificación (IA)': f"Error: {e}"})
        
        progress_bar.progress((index + 1) / total_rows, text=f"Procesando ID: {row['ID']}")

    progress_bar.empty()
    st.success("¡Procesamiento completado!")
    
    # --- ORDENAR Y COLOREAR ---
    
    # 1. Crear DataFrame
    df_results = pd.DataFrame(results_list)
    
    # 2. Ordenar de MAYOR A MENOR Riesgo (Lo más grave arriba)
    df_results = df_results.sort_values(by='IRC (Score)', ascending=False)
    
    # 3. Función Semáforo
    def color_risk(val):
        if isinstance(val, int):
            if val >= 90:
                return 'background-color: #ff4b4b; color: white; font-weight: bold;' # Rojo
            elif val >= 70:
                return 'background-color: #ffa500; color: black; font-weight: bold;' # Naranja
            elif val >= 40:
                return 'background-color: #8ecae6; color: black; font-weight: bold;' # Azul
            elif val >= 0:
                return 'background-color: #90ee90; color: black; font-weight: bold;' # Verde
        return ''

    # 4. Mostrar Tabla con Estilos
    st.dataframe(
        df_results.style.map(color_risk, subset=['IRC (Score)']),
        use_container_width=True,
        hide_index=True
    )
