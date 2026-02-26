import pdfplumber
import requests
import time
import os
import re  # Importamos re para limpiar números sobrantes y formatear patentes

# --- CONFIGURACIÓN ---
FOLDER_TO_WATCH = r"C:\Users\123\Documents\PLANTILLA CAJONES BODEGA\PLANTILLA CAJONES BODEGA\AutoHotkey\REGISTRO BODEGA\TEST REGISTRO BODEGA GUIAS"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbx6ls-HE1ZC_-5SLv7KTuBHv9QImQtM5q2yG1ngvWiR22mL6d_v4zAMMvgErOJ4btuL/exec"

# Se define la ruta completa para el archivo de historial en la carpeta solicitada
HISTORIAL_FILE = r"C:\Users\123\Documents\PLANTILLA CAJONES BODEGA\PLANTILLA CAJONES BODEGA\AutoHotkey\REGISTRO BODEGA\historial_procesados.txt"

# --- AJUSTE PARA TESTEO ---
REINICIO_MEMORIA_MINUTOS = 1 

def cargar_historial_fijo():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def extraer(texto, etiqueta):
    try:
        if etiqueta not in texto: return "No encontrado"
        parte = texto.split(etiqueta)[1].split('\n')[0]
        
        frenos = ["FECHA EMISION", "HES", "TELEFONO", "VENCIMIENTO", "COMUNA", "O/C", "Tipo Documento", "Folio Ref"]
        if "Nota de Venta" in texto:
            frenos.append("Nota de Venta")
            
        for freno in frenos:
            if freno in parte: parte = parte.split(freno)[0]
        
        resultado = parte.replace(":", "").replace('"', '').strip()
        
        # --- LÓGICA PARA EL CHOFER ---
        if etiqueta == "CHOFER : ":
            resultado = re.sub(r'\s\d+$', '', resultado)
            
        # --- LÓGICA PARA LA PATENTE (Formato TEXTO-NUMERO) ---
        if etiqueta == "PATENTE : ":
            # Eliminamos cualquier guion o espacio previo para normalizar
            limpio = resultado.replace("-", "").replace(" ", "").upper()
            # Buscamos la división entre letras y números
            match = re.match(r"([A-Z]+)([0-9]+)", limpio)
            if match:
                resultado = f"{match.group(1)}-{match.group(2)}"
            
        return resultado
    except: return "Error"

def process_pdf(path, historial_fijo):
    try:
        nombre_archivo = os.path.basename(path)
        partes = nombre_archivo.split('_')
        num_guia_nombre = partes[3] 

        # --- OPTIMIZACIÓN: Si ya está en el historial fijo, enviamos datos mínimos sin abrir el PDF ---
        if nombre_archivo in historial_fijo:
            datos_rapidos = {"num_guia": num_guia_nombre, "modo_verificacion": True}
            response = requests.post(WEB_APP_URL, json=datos_rapidos, timeout=15)
            return response.text

        # Si es nuevo, procedemos con el escaneo normal
        timestamp_raw = partes[-1].replace(".pdf", "")
        fecha_hora = timestamp_raw.split('T')
        f = fecha_hora[0]
        fecha_formateada = f"{f[6:8]}-{f[4:6]}-{f[0:4]}"
        h = fecha_hora[1]
        hora_formateada = f"{h[0:2]}:{h[2:4]}"

        with pdfplumber.open(path) as pdf:
            text = pdf.pages[0].extract_text()
            oc_extraida = extraer(text, "Orden de Compra ")
            nv_extraida = extraer(text, "Nota de Venta ")
            
            datos = {
                "rut": extraer(text, "R.U.T. : "),      
                "senores": extraer(text, "SEÑOR(ES) : "), 
                "chofer": extraer(text, "CHOFER : "),    
                "patente": extraer(text, "PATENTE : "),  
                "num_guia": num_guia_nombre,
                "oc": oc_extraida if oc_extraida != "No encontrado" else "S/O",
                "nv": nv_extraida if nv_extraida != "No encontrado" else "S/NV", 
                "fecha": fecha_formateada, 
                "hora": hora_formateada
            }
            
            response = requests.post(WEB_APP_URL, json=datos, timeout=15)
            return response.text
    except:
        return "Error Local"

# --- INICIO DEL SISTEMA ---
print(f"MONITOR ACTIVO. Re-verificación completa cada {REINICIO_MEMORIA_MINUTOS} min.")

procesados_en_esta_sesion = set()
ultima_limpieza = time.time()
historial_fijo = cargar_historial_fijo()

while True:
    try:
        tiempo_actual = time.time()
        if (tiempo_actual - ultima_limpieza) > (REINICIO_MEMORIA_MINUTOS * 60):
            print("\n--- [TEST] RE-VERIFICANDO CARPETA COMPLETA CONTRA SHEETS ---")
            procesados_en_esta_sesion.clear()
            ultima_limpieza = tiempo_actual

        archivos = os.listdir(FOLDER_TO_WATCH)
        pendientes = [a for a in archivos if a.endswith(".pdf") and "CEDIBLE" in a.upper() and a not in procesados_en_esta_sesion]
        
        if pendientes:
            for archivo_actual in pendientes:
                resultado = process_pdf(os.path.join(FOLDER_TO_WATCH, archivo_actual), historial_fijo)
                print(f"-> Archivo: {archivo_actual} | Sheets dice: {resultado}")
                
                procesados_en_esta_sesion.add(archivo_actual)
                
                if archivo_actual not in historial_fijo:
                    with open(HISTORIAL_FILE, "a") as f:
                        f.write(archivo_actual + "\n")
                    historial_fijo.add(archivo_actual)
        
        time.sleep(5) 
            
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)