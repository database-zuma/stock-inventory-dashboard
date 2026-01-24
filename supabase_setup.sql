-- ========================================
-- ZUMA Dashboard Database Setup
-- ========================================
-- Copy-paste script ini ke Supabase SQL Editor

-- 1. TABLE: inventory (Stock Warehouse & Retail)
CREATE TABLE IF NOT EXISTS inventory (
    id BIGSERIAL PRIMARY KEY,
    sku TEXT NOT NULL,
    kode_kecil TEXT,
    name TEXT,
    size TEXT,
    category TEXT,
    gender TEXT,
    series TEXT,
    tipe TEXT,
    tier TEXT,
    color TEXT,
    entity TEXT NOT NULL, -- DDD, LJBB, MBB, UBB
    type TEXT NOT NULL, -- warehouse atau retail
    store_stock JSONB, -- Dynamic: {"Warehouse Pusat": 100, "Zuma DDD": 50, ...}
    total INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_inventory_sku ON inventory(sku);
CREATE INDEX IF NOT EXISTS idx_inventory_entity ON inventory(entity);
CREATE INDEX IF NOT EXISTS idx_inventory_type ON inventory(type);
CREATE INDEX IF NOT EXISTS idx_inventory_tier ON inventory(tier);
CREATE INDEX IF NOT EXISTS idx_inventory_gender ON inventory(gender);


-- 2. TABLE: sales_summary (untuk Control Stock - Turnover Analysis)
CREATE TABLE IF NOT EXISTS sales_summary (
    id BIGSERIAL PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    nov INTEGER DEFAULT 0, -- Sales November
    des INTEGER DEFAULT 0, -- Sales Desember
    jan INTEGER DEFAULT 0, -- Sales Januari
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sales_summary_sku ON sales_summary(sku);


-- 3. TABLE: sales_detail (untuk Sales Dashboard)
CREATE TABLE IF NOT EXISTS sales_detail (
    id BIGSERIAL PRIMARY KEY,
    tanggal TIMESTAMP NOT NULL,
    toko TEXT,
    tipe_produk TEXT,
    barcode TEXT,
    tags TEXT,
    koleksi TEXT,
    kasir TEXT,
    pelanggan TEXT,
    penjualan_kotor NUMERIC,
    jumlah_pembayaran NUMERIC,
    hpp NUMERIC,
    nomor_pesanan TEXT,
    jumlah INTEGER,
    produk TEXT,
    sku TEXT,
    vendor TEXT,
    price NUMERIC,
    persentase_diskon NUMERIC,
    jumlah_diskon NUMERIC,
    kode_diskon TEXT,
    total NUMERIC,
    persentase_pajak NUMERIC,
    promosi TEXT,
    tax_amount NUMERIC,
    status_pemenuhan TEXT,
    tanggal_pemenuhan TIMESTAMP,
    nama_server TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_sales_detail_tanggal ON sales_detail(tanggal);
CREATE INDEX IF NOT EXISTS idx_sales_detail_toko ON sales_detail(toko);
CREATE INDEX IF NOT EXISTS idx_sales_detail_sku ON sales_detail(sku);
CREATE INDEX IF NOT EXISTS idx_sales_detail_kasir ON sales_detail(kasir);


-- 4. TABLE: max_stock (Max stock per store/warehouse)
CREATE TABLE IF NOT EXISTS max_stock (
    id BIGSERIAL PRIMARY KEY,
    store_name TEXT NOT NULL UNIQUE,
    max_stock INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_max_stock_store ON max_stock(store_name);


-- 5. TABLE: master_store (Store/Warehouse area mapping)
CREATE TABLE IF NOT EXISTS master_store (
    id BIGSERIAL PRIMARY KEY,
    store_name TEXT NOT NULL UNIQUE,
    area TEXT,
    entity TEXT,
    type TEXT, -- retail atau warehouse
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_master_store_area ON master_store(area);


-- 6. Enable Row Level Security (RLS) - Buka akses public untuk read
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_summary ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales_detail ENABLE ROW LEVEL SECURITY;
ALTER TABLE max_stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE master_store ENABLE ROW LEVEL SECURITY;

-- Policy: Allow public read access (untuk dashboard)
CREATE POLICY "Allow public read on inventory" ON inventory FOR SELECT USING (true);
CREATE POLICY "Allow public read on sales_summary" ON sales_summary FOR SELECT USING (true);
CREATE POLICY "Allow public read on sales_detail" ON sales_detail FOR SELECT USING (true);
CREATE POLICY "Allow public read on max_stock" ON max_stock FOR SELECT USING (true);
CREATE POLICY "Allow public read on master_store" ON master_store FOR SELECT USING (true);

-- Policy: Allow authenticated insert/update (untuk upload script)
CREATE POLICY "Allow authenticated insert on inventory" ON inventory FOR INSERT WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated update on inventory" ON inventory FOR UPDATE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated delete on inventory" ON inventory FOR DELETE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert on sales_summary" ON sales_summary FOR INSERT WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated update on sales_summary" ON sales_summary FOR UPDATE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated delete on sales_summary" ON sales_summary FOR DELETE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert on sales_detail" ON sales_detail FOR INSERT WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated update on sales_detail" ON sales_detail FOR UPDATE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated delete on sales_detail" ON sales_detail FOR DELETE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert on max_stock" ON max_stock FOR INSERT WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated update on max_stock" ON max_stock FOR UPDATE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Allow authenticated insert on master_store" ON master_store FOR INSERT WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY "Allow authenticated update on master_store" ON master_store FOR UPDATE USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Selesai! Tables sudah siap digunakan.
