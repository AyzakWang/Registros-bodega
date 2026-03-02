const CONFIG = {
  nombreHoja: "Hoja 1",
  filaInicio: 5,
  columnaGuia: 7,          // columna G contiene el número de guía
  columnaInicioDatos: 3    // columna C
};

function _getSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(CONFIG.nombreHoja);
  if (!sh) throw new Error(`No existe la hoja "${CONFIG.nombreHoja}"`);
  return sh;
}

function doGet() {
  try {
    const guias = obtenerGuiasExistentes();
    return ContentService.createTextOutput(JSON.stringify(guias.filter(g => g)))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (e) {
    return ContentService.createTextOutput("[]")
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(5000);              // 5 s bloqueando

    const sheet = _getSheet();
    const data = JSON.parse(e.postData.contents || "{}");
    const numGuiaRecibida = String(data.num_guia || "").trim();

    if (!numGuiaRecibida) {
      return ContentService.createTextOutput("Guía inválida");
    }

    const ultimaFila = sheet.getLastRow();
    const guiasExistentes = obtenerGuiasExistentes(sheet, ultimaFila);

    if (guiasExistentes.includes(numGuiaRecibida)) {
      return ContentService.createTextOutput(data.modo_verificacion ? "Sincronizado" : "Duplicado");
    }

    const filaParaInsertar = [
      data.rut, data.senores, data.chofer, data.patente, numGuiaRecibida,
      data.oc, data.nv, data.fecha, data.hora, data.traslado, data.despacho,
      data.preparador
    ].map(v => String(v || "").toUpperCase().trim());

    const filaDestino = Math.max(CONFIG.filaInicio, ultimaFila + 1);
    const range = sheet.getRange(filaDestino, CONFIG.columnaInicioDatos, 1, 12);
    range.setValues([filaParaInsertar])
         .setFontSize(13)
         .setHorizontalAlignment("CENTER")
         .setVerticalAlignment("MIDDLE")
         .setFontFamily("Arial")
         .setBorder(false, true, false, true, true, false, "black",
                    SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

    // solo ordenar si realmente agregamos algo
    sheet.getRange(CONFIG.filaInicio, CONFIG.columnaInicioDatos,
                   sheet.getLastRow() - (CONFIG.filaInicio - 1), 12)
         .sort({column: CONFIG.columnaGuia, ascending: false});

    return ContentService.createTextOutput("Ingreso exitoso");
  } catch (err) {
    return ContentService.createTextOutput("ERROR: " + err.message);
  } finally {
    try { lock.releaseLock(); } catch (_) {}
  }
}

function obtenerGuiasExistentes(sheet, uFila) {
  const s = sheet || _getSheet();
  const lastRow = uFila || s.getLastRow();
  if (lastRow < CONFIG.filaInicio) return [];
  return s.getRange(CONFIG.filaInicio, CONFIG.columnaGuia,
                    lastRow - (CONFIG.filaInicio - 1), 1)
          .getValues()
          .flat()
          .map(g => String(g).trim());
}