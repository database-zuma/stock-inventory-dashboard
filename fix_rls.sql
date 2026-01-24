-- Fix RLS Policies - Allow public read access
-- Copy-paste ke Supabase SQL Editor

-- Drop existing policies
DROP POLICY IF EXISTS "Allow public read on inventory" ON inventory;
DROP POLICY IF EXISTS "Allow public read on sales_summary" ON sales_summary;
DROP POLICY IF EXISTS "Allow public read on sales_detail" ON sales_detail;

-- Create new policies that allow anonymous access
CREATE POLICY "Enable read access for all users" ON inventory FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON sales_summary FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON sales_detail FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON max_stock FOR SELECT USING (true);
CREATE POLICY "Enable read access for all users" ON master_store FOR SELECT USING (true);

-- Verify policies
SELECT tablename, policyname, cmd, qual
FROM pg_policies
WHERE tablename IN ('inventory', 'sales_summary', 'sales_detail', 'max_stock', 'master_store');
