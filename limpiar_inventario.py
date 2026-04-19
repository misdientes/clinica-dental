import pandas as pd

# === CONFIGURACIÓN ===
archivo_excel = "insumos dental familiar (1).xlsx"  # ← Asegúrate que este sea el nombre exacto
hoja = "Hoja1"

# === LEER EL ARCHIVO EXCEL ===
print("🔍 Leyendo archivo Excel...")
df = pd.read_excel(archivo_excel, sheet_name=hoja, header=None)

# Eliminar filas completamente vacías
df = df.dropna(how='all')

# Asignar nombres a las columnas según tu archivo
df.columns = ["nombre", "categoria", "marca", "precio", "stock", "caducidad", "estado", "acciones"]

# Identificar filas que contienen SKU (empiezan con "SKU:")
sku_rows = df["nombre"].astype(str).str.contains(r"^SKU:", na=False)

# Extraer el SKU real y limpiar
df.loc[sku_rows, "sku"] = df.loc[sku_rows, "nombre"].str.replace("SKU: ", "").str.strip()

# Rellenar hacia atrás para asociar cada SKU al nombre anterior
df["sku"] = df["sku"].bfill()

# Mantener solo las filas con nombre de producto (no las de SKU)
productos_df = df[~sku_rows].copy()

# Seleccionar y ordenar columnas finales
columnas_finales = ["sku", "nombre", "categoria", "marca", "precio", "stock", "caducidad", "estado"]
productos_df = productos_df[columnas_finales]

# Limpiar valores nulos en categoría
productos_df["categoria"] = productos_df["categoria"].fillna("Sin categoría").astype(str)

# Guardar CSV limpio
productos_df.to_csv("productos_limpio.csv", index=False, encoding="utf-8")
print("✅ Archivo 'productos_limpio.csv' generado correctamente!")