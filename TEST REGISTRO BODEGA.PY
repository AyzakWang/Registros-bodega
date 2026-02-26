import pdfplumber
import requests
import time
import os
import re
import keyboard

# --- CONFIGURACIÓN ---
FOLDER_TO_WATCH = r"G:\GUIA DE DESPACHO"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxmKBElpiFfMfXFUK1AzRbnZkjJTz6Y-WR5NVZCTufHZKo4Z-Lr0bH4KNz6OJADAWvr/exec"
HISTORIAL_FILE = r"P:\PLANTILLA CAJONES BODEGA\AutoHotkey\REGISTROS BODEGA\historial_procesados.txt"
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
        if etiqueta == "CHOFER : ":
            resultado = re.sub(r'\s\d+$', '', resultado)
        if etiqueta == "PATENTE : ":
            limpio = resultado.replace("-", "").replace(" ", "").upper()
            match = re.match(r"([A-Z]+)([0-9]+)", limpio)
            if match:
                resultado = f"{match.group(1)}-{match.group(2)}"
        return resultado
    except: return "Error"

def process_pdf(path, es_reverificacion=False):
    try:
        nombre_archivo = os.path.basename(path)
        partes = nombre_archivo.split('_')
        num_guia_nombre = partes[3] 
        
        timestamp_raw = partes[-1].replace(".pdf", "")
        fecha_hora = timestamp_raw.split('T')
        f = fecha_hora[0]
        fecha_formateada = f"{f[6:8]}-{f[4:6]}-{f[0:4]}"
        h = fecha_hora[1]
        hora_formateada = f"{h[0:2]}:{h[2:4]}"

        with pdfplumber.open(path) as pdf:
            text = pdf.pages[0].extract_text()
            tipo_traslado = "VENTA" if "Operación constituye venta" in text else "SERVICIO" if "Otros traslados no venta" in text else "OTRO"
            tipo_despacho = "DESPACHO" if "Desp. por cuenta del emisor a Inst. Cliente" in text else "ENTREGADO" if "Despacho por cuenta del Cliente" in text else "OTRO"

            datos = {
                "rut": extraer(text, "R.U.T. : "),      
                "senores": extraer(text, "SEÑOR(ES) : "), 
                "chofer": extraer(text, "CHOFER : "),    
                "patente": extraer(text, "PATENTE : "),  
                "num_guia": num_guia_nombre,
                "oc": extraer(text, "Orden de Compra ") if "Orden de Compra " in text else "S/OC",
                "nv": extraer(text, "Nota de Venta ") if "Nota de Venta " in text else "S/NV", 
                "fecha": fecha_formateada, 
                "hora": hora_formateada,
                "traslado": tipo_traslado,
                "despacho": tipo_despacho,
                "modo_verificacion": es_reverificacion 
            }
        
            response = requests.post(WEB_APP_URL, json=datos, timeout=15)
            return response.text
    except Exception as e:
        return f"Error Local: {str(e)}"

# --- CICLO PRINCIPAL ---
print(f"MONITOR ACTIVO. Sincronización cada {REINICIO_MEMORIA_MINUTOS} min.")
print(">>> ESC para salir. <<<")

procesados_en_esta_sesion = set()
ultima_limpieza = time.time() - (REINICIO_MEMORIA_MINUTOS * 60) 

while True:
    if keyboard.is_pressed('esc'):
        print("\n[!] Cerrando monitor...")
        break

    try:
        tiempo_actual = time.time()
        
        # --- BLOQUE 1: SINCRONIZACIÓN (Faltantes en Sheets) ---
        if (tiempo_actual - ultima_limpieza) > (REINICIO_MEMORIA_MINUTOS * 60):
            print("\n--- [SINCRO] COMPROBANDO CON GOOGLE SHEETS... ---")
            try:
                res_google = requests.get(WEB_APP_URL, timeout=15)
                guias_en_sheets = set(res_google.json())
                
                historial_fijo = cargar_historial_fijo()
                archivos_en_carpeta = os.listdir(FOLDER_TO_WATCH)
                
                for archivo in archivos_en_carpeta:
                    if not archivo.endswith(".pdf") or "CEDIBLE" not in archivo.upper(): continue
                    
                    num_guia = archivo.split('_')[3]
                    if num_guia not in guias_en_sheets:
                        print(f"[!] RECUPERANDO GUÍA FALTANTE: {num_guia}")
                        res = process_pdf(os.path.join(FOLDER_TO_WATCH, archivo), es_reverificacion=True)
                        # Si se recuperó con éxito, lo añadimos a procesados para que el Bloque 2 no la repita
                        if "Recuperada" in res or "Ingreso" in res:
                            procesados_en_esta_sesion.add(archivo)
                
                ultima_limpieza = time.time()
                print("--- [SINCRO] FINALIZADA (Todo al día) ---\n")
            except Exception as e:
                print(f"Error en Sincro: {e}")

        # --- BLOQUE 2: MONITOR DE ARCHIVOS NUEVOS (Recién llegados) ---
        archivos = os.listdir(FOLDER_TO_WATCH)
        # Buscamos archivos que NO estén en la sesión actual
        pendientes = [a for a in archivos if a.endswith(".pdf") and "CEDIBLE" in a.upper() and a not in procesados_en_esta_sesion]
        
        if pendientes:
            for archivo_actual in pendientes:
                if keyboard.is_pressed('esc'): break
                
                resultado = process_pdf(os.path.join(FOLDER_TO_WATCH, archivo_actual))
                
                if "Ingreso exitoso" in resultado:
                    print(f"-> OK: {archivo_actual} | Ingreso exitoso")
                elif "Error: Guía duplicada" in resultado:
                    # Si es duplicada, la ignoramos silenciosamente pero la marcamos para no re-intentar
                    pass
                else:
                    print(f"-> AVISO: {archivo_actual} | {resultado}")
                
                procesados_en_esta_sesion.add(archivo_actual)
                
                # Actualizar el archivo de texto histórico
                historial_actual = cargar_historial_fijo()
                if archivo_actual not in historial_actual:
                    with open(HISTORIAL_FILE, "a") as f:
                        f.write(archivo_actual + "\n")
                    
        time.sleep(2) # Pausa pequeña para no saturar el procesador
    except Exception as e:
        print(f"Error General: {e}")
        time.sleep(5)