import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

import keyboard
import pdfplumber
import requests

# configure logging once at import time
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# =============================================================================
# --- CONFIGURACIÓN DE RUTAS Y CONSTANTES ---
# =============================================================================
FOLDER_TO_WATCH = Path(r"G:\GUIA DE DESPACHO")
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyThK7Z0xWnZu9ipX-g98ui1rXcVyWgmlIaSXwKDrz5tMAJVdUWLRlyJ3W2JhkdOK0y/exec"
HISTORIAL_FILE = Path(r"C:\Users\attexnet22\Documents\PLANTILLA CAJONES BODEGA\AutoHotkey\REGISTROS BODEGA\historial_procesados.txt")

REINICIO_MEMORIA_MINUTOS = 1
REQUEST_TIMEOUT = 20  # segundos para las llamadas a la API

# frases clave para determinar traslado
RE_TRASLADO_VENTA = re.compile(r"OPERACIÓN CONSTITUYE VENTA", re.IGNORECASE)
RE_TRASLADO_SERVICIO = re.compile(r"OTROS TRASLADOS NO VENTA", re.IGNORECASE)

MAPA_PREPARADORES = {
    "V.C.": "VICTOR CASTILLO", "J.O.": "JEFFERSON OLIVOS", "B.O.": "BENITO OVALLE",
    "E.V.": "EDUARDO VILLAGRA", "L.C.": "LUIS CURIN", "C.J.": "CARLOS JARA",
    "F.G.": "FABIAN GONZALEZ", "I.C.": "ISSAAC CROT", "J.A.": "JUAN ALVAREZ",
    "P.S.": "PEDRO SAENZ", "C.R.": "CRISTIAN RIVEROS",
}

class MonitorBodega:
    def __init__(self) -> None:
        # flags y contadores
        self.running: bool = True
        self.ultima_sincro_sheets: float = 0.0
        self.last_skipped_count: int = 0

        # memoria de archivos ya vistos
        self.ya_identificados_como_duplicados: set[str] = set()
        self.historial_numeros: set[str] = set()
        self.guias_en_nube: set[str] = set()
        self.current_processing: Optional[str] = None

        # sesión HTTP reutilizable
        self.session = requests.Session()

        self.cargar_historial()
        self.configurar_atajos()

    def configurar_atajos(self):
        keyboard.add_hotkey('f12', self.salir, suppress=True)

    def salir(self):
        print("\n>>> CERRANDO SISTEMA...")
        self.running = False

    def guardar_en_historial(self, nombre_archivo):
        """Add a processed filename or guide number to the history file and update the in-memory set."""
        try:
            HISTORIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(HISTORIAL_FILE, "a", encoding="utf-8") as f:
                f.write(f"{nombre_archivo}\n")
        except:
            pass
        # actualizar memoria
        if nombre_archivo.isdigit():
            self.historial_numeros.add(nombre_archivo)
        else:
            num = self.extraer_num_guia_de_nombre(nombre_archivo)
            if num:
                self.historial_numeros.add(num)

    def cargar_historial(self):
        """Load historial_procesados.txt and populate historial_numeros.

        The file can contain full filenames or just guide numbers (one per line).
        """
        if not HISTORIAL_FILE.exists():
            return
        try:
            with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    nombre = line.strip()
                    if not nombre:
                        continue
                    # Si la línea es sólo dígitos, lo consideramos un número de guía
                    if nombre.isdigit():
                        self.historial_numeros.add(nombre)
                        continue
                    num = self.extraer_num_guia_de_nombre(nombre)
                    if num:
                        self.historial_numeros.add(num)
        except Exception:
            pass

    def extraer_num_guia_de_nombre(self, nombre_archivo):
        partes = nombre_archivo.split('_')
        if len(partes) >= 4:
            return partes[3]
        return None

    def informe_comparacion_historial_sheets(self, guias_en_nube):
        """Imprime en terminal un informe entre el historial y los datos de Google Sheets.

        - guias_en_nube: conjunto de números de guía que actualmente figuran en Sheets
        """
        hist = self.historial_numeros
        if not hist:
            print("ℹ️ Historial vacío (todavía no se han registrado archivos).")
            return
        solo_hist = hist - guias_en_nube
        solo_sheets = guias_en_nube - hist
        ambos = hist & guias_en_nube
        print("\n--- INFORME DE SINCRONIZACIÓN ---")
        print(f"Historial contiene {len(hist)} guías")
        print(f"Sheets contiene {len(guias_en_nube)} guías")
        print(f"Guías en ambos: {len(ambos)}")
        if solo_hist:
            print(f"Guías en historial pero NO en sheets ({len(solo_hist)})")
        if solo_sheets:
            print(f"Guías en sheets pero NO en historial ({len(solo_sheets)}): {', '.join(sorted(solo_sheets))}")
        # añadir estado de procesamiento actual si existe
        if getattr(self, 'current_processing', None):
            print(f"Procesando ahora guía: {self.current_processing}")
        print("--- fin del informe ---\n")

    def actualizar_historial_desde_sheets(self, guias_en_nube):
        """Agregar al historial local cualquier guía que esté en Sheets pero falte en el archivo."""
        faltantes = guias_en_nube - self.historial_numeros
        if not faltantes:
            return
        print(f"🔄 Añadiendo {len(faltantes)} guías faltantes al historial (desde Sheets).")
        for num in sorted(faltantes):
            # escribimos sólo el número para no inventar nombre de archivo
            self.guardar_en_historial(num)

    def buscar_preparador_en_texto(self, texto_pdf: str) -> str:
        """Intenta extraer abreviatura de preparador y devolver nombre completo."""
        texto_up = texto_pdf.upper()
        match = re.search(r"PREPARADOR:?\s*([A-Z\.]+)", texto_up)
        if match:
            posible = match.group(1).strip()
            if posible in MAPA_PREPARADORES:
                return MAPA_PREPARADORES[posible]
        for acro, nombre in MAPA_PREPARADORES.items():
            if acro in texto_up.replace(" ", ""):
                return nombre
        return "S/P"

    def extraer_con_regex(self, texto: str, etiqueta: str) -> str:
        """Busca un bloque tras ``etiqueta`` y lo limpia. Devuelve "S/P" si no hay datos."""
        patron = rf"{re.escape(etiqueta)}(.*?)(?=FECHA EMISION|HES|TELEFONO|VENCIMIENTO|COMUNA|O/C|Tipo Documento|Folio Ref|Nota de Venta|\n|$)"
        match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if not match:
            return "S/P"
        res = match.group(1).replace(":", "").replace('"', '').strip()
        if "PATENTE" in etiqueta:
            limpio = re.sub(r'[^A-Z0-9]', '', res.upper())
            m = re.match(r"([A-Z]{2,4})([0-9]{2,4})", limpio)
            if m:
                res = f"{m.group(1)}-{m.group(2)}"
        return res

    # helpers internos --------------------------------------------------------
    def _determinar_traslado(self, texto_up: str) -> str:
        """Devuelve "VENTA" o "SERVICIO" según frases clave en el texto."""
        if RE_TRASLADO_VENTA.search(texto_up):
            return "VENTA"
        if RE_TRASLADO_SERVICIO.search(texto_up):
            return "SERVICIO"
        # fallback
        return "VENTA" if "VENTA" in texto_up else "SERVICIO"

    def _post_to_server(self, datos: dict) -> str:
        """Envia los datos a la API y retorna el texto de la respuesta."""
        try:
            resp = self.session.post(WEB_APP_URL, json=datos, timeout=REQUEST_TIMEOUT)
            return resp.text
        except Exception:
            logging.exception("Error enviando datos a servidor")
            return ""

    def process_pdf(self, path: Path, es_reverificacion: bool = False) -> None:
        try:
            partes = path.name.split('_')
            if len(partes) < 4: return
            num_guia = partes[3]
            self.current_processing = num_guia
            # Saltar si ya está en el historial de procesamiento (salvo cuando es reverificación)
            if num_guia in self.historial_numeros and not es_reverificacion:
                self.current_processing = None
                return
            # Saltar si sabemos que ya figura en Sheets (sin necesidad de consultar al servidor)
            if num_guia in self.guias_en_nube:
                # agregarla al historial para no revisarla otra vez
                self.historial_numeros.add(num_guia)
                return

            # Si es un escaneo normal y ya sabemos que es duplicado, ni lo intentamos
            if not es_reverificacion and path.name in self.ya_identificados_como_duplicados:
                return

            ts = partes[-1].replace(".pdf", "")
            f, h = ts.split('T')
            
            with pdfplumber.open(path) as pdf:
                text = pdf.pages[0].extract_text() or ""
                texto_up = text.upper()
                traslado_val = self._determinar_traslado(texto_up)

                datos = {
                    "rut": self.extraer_con_regex(text, "R.U.T. : "),
                    "senores": self.extraer_con_regex(text, "SEÑOR(ES) : "),
                    "chofer": self.extraer_con_regex(text, "CHOFER : "),
                    "patente": self.extraer_con_regex(text, "PATENTE : "),
                    "num_guia": num_guia,
                    "oc": self.extraer_con_regex(text, "Orden de Compra ") if "Orden de Compra" in text else "S/OC",
                    "nv": self.extraer_con_regex(text, "Nota de Venta ") if "Nota de Venta" in text else "S/NV",
                    "fecha": f"{f[6:8]}-{f[4:6]}-{f[0:4]}", "hora": f"{h[0:2]}:{h[2:4]}",
                    "traslado": traslado_val,
                    "despacho": "DESPACHO" if "EMISOR" in texto_up else "ENTREGADO",
                    "preparador": self.buscar_preparador_en_texto(text),
                    "modo_verificacion": es_reverificacion,
                }
                # aplicar acrónimos cuando no se encontró dato
                if not datos.get("chofer"):
                    datos["chofer"] = "S/C"
                if not datos.get("patente"):
                    datos["patente"] = "S/P"
                if not datos.get("oc"):
                    datos["oc"] = "S/OC"
                if not datos.get("nv"):
                    datos["nv"] = "S/OV"
                if not datos.get("fecha"):
                    datos["fecha"] = "S/F"
                if not datos.get("hora"):
                    datos["hora"] = "S/H"
                if not datos.get("traslado"):
                    datos["traslado"] = "S/T"
                if not datos.get("despacho"):
                    datos["despacho"] = "S/D"
                if not datos.get("preparador"):
                    datos["preparador"] = "S/P"
                
                resultado = self._post_to_server(datos)

                if "Ingreso exitoso" in resultado:
                    logging.info("GUÍA INGRESADA: %s", num_guia)
                    self.guardar_en_historial(path.name)
                    self.ya_identificados_como_duplicados.discard(path.name)
                elif "Sincronizado" in resultado:
                    logging.info("GUÍA RESTAURADA: %s", num_guia)
                elif "Duplicado" in resultado:
                    self.ya_identificados_como_duplicados.add(path.name)
                self.current_processing = None
                    
        except Exception:
            pass

    def ejecutar(self) -> None:
        logging.info("MONITOR DE BODEGA PRIORITARIO ACTIVO")
        try:
            while self.running:
                ahora = time.time()

                # 0. ESCANEO PRELIMINAR: leer archivos disponibles una sola vez
                try:
                    archivos = [f for f in FOLDER_TO_WATCH.glob("*.pdf") if "CEDIBLE" in f.name.upper()]
                    # ordenar de mayor a menor num_guia para que las entradas nuevas se tomen primero
                    def guia_key(f):
                        partes = f.name.split('_')
                        if len(partes) > 3 and partes[3].isdigit():
                            return int(partes[3])
                        return 0
                    archivos.sort(key=guia_key, reverse=True)
                except Exception:
                    logging.exception("Error al listar archivos")
                    archivos = []

                # 2. SINCRONIZACIÓN: siempre chequeamos cerca de los REINICIO_MEMORIA_MINUTOS
                if (ahora - self.ultima_sincro_sheets) >= (REINICIO_MEMORIA_MINUTOS * 60):
                    self.ultima_sincro_sheets = ahora
                    self.ya_identificados_como_duplicados.clear()
                    try:
                        res = self.session.get(WEB_APP_URL, timeout=REQUEST_TIMEOUT)
                        if res.status_code == 200:
                            guias_en_nube = set(res.json())
                            self.guias_en_nube = guias_en_nube
                            self.actualizar_historial_desde_sheets(guias_en_nube)
                            self.informe_comparacion_historial_sheets(guias_en_nube)
                            # resumen físico vs nube
                            numeros_en_dir = {f.name.split('_')[3] for f in archivos if len(f.name.split('_'))>3}
                            ingresadas = numeros_en_dir & (guias_en_nube | self.historial_numeros)
                            faltantes = numeros_en_dir - (guias_en_nube | self.historial_numeros)
                            logging.info(
                                "En carpeta: %d totales; %d ingresadas; %d pendientes",
                                len(numeros_en_dir), len(ingresadas), len(faltantes),
                            )
                            for archivo in archivos:
                                partes = archivo.name.split('_')
                                if len(partes) > 3 and partes[3] not in guias_en_nube:
                                    self.process_pdf(archivo, es_reverificacion=True)
                    except Exception:
                        logging.exception("Error al sincronizar con Sheets")

                # 1. ESCANEO PRIORITARIO: procesar archivos pendientes
                try:

                    numeros_en_dir = {f.name.split('_')[3] for f in archivos if len(f.name.split('_'))>3}
                    ingresadas = numeros_en_dir & (self.guias_en_nube | self.historial_numeros)
                    faltantes = numeros_en_dir - (self.guias_en_nube | self.historial_numeros)
                    # sólo mostramos el mensaje si el conteo de guías omitidas cambió
                    if ingresadas and len(ingresadas) != self.last_skipped_count:
                        logging.info("🔁 Se omitirán %d guías ya ingresadas.", len(ingresadas))
                    # indicar cuántas se van a ingresar este ciclo
                    if faltantes:
                        logging.info("🔁 Se ingresarán %d guías no ingresadas.", len(faltantes))
                        # procesar solo los pendientes e imprimir cada uno
                        mapping = {f.name.split('_')[3]: f for f in archivos if len(f.name.split('_'))>3}
                        # separar guías faltantes: primero las que están en historial, luego las demás
                        # ambas ordenadas de mayor a menor número de guía
                        faltantes_en_hist = sorted([n for n in faltantes if n in self.historial_numeros], reverse=True)
                        faltantes_sin_hist = sorted([n for n in faltantes if n not in self.historial_numeros], reverse=True)
                        # procesar primero las del historial, luego las demás
                        for num in faltantes_en_hist + faltantes_sin_hist:
                            logging.info("🔁 Ingresando guía %s no ingresada.", num)
                            ruta = mapping.get(num)
                            if ruta and self.running:
                                self.process_pdf(ruta)
                        logging.info("--- fin del ingreso de guias---")
                        logging.info("🔁 Buscando guias no ingresadas.")
                    else:
                        # si no hay faltantes, seguir procesando todos
                        for archivo in archivos:
                            if not self.running: break
                            self.process_pdf(archivo)
                    self.last_skipped_count = len(ingresadas)
                except Exception:
                    logging.exception("Error en escaneo prioritario")

                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Interrumpido por usuario, saliendo...")
            print("\n>>> Interrupción de teclado durante ejecución, saliendo bucle.")

# bloque principal con manejo de interrupciones
if __name__ == "__main__":
    try:
        monitor = MonitorBodega()
        monitor.ejecutar()
    except KeyboardInterrupt:
        print("\n>>> Interrupción de teclado detectada en el main, cierre limpio.")