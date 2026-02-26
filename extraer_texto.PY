import pdfplumber

# Ruta del PDF que quieres analizar (puedes usar uno de tus ejemplos)
archivo_pdf = r"C:\Users\123\Documents\PLANTILLA CAJONES BODEGA\PLANTILLA CAJONES BODEGA\AutoHotkey\REGISTRO BODEGA\TEST REGISTRO BODEGA GUIAS\T_52_GD_42697_CEDIBLE_20260113T111328.pdf"
archivo_salida = "contenido_pdf.txt"

try:
    with pdfplumber.open(archivo_pdf) as pdf:
        # Extraemos el texto de la primera página
        texto_completo = pdf.pages[0].extract_text()
        
        # Guardamos el texto en un archivo para que lo revises con calma
        with open(archivo_salida, "w", encoding="utf-8") as f:
            f.write(texto_completo)
            
    print(f"¡Listo! Revisa el archivo '{archivo_salida}' en tu carpeta para ver el texto exacto.")

except Exception as e:
    print(f"Error al leer el PDF: {e}")