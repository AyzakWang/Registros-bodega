function doPost(e) {
  var nombreHoja = "Hoja 1"; 
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName(nombreHoja);
  
  var data = JSON.parse(e.postData.contents);
  var numGuiaNueva = String(data.num_guia).trim(); 
  var ultimaFila = sheet.getLastRow();
  
  // 1. Validar duplicados (Columna G = Columna 7)
  if (ultimaFila >= 5) {
    var guiasExistentes = sheet.getRange(5, 7, ultimaFila - 4, 1).getValues().flat().map(function(item) { 
      return String(item).trim(); 
    });
    
    if (guiasExistentes.indexOf(numGuiaNueva) !== -1) {
      return ContentService.createTextOutput("Error: Guía duplicada");
    }
  }

  // 2. Insertar los datos al final de la tabla para luego ordenar
  // Aplicamos toUpperCase() a todos los campos para que se guarden en MAYÚSCULAS
  var filaParaInsertar = [
    String(data.rut).toUpperCase(),      // Columna C
    String(data.senores).toUpperCase(),  // Columna D
    String(data.chofer).toUpperCase(),   // Columna E
    String(data.patente).toUpperCase(),  // Columna F
    String(data.num_guia).toUpperCase(), // Columna G
    String(data.oc).toUpperCase(),       // Columna H
    String(data.nv).toUpperCase(),       // Columna I
    String(data.fecha).toUpperCase(),    // Columna J
    String(data.hora).toUpperCase()      // Columna K
  ];
  
  // Escribimos el dato al final disponible
  var rowToInsert = (ultimaFila < 5) ? 5 : ultimaFila + 1;
  var range = sheet.getRange(rowToInsert, 3, 1, 9); 
  range.setValues([filaParaInsertar]);
  
// 3. Aplicar formato: SOLO bordes IZQUIERDO, DERECHO y VERTICALES INTERNOS
  range.setFontSize(13)
       .setHorizontalAlignment("CENTER")
       .setVerticalAlignment("MIDDLE")
       .setFontFamily("Arial")
       .setBorder(
         false, // Superior (Top)
         true,  // Izquierdo (Left)
         false, // Inferior (Bottom)
         true,  // Derecho (Right)
         true,  // Verticales internos
         false, // Horizontales internos
         "black", 
         SpreadsheetApp.BorderStyle.SOLID_MEDIUM
       );

  // 4. ORDENAR AUTOMÁTICAMENTE
  var nuevaUltimaFila = sheet.getLastRow();
  if (nuevaUltimaFila >= 5) {
    var rangeToSort = sheet.getRange(5, 3, nuevaUltimaFila - 4, 9);
    // Ordenar por la columna 7 (Número de Guía) de forma Descendente
    rangeToSort.sort({column: 7, ascending: false});
  }
  
  return ContentService.createTextOutput("Ingreso exitoso y tabla ordenada por N° Guía");
}