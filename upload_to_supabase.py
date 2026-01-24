#!/usr/bin/env python3
"""
Script untuk upload data CSV ke Supabase
- Master data produk
- Stock warehouse (DDD, LJBB, MBB, UBB)
- Stock retail (DDD)

Jalankan: python upload_to_supabase.py
"""

import csv
import json
import requests
import time
import re
from pathlib import Path

# Supabase Configuration
SUPABASE_URL = "https://usxmptrqsovoxvrburvp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVzeG1wdHJxc292b3h2cmJ1cnZwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxODA2NzMsImV4cCI6MjA4NDc1NjY3M30.JkznqF6YWFgg22ta9F8feZuFbRPkHqkpDnJdm2G4C5Q"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# Headers for upsert (conflict resolution on unique constraint)
# The unique constraint is: inventory_unique_sku_location_entity
# Columns: sku_code, location_name, entity
headers_upsert = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal"
}

# File configuration
FILES_CONFIG = {
    'DDD': {
        'warehouse': 'Stock WH DDD.csv',
        'retail': 'Stok Retail DDD.csv'
    },
    'LJBB': {
        'warehouse': 'Stock WH LJBB.csv',
        'retail': None
    },
    'MBB': {
        'warehouse': 'Stock WH MBB.csv',
        'retail': None
    },
    'UBB': {
        'warehouse': 'Stock WH UBB.csv',
        'retail': None
    }
}

# Global data
MASTER_DATA = {}  # {sku: {kode_kecil, name, size, tier, gender, series}}

def extract_kode_kecil(sku):
    """Extract kode kecil dari SKU dengan menghilangkan Z+size di akhir"""
    if not sku:
        return ''
    kode_kecil = re.sub(r'Z\d{2,3}$', '', sku.strip(), flags=re.IGNORECASE)
    return kode_kecil

def load_master_data():
    """Load master data dari master_data_full.csv"""
    global MASTER_DATA
    MASTER_DATA = {}

    filepath = Path(__file__).parent / "master_data_full.csv"
    if not filepath.exists():
        print("WARNING: master_data_full.csv tidak ditemukan")
        return

    print("=== Loading Master Data ===")
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Skip header rows (0-2), data starts at row 3
    for row in rows[3:]:
        if len(row) < 10:
            continue

        sku = row[0].strip().upper()
        if not sku:
            continue

        MASTER_DATA[sku] = {
            'kode_kecil': row[1].strip().upper() if len(row) > 1 else extract_kode_kecil(sku),
            'name': row[4].strip() if len(row) > 4 else row[3].strip() if len(row) > 3 else '',
            'size': row[5].strip() if len(row) > 5 else '',
            'tier': row[6].strip() if len(row) > 6 else '',
            'gender': row[7].strip() if len(row) > 7 else '',
            'series': row[9].strip() if len(row) > 9 else ''
        }

    print(f"Loaded {len(MASTER_DATA)} SKU dari master data")

def get_product_info(sku):
    """Get product info dari master data"""
    sku_upper = sku.upper().strip()
    if sku_upper in MASTER_DATA:
        return MASTER_DATA[sku_upper]
    return {
        'kode_kecil': extract_kode_kecil(sku),
        'name': '',
        'size': '',
        'tier': '',
        'gender': '',
        'series': ''
    }

def clear_inventory_table():
    """Clear existing inventory data in batches"""
    print("\n=== Clearing inventory table ===")
    total_deleted = 0

    while True:
        try:
            # Get IDs to delete (batch of 1000)
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/inventory?select=id&limit=1000",
                headers=headers,
                timeout=60
            )
            if resp.status_code != 200:
                print(f"Error getting IDs: {resp.status_code}")
                break

            ids = [r['id'] for r in resp.json()]
            if not ids:
                break

            # Delete by ID range
            min_id = min(ids)
            max_id = max(ids)
            resp = requests.delete(
                f"{SUPABASE_URL}/rest/v1/inventory?id=gte.{min_id}&id=lte.{max_id}",
                headers=headers,
                timeout=60
            )
            if resp.status_code in [200, 204]:
                total_deleted += len(ids)
                print(f"  Deleted batch ({len(ids)} records), total: {total_deleted}")
            else:
                print(f"Warning: Could not delete batch - {resp.status_code}")
                break

            time.sleep(0.2)  # Rate limiting

        except Exception as e:
            print(f"Error clearing table: {e}")
            break

    print(f"Total deleted: {total_deleted}")

def parse_warehouse_csv(filepath, entity):
    """Parse warehouse CSV file and return inventory records"""
    records = []

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    # Header is on line 5 (index 4)
    header_line = lines[4] if len(lines) > 4 else ""

    # Detect format based on entity and header structure
    # DDD: Nama Barang;;Kode Barang;;WH1;WH2;...;;Total
    # LJBB: ;;Kode Barang;WH1;Total;;
    # MBB/UBB: Nama Barang;;;Kode Barang;WH1;WH2;...;Total;

    warehouses = []
    sku_col_idx = -1
    wh_start_idx = -1
    has_product_name = True

    if ';;' in header_line and ';;;' not in header_line:
        # DDD format: Nama Barang;;Kode Barang;;WH1;WH2;...;;Total
        header_sections = header_line.strip().split(';;')
        if len(header_sections) >= 3:
            warehouse_part = header_sections[2]
            warehouses = [w.strip() for w in warehouse_part.split(';')
                         if w.strip() and 'Total' not in w]
    elif ';;;' in header_line:
        # MBB/UBB format: Nama Barang;;;Kode Barang;WH1;WH2;...;Total;
        parts = header_line.strip().split(';')
        # Find Kode Barang position
        for i, p in enumerate(parts):
            if 'Kode Barang' in p:
                sku_col_idx = i
                wh_start_idx = i + 1
                break
        if wh_start_idx > 0:
            warehouses = [p.strip() for p in parts[wh_start_idx:]
                         if p.strip() and 'Total' not in p]
    else:
        # LJBB format: ;;Kode Barang;WH1;Total;;
        parts = header_line.strip().split(';')
        for i, p in enumerate(parts):
            if 'Kode Barang' in p:
                sku_col_idx = i
                wh_start_idx = i + 1
                has_product_name = False
                break
        if wh_start_idx > 0:
            warehouses = [p.strip() for p in parts[wh_start_idx:]
                         if p.strip() and 'Total' not in p]

    print(f"  Found warehouses: {warehouses[:5]}...")
    print(f"  Total warehouse columns: {len(warehouses)}")

    # Parse data rows
    current_product_name = ""
    for line in lines[5:]:  # Data starts after header
        line = line.strip()
        if not line or 'Total Kode Barang' in line:
            continue

        if ';;' in line and ';;;' not in line:
            # DDD format
            sections = line.split(';;')
            if len(sections) < 3:
                continue
            name_part = sections[0].strip().strip('"')
            if name_part:
                current_product_name = name_part
            sku = sections[1].strip()
            if not sku:
                continue
            quantities = sections[2].split(';') if sections[2] else []
        elif ';;;' in line:
            # MBB/UBB format
            parts = line.split(';')
            name_part = parts[0].strip().strip('"') if parts else ''
            if name_part:
                current_product_name = name_part
            sku = parts[3].strip() if len(parts) > 3 else ''
            if not sku:
                continue
            quantities = parts[4:] if len(parts) > 4 else []
        else:
            # LJBB format (single semicolons)
            parts = line.split(';')
            if sku_col_idx >= 0 and len(parts) > sku_col_idx:
                sku = parts[sku_col_idx].strip()
                if not sku:
                    continue
                quantities = parts[wh_start_idx:] if wh_start_idx > 0 else []
            else:
                continue

        # Get product info from master data
        info = get_product_info(sku)
        product_name = current_product_name if current_product_name else info['name']

        # Create records for each warehouse
        for i, wh_name in enumerate(warehouses):
            if i >= len(quantities):
                break

            try:
                # Handle "0," format (with trailing comma)
                qty_str = quantities[i].strip().replace(',', '').replace('"', '')
                qty = int(float(qty_str)) if qty_str and qty_str != '-' else 0
            except:
                qty = 0

            if qty != 0:  # Only store non-zero quantities
                records.append({
                    'sku_code': sku.upper(),
                    'product_name': product_name,
                    'entity': entity,
                    'location_type': 'warehouse',
                    'location_name': wh_name,
                    'quantity': qty
                })

    return records

def parse_retail_csv(filepath, entity):
    """Parse retail CSV file and return inventory records"""
    records = []

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    # Header is on line 5 (index 4)
    header_line = lines[4] if len(lines) > 4 else ""
    parts = header_line.strip().split(';')

    # Skip first 2 columns (Nama Barang, Kode Barang), rest are store names
    stores = []
    for i, col in enumerate(parts[2:]):
        col = col.strip()
        if col and col != 'Total Nama Gudang':
            stores.append(col)

    print(f"  Found stores: {len(stores)} stores")

    # Parse data rows
    current_product_name = ""
    for line in lines[5:]:
        line = line.strip()
        if not line:
            continue

        parts = line.split(';')
        if len(parts) < 3:
            continue

        name_part = parts[0].strip().strip('"')
        if name_part:
            current_product_name = name_part

        sku = parts[1].strip()
        if not sku:
            continue

        quantities = parts[2:]

        # Get product info
        info = get_product_info(sku)
        product_name = current_product_name if current_product_name else info['name']

        # Create records for each store
        for i, store_name in enumerate(stores):
            if i >= len(quantities):
                break

            try:
                qty_str = quantities[i].strip().replace(',', '')
                qty = int(qty_str) if qty_str and qty_str != '-' else 0
            except:
                qty = 0

            if qty != 0:  # Only store non-zero quantities
                records.append({
                    'sku_code': sku.upper(),
                    'product_name': product_name,
                    'entity': entity,
                    'location_type': 'retail',
                    'location_name': store_name,
                    'quantity': qty
                })

    return records

def upload_batch(records, batch_size=100):
    """Upload records to Supabase in batches using upsert"""
    total = len(records)
    uploaded = 0
    failed = 0

    # Upsert URL with on_conflict parameter
    # Conflict columns from unique constraint: sku_code, location_name, entity
    upsert_url = f"{SUPABASE_URL}/rest/v1/inventory?on_conflict=sku_code,location_name,entity"

    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        try:
            # Use POST with upsert headers to handle duplicates
            resp = requests.post(
                upsert_url,
                headers=headers_upsert,
                json=batch,
                timeout=60
            )
            if resp.status_code in [200, 201]:
                uploaded += len(batch)
            else:
                failed += len(batch)
                if failed <= batch_size:
                    print(f"  Error: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            failed += len(batch)
            print(f"  Exception: {e}")

        # Progress
        if (i + batch_size) % 500 == 0 or i + batch_size >= total:
            print(f"  Progress: {min(i+batch_size, total)}/{total} | Uploaded: {uploaded} | Failed: {failed}")

        time.sleep(0.1)  # Rate limiting

    return uploaded, failed

def main():
    print("=" * 60)
    print("UPLOAD CSV DATA KE SUPABASE")
    print("=" * 60)

    # Load master data first
    load_master_data()

    # Skip clearing - use upsert instead to update existing records
    print("\n=== Skipping clear (using upsert mode) ===")

    all_records = []

    # Process each entity
    for entity, files in FILES_CONFIG.items():
        print(f"\n=== Processing {entity} ===")

        # Warehouse
        wh_file = files.get('warehouse')
        if wh_file:
            filepath = Path(__file__).parent / wh_file
            if filepath.exists():
                print(f"  Loading warehouse: {wh_file}")
                records = parse_warehouse_csv(filepath, entity)
                print(f"  Found {len(records)} warehouse records")
                all_records.extend(records)
            else:
                print(f"  WARNING: {wh_file} not found")

        # Retail
        retail_file = files.get('retail')
        if retail_file:
            filepath = Path(__file__).parent / retail_file
            if filepath.exists():
                print(f"  Loading retail: {retail_file}")
                records = parse_retail_csv(filepath, entity)
                print(f"  Found {len(records)} retail records")
                all_records.extend(records)
            else:
                print(f"  WARNING: {retail_file} not found")

    print(f"\n=== Total: {len(all_records)} records to upload ===")

    # Upload to Supabase
    print("\n=== Uploading to Supabase ===")
    uploaded, failed = upload_batch(all_records, batch_size=100)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total records: {len(all_records)}")
    print(f"Uploaded: {uploaded}")
    print(f"Failed: {failed}")
    print("=" * 60)

if __name__ == "__main__":
    main()
