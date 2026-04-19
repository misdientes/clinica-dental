"""
importar_datos.py
Ejecuta este script UNA SOLA VEZ para cargar tus CSV a Supabase.

Uso:
    python importar_datos.py

Requiere:
    pip install supabase pandas
"""

import pandas as pd
from supabase import create_client
import os
from dotenv import load_dotenv

# ── Configura aquí tus credenciales de Supabase ──────────────
# Cargar variables del archivo .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# ─────────────────────────────────────────────────────────────

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def log(msg): print(f"  → {msg}")

# 1. Productos
print("\n📦 Importando productos...")
df_p = pd.read_csv("productos.csv")
df_p.columns = [c.strip().lower().replace(" ", "_") for c in df_p.columns]
df_p = df_p.rename(columns={"producto": "nombre", "precio": "precio_unitario",
                             "stock_actual": "_ignorar"})
df_p["categoria"] = df_p["categoria"].astype(str).str.strip()
df_p = df_p[df_p["categoria"].notna() & (df_p["categoria"] != "nan")]
df_p["precio_unitario"] = pd.to_numeric(df_p["precio_unitario"], errors="coerce").fillna(0)

rows_p = df_p[["sku","nombre","categoria","marca","precio_unitario","estado"]].to_dict("records")
for i in range(0, len(rows_p), 50):
    batch = rows_p[i:i+50]
    sb.table("productos").upsert(batch).execute()
    log(f"Productos {i+1}–{min(i+50, len(rows_p))} ✓")

# 2. Stock
print("\n📊 Importando stock...")
df_s = pd.read_csv("stock_por_sucursal.csv")
rows_s = df_s.to_dict("records")
for i in range(0, len(rows_s), 100):
    batch = rows_s[i:i+100]
    sb.table("stock").upsert(batch, on_conflict="sku,sucursal").execute()
    log(f"Stock {i+1}–{min(i+100, len(rows_s))} ✓")

# 3. Movimientos (si existen)
if os.path.exists("movimientos.csv") and os.path.getsize("movimientos.csv") > 0:
    print("\n📋 Importando movimientos...")
    df_m = pd.read_csv("movimientos.csv")
    if not df_m.empty:
        rows_m = df_m.to_dict("records")
        for i in range(0, len(rows_m), 100):
            sb.table("movimientos").insert(rows_m[i:i+100]).execute()
            log(f"Movimientos {i+1}–{min(i+100, len(rows_m))} ✓")

print("\n✅ Importación completada exitosamente.")
print("   Ya puedes lanzar la app con: streamlit run app.py")
