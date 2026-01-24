-- ========================================
-- FIX RLS POLICIES FOR AUTHENTICATED USERS
-- ========================================
-- Jalankan SQL ini di Supabase SQL Editor
-- untuk allow read access ke semua users (authenticated & anonymous)

-- Drop existing policies (kalau ada)
DROP POLICY IF EXISTS "Enable read access for all users" ON inventory;
DROP POLICY IF EXISTS "Enable read access for all users" ON sales_summary;
DROP POLICY IF EXISTS "Enable read access for all users" ON sales_detail;
DROP POLICY IF EXISTS "Enable read access for all users" ON max_stock;
DROP POLICY IF EXISTS "Enable read access for all users" ON master_store;

-- ========================================
-- TABLE: inventory
-- ========================================

-- Enable RLS
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;

-- Allow SELECT for everyone (authenticated & anonymous)
CREATE POLICY "Allow public read access" ON inventory
    FOR SELECT
    USING (true);

-- ========================================
-- TABLE: sales_summary
-- ========================================

-- Enable RLS
ALTER TABLE sales_summary ENABLE ROW LEVEL SECURITY;

-- Allow SELECT for everyone
CREATE POLICY "Allow public read access" ON sales_summary
    FOR SELECT
    USING (true);

-- ========================================
-- TABLE: sales_detail
-- ========================================

-- Enable RLS
ALTER TABLE sales_detail ENABLE ROW LEVEL SECURITY;

-- Allow SELECT for everyone
CREATE POLICY "Allow public read access" ON sales_detail
    FOR SELECT
    USING (true);

-- ========================================
-- TABLE: max_stock
-- ========================================

-- Enable RLS (kalau table ada)
ALTER TABLE max_stock ENABLE ROW LEVEL SECURITY;

-- Allow SELECT for everyone
CREATE POLICY "Allow public read access" ON max_stock
    FOR SELECT
    USING (true);

-- ========================================
-- TABLE: master_store
-- ========================================

-- Enable RLS (kalau table ada)
ALTER TABLE master_store ENABLE ROW LEVEL SECURITY;

-- Allow SELECT for everyone
CREATE POLICY "Allow public read access" ON master_store
    FOR SELECT
    USING (true);

-- ========================================
-- VERIFICATION
-- ========================================

-- Check RLS status
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('inventory', 'sales_summary', 'sales_detail', 'max_stock', 'master_store');

-- Check policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
AND tablename IN ('inventory', 'sales_summary', 'sales_detail', 'max_stock', 'master_store');
