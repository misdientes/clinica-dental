-- ============================================================
-- CLÍNICA DENTAL FAMILIAR — Script de creación de tablas
-- Ejecutar en Supabase → SQL Editor
-- ============================================================

-- 1. PRODUCTOS
CREATE TABLE IF NOT EXISTS productos (
    sku              TEXT PRIMARY KEY,
    nombre           TEXT NOT NULL,
    categoria        TEXT,
    marca            TEXT,
    precio_unitario  NUMERIC(10,2) DEFAULT 0,
    caducidad        TEXT,
    estado           TEXT DEFAULT 'Activo'
);

-- 2. STOCK POR SUCURSAL
CREATE TABLE IF NOT EXISTS stock (
    id               SERIAL PRIMARY KEY,
    sku              TEXT REFERENCES productos(sku),
    sucursal         TEXT NOT NULL,
    stock_actual     INTEGER DEFAULT 0,
    ubicacion_bodega TEXT,
    UNIQUE(sku, sucursal)
);

-- 3. MOVIMIENTOS
CREATE TABLE IF NOT EXISTS movimientos (
    id_movimiento    SERIAL PRIMARY KEY,
    fecha_hora       TIMESTAMP DEFAULT NOW(),
    sku              TEXT REFERENCES productos(sku),
    sucursal         TEXT,
    tipo_movimiento  TEXT,
    cantidad         INTEGER,
    motivo           TEXT,
    usuario          TEXT
);

-- 4. USUARIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id               SERIAL PRIMARY KEY,
    usuario          TEXT UNIQUE NOT NULL,
    password         TEXT NOT NULL,
    rol              TEXT DEFAULT 'Operador',
    nombre_completo  TEXT
);

-- 5. STOCK MÍNIMO
CREATE TABLE IF NOT EXISTS stock_minimo (
    sku          TEXT PRIMARY KEY REFERENCES productos(sku),
    stock_minimo INTEGER DEFAULT 5
);

-- 6. LOTES (vencimientos)
CREATE TABLE IF NOT EXISTS lotes (
    id_lote           SERIAL PRIMARY KEY,
    sku               TEXT REFERENCES productos(sku),
    sucursal          TEXT,
    cantidad          INTEGER,
    fecha_vencimiento DATE,
    fecha_ingreso     DATE DEFAULT CURRENT_DATE
);

-- 7. ÓRDENES DE COMPRA
CREATE TABLE IF NOT EXISTS ordenes (
    id_orden            SERIAL PRIMARY KEY,
    fecha               DATE DEFAULT CURRENT_DATE,
    sku                 TEXT REFERENCES productos(sku),
    nombre              TEXT,
    sucursal            TEXT,
    cantidad_solicitada INTEGER,
    estado              TEXT DEFAULT 'Pendiente',
    usuario             TEXT
);

-- ============================================================
-- USUARIO ADMIN POR DEFECTO
-- ============================================================
INSERT INTO usuarios (usuario, password, rol, nombre_completo)
VALUES ('admin', 'admin123', 'Admin', 'Administrador')
ON CONFLICT (usuario) DO NOTHING;

-- ============================================================
-- DESACTIVAR RLS (Row Level Security) para todas las tablas
-- (la app maneja la seguridad por login propio)
-- ============================================================
ALTER TABLE productos    DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock        DISABLE ROW LEVEL SECURITY;
ALTER TABLE movimientos  DISABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios     DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock_minimo DISABLE ROW LEVEL SECURITY;
ALTER TABLE lotes        DISABLE ROW LEVEL SECURITY;
ALTER TABLE ordenes      DISABLE ROW LEVEL SECURITY;
