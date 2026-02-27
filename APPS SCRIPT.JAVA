const CONFIG = {
  nombreHoja: "Hoja 1",
  filaInicio: 5,
  columnaGuia: 7, 
  columnaInicioDatos: 3 
};

function doGet() {
  try {
    const guias = obtenerGuiasExistentes();
    return ContentService.createTextOutput(JSON.stringify(guias.filter(g => g)))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (e) {
    return ContentService.createTextOutput("[]").setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName(CONFIG.nombreHoja);
  const data = JSON.parse(e.postData.contents);
  const numGuiaRecibida = String(data.num_guia || "").trim();
  
  const ultimaFila = sheet.getLastRow();
  const guiasExistentes = obtenerGuiasExistentes(sheet, ultimaFila);

  if (guiasExistentes.includes(numGuiaRecibida)) {
    return ContentService.createTextOutput(data.modo_verificacion ? "Sincronizado" : "Duplicado");
  }

  // CONFIGURACIÓN DE 12 COLUMNAS (C a N)
  const filaParaInsertar = [
    data.rut, data.senores, data.chofer, data.patente, numGuiaRecibida,
    data.oc, data.nv, data.fecha, data.hora, data.traslado, data.despacho,
    data.preparador // <--- Aquí llega el NOMBRE COMPLETO a la Columna N
  ].map(val => String(val || "").toUpperCase().trim());

  const filaDestino = Math.max(CONFIG.filaInicio, ultimaFila + 1);
  const range = sheet.getRange(filaDestino, CONFIG.columnaInicioDatos, 1, 12);
  
  range.setValues([filaParaInsertar])
       .setFontSize(13)
       .setHorizontalAlignment("CENTER")
       .setVerticalAlignment("MIDDLE")
       .setFontFamily("Arial")
       .setBorder(false, true, false, true, true, false, "black", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // Ordenar incluyendo la nueva columna N (12 columnas)
  sheet.getRange(CONFIG.filaInicio, CONFIG.columnaInicioDatos, sheet.getLastRow() - (CONFIG.filaInicio - 1), 12)
       .sort({column: CONFIG.columnaGuia, ascending: false});
  
  return ContentService.createTextOutput("Ingreso exitoso");
}

function obtenerGuiasExistentes(sheet, uFila) {
  const s = sheet || SpreadsheetApp.getActiveSpreadsheet().getSheetByName(CONFIG.nombreHoja);
  const lastRow = uFila || s.getLastRow();
  if (lastRow < CONFIG.filaInicio) return [];
  return s.getRange(CONFIG.filaInicio, CONFIG.columnaGuia, lastRow - (CONFIG.filaInicio - 1), 1)
          .getValues().flat().map(g => String(g).trim());
}