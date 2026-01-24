#!/usr/bin/env python3
"""
Generate Dashboard dari data Supabase
Fetches data dari Supabase dan generate dashboard_inventory.html

Cara pakai: python generate_dashboard_supabase.py
"""

import csv
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

# Master data for enriching product info
MASTER_DATA = {}

def load_master_data():
    """Load master data from CSV for product info"""
    global MASTER_DATA

    filepath = Path(__file__).parent / "master_data_full.csv"
    if not filepath.exists():
        print("Warning: master_data_full.csv not found")
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

    print(f"Loaded {len(MASTER_DATA)} SKU from master data")

def extract_kode_kecil(sku):
    """Extract kode kecil from SKU"""
    if not sku:
        return ''
    return re.sub(r'Z\d{2,3}$', '', sku.strip(), flags=re.IGNORECASE)

def get_product_info(sku):
    """Get enriched product info"""
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
    """Fetch all inventory data from Supabase"""
    print("Fetching inventory data from Supabase...")

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
            print(f"Error fetching data: {resp.status_code}")
            break

        data = resp.json()
        if not data:
            break

        all_data.extend(data)
        offset += limit

        if len(data) < limit:
            break

        print(f"  Fetched {len(all_data)} records...")

    print(f"Total: {len(all_data)} inventory records")
    return all_data

def transform_to_dashboard_format(inventory_data):
    """Transform flat Supabase data to nested dashboard format"""

    # Group by entity, then by location_type, then by SKU
    entity_data = defaultdict(lambda: {'warehouse': {}, 'retail': {}})

    for record in inventory_data:
        entity = record.get('entity', 'DDD')
        loc_type = record.get('location_type', 'retail')
        sku = record.get('sku_code', '')
        loc_name = record.get('location_name', '')
        qty = record.get('quantity', 0)
        product_name = record.get('product_name', '')

        if not sku:
            continue

        # Get enriched product info
        info = get_product_info(sku)

        # Initialize SKU entry if not exists
        if sku not in entity_data[entity][loc_type]:
            # Parse name to extract info
            name_parts = product_name.split(',') if product_name else []
            base_name = name_parts[0].strip() if name_parts else info['name']

            entity_data[entity][loc_type][sku] = {
                'sku': sku,
                'kode_kecil': info['kode_kecil'] or extract_kode_kecil(sku),
                'name': base_name,
                'size': info['size'] or '',
                'category': info['gender'] or 'UNISEX',
                'gender': info['gender'] or '',
                'series': info['series'] or '',
                'tipe': 'Jepit',
                'tier': info['tier'] or '',
                'color': '',
                'total': 0,
                'store_stock': {},
                'entity': entity,
                'type': loc_type
            }

        # Add stock for this location
        entity_data[entity][loc_type][sku]['store_stock'][loc_name] = qty
        entity_data[entity][loc_type][sku]['total'] += qty

    # Convert to list format
    result = {}
    for entity, types in entity_data.items():
        result[entity] = {
            'warehouse': list(types['warehouse'].values()),
            'retail': list(types['retail'].values())
        }

    return result

def generate_dashboard(all_data):
    """Generate dashboard HTML with embedded data"""

    # Read template from original dashboard (first 1377 lines = HTML structure)
    template_path = Path(__file__).parent / "dashboard_inventory_original.html"

    if not template_path.exists():
        # Fallback to current dashboard
        template_path = Path(__file__).parent / "dashboard_inventory.html"

    if not template_path.exists():
        print("Error: No template dashboard found")
        return None

    print(f"Using template: {template_path}")

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the position of 'const allData = '
    alldata_pos = content.find('const allData = ')
    if alldata_pos == -1:
        print("Error: Could not find 'const allData' in template")
        return None

    # Find the end of allData (next 'const' or ';' pattern)
    # Look for pattern: };  followed by whitespace and const
    end_pattern = re.search(r'const allData = .*?;\s*\n\s*const', content[alldata_pos:], re.DOTALL)
    if end_pattern:
        end_pos = alldata_pos + end_pattern.end() - 5  # -5 to keep 'const'
    else:
        print("Warning: Could not find end of allData, trying alternative method")
        # Alternative: find the matching closing brace
        # For now, use a large chunk replacement
        end_pos = content.find('const allStores', alldata_pos)
        if end_pos == -1:
            print("Error: Could not find allStores marker")
            return None

    # Build new data string
    new_alldata = f'const allData = {json.dumps(all_data, ensure_ascii=False)};\n        '

    # Replace
    new_content = content[:alldata_pos] + new_alldata + content[end_pos:]

    return new_content

def main():
    print("=" * 60)
    print("GENERATE DASHBOARD DARI SUPABASE")
    print("=" * 60)

    # Load master data for enrichment
    load_master_data()

    # Fetch data from Supabase
    inventory_data = fetch_inventory_data()

    if not inventory_data:
        print("No data found in Supabase!")
        return

    # Transform to dashboard format
    print("\nTransforming data to dashboard format...")
    all_data = transform_to_dashboard_format(inventory_data)

    # Print summary
    for entity, data in all_data.items():
        wh_count = len(data.get('warehouse', []))
        rt_count = len(data.get('retail', []))
        print(f"  {entity}: {wh_count} warehouse SKUs, {rt_count} retail SKUs")

    # Generate dashboard
    print("\nGenerating dashboard HTML...")
    html_content = generate_dashboard(all_data)

    if html_content:
        output_path = Path(__file__).parent / "dashboard_inventory.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nDashboard saved to: {output_path}")
        print(f"File size: {len(html_content):,} bytes")
        print("=" * 60)
    else:
        print("Failed to generate dashboard!")

if __name__ == "__main__":
    main()
