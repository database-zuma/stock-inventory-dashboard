-- =============================================
-- SUPABASE RPC FUNCTIONS FOR SALES AGGREGATION
-- =============================================

-- 1. Sales Summary by SKU (for salesMap - used in Stock views)
-- Returns: sku_code, nov, dec, jan, total, avg
CREATE OR REPLACE FUNCTION get_sales_summary_by_sku()
RETURNS TABLE (
    sku_code TEXT,
    nov BIGINT,
    dec BIGINT,
    jan BIGINT,
    total BIGINT,
    avg_qty BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.sku_code,
        COALESCE(SUM(CASE WHEN EXTRACT(MONTH FROM s.order_date::timestamp) = 11 THEN s.quantity ELSE 0 END), 0)::BIGINT as nov,
        COALESCE(SUM(CASE WHEN EXTRACT(MONTH FROM s.order_date::timestamp) = 12 THEN s.quantity ELSE 0 END), 0)::BIGINT as dec,
        COALESCE(SUM(CASE WHEN EXTRACT(MONTH FROM s.order_date::timestamp) = 1 THEN s.quantity ELSE 0 END), 0)::BIGINT as jan,
        COALESCE(SUM(s.quantity), 0)::BIGINT as total,
        COALESCE(ROUND(SUM(s.quantity)::numeric / 3), 0)::BIGINT as avg_qty
    FROM sales s
    WHERE s.sku_code IS NOT NULL AND s.sku_code != ''
    GROUP BY s.sku_code;
END;
$$;

-- 2. Sales Summary by Store (for Sales Dashboard - Performance tab)
-- Returns: store_name, total_qty, total_sales, total_transactions, total_gross
CREATE OR REPLACE FUNCTION get_sales_by_store_summary()
RETURNS TABLE (
    store_name TEXT,
    total_qty BIGINT,
    total_sales NUMERIC,
    total_gross NUMERIC,
    total_transactions BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.store_name,
        COALESCE(SUM(s.quantity), 0)::BIGINT as total_qty,
        COALESCE(SUM(s.total), 0) as total_sales,
        COALESCE(SUM(s.gross_sales), 0) as total_gross,
        COUNT(DISTINCT s.order_number)::BIGINT as total_transactions
    FROM sales s
    WHERE s.store_name IS NOT NULL AND s.store_name != ''
    GROUP BY s.store_name
    ORDER BY total_sales DESC;
END;
$$;

-- 3. Sales Summary by Store and Month (detailed breakdown)
CREATE OR REPLACE FUNCTION get_sales_by_store_monthly()
RETURNS TABLE (
    store_name TEXT,
    month_num INT,
    total_qty BIGINT,
    total_sales NUMERIC,
    total_gross NUMERIC,
    transaction_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.store_name,
        EXTRACT(MONTH FROM s.order_date::timestamp)::INT as month_num,
        COALESCE(SUM(s.quantity), 0)::BIGINT as total_qty,
        COALESCE(SUM(s.total), 0) as total_sales,
        COALESCE(SUM(s.gross_sales), 0) as total_gross,
        COUNT(DISTINCT s.order_number)::BIGINT as transaction_count
    FROM sales s
    WHERE s.store_name IS NOT NULL AND s.store_name != ''
    GROUP BY s.store_name, EXTRACT(MONTH FROM s.order_date::timestamp)
    ORDER BY s.store_name, month_num;
END;
$$;

-- 4. Sales by SPG/Cashier Summary
CREATE OR REPLACE FUNCTION get_sales_by_spg_summary()
RETURNS TABLE (
    spg_name TEXT,
    store_name TEXT,
    total_qty BIGINT,
    total_sales NUMERIC,
    transaction_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.cashier as spg_name,
        s.store_name,
        COALESCE(SUM(s.quantity), 0)::BIGINT as total_qty,
        COALESCE(SUM(s.total), 0) as total_sales,
        COUNT(DISTINCT s.order_number)::BIGINT as transaction_count
    FROM sales s
    WHERE s.cashier IS NOT NULL AND s.cashier != ''
    GROUP BY s.cashier, s.store_name
    ORDER BY total_sales DESC;
END;
$$;

-- 5. Top Products Summary
CREATE OR REPLACE FUNCTION get_top_products_summary(limit_count INT DEFAULT 100)
RETURNS TABLE (
    sku_code TEXT,
    product_name TEXT,
    product_type TEXT,
    total_qty BIGINT,
    total_sales NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.sku_code,
        MAX(s.product_name) as product_name,
        MAX(s.product_type) as product_type,
        COALESCE(SUM(s.quantity), 0)::BIGINT as total_qty,
        COALESCE(SUM(s.total), 0) as total_sales
    FROM sales s
    WHERE s.sku_code IS NOT NULL AND s.sku_code != ''
    GROUP BY s.sku_code
    ORDER BY total_qty DESC
    LIMIT limit_count;
END;
$$;

-- 6. Sales Filtered by Date Range (for on-demand loading)
CREATE OR REPLACE FUNCTION get_sales_filtered(
    start_date TEXT DEFAULT NULL,
    end_date TEXT DEFAULT NULL,
    filter_store TEXT DEFAULT NULL,
    limit_count INT DEFAULT 10000
)
RETURNS TABLE (
    order_date TEXT,
    store_name TEXT,
    sku_code TEXT,
    product_name TEXT,
    product_type TEXT,
    cashier TEXT,
    quantity INT,
    total NUMERIC,
    gross_sales NUMERIC,
    discount_amount NUMERIC,
    order_number TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.order_date::TEXT,
        s.store_name,
        s.sku_code,
        s.product_name,
        s.product_type,
        s.cashier,
        s.quantity,
        s.total,
        s.gross_sales,
        s.discount_amount,
        s.order_number
    FROM sales s
    WHERE
        (start_date IS NULL OR s.order_date::date >= start_date::date)
        AND (end_date IS NULL OR s.order_date::date <= end_date::date)
        AND (filter_store IS NULL OR filter_store = '' OR s.store_name = filter_store)
    ORDER BY s.order_date DESC
    LIMIT limit_count;
END;
$$;

-- 7. Daily Sales Trend
CREATE OR REPLACE FUNCTION get_sales_daily_trend()
RETURNS TABLE (
    sale_date DATE,
    total_qty BIGINT,
    total_sales NUMERIC,
    transaction_count BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.order_date::date as sale_date,
        COALESCE(SUM(s.quantity), 0)::BIGINT as total_qty,
        COALESCE(SUM(s.total), 0) as total_sales,
        COUNT(DISTINCT s.order_number)::BIGINT as transaction_count
    FROM sales s
    GROUP BY s.order_date::date
    ORDER BY sale_date;
END;
$$;

-- 8. VIEW: Inventory with Products JOIN (queryable with pagination like a table)
-- This replaces the RPC function - views support pagination via PostgREST
CREATE OR REPLACE VIEW inventory_full AS
SELECT
    i.id,
    i.sku_code,
    i.quantity,
    i.entity,
    i.location_type,
    i.location_name,
    COALESCE(p.product_name, '') as product_name,
    COALESCE(p.kode_kecil, LEFT(i.sku_code::TEXT, 7)) as kode_kecil,
    COALESCE(p.size, '') as size,
    COALESCE(p.gender, '') as gender,
    COALESCE(p.series, '') as series,
    COALESCE(p.product_type, '') as product_type,
    COALESCE(p.tier, '') as tier
FROM inventory i
LEFT JOIN products p ON i.sku_code = p.sku_code;

-- 9. VIEW: Sales Summary by SKU (only Jan 2026 onwards)
CREATE OR REPLACE VIEW sales_summary_by_sku AS
SELECT
    s.sku_code::TEXT as sku_code,
    COALESCE(SUM(s.quantity), 0)::BIGINT as jan,
    COALESCE(SUM(s.quantity), 0)::BIGINT as total,
    COALESCE(SUM(s.quantity), 0)::BIGINT as avg_qty
FROM sales s
WHERE s.sku_code IS NOT NULL AND s.sku_code != ''
  AND s.order_date::date >= '2026-01-01'
GROUP BY s.sku_code;

-- Grant execute permissions to anon and authenticated roles
GRANT EXECUTE ON FUNCTION get_sales_summary_by_sku() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_sales_by_store_summary() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_sales_by_store_monthly() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_sales_by_spg_summary() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_top_products_summary(INT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_sales_filtered(TEXT, TEXT, TEXT, INT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_sales_daily_trend() TO anon, authenticated;
GRANT SELECT ON inventory_full TO anon, authenticated;
GRANT SELECT ON sales_summary_by_sku TO anon, authenticated;
