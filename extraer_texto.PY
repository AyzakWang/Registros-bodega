import pdfplumber

# Ruta del PDF que quieres analizar (puedes usar uno de tus ejemplos)
archivo_pdf = r"P:\PLANTILLA CAJONES BODEGA\AutoHotkey\REGISTROS BODEGA\TEST EXTRACCION\T_52_GD_41156_CEDIBLE_20251006T091713.pdf"
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