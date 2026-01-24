#!/usr/bin/env python3
"""
Generate Dashboard dari Supabase - CORRECT VERSION
Mengambil HTML/CSS/JS dari original, hanya mengganti allData dengan data dari Supabase

Cara pakai: python generate_dashboard_from_supabase.py
"""

import json
import requests
import re
from collections import defaultdict
from pathlib import Path

# Supabase Configuration
SUPABASE_URL = "https://usxmptrqsovoxvrburvp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVzeG1wdHJxc292b3h2cmJ1cnZwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxODA2NzMsImV4cCI6MjA4NDc1NjY3M30.JkznqF6YWFgg22ta9F8feZuFbRPkHqkpDnJdm2G4C5Q"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# Load master data for enrichment
MASTER_DATA = {}

def load_master_data():
    """Load master data dari CSV"""
    global MASTER_DATA
    import csv

    filepath = Path(__file__).parent / "master_data_full.csv"
    if not filepath.exists():
        print("Warning: master_data_full.csv tidak ditemukan")
        return

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        rows = list(reader)

    for row in rows[3:]:
        if len(row) < 10:
            continue
        sku = row[0].strip().upper()
        if not sku:
            continue

        MASTER_DATA[sku] = {
            'kode_kecil': row[1].strip().upper() if len(row) > 1 else '',
            'name': row[3].strip() if len(row) > 3 else '',
            'variant_name': row[4].strip() if len(row) > 4 else '',
            'size': row[5].strip() if len(row) > 5 else '',
            'tier': row[6].strip() if len(row) > 6 else '',
            'gender': row[7].strip() if len(row) > 7 else '',
            'series': row[9].strip() if len(row) > 9 else ''
        }

    print(f"Loaded {len(MASTER_DATA)} SKU dari master data")

def extract_kode_kecil(sku):
    """Extract kode kecil dari SKU"""
    if not sku:
        return ''
    return re.sub(r'Z\d{2,3}$', '', sku.strip(), flags=re.IGNORECASE)

def get_product_info(sku):
    """Get product info dari master data"""
    sku_upper = sku.upper().strip()
    if sku_upper in MASTER_DATA:
        return MASTER_DATA[sku_upper]
    return {
        'kode_kecil': extract_kode_kecil(sku),
        'name': '',
        'variant_name': '',
        'size': '',
        'tier': '',
        'gender': '',
        'series': ''
    }

def fetch_inventory_data():
    """Fetch semua data inventory dari Supabase"""
    print("Fetching data dari Supabase...")

    all_data = []
    offset = 0
    limit = 1000

    while True:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/inventory?select=*&limit={limit}&offset={offset}",
            headers=headers,
            timeout=60
        )

        if resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            break

        data = resp.json()
        if not data:
            break

        all_data.extend(data)
        offset += limit

        if len(data) < limit:
            break

        if offset % 5000 == 0:
            print(f"  Fetched {len(all_data)} records...")

    print(f"Total: {len(all_data)} records")
    return all_data

def transform_to_alldata_format(inventory_data):
    """
    Transform flat Supabase data ke format allData yang dipakai dashboard original.

    Format allData:
    {
        "DDD": {
            "warehouse": [
                {
                    "sku": "Z2BT01Z24",
                    "kode_kecil": "Z2BT01",
                    "name": "BABY BATMAN 1, BLUE",
                    "size": "23/24",
                    "category": "BABY",
                    "gender": "BABY",
                    "series": "BATMAN",
                    "tipe": "Jepit",
                    "tier": "1",
                    "color": "BLUE",
                    "total": 102,
                    "store_stock": {
                        "Warehouse Bali Gatsu - Box": 0,
                        "Warehouse Pluit": 49,
                        ...
                    },
                    "entity": "DDD",
                    "type": "warehouse"
                },
                ...
            ],
            "retail": [...]
        },
        "LJBB": {...},
        ...
    }
    """

    # Group by entity -> location_type -> sku
    entity_data = defaultdict(lambda: {'warehouse': {}, 'retail': {}})

    for record in inventory_data:
        entity = record.get('entity', 'DDD')
        loc_type = record.get('location_type', 'retail')
        sku = record.get('sku_code', '')
        loc_name = record.get('location_name', '')
        qty = record.get('quantity', 0) or 0
        product_name = record.get('product_name', '')

        if not sku:
            continue

        # Get enriched product info from master data
        info = get_product_info(sku)

        # Initialize SKU entry if not exists
        if sku not in entity_data[entity][loc_type]:
            # Parse product name for additional info
            name_parts = product_name.split(',') if product_name else []
            base_name = name_parts[0].strip() if name_parts else (info['variant_name'] or info['name'])

            # Extract size from product name or SKU
            size = ''
            if len(name_parts) >= 2:
                size = name_parts[1].strip()
            elif info['size']:
                size = info['size']

            # Extract color
            color = ''
            if len(name_parts) >= 3:
                color = name_parts[2].strip()

            # Determine category from gender
            gender = info['gender'] or 'UNISEX'
            category = gender

            entity_data[entity][loc_type][sku] = {
                'sku': sku,
                'kode_kecil': info['kode_kecil'] or extract_kode_kecil(sku),
                'name': base_name,
                'size': size,
                'category': category,
                'gender': gender,
                'series': info['series'] or '',
                'tipe': 'Jepit',
                'tier': info['tier'] or '',
                'color': color,
                'total': 0,
                'store_stock': {},
                'entity': entity,
                'type': loc_type
            }

        # Add stock for this location
        entity_data[entity][loc_type][sku]['store_stock'][loc_name] = qty
        entity_data[entity][loc_type][sku]['total'] += qty

    # Convert to list format (same as original allData)
    result = {}
    for entity, types in entity_data.items():
        result[entity] = {
            'warehouse': list(types['warehouse'].values()),
            'retail': list(types['retail'].values())
        }

    return result

def generate_dashboard(all_data):
    """Generate dashboard HTML dengan mengganti allData di template original"""

    template_path = Path(__file__).parent / "dashboard_inventory_original.html"

    if not template_path.exists():
        print("Error: dashboard_inventory_original.html tidak ditemukan!")
        return None

    print(f"Membaca template: {template_path}")

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Cari posisi "const allData = "
    pattern = r'const allData = \{.*?\};\s*\n\s*const allStores'

    # Buat replacement string
    new_alldata = f'const allData = {json.dumps(all_data, ensure_ascii=False)};\n        const allStores'

    # Replace menggunakan regex
    new_content = re.sub(pattern, new_alldata, content, flags=re.DOTALL)

    # Verifikasi replacement berhasil
    if 'const allData = {' in new_content and '"DDD"' in new_content[:50000]:
        print("Data berhasil di-replace!")
    else:
        print("Warning: Replacement mungkin tidak berhasil")

    return new_content

def main():
    print("=" * 60)
    print("GENERATE DASHBOARD DARI SUPABASE")
    print("=" * 60)

    # Load master data
    load_master_data()

    # Fetch dari Supabase
    inventory_data = fetch_inventory_data()

    if not inventory_data:
        print("Tidak ada data!")
        return

    # Transform ke format allData
    print("\nTransforming data...")
    all_data = transform_to_alldata_format(inventory_data)

    # Print summary
    for entity, data in all_data.items():
        wh_count = len(data.get('warehouse', []))
        rt_count = len(data.get('retail', []))
        print(f"  {entity}: {wh_count} warehouse SKUs, {rt_count} retail SKUs")

    # Generate dashboard
    print("\nGenerating dashboard...")
    html_content = generate_dashboard(all_data)

    if html_content:
        # Save ke dashboard_inventory.html
        output_path = Path(__file__).parent / "dashboard_inventory.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nDashboard saved: {output_path}")
        print(f"File size: {len(html_content):,} bytes")

        # Copy ke index.html
        index_path = Path(__file__).parent / "index.html"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Copied to: {index_path}")

        print("=" * 60)
        print("SELESAI! Dashboard sudah di-generate dari Supabase.")
        print("=" * 60)
    else:
        print("Gagal generate dashboard!")

if __name__ == "__main__":
    main()
