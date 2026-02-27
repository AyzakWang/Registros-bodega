import sys
import os
import webbrowser
import keyboard
import threading
import time
import pyperclip
import pyautogui
import pygetwindow as gw
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont

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
        self.preparadores = [
            "", "VICTOR CASTILLO [V.C.]", "JEFFERSON OLIVOS [J.O.]", "BENITO OVALLE [B.O.]",
            "EDUARDO VILLAGRA [E.V.]", "LUIS CURIN [L.C.]", "CARLOS JARA [C.J.]",
            "FABIAN GONZALEZ [F.G.]", "ISSAAC CROT [I.C.]", "JUAN ALVAREZ [J.A.]",
            "PEDRO SAENZ [P.S.]", "CRISTIAN RIVEROS [C.R.]"
        ]
        self.lista_choferes = ["", "EDUARDO VILLAGRA", "CRISTIAN RIVEROS", "CARLOS JARA", "FABIAN GONZALEZ", "ISSAAC CROT", "JUAN ALVAREZ"]
        self.lista_patentes = ["", "SKXG-70", "SHRB-88", "KRPH-61"]
        
        self.crear_interfaces()
        self.configurar_atajos()
        
        print(">>> SISTEMA ACTIVO (MODO FUNCIONANDO) <<<")
        print(">>> F1-F4: GUIs | Ctrl+1..9: F2..F10 | Ctrl+sc029: Ctrl+Shift+U <<<")

    # -------------------------------------------------------------------------
    # --- CONFIGURACIÓN DE ATAJOS (HOTKEYS) ---
    # -------------------------------------------------------------------------
    def configurar_atajos(self):
        keyboard.add_hotkey('f1', lambda: self.validar_y_enviar('f1'), suppress=True)
        keyboard.add_hotkey('f2', lambda: self.validar_y_enviar('f2'), suppress=True)
        keyboard.add_hotkey('f3', lambda: self.validar_y_enviar('f3'), suppress=True)
        keyboard.add_hotkey('f4', lambda: self.validar_y_enviar('f4'), suppress=True)
        keyboard.add_hotkey('f12', lambda: self.signaller.trigger.emit('exit'), suppress=True)
        keyboard.on_press_key(41, self._handle_special_key, suppress=True)

        for i in range(1, 10):
            self._mapear_ctrl_num(i)

        keyboard.add_hotkey('page up', lambda: self.validar_y_enviar_directo('ctrl+f'), suppress=True)
        keyboard.add_hotkey('page down', lambda: self.validar_y_enviar_directo('ctrl+a'), suppress=True)
        keyboard.add_hotkey('print screen', lambda: self.validar_y_enviar_directo('ctrl+p'), suppress=True)
        keyboard.add_hotkey('ctrl+space', lambda: self.validar_y_enviar_directo('ctrl+0'), suppress=True)
        keyboard.add_hotkey('num minus', lambda: self.validar_y_enviar_chrome(':'), suppress=True)

    def _handle_special_key(self, event):
        if keyboard.is_pressed('ctrl'):
            self.validar_y_enviar_directo('ctrl+shift+u')
        else:
            keyboard.send(41)

    def _mapear_ctrl_num(self, n):
        f_key = f'f{n+1}'
        keyboard.add_hotkey(f'ctrl+{n}', lambda k=f_key: self.validar_y_enviar_directo(k), suppress=True)

    # -------------------------------------------------------------------------
    # --- LÓGICA DE VALIDACIÓN DE VENTANAS ---
    # -------------------------------------------------------------------------
    def validar_y_enviar(self, comando):
        if self.is_sap_active() or comando == 'f4':
            self.signaller.trigger.emit(comando)

    def validar_y_enviar_directo(self, comando):
        if self.is_sap_active():
            keyboard.send(comando)

    def validar_y_enviar_chrome(self, comando):
        try:
            active_win = gw.getActiveWindow()
            if active_win and "CHROME" in active_win.title.upper():
                if comando == ":": keyboard.write(":")
                else: keyboard.send(comando)
        except: pass

    def is_sap_active(self):
        try:
            active_win = gw.getActiveWindow()
            if active_win:
                t = active_win.title.upper()
                return any(x in t for x in ["SAP BUSINESS ONE", "MANUAL", "LISTA", "SOLICITUDES"])
            return False
        except: return False

    # -------------------------------------------------------------------------
    # --- MANEJO DE SEÑALES Y GUI ---
    # -------------------------------------------------------------------------
    def handle_signals(self, comando):
        if comando == 'exit': self.app.quit()
        elif comando == 'f1': self.toggle_gui(self.gui_f1)
        elif comando == 'f2': self.toggle_gui(self.gui_f2)
        elif comando == 'f3': self.on_aceptar_f3()
        elif comando == 'f4': self.toggle_gui(self.gui_f4)

    def toggle_gui(self, win):
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
    def run_macro(self, despCfg, trasCfg, chofer_text="", patente_text="", preparador_full=""):
        old_clip = pyperclip.paste()
        try:
            active_win = gw.getActiveWindow()
            if active_win and "SAP BUSINESS ONE" in active_win.title.upper():
                if not active_win.isMaximized: active_win.maximize()
            
            # --- ACCIÓN PREPARADOR EN 218, 274 ---
            if preparador_full and "[" in preparador_full:
                acronimo = preparador_full.split("[")[1].split("]")[0]
                texto_a_pegar = f"PREPARADOR:{acronimo}"
                
                pyautogui.click(218, 274)
                time.sleep(0.2)
                pyperclip.copy(texto_a_pegar)
                keyboard.press('ctrl'); keyboard.press('v'); time.sleep(0.1); keyboard.release('v'); keyboard.release('ctrl')
                time.sleep(0.10)

            # --- ACCIÓN ORIGINAL EN 300, 655 ---
            pyautogui.click(300, 655)
            time.sleep(0.5) 

            self.select_option(despCfg)
            keyboard.send('tab')
            time.sleep(0.15)
            self.select_option(trasCfg)
            keyboard.send('tab')
            time.sleep(0.4) 

            def pegado_seguro(texto):
                if not texto: return
                txt = str(texto).strip().upper()
                pyperclip.copy(txt)
                time.sleep(0.05)
                keyboard.press('ctrl'); keyboard.press('v')
                time.sleep(0.1)
                keyboard.release('v'); keyboard.release('ctrl')
                time.sleep(0.15)

            if chofer_text: pegado_seguro(chofer_text)
            keyboard.send('tab')
            time.sleep(0.15)
            if patente_text: pegado_seguro(patente_text)
            
            for _ in range(3):
                keyboard.send('tab'); time.sleep(0.1)
            for k in ['down', 'up', 'up', 'down', 'down']:
                keyboard.send(k); time.sleep(0.08)
            
            time.sleep(0.3); keyboard.send('enter')
        except Exception as e: print(f"Error macro: {e}")
        finally:
            time.sleep(0.5); pyperclip.copy(old_clip)

    def select_option(self, cfg):
        for _ in range(cfg[0]): keyboard.send('down'); time.sleep(0.02)
        for _ in range(cfg[1]): keyboard.send('up'); time.sleep(0.02)
        for _ in range(cfg[2]): keyboard.send('down'); time.sleep(0.02)
        time.sleep(0.1); keyboard.send('enter')

    # -------------------------------------------------------------------------
    # --- EVENTOS DE BOTONES ---
    # -------------------------------------------------------------------------
    def on_aceptar_manual(self):
        c, p, pr = self.edit_chofer_man.text().upper(), self.edit_patente_man.text().upper(), self.cb_preparador_f1.currentText()
        if not c or not p: return
        self.gui_f1.hide(); self.run_macro([1,4,0], [1,11,0], c, p, pr)

    def on_aceptar_lista(self):
        c, p, pr = self.ddl_chofer.currentText(), self.ddl_patente.currentText(), self.cb_preparador_f2.currentText()
        if not c or not p: return 
        self.gui_f2.hide(); self.run_macro([1,4,1], [1,11,0], c, p, pr)

    def on_aceptar_f3(self):
        self.run_macro([1,4,1], [1,11,5])

    def redactar_gmail(self, tipo):
        cant = self.edit_gas.text() if tipo == "GAS" else self.edit_agua.text()
        if not cant: return
        dest = "ysanchez@attex.cl,a.arredondo@attex.cl,f.gonzalez@attex.cl,jalvarez@attex.cl" if tipo == "GAS" else "jneira.attex@gmail.com,recepcionattex@attex.cl,proveedores@attex.cl,jalvarez@attex.cl,f.gonzalez@attex.cl"
        asunto = "SOLICITUD DE COMPRA DE GAS" if tipo == "GAS" else "BIDONES DE AGUA BODEGA"
        cuerpo = f"Estimados.%0A%0AFavor gestionar la compra de {cant} {'cilindros para grúa horquilla' if tipo == 'GAS' else 'bidones de agua'}.%0A%0AAtte."
        webbrowser.open(f"https://mail.google.com/mail/?view=cm&fs=1&to={dest}&su={asunto.replace(' ', '%20')}&body={cuerpo}")
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
    def _crear_base_gui(self, t, w, h):
        win = QWidget()
        win.setWindowTitle(t); win.setFixedSize(w, h)
        win.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        l = QVBoxLayout(); l.setContentsMargins(15, 10, 15, 15); l.setSpacing(5); win.setLayout(l); return win

    def _add_titulo(self, win, texto):
        l = QLabel(texto); l.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        l.setStyleSheet("color: #FFFFFF; margin-bottom: 2px;")
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #3F4451; max-height: 1px;")
        win.layout().addWidget(l); win.layout().addWidget(line)

    def _add_input(self, win, label, default=""):
        win.layout().addWidget(QLabel(label))
        e = QLineEdit(default); win.layout().addWidget(e); return e

    def _add_footer_btns(self, win, callback):
        l = QHBoxLayout(); l.setSpacing(10); l.setContentsMargins(0, 10, 0, 0)
        b1 = QPushButton("ACEPTAR"); b1.setObjectName("btnAceptar"); b1.clicked.connect(callback)
        b2 = QPushButton("CANCELAR"); b2.clicked.connect(win.hide)
        l.addWidget(b1); l.addWidget(b2); win.layout().addLayout(l)

# =============================================================================
# --- EJECUCIÓN ---
# =============================================================================
if __name__ == "__main__":
    nitro = NitroSystem()
    sys.exit(nitro.app.exec())