#!/usr/bin/env python3
"""
Upload CSV Data ke Supabase Database
Untuk: ZUMA Stock & Sales Dashboard

Cara pakai:
1. Pastikan semua CSV file sudah ada di folder ini
2. Double-click "upload_data.bat" ATAU
3. Run: python upload_to_supabase.py
"""

import os
import csv
import json
import re
from datetime import datetime
from pathlib import Path

# Check if required libraries are installed
try:
    import requests
except ImportError:
    print("❌ Library 'requests' belum terinstall!")
    print("   Install dengan: pip install requests")
    input("Press Enter to exit...")
    exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("⚠️  Library 'python-dotenv' belum terinstall (optional)")
    print("   Install dengan: pip install python-dotenv")
    print("   Untuk sekarang, akan pakai hardcoded config.\n")
    load_dotenv = None

# Load environment variables
if load_dotenv:
    load_dotenv()

# Supabase Config
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://voypxpibaujymwmhavjl.supabase.co')
# Use SERVICE_ROLE key for upload (has permission to insert/update/delete)
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZveXB4cGliYXVqeW13bWhhdmpsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTExOTUwOCwiZXhwIjoyMDg0Njk1NTA4fQ.2NzFm-oezFl6Vq7K_hBdR8nAYzfPc1991FZj3eW3UFQ')

# Base headers (use service_role key for upload operations)
HEADERS = {
    'apikey': SUPABASE_SERVICE_KEY,
    'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

# Files Config
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

# Exclude non-sandal products
EXCLUDE_KEYWORDS = ['HANGER', 'GANTUNGAN', 'DISPLAY', 'AKSESORIS', 'AKSESORI',
                    'BAG ', 'TAS ', 'POUCH', 'SOCK', 'KAOS KAKI', 'DOMPET']


def is_sandal_product(name, sku):
    """Check if product is sandal (not accessories)"""
    if not name and not sku:
        return True

    upper_name = (name or '').upper()
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in upper_name:
            return False
    return True


def extract_kode_kecil(sku):
    """Extract kode kecil from SKU (remove Z + size at the end)"""
    if not sku:
        return ''
    return re.sub(r'Z\d{2,3}$', '', sku.strip(), flags=re.IGNORECASE)


def clear_table(table_name):
    """Clear all data from table"""
    print(f"  🗑️  Clearing table '{table_name}'...")
    try:
        # Delete all rows (using eq filter with a field that exists)
        url = f"{SUPABASE_URL}/rest/v1/{table_name}?id=neq.0"
        response = requests.delete(url, headers=HEADERS)

        if response.status_code in [200, 204]:
            print(f"  ✅ Table '{table_name}' cleared")
            return True
        else:
            print(f"  ⚠️  Warning: Could not clear table '{table_name}' (might be empty)")
            return True  # Continue anyway
    except Exception as e:
        print(f"  ⚠️  Error clearing table: {e}")
        return True  # Continue anyway


def upload_batch(table_name, data_batch, batch_num=None):
    """Upload batch of data to Supabase"""
    if not data_batch:
        return True

    try:
        url = f"{SUPABASE_URL}/rest/v1/{table_name}"
        response = requests.post(url, headers=HEADERS, json=data_batch)

        if response.status_code in [200, 201]:
            if batch_num:
                print(f"    ✅ Batch {batch_num}: {len(data_batch)} rows uploaded")
            return True
        else:
            print(f"    ❌ Error uploading batch: {response.status_code}")
            print(f"       Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"    ❌ Exception: {e}")
        return False


def parse_stock_csv(filepath, entity, stock_type):
    """Parse stock CSV (Warehouse or Retail) and return data list"""
    print(f"  📂 Reading: {os.path.basename(filepath)}")

    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
            content = f.read()

        # Parse CSV
        reader = csv.reader(content.splitlines(), delimiter=';')
        rows = list(reader)

        # Find header row (contains 'Kode Variant' or similar)
        header_row = -1
        for i, row in enumerate(rows):
            if any('KODE' in str(cell).upper() for cell in row):
                header_row = i
                break

        if header_row == -1:
            print(f"    ⚠️  Header not found, skipping")
            return []

        # Parse header to get store/warehouse columns
        header = rows[header_row]
        store_columns = {}
        for idx, col in enumerate(header):
            col_clean = str(col).strip()
            if col_clean and idx > 2:  # Skip first 3 columns (SKU, Kode, Nama)
                if 'TOTAL' not in col_clean.upper():
                    store_columns[idx] = col_clean

        # Parse data rows
        inventory_data = []
        for row in rows[header_row + 1:]:
            if len(row) < 3:
                continue

            # Extract basic info
            sku = str(row[0]).strip().upper() if len(row) > 0 else ''
            name = str(row[2]).strip() if len(row) > 2 else ''  # Column 2 usually has name

            if not sku or not is_sandal_product(name, sku):
                continue

            # Parse size from name (e.g., "BABY BATMAN 1, 23/24, BLUE" -> size = "23/24")
            size = ''
            if ',' in name:
                parts = [p.strip() for p in name.split(',')]
                for part in parts:
                    if '/' in part or part.isdigit():
                        size = part
                        break

            # Extract kode kecil
            kode_kecil = extract_kode_kecil(sku)

            # Parse stock per store
            store_stock = {}
            total = 0
            for col_idx, store_name in store_columns.items():
                if col_idx < len(row):
                    try:
                        stock = int(row[col_idx]) if row[col_idx].strip() else 0
                        store_stock[store_name] = stock
                        total += stock
                    except:
                        store_stock[store_name] = 0

            # Create inventory record
            inventory_data.append({
                'sku': sku,
                'kode_kecil': kode_kecil,
                'name': name,
                'size': size,
                'entity': entity,
                'type': stock_type,
                'store_stock': json.dumps(store_stock),
                'total': total
            })

        print(f"    ✅ Parsed {len(inventory_data)} items")
        return inventory_data

    except Exception as e:
        print(f"    ❌ Error parsing CSV: {e}")
        return []


def upload_inventory():
    """Upload all inventory data (Stock WH + Retail)"""
    print("\n" + "="*60)
    print("📦 UPLOADING INVENTORY DATA")
    print("="*60)

    # Clear existing data
    clear_table('inventory')

    all_inventory = []

    # Process each entity
    for entity, files in FILES_CONFIG.items():
        print(f"\n🏢 Processing {entity}...")

        # Warehouse
        if files['warehouse']:
            wh_file = os.path.join(os.path.dirname(__file__), files['warehouse'])
            if os.path.exists(wh_file):
                data = parse_stock_csv(wh_file, entity, 'warehouse')
                all_inventory.extend(data)
            else:
                print(f"    ⚠️  File not found: {files['warehouse']}")

        # Retail
        if files['retail']:
            retail_file = os.path.join(os.path.dirname(__file__), files['retail'])
            if os.path.exists(retail_file):
                data = parse_stock_csv(retail_file, entity, 'retail')
                all_inventory.extend(data)
            else:
                print(f"    ⚠️  File not found: {files['retail']}")

    # Upload in batches (1000 rows per batch)
    print(f"\n📤 Uploading {len(all_inventory)} inventory items...")
    batch_size = 1000
    for i in range(0, len(all_inventory), batch_size):
        batch = all_inventory[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(all_inventory) + batch_size - 1) // batch_size
        print(f"  📦 Batch {batch_num}/{total_batches}...")
        upload_batch('inventory', batch, batch_num)

    print(f"\n✅ Inventory upload complete! Total: {len(all_inventory)} items")


def upload_sales_summary():
    """Upload sales summary data (salesss.csv)"""
    print("\n" + "="*60)
    print("📊 UPLOADING SALES SUMMARY DATA")
    print("="*60)

    sales_file = os.path.join(os.path.dirname(__file__), 'salesss.csv')
    if not os.path.exists(sales_file):
        print(f"  ⚠️  File not found: salesss.csv (skipping)")
        return

    # Clear existing data
    clear_table('sales_summary')

    print(f"  📂 Reading: salesss.csv")

    try:
        with open(sales_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)

        # Aggregate sales by SKU and month
        sales_data = {}
        for row in rows[1:]:  # Skip header
            if len(row) < 16:
                continue

            try:
                date_str = row[0].split()[0]  # YYYY-MM-DD
                month = date_str[5:7]  # MM
                sku = row[15].strip().upper()  # SKU column
                qty = int(row[13]) if row[13].strip() else 1  # Quantity

                if not sku:
                    continue

                if sku not in sales_data:
                    sales_data[sku] = {'nov': 0, 'des': 0, 'jan': 0}

                if month == '11':
                    sales_data[sku]['nov'] += qty
                elif month == '12':
                    sales_data[sku]['des'] += qty
                elif month == '01':
                    sales_data[sku]['jan'] += qty
            except:
                continue

        # Convert to list
        sales_list = [
            {
                'sku': sku,
                'nov': data['nov'],
                'des': data['des'],
                'jan': data['jan']
            }
            for sku, data in sales_data.items()
        ]

        print(f"    ✅ Parsed {len(sales_list)} SKUs with sales data")

        # Upload in batches
        print(f"\n📤 Uploading {len(sales_list)} sales records...")
        batch_size = 1000
        for i in range(0, len(sales_list), batch_size):
            batch = sales_list[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(sales_list) + batch_size - 1) // batch_size
            print(f"  📦 Batch {batch_num}/{total_batches}...")
            upload_batch('sales_summary', batch, batch_num)

        print(f"\n✅ Sales summary upload complete! Total: {len(sales_list)} SKUs")

    except Exception as e:
        print(f"    ❌ Error: {e}")


def upload_sales_detail():
    """Upload detailed sales data (sales_2026.csv)"""
    print("\n" + "="*60)
    print("📈 UPLOADING SALES DETAIL DATA")
    print("="*60)

    sales_file = os.path.join(os.path.dirname(__file__), 'sales_2026.csv')
    if not os.path.exists(sales_file):
        print(f"  ⚠️  File not found: sales_2026.csv (skipping)")
        return

    # Clear existing data
    clear_table('sales_detail')

    print(f"  📂 Reading: sales_2026.csv")
    print(f"  ⚠️  This might take a while for large files...")

    try:
        with open(sales_file, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)

        sales_detail = []
        for idx, row in enumerate(rows[1:], 1):  # Skip header
            if len(row) < 20:
                continue

            try:
                # Parse date
                tanggal_str = row[0].split()[0] if row[0] else None

                # Helper function to parse numeric
                def parse_num(val):
                    try:
                        return float(val.replace(',', '')) if val else 0
                    except:
                        return 0

                sales_detail.append({
                    'tanggal': tanggal_str,
                    'toko': row[1].strip() if len(row) > 1 else '',
                    'tipe_produk': row[2].strip() if len(row) > 2 else '',
                    'barcode': row[3].strip() if len(row) > 3 else '',
                    'kasir': row[6].strip() if len(row) > 6 else '',
                    'jumlah': int(row[13]) if len(row) > 13 and row[13].strip() else 0,
                    'produk': row[14].strip() if len(row) > 14 else '',
                    'sku': row[15].strip().upper() if len(row) > 15 else '',
                    'price': parse_num(row[17]) if len(row) > 17 else 0,
                    'persentase_diskon': parse_num(row[18]) if len(row) > 18 else 0,
                    'total': parse_num(row[22]) if len(row) > 22 else 0,
                    'promosi': row[24].strip() if len(row) > 24 else '',
                    'nama_server': row[36].strip() if len(row) > 36 else ''
                })

                # Show progress every 10000 rows
                if idx % 10000 == 0:
                    print(f"    Processing... {idx} rows")

            except Exception as e:
                continue

        print(f"    ✅ Parsed {len(sales_detail)} transactions")

        # Upload in batches
        print(f"\n📤 Uploading {len(sales_detail)} transactions...")
        batch_size = 1000
        for i in range(0, len(sales_detail), batch_size):
            batch = sales_detail[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(sales_detail) + batch_size - 1) // batch_size
            print(f"  📦 Batch {batch_num}/{total_batches}...")
            upload_batch('sales_detail', batch, batch_num)

        print(f"\n✅ Sales detail upload complete! Total: {len(sales_detail)} transactions")

    except Exception as e:
        print(f"    ❌ Error: {e}")


def main():
    """Main function"""
    print("\n" + "="*60)
    print("🚀 ZUMA DASHBOARD - DATA UPLOAD TO SUPABASE")
    print("="*60)
    print(f"Database: {SUPABASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Upload all data
    upload_inventory()
    upload_sales_summary()
    upload_sales_detail()

    print("\n" + "="*60)
    print("✅ ALL DATA UPLOADED SUCCESSFULLY!")
    print("="*60)
    print("\nSekarang dashboard bisa diakses dengan data dari Supabase.")
    print("Tekan Enter untuk keluar...")
    input()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Upload dibatalkan oleh user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        input("Press Enter to exit...")
