import streamlit as st
import google.generativeai as genai
import pandas as pd  
import json
import re
import time
from google.generativeai.types import HarmCategory, HarmBlockThreshold # Importa los settings de seguridad

# --- SOLUCIÓN (LÍNEA NUEVA) ---
# Esto DEBE ser el *primer* comando de Streamlit que ejecutas.
# Le dice a la app que use todo el ancho de la página.
st.set_page_config(layout="wide")
# --- FIN DE LA SOLUCIÓN ---

# --- CONFIGURACIÓN DE LA IA (El Cerebro) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-flash-latest')
except Exception as e:
    st.error(f"Error al configurar la API de Google. ¿Creaste el archivo .streamlit/secrets.toml? Error: {e}")
    st.stop() 

# --- FUNCIÓN DE LLAMADA A LA IA (Para no repetir código) ---
def get_irc_from_ia(texto_paciente):
    prompt_template = f"""
    ACTÚA COMO: Un médico especialista senior y un ingeniero de riesgos clínicos del Hospital Padre Hurtado.
    
    TAREA: Evaluar el siguiente resumen de paciente anonimizado. Tu misión es generar un "Índice de Riesgo Clínico" (IRC) de 0 a 100 y una justificación clara.
    
    REGLAS DE EVALUACIÓN:
    - **Riesgo Crítico (90-100):** Cirugía compleja recente (<30 días) + eventos adversos (Urgencia/MAE) + polifarmacia de riesgo (anticoagulantes, quimio, insulina). Pacientes oncológicos descompensados.
    - **Riesgo Alto (70-89):** Cirugía reciente O eventos adversos O polifarmacia de riesgo. Vulnerabilidad demográfica (ej. vive solo, edad avanzada).
    - **Riesgo Medio (40-69):** Paciente crónico (DM2, HTA) con cirugía programada pasada (ej. > 2 meses) pero estable.
    - **Riesgo Bajo (0-39):** Paciente estable, crónico controlado, o consulta de rutina.
    
    FORMATO DE SALIDA (OBLIGORIO):
    Debes responder *únicamente* con un objeto JSON válido, sin ningún texto antes o después. La estructura debe ser:
    {{
      "score": <score numérico>,
      "nivel": "<nivel de riesgo>",
      "justificacion": [
        "<Primera justificación (sin asterisco)>",
        "<Segunda justificación (sin asterisco)>"
      ]
    }}
    
    RESUMEN DEL PACIENTE A EVALUAR:
    "{texto_paciente}"
    """
    
    # Ajustes de seguridad para evitar bloqueos de contenido clínico
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # Llamamos al modelo con los ajustes de seguridad
    response = model.generate_content(
        prompt_template,
        safety_settings=safety_settings
    )
    
    clean_text = re.sub(r"```json\n?|```", "", response.text.strip())
    data = json.loads(clean_text)
    return data 

# --- INTERFAZ DE USUARIO ---

st.title("PRIOR-IA: Índice de Riesgo Clínico (IRC)")
st.subheader("Prototipo calculo IRC Salud a la vanguardIA Hospital Padre Hurtado")

# --- MODO 1: CONSULTA INDIVIDUAL ---
st.header("1. Herramienta de Consulta Individual (Clínico)")
resumen_paciente = st.text_area(
    "Resumen del Paciente", 
    placeholder="Pegue aquí el resumen sintético del paciente...",
    height=200 
)

if st.button("Calcular IRC Individual"): 
    if resumen_paciente: 
        with st.spinner("Analizando paciente y calculando IRC..."):
            try:
                data = get_irc_from_ia(resumen_paciente)
                
                score_val = int(data["score"])
                nivel_val = data["nivel"]
                justificacion_lista = data["justificacion"]
                justificacion_val = "\n".join(f"* {item}" for item in justificacion_lista)
                
                st.success("IRC Calculado exitosamente")
                if score_val >= 90:
                    st.metric(label="IRC Score (0-100)", value=score_val, delta=nivel_val + " (Crítico)")
                elif score_val >= 70:
                    st.metric(label="IRC Score (0-100)", value=score_val, delta=nivel_val)
                else:
                    st.metric(label="IRC Score (0-100)", value=score_val, delta=nivel_val)
                st.subheader("Justificación del Riesgo (Generada por IA)")
                st.info(justificacion_val)
            except Exception as e:
                st.error(f"Error al llamar o procesar la respuesta de la IA. Error técnico: {e}")
    else:
        st.error("Por favor, ingrese el resumen del paciente.")

# --- LÍNEA DIVISORIA ---
st.divider()

# --- MODO 2: PROCESAMIENTO MASIVO ---
st.header("2. Herramienta de Procesamiento Masivo (Gestión)")
st.info("Esta sección lee el archivo `casos_pacientes.xlsx` (o `.csv`) de la carpeta raíz.")

if st.button("Procesar Archivo Completo de Pacientes"):
    
    file_path_xlsx = "casos_pacientes.xlsx"
    file_path_csv = "casos_pacientes.csv" 
    df = None

    try:
        df = pd.read_excel(file_path_xlsx)
        st.info(f"Archivo '{file_path_xlsx}' leído exitosamente.")
    except FileNotFoundError:
        st.warning(f"No se encontró '{file_path_xlsx}', intentando leer '{file_path_csv}'...")
        try:
            df = pd.read_csv(file_path_csv)
            st.info(f"Archivo '{file_path_csv}' leído exitosamente.")
        except FileNotFoundError:
            st.error(f"Error: No se encontró ni '{file_path_xlsx}' ni '{file_path_csv}'. Asegúrate de que el archivo esté en la carpeta.")
            st.stop()
        except Exception as e:
            st.error(f"Error al leer el archivo CSV: {e}")
            st.stop()
    except Exception as e:
        st.error(f"Error al leer el archivo Excel: {e}")
        st.stop()

    df = df.fillna('N/A') 
    
    df.columns = df.columns.str.upper().str.strip() 
    
    columnas_requeridas = ['ID', 'DEMOGRAFÍA', 'PABELLÓN', 'FARMACIA', 'EVENTOS ADVERSOS', 
                           'INDICACIÓN MÉDICA', 'HOSPITALIZACIÓN', 'ATENCIÓN AMBULATORIA', 
                           'LISTA DE ESPERA CONSULTA NUEVA']
    
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    
    if columnas_faltantes:
        st.error(f"Error Crítico: Faltan las siguientes columnas (ya normalizadas) en tu archivo: {columnas_faltantes}")
        st.error("Por favor, renombra las columnas en tu archivo Excel/CSV para que coincidan exactamente.")
        st.stop()
    
    results_list = []
    progress_bar = st.progress(0, text="Iniciando procesamiento masivo...")
    
    st.warning("Procesando múltiples pacientes. Esto puede tardar...", icon="⏳")
    
    for index, row in df.iterrows():
        
        texto_paciente_masivo = f"""
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
            data = get_irc_from_ia(texto_paciente_masivo)
            
            results_list.append({
                'ID': row['ID'], 
                'IRC (Score)': int(data["score"]), 
                'Nivel de Riesgo': data["nivel"],
                'Justificación (IA)': " / ".join(data["justificacion"]) 
            })
            
        except Exception as e:
            st.error(f"Error procesando ID {row['ID']}: {e}")
            results_list.append({
                'ID': row['ID'], 
                'IRC (Score)': -1, 
                'Nivel de Riesgo': "Error de Procesamiento",
                'Justificación (IA)': str(e)
            })
        
        progress_bar.progress((index + 1) / len(df), text=f"Procesando paciente: {row['ID']} ({index+1}/{len(df)})")

    progress_bar.empty() 
    st.success("¡Procesamiento masivo completado!")

    results_df = pd.DataFrame(results_list)
    
    st.subheader("Resultados del Procesamiento Masivo")
    st.dataframe(results_df, use_container_width=True) # <-- use_container_width ahora funcionará bien
