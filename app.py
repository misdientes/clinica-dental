import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import io
from supabase import create_client, Client

# ══════════════════════════════════════════════
# CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════
st.set_page_config(
    page_title="🦷 Inventario Clínica Dental",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .stMetric { background: #f8faff; border-radius: 10px; padding: 8px; }
    .user-badge {
        background: #1f77b4; color: white; border-radius: 20px;
        padding: 4px 14px; font-size: 13px; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

SUCURSALES = ["Serrano", "Norte-Salud", "Calama"]

# ══════════════════════════════════════════════
# CONEXIÓN A SUPABASE
# ══════════════════════════════════════════════
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

sb = get_supabase()

# ══════════════════════════════════════════════
# FUNCIONES DE BASE DE DATOS
# ══════════════════════════════════════════════
def q(tabla, filtros=None, orden=None, limite=None):
    try:
        req = sb.table(tabla).select("*")
        if filtros:
            for col, val in filtros.items():
                req = req.eq(col, val)
        if orden:
            req = req.order(orden, desc=True)
        if limite:
            req = req.limit(limite)
        res = req.execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer {tabla}: {e}")
        return pd.DataFrame()

def load_productos():
    df = q("productos")
    if df.empty:
        return df
    df["categoria"] = df["categoria"].astype(str).str.strip()
    df = df[df["categoria"].notna() & (df["categoria"] != "nan") & (df["categoria"] != "")]
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce").fillna(0)
    return df

def load_stock():       return q("stock")
def load_movimientos(): return q("movimientos", orden="fecha_hora")
def load_stock_min():   return q("stock_minimo")
def load_lotes():       return q("lotes")
def load_ordenes():     return q("ordenes", orden="fecha")
def load_usuarios():    return q("usuarios")

def get_stock_val(sku, sucursal):
    df = q("stock", {"sku": sku, "sucursal": sucursal})
    if df.empty:
        return None
    return int(df.iloc[0]["stock_actual"])

def update_stock(sku, sucursal, nuevo_valor):
    sb.table("stock").update({"stock_actual": nuevo_valor}).eq("sku", sku).eq("sucursal", sucursal).execute()

def insert_movimiento(mov: dict):
    sb.table("movimientos").insert(mov).execute()

def insert_lote(lote: dict):
    sb.table("lotes").insert(lote).execute()

def insert_orden(orden: dict):
    sb.table("ordenes").insert(orden).execute()

def update_orden_estado(numero_orden, estado):
    sb.table("ordenes").update({"estado": estado}).eq("numero_orden", numero_orden).execute()

def upsert_stock_min(sku, minimo):
    sb.table("stock_minimo").upsert({"sku": sku, "stock_minimo": minimo}).execute()

def insert_usuario(u: dict):
    sb.table("usuarios").insert(u).execute()

def delete_usuario(usuario):
    sb.table("usuarios").delete().eq("usuario", usuario).execute()

def verificar_login(usuario, password):
    try:
        res = sb.table("usuarios").select("*").eq("usuario", usuario).eq("password", password).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        st.error(f"Error de login: {e}")
    return None

def semaforo(v, minimo=5):
    if v == 0:          return "⛔ Sin stock"
    if v <= minimo:     return "🔴 Crítico"
    if v <= minimo * 2: return "🟡 Bajo"
    return "🟢 OK"

def exportar_excel(df, hoja="Datos"):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=hoja)
    return buf.getvalue()

# ══════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    _, col_form, _ = st.columns([1, 1.2, 1])
    with col_form:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://img.icons8.com/emoji/96/tooth-emoji.png", width=80)
        st.title("Clínica Dental Familiar")
        st.subheader("🔐 Iniciar Sesión")
        with st.form("login_form"):
            u_input = st.text_input("Usuario")
            p_input = st.text_input("Contraseña", type="password")
            ok = st.form_submit_button("Entrar", use_container_width=True, type="primary")
        if ok:
            resultado = verificar_login(u_input.strip(), p_input.strip())
            if resultado:
                st.session_state.user = resultado
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
    st.stop()

# ══════════════════════════════════════════════
# USUARIO AUTENTICADO
# ══════════════════════════════════════════════
user     = st.session_state.user
es_admin = user["rol"] == "Admin"

# SIDEBAR
st.sidebar.image("https://img.icons8.com/emoji/96/tooth-emoji.png", width=50)
st.sidebar.markdown("**Clínica Dental Familiar**")
st.sidebar.markdown(
    f"<span class='user-badge'>👤 {user['nombre_completo']} · {user['rol']}</span>",
    unsafe_allow_html=True
)
st.sidebar.markdown("---")

MENU_ADMIN    = ["📊 Dashboard","➕ Agregar Producto","📥 Registrar Movimiento", "🔀 Transferencia entre Sucursales",
                 "📦 Inventario por Sucursal", "⚠️ Alertas", "📋 Historial",
                 "🛒 Órdenes de Compra", "📅 Vencimientos", "📈 Gráficos",
                 "⚙️ Configuración", "👥 Gestión de Usuarios"]
MENU_OPERADOR = ["➕ Agregar Producto","📥 Registrar Movimiento", "📦 Inventario por Sucursal",
                 "⚠️ Alertas", "📋 Historial", "🛒 Órdenes de Compra", "📅 Vencimientos"]

opcion = st.sidebar.radio("Navegación", MENU_ADMIN if es_admin else MENU_OPERADOR)
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.user = None
    st.rerun()

# ══════════════════════════════════════════════
# 📊 DASHBOARD
# ══════════════════════════════════════════════
if opcion == "📊 Dashboard":
    st.title("📊 Dashboard General")

    productos   = load_productos()
    stock       = load_stock()
    movimientos = load_movimientos()
    lotes       = load_lotes()
    stock_min   = load_stock_min()

    merged = stock.merge(productos[["sku","nombre","precio_unitario","categoria"]], on="sku", how="left")
    merged = merged.merge(stock_min, on="sku", how="left")
    merged["stock_minimo"] = merged["stock_minimo"].fillna(5)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        valor = (merged["stock_actual"] * merged["precio_unitario"].fillna(0)).sum()
        st.metric("💰 Valor Inventario", f"${valor:,.0f}")
    with c2:
        st.metric("📦 Productos Únicos", len(productos))
    with c3:
        st.metric("🔴 Bajo Mínimo", int((merged["stock_actual"] <= merged["stock_minimo"]).sum()))
    with c4:
        st.metric("⛔ Sin Stock", int((merged["stock_actual"] == 0).sum()))
    with c5:
        if not lotes.empty:
            lotes["fecha_vencimiento"] = pd.to_datetime(lotes["fecha_vencimiento"], errors="coerce")
            prox = lotes[lotes["fecha_vencimiento"].dt.date <= date.today() + timedelta(days=30)]
            st.metric("📅 Vencen en 30 días", len(prox))
        else:
            st.metric("📅 Vencen en 30 días", 0)

    st.markdown("---")
    ca, cb = st.columns(2)
    with ca:
        st.subheader("📈 Stock por Sucursal")
        res = stock.groupby("sucursal")["stock_actual"].sum().reset_index()
        res.columns = ["Sucursal","Unidades"]
        st.dataframe(res, use_container_width=True, hide_index=True)
    with cb:
        st.subheader("📂 Stock por Categoría")
        cat_s = merged.groupby("categoria")["stock_actual"].sum().reset_index()
        cat_s.columns = ["Categoría","Unidades"]
        st.dataframe(cat_s.sort_values("Unidades", ascending=False), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("🕐 Últimos 10 Movimientos")
    if not movimientos.empty:
        ult = movimientos.sort_values("fecha_hora", ascending=False).head(10)
        ult = ult.merge(productos[["sku","nombre"]], on="sku", how="left")
        st.dataframe(
            ult[["fecha_hora","nombre","sucursal","tipo_movimiento","cantidad","usuario"]]
            .rename(columns={"fecha_hora":"Fecha","nombre":"Producto","sucursal":"Sucursal",
                             "tipo_movimiento":"Tipo","cantidad":"Cant.","usuario":"Usuario"}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Sin movimientos registrados aún.")

# ══════════════════════════════════════════════
# 📥 REGISTRAR MOVIMIENTO
# ══════════════════════════════════════════════
elif opcion == "📥 Registrar Movimiento":
    st.title("📥 Registrar Movimiento de Inventario")

    productos = load_productos()
    stock_min = load_stock_min()

    st.subheader("1️⃣ Sucursal")
    sucursal = st.selectbox("📍 Sucursal", SUCURSALES)
    st.markdown("---")

    st.subheader("2️⃣ Buscar producto")
    cc, ct = st.columns([1, 2])
    with cc:
        cats = ["Todas"] + sorted(productos["categoria"].unique().tolist())
        cat_f = st.selectbox("🗂️ Categoría", cats)
    with ct:
        busq = st.text_input("🔍 Nombre, SKU o marca", placeholder="Ej: Alcohol, guante...")

    df_f = productos.copy()
    if cat_f != "Todas":
        df_f = df_f[df_f["categoria"] == cat_f]
    if busq.strip():
        t = busq.strip().lower()
        df_f = df_f[
            df_f["nombre"].str.lower().str.contains(t, na=False) |
            df_f["sku"].str.lower().str.contains(t, na=False) |
            df_f["marca"].str.lower().str.contains(t, na=False)
        ]

    st.caption(f"🔎 {len(df_f)} producto(s) encontrado(s)")
    sku_sel = None

    if df_f.empty:
        st.warning("❌ Sin resultados.")
    else:
        df_f = df_f.copy()
        df_f["_op"] = df_f.apply(lambda r: f"{r['nombre']}  ·  {r['marca']}  [{r['sku']}]", axis=1)
        sel = st.selectbox("📦 Producto", df_f["_op"].tolist())
        if sel:
            sku_sel = df_f.loc[df_f["_op"] == sel, "sku"].iloc[0]
            pi  = productos[productos["sku"] == sku_sel].iloc[0]
            sv  = get_stock_val(sku_sel, sucursal)
            sm_row = stock_min[stock_min["sku"] == sku_sel] if not stock_min.empty else pd.DataFrame()
            minimo = int(sm_row.iloc[0]["stock_minimo"]) if not sm_row.empty else 5

            c1, c2, c3 = st.columns(3)
            with c1: st.info(f"**{pi['nombre']}**\n\n**Marca:** {pi['marca']}")
            with c2: st.info(f"**Categoría:** {pi['categoria']}\n\n**SKU:** {sku_sel}")
            with c3:
                if sv is not None:
                    ic = "🟢" if sv > minimo*2 else ("🟡" if sv > minimo else "🔴")
                    st.info(f"**Stock en {sucursal}:**\n\n{ic} **{sv} uds** (mín: {minimo})")
                else:
                    st.warning("⚠️ Sin registro en esta sucursal")

    st.markdown("---")

    if sku_sel:
        st.subheader("3️⃣ Datos del movimiento")
        ct2, cc2 = st.columns(2)
        with ct2:
            tipo = st.selectbox("🔄 Tipo", ["Entrada por Compra","Salida por Uso Clínico","Ajuste de Inventario"])
        with cc2:
            label = "🔢 Nuevo stock total" if tipo == "Ajuste de Inventario" else "🔢 Cantidad"
            cantidad = st.number_input(label, min_value=0, max_value=99999, value=1)

        fecha_venc = None
        if tipo == "Entrada por Compra":
            with st.expander("📅 Registrar fecha de vencimiento (opcional)"):
                if st.checkbox("Este producto tiene fecha de vencimiento"):
                    fecha_venc = st.date_input("Fecha de vencimiento", min_value=date.today())

        cm, cu = st.columns(2)
        with cm: motivo = st.text_area("📝 Motivo / Observaciones", height=80)
        with cu: usuario_mov = st.text_input("👤 Usuario responsable", value=user["nombre_completo"])

        if st.button("✅ Confirmar Movimiento", type="primary", use_container_width=True):
            if not usuario_mov.strip():
                st.error("⚠️ Ingresa tu nombre.")
            else:
                sv_actual = get_stock_val(sku_sel, sucursal)
                if sv_actual is None:
                    st.error("❌ Producto sin registro en esta sucursal.")
                else:
                    exito = False
                    if tipo == "Entrada por Compra":
                        update_stock(sku_sel, sucursal, sv_actual + cantidad)
                        exito = True
                        if fecha_venc:
                            insert_lote({"sku": sku_sel, "sucursal": sucursal, "cantidad": cantidad,
                                         "fecha_vencimiento": str(fecha_venc), "fecha_ingreso": str(date.today())})
                    elif tipo == "Salida por Uso Clínico":
                        if cantidad > sv_actual:
                            st.error(f"❌ Stock insuficiente: hay {sv_actual} unidades.")
                        else:
                            update_stock(sku_sel, sucursal, sv_actual - cantidad)
                            exito = True
                    elif tipo == "Ajuste de Inventario":
                        update_stock(sku_sel, sucursal, cantidad)
                        exito = True

                    if exito:
                        insert_movimiento({
                            "fecha_hora": datetime.now().isoformat(),
                            "sku": sku_sel, "sucursal": sucursal,
                            "tipo_movimiento": tipo, "cantidad": cantidad,
                            "motivo": motivo.strip(), "usuario": usuario_mov.strip(),
                        })
                        nuevo_sv = get_stock_val(sku_sel, sucursal)
                        st.success(f"✅ Registrado — Stock en {sucursal}: **{nuevo_sv} unidades**")

# ══════════════════════════════════════════════
# 🔀 TRANSFERENCIA ENTRE SUCURSALES
# ══════════════════════════════════════════════
elif opcion == "🔀 Transferencia entre Sucursales":
    st.title("🔀 Transferencia de Stock entre Sucursales")
    productos = load_productos()

    c1, c2 = st.columns(2)
    with c1: origen  = st.selectbox("📤 Sucursal origen",  SUCURSALES)
    with c2: destino = st.selectbox("📥 Sucursal destino", SUCURSALES)

    if origen == destino:
        st.warning("⚠️ Origen y destino deben ser distintos.")
    else:
        busq_t = st.text_input("🔍 Buscar producto")
        df_t = productos.copy()
        if busq_t.strip():
            t = busq_t.strip().lower()
            df_t = df_t[df_t["nombre"].str.lower().str.contains(t, na=False) |
                        df_t["sku"].str.lower().str.contains(t, na=False)]
        if not df_t.empty:
            df_t["_op"] = df_t.apply(lambda r: f"{r['nombre']}  [{r['sku']}]", axis=1)
            sel_t = st.selectbox("📦 Producto", df_t["_op"].tolist())
            sku_t = df_t.loc[df_t["_op"] == sel_t, "sku"].iloc[0]
            sv_o  = get_stock_val(sku_t, origen)
            sv_d  = get_stock_val(sku_t, destino)

            co, cd = st.columns(2)
            with co: st.info(f"**Stock en {origen}:** {sv_o if sv_o is not None else '—'} unidades")
            with cd: st.info(f"**Stock en {destino}:** {sv_d if sv_d is not None else '—'} unidades")

            cant_t   = st.number_input("🔢 Cantidad a transferir", min_value=1, value=1)
            motivo_t = st.text_area("📝 Motivo")

            if st.button("✅ Confirmar Transferencia", type="primary", use_container_width=True):
                if sv_o is None or sv_d is None:
                    st.error("❌ Producto sin registro en alguna sucursal.")
                elif cant_t > sv_o:
                    st.error(f"❌ Solo hay {sv_o} unidades en {origen}.")
                else:
                    update_stock(sku_t, origen,  sv_o - cant_t)
                    update_stock(sku_t, destino, sv_d + cant_t)
                    ts = datetime.now().isoformat()
                    insert_movimiento({"fecha_hora": ts, "sku": sku_t, "sucursal": origen,
                                       "tipo_movimiento": "Transferencia Salida", "cantidad": cant_t,
                                       "motivo": f"A {destino}. {motivo_t}", "usuario": user["nombre_completo"]})
                    insert_movimiento({"fecha_hora": ts, "sku": sku_t, "sucursal": destino,
                                       "tipo_movimiento": "Transferencia Entrada", "cantidad": cant_t,
                                       "motivo": f"Desde {origen}. {motivo_t}", "usuario": user["nombre_completo"]})
                    st.success(f"✅ {cant_t} unidades transferidas de {origen} → {destino}")

# ══════════════════════════════════════════════
# 📦 INVENTARIO POR SUCURSAL
# ══════════════════════════════════════════════
elif opcion == "📦 Inventario por Sucursal":
    st.title("📦 Inventario por Sucursal")
    productos = load_productos()
    stock     = load_stock()
    stock_min = load_stock_min()

    c1, c2 = st.columns(2)
    with c1: suc_s = st.selectbox("📍 Sucursal", SUCURSALES)
    with c2:
        cats = ["Todas"] + sorted(productos["categoria"].unique().tolist())
        cat_s = st.selectbox("🗂️ Categoría", cats)
    busq_s = st.text_input("🔍 Buscar", placeholder="Nombre, SKU o marca...")

    st_suc = (stock[stock["sucursal"] == suc_s]
              .merge(productos[["sku","nombre","categoria","marca","precio_unitario"]], on="sku", how="left")
              .merge(stock_min, on="sku", how="left"))
    st_suc["stock_minimo"] = st_suc["stock_minimo"].fillna(5)

    if cat_s != "Todas":
        st_suc = st_suc[st_suc["categoria"] == cat_s]
    if busq_s.strip():
        t = busq_s.strip().lower()
        st_suc = st_suc[st_suc["nombre"].str.lower().str.contains(t, na=False) |
                        st_suc["sku"].str.lower().str.contains(t, na=False) |
                        st_suc["marca"].str.lower().str.contains(t, na=False)]

    st_suc["Estado"] = st_suc.apply(lambda r: semaforo(r["stock_actual"], r["stock_minimo"]), axis=1)

    cm1, cm2, cm3 = st.columns(3)
    cm1.metric("Total unidades", int(st_suc["stock_actual"].sum()))
    cm2.metric("Valor total", f"${(st_suc['stock_actual']*st_suc['precio_unitario'].fillna(0)).sum():,.0f}")
    cm3.metric("Bajo mínimo", int((st_suc["stock_actual"] <= st_suc["stock_minimo"]).sum()))

    df_show = (st_suc[["nombre","categoria","marca","stock_actual","stock_minimo","ubicacion_bodega","Estado"]]
               .rename(columns={"nombre":"Producto","categoria":"Categoría","marca":"Marca",
                                "stock_actual":"Stock","stock_minimo":"Mínimo","ubicacion_bodega":"Ubicación"})
               .sort_values("Stock"))
    st.caption(f"📋 {len(df_show)} productos")
    st.dataframe(df_show, use_container_width=True, hide_index=True)
    st.download_button("📥 Exportar a Excel",
                       data=exportar_excel(df_show, f"Inventario {suc_s}"),
                       file_name=f"inventario_{suc_s}_{date.today()}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ══════════════════════════════════════════════
# ⚠️ ALERTAS
# ══════════════════════════════════════════════
elif opcion == "⚠️ Alertas":
    st.title("⚠️ Alertas de Inventario")
    productos = load_productos()
    stock     = load_stock()
    stock_min = load_stock_min()

    merged_a = (stock.merge(productos[["sku","nombre","categoria","marca"]], on="sku", how="left")
                     .merge(stock_min, on="sku", how="left"))
    merged_a["stock_minimo"] = merged_a["stock_minimo"].fillna(5)
    merged_a["bajo"] = merged_a["stock_actual"] <= merged_a["stock_minimo"]

    suc_f = st.selectbox("📍 Filtrar por sucursal", ["Todas"] + SUCURSALES)
    if suc_f != "Todas":
        merged_a = merged_a[merged_a["sucursal"] == suc_f]

    sin_stk = merged_a[merged_a["stock_actual"] == 0]
    critico  = merged_a[(merged_a["stock_actual"] > 0) & (merged_a["bajo"])]

    c1, c2 = st.columns(2)
    c1.metric("⛔ Sin stock", len(sin_stk))
    c2.metric("🔴 Bajo mínimo", len(critico))

    cols_alert = {"nombre":"Producto","categoria":"Categoría","sucursal":"Sucursal",
                  "stock_actual":"Stock","stock_minimo":"Mínimo"}
    if not sin_stk.empty:
        st.subheader("⛔ Sin Stock")
        st.dataframe(sin_stk[list(cols_alert)].rename(columns=cols_alert),
                     use_container_width=True, hide_index=True)

    if not critico.empty:
        st.subheader("🔴 Stock Bajo Mínimo")
        st.dataframe(critico[list(cols_alert)].rename(columns=cols_alert),
                     use_container_width=True, hide_index=True)
        if es_admin and st.button("🛒 Generar Orden de Compra con estos productos"):
            from datetime import datetime
            numero_orden = f"ORD-AUTO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            for _, row in critico.iterrows():
                insert_orden({
                    "numero_orden": numero_orden,
                    "fecha": str(date.today()),
                    "sku": row["sku"],
                    "nombre": row["nombre"],
                    "sucursal": row["sucursal"],
                    "cantidad_solicitada": max(1, int(row["stock_minimo"]) * 2),
                    "estado": "Pendiente",
                    "usuario": user["nombre_completo"],
                    "comentarios": "Generada automáticamente desde alertas"
                })
            st.success(f"✅ Orden {numero_orden} generada con {len(critico)} productos")
            st.rerun()

    if sin_stk.empty and critico.empty:
        st.success("✅ ¡Todo el inventario está sobre el mínimo!")

    if not (sin_stk.empty and critico.empty):
        alerta_df = pd.concat([sin_stk, critico])
        st.download_button("📥 Exportar alertas",
                           data=exportar_excel(alerta_df[list(cols_alert)].rename(columns=cols_alert), "Alertas"),
                           file_name=f"alertas_{date.today()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ══════════════════════════════════════════════
# 📋 HISTORIAL
# ══════════════════════════════════════════════
elif opcion == "📋 Historial":
    st.title("📋 Historial de Movimientos")
    movimientos = load_movimientos()
    productos   = load_productos()

    if movimientos.empty:
        st.info("Aún no hay movimientos registrados.")
    else:
        mov_e = movimientos.merge(productos[["sku","nombre"]], on="sku", how="left")
        mov_e["fecha_hora"] = pd.to_datetime(mov_e["fecha_hora"], errors="coerce")

        c1, c2, c3 = st.columns(3)
        with c1: suc_h  = st.selectbox("Sucursal", ["Todas"] + SUCURSALES)
        with c2: tipo_h = st.selectbox("Tipo", ["Todos"] + sorted(mov_e["tipo_movimiento"].dropna().unique().tolist()))
        with c3: usr_h  = st.text_input("Usuario", placeholder="Filtrar...")
        c4, c5 = st.columns(2)
        with c4: f_desde = st.date_input("Desde", value=date.today() - timedelta(days=30))
        with c5: f_hasta = st.date_input("Hasta",  value=date.today())

        df_h = mov_e.copy()
        if suc_h  != "Todas": df_h = df_h[df_h["sucursal"] == suc_h]
        if tipo_h != "Todos":  df_h = df_h[df_h["tipo_movimiento"] == tipo_h]
        if usr_h.strip():      df_h = df_h[df_h["usuario"].str.lower().str.contains(usr_h.lower(), na=False)]
        df_h = df_h[(df_h["fecha_hora"].dt.date >= f_desde) & (df_h["fecha_hora"].dt.date <= f_hasta)]
        df_h = df_h.sort_values("fecha_hora", ascending=False)

        df_show = df_h[["fecha_hora","nombre","sucursal","tipo_movimiento","cantidad","motivo","usuario"]].rename(
            columns={"fecha_hora":"Fecha","nombre":"Producto","sucursal":"Sucursal",
                     "tipo_movimiento":"Tipo","cantidad":"Cant.","motivo":"Motivo","usuario":"Usuario"})
        st.caption(f"{len(df_show)} movimiento(s)")
        st.dataframe(df_show, use_container_width=True, hide_index=True)
        st.download_button("📥 Exportar a Excel", data=exportar_excel(df_show, "Historial"),
                           file_name=f"historial_{f_desde}_{f_hasta}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ══════════════════════════════════════════════
# 🛒 ÓRDENES DE COMPRA (VERSIÓN MEJORADA)
# ══════════════════════════════════════════════
elif opcion == "🛒 Órdenes de Compra":
    st.title("🛒 Órdenes de Compra")

    def generar_numero_orden():
        now = datetime.now()
        sufijo = user.get("sucursal", "GEN")[:3].upper() if not es_admin else "ADM"
        return f"ORD-{now.strftime('%Y%m%d-%H%M%S')}-{sufijo}"

    def ordenes_agrupadas(filtrar_sucursal=None, estado_filtro=None):
        ordenes_df = load_ordenes()
        if ordenes_df.empty:
            return pd.DataFrame()
        if filtrar_sucursal and not es_admin:
            ordenes_df = ordenes_df[ordenes_df["sucursal"] == filtrar_sucursal]
        if estado_filtro and estado_filtro != "Todos":
            ordenes_df = ordenes_df[ordenes_df["estado"] == estado_filtro]
        if ordenes_df.empty:
            return pd.DataFrame()
        resumen = ordenes_df.groupby("numero_orden").agg({
            "fecha": "first",
            "sucursal": "first",
            "estado": "first",
            "usuario": "first",
            "cantidad_solicitada": "sum",
            "sku": lambda x: list(x)
        }).reset_index()
        resumen.rename(columns={"cantidad_solicitada": "total_items", "sku": "productos"}, inplace=True)
        resumen["productos"] = resumen["productos"].apply(lambda x: len(x))
        return resumen

    tab1, tab2, tab3 = st.tabs(["➕ Nueva Orden (Múltiples productos)", "📋 Órdenes Activas", "📜 Historial de Órdenes Cerradas"])

    with tab1:
        st.subheader("🛒 Arma tu orden de compra")
        productos = load_productos()
        if productos.empty:
            st.warning("No hay productos cargados. Agrega productos primero.")
        else:
            if "carrito" not in st.session_state:
                st.session_state.carrito = []

            with st.form("agregar_al_carrito"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    producto_opciones = productos.apply(lambda r: f"{r['nombre']} [{r['sku']}]", axis=1).tolist()
                    seleccion = st.selectbox("Producto", producto_opciones)
                    sku_seleccionado = productos[productos.apply(lambda r: f"{r['nombre']} [{r['sku']}]" == seleccion, axis=1)]["sku"].iloc[0]
                    nombre_seleccionado = productos[productos["sku"] == sku_seleccionado]["nombre"].iloc[0]
                with col2:
                    cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
                with col3:
                    sucursal_destino = st.selectbox("Sucursal destino", SUCURSALES)
                agregar = st.form_submit_button("➕ Agregar al carrito")
                if agregar and cantidad > 0:
                    st.session_state.carrito.append({
                        "sku": sku_seleccionado,
                        "nombre": nombre_seleccionado,
                        "cantidad": cantidad,
                        "sucursal": sucursal_destino
                    })
                    st.success(f"✅ {nombre_seleccionado} x{cantidad} agregado")

            if st.session_state.carrito:
                st.subheader("📦 Carrito actual")
                df_carrito = pd.DataFrame(st.session_state.carrito)
                st.dataframe(df_carrito[["nombre", "cantidad", "sucursal"]], use_container_width=True, hide_index=True)

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("🗑️ Vaciar carrito", use_container_width=True):
                        st.session_state.carrito = []
                        st.rerun()
                with col_btn2:
                    comentarios = st.text_area("Comentarios para la orden (opcional)")
                    if st.button("✅ Generar Orden de Compra", type="primary", use_container_width=True):
                        if not st.session_state.carrito:
                            st.error("El carrito está vacío")
                        else:
                            numero_ord = generar_numero_orden()
                            fecha_actual = str(date.today())
                            for item in st.session_state.carrito:
                                insert_orden({
                                    "numero_orden": numero_ord,
                                    "fecha": fecha_actual,
                                    "sku": item["sku"],
                                    "nombre": item["nombre"],
                                    "sucursal": item["sucursal"],
                                    "cantidad_solicitada": item["cantidad"],
                                    "estado": "Pendiente",
                                    "usuario": user["nombre_completo"],
                                    "comentarios": comentarios
                                })
                            st.success(f"✅ Orden {numero_ord} generada con {len(st.session_state.carrito)} productos")
                            st.session_state.carrito = []
                            st.rerun()
            else:
                st.info("El carrito está vacío. Agrega productos arriba.")

    with tab2:
        st.subheader("📋 Órdenes activas")
        if es_admin:
            suc_filtro = st.selectbox("Filtrar por sucursal", ["Todas"] + SUCURSALES)
            sucursal_filtro = None if suc_filtro == "Todas" else suc_filtro
        else:
            sucursal_filtro = user.get("sucursal", None)
            if sucursal_filtro:
                st.info(f"Mostrando órdenes de tu sucursal: {sucursal_filtro}")
            else:
                st.warning("Tu usuario no tiene asignada una sucursal. Contacta al administrador.")
        estado_filtro = st.selectbox("Estado", ["Todos", "Pendiente", "Enviada"])
        ordenes_activas = ordenes_agrupadas(sucursal_filtro, estado_filtro)
        if ordenes_activas.empty:
            st.info("No hay órdenes activas.")
        else:
            for _, orden in ordenes_activas.iterrows():
                with st.expander(f"📄 {orden['numero_orden']} - {orden['sucursal']} - {orden['estado']} - {orden['fecha']}"):
                    st.write(f"**Productos:** {orden['productos']} items")
                    st.write(f"**Total unidades:** {orden['total_items']}")
                    st.write(f"**Creada por:** {orden['usuario']}")
                    detalle = q("ordenes", {"numero_orden": orden['numero_orden']})
                    if not detalle.empty:
                        st.dataframe(detalle[["nombre", "cantidad_solicitada", "sucursal"]].rename(
                            columns={"nombre":"Producto", "cantidad_solicitada":"Cantidad", "sucursal":"Sucursal"}),
                            use_container_width=True, hide_index=True)
                    if es_admin and orden['estado'] not in ["Recibida", "Cerrada"]:
                        nuevo_estado = st.selectbox(f"Cambiar estado para {orden['numero_orden']}",
                                                    ["Pendiente", "Enviada", "Recibida", "Cerrada"],
                                                    key=f"estado_{orden['numero_orden']}")
                        if st.button(f"Actualizar {orden['numero_orden']}", key=f"btn_{orden['numero_orden']}"):
                            update_orden_estado(orden['numero_orden'], nuevo_estado)
                            st.success(f"Orden {orden['numero_orden']} actualizada a '{nuevo_estado}'")
                            st.rerun()

    with tab3:
        st.subheader("📜 Historial de órdenes cerradas")
        if es_admin:
            suc_hist = st.selectbox("Sucursal", ["Todas"] + SUCURSALES, key="hist_suc")
            suc_hist_filtro = None if suc_hist == "Todas" else suc_hist
        else:
            suc_hist_filtro = user.get("sucursal", None)
        ordenes_hist = ordenes_agrupadas(suc_hist_filtro, estado_filtro="Cerrada")
        if ordenes_hist.empty:
            st.info("No hay órdenes cerradas aún.")
        else:
            st.dataframe(ordenes_hist[["numero_orden", "fecha", "sucursal", "total_items", "usuario"]],
                         use_container_width=True, hide_index=True)
            st.download_button("📥 Exportar historial", data=exportar_excel(ordenes_hist, "Historial_Ordenes"),
                               file_name=f"historial_ordenes_{date.today()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ══════════════════════════════════════════════
# 📅 VENCIMIENTOS
# ══════════════════════════════════════════════
elif opcion == "📅 Vencimientos":
    st.title("📅 Control de Vencimientos")
    productos = load_productos()
    lotes     = load_lotes()

    if lotes.empty:
        st.info("No hay lotes con vencimiento. Al registrar una entrada puedes agregar fecha de vencimiento.")
    else:
        lotes["fecha_vencimiento"] = pd.to_datetime(lotes["fecha_vencimiento"], errors="coerce")
        lotes_e = lotes.merge(productos[["sku","nombre","categoria"]], on="sku", how="left")
        hoy = date.today()

        vencidos = lotes_e[lotes_e["fecha_vencimiento"].dt.date < hoy]
        prox7    = lotes_e[(lotes_e["fecha_vencimiento"].dt.date >= hoy) &
                           (lotes_e["fecha_vencimiento"].dt.date <= hoy + timedelta(days=7))]
        prox30   = lotes_e[(lotes_e["fecha_vencimiento"].dt.date >= hoy) &
                           (lotes_e["fecha_vencimiento"].dt.date <= hoy + timedelta(days=30))]

        c1, c2, c3 = st.columns(3)
        c1.metric("🔴 Vencidos", len(vencidos))
        c2.metric("🟡 Vencen en 7 días", len(prox7))
        c3.metric("📅 Vencen en 30 días", len(prox30))

        filtro_v = st.selectbox("Ver", ["Todos","Solo vencidos","Próximos 30 días"])
        df_v = vencidos if filtro_v == "Solo vencidos" else (prox30 if filtro_v == "Próximos 30 días" else lotes_e)
        df_v = df_v.sort_values("fecha_vencimiento")

        st.dataframe(
            df_v[["nombre","categoria","sucursal","cantidad","fecha_vencimiento","fecha_ingreso"]]
            .rename(columns={"nombre":"Producto","categoria":"Categoría","sucursal":"Sucursal",
                             "cantidad":"Cantidad","fecha_vencimiento":"Vencimiento","fecha_ingreso":"Ingreso"}),
            use_container_width=True, hide_index=True)
        st.download_button("📥 Exportar a Excel",
                           data=exportar_excel(df_v[["nombre","categoria","sucursal","cantidad","fecha_vencimiento"]], "Vencimientos"),
                           file_name=f"vencimientos_{date.today()}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ══════════════════════════════════════════════
# 📈 GRÁFICOS
# ══════════════════════════════════════════════
elif opcion == "📈 Gráficos":
    st.title("📈 Gráficos y Análisis")
    productos   = load_productos()
    stock       = load_stock()
    movimientos = load_movimientos()

    tab1, tab2, tab3 = st.tabs(["Movimientos por día","Stock por Sucursal","Consumo por Categoría"])

    with tab1:
        if movimientos.empty:
            st.info("Sin movimientos.")
        else:
            mg = movimientos.copy()
            mg["fecha_hora"] = pd.to_datetime(mg["fecha_hora"], errors="coerce")
            mg["fecha"] = mg["fecha_hora"].dt.date
            pivot = (mg.groupby(["fecha","tipo_movimiento"]).size().reset_index(name="n")
                       .pivot(index="fecha", columns="tipo_movimiento", values="n").fillna(0))
            st.bar_chart(pivot)

    with tab2:
        sg = stock.groupby("sucursal")["stock_actual"].sum().reset_index()
        sg.columns = ["Sucursal","Unidades"]
        st.bar_chart(sg.set_index("Sucursal"))

    with tab3:
        mg2 = stock.merge(productos[["sku","categoria"]], on="sku", how="left")
        cg  = mg2.groupby("categoria")["stock_actual"].sum().reset_index()
        cg.columns = ["Categoría","Unidades"]
        st.bar_chart(cg.sort_values("Unidades", ascending=False).set_index("Categoría"))
        if not movimientos.empty:
            st.subheader("Top 10 productos más usados")
            mp = movimientos.merge(productos[["sku","nombre"]], on="sku", how="left")
            top = (mp[mp["tipo_movimiento"] == "Salida por Uso Clínico"]
                   .groupby("nombre")["cantidad"].sum()
                   .sort_values(ascending=False).head(10).reset_index())
            if not top.empty:
                st.bar_chart(top.set_index("nombre"))

# ══════════════════════════════════════════════
# ⚙️ CONFIGURACIÓN
# ══════════════════════════════════════════════
elif opcion == "⚙️ Configuración":
    st.title("⚙️ Configuración — Stock Mínimo")
    productos = load_productos()
    stock_min = load_stock_min()

    busq_cfg = st.text_input("🔍 Buscar producto")
    df_cfg = productos.copy()
    if busq_cfg.strip():
        t = busq_cfg.strip().lower()
        df_cfg = df_cfg[df_cfg["nombre"].str.lower().str.contains(t, na=False) |
                        df_cfg["sku"].str.lower().str.contains(t, na=False)]

    df_cfg["_op"] = df_cfg.apply(lambda r: f"{r['nombre']}  [{r['sku']}]", axis=1)
    sel_cfg = st.selectbox("📦 Producto", df_cfg["_op"].tolist())
    if sel_cfg:
        sku_cfg = df_cfg.loc[df_cfg["_op"] == sel_cfg, "sku"].iloc[0]
        sm_row  = stock_min[stock_min["sku"] == sku_cfg] if not stock_min.empty else pd.DataFrame()
        val_act = int(sm_row.iloc[0]["stock_minimo"]) if not sm_row.empty else 5
        nuevo_min = st.number_input("📉 Stock mínimo", min_value=0, max_value=999, value=val_act)
        if st.button("💾 Guardar", type="primary"):
            upsert_stock_min(sku_cfg, nuevo_min)
            st.success(f"✅ Mínimo actualizado a {nuevo_min} unidades")

    st.markdown("---")
    st.subheader("📋 Mínimos configurados")
    if not stock_min.empty:
        df_ms = stock_min.merge(productos[["sku","nombre","categoria"]], on="sku", how="left")
        st.dataframe(
            df_ms[["nombre","categoria","stock_minimo"]]
            .rename(columns={"nombre":"Producto","categoria":"Categoría","stock_minimo":"Mínimo"}),
            use_container_width=True, hide_index=True)
    else:
        st.info("Sin mínimos configurados. Por defecto todos son 5.")

# ══════════════════════════════════════════════
# 👥 GESTIÓN DE USUARIOS
# ══════════════════════════════════════════════
elif opcion == "👥 Gestión de Usuarios":
    st.title("👥 Gestión de Usuarios")
    usuarios = load_usuarios()

    st.subheader("Usuarios actuales")
    st.dataframe(
        usuarios[["usuario","nombre_completo","rol"]]
        .rename(columns={"usuario":"Usuario","nombre_completo":"Nombre","rol":"Rol"}),
        use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("➕ Agregar usuario")
    c1, c2 = st.columns(2)
    with c1:
        nu = st.text_input("Usuario (sin espacios)")
        nn = st.text_input("Nombre completo")
    with c2:
        np_ = st.text_input("Contraseña", type="password")
        nr  = st.selectbox("Rol", ["Operador","Admin"])

    if st.button("➕ Crear usuario", type="primary"):
        if not nu.strip() or not np_.strip() or not nn.strip():
            st.error("⚠️ Completa todos los campos.")
        elif nu in usuarios["usuario"].values:
            st.error("❌ Ese usuario ya existe.")
        else:
            insert_usuario({"usuario": nu.strip(), "password": np_.strip(),
                            "rol": nr, "nombre_completo": nn.strip()})
            st.success(f"✅ Usuario '{nu}' creado")
            st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Eliminar usuario")
    otros = [u for u in usuarios["usuario"].tolist() if u != user["usuario"]]
    if otros:
        ud = st.selectbox("Usuario a eliminar", otros)
        if st.button("🗑️ Eliminar", type="secondary"):
            delete_usuario(ud)
            st.success(f"✅ Usuario '{ud}' eliminado")
            st.rerun()
    else:
        st.info("No hay otros usuarios para eliminar.")

# ══════════════════════════════════════════════
# ➕ AGREGAR PRODUCTO
# ══════════════════════════════════════════════
elif opcion == "➕ Agregar Producto":
    st.title("➕ Agregar Nuevo Producto")
    
    with st.form("form_nuevo_producto"):
        st.subheader("Datos del producto")
        
        col1, col2 = st.columns(2)
        with col1:
            sku = st.text_input("SKU (código único)", placeholder="Ej: ALCOHOL-001")
            nombre = st.text_input("Nombre del producto *", placeholder="Ej: Alcohol 70%")
            categoria = st.selectbox("Categoría", ["Insumos", "Medicamentos", "Equipos", "Material de curación", "Otros"])
            marca = st.text_input("Marca", placeholder="Ej: 3M, J&J, etc.")
        
        with col2:
            precio = st.number_input("Precio unitario", min_value=0.0, step=100.0, format="%.0f")
            stock_inicial = st.number_input("Stock inicial (unidades)", min_value=0, value=0)
            sucursal = st.selectbox("Sucursal inicial", SUCURSALES)
            ubicacion = st.text_input("Ubicación en bodega", placeholder="Ej: Estante A1")
        
        submitted = st.form_submit_button("✅ Guardar Producto", type="primary", use_container_width=True)
        
        if submitted:
            if not sku.strip():
                st.error("❌ El SKU es obligatorio")
            elif not nombre.strip():
                st.error("❌ El nombre es obligatorio")
            else:
                try:
                    sb.table("productos").insert({
                        "sku": sku.strip().upper(),
                        "nombre": nombre.strip(),
                        "categoria": categoria,
                        "marca": marca.strip(),
                        "precio_unitario": precio
                    }).execute()
                    
                    sb.table("stock").insert({
                        "sku": sku.strip().upper(),
                        "sucursal": sucursal,
                        "stock_actual": stock_inicial,
                        "ubicacion_bodega": ubicacion
                    }).execute()
                    
                    sb.table("stock_minimo").insert({
                        "sku": sku.strip().upper(),
                        "stock_minimo": 5
                    }).execute(on_conflict="sku")
                    
                    st.success(f"✅ Producto '{nombre}' agregado exitosamente con SKU: {sku.strip().upper()}")
                    st.balloons()
                    
                except Exception as e:
                    if "duplicate key" in str(e):
                        st.error("❌ Ya existe un producto con ese SKU. Usa otro código.")
                    else:
                        st.error(f"❌ Error al guardar: {e}")

# ══════════════════════════════════════════════
# PIE DE PÁGINA
# ══════════════════════════════════════════════
st.markdown("---")
st.caption(f"🦷 Clínica Dental Familiar · {user['nombre_completo']} · {datetime.now().strftime('%d/%m/%Y %H:%M')}")