import pdfplumber
import requests
import time
import os
import re
import keyboard
import sys
from pathlib import Path

# =============================================================================
# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES ---
# =============================================================================
FOLDER_TO_WATCH = Path(r"G:\GUIA DE DESPACHO")
WEB_APP_URL     = "https://script.google.com/macros/s/AKfycbwIDp_qHkYeJSnF74itwMDqD_cdiKGowfSKew5N9GqOCRZmUTSeJEV7NKlggiAtzXAo/exec"
HISTORIAL_FILE  = Path(r"C:\Users\attexnet22\Documents\PLANTILLA CAJONES BODEGA\AutoHotkey\REGISTROS BODEGA\historial_procesados.txt")

REINICIO_MEMORIA_MINUTOS = 1 

MAPA_PREPARADORES = {
    "V.C.": "VICTOR CASTILLO", "J.O.": "JEFFERSON OLIVOS", "B.O.": "BENITO OVALLE",
    "E.V.": "EDUARDO VILLAGRA", "L.C.": "LUIS CURIN", "C.J.": "CARLOS JARA",
    "F.G.": "FABIAN GONZALEZ", "I.C.": "ISSAAC CROT", "J.A.": "JUAN ALVAREZ",
    "P.S.": "PEDRO SAENZ", "C.R.": "CRISTIAN RIVEROS"
}

class MonitorBodega:
    def __init__(self):
        self.running = True
        self.ultima_sincro_sheets = 0
        # MEMORIA VOLATIL: Guardamos archivos que YA sabemos que son duplicados para saltarlos
        self.ya_identificados_como_duplicados = set()
        self.configurar_atajos()

    def configurar_atajos(self):
        keyboard.add_hotkey('f12', self.salir, suppress=True)

    def salir(self):
        print("\n>>> CERRANDO SISTEMA...")
        self.running = False

    def guardar_en_historial(self, nombre_archivo):
        try:
            HISTORIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORIAL_FILE, "a", encoding="utf-8") as f:
                f.write(f"{nombre_archivo}\n")
        except: pass

    def buscar_preparador_en_texto(self, texto_pdf):
        texto_up = texto_pdf.upper()
        match = re.search(r"PREPARADOR:?\s*([A-Z\.]+)", texto_up)
        if match:
            posible = match.group(1).strip()
            if posible in MAPA_PREPARADORES: return MAPA_PREPARADORES[posible]
        for acro, nombre in MAPA_PREPARADORES.items():
            if acro in texto_up.replace(" ", ""): return nombre
        return "SIN PREPARADOR"

    def extraer_con_regex(self, texto, etiqueta):
        patron = rf"{re.escape(etiqueta)}(.*?)(?=FECHA EMISION|HES|TELEFONO|VENCIMIENTO|COMUNA|O/C|Tipo Documento|Folio Ref|Nota de Venta|\n|$)"
        match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if not match: return "SIN DATOS"
        res = match.group(1).replace(":", "").replace('"', '').strip()
        if "PATENTE" in etiqueta:
            limpio = re.sub(r'[^A-Z0-9]', '', res.upper())
            m = re.match(r"([A-Z]{2,4})([0-9]{2,4})", limpio)
            if m: res = f"{m.group(1)}-{m.group(2)}"
        return res

    def process_pdf(self, path, es_reverificacion=False):
        try:
            partes = path.name.split('_')
            if len(partes) < 4: return
            num_guia = partes[3]
            
            # Si es un escaneo normal y ya sabemos que es duplicado, ni lo intentamos
            if not es_reverificacion and path.name in self.ya_identificados_como_duplicados:
                return

            ts = partes[-1].replace(".pdf", "")
            f, h = ts.split('T')
            
            with pdfplumber.open(path) as pdf:
                text = pdf.pages[0].extract_text() or ""
                datos = {
                    "rut": self.extraer_con_regex(text, "R.U.T. : "),
                    "senores": self.extraer_con_regex(text, "SEÑOR(ES) : "),
                    "chofer": self.extraer_con_regex(text, "CHOFER : "),
                    "patente": self.extraer_con_regex(text, "PATENTE : "),
                    "num_guia": num_guia,
                    "oc": self.extraer_con_regex(text, "Orden de Compra ") if "Orden de Compra" in text else "S/OC",
                    "nv": self.extraer_con_regex(text, "Nota de Venta ") if "Nota de Venta" in text else "S/NV",
                    "fecha": f"{f[6:8]}-{f[4:6]}-{f[0:4]}", "hora": f"{h[0:2]}:{h[2:4]}",
                    "traslado": "VENTA" if "VENTA" in text.upper() else "SERVICIO",
                    "despacho": "DESPACHO" if "EMISOR" in text.upper() else "ENTREGADO",
                    "preparador": self.buscar_preparador_en_texto(text),
                    "modo_verificacion": es_reverificacion
                }
                
                resp = requests.post(WEB_APP_URL, json=datos, timeout=20)
                resultado = resp.text

                if "Ingreso exitoso" in resultado:
                    print(f"✅ GUÍA INGRESADA: {num_guia}")
                    self.guardar_en_historial(path.name)
                    # Si se ingresó, lo quitamos de la lista de duplicados por si acaso
                    self.ya_identificados_como_duplicados.discard(path.name)
                elif "Sincronizado" in resultado:
                    print(f"🔄 GUÍA RESTAURADA (Estaba borrada del Sheets): {num_guia}")
                elif "Duplicado" in resultado:
                    # Lo guardamos en memoria para no volver a procesarlo en este ciclo
                    self.ya_identificados_como_duplicados.add(path.name)
                    
        except Exception:
            pass

    def ejecutar(self):
        print("="*40)
        print(">>> MONITOR DE BODEGA PRIORITARIO ACTIVO <<<")
        print("="*40)
        
        while self.running:
            ahora = time.time()
            
            # 1. ESCANEO PRIORITARIO: Ordenamos por FECHA DE MODIFICACIÓN (MÁS NUEVOS PRIMERO)
            try:
                # Obtenemos lista de archivos .pdf que contienen CEDIBLE
                archivos = [f for f in FOLDER_TO_WATCH.glob("*.pdf") if "CEDIBLE" in f.name.upper()]
                # ORDENAR: El más reciente primero
                archivos.sort(key=lambda x: x.stat().st_mtime, reverse=True)

                for archivo in archivos:
                    if not self.running: break
                    # Intentar procesar. Si es duplicado, process_pdf lo anotará y lo saltará después.
                    self.process_pdf(archivo)
                    
            except Exception as e:
                print(f"Error en escaneo prioritario: {e}")

            # 2. SINCRONIZACIÓN: Solo si se borró algo del Sheets
            if (ahora - self.ultima_sincro_sheets) > (REINICIO_MEMORIA_MINUTOS * 60):
                self.ultima_sincro_sheets = ahora
                # Limpiamos memoria de duplicados cada minuto para obligar a re-chequear
                self.ya_identificados_como_duplicados.clear() 
                
                try:
                    res = requests.get(WEB_APP_URL, timeout=25)
                    if res.status_code == 200:
                        guias_en_nube = set(res.json())
                        # Solo procesamos archivos que NO están en la lista del Sheets
                        for archivo in archivos:
                            partes = archivo.name.split('_')
                            if len(partes) > 3 and partes[3] not in guias_en_nube:
                                self.process_pdf(archivo, es_reverificacion=True)
                except: pass

            time.sleep(1)

if __name__ == "__main__":
    monitor = MonitorBodega()
    monitor.ejecutar()