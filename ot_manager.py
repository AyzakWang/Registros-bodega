import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# requires `pip install fpdf2` in your virtualenv
from fpdf import FPDF

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QDateEdit,
    QMessageBox,
    QGridLayout,
    QSpacerItem,
    QSizePolicy,
    QGroupBox,
)
from PyQt6.QtCore import Qt, QDate


# -----------------------------------------------------------------------------
# configuration
# -----------------------------------------------------------------------------
# database file (SQLite) that holds both SKU table and saved orders
DB_FILE = Path("ot_data.db")


# previously used for Excel-based SKU sheet; now replaced by SQLite table


# -----------------------------------------------------------------------------
# helpers / database
# -----------------------------------------------------------------------------

def init_db() -> None:
    """Ensure the SQLite file exists and the required tables are present."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS sku (
               sku TEXT PRIMARY KEY,
               descripcion TEXT,
               unidad TEXT
           )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS orders (
               folio TEXT PRIMARY KEY,
               cliente TEXT,
               solicitante TEXT,
               fecha_solicitud TEXT,
               fecha_entrega TEXT,
               items TEXT
           )"""
    )
    conn.commit()
    conn.close()

def append_order(order: dict) -> None:
    """Insert the order into the SQLite database."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    items_json = json.dumps(order["items"], ensure_ascii=False)
    c.execute(
        "INSERT INTO orders(folio,cliente,solicitante,fecha_solicitud,fecha_entrega,items) VALUES (?,?,?,?,?,?)",
        (
            order["folio"],
            order["cliente"],
            order["solicitante"],
            order["fecha_solicitud"],
            order["fecha_entrega"],
            items_json,
        ),
    )
    conn.commit()
    conn.close()


def load_orders() -> list[dict]:
    """Return list of orders stored in the database."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT folio,cliente,solicitante,fecha_solicitud,fecha_entrega,items FROM orders ORDER BY rowid"
    )
    rows = c.fetchall()
    conn.close()
    orders = []
    for folio, cliente, solicitante, fsol, fent, items_str in rows:
        try:
            items = json.loads(items_str) if items_str else []
        except Exception:
            items = []
        orders.append(
            {
                "folio": folio,
                "cliente": cliente,
                "solicitante": solicitante,
                "fecha_solicitud": fsol,
                "fecha_entrega": fent,
                "items": items,
            }
        )
    return orders


def load_sku_map() -> dict:
    """Read the SKU table from the database and return sku -> entry dict."""
    init_db()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT sku,descripcion,unidad FROM sku")
    rows = c.fetchall()
    conn.close()
    sku_map = {}
    for sku, desc, unidad in rows:
        if sku:
            sku_key = str(sku).strip().upper()
            sku_map[sku_key] = {"desc": str(desc or ""), "unidad": str(unidad or "")}
    return sku_map


# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

from PyQt6.QtWidgets import QDialog


class SKUManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Base de SKUs")
        self.resize(500, 400)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["SKU", "Descripcion", "Unidad"])
        from PyQt6.QtWidgets import QHeaderView
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.save)
        btn_import = QPushButton("Importar CSV")
        btn_import.clicked.connect(self.import_csv)
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        btn_hbox = QHBoxLayout()
        btn_hbox.addWidget(btn_import)
        btn_hbox.addWidget(btn_save)
        layout.addLayout(btn_hbox)
        self.setLayout(layout)
        self.load_data()
    
    def import_csv(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        import csv
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            # optionally skip header if present
            self.table.setRowCount(0)
            for row in reader:
                if not row:
                    continue
                # take first three columns
                sku = row[0]
                desc = row[1] if len(row) > 1 else ''
                unidad = row[2] if len(row) > 2 else ''
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(sku))
                self.table.setItem(r, 1, QTableWidgetItem(desc))
                self.table.setItem(r, 2, QTableWidgetItem(unidad))

    def load_data(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT sku,descripcion,unidad FROM sku")
        rows = c.fetchall()
        conn.close()
        self.table.setRowCount(0)
        for sku, desc, unidad in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(sku))
            self.table.setItem(r, 1, QTableWidgetItem(desc))
            self.table.setItem(r, 2, QTableWidgetItem(unidad))

    def save(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM sku")
        for r in range(self.table.rowCount()):
            sku_item = self.table.item(r, 0)
            desc_item = self.table.item(r, 1)
            unidad_item = self.table.item(r, 2)
            if sku_item and sku_item.text().strip():
                c.execute(
                    "INSERT OR REPLACE INTO sku(sku,descripcion,unidad) VALUES (?,?,?)",
                    (
                        sku_item.text().strip().upper(),
                        desc_item.text() if desc_item else "",
                        unidad_item.text() if unidad_item else "",
                    ),
                )
        conn.commit()
        conn.close()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestor de Órdenes de Trabajo")
        self.resize(900, 700)
        # cargar mapa de SKUs
        init_db()  # make sure db present before loading
        self.sku_map = load_sku_map()
        print(f"SKU map cargado: {len(self.sku_map)} entradas")
        # flag para evitar bucles infinitos en cellChanged
        self.updating = False
        self._build_ui()
        self._load_existing_orders()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        # simple stylesheet for a cleaner, more professional look
        self.setStyleSheet("QLabel, QLineEdit, QTableWidget { font-size: 11pt; }")
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # header fields - use a grid for better alignment
        from PyQt6.QtWidgets import QGridLayout, QSpacerItem, QSizePolicy
        header_layout = QGridLayout()
        self.edit_folio = QLineEdit()
        self.edit_cliente = QLineEdit()
        self.edit_solicitante = QLineEdit()
        # constrain widths so fields don't stretch excessively when window resizes
        self.edit_folio.setMaximumWidth(120)
        self.edit_cliente.setMaximumWidth(200)
        self.edit_solicitante.setMaximumWidth(200)
        self.date_solicitud = QDateEdit(QDate.currentDate())
        self.date_solicitud.setCalendarPopup(True)
        self.date_entrega = QDateEdit(QDate.currentDate())
        self.date_entrega.setCalendarPopup(True)

        # place labels and fields in a grid two columns wide
        header_layout.addWidget(QLabel("Folio:"), 0, 0)
        header_layout.addWidget(self.edit_folio, 0, 1)
        header_layout.addWidget(QLabel("Cliente:"), 1, 0)
        header_layout.addWidget(self.edit_cliente, 1, 1)
        header_layout.addWidget(QLabel("Solicitante:"), 2, 0)
        header_layout.addWidget(self.edit_solicitante, 2, 1)
        header_layout.addWidget(QLabel("Fecha solicitud:"), 3, 0)
        header_layout.addWidget(self.date_solicitud, 3, 1)
        header_layout.addWidget(QLabel("Fecha entrega:"), 4, 0)
        header_layout.addWidget(self.date_entrega, 4, 1)
        # button to edit SKU database
        sku_btn = QPushButton("Editar SKUs")
        sku_btn.clicked.connect(self._edit_skus)
        header_layout.addWidget(sku_btn, 5, 0, 1, 2)
        # add a spacer so the header section doesn't stretch weirdly
        header_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum), 0, 2, 6, 1)
        # wrap header in group box
        gb = QGroupBox("Datos de la Orden")
        gb.setLayout(header_layout)
        main_layout.addWidget(gb)

        # items table
        # Qty, (UDM hidden), SKU, Descripción, Trabajo
        self.table_items = QTableWidget(0, 5)
        self.table_items.setHorizontalHeaderLabels(["Qty", "UDM", "SKU", "Descripción", "Trabajo"])
        header = self.table_items.horizontalHeader()
        from PyQt6.QtWidgets import QHeaderView
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # hide the UDM column entirely - the unit will be computed automatically
        self.table_items.setColumnHidden(1, True)
        # conectar señal para autocompletar descripción cuando se edita SKU
        self.table_items.cellChanged.connect(self._on_item_changed)

        # controls for items
        btn_layout = QHBoxLayout()
        add_row = QPushButton("Agregar fila")
        add_row.clicked.connect(self._add_item_row)
        btn_layout.addWidget(add_row)
        save_btn = QPushButton("Guardar OT")
        save_btn.clicked.connect(self._save_order)
        btn_layout.addWidget(save_btn)

        items_group = QGroupBox("Ítems")
        items_layout = QVBoxLayout()
        items_layout.addWidget(self.table_items)
        items_layout.addLayout(btn_layout)
        items_group.setLayout(items_layout)
        main_layout.addWidget(items_group)

        # orders list
        self.table_orders = QTableWidget(0, 5)
        self.table_orders.setHorizontalHeaderLabels([
            "Folio",
            "Cliente",
            "Solicitud",
            "Entrega",
            "# ítems",
        ])
        from PyQt6.QtWidgets import QHeaderView
        self.table_orders.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(QLabel("Órdenes registradas:"))
        main_layout.addWidget(self.table_orders)

    def _edit_skus(self) -> None:
        dlg = SKUManagerDialog(self)
        if dlg.exec():
            # reload map after user saved changes
            self.sku_map = load_sku_map()

    def _add_item_row(self) -> None:
        r = self.table_items.rowCount()
        self.table_items.insertRow(r)
        # crear celdas vacías; UDM columna 1 permanecerá oculta y no editable
        for c in range(self.table_items.columnCount()):
            item = QTableWidgetItem("")
            if c == 1:  # hidden UDM
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table_items.setItem(r, c, item)

    def _save_order(self) -> None:
        folio = self.edit_folio.text().strip()
        if not folio:
            QMessageBox.warning(self, "Error", "Folio obligatorio")
            return
        # evitar folios duplicados
        orders = load_orders()
        for o in orders:
            if str(o.get("folio")) == folio:
                QMessageBox.warning(self, "Error", "Folio ya existe, elija otro")
                return
        order = {
            "folio": folio,
            "cliente": self.edit_cliente.text().strip(),
            "solicitante": self.edit_solicitante.text().strip(),
            "fecha_solicitud": self.date_solicitud.date().toString("yyyy-MM-dd"),
            "fecha_entrega": self.date_entrega.date().toString("yyyy-MM-dd"),
            "items": [],
        }
        for row in range(self.table_items.rowCount()):
            qty = self.table_items.item(row, 0)
            udm = self.table_items.item(row, 1)  # hidden
            sku = self.table_items.item(row, 2)
            desc = self.table_items.item(row, 3)
            trab = self.table_items.item(row, 4)
            if qty or sku or desc or trab:
                order["items"].append(
                    {
                        "qty": qty.text() if qty else "",
                        "udm": udm.text() if udm else "",
                        "sku": sku.text() if sku else "",
                        "descripcion": desc.text() if desc else "",
                        "trabajo": trab.text() if trab else "",
                    }
                )
        append_order(order)
        # export PDF
        pdf_file = generate_pdf(order)
        QMessageBox.information(
            self,
            "Guardado",
            f"Orden guardada correctamente\nPDF generado: {pdf_file}",
        )
        self._clear_form()
        self._load_existing_orders()

    def _clear_form(self) -> None:
        self.edit_folio.clear()
        self.edit_cliente.clear()
        self.edit_solicitante.clear()
        self.date_solicitud.setDate(QDate.currentDate())
        self.date_entrega.setDate(QDate.currentDate())
        self.table_items.setRowCount(0)

    def _on_item_changed(self, row: int, column: int) -> None:
        """Si el usuario escribió un SKU, buscar descripción y unidad."""
        if self.updating:
            return
        if column != 2:  # columna SKU (índice 2)
            return
        item = self.table_items.item(row, 2)
        if not item:
            return
        sku = item.text().strip().upper()
        if not sku:
            return
        unidad = ""
        descripcion = ""
        if sku in self.sku_map:
            entry = self.sku_map[sku]
            if isinstance(entry, dict):
                descripcion = entry.get("desc", "")
                unidad = entry.get("unidad", "")
            else:
                descripcion = str(entry)
                unidad = ""
            print(f"SKU encontrado: {sku} -> {descripcion}, unidad={unidad}")
        else:
            print(f"SKU no encontrado: {sku}")
            # regla heurística
            if "F" in sku:
                unidad = "UNI"
            else:
                unidad = "MTS"
        self.updating = True
        try:
            # colocar descripción y unidad (UDM se coloca en columna oculta)
            desc_item = self.table_items.item(row, 3)
            if desc_item is None:
                desc_item = QTableWidgetItem("")
                self.table_items.setItem(row, 3, desc_item)
            desc_item.setText(descripcion)
            udm_item = self.table_items.item(row, 1)
            if udm_item is None:
                udm_item = QTableWidgetItem("")
                self.table_items.setItem(row, 1, udm_item)
            udm_item.setText(unidad)
            # no editable even though hidden
            udm_item.setFlags(udm_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        finally:
            self.updating = False

    def _load_existing_orders(self) -> None:
        orders = load_orders()
        self.table_orders.setRowCount(0)
        for o in orders:
            r = self.table_orders.rowCount()
            self.table_orders.insertRow(r)
            self.table_orders.setItem(r, 0, QTableWidgetItem(str(o.get("folio", ""))))
            self.table_orders.setItem(r, 1, QTableWidgetItem(str(o.get("cliente", ""))))
            self.table_orders.setItem(r, 2, QTableWidgetItem(str(o.get("fecha_solicitud", ""))))
            self.table_orders.setItem(r, 3, QTableWidgetItem(str(o.get("fecha_entrega", ""))))
            self.table_orders.setItem(r, 4, QTableWidgetItem(str(len(o.get("items", [])))))


def generate_pdf(order: dict) -> str:
    """Create a PDF file with a fixed layout for the given order.

    Returns the filename created.
    """
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(False)

    # header section
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "ATTEX SPA", ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"O/T FOLIO Nº {order['folio']}", ln=True, align="C")
    pdf.ln(1)
    pdf.cell(0, 6, f"FECHA DE ENTREGA : {order['fecha_entrega']}", ln=True, align="R")
    pdf.ln(8)

    # information block
    pdf.set_font("Arial", "", 11)
    pdf.cell(30, 6, "CLIENTE:")
    pdf.cell(0, 6, order["cliente"], ln=True)
    pdf.cell(30, 6, "SOLICITANTE:")
    pdf.cell(0, 6, order["solicitante"], ln=True)
    pdf.cell(30, 6, "FECHA DE SOLICITUD:")
    pdf.cell(0, 6, order["fecha_solicitud"], ln=True)
    pdf.ln(6)

    # table header
    pdf.set_font("Arial", "B", 11)
    pdf.cell(20, 7, "QTY", border=1)
    pdf.cell(50, 7, "SKU", border=1)
    pdf.cell(80, 7, "DESCRIPCION", border=1)
    pdf.cell(40, 7, "TRABAJO", border=1, ln=True)
    pdf.set_font("Arial", "", 11)
    # items
    for item in order["items"]:
        pdf.cell(20, 6, item.get("qty", ""), border=1)
        pdf.cell(50, 6, item.get("sku", ""), border=1)
        pdf.cell(80, 6, item.get("descripcion", ""), border=1)
        pdf.cell(40, 6, item.get("trabajo", ""), border=1, ln=True)
    filename = f"OT_{order['folio']}.pdf"
    pdf.output(filename)
    return filename


if __name__ == "__main__":
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()