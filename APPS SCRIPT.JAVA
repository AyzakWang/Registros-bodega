// NUEVO: Esta función permite a Python descargar todos los números de guía de una sola vez
function doGet() {
  var nombreHoja = "Hoja 1"; 
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(nombreHoja);
  var ultimaFila = sheet.getLastRow();
  
  if (ultimaFila < 5) {
    return ContentService.createTextOutput(JSON.stringify([])).setMimeType(ContentService.MimeType.JSON);
  }
  
  // Obtenemos solo la columna G (índice 7) donde están los números de guía
  var guias = sheet.getRange(5, 7, ultimaFila - 4, 1).getValues().flat().map(function(g) {
    return String(g).trim();
  });
  
  return ContentService.createTextOutput(JSON.stringify(guias)).setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  var nombreHoja = "Hoja 1"; 
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(nombreHoja);
  
  var data = JSON.parse(e.postData.contents);
  var numGuiaRecibida = String(data.num_guia || "").trim(); 
  var ultimaFila = sheet.getLastRow();

  // --- 1. OPTIMIZACIÓN: CHEQUEO RÁPIDO ---
  if (data.chequeo_rapido === true) {
    if (ultimaFila >= 5) {
      var guiasExistentes = sheet.getRange(5, 7, ultimaFila - 4, 1).getValues().flat().map(function(item) { 
        return String(item).trim(); 
      });
      if (guiasExistentes.indexOf(numGuiaRecibida) !== -1) {
        return ContentService.createTextOutput("YA_EXISTE");
      }
    }
    return ContentService.createTextOutput("FALTA_DATOS");
  }

  // --- 2. VALIDACIÓN DE EXISTENCIA PARA INGRESO COMPLETO ---
  var existeEnSheets = false;
  if (ultimaFila >= 5) {
    var guiasExistentesParaIngreso = sheet.getRange(5, 7, ultimaFila - 4, 1).getValues().flat().map(function(item) { 
      return String(item).trim(); 
    });
    if (guiasExistentesParaIngreso.indexOf(numGuiaRecibida) !== -1) {
      existeEnSheets = true;
    }
  }

  if (data.modo_verificacion === true && existeEnSheets) {
    return ContentService.createTextOutput("Sincronizado: Guía ya presente.");
  }
  
  if (data.modo_verificacion === false && existeEnSheets) {
    return ContentService.createTextOutput("Error: Guía duplicada");
  }

  // --- 3. INSERTAR DATOS ---
  var filaParaInsertar = [
    String(data.rut || "S/R").toUpperCase(),      
    String(data.senores || "S/N").toUpperCase(),  
    String(data.chofer || "S/C").toUpperCase(),   
    String(data.patente || "S/P").toUpperCase(),  
    String(data.num_guia || "S/G").toUpperCase(), 
    String(data.oc || "S/OC").toUpperCase(),       
    String(data.nv || "S/NV").toUpperCase(),       
    String(data.fecha || "").toUpperCase(),    
    String(data.hora || "").toUpperCase(),
    String(data.traslado || "S/T").toUpperCase(),  
    String(data.despacho || "S/D").toUpperCase()   
  ];
  
  var rowToInsert = (ultimaFila < 5) ? 5 : ultimaFila + 1;
  var range = sheet.getRange(rowToInsert, 3, 1, 11); 
  range.setValues([filaParaInsertar]);
  
  // --- 4. FORMATO ---
  range.setFontSize(13)
       .setHorizontalAlignment("CENTER")
       .setVerticalAlignment("MIDDLE")
       .setFontFamily("Arial")
       .setBorder(false, true, false, true, true, false, "black", SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  // --- 5. ORDENAR ---
  var nuevaUltimaFila = sheet.getLastRow();
  if (nuevaUltimaFila >= 5) {
    var rangeToSort = sheet.getRange(5, 3, nuevaUltimaFila - 4, 11);
    rangeToSort.sort({column: 7, ascending: false}); 
  }
  
  return ContentService.createTextOutput(data.modo_verificacion ? "Recuperada" : "Ingreso exitoso");
}