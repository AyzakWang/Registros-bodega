import sys
import os
import logging
import webbrowser
import keyboard
import time
from dataclasses import dataclass
from typing import List, Optional

import pyperclip
import pyautogui
import pygetwindow as gw
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont

# ----------------------------------------------------------------------------
# logging configuration
# ----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(message)s"
)

# ----------------------------------------------------------------------------
# constants / configuration
# ----------------------------------------------------------------------------
COORD_PREPARADOR = (218, 274)
COORD_ACCION = (300, 655)
MIN_DELAY = 0.05
SHORT_DELAY = 0.15
MEDIUM_DELAY = 0.3
LONG_DELAY = 0.5

# factor global de velocidad: <1 acelera, >1 ralentiza
# se multiplica a todos los delays, permite ajustar sin tocar cada llamada
SPEED_FACTOR = 0.5

# ventana target substrings
SAP_TITLES = ["SAP BUSINESS ONE", "MANUAL", "LISTA", "SOLICITUDES"]

# supporting classes

@dataclass
class OptionCfg:
    down: int = 0
    up: int = 0
    down2: int = 0

    def __iter__(self):
        yield from (self.down, self.up, self.down2)


class ClipboardGuard:
    """Context manager that preserves the current clipboard content."""
    def __enter__(self):
        try:
            self._old = pyperclip.paste()
        except Exception:
            self._old = ""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            pyperclip.copy(self._old)
        except Exception:
            logging.exception("Failed to restore clipboard")

# configuraciones predefinidas de opciones (mesa original del autor)
DESP_MANUAL = OptionCfg(1, 4, 0)
TRAS_LISTA = OptionCfg(1, 11, 0)
TRAS_F3 = OptionCfg(1, 11, 5)

# GUI data
PREPARADORES: List[str] = [
    "", "VICTOR CASTILLO [V.C.]", "JEFFERSON OLIVOS [J.O.]", "BENITO OVALLE [B.O.]",
    "EDUARDO VILLAGRA [E.V.]", "LUIS CURIN [L.C.]", "CARLOS JARA [C.J.]",
    "FABIAN GONZALEZ [F.G.]", "ISSAAC CROT [I.C.]", "JUAN ALVAREZ [J.A.]",
    "PEDRO SAENZ [P.S.]", "CRISTIAN RIVEROS [C.R.]",
]
LISTA_CHOFERES: List[str] = [
    "", "EDUARDO VILLAGRA", "CRISTIAN RIVEROS", "CARLOS JARA", "FABIAN GONZALEZ", "ISSAAC CROT", "JUAN ALVAREZ",
]
LISTA_PATENTES: List[str] = ["", "SKXG-70", "SHRB-88", "KRPH-61"]

# =============================================================================
# --- CONFIGURACIÓN DE ENTORNO ---
# =============================================================================
os.environ["QT_LOGGING_RULES"] = "qt.qpa.screen=false;qt.qpa.window=false"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
pyautogui.PAUSE = 0.05 

# =============================================================================
# --- ESTILOS PROFESIONALES (NITRO CSS) ---
# =============================================================================
ESTILO_NITRO = """
    QWidget {
        background-color: #1A1C23;
        color: #E0E0E0;
        font-family: 'Segoe UI', Arial;
    }
    QLabel {
        font-size: 12px;
        font-weight: bold;
        color: #9BA1A6;
        margin-top: 5px;
    }
    QLineEdit, QComboBox {
        background-color: #252833;
        border: 1px solid #3F4451;
        border-radius: 6px;
        padding: 2px 8px;
        color: white;
        font-size: 14px;
        min-height: 28px;
    }
    QLineEdit:focus {
        border: 1px solid #4D90FE;
    }
    QPushButton {
        background-color: #3F4451;
        border: none;
        border-radius: 6px;
        color: white;
        font-weight: bold;
        font-size: 12px;
        height: 32px;
    }
    QPushButton:hover {
        background-color: #4D5363;
    }
    QPushButton#btnAceptar {
        background-color: #0078D4;
    }
    QPushButton#btnAceptar:hover {
        background-color: #1086E8;
    }
    QPushButton#btnEspecial {
        background-color: #2D323E;
        border: 1px solid #3F4451;
    }
    QPushButton#btnEspecial:hover {
        background-color: #3F4451;
        border-color: #4D90FE;
    }
"""

# =============================================================================
# --- CLASES DE SOPORTE ---
# =============================================================================
class KeySignaller(QObject):
    trigger = pyqtSignal(str)

# =============================================================================
# --- NÚCLEO DEL SISTEMA (NITROSYSTEM) ---
# =============================================================================
class NitroSystem:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyleSheet(ESTILO_NITRO)
        self.signaller = KeySignaller()
        self.signaller.trigger.connect(self.handle_signals)
        
        # --- LISTAS DE DATOS ---
        # se cargan desde constantes globales para facilitar mantenimiento
        self.preparadores: List[str] = PREPARADORES
        self.lista_choferes: List[str] = LISTA_CHOFERES
        self.lista_patentes: List[str] = LISTA_PATENTES

        self.crear_interfaces()
        self.configurar_atajos()

        logging.info("SISTEMA ACTIVO (MODO FUNCIONANDO)")
        logging.info("F1-F4: GUIs | Ctrl+1..9: F2..F10 | Ctrl+sc029: Ctrl+Shift+U")

    # -------------------------------------------------------------------------
    # --- CONFIGURACIÓN DE ATAJOS (HOTKEYS) ---
    # -------------------------------------------------------------------------
    def configurar_atajos(self) -> None:
        """Registra atajos globales y letra/teclas especiales."""
        # F keys
        for i in range(1, 5):
            keyboard.add_hotkey(f'f{i}', lambda c=f'f{i}': self.validar_y_enviar(c), suppress=True)
        keyboard.add_hotkey('f12', lambda: self.signaller.trigger.emit('exit'), suppress=True)
        keyboard.on_press_key(41, self._handle_special_key, suppress=True)

        # Ctrl+1..9 mapean a F2..F10
        for n in range(1, 10):
            self._mapear_ctrl_num(n)

        # otros atajos útiles
        keyboard.add_hotkey('print screen', lambda: self.validar_y_enviar_directo('ctrl+p'), suppress=True)
        keyboard.add_hotkey('ctrl+space', lambda: self.validar_y_enviar_directo('ctrl+0'), suppress=True)

    def _handle_special_key(self, event) -> None:
        """Intercepta la tecla sc029 (botón especial) para combinar con Ctrl."""
        if keyboard.is_pressed('ctrl'):
            self.validar_y_enviar_directo('ctrl+shift+u')
        else:
            keyboard.send(41)

    def _mapear_ctrl_num(self, n: int) -> None:
        """Mapea Ctrl+<n> a la tecla F<n+1>."""
        f_key = f'f{n+1}'
        keyboard.add_hotkey(f'ctrl+{n}', lambda k=f_key: self.validar_y_enviar_directo(k), suppress=True)

    # -------------------------------------------------------------------------
    # --- LÓGICA DE VALIDACIÓN DE VENTANAS ---
    # -------------------------------------------------------------------------
    def validar_y_enviar(self, comando: str) -> None:
        """Emite la señal si SAP está activo o es F4 (cerrar)."""
        if self.is_sap_active() or comando == "f4":
            self.signaller.trigger.emit(comando)

    def validar_y_enviar_directo(self, comando: str) -> None:
        """Envía la pulsación directamente si SAP está activo."""
        if self.is_sap_active():
            keyboard.send(comando)

    def validar_y_enviar_chrome(self, comando: str) -> None:
        """Envía un comando si la ventana activa es un navegador Chrome."""
        try:
            active_win = gw.getActiveWindow()
            if active_win and "CHROME" in active_win.title.upper():
                if comando == ":":
                    keyboard.write(":")
                else:
                    keyboard.send(comando)
        except Exception:
            logging.exception("Fallo al validar envío a Chrome")

    def is_sap_active(self) -> bool:
        """Comprueba si la ventana activa parece ser SAP Business One."""
        try:
            active_win = gw.getActiveWindow()
            if active_win:
                title = active_win.title.upper()
                return any(key in title for key in SAP_TITLES)
            return False
        except Exception:
            logging.exception("No pude verificar la ventana activa")
            return False

    # -------------------------------------------------------------------------
    # --- MANEJO DE SEÑALES Y GUI ---
    # -------------------------------------------------------------------------
    def handle_signals(self, comando: str) -> None:
        """Procesa las señales emitidas por los atajos."""
        if comando == "exit":
            self.app.quit()
        elif comando == "f1":
            self.toggle_gui(self.gui_f1)
        elif comando == "f2":
            self.toggle_gui(self.gui_f2)
        elif comando == "f3":
            self.on_aceptar_f3()
        elif comando == "f4":
            self.toggle_gui(self.gui_f4)

    def toggle_gui(self, win: QWidget) -> None:
        """Muestra/oculta una ventana y reinicia campos si es necesario."""
        if win.isVisible():
            win.hide()
        else:
            if win == self.gui_f1:
                self.edit_chofer_man.clear()
                self.edit_patente_man.clear()
                self.cb_preparador_f1.setCurrentIndex(0)
            elif win == self.gui_f2:
                self.ddl_chofer.setCurrentIndex(0)
                self.ddl_patente.setCurrentIndex(0)
                self.cb_preparador_f2.setCurrentIndex(0)
            win.show()
            win.raise_()
            win.activateWindow()

    # -------------------------------------------------------------------------
    # --- LÓGICA DE AUTOMATIZACIÓN (MACROS) ---
    # -------------------------------------------------------------------------
    def run_macro(
        self,
        despCfg: OptionCfg,
        trasCfg: OptionCfg,
        chofer_text: str = "",
        patente_text: str = "",
        preparador_full: str = "",
    ) -> None:
        """Realiza la secuencia de teclas y clics necesaria en SAP.

        ``despCfg`` y ``trasCfg`` describen cómo navegar las listas desplegables.
        El texto del chofer/patente se pega de forma segura usando el portapapeles.
        ``preparador_full`` puede contener un código entre corchetes que se copiará
        al campo correspondiente.
        """
        with ClipboardGuard():
            try:
                active_win = gw.getActiveWindow()
                if active_win and "SAP BUSINESS ONE" in active_win.title.upper():
                    if not active_win.isMaximized:
                        active_win.maximize()

                # --- ACCIÓN PREPARADOR ---
                if preparador_full and "[" in preparador_full:
                    acronimo = preparador_full.split("[")[1].split("]")[0]
                    texto_a_pegar = f"PREPARADOR:{acronimo}"
                    pyautogui.click(*COORD_PREPARADOR)
                    time.sleep(SHORT_DELAY * SPEED_FACTOR)
                    pyperclip.copy(texto_a_pegar)
                    keyboard.press("ctrl")
                    keyboard.press("v")
                    time.sleep(MIN_DELAY * SPEED_FACTOR)
                    keyboard.release("v")
                    keyboard.release("ctrl")
                    time.sleep(MIN_DELAY * SPEED_FACTOR)

                # --- ACCIÓN PRINCIPAL ---
                pyautogui.click(*COORD_ACCION)
                time.sleep(LONG_DELAY * SPEED_FACTOR)

                self.select_option(despCfg)
                keyboard.send("tab")
                time.sleep(SHORT_DELAY * SPEED_FACTOR)
                self.select_option(trasCfg)
                keyboard.send("tab")
                time.sleep(MEDIUM_DELAY * SPEED_FACTOR)

                # helper para pegar texto sin perder el portapapeles
                if chofer_text:
                    logging.debug("pegando chofer: %s", chofer_text)
                    self._safe_paste(chofer_text)
                keyboard.send("tab")
                time.sleep(SHORT_DELAY * SPEED_FACTOR)
                if patente_text:
                    logging.debug("pegando patente: %s", patente_text)
                    self._safe_paste(patente_text)

                for _ in range(3):
                    keyboard.send("tab")
                    time.sleep(MIN_DELAY * SPEED_FACTOR)
                for k in ["down", "up", "up", "down", "down"]:
                    keyboard.send(k)
                    time.sleep(0.08 * SPEED_FACTOR)

                time.sleep(MEDIUM_DELAY * SPEED_FACTOR)
                keyboard.send("enter")
            except Exception:
                logging.exception("Error en macro")

    def select_option(self, cfg: OptionCfg) -> None:
        """Navega en un popup usando la configuración especificada."""
        for _ in range(cfg.down):
            keyboard.send("down")
            time.sleep(MIN_DELAY * SPEED_FACTOR)
        for _ in range(cfg.up):
            keyboard.send("up")
            time.sleep(MIN_DELAY * SPEED_FACTOR)
        for _ in range(cfg.down2):
            keyboard.send("down")
            time.sleep(MIN_DELAY * SPEED_FACTOR)
        time.sleep(SHORT_DELAY * SPEED_FACTOR)
        keyboard.send("enter")

    def _safe_paste(self, texto: str) -> None:
        """Introduce ``texto`` en el campo actual con reintentos.

        La operación se intenta hasta 3 veces. Cada intento realiza:
        1. pegar con ctrl+v
        2. comprobar contenido
        3. si hay error o no coincide, se escribe manualmente y se vuelve a comprobar.
        Si tras los reintentos el campo sigue vacío o incorrecto, se deja lo que
        esté (para evitar bucles infinitos) y se registra un warning.
        """
        txt = str(texto).strip().upper()
        if not txt:
            return

        for attempt in range(1, 4):
            logging.debug("_safe_paste intento %d para '%s'", attempt, txt)

            # asegurarse de que el campo está vacío y tiene foco
            try:
                keyboard.send("ctrl+a")
                time.sleep(MIN_DELAY * SPEED_FACTOR)
                keyboard.send("delete")
                time.sleep(MIN_DELAY * SPEED_FACTOR)
            except Exception:
                logging.debug("falló limpiar campo antes de pegar (intento %d)", attempt)

            # intentar pegar desde portapapeles
            try:
                pyperclip.copy(txt)
                time.sleep(max(0.1, MIN_DELAY * SPEED_FACTOR))
                keyboard.send("ctrl+v")
                time.sleep(max(0.12, MIN_DELAY * SPEED_FACTOR))
            except Exception:
                logging.debug("clipboard paste failed on attempt %d", attempt)

            # comprobar lo que quedó en el campo
            try:
                keyboard.send("ctrl+a")
                time.sleep(MIN_DELAY * SPEED_FACTOR)
                keyboard.send("ctrl+c")
                time.sleep(max(0.08, MIN_DELAY * SPEED_FACTOR))
                campo = (pyperclip.paste() or "").strip().upper()
            except Exception:
                logging.exception("No pude leer el campo en intento %d", attempt)
                campo = ""

            logging.debug("contenido tras intento %d: '%s'", attempt, campo)

            if campo == txt:
                logging.debug("_safe_paste éxito en intento %d", attempt)
                time.sleep(SHORT_DELAY * SPEED_FACTOR)
                return

            # sino, escribir manualmente y reintentar
            keyboard.write(txt, delay=0.01)
            time.sleep(SHORT_DELAY * SPEED_FACTOR)

        # si llegamos aquí, falló varias veces
        logging.warning("_safe_paste no pudo asegurar '%s' en el campo", txt)

    # -------------------------------------------------------------------------
    # --- EVENTOS DE BOTONES ---
    # -------------------------------------------------------------------------
    def on_aceptar_manual(self) -> None:
        c = self.edit_chofer_man.text().upper()
        p = self.edit_patente_man.text().upper()
        pr = self.cb_preparador_f1.currentText()
        if not c or not p:
            return
        self.gui_f1.hide()
        self.run_macro(DESP_MANUAL, TRAS_LISTA, c, p, pr)

    def on_aceptar_lista(self) -> None:
        c = self.ddl_chofer.currentText()
        p = self.ddl_patente.currentText()
        pr = self.cb_preparador_f2.currentText()
        if not c or not p:
            return
        self.gui_f2.hide()
        # segunda tupla difiere sólo en el segundo valor
        self.run_macro(OptionCfg(1, 4, 1), TRAS_LISTA, c, p, pr)

    def on_aceptar_f3(self) -> None:
        # macro sin chofer/patente (sólo navega)
        self.run_macro(OptionCfg(1, 4, 1), TRAS_F3)

    def redactar_gmail(self, tipo: str) -> None:
        """Abre Gmail con el cuerpo pre‑llenado según el tipo de solicitud."""
        cant = self.edit_gas.text() if tipo == "GAS" else self.edit_agua.text()
        if not cant:
            return
        dest = (
            "ysanchez@attex.cl,a.arredondo@attex.cl,f.gonzalez@attex.cl,jalvarez@attex.cl,bodega02@attex.cl"
            if tipo == "GAS"
            else "jneira.attex@gmail.com,recepcionattex@attex.cl,proveedores@attex.cl,jalvarez@attex.cl,f.gonzalez@attex.cl,bodega02@attex.cl"
        )
        asunto = "SOLICITUD DE COMPRA DE GAS" if tipo == "GAS" else "BIDONES DE AGUA BODEGA"
        cuerpo = (
            f"Estimados.%0A%0AFavor gestionar la compra de {cant} "
            f"{'cilindros para grúa horquilla' if tipo == 'GAS' else 'bidones de agua'}.%0A%0AAtte."
        )
        webbrowser.open(
            f"https://mail.google.com/mail/?view=cm&fs=1&to={dest}"
            f"&su={asunto.replace(' ', '%20')}&body={cuerpo}"
        )
        self.gui_f4.hide()

    # -------------------------------------------------------------------------
    # --- CONSTRUCCIÓN DE INTERFACES (GUI FACTORY) ---
    # -------------------------------------------------------------------------
    def crear_interfaces(self):
        # --- GUI F4 ---
        self.gui_f4 = self._crear_base_gui("Solicitudes Attex", 280, 220)
        self._add_titulo(self.gui_f4, "PEDIDOS DE INSUMOS")
        self.edit_gas = self._add_input(self.gui_f4, "CILINDROS GAS:", "6")
        self.edit_agua = self._add_input(self.gui_f4, "BIDONES AGUA:", "12")
        btns_f4 = QHBoxLayout()
        bg = QPushButton("SOLICITAR GAS"); bg.setObjectName("btnEspecial"); bg.clicked.connect(lambda: self.redactar_gmail("GAS"))
        ba = QPushButton("SOLICITAR AGUA"); ba.setObjectName("btnEspecial"); ba.clicked.connect(lambda: self.redactar_gmail("AGUA"))
        btns_f4.addWidget(bg); btns_f4.addWidget(ba); self.gui_f4.layout().addLayout(btns_f4)

        # --- GUI F1 ---
        self.gui_f1 = self._crear_base_gui("Despacho Manual", 500, 230)
        self._add_titulo(self.gui_f1, "INGRESO MANUAL")
        h_layout_f1 = QHBoxLayout()
        v_left_f1 = QVBoxLayout()
        self.edit_patente_man = QLineEdit(); v_left_f1.addWidget(QLabel("PATENTE VEHÍCULO:")); v_left_f1.addWidget(self.edit_patente_man)
        self.edit_chofer_man = QLineEdit(); v_left_f1.addWidget(QLabel("NOMBRE CHOFER:")); v_left_f1.addWidget(self.edit_chofer_man)
        v_right_f1 = QVBoxLayout()
        v_right_f1.addWidget(QLabel("PREPARADOR:"))
        self.cb_preparador_f1 = QComboBox(); self.cb_preparador_f1.addItems(self.preparadores)
        v_right_f1.addWidget(self.cb_preparador_f1); v_right_f1.addStretch()
        h_layout_f1.addLayout(v_left_f1); h_layout_f1.addLayout(v_right_f1)
        self.gui_f1.layout().addLayout(h_layout_f1)
        self._add_footer_btns(self.gui_f1, self.on_aceptar_manual)

        # --- GUI F2 ---
        self.gui_f2 = self._crear_base_gui("Asignación Lista", 500, 230)
        self._add_titulo(self.gui_f2, "DATOS TRANSPORTE")
        h_layout_f2 = QHBoxLayout()
        v_left_f2 = QVBoxLayout()
        self.ddl_chofer = QComboBox(); self.ddl_chofer.addItems(self.lista_choferes)
        self.ddl_patente = QComboBox(); self.ddl_patente.addItems(self.lista_patentes)
        v_left_f2.addWidget(QLabel("SELECCIONAR CHOFER:")); v_left_f2.addWidget(self.ddl_chofer)
        v_left_f2.addWidget(QLabel("SELECCIONAR PATENTE:")); v_left_f2.addWidget(self.ddl_patente)
        v_right_f2 = QVBoxLayout()
        v_right_f2.addWidget(QLabel("PREPARADOR:"))
        self.cb_preparador_f2 = QComboBox(); self.cb_preparador_f2.addItems(self.preparadores)
        v_right_f2.addWidget(self.cb_preparador_f2)
        v_right_f2.addStretch()
        h_layout_f2.addLayout(v_left_f2); h_layout_f2.addLayout(v_right_f2)
        self.gui_f2.layout().addLayout(h_layout_f2)
        self._add_footer_btns(self.gui_f2, self.on_aceptar_lista)

    # -------------------------------------------------------------------------
    # --- MÉTODOS AUXILIARES DE INTERFAZ ---
    # -------------------------------------------------------------------------
    def _crear_base_gui(self, t: str, w: int, h: int) -> QWidget:
        """Construye una ventana básica con estilo nitro y tamaños fijos."""
        win = QWidget()
        win.setWindowTitle(t)
        win.setFixedSize(w, h)
        win.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        l = QVBoxLayout()
        l.setContentsMargins(15, 10, 15, 15)
        l.setSpacing(5)
        win.setLayout(l)
        return win

    def _add_titulo(self, win: QWidget, texto: str) -> None:
        l = QLabel(texto)
        l.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        l.setStyleSheet("color: #FFFFFF; margin-bottom: 2px;")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #3F4451; max-height: 1px;")
        win.layout().addWidget(l)
        win.layout().addWidget(line)

    def _add_input(self, win: QWidget, label: str, default: str = "") -> QLineEdit:
        win.layout().addWidget(QLabel(label))
        e = QLineEdit(default)
        win.layout().addWidget(e)
        return e

    def _add_footer_btns(self, win: QWidget, callback) -> None:
        l = QHBoxLayout()
        l.setSpacing(10)
        l.setContentsMargins(0, 10, 0, 0)
        b1 = QPushButton("ACEPTAR")
        b1.setObjectName("btnAceptar")
        b1.clicked.connect(callback)
        b2 = QPushButton("CANCELAR")
        b2.clicked.connect(win.hide)
        l.addWidget(b1)
        l.addWidget(b2)
        win.layout().addLayout(l)

# =============================================================================
# --- EJECUCIÓN ---
# =============================================================================
if __name__ == "__main__":
    nitro = NitroSystem()
    sys.exit(nitro.app.exec())