#!/usr/bin/env python3
"""
Script untuk generate dashboard inventory dengan data embedded
Jalankan: python generate_dashboard.py
Output: dashboard_inventory.html
"""

import csv
import json
import os
import re
import io
import base64
from pathlib import Path
from collections import defaultdict

# Untuk fetch dari Google Sheets
try:
    import urllib.request
    import ssl
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

# Load logos as base64
def load_logo_base64(filename):
    """Load image file and convert to base64 data URI"""
    try:
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            with open(filepath, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{data}"
    except Exception as e:
        print(f"Warning: Could not load logo {filename}: {e}")
    return ""

# Load all logos
LOGO_ZUMA = load_logo_base64("ZUMA_FINAL LOGO_UPDATED-07.png")
LOGO_DDD = load_logo_base64("b.png")
LOGO_LJBB = load_logo_base64("ljbb.png")
LOGO_MBB = load_logo_base64("mbb.png")
LOGO_UBB = load_logo_base64("a.png")

# Konfigurasi file
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

# Toko dengan data DOUBLED (perlu dibagi 2) - karena export dari sistem punya duplikat kode lama & baru
DOUBLED_STORES = {
    'zuma city of tomorrow mall': 0.5,  # Data dobel, kalikan 0.5
    'zuma tanah lot': 0.5,
    'zuma lippo bali': 0.5,
}

# Google Sheets Configuration
# Base URL untuk spreadsheet
SPREADSHEET_BASE = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vRMI13PjlcKpGxF2QKXIkn0-QS0bVsqrw2MZVRVcm8l7jt_lT2sKgRcFYnVDDqmT5LUzPm8nFxMTgS9/pub'

# GID untuk masing-masing sheet
SHEET_GID = {
    'master_produk': 813944059,  # Sheet Master Produk (Kolom B: Kode Kecil, C: Article, G: Tier)
    'master_data': 0,            # Sheet Master Data (Kolom A: Kode SKU, B: Kode Kecil, D: Nama, H: Gender, J: Series)
    'master_store': 1803569317,  # Sheet Master Store/Warehouse (mapping area)
    'max_stock': 382740121,      # Sheet Max Stock per store/warehouse
    'master_assortment': 1063661008,  # Sheet Master Assortment (Kolom B: Kode Kecil, C: Assorment)
}

# File Master Produk (backup jika online gagal)
MASTER_PRODUK_FILE = 'Master Produk.csv'

# Global master data
MASTER_DATA = {}      # {kode_sku: {kode_kecil, nama, gender, series, tier}}
MASTER_PRODUK = {}    # {kode_kecil: {nama, series, gender, tipe, tier}} - dari Master Produk jika ada
MASTER_PRODUK_BY_ARTICLE = {}  # {article_upper: tier} - untuk lookup tier by nama artikel
STORE_AREA_MAP = {}   # {store_name_lower: area} - dari Master Store/Warehouse
MAX_STOCK_MAP = {}    # {store_name_lower: max_stock} - dari sheet Max Stock
MASTER_ASSORTMENT = {}  # {kode_kecil_upper: assortment} - dari sheet Master Assortment

# Filter: Exclude produk non-sandal
EXCLUDE_KEYWORDS = ['HANGER', 'GANTUNGAN', 'DISPLAY', 'AKSESORIS', 'AKSESORI',
                    'BAG ', 'TAS ', 'POUCH', 'SOCK', 'KAOS KAKI', 'DOMPET']

def is_sandal_product(name, sku):
    """Check apakah produk adalah sandal (bukan aksesori/lainnya)"""
    if not name and not sku:
        return True  # Default include jika tidak ada info

    upper_name = (name or '').upper()
    upper_sku = (sku or '').upper()

    # Exclude jika nama mengandung keyword non-sandal
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in upper_name:
            return False

    return True

def extract_kode_kecil(sku):
    """Extract kode kecil dari SKU dengan menghilangkan Z+size di akhir"""
    if not sku:
        return ''
    # Hilangkan Z + 2-3 digit angka di akhir (contoh: Z24, Z26, Z100)
    kode_kecil = re.sub(r'Z\d{2,3}$', '', sku.strip(), flags=re.IGNORECASE)
    return kode_kecil

def fetch_google_sheet(gid):
    """Fetch data dari Google Sheets berdasarkan gid"""
    if not HAS_URLLIB:
        print("    ⚠ urllib tidak tersedia")
        return None

    url = f"{SPREADSHEET_BASE}?gid={gid}&single=true&output=csv"
    print(f"    Fetching: gid={gid}")

    try:
        # Create SSL context that doesn't verify (untuk menghindari SSL issues)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Create request dengan User-Agent
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Fetch dengan timeout
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            # Handle redirect
            final_url = response.geturl()
            content = response.read()

            # Try decode dengan berbagai encoding
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    text = content.decode(encoding)
                    return text
                except:
                    continue

            return content.decode('utf-8', errors='replace')

    except urllib.error.HTTPError as e:
        print(f"    ⚠ HTTP Error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"    ⚠ URL Error: {e.reason}")
        return None
    except Exception as e:
        print(f"    ⚠ Error fetching: {e}")
        return None

def load_master_data():
    """Load Master Data dari Google Sheets - mapping SKU ke info produk"""
    global MASTER_DATA
    MASTER_DATA = {}

    gid = SHEET_GID.get('master_data', 0)
    print(f"  🌐 Fetching Master Data dari Google Sheets (gid={gid})...")
    csv_content = fetch_google_sheet(gid)

    if not csv_content or len(csv_content) < 100 or 'Loading' in csv_content[:50]:
        print(f"    ⚠ Gagal fetch Master Data")
        return False

    print(f"    ✓ Berhasil fetch dari Google Sheets")

    # Parse CSV dengan csv module (handle quoted fields dengan benar)
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    if not rows:
        return False

    # Find header row - cari baris dengan "Kode Variant" atau "Kode(*)"
    header_row = 0
    for i, row in enumerate(rows[:10]):
        row_str = ''.join(str(x).lower() for x in row)
        if 'kode variant' in row_str or 'kode(*)' in row_str:
            header_row = i
            break

    # Berdasarkan struktur yang terlihat:
    # Kolom 0: Kode Variant (Kode SKU) - Z2CA01Z21
    # Kolom 1: Kode (Kode Kecil) - Z2CA01
    # Kolom 3: Nama Barang
    # Kolom 5: Size (kolom F)
    # Kolom 6: Tier
    # Kolom 7: Gender
    # Kolom 9: Series

    count = 0
    for row in rows[header_row + 1:]:
        if len(row) < 10:
            continue

        kode_sku = str(row[0]).strip().upper()
        if not kode_sku or kode_sku in ['', 'KODE VARIANT(*)', 'KODE VARIANT']:
            continue

        kode_kecil = str(row[1]).strip().upper() if len(row) > 1 else ''
        nama = str(row[3]).strip() if len(row) > 3 else ''
        size = str(row[5]).strip() if len(row) > 5 else ''  # Kolom F = index 5
        tier = str(row[6]).strip() if len(row) > 6 else ''
        gender = str(row[7]).strip() if len(row) > 7 else ''
        series = str(row[9]).strip() if len(row) > 9 else ''

        MASTER_DATA[kode_sku] = {
            'kode_kecil': kode_kecil,
            'nama': nama,
            'size': size,
            'tier': tier,
            'gender': gender,
            'series': series
        }
        count += 1

    print(f"    -> {count} SKU loaded dari Master Data")
    return count > 0

def load_master_produk():
    """Load Master Produk dari Google Sheets - Tier per Kode Kecil"""
    global MASTER_PRODUK
    MASTER_PRODUK = {}

    gid = SHEET_GID.get('master_produk', 813944059)
    print(f"  🌐 Fetching Master Produk dari Google Sheets (gid={gid})...")
    csv_content = fetch_google_sheet(gid)

    if not csv_content or len(csv_content) < 100 or 'Loading' in csv_content[:50]:
        print(f"    ⚠ Gagal fetch Master Produk")
        return False

    print(f"    ✓ Berhasil fetch dari Google Sheets")

    # Parse CSV dengan csv module (handle quoted fields dengan benar)
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    if not rows:
        return False

    # Struktur Master Produk:
    # Baris 0: Data aneh
    # Baris 1: Index angka (0,1,2,3...)
    # Baris 2: Header nama (No, Code, Article, Tipe, Series, Gender, Tier, ...)
    # Baris 3+: Data
    # Kolom B (index 1): Code (Kode Kecil)
    # Kolom C (index 2): Article (Nama Barang)
    # Kolom D (index 3): Tipe
    # Kolom E (index 4): Series
    # Kolom F (index 5): Gender
    # Kolom G (index 6): Tier

    count = 0
    for row in rows[3:]:  # Skip 3 header rows (baris 0, 1, 2)
        if len(row) < 7:
            continue

        kode_kecil = str(row[1]).strip().upper()  # Kolom B - Code
        if not kode_kecil or kode_kecil in ['CODE', 'NO', '1', '']:
            continue

        article = str(row[2]).strip() if len(row) > 2 else ''   # Kolom C - Article
        tipe = str(row[3]).strip() if len(row) > 3 else ''      # Kolom D - Tipe
        series = str(row[4]).strip() if len(row) > 4 else ''    # Kolom E - Series
        gender = str(row[5]).strip() if len(row) > 5 else ''    # Kolom F - Gender
        tier = str(row[6]).strip() if len(row) > 6 else ''      # Kolom G - Tier

        MASTER_PRODUK[kode_kecil] = {
            'article': article,
            'tipe': tipe,
            'series': series,
            'gender': gender,
            'tier': tier
        }
        # Juga simpan by article name untuk lookup
        if article and tier:
            MASTER_PRODUK_BY_ARTICLE[article.upper()] = tier
        count += 1

    print(f"    -> {count} produk loaded dari Master Produk (dengan Tier)")
    print(f"    -> {len(MASTER_PRODUK_BY_ARTICLE)} artikel dengan tier")
    return count > 0

def load_master_store():
    """Load Master Store/Warehouse dari Google Sheets - mapping store ke area"""
    global STORE_AREA_MAP
    STORE_AREA_MAP = {}

    gid = SHEET_GID.get('master_store', 1803569317)
    print(f"  🌐 Fetching Master Store/Warehouse dari Google Sheets (gid={gid})...")
    csv_content = fetch_google_sheet(gid)

    if not csv_content or len(csv_content) < 100:
        print(f"    ⚠ Gagal fetch Master Store/Warehouse")
        return False

    print(f"    ✓ Berhasil fetch dari Google Sheets")

    # Parse CSV
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    if not rows:
        return False

    # Struktur: Kolom A=Nama Retail, B=Area, C=Entitas, D=kosong, E=Nama Gudang, F=Area Gudang
    count = 0
    for row in rows[1:]:  # Skip header
        if len(row) >= 3:
            # Retail store (kolom A, B)
            store_name = str(row[0]).strip()
            area = str(row[1]).strip()
            if store_name and area:
                # Simpan beberapa variasi nama untuk matching
                STORE_AREA_MAP[store_name.lower()] = area
                # Simpan juga versi singkat (tanpa prefix ZUMA/Zuma)
                short_name = store_name.lower().replace('zuma ', '').replace('zuma', '').strip()
                if short_name:
                    STORE_AREA_MAP[short_name] = area
                count += 1

        if len(row) >= 6:
            # Warehouse (kolom E, F)
            wh_name = str(row[4]).strip()
            wh_area = str(row[5]).strip()
            if wh_name and wh_area:
                STORE_AREA_MAP[wh_name.lower()] = wh_area
                # Variasi nama warehouse
                short_wh = wh_name.lower().replace('warehouse ', '').replace('wh ', '').strip()
                if short_wh:
                    STORE_AREA_MAP[short_wh] = wh_area
                count += 1

    print(f"    -> {count} store/warehouse mappings loaded")
    return count > 0

def load_max_stock():
    """Load Max Stock dari Google Sheets - max stock per store/warehouse"""
    global MAX_STOCK_MAP
    MAX_STOCK_MAP = {}

    gid = SHEET_GID.get('max_stock', 382740121)
    print(f"  🌐 Fetching Max Stock dari Google Sheets (gid={gid})...")
    csv_content = fetch_google_sheet(gid)

    if not csv_content or len(csv_content) < 50:
        print(f"    ⚠ Gagal fetch Max Stock")
        return False

    print(f"    ✓ Berhasil fetch dari Google Sheets")

    # Parse CSV
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    if not rows:
        return False

    # Struktur: Kolom A=Store, B=MAX Stock
    count = 0
    for row in rows[1:]:  # Skip header
        if len(row) >= 2:
            store_name = str(row[0]).strip()
            max_stock_str = str(row[1]).strip()

            if store_name and max_stock_str:
                # Parse max stock (handle "tidak diketahui" atau nilai kosong)
                try:
                    max_stock = int(max_stock_str.replace(',', '').replace('.', ''))
                except:
                    max_stock = 0  # Jika tidak bisa di-parse, set 0

                # Simpan dengan lowercase untuk matching
                MAX_STOCK_MAP[store_name.lower()] = {
                    'name': store_name,
                    'max_stock': max_stock
                }
                # Simpan juga variasi nama tanpa prefix
                short_name = store_name.lower().replace('zuma ', '').replace('zuma', '').replace('warehouse ', '').strip()
                if short_name and short_name != store_name.lower():
                    MAX_STOCK_MAP[short_name] = {
                        'name': store_name,
                        'max_stock': max_stock
                    }
                count += 1

    print(f"    -> {count} max stock entries loaded")
    return count > 0

def load_master_assortment():
    """Load Master Assortment dari Google Sheets - assortment per kode kecil"""
    global MASTER_ASSORTMENT
    MASTER_ASSORTMENT = {}

    gid = SHEET_GID.get('master_assortment', 1063661008)
    print(f"  🌐 Fetching Master Assortment dari Google Sheets (gid={gid})...")
    csv_content = fetch_google_sheet(gid)

    if not csv_content or len(csv_content) < 50:
        print(f"    ⚠ Gagal fetch Master Assortment")
        return False

    print(f"    ✓ Berhasil fetch dari Google Sheets")

    # Parse CSV
    reader = csv.reader(io.StringIO(csv_content))
    rows = list(reader)

    if not rows:
        return False

    # Struktur: Kolom A=Kode Sku, B=Kode Kecil, C=Assorment, D=Count
    count = 0
    for row in rows[1:]:  # Skip header
        if len(row) >= 3:
            kode_kecil = str(row[1]).strip().upper()
            assortment = str(row[2]).strip()

            if kode_kecil and assortment:
                # Simpan assortment per kode kecil (hanya perlu 1 karena sama untuk semua size)
                if kode_kecil not in MASTER_ASSORTMENT:
                    MASTER_ASSORTMENT[kode_kecil] = assortment
                    count += 1

    print(f"    -> {count} assortment entries loaded")
    return count > 0

def get_product_info_from_master(sku):
    """Get product info dari Master Data (by SKU) dan Tier dari Master Produk (by Kode Kecil)"""
    if not sku:
        return None

    sku_upper = sku.upper()
    result = None

    # Coba dari Master Data dulu (by full SKU)
    if sku_upper in MASTER_DATA:
        result = MASTER_DATA[sku_upper].copy()

    if not result:
        return None

    # Prioritas tier: Master Produk by kode_kecil > Master Data
    kode_kecil = result.get('kode_kecil', '') or extract_kode_kecil(sku)

    # 1. Coba lookup dari MASTER_PRODUK by kode_kecil (paling akurat)
    if kode_kecil and kode_kecil.upper() in MASTER_PRODUK:
        produk_info = MASTER_PRODUK[kode_kecil.upper()]
        if produk_info.get('tier'):
            result['tier'] = produk_info.get('tier', '')
    # 2. Kalau tidak ada di MASTER_PRODUK, gunakan tier dari Master Data (sudah ada di result)
    # Tidak perlu action karena result['tier'] sudah ada dari Master Data

    return result

# Fallback Area Mapping (digunakan jika tidak ada di Master Store/Warehouse)
AREA_MAPPING_FALLBACK = {
    'Warehouse': 'Warehouse', 'Pusat': 'Jawa Timur', 'WH': 'Warehouse',
    'Gudang': 'Warehouse', 'Box': 'Bali', 'Protol': 'Bali', 'Reject': 'Bali'
}

def get_area(location_name):
    """Tentukan area dari nama lokasi - prioritas dari Master Store/Warehouse"""
    if not location_name:
        return 'Warehouse'

    loc_lower = location_name.lower().strip()

    # 1. Cek exact match di STORE_AREA_MAP (dari Master Store/Warehouse)
    if loc_lower in STORE_AREA_MAP:
        return STORE_AREA_MAP[loc_lower]

    # 2. Cek partial match di STORE_AREA_MAP
    for store_key, area in STORE_AREA_MAP.items():
        if store_key in loc_lower or loc_lower in store_key:
            return area

    # 3. Cek keyword matching untuk warehouse
    loc_upper = location_name.upper()
    for keyword, area in AREA_MAPPING_FALLBACK.items():
        if keyword.upper() in loc_upper:
            return area

    # 4. Default patterns
    if 'WAREHOUSE' in loc_upper or 'WH ' in loc_upper or 'GUDANG' in loc_upper:
        return 'Warehouse'

    # 5. Default ke Bali
    return 'Bali'

def parse_number(val):
    """Parse number dari format Indonesia (comma decimal, dot thousand)"""
    if not val:
        return 0
    val_str = str(val).replace('"', '').strip()
    val_str = val_str.replace('.', '')
    val_str = val_str.replace(',', '.')
    try:
        return int(round(float(val_str)))
    except:
        return 0

def extract_product_info(name, sku):
    """Extract kategori, gender, series dari Master Data atau SKU"""
    info = {
        'size': '',
        'category': '',
        'gender': '',
        'series': '',
        'tipe': '',
        'color': '',
        'kode_kecil': '',
        'nama_master': '',
        'tier': ''
    }

    upper_name = (name or '').upper()
    upper_sku = (sku or '').upper()

    # Coba ambil dari Master Data (by full SKU)
    master_info = get_product_info_from_master(sku)
    if master_info:
        info['kode_kecil'] = master_info.get('kode_kecil', '')
        info['nama_master'] = master_info.get('nama', '')
        info['series'] = master_info.get('series', '')
        info['gender'] = master_info.get('gender', '')
        info['tier'] = master_info.get('tier', '')
        # Size dari Master Data (kolom F) - prioritas utama
        if master_info.get('size'):
            info['size'] = master_info.get('size', '')
    else:
        # Fallback: extract kode kecil dari SKU
        info['kode_kecil'] = extract_kode_kecil(sku)

    # Get tipe from MASTER_PRODUK by kode_kecil
    kode_kecil_upper = (info['kode_kecil'] or '').upper()
    if kode_kecil_upper and kode_kecil_upper in MASTER_PRODUK:
        produk_info = MASTER_PRODUK[kode_kecil_upper]
        info['tipe'] = produk_info.get('tipe', '')

    # Fallback size dari SKU jika Master Data tidak punya
    if not info['size']:
        size_match = re.search(r'Z(\d{2,3})$', upper_sku)
        if size_match:
            info['size'] = size_match.group(1)

    # Category dari Gender di Master Data
    gender_upper = (info['gender'] or '').upper()
    if gender_upper == 'BABY':
        info['category'] = 'BABY'
    elif gender_upper == 'BOYS':
        info['category'] = 'BOYS'
    elif gender_upper == 'GIRLS':
        info['category'] = 'GIRLS'
    elif gender_upper == 'JUNIOR':
        info['category'] = 'JUNIOR'
    elif gender_upper == 'LADIES':
        info['category'] = 'LADIES'
    elif gender_upper == 'MEN':
        info['category'] = 'MEN'
    else:
        # Fallback dari SKU prefix
        if upper_sku.startswith('Z') or upper_sku.startswith('BB'):
            info['category'] = 'BABY'
        elif upper_sku.startswith('B2') or upper_sku.startswith('B1'):
            info['category'] = 'BOYS'
        elif upper_sku.startswith('G2') or upper_sku.startswith('G1'):
            info['category'] = 'GIRLS'
        elif upper_sku.startswith('J'):
            info['category'] = 'JUNIOR'
        elif upper_sku.startswith('L'):
            info['category'] = 'LADIES'
        elif upper_sku.startswith('M'):
            info['category'] = 'MEN'
        else:
            info['category'] = 'BABY'

    # Series - gunakan dari master, jika kosong tampilkan "-"
    if not info['series'] or info['series'].strip() == '':
        info['series'] = '-'

    # Color - extract from name after last comma
    if ',' in (name or ''):
        parts = name.split(',')
        if len(parts) >= 2:
            info['color'] = parts[-1].strip()

    return info

def read_csv_detailed(filepath, entity, data_type):
    """Baca CSV dengan detail per store/warehouse"""
    items = []
    stores_list = []

    if not os.path.exists(filepath):
        print(f"  File tidak ditemukan: {filepath}")
        return items, stores_list

    print(f"  Membaca: {filepath}")

    try:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        rows = []

        for encoding in encodings:
            try:
                with open(filepath, 'r', encoding=encoding, errors='replace') as f:
                    sample = f.read(2000)
                    f.seek(0)
                    delimiter = ';' if sample.count(';') > sample.count(',') else ','
                    reader = csv.reader(f, delimiter=delimiter)
                    rows = list(reader)
                    break
            except:
                continue

        if not rows:
            return items, stores_list

        # Find header row
        header_row = 0
        headers = []
        for i, row in enumerate(rows[:15]):
            row_str = ''.join(str(x).lower() for x in row)
            if 'kode barang' in row_str or ('nama barang' in row_str and len(row) > 5):
                headers = row
                header_row = i
                break

        if not headers:
            return items, stores_list

        # Find column indices
        sku_col = -1
        name_col = -1
        total_col = -1
        store_cols = {}  # {col_index: store_name}

        for idx, h in enumerate(headers):
            h_str = str(h).strip()
            h_lower = h_str.lower()

            if 'kode barang' in h_lower or h_lower == 'kode':
                sku_col = idx
            elif 'nama barang' in h_lower:
                name_col = idx
            elif 'total' in h_lower:
                total_col = idx
            elif h_str and len(h_str) > 2:
                # Check if it's a store/warehouse column
                if any(x in h_str.upper() for x in ['ZUMA', 'WAREHOUSE', 'WH']):
                    store_cols[idx] = h_str
                elif any(x in h_str for x in ['Mall', 'Store', 'Toko']):
                    store_cols[idx] = h_str

        # Build stores list with areas
        for col_idx, store_name in store_cols.items():
            area = get_area(store_name)
            stores_list.append({
                'name': store_name,
                'area': area,
                'col_index': col_idx
            })

        # Process data rows
        seen_skus = set()

        for i, row in enumerate(rows[header_row + 1:], start=header_row + 1):
            if len(row) < 3:
                continue

            # Find SKU
            sku = ''
            for j, cell in enumerate(row):
                cell_str = str(cell).strip()
                if cell_str and re.match(r'^[A-Z0-9\-]{5,}$', cell_str, re.IGNORECASE):
                    if ' ' not in cell_str and 'total' not in cell_str.lower():
                        sku = cell_str
                        break

            if not sku or 'total' in sku.lower():
                continue

            # Get unique key
            row_key = sku
            if row_key in seen_skus:
                continue
            seen_skus.add(row_key)

            # Get name
            name = ''
            if name_col >= 0 and name_col < len(row):
                name = str(row[name_col]).strip()
            if not name:
                for cell in row:
                    cell_str = str(cell).strip()
                    if cell_str and len(cell_str) > 10 and ',' in cell_str:
                        name = cell_str
                        break

            # Get total stock
            total = 0
            if total_col >= 0 and total_col < len(row):
                total = parse_number(row[total_col])
            else:
                for j in range(len(row) - 1, -1, -1):
                    cell_str = str(row[j]).strip()
                    if cell_str and cell_str not in ['', '-']:
                        val = parse_number(row[j])
                        if val != 0 or '0' in cell_str:
                            total = val
                            break

            # Get per-store stock (termasuk stok 0 agar bisa filter Out of Stock per store)
            store_stock = {}
            for col_idx, store_name in store_cols.items():
                if col_idx < len(row):
                    stock_val = parse_number(row[col_idx])
                    # Apply correction for doubled stores
                    correction = DOUBLED_STORES.get(store_name.lower(), 1.0)
                    if correction != 1.0:
                        stock_val = int(stock_val * correction)
                    store_stock[store_name] = stock_val  # Include semua, termasuk 0

            # Extract product info
            info = extract_product_info(name, sku)

            # Gunakan nama dari master jika ada, jika tidak gunakan dari CSV
            display_name = info['nama_master'] if info['nama_master'] else (name or sku)

            # Filter: hanya produk sandal (exclude hanger, aksesoris, dll)
            if not is_sandal_product(display_name, sku):
                continue

            items.append({
                'sku': sku,
                'kode_kecil': info['kode_kecil'],
                'name': display_name,
                'size': info['size'],
                'category': info['category'],
                'gender': info['gender'],
                'series': info['series'],
                'tipe': info['tipe'],
                'tier': info['tier'],
                'color': info['color'],
                'total': total,
                'store_stock': store_stock,
                'entity': entity,
                'type': data_type
            })

        print(f"    -> {len(items)} items, {len(stores_list)} locations")

    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        import traceback
        traceback.print_exc()

    return items, stores_list

def generate_html(all_data, all_stores):
    """Generate HTML dashboard dengan data embedded"""

    data_json = json.dumps(all_data, ensure_ascii=False)
    stores_json = json.dumps(all_stores, ensure_ascii=False)
    store_area_json = json.dumps(STORE_AREA_MAP, ensure_ascii=False)
    max_stock_json = json.dumps(MAX_STOCK_MAP, ensure_ascii=False)
    assortment_json = json.dumps(MASTER_ASSORTMENT, ensure_ascii=False)

    html = '''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoring Stock Retail & Warehouse - Zuma Indonesia</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1; --primary-light: #818cf8; --secondary: #ec4899;
            --success: #10b981; --warning: #f59e0b; --danger: #ef4444; --info: #06b6d4;
            --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --card-bg: rgba(255, 255, 255, 0.98); --shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Poppins', sans-serif;
            background: linear-gradient(135deg, #f0f4ff 0%, #fce7f3 50%, #dbeafe 100%);
            min-height: 100vh; color: #1f2937;
        }
        .header {
            background: linear-gradient(135deg, #1f2937 0%, #111827 50%, #0f172a 100%); padding: 20px 40px; color: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3); position: sticky; top: 0; z-index: 100;
            display: flex; justify-content: space-between; align-items: center;
        }
        .header h1 { font-size: 1.6rem; font-weight: 700; }
        .header p { opacity: 0.9; font-size: 0.85rem; }
        .header .date { font-size: 0.8rem; opacity: 0.85; text-align: right; }
        .container { max-width: 1700px; margin: 0 auto; padding: 25px; }

        /* Entity Pills */
        .entity-section {
            display: flex; gap: 15px; align-items: center;
            flex-wrap: wrap; margin-bottom: 20px;
        }
        .entity-pills { display: flex; gap: 8px; flex-wrap: wrap; }
        .entity-pill {
            padding: 10px 20px; border-radius: 25px; font-size: 0.85rem;
            font-weight: 600; cursor: pointer; transition: all 0.3s ease;
            border: 2px solid transparent; display: flex; align-items: center; gap: 8px;
        }
        .entity-pill.ddd { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: 2px solid #b91c1c; }
        .entity-pill.ljbb { background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: 2px solid #1d4ed8; }
        .entity-pill.mbb { background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; border: 2px solid #6d28d9; }
        .entity-pill.ubb { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: 2px solid #b45309; }
        .entity-pill.active { transform: scale(1.08); box-shadow: 0 6px 20px rgba(0,0,0,0.4); }
        .entity-pill .count {
            background: rgba(255,255,255,0.5); padding: 2px 8px;
            border-radius: 10px; font-size: 0.75rem;
        }

        /* Tabs */
        .tabs {
            display: flex; gap: 5px; margin-bottom: 25px; background: var(--card-bg);
            padding: 6px; border-radius: 14px; box-shadow: var(--shadow); width: fit-content;
        }
        .tab {
            padding: 10px 22px; border: none; background: transparent; border-radius: 10px;
            font-size: 0.9rem; font-weight: 500; cursor: pointer; transition: all 0.3s ease;
            font-family: 'Poppins', sans-serif; color: #6b7280;
        }
        .tab:hover { background: #f3f4f6; }
        .tab.active { background: var(--bg-gradient); color: white; }

        /* Stats Cards */
        .stats-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px; margin-bottom: 25px;
        }
        .stat-card {
            background: var(--card-bg); border-radius: 16px; padding: 20px;
            box-shadow: var(--shadow); position: relative; overflow: hidden;
        }
        .stat-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0;
            height: 4px; border-radius: 16px 16px 0 0;
        }
        .stat-card.primary::before { background: linear-gradient(90deg, #6366f1, #818cf8); }
        .stat-card.success::before { background: linear-gradient(90deg, #10b981, #34d399); }
        .stat-card.warning::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .stat-card.info::before { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
        .stat-card.danger::before { background: linear-gradient(90deg, #ef4444, #f87171); }
        .stat-card.secondary::before { background: linear-gradient(90deg, #ec4899, #f472b6); }
        .stat-card h3 {
            font-size: 0.7rem; color: #6b7280; font-weight: 600; margin-bottom: 8px;
            text-transform: uppercase; letter-spacing: 0.5px;
        }
        .stat-card .value { font-size: 1.6rem; font-weight: 700; color: #1f2937; }
        .stat-card .sub-value { font-size: 0.75rem; color: #9ca3af; margin-top: 3px; }

        /* Charts */
        .charts-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px; margin-bottom: 25px;
        }
        .chart-card {
            background: var(--card-bg); border-radius: 16px; padding: 20px; box-shadow: var(--shadow);
        }
        .chart-card h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 15px; color: #374151; }
        .chart-container { position: relative; height: 250px; }

        /* Filter Section */
        .filter-section {
            background: var(--card-bg); border-radius: 16px; padding: 20px 25px;
            margin-bottom: 25px; box-shadow: var(--shadow);
            display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px;
            align-items: end;
        }
        .filter-group label {
            display: block; font-weight: 600; margin-bottom: 6px; color: #374151;
            font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;
        }
        .filter-group select, .filter-group input {
            width: 100%; padding: 10px 14px; border: 2px solid #e5e7eb;
            border-radius: 10px; font-size: 0.85rem; font-family: 'Poppins', sans-serif;
            background: white; transition: all 0.3s ease;
        }
        .filter-group select:focus, .filter-group input:focus {
            outline: none; border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }
        .btn {
            padding: 10px 20px; border: none; border-radius: 10px; font-size: 0.85rem;
            font-weight: 600; cursor: pointer; transition: all 0.3s ease;
            font-family: 'Poppins', sans-serif;
        }
        .btn-primary { background: var(--bg-gradient); color: white; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(99, 102, 241, 0.4); }
        .btn-secondary { background: #f3f4f6; color: #374151; }
        .btn-secondary:hover { background: #e5e7eb; }

        /* Store Summary */
        .store-summary {
            background: var(--card-bg); border-radius: 16px; padding: 20px;
            margin-bottom: 25px; box-shadow: var(--shadow);
        }
        .store-summary h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 15px; }
        .store-grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;
        }
        .store-item {
            background: #f8fafc; border-radius: 10px; padding: 12px 15px;
            display: flex; justify-content: space-between; align-items: center;
            cursor: pointer; transition: all 0.2s ease; border: 2px solid transparent;
        }
        .store-item:hover { background: #f1f5f9; border-color: var(--primary-light); }
        .store-item.active { background: #eef2ff; border-color: var(--primary); }
        .store-item .store-name { font-size: 0.8rem; font-weight: 500; color: #374151; }
        .store-item .store-area { font-size: 0.7rem; color: #9ca3af; }
        .store-item .store-stock { font-size: 0.9rem; font-weight: 700; color: var(--primary); }

        /* Table */
        .table-section {
            background: var(--card-bg); border-radius: 16px; box-shadow: var(--shadow); overflow: hidden;
        }
        .table-header {
            padding: 18px 22px; border-bottom: 1px solid #e5e7eb;
            display: flex; justify-content: space-between; align-items: center;
            flex-wrap: wrap; gap: 12px;
        }
        .table-header h3 { font-size: 0.95rem; font-weight: 600; color: #374151; }
        .table-actions { display: flex; gap: 10px; align-items: center; }
        .search-box { position: relative; }
        .search-box input {
            padding: 9px 14px 9px 38px; border: 2px solid #e5e7eb; border-radius: 10px;
            font-size: 0.85rem; width: 260px; font-family: 'Poppins', sans-serif;
        }
        .search-box::before {
            content: '🔍'; position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 0.85rem;
        }
        .table-wrapper { overflow-x: auto; max-height: 500px; overflow-y: auto; }
        table { width: 100%; border-collapse: collapse; }
        th {
            color: white; padding: 12px 14px; text-align: left; font-size: 0.75rem;
            font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
            position: sticky; top: 0; z-index: 10; cursor: pointer;
        }
        /* Retail table header - Blue */
        .retail-section th {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        }
        .retail-section th:hover { background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%); }
        /* Warehouse table header - Teal/Green */
        .warehouse-section th {
            background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%);
        }
        .warehouse-section th:hover { background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%); }
        td { padding: 11px 14px; border-bottom: 1px solid #f3f4f6; font-size: 0.82rem; }
        tr:hover { background: #f8fafc; }
        tr:nth-child(even) { background: #fafbfc; }
        tr:nth-child(even):hover { background: #f0f4f8; }

        .stock-badge {
            display: inline-block; padding: 3px 10px; border-radius: 15px;
            font-size: 0.7rem; font-weight: 600;
        }
        .stock-high { background: #d1fae5; color: #065f46; }
        .stock-medium { background: #fef3c7; color: #92400e; }
        .stock-low { background: #fee2e2; color: #991b1b; }
        .stock-zero { background: #f3f4f6; color: #6b7280; }
        .stock-negative { background: #fecaca; color: #dc2626; }

        .pagination {
            display: flex; justify-content: space-between; align-items: center;
            padding: 12px 22px; border-top: 1px solid #e5e7eb;
        }
        .page-info { font-size: 0.8rem; color: #6b7280; }
        .page-buttons { display: flex; gap: 4px; }
        .page-btn {
            padding: 6px 12px; border: 1px solid #e5e7eb; background: white;
            border-radius: 6px; cursor: pointer; font-size: 0.8rem; transition: all 0.2s ease;
        }
        .page-btn:hover { background: #f3f4f6; }
        .page-btn.active { background: var(--primary); color: white; border-color: var(--primary); }
        .page-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* Area Tags */
        .area-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 15px; }
        .area-tag {
            padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 500;
            cursor: pointer; transition: all 0.2s ease; border: 2px solid transparent;
        }
        .area-tag.bali { background: #dcfce7; color: #166534; }
        .area-tag.jakarta { background: #dbeafe; color: #1e40af; }
        .area-tag.jawa-timur { background: #fef3c7; color: #b45309; }
        .area-tag.jawa-barat { background: #fae8ff; color: #86198f; }
        .area-tag.lombok { background: #fce7f3; color: #be185d; }
        .area-tag.sulawesi { background: #e0e7ff; color: #4338ca; }
        .area-tag.sumatera { background: #ffedd5; color: #c2410c; }
        .area-tag.warehouse { background: #f3f4f6; color: #374151; }
        .area-tag.active { border-color: #1f2937; transform: scale(1.05); }

        @media (max-width: 768px) {
            .container { padding: 15px; }
            .filter-section { grid-template-columns: 1fr 1fr; }
            .charts-grid { grid-template-columns: 1fr; }
            .search-box input { width: 180px; }
        }

        /* Tooltip */
        .tooltip {
            position: relative; cursor: help;
        }
        .tooltip:hover::after {
            content: attr(data-tooltip); position: absolute; bottom: 100%;
            left: 50%; transform: translateX(-50%); padding: 6px 10px;
            background: #1f2937; color: white; font-size: 0.75rem;
            border-radius: 6px; white-space: nowrap; z-index: 100;
        }

        /* Clickable stat card */
        .stat-card.clickable:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
        }

        /* Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); z-index: 1000;
            display: none; justify-content: center; align-items: center;
            backdrop-filter: blur(4px);
        }
        .modal-overlay.active { display: flex; }
        .modal-content {
            background: white; border-radius: 20px; width: 90%; max-width: 900px;
            max-height: 85vh; overflow: hidden; box-shadow: 0 25px 60px rgba(0,0,0,0.3);
            animation: modalSlide 0.3s ease;
        }
        @keyframes modalSlide {
            from { transform: translateY(-30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        .modal-header {
            background: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
            color: white; padding: 20px 25px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .modal-header h2 { font-size: 1.2rem; font-weight: 600; display: flex; align-items: center; gap: 10px; }
        .modal-close {
            background: rgba(255,255,255,0.2); border: none; color: white;
            width: 36px; height: 36px; border-radius: 50%; font-size: 1.2rem;
            cursor: pointer; transition: all 0.2s ease;
        }
        .modal-close:hover { background: rgba(255,255,255,0.3); transform: rotate(90deg); }
        .modal-body { padding: 20px 25px; max-height: 60vh; overflow-y: auto; }
        .modal-summary {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px; margin-bottom: 20px;
        }
        .modal-stat {
            background: #fef2f2; border-radius: 12px; padding: 15px; text-align: center;
        }
        .modal-stat .label { font-size: 0.75rem; color: #991b1b; font-weight: 600; text-transform: uppercase; }
        .modal-stat .value { font-size: 1.5rem; font-weight: 700; color: #dc2626; margin-top: 5px; }
        .negative-list { margin-top: 15px; }
        .negative-item {
            background: #fff; border: 1px solid #fecaca; border-radius: 12px;
            margin-bottom: 10px; overflow: hidden; transition: all 0.2s ease;
        }
        .negative-item:hover { box-shadow: 0 4px 15px rgba(239, 68, 68, 0.15); }
        .negative-item-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 16px 20px; cursor: pointer; background: #fef2f2;
            transition: background 0.2s ease;
        }
        .negative-item-header:hover { background: #fee2e2; }
        .negative-store {
            font-weight: 600; color: #1f2937; font-size: 0.95rem;
            display: flex; align-items: center; gap: 10px;
        }
        .negative-store-icon { font-size: 1.2rem; }
        .negative-store-area {
            font-size: 0.7rem; background: #fee2e2; color: #991b1b;
            padding: 4px 10px; border-radius: 12px; font-weight: 500;
        }
        .negative-stats {
            display: flex; align-items: center; gap: 12px;
        }
        .negative-count {
            background: #dc2626; color: white; padding: 6px 14px;
            border-radius: 20px; font-size: 0.8rem; font-weight: 600;
        }
        .negative-pairs {
            background: #fecaca; color: #991b1b; padding: 6px 14px;
            border-radius: 20px; font-size: 0.8rem; font-weight: 600;
        }
        .expand-icon {
            font-size: 1.2rem; color: #991b1b; transition: transform 0.3s ease;
            margin-left: 10px;
        }
        .negative-item.expanded .expand-icon { transform: rotate(180deg); }
        .negative-articles {
            display: none; padding: 0 20px 20px; background: #fff;
        }
        .negative-item.expanded .negative-articles { display: block; }
        .articles-table {
            width: 100%; border-collapse: collapse; margin-top: 10px;
        }
        .articles-table th {
            background: #fef2f2; color: #991b1b; padding: 10px 12px;
            text-align: left; font-size: 0.75rem; font-weight: 600;
            text-transform: uppercase; border-bottom: 2px solid #fecaca;
        }
        .articles-table td {
            padding: 10px 12px; border-bottom: 1px solid #fee2e2; font-size: 0.85rem;
        }
        .articles-table tr:hover { background: #fef2f2; }
        .articles-table .sku { font-weight: 600; color: #1f2937; }
        .articles-table .name { color: #6b7280; }
        .articles-table .stock { color: #dc2626; font-weight: 700; text-align: right; }

        /* Toggle View Dashboard */
        .view-toggle {
            display: flex; gap: 8px; background: var(--card-bg);
            padding: 6px; border-radius: 14px; box-shadow: var(--shadow);
            width: fit-content; margin-bottom: 20px;
        }
        .view-btn {
            padding: 12px 24px; border: none; background: transparent; border-radius: 10px;
            font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: all 0.3s ease;
            font-family: 'Poppins', sans-serif; color: #6b7280;
            display: flex; align-items: center; gap: 8px;
        }
        .view-btn:hover { background: #f3f4f6; }
        .view-btn.active { background: linear-gradient(135deg, #10b981 0%, #34d399 100%); color: white; }
        .view-container { display: none; }
        .view-container.active { display: block; }

        /* Max Stock Analysis Styles */
        .analysis-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px; margin-bottom: 25px;
        }
        .analysis-card {
            background: var(--card-bg); border-radius: 16px; padding: 20px;
            box-shadow: var(--shadow); overflow: hidden;
        }
        .analysis-card h3 {
            font-size: 0.95rem; font-weight: 600; margin-bottom: 15px; color: #374151;
            display: flex; align-items: center; gap: 8px;
        }
        .store-analysis-item {
            display: flex; align-items: center; gap: 15px; padding: 12px;
            background: #f8fafc; border-radius: 10px; margin-bottom: 10px;
            transition: all 0.2s ease; cursor: pointer;
        }
        .store-analysis-item:hover { background: #f1f5f9; transform: translateX(5px); }
        .store-info { flex: 1; }
        .store-info .name { font-weight: 600; color: #1f2937; font-size: 0.9rem; }
        .store-info .area { font-size: 0.75rem; color: #9ca3af; }
        .stock-comparison { text-align: right; }
        .stock-comparison .actual { font-size: 0.85rem; color: #6b7280; }
        .stock-comparison .max { font-size: 0.75rem; color: #9ca3af; }
        .fill-indicator {
            width: 80px; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;
        }
        .fill-bar {
            height: 100%; border-radius: 4px; transition: width 0.5s ease;
        }
        .fill-bar.low { background: linear-gradient(90deg, #3b82f6, #60a5fa); }
        .fill-bar.medium { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
        .fill-bar.high { background: linear-gradient(90deg, #10b981, #34d399); }
        .fill-bar.over { background: linear-gradient(90deg, #dc2626, #b91c1c); }
        .fill-percent {
            font-size: 0.8rem; font-weight: 700; min-width: 50px; text-align: right;
        }
        .fill-percent.low { color: #3b82f6; }
        .fill-percent.medium { color: #f59e0b; }
        .fill-percent.high { color: #10b981; }
        .fill-percent.over { color: #dc2626; }

        /* Tier breakdown mini di store list */
        .tier-breakdown-mini {
            display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px;
        }
        .tier-tag {
            font-size: 0.65rem; background: #eef2ff; color: #6366f1;
            padding: 2px 6px; border-radius: 4px; font-weight: 600;
        }

        /* Tier Distribution */
        .tier-distribution {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 10px; margin-top: 15px;
        }
        .tier-item {
            text-align: center; padding: 12px 8px; background: #f8fafc;
            border-radius: 10px; transition: all 0.2s ease;
        }
        .tier-item:hover { background: #eef2ff; transform: scale(1.05); }
        .tier-item.clickable { border: 2px solid #e0e7ff; }
        .tier-item.clickable:hover { background: #eef2ff; border-color: #6366f1; box-shadow: 0 4px 12px rgba(99,102,241,0.2); }
        .tier-item .tier-label { font-size: 0.7rem; color: #9ca3af; font-weight: 600; }
        .tier-item .tier-value { font-size: 1.1rem; font-weight: 700; color: #1f2937; margin-top: 4px; }
        .tier-item .tier-percent { font-size: 0.75rem; color: #6366f1; }

        /* Summary Cards for Max Stock */
        .max-stock-summary {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px; margin-bottom: 25px;
        }
        .summary-card {
            background: var(--card-bg); border-radius: 16px; padding: 20px;
            box-shadow: var(--shadow); text-align: center;
        }
        .summary-card.green { border-top: 4px solid #10b981; }
        .summary-card.yellow { border-top: 4px solid #f59e0b; }
        .summary-card.red { border-top: 4px solid #ef4444; }
        .summary-card.blue { border-top: 4px solid #6366f1; }
        .summary-card .label { font-size: 0.75rem; color: #6b7280; font-weight: 600; text-transform: uppercase; }
        .summary-card .value { font-size: 1.8rem; font-weight: 700; color: #1f2937; margin-top: 8px; }
        .summary-card .sub { font-size: 0.8rem; color: #9ca3af; margin-top: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <div style="display:flex;align-items:center;gap:20px;">
            <img src="''' + LOGO_ZUMA + '''" alt="Zuma Logo" style="height:80px;width:auto;filter:brightness(0) invert(1);">
            <div>
                <h1 style="font-size:1.4rem;margin:0;">Monitoring Stock Retail & Warehouse</h1>
                <p style="margin:5px 0 0 0;font-size:1rem;">Zuma Indonesia</p>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:15px;">
            <div class="entity-logos" style="display:flex;gap:6px;align-items:center;">
                <div style="width:70px;height:35px;display:flex;align-items:center;justify-content:center;background:white;border-radius:5px;padding:3px;"><img src="''' + LOGO_DDD + '''" alt="DDD" style="max-height:30px;max-width:65px;object-fit:contain;"></div>
                <div style="width:70px;height:35px;display:flex;align-items:center;justify-content:center;background:white;border-radius:5px;padding:3px;"><img src="''' + LOGO_LJBB + '''" alt="LJBB" style="max-height:30px;max-width:65px;object-fit:contain;"></div>
                <div style="width:70px;height:35px;display:flex;align-items:center;justify-content:center;background:white;border-radius:5px;padding:3px;"><img src="''' + LOGO_MBB + '''" alt="MBB" style="max-height:30px;max-width:65px;object-fit:contain;"></div>
                <div style="width:70px;height:35px;display:flex;align-items:center;justify-content:center;background:white;border-radius:5px;padding:3px;"><img src="''' + LOGO_UBB + '''" alt="UBB" style="max-height:30px;max-width:65px;object-fit:contain;"></div>
            </div>
            <div class="date">
                <div>Data per:</div>
                <div><strong>''' + __import__('datetime').datetime.now().strftime('%d %B %Y, %H:%M WIB') + '''</strong></div>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Toggle View Dashboard -->
        <div class="view-toggle">
            <button class="view-btn active" data-view="inventory" onclick="switchView('inventory')">
                📊 Stock Inventory
            </button>
            <button class="view-btn" data-view="maxstock" onclick="switchView('maxstock')">
                📈 Max Stock Analysis
            </button>
            <button class="view-btn" data-view="stockcontrol" onclick="switchView('stockcontrol')">
                📋 Stock Control
            </button>
        </div>

        <!-- ==================== INVENTORY VIEW ==================== -->
        <div class="view-container active" id="inventoryView">

        <!-- Entity Section (only for Stock Inventory) -->
        <div class="entity-section">
            <span style="font-weight:600; color:#374151; font-size:0.85rem;">ENTITAS:</span>
            <div class="entity-pills">
                <div class="entity-pill ddd active" data-entity="DDD" onclick="selectEntity('DDD')">
                    <img src="''' + LOGO_DDD + '''" alt="DDD" style="height:22px;object-fit:contain;">
                </div>
                <div class="entity-pill ljbb" data-entity="LJBB" onclick="selectEntity('LJBB')">
                    <img src="''' + LOGO_LJBB + '''" alt="LJBB" style="height:22px;object-fit:contain;">
                </div>
                <div class="entity-pill mbb" data-entity="MBB" onclick="selectEntity('MBB')">
                    <img src="''' + LOGO_MBB + '''" alt="MBB" style="height:22px;object-fit:contain;">
                </div>
                <div class="entity-pill ubb" data-entity="UBB" onclick="selectEntity('UBB')">
                    <img src="''' + LOGO_UBB + '''" alt="UBB" style="height:22px;object-fit:contain;">
                </div>
            </div>
        </div>

        <!-- ==================== RETAIL SECTION ==================== -->
        <div class="section-wrapper retail-section" id="retailSectionWrapper" style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border: 2px solid #3b82f6; border-radius: 16px; padding: 20px; margin-bottom: 30px;">
            <!-- Retail Section Header -->
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #3b82f6;">
                <div style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; padding: 10px 20px; border-radius: 10px; font-weight: 700; font-size: 1.1rem; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);">
                    🏪 RETAIL STORE
                </div>
                <span style="color: #1e40af; font-size: 0.9rem;">Data stock di toko retail</span>
            </div>

            <!-- Retail Stats Cards -->
            <div class="stats-grid" id="rtStatsGrid" style="margin-bottom: 15px;">
                <div class="stat-card" style="border-left: 4px solid #3b82f6; background: white;">
                    <h3 style="color: #1e40af;">Total SKU</h3>
                    <div class="value" id="rtTotalSku" style="color: #1d4ed8;">0</div>
                    <div class="sub-value">Artikel terdaftar</div>
                </div>
                <div class="stat-card" style="border-left: 4px solid #3b82f6; background: white;">
                    <h3 style="color: #1e40af;">Total Stock</h3>
                    <div class="value" id="rtTotalStock" style="color: #2563eb;">0</div>
                    <div class="sub-value">Total unit positif</div>
                </div>
                <div class="stat-card clickable" onclick="showNegativeDetails('retail')" style="cursor:pointer; border-left: 4px solid #ef4444; background: white;">
                    <h3 style="color: #b91c1c;">Minus on Hand</h3>
                    <div class="value" id="rtNegativeStock" style="color: #dc2626;">0</div>
                    <div class="sub-value" id="rtNegativeSubValue">0 artikel | 0 pairs</div>
                </div>
            </div>

            <!-- Retail Stock Data Table -->
            <div class="table-section" id="retailTableSection" style="background: white; border-radius: 12px; padding: 15px;">
                <div class="table-header" style="flex-direction: column; align-items: stretch;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: #1e40af;">📋 Data Stock Retail</h3>
                        <button class="btn btn-secondary" onclick="exportData('retail')" style="background: #3b82f6; color: white; border: none;">📥 Export</button>
                    </div>
                <!-- Filter Row -->
                <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: end; padding: 15px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Area</label>
                        <select id="tableFilterArea" onchange="updateTableStoreDropdown(); applyRetailFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 120px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua Area</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Store</label>
                        <select id="tableFilterStore" onchange="applyRetailFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 180px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua Store</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Tier</label>
                        <select id="tableFilterTier" onchange="applyRetailFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 90px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua</option>
                            <option value="0">Tier 0</option>
                            <option value="1">Tier 1</option>
                            <option value="2">Tier 2</option>
                            <option value="3">Tier 3</option>
                            <option value="4">Tier 4</option>
                            <option value="5">Tier 5</option>
                            <option value="8">Tier 8</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Gender</label>
                        <select id="rtFilterGender" onchange="applyRetailFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 100px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua</option>
                            <option value="BABY">Baby</option>
                            <option value="BOYS">Boys</option>
                            <option value="GIRLS">Girls</option>
                            <option value="JUNIOR">Junior</option>
                            <option value="LADIES">Ladies</option>
                            <option value="MEN">Men</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Series</label>
                        <select id="rtFilterSeries" onchange="applyRetailFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 120px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Cari</label>
                        <input type="text" id="rtSearchInput" placeholder="Cari..." oninput="applyRetailFilters()" style="font-size: 0.85rem; padding: 8px 12px; width: 140px; border-radius: 6px; border: 1px solid #cbd5e1;">
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: transparent; margin-bottom: 4px; display: block;">.</label>
                        <button class="btn btn-secondary" onclick="resetRetailFilters()" style="font-size: 0.85rem; padding: 8px 14px; border-radius: 6px;">↺ Reset</button>
                    </div>
                </div>
            </div>
            <div class="table-wrapper" style="margin-top: 15px;">
                <table>
                    <thead>
                        <tr>
                            <th onclick="sortRetailData('kode_kecil')">Kode Kecil ↕</th>
                            <th onclick="sortRetailData('gender')">Gender ↕</th>
                            <th onclick="sortRetailData('series')">Series ↕</th>
                            <th onclick="sortRetailData('tipe')">Tipe ↕</th>
                            <th onclick="sortRetailData('name')">Nama Barang ↕</th>
                            <th onclick="sortRetailData('tier')">Tier ↕</th>
                            <th onclick="sortRetailData('total')">Total Qty ↕</th>
                        </tr>
                    </thead>
                    <tbody id="rtTableBody"></tbody>
                </table>
            </div>
            <div class="pagination">
                <div class="page-info" id="rtPageInfo">Showing 0 items</div>
                <div class="page-buttons" id="rtPageButtons"></div>
            </div>
            <!-- Retail Charts -->
            <div class="charts-grid" style="margin-top: 20px;">
                <div class="chart-card" style="background: white;">
                    <h3 style="color: #1e40af;">📊 Stock per Gender</h3>
                    <div class="chart-container"><canvas id="rtCategoryChart"></canvas></div>
                </div>
                <div class="chart-card" style="background: white;">
                    <h3 style="color: #1e40af;">📈 Stock per Area</h3>
                    <div class="chart-container"><canvas id="rtAreaChart"></canvas></div>
                </div>
                <div class="chart-card" style="background: white;">
                    <h3 style="color: #1e40af;">🎯 Stock per Series</h3>
                    <div class="chart-container"><canvas id="rtSeriesChart"></canvas></div>
                </div>
            </div>
            </div>
        </div>
        <!-- END RETAIL SECTION -->

        <!-- ==================== SEPARATOR ==================== -->
        <div style="display: flex; align-items: center; gap: 20px; margin: 40px 0;">
            <div style="flex: 1; height: 3px; background: linear-gradient(90deg, transparent, #94a3b8, transparent);"></div>
            <div style="background: #f1f5f9; padding: 8px 20px; border-radius: 20px; color: #64748b; font-weight: 600; font-size: 0.85rem;">⬇️ WAREHOUSE DATA ⬇️</div>
            <div style="flex: 1; height: 3px; background: linear-gradient(90deg, transparent, #94a3b8, transparent);"></div>
        </div>

        <!-- ==================== WAREHOUSE SECTION ==================== -->
        <div class="section-wrapper warehouse-section" id="warehouseSectionWrapper" style="background: linear-gradient(135deg, #f0fdfa 0%, #ccfbf1 100%); border: 2px solid #14b8a6; border-radius: 16px; padding: 20px; margin-bottom: 30px;">
            <!-- Warehouse Section Header -->
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #14b8a6;">
                <div style="background: linear-gradient(135deg, #14b8a6 0%, #0d9488 100%); color: white; padding: 10px 20px; border-radius: 10px; font-weight: 700; font-size: 1.1rem; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 6px rgba(20, 184, 166, 0.3);">
                    📦 WAREHOUSE
                </div>
                <span style="color: #0f766e; font-size: 0.9rem;">Data stock di gudang</span>
            </div>

            <!-- Warehouse Stats Cards -->
            <div class="stats-grid" id="whStatsGrid" style="margin-bottom: 15px;">
                <div class="stat-card" style="border-left: 4px solid #14b8a6; background: white;">
                    <h3 style="color: #0f766e;">Total SKU</h3>
                    <div class="value" id="whTotalSku" style="color: #0d9488;">0</div>
                    <div class="sub-value">Artikel terdaftar</div>
                </div>
                <div class="stat-card" style="border-left: 4px solid #14b8a6; background: white;">
                    <h3 style="color: #0f766e;">Total Stock</h3>
                    <div class="value" id="whTotalStock" style="color: #0d9488;">0</div>
                    <div class="sub-value">Total unit positif</div>
                </div>
                <div class="stat-card clickable" onclick="showNegativeDetails('warehouse')" style="cursor:pointer; border-left: 4px solid #ef4444; background: white;">
                    <h3 style="color: #b91c1c;">Minus on Hand</h3>
                    <div class="value" id="whNegativeStock" style="color: #dc2626;">0</div>
                    <div class="sub-value" id="whNegativeSubValue">0 artikel | 0 pairs</div>
                </div>
            </div>

            <div class="table-section" id="warehouseTableSection" style="background: white; border-radius: 12px; padding: 15px;">
                <div class="table-header" style="flex-direction: column; align-items: stretch;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: #0f766e;">📋 Data Stock Warehouse</h3>
                        <button class="btn btn-secondary" onclick="exportData('warehouse')" style="background: #14b8a6; color: white; border: none;">📥 Export</button>
                    </div>
                <!-- Filter Row -->
                <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: end; padding: 15px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Area</label>
                        <select id="whFilterArea" onchange="updateWhWarehouseDropdown(); applyWarehouseFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 120px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua Area</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Warehouse</label>
                        <select id="whFilterWarehouse" onchange="applyWarehouseFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 180px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua Warehouse</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Tier</label>
                        <select id="whFilterTier" onchange="applyWarehouseFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 90px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua</option>
                            <option value="0">Tier 0</option>
                            <option value="1">Tier 1</option>
                            <option value="2">Tier 2</option>
                            <option value="3">Tier 3</option>
                            <option value="4">Tier 4</option>
                            <option value="5">Tier 5</option>
                            <option value="8">Tier 8</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Gender</label>
                        <select id="whFilterGender" onchange="applyWarehouseFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 100px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua</option>
                            <option value="BABY">Baby</option>
                            <option value="BOYS">Boys</option>
                            <option value="GIRLS">Girls</option>
                            <option value="JUNIOR">Junior</option>
                            <option value="LADIES">Ladies</option>
                            <option value="MEN">Men</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Series</label>
                        <select id="whFilterSeries" onchange="applyWarehouseFilters()" style="font-size: 0.85rem; padding: 8px 12px; min-width: 120px; border-radius: 6px; border: 1px solid #cbd5e1;">
                            <option value="">Semua</option>
                        </select>
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: #64748b; margin-bottom: 4px; display: block;">Cari</label>
                        <input type="text" id="whSearchInput" placeholder="Cari..." oninput="applyWarehouseFilters()" style="font-size: 0.85rem; padding: 8px 12px; width: 140px; border-radius: 6px; border: 1px solid #cbd5e1;">
                    </div>
                    <div class="filter-group" style="flex: 0 0 auto;">
                        <label style="font-size: 0.75rem; color: transparent; margin-bottom: 4px; display: block;">.</label>
                        <button class="btn btn-secondary" onclick="resetWarehouseFilters()" style="font-size: 0.85rem; padding: 8px 14px; border-radius: 6px;">↺ Reset</button>
                    </div>
                </div>
            </div>
            <div class="table-wrapper" style="margin-top: 15px;">
                <table>
                    <thead>
                        <tr>
                            <th onclick="sortWarehouseData('kode_kecil')">Kode Kecil ↕</th>
                            <th onclick="sortWarehouseData('gender')">Gender ↕</th>
                            <th onclick="sortWarehouseData('series')">Series ↕</th>
                            <th onclick="sortWarehouseData('tipe')">Tipe ↕</th>
                            <th onclick="sortWarehouseData('name')">Nama Barang ↕</th>
                            <th onclick="sortWarehouseData('tier')">Tier ↕</th>
                            <th onclick="sortWarehouseData('total')">Total Qty ↕</th>
                        </tr>
                    </thead>
                    <tbody id="whTableBody"></tbody>
                </table>
            </div>
            <div class="pagination">
                <div class="page-info" id="whPageInfo">Showing 0 items</div>
                <div class="page-buttons" id="whPageButtons"></div>
            </div>
            <!-- Warehouse Charts -->
            <div class="charts-grid" style="margin-top: 20px;">
                <div class="chart-card" style="background: white;">
                    <h3 style="color: #0f766e;">📊 Stock per Gender</h3>
                    <div class="chart-container"><canvas id="whCategoryChart"></canvas></div>
                </div>
                <div class="chart-card" style="background: white;">
                    <h3 style="color: #0f766e;">📈 Stock per Area</h3>
                    <div class="chart-container"><canvas id="whAreaChart"></canvas></div>
                </div>
                <div class="chart-card" style="background: white;">
                    <h3 style="color: #0f766e;">🎯 Stock per Series</h3>
                    <div class="chart-container"><canvas id="whSeriesChart"></canvas></div>
                </div>
            </div>
            </div>
        </div>
        <!-- END WAREHOUSE SECTION -->

        </div> <!-- End inventoryView -->

        <!-- ==================== MAX STOCK ANALYSIS VIEW ==================== -->
        <div class="view-container" id="maxstockView">

            <!-- Tabs for Max Stock -->
            <div class="tabs">
                <button class="tab active" data-mstype="warehouse" onclick="switchMaxStockTab('warehouse')">📦 Warehouse</button>
                <button class="tab" data-mstype="retail" onclick="switchMaxStockTab('retail')">🏪 Retail Store</button>
            </div>

            <!-- Filters for Warehouse -->
            <div class="filters" id="msWHFilters" style="display: flex;">
                <div class="filter-group">
                    <label>Area</label>
                    <select id="msWHFilterArea" onchange="updateMaxStockAnalysis()">
                        <option value="">Semua Area</option>
                        <option value="Bali">Bali</option>
                        <option value="Jakarta">Jakarta</option>
                        <option value="Jawa Timur">Jawa Timur</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Fill Rate</label>
                    <select id="msWHFilterFillRate" onchange="updateMaxStockAnalysis()">
                        <option value="">Semua</option>
                        <option value="over">Overflow (>100%)</option>
                        <option value="high">High (80-100%)</option>
                        <option value="medium">Medium (50-80%)</option>
                        <option value="low">Low (<50%)</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>&nbsp;</label>
                    <button class="btn btn-secondary" onclick="resetWHFilters()">↺ Reset</button>
                </div>
            </div>

            <!-- Filters for Retail -->
            <div class="filters" id="msFilters" style="display: none;">
                <div class="filter-group">
                    <label>Area</label>
                    <select id="msFilterArea" onchange="updateStoreDropdown(); updateMaxStockAnalysis()">
                        <option value="">Semua Area</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Store</label>
                    <select id="msFilterStore" onchange="updateMaxStockAnalysis()">
                        <option value="">Semua Store</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Fill Rate</label>
                    <select id="msFilterFillRate" onchange="updateMaxStockAnalysis()">
                        <option value="">Semua</option>
                        <option value="over">Overflow (>100%)</option>
                        <option value="high">High (80-100%)</option>
                        <option value="medium">Medium (50-80%)</option>
                        <option value="low">Low (<50%)</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>&nbsp;</label>
                    <button class="btn btn-secondary" onclick="resetMSFilters()">↺ Reset</button>
                </div>
            </div>

            <!-- Summary Cards -->
            <div class="max-stock-summary" id="maxStockSummary">
                <div class="summary-card green">
                    <div class="label">Total Max Stock</div>
                    <div class="value" id="msTotalMax">0</div>
                    <div class="sub">Kapasitas maksimal</div>
                </div>
                <div class="summary-card blue">
                    <div class="label">Actual Stock</div>
                    <div class="value" id="msTotalActual">0</div>
                    <div class="sub">Stock saat ini</div>
                </div>
                <div class="summary-card yellow">
                    <div class="label">Fill Rate</div>
                    <div class="value" id="msFillRate">0%</div>
                    <div class="sub">Persentase terisi</div>
                </div>
                <div class="summary-card red">
                    <div class="label">Remaining Capacity</div>
                    <div class="value" id="msRemaining">0</div>
                    <div class="sub">Sisa kapasitas</div>
                </div>
            </div>

            <!-- Charts Grid -->
            <div class="charts-grid">
                <div class="chart-card">
                    <h3>📊 Fill Rate per Store/WH</h3>
                    <div class="chart-container"><canvas id="fillRateChart"></canvas></div>
                </div>
                <div class="chart-card">
                    <h3>🎯 Tier Distribution</h3>
                    <div class="chart-container"><canvas id="tierDistChart"></canvas></div>
                </div>
            </div>

            <!-- Store Analysis List -->
            <div class="analysis-grid">
                <div class="analysis-card">
                    <h3>🏪 Detail per Store/Warehouse</h3>
                    <div id="storeAnalysisList" style="max-height: 500px; overflow-y: auto;">
                        <!-- Will be filled by JavaScript -->
                    </div>
                </div>
                <div class="analysis-card">
                    <h3>📈 Tier Breakdown</h3>
                    <div id="tierBreakdown">
                        <!-- Will be filled by JavaScript -->
                    </div>
                </div>
            </div>

        </div> <!-- End maxstockView -->

        <!-- ==================== STOCK CONTROL VIEW ==================== -->
        <div class="view-container" id="stockControlView">
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:20px;">
                <h2 style="margin:0 0 20px 0;color:#1f2937;">📋 Stock Control - Sales & Days of Stock Analysis</h2>

                <!-- Filters Row 1 -->
                <div style="display:flex;gap:15px;flex-wrap:wrap;margin-bottom:15px;">
                    <div style="flex:1;min-width:120px;">
                        <label style="display:block;font-size:0.8rem;color:#6b7280;margin-bottom:5px;">Area</label>
                        <select id="scFilterArea" onchange="renderStockControlTable()" style="width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;">
                            <option value="all">Semua Area</option>
                            <option value="BALI">Bali</option>
                            <option value="JAKARTA">Jakarta</option>
                            <option value="JATIM">Jawa Timur</option>
                            <option value="BATAM">Batam</option>
                            <option value="SULAWESI">Sulawesi</option>
                            <option value="SUMATERA">Sumatera</option>
                        </select>
                    </div>
                    <div style="flex:1;min-width:120px;">
                        <label style="display:block;font-size:0.8rem;color:#6b7280;margin-bottom:5px;">Gender</label>
                        <select id="scFilterGender" onchange="renderStockControlTable()" style="width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;">
                            <option value="">Semua</option>
                            <option value="BABY">Baby</option>
                            <option value="BOYS">Boys</option>
                            <option value="GIRLS">Girls</option>
                            <option value="JUNIOR">Junior</option>
                            <option value="LADIES">Ladies</option>
                            <option value="MEN">Men</option>
                        </select>
                    </div>
                    <div style="flex:1;min-width:120px;">
                        <label style="display:block;font-size:0.8rem;color:#6b7280;margin-bottom:5px;">Series</label>
                        <select id="scFilterSeries" onchange="renderStockControlTable()" style="width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;">
                            <option value="">Semua</option>
                        </select>
                    </div>
                    <div style="flex:1;min-width:120px;">
                        <label style="display:block;font-size:0.8rem;color:#6b7280;margin-bottom:5px;">Tier</label>
                        <select id="scFilterTier" onchange="renderStockControlTable()" style="width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;">
                            <option value="">Semua</option>
                            <option value="1">Tier 1</option>
                            <option value="2">Tier 2</option>
                            <option value="3">Tier 3</option>
                        </select>
                    </div>
                </div>

                <!-- Filters Row 2 -->
                <div style="display:flex;gap:15px;flex-wrap:wrap;align-items:flex-end;">
                    <div style="flex:1;min-width:120px;">
                        <label style="display:block;font-size:0.8rem;color:#6b7280;margin-bottom:5px;">TW+TO Filter</label>
                        <select id="scFilterTWTO" onchange="renderStockControlTable()" style="width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;">
                            <option value="">Semua</option>
                            <option value="critical">&lt; 2 minggu (Critical)</option>
                            <option value="low">2-4 minggu (Low)</option>
                            <option value="normal">4-8 minggu (Normal)</option>
                            <option value="high">&gt; 8 minggu (High)</option>
                        </select>
                    </div>
                    <div style="flex:2;min-width:200px;">
                        <label style="display:block;font-size:0.8rem;color:#6b7280;margin-bottom:5px;">Search SKU/Article</label>
                        <input type="text" id="scSearch" onkeyup="renderStockControlTable()" placeholder="Cari kode SKU atau nama artikel..." style="width:100%;padding:8px 12px;border:1px solid #d1d5db;border-radius:8px;font-size:0.9rem;">
                    </div>
                    <div>
                        <button onclick="exportStockControl()" style="padding:8px 16px;background:#10b981;color:white;border:none;border-radius:8px;cursor:pointer;font-size:0.9rem;">
                            📥 Export
                        </button>
                    </div>
                </div>
            </div>

            <!-- Stock Control Table -->
            <div style="background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);overflow:hidden;">
                <div style="overflow-x:auto;">
                    <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                        <thead>
                            <tr style="background:linear-gradient(135deg,#1f2937 0%,#374151 100%);">
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;color:white;">Kode SKU</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;color:white;">Size</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;color:white;">Article</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;color:white;">Series</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;color:white;">Gender</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;color:white;">Tier</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;">M1</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;">M2</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;">M3</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;background:#92400e;">Avg</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;">WH Pusat</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;">WH Bali</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;">WH Jkt</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;background:#1e3a8a;">WH Total</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;background:#166534;">Toko</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;color:white;background:#7c3aed;">Global</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;color:white;">TW</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;color:white;">TO</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;color:white;background:#dc2626;">TW+TO</th>
                            </tr>
                        </thead>
                        <tbody id="scTableBody">
                        </tbody>
                    </table>
                </div>
                <!-- Pagination -->
                <div style="padding:15px;border-top:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;">
                    <div id="scPageInfo" style="color:#6b7280;font-size:0.85rem;"></div>
                    <div id="scPagination" style="display:flex;gap:5px;"></div>
                </div>
            </div>
        </div> <!-- End stockControlView -->

    </div>

    <!-- Modal Minus on Hand Detail -->
    <div class="modal-overlay" id="negativeModal" onclick="closeNegativeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2>⚠️ Detail Minus on Hand</h2>
                <button class="modal-close" onclick="closeNegativeModal()">&times;</button>
            </div>
            <div class="modal-body" id="negativeModalBody">
                <!-- Content will be filled by JavaScript -->
            </div>
        </div>
    </div>

    <!-- Modal Tier Article Detail -->
    <div class="modal-overlay" id="tierModal" onclick="closeTierModal(event)">
        <div class="modal-content" style="max-width: 900px;" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2 id="tierModalTitle">📦 Detail Artikel</h2>
                <button class="modal-close" onclick="closeTierModal()">&times;</button>
            </div>
            <div class="modal-body" id="tierModalBody">
                <!-- Content will be filled by JavaScript -->
            </div>
        </div>
    </div>

    <!-- Modal SKU Detail (when clicking Kode Kecil) -->
    <div class="modal-overlay" id="skuModal" onclick="closeSkuModal(event)">
        <div class="modal-content" style="max-width: 800px;" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h2 id="skuModalTitle">📋 Detail SKU</h2>
                <button class="modal-close" onclick="closeSkuModal()">&times;</button>
            </div>
            <div class="modal-body" id="skuModalBody">
                <!-- Content will be filled by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        // Embedded data
        const allData = ''' + data_json + ''';
        const allStores = ''' + stores_json + ''';
        const storeAreaMap = ''' + store_area_json + ''';  // Mapping dari Master Store/Warehouse
        const maxStockMap = ''' + max_stock_json + ''';    // Max Stock per store/WH
        const assortmentMap = ''' + assortment_json + ''';  // Assortment per kode kecil

        let currentEntity = 'DDD';
        let currentType = 'warehouse';
        let currentArea = '';
        let currentStore = '';
        // Retail charts
        let rtCategoryChart, rtAreaChart, rtSeriesChart;
        // Warehouse charts
        let whCategoryChart, whAreaChart, whSeriesChart;

        // Retail table state
        let rtFilteredData = [];
        let rtCurrentPage = 1;
        let rtSortField = 'total';
        let rtSortDir = 'desc';

        // Warehouse table state
        let whFilteredData = [];
        let whCurrentPage = 1;
        let whSortField = 'total';
        let whSortDir = 'desc';

        const itemsPerPage = 50;

        // Max Stock Analysis state
        let currentView = 'inventory';
        let currentMSType = 'warehouse';
        let fillRateChart, tierDistChart;
        let filteredTierArticles = {};  // Store articles by tier for modal

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            updateEntityCounts();
            updateDisplay();
        });

        function updateEntityCounts() {
            // Entity counts removed from UI - function kept for compatibility
        }

        function selectEntity(entity) {
            currentEntity = entity;
            document.querySelectorAll('.entity-pill').forEach(pill => {
                pill.classList.toggle('active', pill.dataset.entity === entity);
            });
            rtCurrentPage = 1;
            whCurrentPage = 1;
            currentArea = '';
            currentStore = '';

            // Show/hide tables and stats based on entity
            // DDD has both retail and warehouse, others only warehouse
            const hasRetail = (entity === 'DDD');
            document.getElementById('retailSectionWrapper').style.display = hasRetail ? 'block' : 'none';

            updateDisplay();

            // Update Max Stock Analysis jika view aktif
            if (currentView === 'maxstock') {
                updateMaxStockAnalysis();
            }
        }

        function switchTab(type) {
            currentType = type;
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.toggle('active', tab.dataset.type === type);
            });
            const titles = {
                warehouse: '🏪 Retail Stock Data',
                retail: '🏪 Retail Stock Data',
                all: '🏪 Retail Stock Data'
            };
            document.getElementById('tableTitle').textContent = titles[type];
            currentPage = 1;
            currentArea = '';
            currentStore = '';
            updateDisplay();
        }

        function selectArea(area) {
            currentArea = currentArea === area ? '' : area;
            currentStore = '';
            document.querySelectorAll('.area-tag').forEach(tag => {
                tag.classList.toggle('active', tag.dataset.area === currentArea);
            });
            applyFilters();
            renderStoreGrid();
        }

        function selectStore(store) {
            currentStore = currentStore === store ? '' : store;
            document.querySelectorAll('.store-item').forEach(item => {
                item.classList.toggle('active', item.dataset.store === currentStore);
            });
            applyFilters();
        }

        function getData() {
            var entityData = allData[currentEntity] || {};
            var data = [];
            if (currentType === 'all') {
                var wh = entityData.warehouse || [];
                var rt = entityData.retail || [];
                data = wh.concat(rt);
            } else {
                data = entityData[currentType] || [];
            }
            return data;
        }

        function updateDisplay() {
            const data = getData();

            // Update series filters for both tables
            updateSeriesDropdowns();

            // Update retail table (only if DDD)
            if (currentEntity === 'DDD') {
                updateTableAreaDropdown();
                updateTableStoreDropdown();
                applyRetailFilters();
            }

            // Update warehouse table
            updateWhAreaDropdown();
            updateWhWarehouseDropdown();
            applyWarehouseFilters();
        }

        function updateSeriesDropdowns() {
            var entityData = allData[currentEntity] || {};
            var rtData = entityData.retail || [];
            var whData = entityData.warehouse || [];

            // Get unique series from retail
            const rtSeriesSet = new Set();
            rtData.forEach(item => {
                if (item.series && item.series !== '-' && item.series !== '') {
                    rtSeriesSet.add(item.series);
                }
            });
            const rtSeriesList = Array.from(rtSeriesSet).sort();

            const rtSelect = document.getElementById('rtFilterSeries');
            if (rtSelect) {
                rtSelect.innerHTML = '<option value="">Semua</option>';
                rtSeriesList.forEach(s => {
                    rtSelect.innerHTML += `<option value="${s}">${s}</option>`;
                });
            }

            // Get unique series from warehouse
            const whSeriesSet = new Set();
            whData.forEach(item => {
                if (item.series && item.series !== '-' && item.series !== '') {
                    whSeriesSet.add(item.series);
                }
            });
            const whSeriesList = Array.from(whSeriesSet).sort();

            const whSelect = document.getElementById('whFilterSeries');
            if (whSelect) {
                whSelect.innerHTML = '<option value="">Semua</option>';
                whSeriesList.forEach(s => {
                    whSelect.innerHTML += `<option value="${s}">${s}</option>`;
                });
            }
        }

        function updateSeriesFilter(data) {
            // Legacy - keep for compatibility
            const seriesSet = new Set();
            data.forEach(item => {
                if (item.series && item.series !== '-' && item.series !== '') {
                    seriesSet.add(item.series);
                }
            });
            const seriesList = Array.from(seriesSet).sort();

            const select = document.getElementById('filterSeries');
            if (!select) return;
            const currentValue = select.value;

            // Keep first option (Semua)
            select.innerHTML = '<option value="">Semua</option>';
            seriesList.forEach(s => {
                select.innerHTML += `<option value="${s}">${s}</option>`;
            });

            // Restore previous selection if still valid
            if (seriesList.includes(currentValue)) {
                select.value = currentValue;
            }
        }

        // Update Retail charts
        function updateRetailCharts(data, locationFilter, areaFilter) {
            const catData = {}, areaData = {}, seriesData = {};
            // Total SKU = jumlah item dalam data (data sudah difilter sebelum masuk fungsi ini)
            let totalSku = data.length;
            let totalStock = 0;
            let minusArticles = 0;
            let minusPairs = 0;
            let minusLocations = new Set();

            data.forEach(item => {
                const gender = item.gender || 'BABY';
                const series = item.series || '-';
                const seriesGender = (series && series !== '-' && series !== '') ? series + ' - ' + gender : '';

                // Calculate stock value based on filter
                let stockValue = 0;

                if (locationFilter) {
                    // Store filter - get stock for this store
                    if (item.store_stock && item.store_stock[locationFilter] !== undefined) {
                        stockValue = item.store_stock[locationFilter];
                    }
                } else if (areaFilter) {
                    // Area filter - sum stock for all stores in this area
                    if (item.store_stock) {
                        Object.entries(item.store_stock).forEach(([loc, stock]) => {
                            if (getAreaFromStore(loc) === areaFilter) {
                                stockValue += stock;
                            }
                        });
                    }
                } else {
                    // No filter - use total
                    stockValue = item.total || 0;
                }

                catData[gender] = (catData[gender] || 0) + Math.max(0, stockValue);
                if (seriesGender) {
                    seriesData[seriesGender] = (seriesData[seriesGender] || 0) + Math.max(0, stockValue);
                }

                if (stockValue > 0) totalStock += stockValue;

                // Area calculation
                if (locationFilter) {
                    if (item.store_stock && item.store_stock[locationFilter] !== undefined) {
                        const area = getAreaFromStore(locationFilter);
                        areaData[area] = (areaData[area] || 0) + Math.max(0, item.store_stock[locationFilter]);
                    }
                } else if (areaFilter) {
                    if (item.store_stock) {
                        Object.entries(item.store_stock).forEach(([loc, stock]) => {
                            if (getAreaFromStore(loc) === areaFilter) {
                                areaData[areaFilter] = (areaData[areaFilter] || 0) + Math.max(0, stock);
                            }
                        });
                    }
                } else if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([store, stock]) => {
                        const area = getAreaFromStore(store);
                        areaData[area] = (areaData[area] || 0) + Math.max(0, stock);
                    });
                }

                // Minus calculation
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([storeName, stock]) => {
                        if (locationFilter && storeName !== locationFilter) return;
                        if (areaFilter && getAreaFromStore(storeName) !== areaFilter) return;
                        if (stock < 0) {
                            minusArticles++;
                            minusPairs += Math.abs(stock);
                            minusLocations.add(storeName);
                        }
                    });
                }
            });

            // Update retail stats
            document.getElementById('rtTotalSku').textContent = totalSku.toLocaleString('id-ID');
            document.getElementById('rtTotalStock').textContent = totalStock.toLocaleString('id-ID');
            const locCount = minusLocations.size;
            document.getElementById('rtNegativeStock').textContent = locCount.toLocaleString('id-ID') + ' lokasi';
            document.getElementById('rtNegativeSubValue').textContent = minusArticles.toLocaleString('id-ID') + ' artikel | -' + minusPairs.toLocaleString('id-ID') + ' pairs';

            // Update retail charts
            const colors = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6', '#ef4444', '#84cc16'];

            if (rtCategoryChart) rtCategoryChart.destroy();
            rtCategoryChart = new Chart(document.getElementById('rtCategoryChart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(catData),
                    datasets: [{ data: Object.values(catData), backgroundColor: colors, borderWidth: 0 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { font: { family: 'Poppins', size: 11 } } } } }
            });

            if (rtAreaChart) rtAreaChart.destroy();
            rtAreaChart = new Chart(document.getElementById('rtAreaChart'), {
                type: 'bar',
                data: {
                    labels: Object.keys(areaData),
                    datasets: [{ label: 'Stock', data: Object.values(areaData), backgroundColor: colors, borderRadius: 6 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });

            if (rtSeriesChart) rtSeriesChart.destroy();
            const topSeries = Object.entries(seriesData).sort((a,b) => b[1] - a[1]).slice(0, 8);
            rtSeriesChart = new Chart(document.getElementById('rtSeriesChart'), {
                type: 'bar',
                data: {
                    labels: topSeries.map(s => s[0]),
                    datasets: [{ label: 'Stock', data: topSeries.map(s => s[1]), backgroundColor: colors, borderRadius: 6 }]
                },
                options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
            });
        }

        // Update Warehouse charts
        function updateWarehouseCharts(data, locationFilter, areaFilter) {
            const catData = {}, areaData = {}, seriesData = {};
            // Total SKU = jumlah item dalam data (data sudah difilter sebelum masuk fungsi ini)
            let totalSku = data.length;
            let totalStock = 0;
            let minusArticles = 0;
            let minusPairs = 0;
            let minusLocations = new Set();

            data.forEach(item => {
                const gender = item.gender || 'BABY';
                const series = item.series || '-';
                const seriesGender = (series && series !== '-' && series !== '') ? series + ' - ' + gender : '';

                // Calculate stock value based on filter
                let stockValue = 0;

                if (locationFilter) {
                    // Warehouse filter - get stock for this warehouse
                    if (item.store_stock && item.store_stock[locationFilter] !== undefined) {
                        stockValue = item.store_stock[locationFilter];
                    }
                } else if (areaFilter) {
                    // Area filter - sum stock for all warehouses in this area
                    if (item.store_stock) {
                        Object.entries(item.store_stock).forEach(([loc, stock]) => {
                            if (getAreaFromStore(loc) === areaFilter) {
                                stockValue += stock;
                            }
                        });
                    }
                } else {
                    // No filter - use total
                    stockValue = item.total || 0;
                }

                catData[gender] = (catData[gender] || 0) + Math.max(0, stockValue);
                if (seriesGender) {
                    seriesData[seriesGender] = (seriesData[seriesGender] || 0) + Math.max(0, stockValue);
                }

                if (stockValue > 0) totalStock += stockValue;

                // Area calculation
                if (locationFilter) {
                    if (item.store_stock && item.store_stock[locationFilter] !== undefined) {
                        const area = getAreaFromStore(locationFilter);
                        areaData[area] = (areaData[area] || 0) + Math.max(0, item.store_stock[locationFilter]);
                    }
                } else if (areaFilter) {
                    if (item.store_stock) {
                        Object.entries(item.store_stock).forEach(([loc, stock]) => {
                            if (getAreaFromStore(loc) === areaFilter) {
                                areaData[areaFilter] = (areaData[areaFilter] || 0) + Math.max(0, stock);
                            }
                        });
                    }
                } else if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([store, stock]) => {
                        const area = getAreaFromStore(store);
                        areaData[area] = (areaData[area] || 0) + Math.max(0, stock);
                    });
                }

                // Minus calculation
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([storeName, stock]) => {
                        if (locationFilter && storeName !== locationFilter) return;
                        if (areaFilter && getAreaFromStore(storeName) !== areaFilter) return;
                        if (stock < 0) {
                            minusArticles++;
                            minusPairs += Math.abs(stock);
                            minusLocations.add(storeName);
                        }
                    });
                }
            });

            // Update warehouse stats
            document.getElementById('whTotalSku').textContent = totalSku.toLocaleString('id-ID');
            document.getElementById('whTotalStock').textContent = totalStock.toLocaleString('id-ID');
            const whLocCount = minusLocations.size;
            document.getElementById('whNegativeStock').textContent = whLocCount.toLocaleString('id-ID') + ' lokasi';
            document.getElementById('whNegativeSubValue').textContent = minusArticles.toLocaleString('id-ID') + ' artikel | -' + minusPairs.toLocaleString('id-ID') + ' pairs';

            // Update warehouse charts
            const colors = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6', '#ef4444', '#84cc16'];

            if (whCategoryChart) whCategoryChart.destroy();
            whCategoryChart = new Chart(document.getElementById('whCategoryChart'), {
                type: 'doughnut',
                data: {
                    labels: Object.keys(catData),
                    datasets: [{ data: Object.values(catData), backgroundColor: colors, borderWidth: 0 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { font: { family: 'Poppins', size: 11 } } } } }
            });

            if (whAreaChart) whAreaChart.destroy();
            // Convert area names to warehouse codes for warehouse chart
            const whAreaLabels = Object.keys(areaData).map(area => {
                if (area === 'Jakarta') return 'WHJ';
                if (area === 'Bali') return 'WHB';
                if (area === 'Jawa Timur') return 'WHS';
                return area;
            });
            whAreaChart = new Chart(document.getElementById('whAreaChart'), {
                type: 'bar',
                data: {
                    labels: whAreaLabels,
                    datasets: [{ label: 'Stock', data: Object.values(areaData), backgroundColor: colors, borderRadius: 6 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
            });

            if (whSeriesChart) whSeriesChart.destroy();
            const topSeries = Object.entries(seriesData).sort((a,b) => b[1] - a[1]).slice(0, 8);
            whSeriesChart = new Chart(document.getElementById('whSeriesChart'), {
                type: 'bar',
                data: {
                    labels: topSeries.map(s => s[0]),
                    datasets: [{ label: 'Stock', data: topSeries.map(s => s[1]), backgroundColor: colors, borderRadius: 6 }]
                },
                options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } } }
            });
        }

        function getAreaFromStore(storeName) {
            const s = storeName.toLowerCase().trim();

            // 1. Cek exact match di storeAreaMap (dari Master Store/Warehouse)
            if (storeAreaMap[s]) return storeAreaMap[s];

            // 2. Cek partial match di storeAreaMap
            for (const [key, area] of Object.entries(storeAreaMap)) {
                if (s.includes(key) || key.includes(s)) return area;
            }

            // 3. Fallback untuk warehouse - detect area from warehouse name
            const upper = storeName.toUpperCase();
            if (upper.includes('WAREHOUSE') || upper.includes('GUDANG')) {
                // WHB - Warehouse Bali
                if (upper.includes('BALI') || upper.includes('GATSU')) return 'Bali';
                // WHJ - Warehouse Jakarta
                if (upper.includes('JAKARTA') || upper.includes('PLUIT')) return 'Jakarta';
                // WHS - Warehouse Pusat (Jawa Timur)
                if (upper.includes('PUSAT')) return 'Jawa Timur';
                return 'Jawa Timur'; // Default warehouse to Jawa Timur
            }

            // 4. Default ke Bali
            return 'Bali';
        }

        function renderAreaTags() {
            var storesData = allStores[currentEntity] || {};
            var stores = storesData[currentType] || [];
            const areas = new Set();

            stores.forEach(s => areas.add(getAreaFromStore(s.name)));

            const areaColors = {
                'Bali': 'bali', 'Jakarta': 'jakarta', 'Jawa Timur': 'jawa-timur',
                'Jawa Barat': 'jawa-barat', 'Lombok NTT': 'lombok', 'Sulawesi': 'sulawesi',
                'Sumatera': 'sumatera', 'Warehouse': 'warehouse'
            };

            const tagsHtml = Array.from(areas).map(area =>
                `<div class="area-tag ${areaColors[area] || 'bali'} ${currentArea === area ? 'active' : ''}"
                     data-area="${area}" onclick="selectArea('${area}')">${area}</div>`
            ).join('');

            document.getElementById('areaTags').innerHTML = tagsHtml;
        }

        function renderStoreGrid() {
            var storesData = allStores[currentEntity] || {};
            var stores = storesData[currentType] || [];
            const data = getData();

            // Calculate stock per store
            const storeStock = {};
            data.forEach(item => {
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([store, stock]) => {
                        storeStock[store] = (storeStock[store] || 0) + stock;
                    });
                }
            });

            let filteredStores = stores;
            if (currentArea) {
                filteredStores = stores.filter(s => getAreaFromStore(s.name) === currentArea);
            }

            const storeHtml = filteredStores.slice(0, 30).map(s => {
                const stock = storeStock[s.name] || 0;
                const area = getAreaFromStore(s.name);
                return `<div class="store-item ${currentStore === s.name ? 'active' : ''}"
                            data-store="${s.name}" onclick="selectStore('${s.name}')">
                    <div>
                        <div class="store-name">${s.name}</div>
                        <div class="store-area">${area}</div>
                    </div>
                    <div class="store-stock">${stock.toLocaleString('id-ID')}</div>
                </div>`;
            }).join('');

            document.getElementById('storeGrid').innerHTML = storeHtml || '<div style="color:#9ca3af;padding:20px;">Tidak ada store untuk area ini</div>';
        }

        // ==================== RETAIL TABLE FUNCTIONS ====================
        function applyRetailFilters() {
            var entityData = allData[currentEntity] || {};
            let data = entityData.retail || [];

            const search = document.getElementById('rtSearchInput').value.toLowerCase();
            const gender = document.getElementById('rtFilterGender').value;
            const series = document.getElementById('rtFilterSeries').value;
            const tableArea = document.getElementById('tableFilterArea').value;
            const tableStore = document.getElementById('tableFilterStore').value;
            const tableTier = document.getElementById('tableFilterTier').value;

            if (search) {
                data = data.filter(item => item.sku.toLowerCase().includes(search) || (item.name || '').toLowerCase().includes(search) || (item.kode_kecil || '').toLowerCase().includes(search));
            }
            if (gender) {
                data = data.filter(item => (item.gender || '').toUpperCase().includes(gender.toUpperCase()));
            }
            if (tableTier) {
                data = data.filter(item => (item.tier || '') === tableTier);
            }
            if (series) {
                data = data.filter(item => (item.series || '').includes(series) || (item.name || '').toUpperCase().includes(series));
            }
            if (tableStore) {
                // Filter: hanya item yang punya stock di store ini (stock !== 0)
                data = data.filter(item => item.store_stock && item.store_stock[tableStore] !== undefined && item.store_stock[tableStore] !== 0);
            } else if (tableArea) {
                // Filter: hanya item yang punya stock di area ini (stock !== 0)
                data = data.filter(item => {
                    if (!item.store_stock) return false;
                    return Object.entries(item.store_stock).some(([store, stock]) => !isWarehouseLocation(store) && getAreaFromStore(store) === tableArea && stock !== 0);
                });
            }

            // Group by kode_kecil
            const groupedMap = {};
            data.forEach(item => {
                const kk = (item.kode_kecil || '').toUpperCase();
                if (!kk) return;
                if (!groupedMap[kk]) {
                    groupedMap[kk] = { ...item, total: 0, store_stock: {} };
                }
                groupedMap[kk].total += item.total || 0;
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([store, qty]) => {
                        groupedMap[kk].store_stock[store] = (groupedMap[kk].store_stock[store] || 0) + qty;
                    });
                }
            });
            data = Object.values(groupedMap);

            // Sort
            data.sort((a, b) => {
                let aVal, bVal;
                if (rtSortField === 'total' && tableStore) {
                    aVal = (a.store_stock && a.store_stock[tableStore]) || 0;
                    bVal = (b.store_stock && b.store_stock[tableStore]) || 0;
                } else {
                    aVal = a[rtSortField];
                    bVal = b[rtSortField];
                }
                if (typeof aVal === 'string') aVal = (aVal || '').toLowerCase();
                if (typeof bVal === 'string') bVal = (bVal || '').toLowerCase();
                if (aVal < bVal) return rtSortDir === 'asc' ? -1 : 1;
                if (aVal > bVal) return rtSortDir === 'asc' ? 1 : -1;
                return 0;
            });

            rtFilteredData = data;
            rtCurrentPage = 1;
            renderRetailTable();

            // Update retail charts with filtered data
            updateRetailCharts(data, tableStore, tableArea);
        }

        function sortRetailData(field) {
            rtSortDir = rtSortField === field && rtSortDir === 'desc' ? 'asc' : 'desc';
            rtSortField = field;
            applyRetailFilters();
        }

        function resetRetailFilters() {
            document.getElementById('rtSearchInput').value = '';
            document.getElementById('rtFilterGender').value = '';
            document.getElementById('rtFilterSeries').value = '';
            document.getElementById('tableFilterArea').value = '';
            document.getElementById('tableFilterStore').value = '';
            document.getElementById('tableFilterTier').value = '';
            rtSortField = 'total';
            rtSortDir = 'desc';
            updateTableStoreDropdown();
            applyRetailFilters();
        }

        function renderRetailTable() {
            const start = (rtCurrentPage - 1) * itemsPerPage;
            const pageData = rtFilteredData.slice(start, start + itemsPerPage);
            const tbody = document.getElementById('rtTableBody');
            const tableStore = document.getElementById('tableFilterStore').value;

            if (!pageData.length) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#9ca3af;">Tidak ada data</td></tr>';
            } else {
                tbody.innerHTML = pageData.map(item => {
                    let displayStock = item.total;
                    if (tableStore && item.store_stock) {
                        displayStock = item.store_stock[tableStore] || 0;
                    }
                    const kodeKecil = item.kode_kecil || '-';
                    return `<tr>
                        <td><a href="#" onclick="showSkuDetail('${kodeKecil}', 'retail'); return false;" style="color:#1f2937; text-decoration:underline; font-weight:600; cursor:pointer;">${kodeKecil}</a></td>
                        <td>${item.gender || '-'}</td>
                        <td>${item.series || '-'}</td>
                        <td>${item.tipe || '-'}</td>
                        <td>${item.name || '-'}</td>
                        <td>${item.tier || '-'}</td>
                        <td><strong>${displayStock.toLocaleString('id-ID')}</strong></td>
                    </tr>`;
                }).join('');
            }
            renderRetailPagination();
        }

        function renderRetailPagination() {
            const totalPages = Math.ceil(rtFilteredData.length / itemsPerPage);
            const pageInfo = document.getElementById('rtPageInfo');
            const pageButtons = document.getElementById('rtPageButtons');

            const start = (rtCurrentPage - 1) * itemsPerPage + 1;
            const end = Math.min(rtCurrentPage * itemsPerPage, rtFilteredData.length);
            pageInfo.textContent = rtFilteredData.length ? `Showing ${start}-${end} of ${rtFilteredData.length} items` : 'Showing 0 items';

            let btns = '';
            if (totalPages > 1) {
                if (rtCurrentPage > 1) btns += `<button onclick="rtGoToPage(${rtCurrentPage - 1})">‹</button>`;
                for (let i = Math.max(1, rtCurrentPage - 2); i <= Math.min(totalPages, rtCurrentPage + 2); i++) {
                    btns += `<button class="${i === rtCurrentPage ? 'active' : ''}" onclick="rtGoToPage(${i})">${i}</button>`;
                }
                if (rtCurrentPage < totalPages) btns += `<button onclick="rtGoToPage(${rtCurrentPage + 1})">›</button>`;
            }
            pageButtons.innerHTML = btns;
        }

        function rtGoToPage(page) {
            rtCurrentPage = page;
            renderRetailTable();
        }

        // ==================== WAREHOUSE TABLE FUNCTIONS ====================
        function applyWarehouseFilters() {
            var entityData = allData[currentEntity] || {};
            let data = entityData.warehouse || [];

            const search = document.getElementById('whSearchInput').value.toLowerCase();
            const gender = document.getElementById('whFilterGender').value;
            const series = document.getElementById('whFilterSeries').value;
            const whArea = document.getElementById('whFilterArea').value;
            const whWarehouse = document.getElementById('whFilterWarehouse').value;
            const whTier = document.getElementById('whFilterTier').value;

            if (search) {
                data = data.filter(item => item.sku.toLowerCase().includes(search) || (item.name || '').toLowerCase().includes(search) || (item.kode_kecil || '').toLowerCase().includes(search));
            }
            if (gender) {
                data = data.filter(item => (item.gender || '').toUpperCase().includes(gender.toUpperCase()));
            }
            if (whTier) {
                data = data.filter(item => (item.tier || '') === whTier);
            }
            if (series) {
                data = data.filter(item => (item.series || '').includes(series) || (item.name || '').toUpperCase().includes(series));
            }
            if (whWarehouse) {
                // Filter: hanya item yang punya stock di warehouse ini (stock !== 0)
                data = data.filter(item => item.store_stock && item.store_stock[whWarehouse] !== undefined && item.store_stock[whWarehouse] !== 0);
            } else if (whArea) {
                // Filter: hanya item yang punya stock di area ini (stock !== 0)
                data = data.filter(item => {
                    if (!item.store_stock) return false;
                    return Object.entries(item.store_stock).some(([wh, stock]) => getAreaFromStore(wh) === whArea && stock !== 0);
                });
            }

            // Group by kode_kecil
            const groupedMap = {};
            data.forEach(item => {
                const kk = (item.kode_kecil || '').toUpperCase();
                if (!kk) return;
                if (!groupedMap[kk]) {
                    groupedMap[kk] = { ...item, total: 0, store_stock: {} };
                }
                groupedMap[kk].total += item.total || 0;
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([wh, qty]) => {
                        groupedMap[kk].store_stock[wh] = (groupedMap[kk].store_stock[wh] || 0) + qty;
                    });
                }
            });
            data = Object.values(groupedMap);

            // Sort
            data.sort((a, b) => {
                let aVal, bVal;
                if (whSortField === 'total' && whWarehouse) {
                    aVal = (a.store_stock && a.store_stock[whWarehouse]) || 0;
                    bVal = (b.store_stock && b.store_stock[whWarehouse]) || 0;
                } else {
                    aVal = a[whSortField];
                    bVal = b[whSortField];
                }
                if (typeof aVal === 'string') aVal = (aVal || '').toLowerCase();
                if (typeof bVal === 'string') bVal = (bVal || '').toLowerCase();
                if (aVal < bVal) return whSortDir === 'asc' ? -1 : 1;
                if (aVal > bVal) return whSortDir === 'asc' ? 1 : -1;
                return 0;
            });

            whFilteredData = data;
            whCurrentPage = 1;
            renderWarehouseTable();

            // Update warehouse charts with filtered data
            updateWarehouseCharts(data, whWarehouse, whArea);
        }

        function sortWarehouseData(field) {
            whSortDir = whSortField === field && whSortDir === 'desc' ? 'asc' : 'desc';
            whSortField = field;
            applyWarehouseFilters();
        }

        function resetWarehouseFilters() {
            document.getElementById('whSearchInput').value = '';
            document.getElementById('whFilterGender').value = '';
            document.getElementById('whFilterSeries').value = '';
            document.getElementById('whFilterArea').value = '';
            document.getElementById('whFilterWarehouse').value = '';
            document.getElementById('whFilterTier').value = '';
            whSortField = 'total';
            whSortDir = 'desc';
            updateWhWarehouseDropdown();
            applyWarehouseFilters();
        }

        function renderWarehouseTable() {
            const start = (whCurrentPage - 1) * itemsPerPage;
            const pageData = whFilteredData.slice(start, start + itemsPerPage);
            const tbody = document.getElementById('whTableBody');
            const whWarehouse = document.getElementById('whFilterWarehouse').value;

            if (!pageData.length) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#9ca3af;">Tidak ada data</td></tr>';
            } else {
                tbody.innerHTML = pageData.map(item => {
                    let displayStock = item.total;
                    if (whWarehouse && item.store_stock) {
                        displayStock = item.store_stock[whWarehouse] || 0;
                    }
                    const kodeKecil = item.kode_kecil || '-';
                    return `<tr>
                        <td><a href="#" onclick="showSkuDetail('${kodeKecil}', 'warehouse'); return false;" style="color:#1f2937; text-decoration:underline; font-weight:600; cursor:pointer;">${kodeKecil}</a></td>
                        <td>${item.gender || '-'}</td>
                        <td>${item.series || '-'}</td>
                        <td>${item.tipe || '-'}</td>
                        <td>${item.name || '-'}</td>
                        <td>${item.tier || '-'}</td>
                        <td><strong>${displayStock.toLocaleString('id-ID')}</strong></td>
                    </tr>`;
                }).join('');
            }
            renderWarehousePagination();
        }

        function renderWarehousePagination() {
            const totalPages = Math.ceil(whFilteredData.length / itemsPerPage);
            const pageInfo = document.getElementById('whPageInfo');
            const pageButtons = document.getElementById('whPageButtons');

            const start = (whCurrentPage - 1) * itemsPerPage + 1;
            const end = Math.min(whCurrentPage * itemsPerPage, whFilteredData.length);
            pageInfo.textContent = whFilteredData.length ? `Showing ${start}-${end} of ${whFilteredData.length} items` : 'Showing 0 items';

            let btns = '';
            if (totalPages > 1) {
                if (whCurrentPage > 1) btns += `<button onclick="whGoToPage(${whCurrentPage - 1})">‹</button>`;
                for (let i = Math.max(1, whCurrentPage - 2); i <= Math.min(totalPages, whCurrentPage + 2); i++) {
                    btns += `<button class="${i === whCurrentPage ? 'active' : ''}" onclick="whGoToPage(${i})">${i}</button>`;
                }
                if (whCurrentPage < totalPages) btns += `<button onclick="whGoToPage(${whCurrentPage + 1})">›</button>`;
            }
            pageButtons.innerHTML = btns;
        }

        function whGoToPage(page) {
            whCurrentPage = page;
            renderWarehouseTable();
        }

        function updateWhAreaDropdown() {
            var entityData = allData[currentEntity] || {};
            var whData = entityData.warehouse || [];
            const areas = new Set();

            whData.forEach(item => {
                if (item.store_stock) {
                    Object.keys(item.store_stock).forEach(wh => {
                        areas.add(getAreaFromStore(wh));
                    });
                }
            });

            const areaSelect = document.getElementById('whFilterArea');
            areaSelect.innerHTML = '<option value="">Semua Area</option>';
            Array.from(areas).sort().forEach(area => {
                areaSelect.innerHTML += `<option value="${area}">${area}</option>`;
            });
        }

        function updateWhWarehouseDropdown() {
            var entityData = allData[currentEntity] || {};
            var whData = entityData.warehouse || [];
            const whArea = document.getElementById('whFilterArea').value;

            const whStock = {};
            whData.forEach(item => {
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([wh, stock]) => {
                        if (!whArea || getAreaFromStore(wh) === whArea) {
                            if (!whStock[wh]) whStock[wh] = 0;
                            whStock[wh] += stock || 0;
                        }
                    });
                }
            });

            const whSelect = document.getElementById('whFilterWarehouse');
            const currentValue = whSelect.value;
            whSelect.innerHTML = '<option value="">Semua Warehouse</option>';

            Object.entries(whStock)
                .sort((a, b) => a[0].localeCompare(b[0]))
                .forEach(([name, stock]) => {
                    whSelect.innerHTML += `<option value="${name}">${name}</option>`;
                });

            if (whStock[currentValue]) {
                whSelect.value = currentValue;
            }
        }

        // Legacy functions - keep for compatibility
        function applyFilters() {
            applyRetailFilters();
        }

        function sortData(field) {
            sortRetailData(field);
        }

        function resetFilters() {
            resetRetailFilters();
        }

        function resetTableFilters() {
            document.getElementById('rtSearchInput').value = '';
            document.getElementById('tableFilterArea').value = '';
            document.getElementById('tableFilterStore').value = '';
            document.getElementById('tableFilterTier').value = '';
            updateTableStoreDropdown();
            applyFilters();
        }

        function getAllStoresAndWarehouses() {
            // Get ALL data (warehouse + retail) regardless of current tab
            var entityData = allData[currentEntity] || {};
            var wh = entityData.warehouse || [];
            var rt = entityData.retail || [];
            return wh.concat(rt);
        }

        function isWarehouseLocation(name) {
            const upper = (name || '').toUpperCase();
            return upper.includes('WAREHOUSE') || upper.includes('GUDANG') || upper.includes('BOX') ||
                   upper.includes('PROTOL') || upper.includes('REJECT') || upper.includes('WH ') ||
                   upper.startsWith('WH') || upper.includes('PUSAT');
        }

        function updateTableAreaDropdown() {
            var entityData = allData[currentEntity] || {};
            var rtData = entityData.retail || [];
            const areas = new Set();

            // Collect unique areas from retail stores only
            rtData.forEach(item => {
                if (item.store_stock) {
                    Object.keys(item.store_stock).forEach(store => {
                        if (!isWarehouseLocation(store)) {
                            const area = getAreaFromStore(store);
                            if (area && area !== 'Warehouse') areas.add(area);
                        }
                    });
                }
            });

            const areaSelect = document.getElementById('tableFilterArea');
            const currentValue = areaSelect.value;
            areaSelect.innerHTML = '<option value="">Semua Area</option>';

            Array.from(areas).sort().forEach(area => {
                areaSelect.innerHTML += `<option value="${area}">${area}</option>`;
            });

            if (areas.has(currentValue)) {
                areaSelect.value = currentValue;
            }

            updateTableStoreDropdown();
        }

        function updateTableStoreDropdown() {
            var entityData = allData[currentEntity] || {};
            var rtData = entityData.retail || [];
            const selectedArea = document.getElementById('tableFilterArea').value;
            const storeSelect = document.getElementById('tableFilterStore');
            const currentValue = storeSelect.value;

            // Collect retail stores only
            const storeStock = {};
            rtData.forEach(item => {
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([store, stock]) => {
                        if (!isWarehouseLocation(store)) {
                            if (!storeStock[store]) storeStock[store] = 0;
                            storeStock[store] += stock || 0;
                        }
                    });
                }
            });

            let stores = Object.entries(storeStock)
                .map(([name, stock]) => ({ name, stock }))
                .sort((a, b) => a.name.localeCompare(b.name));

            if (selectedArea) {
                stores = stores.filter(s => getAreaFromStore(s.name) === selectedArea);
            }

            storeSelect.innerHTML = '<option value="">Semua Store</option>';
            stores.forEach(s => {
                storeSelect.innerHTML += `<option value="${s.name}">${s.name}</option>`;
            });

            if (stores.some(s => s.name === currentValue)) {
                storeSelect.value = currentValue;
            }
        }

        // Legacy renderTable - redirect to renderRetailTable
        function renderTable() {
            renderRetailTable();
        }

        function goToPage(page) {
            rtGoToPage(page);
        }

        function getStockBadge(stock) {
            const s = Number(stock) || 0;
            if (s < 0) return '<span class="stock-badge stock-negative">Minus</span>';
            if (s === 0) return '<span class="stock-badge stock-zero">Out of Stock</span>';
            if (s < 10) return '<span class="stock-badge stock-low">Low</span>';
            if (s > 100) return '<span class="stock-badge stock-high">High</span>';
            return '<span class="stock-badge stock-medium">Normal</span>';
        }

        function exportData() {
            if (!filteredData.length) { alert('Tidak ada data'); return; }
            const headers = ['Kode Kecil', 'Gender', 'Series', 'Tipe', 'Nama Barang', 'Tier', 'Total Stock'];
            const csv = [headers.join(','), ...filteredData.map(i => [
                i.kode_kecil || '', i.gender || '', i.series || '', i.tipe || '', `"${(i.name || '').replace(/"/g, '""')}"`, i.tier || '', i.total
            ].join(','))].join('\\n');

            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `stock_${currentEntity}_${currentType}_${new Date().toISOString().split('T')[0]}.csv`;
            link.click();
        }

        // ============ MINUS ON HAND DETAIL FUNCTIONS ============
        function showNegativeDetails(dataType) {
            // Get data based on dataType (retail or warehouse)
            let data;
            if (dataType === 'retail') {
                data = rtFilteredData || [];
            } else if (dataType === 'warehouse') {
                data = whFilteredData || [];
            } else {
                data = getData();
            }

            // Kumpulkan data minus per store/warehouse
            const minusByLocation = {};
            let totalMinusItems = 0;
            let totalMinusPairs = 0;

            data.forEach(item => {
                // Check per-store stock minus (prioritas)
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([storeName, stock]) => {
                        if (stock < 0) {
                            if (!minusByLocation[storeName]) {
                                minusByLocation[storeName] = {
                                    area: getAreaFromStore(storeName),
                                    articles: [],
                                    totalPairs: 0
                                };
                            }
                            const exists = minusByLocation[storeName].articles.some(a => a.sku === item.sku);
                            if (!exists) {
                                minusByLocation[storeName].articles.push({
                                    sku: item.sku,
                                    name: item.name || '-',
                                    stock: stock
                                });
                                minusByLocation[storeName].totalPairs += Math.abs(stock);
                                totalMinusItems++;
                                totalMinusPairs += Math.abs(stock);
                            }
                        }
                    });
                }
                // Fallback: jika tidak ada store_stock, gunakan total
                else if (item.total < 0) {
                    const locName = currentType === 'warehouse' ? 'Warehouse ' + currentEntity : 'Stock ' + currentEntity;
                    if (!minusByLocation[locName]) {
                        minusByLocation[locName] = { area: 'Warehouse', articles: [], totalPairs: 0 };
                    }
                    minusByLocation[locName].articles.push({
                        sku: item.sku,
                        name: item.name || '-',
                        stock: item.total
                    });
                    minusByLocation[locName].totalPairs += Math.abs(item.total);
                    totalMinusItems++;
                    totalMinusPairs += Math.abs(item.total);
                }
            });

            const locationCount = Object.keys(minusByLocation).length;

            // Build modal content
            let html = `
                <div class="modal-summary">
                    <div class="modal-stat">
                        <div class="label">Total Artikel</div>
                        <div class="value">${totalMinusItems.toLocaleString('id-ID')}</div>
                    </div>
                    <div class="modal-stat">
                        <div class="label">Total Pairs</div>
                        <div class="value">-${totalMinusPairs.toLocaleString('id-ID')}</div>
                    </div>
                    <div class="modal-stat">
                        <div class="label">Jumlah Lokasi</div>
                        <div class="value">${locationCount}</div>
                    </div>
                </div>
                <p style="color:#6b7280;font-size:0.85rem;margin-bottom:15px;">Klik pada store/warehouse untuk melihat detail artikel</p>
            `;

            if (locationCount === 0) {
                html += '<div style="text-align:center;padding:40px;color:#6b7280;">Tidak ada minus on hand saat ini</div>';
            } else {
                html += '<div class="negative-list">';

                // Sort descending by totalPairs (toko dengan minus terbanyak di atas)
                const sortedLocations = Object.entries(minusByLocation)
                    .sort((a, b) => b[1].totalPairs - a[1].totalPairs);

                sortedLocations.forEach(([location, locData], index) => {
                    const storeIcon = locData.area === 'Warehouse' ? '📦' : '🏪';
                    html += `
                        <div class="negative-item" id="negItem${index}">
                            <div class="negative-item-header" onclick="toggleNegativeItem(${index})">
                                <div class="negative-store">
                                    <span class="negative-store-icon">${storeIcon}</span>
                                    <span>${location}</span>
                                    <span class="negative-store-area">${locData.area}</span>
                                </div>
                                <div class="negative-stats">
                                    <span class="negative-count">${locData.articles.length} artikel</span>
                                    <span class="negative-pairs">-${locData.totalPairs.toLocaleString('id-ID')} pairs</span>
                                    <span class="expand-icon">▼</span>
                                </div>
                            </div>
                            <div class="negative-articles">
                                <table class="articles-table">
                                    <thead>
                                        <tr>
                                            <th>SKU</th>
                                            <th>Nama Barang</th>
                                            <th style="text-align:right;">Minus on Hand</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                    `;

                    // Sort articles by stock (most negative first)
                    locData.articles.sort((a, b) => a.stock - b.stock);

                    locData.articles.forEach(article => {
                        html += `
                            <tr>
                                <td class="sku">${article.sku}</td>
                                <td class="name">${article.name.length > 40 ? article.name.substring(0, 40) + '...' : article.name}</td>
                                <td class="stock">${article.stock} pairs</td>
                            </tr>
                        `;
                    });

                    html += '</tbody></table></div></div>';
                });

                html += '</div>';
            }

            document.getElementById('negativeModalBody').innerHTML = html;
            document.getElementById('negativeModal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function toggleNegativeItem(index) {
            const item = document.getElementById('negItem' + index);
            if (item) {
                item.classList.toggle('expanded');
            }
        }

        function closeNegativeModal(event) {
            if (event && event.target !== event.currentTarget) return;
            document.getElementById('negativeModal').classList.remove('active');
            document.body.style.overflow = 'auto';
        }

        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeNegativeModal();
        });

        // ============ VIEW TOGGLE FUNCTIONS ============
        function switchView(view) {
            console.log('switchView:', view);
            currentView = view;

            var viewBtns = document.querySelectorAll('.view-btn');
            for (var i = 0; i < viewBtns.length; i++) {
                var btn = viewBtns[i];
                if (btn.dataset.view === view) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            }

            var containers = document.querySelectorAll('.view-container');
            for (var j = 0; j < containers.length; j++) {
                var container = containers[j];
                if (container.id === view + 'View') {
                    container.classList.add('active');
                } else {
                    container.classList.remove('active');
                }
            }

            if (view === 'maxstock') {
                setTimeout(function() {
                    try {
                        updateMaxStockAnalysis();
                    } catch(e) {
                        console.error('Error updateMaxStockAnalysis:', e);
                        alert('Error: ' + e.message);
                    }
                }, 100);
            } else if (view === 'stockcontrol') {
                setTimeout(function() {
                    try {
                        initStockControl();
                    } catch(e) {
                        console.error('Error initStockControl:', e);
                        alert('Error: ' + e.message);
                    }
                }, 100);
            }
        }

        function switchMaxStockTab(type) {
            console.log('switchMaxStockTab:', type);
            currentMSType = type;

            var tabs = document.querySelectorAll('#maxstockView .tab');
            for (var i = 0; i < tabs.length; i++) {
                var tab = tabs[i];
                if (tab.dataset.mstype === type) {
                    tab.classList.add('active');
                } else {
                    tab.classList.remove('active');
                }
            }

            // Show/hide filters based on tab
            var msFilters = document.getElementById('msFilters');
            var msWHFilters = document.getElementById('msWHFilters');
            if (type === 'retail') {
                msFilters.style.display = 'flex';
                msWHFilters.style.display = 'none';
                populateMSFilters();
            } else {
                msFilters.style.display = 'none';
                msWHFilters.style.display = 'flex';
            }

            try {
                updateMaxStockAnalysis();
            } catch(e) {
                console.error('Error updateMaxStockAnalysis:', e);
            }
        }

        // Store data cache for filter
        var msStoresByArea = {};

        function populateMSFilters() {
            var entityData = allData[currentEntity];
            if (!entityData || !entityData.retail) return;

            var areas = {};
            msStoresByArea = {}; // Reset cache
            var retailData = entityData.retail;

            for (var i = 0; i < retailData.length; i++) {
                var item = retailData[i];
                if (item.store_stock) {
                    var storeNames = Object.keys(item.store_stock);
                    for (var j = 0; j < storeNames.length; j++) {
                        var store = storeNames[j];
                        if (!store) continue;
                        var storeLower = store.toLowerCase();
                        if (storeLower.indexOf('warehouse') >= 0) continue;

                        var area = getAreaFromStore(store);
                        if (area) {
                            areas[area] = true;
                            if (!msStoresByArea[area]) msStoresByArea[area] = {};
                            msStoresByArea[area][store] = true;
                        }
                    }
                }
            }

            // Populate area dropdown
            var areaSelect = document.getElementById('msFilterArea');
            var currentArea = areaSelect.value;
            areaSelect.innerHTML = '<option value="">Semua Area</option>';
            var areaNames = Object.keys(areas).sort();
            for (var k = 0; k < areaNames.length; k++) {
                var opt = document.createElement('option');
                opt.value = areaNames[k];
                opt.textContent = areaNames[k];
                areaSelect.appendChild(opt);
            }
            areaSelect.value = currentArea;

            // Populate store dropdown based on selected area
            updateStoreDropdown();
        }

        function updateStoreDropdown() {
            var selectedArea = document.getElementById('msFilterArea').value;
            var storeSelect = document.getElementById('msFilterStore');
            var currentStore = storeSelect.value;
            storeSelect.innerHTML = '<option value="">Semua Store</option>';

            // Get stores - filtered by area if selected
            var storesToShow = {};
            if (selectedArea && msStoresByArea[selectedArea]) {
                storesToShow = msStoresByArea[selectedArea];
            } else {
                // Show all stores from all areas
                var allAreas = Object.keys(msStoresByArea);
                for (var i = 0; i < allAreas.length; i++) {
                    var areaStores = msStoresByArea[allAreas[i]];
                    var storeKeys = Object.keys(areaStores);
                    for (var j = 0; j < storeKeys.length; j++) {
                        storesToShow[storeKeys[j]] = true;
                    }
                }
            }

            var storeNamesList = Object.keys(storesToShow).sort();
            for (var m = 0; m < storeNamesList.length; m++) {
                var opt2 = document.createElement('option');
                opt2.value = storeNamesList[m];
                opt2.textContent = storeNamesList[m];
                storeSelect.appendChild(opt2);
            }
            storeSelect.value = currentStore;
        }

        function resetMSFilters() {
            document.getElementById('msFilterArea').value = '';
            document.getElementById('msFilterStore').value = '';
            document.getElementById('msFilterFillRate').value = '';
            updateMaxStockAnalysis();
        }

        function resetWHFilters() {
            document.getElementById('msWHFilterArea').value = '';
            document.getElementById('msWHFilterFillRate').value = '';
            updateMaxStockAnalysis();
        }

        // ============ MAX STOCK ANALYSIS FUNCTIONS ============
        function getMaxStockForStore(storeName) {
            if (!storeName) return 0;
            var s = storeName.toLowerCase().trim();

            // Direct match
            if (maxStockMap[s]) return maxStockMap[s].max_stock;

            // Try tanpa "zuma " prefix
            var sNoZuma = s.replace(/^zuma\s+/i, '');
            if (maxStockMap[sNoZuma]) return maxStockMap[sNoZuma].max_stock;

            // Partial match
            var keys = Object.keys(maxStockMap);
            for (var i = 0; i < keys.length; i++) {
                var key = keys[i];
                if (s.indexOf(key) >= 0 || key.indexOf(s) >= 0) {
                    return maxStockMap[key].max_stock;
                }
            }

            return 0;
        }

        function updateMaxStockAnalysis() {
            console.log('updateMaxStockAnalysis START');
            var isWarehouse = (currentMSType === 'warehouse');

            var locationData = {};
            var tierCounts = {};
            var totalActual = 0;
            var totalMax = 0;
            filteredTierArticles = {};  // Reset articles

            if (isWarehouse) {
                // WAREHOUSE: Track per individual warehouse AND per area
                var whStock = {};      // {whName: stock}
                var whTiers = {};      // {whName: {tier: stock}}
                var whArticles = {};   // {whName: {tier: [articles]}}
                var whEntityStock = {};  // {whName: {entity: stock}} - NEW: track per entity
                var areaStock = { 'Bali': 0, 'Jakarta': 0, 'Jawa Timur': 0 };
                var areaTiers = { 'Bali': {}, 'Jakarta': {}, 'Jawa Timur': {} };
                var areaEntityStock = { 'Bali': {}, 'Jakarta': {}, 'Jawa Timur': {} };  // NEW: track per entity per area
                var maxStockArea = { 'Bali': 72000, 'Jakarta': 48000, 'Jawa Timur': 120000 };
                var warehousesByArea = { 'Bali': [], 'Jakarta': [], 'Jawa Timur': [] };

                // Get filter values
                var filterArea = document.getElementById('msWHFilterArea').value;
                var filterFillRate = document.getElementById('msWHFilterFillRate').value;

                // Helper function to get area from warehouse name
                function getWarehouseArea(whName) {
                    if (!whName) return 'Jawa Timur';
                    var whLower = whName.toLowerCase();
                    if (storeAreaMap[whLower]) return storeAreaMap[whLower];
                    if (whLower.indexOf('bali') >= 0 || whLower.indexOf('gatsu') >= 0) return 'Bali';
                    if (whLower.indexOf('jakarta') >= 0 || whLower.indexOf('pluit') >= 0) return 'Jakarta';
                    if (whLower.indexOf('pusat') >= 0) return 'Jawa Timur';
                    return 'Jawa Timur';
                }

                var entities = ['DDD', 'LJBB', 'MBB', 'UBB'];
                for (var i = 0; i < entities.length; i++) {
                    var entity = entities[i];
                    var entityData = allData[entity];
                    if (!entityData || !entityData.warehouse) continue;

                    var whData = entityData.warehouse;

                    for (var j = 0; j < whData.length; j++) {
                        var item = whData[j];
                        var tier = item.tier || '';

                        // Skip item tanpa tier valid (hanya tier 1,2,3,4,5,8)
                        if (!tier || tier === '-' || !['1','2','3','4','5','8'].includes(tier.toString())) continue;

                        if (item.store_stock) {
                            var whNames = Object.keys(item.store_stock);
                            for (var w = 0; w < whNames.length; w++) {
                                var whName = whNames[w];
                                var stock = item.store_stock[whName];

                                var area = getWarehouseArea(whName);

                                // Skip if area filter active and doesn't match
                                if (filterArea && area !== filterArea) continue;

                                // Track per warehouse (include all values, positive and negative)
                                if (!whStock[whName]) {
                                    whStock[whName] = 0;
                                    whTiers[whName] = {};
                                    whArticles[whName] = {};
                                    whEntityStock[whName] = {};
                                }
                                whStock[whName] = whStock[whName] + stock;

                                // Track per entity per warehouse
                                if (!whEntityStock[whName][entity]) whEntityStock[whName][entity] = 0;
                                whEntityStock[whName][entity] = whEntityStock[whName][entity] + stock;

                                if (!whTiers[whName][tier]) whTiers[whName][tier] = 0;
                                whTiers[whName][tier] = whTiers[whName][tier] + stock;

                                // Track per area
                                areaStock[area] = areaStock[area] + stock;
                                if (!areaTiers[area][tier]) areaTiers[area][tier] = 0;
                                areaTiers[area][tier] = areaTiers[area][tier] + stock;

                                // Track per entity per area
                                if (!areaEntityStock[area][entity]) areaEntityStock[area][entity] = 0;
                                areaEntityStock[area][entity] = areaEntityStock[area][entity] + stock;

                                // Track articles (include negatif agar bisa di-investigate)
                                if (stock !== 0) {
                                    if (!whArticles[whName][tier]) whArticles[whName][tier] = [];
                                    whArticles[whName][tier].push({
                                        sku: item.sku,
                                        nama: item.name || item.nama || item.sku,
                                        size: item.size || '-',
                                        stock: stock,
                                        store: whName
                                    });
                                }
                            }
                        }
                    }
                }

                // Build locationData per individual warehouse grouped by area
                var whNamesList = Object.keys(whStock).sort();
                for (var k = 0; k < whNamesList.length; k++) {
                    var whName = whNamesList[k];
                    var actual = whStock[whName] || 0;

                    // SELALU kumpulkan tier counts dan articles (sebelum skip actual=0)
                    // Ini memastikan tier bisa diklik meski warehouse total 0
                    var whTierData = whTiers[whName];
                    var whArticleData = whArticles[whName];
                    if (whTierData) {
                        var tierKeys = Object.keys(whTierData);
                        for (var t = 0; t < tierKeys.length; t++) {
                            var tierKey = tierKeys[t];
                            if (!tierCounts[tierKey]) tierCounts[tierKey] = 0;
                            tierCounts[tierKey] = tierCounts[tierKey] + whTierData[tierKey];

                            if (whArticleData && whArticleData[tierKey]) {
                                if (!filteredTierArticles[tierKey]) filteredTierArticles[tierKey] = [];
                                filteredTierArticles[tierKey] = filteredTierArticles[tierKey].concat(whArticleData[tierKey]);
                            }
                        }
                    }

                    // Skip warehouse dengan total 0 dari locationData (tapi articles sudah dikumpulkan)
                    if (actual === 0) continue;

                    var area = getWarehouseArea(whName);

                    locationData[whName] = {
                        name: whName,
                        area: area,
                        actual: actual,
                        max: 0,  // Individual WH doesn't have max
                        fillRate: 0,
                        tiers: whTiers[whName],
                        entityStock: whEntityStock[whName] || {},  // NEW: per entity breakdown
                        isIndividual: true
                    };

                    // Track warehouses per area
                    if (warehousesByArea[area].indexOf(whName) < 0) {
                        warehousesByArea[area].push(whName);
                    }
                }

                // Add area totals
                var areaOrder = ['Bali', 'Jakarta', 'Jawa Timur'];
                for (var a = 0; a < areaOrder.length; a++) {
                    var areaName = areaOrder[a];
                    if (filterArea && areaName !== filterArea) continue;

                    var areaActual = areaStock[areaName] || 0;
                    var areaMax = maxStockArea[areaName] || 0;
                    var areaFillRate = areaMax > 0 ? (areaActual / areaMax * 100) : 0;

                    if (areaActual !== 0) {
                        locationData['__TOTAL_' + areaName] = {
                            name: 'TOTAL ' + areaName,
                            area: areaName,
                            actual: areaActual,
                            max: areaMax,
                            fillRate: areaFillRate,
                            tiers: areaTiers[areaName],
                            entityStock: areaEntityStock[areaName] || {},  // NEW: per entity breakdown
                            isAreaTotal: true,
                            warehouses: warehousesByArea[areaName]
                        };

                        totalActual = totalActual + areaActual;
                    }
                }

                // Calculate total max based on selected area filter
                if (filterArea) {
                    totalMax = maxStockArea[filterArea] || 0;
                } else {
                    totalMax = maxStockArea['Bali'] + maxStockArea['Jakarta'] + maxStockArea['Jawa Timur'];
                }

            } else {
                // RETAIL: Per store untuk entity yang dipilih
                var entityData = allData[currentEntity];
                if (!entityData || !entityData.retail || entityData.retail.length === 0) {
                    document.getElementById('msTotalMax').textContent = '0';
                    document.getElementById('msTotalActual').textContent = '0';
                    document.getElementById('msFillRate').textContent = '0%';
                    document.getElementById('msRemaining').textContent = '0';
                    document.getElementById('storeAnalysisList').innerHTML = '<div style="padding:40px;text-align:center;color:#9ca3af;">Tidak ada data retail untuk ' + currentEntity + '</div>';
                    document.getElementById('tierBreakdown').innerHTML = '';
                    return;
                }

                var retailData = entityData.retail;
                var storeStock = {};
                var storeTiers = {};
                var storeArticles = {};  // {store: {tier: [{sku, nama, stock}]}}

                // Get filter values first
                var filterArea = document.getElementById('msFilterArea').value;
                var filterStore = document.getElementById('msFilterStore').value;
                var filterFillRate = document.getElementById('msFilterFillRate').value;

                for (var m = 0; m < retailData.length; m++) {
                    var item = retailData[m];
                    var tier = item.tier || '';

                    // Skip item tanpa tier valid (hanya tier 1,2,3,4,5,8)
                    if (!tier || tier === '-' || !['1','2','3','4','5','8'].includes(tier.toString())) continue;

                    if (item.store_stock) {
                        var storeNames = Object.keys(item.store_stock);
                        for (var n = 0; n < storeNames.length; n++) {
                            var store = storeNames[n];
                            if (!store) continue;
                            var storeLower = store.toLowerCase();
                            if (storeLower.indexOf('warehouse') >= 0) continue;

                            var stock = item.store_stock[store];
                            var positiveStock = (stock > 0) ? stock : 0;

                            if (!storeStock[store]) {
                                storeStock[store] = 0;
                                storeTiers[store] = {};
                                storeArticles[store] = {};
                            }
                            storeStock[store] = storeStock[store] + positiveStock;

                            if (!storeTiers[store][tier]) {
                                storeTiers[store][tier] = 0;
                                storeArticles[store][tier] = [];
                            }
                            storeTiers[store][tier] = storeTiers[store][tier] + stock;  // Include semua untuk tier count

                            // Track article detail (include negatif agar bisa di-investigate)
                            if (stock !== 0) {
                                storeArticles[store][tier].push({
                                    sku: item.sku,
                                    nama: item.name || item.nama || item.sku,
                                    size: item.size || '-',
                                    stock: stock,
                                    store: store
                                });
                            }
                        }
                    }
                }

                // Build locationData with filters AND calculate tierCounts from filtered data
                var allStoreNames = Object.keys(storeStock);
                for (var p = 0; p < allStoreNames.length; p++) {
                    var storeName = allStoreNames[p];
                    var actual = storeStock[storeName];
                    var max = getMaxStockForStore(storeName);
                    var fillRate = (max > 0) ? (actual / max * 100) : 0;
                    var area = getAreaFromStore(storeName);

                    // Apply filters
                    if (filterArea && area !== filterArea) continue;
                    if (filterStore && storeName !== filterStore) continue;
                    if (filterFillRate) {
                        if (filterFillRate === 'over' && fillRate <= 100) continue;
                        if (filterFillRate === 'high' && (fillRate <= 80 || fillRate > 100)) continue;
                        if (filterFillRate === 'medium' && (fillRate <= 50 || fillRate > 80)) continue;
                        if (filterFillRate === 'low' && fillRate >= 50) continue;
                    }

                    locationData[storeName] = {
                        name: storeName,
                        area: area,
                        actual: actual,
                        max: max,
                        fillRate: fillRate,
                        tiers: storeTiers[storeName]
                    };

                    // Add tier counts and articles from filtered stores only
                    var storeTierData = storeTiers[storeName];
                    var storeArticleData = storeArticles[storeName];
                    if (storeTierData) {
                        var tierKeys = Object.keys(storeTierData);
                        for (var t = 0; t < tierKeys.length; t++) {
                            var tierKey = tierKeys[t];
                            if (!tierCounts[tierKey]) tierCounts[tierKey] = 0;
                            tierCounts[tierKey] = tierCounts[tierKey] + storeTierData[tierKey];

                            // Collect articles for this tier
                            if (storeArticleData && storeArticleData[tierKey]) {
                                if (!filteredTierArticles[tierKey]) filteredTierArticles[tierKey] = [];
                                filteredTierArticles[tierKey] = filteredTierArticles[tierKey].concat(storeArticleData[tierKey]);
                            }
                        }
                    }

                    totalActual = totalActual + actual;
                    totalMax = totalMax + max;
                }
            }

            var overallFillRate = (totalMax > 0) ? (totalActual / totalMax * 100) : 0;
            var remaining = totalMax - totalActual;

            // Update summary
            document.getElementById('msTotalMax').textContent = totalMax.toLocaleString('id-ID') + ' pairs';
            document.getElementById('msTotalActual').textContent = totalActual.toLocaleString('id-ID') + ' pairs';
            document.getElementById('msFillRate').textContent = overallFillRate.toFixed(1) + '%';
            document.getElementById('msRemaining').textContent = remaining.toLocaleString('id-ID') + ' pairs';

            // Update charts and lists
            updateFillRateChart(locationData);
            updateTierDistChart(tierCounts);
            renderStoreAnalysisList(locationData);
            renderTierBreakdown(tierCounts, filteredTierArticles);

            console.log('updateMaxStockAnalysis DONE - Actual:', totalActual, 'Max:', totalMax);
        }

        function showNoDataMessage(type) {
            const typeLabel = type === 'warehouse' ? 'Warehouse' : 'Retail Store';
            const message = `<div style="padding:40px;text-align:center;color:#9ca3af;">
                <div style="font-size:48px;margin-bottom:15px;">📭</div>
                <div style="font-size:16px;font-weight:600;color:#6b7280;">Tidak ada data ${typeLabel}</div>
                <div style="font-size:14px;margin-top:8px;">Entity ${currentEntity} tidak memiliki data ${typeLabel}</div>
            </div>`;

            document.getElementById('msTotalMax').textContent = '0';
            document.getElementById('msTotalActual').textContent = '0';
            document.getElementById('msFillRate').textContent = '0%';
            document.getElementById('msRemaining').textContent = '0';
            document.getElementById('storeAnalysisList').innerHTML = message;
            document.getElementById('tierBreakdown').innerHTML = message;

            // Clear charts
            if (fillRateChart) fillRateChart.destroy();
            if (tierDistChart) tierDistChart.destroy();
        }

        function updateFillRateChart(locationData) {
            try {
                const sorted = Object.entries(locationData)
                    .sort((a, b) => b[1].fillRate - a[1].fillRate)
                    .slice(0, 10);

                if (sorted.length === 0) {
                    console.log('No data for fill rate chart');
                    if (fillRateChart) fillRateChart.destroy();
                    return;
                }

                const labels = sorted.map(([k, v]) => v.name.length > 20 ? v.name.substring(0, 20) + '...' : v.name);
                const fillRates = sorted.map(([k, v]) => v.fillRate);
                const colors = fillRates.map(rate => {
                    if (rate > 100) return '#dc2626';  // Red - overflow (BAD)
                    if (rate > 80) return '#10b981';   // Green - good fill rate
                    if (rate > 50) return '#f59e0b';   // Orange - medium
                    return '#3b82f6';                  // Blue - low
                });

                const maxVal = fillRates.length > 0 ? Math.max(100, ...fillRates) + 10 : 110;

                if (fillRateChart) fillRateChart.destroy();
                fillRateChart = new Chart(document.getElementById('fillRateChart'), {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Fill Rate %',
                            data: fillRates,
                            backgroundColor: colors,
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'y',
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { beginAtZero: true, max: maxVal }
                        }
                    }
                });
                console.log('Fill rate chart created with', labels.length, 'entries');
            } catch(e) {
                console.error('Error in updateFillRateChart:', e);
            }
        }

        function updateTierDistChart(tierCounts) {
            try {
                // Filter out T0 and tiers with 0 stock
                const filteredTiers = Object.entries(tierCounts)
                    .filter(([tier, count]) => count > 0 && tier !== '0')
                    .sort((a, b) => a[0].localeCompare(b[0]));
                const tiers = filteredTiers.map(([t, c]) => t);
                const values = filteredTiers.map(([t, c]) => c);
                const colors = ['#6366f1', '#ec4899', '#10b981', '#f59e0b', '#06b6d4', '#8b5cf6', '#ef4444', '#84cc16'];

                if (tiers.length === 0) {
                    console.log('No data for tier chart');
                    if (tierDistChart) tierDistChart.destroy();
                    return;
                }

                if (tierDistChart) tierDistChart.destroy();
                tierDistChart = new Chart(document.getElementById('tierDistChart'), {
                    type: 'bar',
                    data: {
                        labels: tiers.map(t => 'Tier ' + t),
                        datasets: [{
                            label: 'Stock',
                            data: values,
                            backgroundColor: colors,
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        indexAxis: 'x',
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    font: { family: 'Poppins', size: 10 },
                                    callback: function(value) {
                                        return value.toLocaleString('id-ID');
                                    }
                                }
                            },
                            x: {
                                ticks: { font: { family: 'Poppins', size: 11 } }
                            }
                        }
                    }
                });
                console.log('Tier chart created with', tiers.length, 'tiers');
            } catch(e) {
                console.error('Error in updateTierDistChart:', e);
            }
        }

        function renderStoreAnalysisList(locationData) {
            // Check if this is warehouse data (has isIndividual or isAreaTotal flags)
            const isWarehouseData = Object.values(locationData).some(loc => loc.isIndividual || loc.isAreaTotal);

            if (isWarehouseData) {
                // Warehouse: Group by area with totals
                const areaOrder = ['Bali', 'Jakarta', 'Jawa Timur'];
                let html = '';

                areaOrder.forEach(areaName => {
                    // Get warehouses for this area
                    const areaWarehouses = Object.entries(locationData)
                        .filter(([key, loc]) => loc.area === areaName && loc.isIndividual)
                        .sort((a, b) => b[1].actual - a[1].actual);

                    // Get area total
                    const areaTotal = locationData['__TOTAL_' + areaName];

                    if (areaWarehouses.length === 0 && !areaTotal) return;

                    // Area header
                    html += `<div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);color:white;padding:12px 15px;margin-top:15px;border-radius:10px 10px 0 0;font-weight:600;">
                        📦 ${areaName}
                    </div>`;

                    // Individual warehouses
                    areaWarehouses.forEach(([key, loc]) => {
                        // Build entity breakdown HTML
                        let entityHtml = '';
                        if (loc.entityStock && Object.keys(loc.entityStock).length > 0) {
                            const entities = ['DDD', 'LJBB', 'MBB', 'UBB'];
                            let entityParts = [];
                            entities.forEach(ent => {
                                if (loc.entityStock[ent] && loc.entityStock[ent] !== 0) {
                                    const val = loc.entityStock[ent];
                                    const color = val < 0 ? '#ef4444' : '#10b981';
                                    entityParts.push(`<span style="color:${color};font-size:0.75rem;">${ent}:${val.toLocaleString('id-ID')}</span>`);
                                }
                            });
                            if (entityParts.length > 0) {
                                entityHtml = `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:2px;">${entityParts.join('')}</div>`;
                            }
                        }

                        html += `
                            <div class="store-analysis-item" style="border-left:3px solid #e5e7eb;margin-left:10px;background:#fafafa;">
                                <div class="store-info" style="flex:2;">
                                    <div class="name" style="font-size:0.9rem;">${loc.name}</div>
                                    ${entityHtml}
                                </div>
                                <div class="stock-comparison">
                                    <div class="actual" style="font-weight:600;">${loc.actual.toLocaleString('id-ID')} prs</div>
                                </div>
                                <div style="width:100px;"></div>
                                <div style="width:60px;"></div>
                            </div>
                        `;
                    });

                    // Area total
                    if (areaTotal) {
                        const fillClass = areaTotal.fillRate > 100 ? 'over' : (areaTotal.fillRate > 80 ? 'high' : (areaTotal.fillRate > 50 ? 'medium' : 'low'));
                        const fillWidth = Math.min(100, Math.abs(areaTotal.fillRate));

                        // Build entity breakdown for area total
                        let areaTotalEntityHtml = '';
                        if (areaTotal.entityStock && Object.keys(areaTotal.entityStock).length > 0) {
                            const entities = ['DDD', 'LJBB', 'MBB', 'UBB'];
                            let entityParts = [];
                            entities.forEach(ent => {
                                if (areaTotal.entityStock[ent] && areaTotal.entityStock[ent] !== 0) {
                                    const val = areaTotal.entityStock[ent];
                                    const color = val < 0 ? '#ef4444' : '#059669';
                                    entityParts.push(`<span style="background:${val < 0 ? '#fee2e2' : '#d1fae5'};color:${color};padding:2px 6px;border-radius:4px;font-size:0.7rem;font-weight:600;">${ent}: ${val.toLocaleString('id-ID')}</span>`);
                                }
                            });
                            if (entityParts.length > 0) {
                                areaTotalEntityHtml = `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px;">${entityParts.join('')}</div>`;
                            }
                        }

                        html += `
                            <div class="store-analysis-item" style="background:linear-gradient(135deg,#f0f9ff,#e0f2fe);border:2px solid #6366f1;border-radius:0 0 10px 10px;">
                                <div class="store-info" style="flex:2;">
                                    <div class="name" style="font-weight:700;color:#6366f1;">📊 ${areaTotal.name}</div>
                                    <div class="area" style="font-size:0.75rem;color:#64748b;">${areaWarehouses.length} warehouse</div>
                                    ${areaTotalEntityHtml}
                                </div>
                                <div class="stock-comparison">
                                    <div class="actual" style="font-weight:700;color:#1f2937;">${areaTotal.actual.toLocaleString('id-ID')} prs</div>
                                    <div class="max">Max: ${areaTotal.max.toLocaleString('id-ID')}</div>
                                </div>
                                <div class="fill-indicator">
                                    <div class="fill-bar ${fillClass}" style="width: ${fillWidth}%"></div>
                                </div>
                                <div class="fill-percent ${fillClass}" style="font-weight:700;">${areaTotal.fillRate.toFixed(1)}%</div>
                            </div>
                        `;
                    }
                });

                document.getElementById('storeAnalysisList').innerHTML = html || '<div style="padding:20px;color:#9ca3af;text-align:center;">Tidak ada data</div>';
            } else {
                // Retail: Original sorting by fill rate
                const sorted = Object.entries(locationData)
                    .sort((a, b) => b[1].fillRate - a[1].fillRate);

                let html = '';
                sorted.forEach(([key, loc]) => {
                    const fillClass = loc.fillRate > 100 ? 'over' : (loc.fillRate > 80 ? 'high' : (loc.fillRate > 50 ? 'medium' : 'low'));
                    const fillWidth = Math.min(100, loc.fillRate);

                    // Tier breakdown untuk lokasi ini
                    let tierHtml = '';
                    if (loc.tiers && Object.keys(loc.tiers).length > 0) {
                        const tiersSorted = Object.entries(loc.tiers)
                            .filter(([tier, count]) => count > 0 && tier !== '0')
                            .sort((a, b) => a[0].localeCompare(b[0]));
                        const totalTier = Object.values(loc.tiers).reduce((a, b) => a + b, 0);
                        if (tiersSorted.length > 0) {
                            tierHtml = '<div class="tier-breakdown-mini">';
                            tiersSorted.forEach(([tier, count]) => {
                                const pct = totalTier > 0 ? (count / totalTier * 100) : 0;
                                tierHtml += `<span class="tier-tag">T${tier}: ${pct.toFixed(0)}%</span>`;
                            });
                            tierHtml += '</div>';
                        }
                    }

                    html += `
                        <div class="store-analysis-item">
                            <div class="store-info">
                                <div class="name">${loc.name}</div>
                                <div class="area">${loc.area}</div>
                                ${tierHtml}
                            </div>
                            <div class="stock-comparison">
                                <div class="actual">${loc.actual.toLocaleString('id-ID')} prs</div>
                                <div class="max">Max: ${loc.max > 0 ? loc.max.toLocaleString('id-ID') : '-'}</div>
                            </div>
                            <div class="fill-indicator">
                                <div class="fill-bar ${fillClass}" style="width: ${fillWidth}%"></div>
                            </div>
                            <div class="fill-percent ${fillClass}">${loc.fillRate.toFixed(1)}%</div>
                        </div>
                    `;
                });

                document.getElementById('storeAnalysisList').innerHTML = html || '<div style="padding:20px;color:#9ca3af;text-align:center;">Tidak ada data</div>';
            }
        }

        function renderTierBreakdown(tierCounts, tierArticles) {
            const total = Object.values(tierCounts).reduce((a, b) => a + b, 0);
            const tiers = Object.keys(tierCounts).sort();

            let html = '<div class="tier-distribution">';
            tiers.forEach(tier => {
                const count = tierCounts[tier];
                // Skip tiers with stock = 0 only, tampilkan negatif agar bisa di-investigate
                if (count === 0) return;
                const percent = total > 0 ? (count / total * 100) : 0;
                const hasArticles = tierArticles && tierArticles[tier] && tierArticles[tier].length > 0;
                html += `
                    <div class="tier-item ${hasArticles ? 'clickable' : ''}" ${hasArticles ? 'onclick="showTierArticles(\\'' + tier + '\\')"' : ''} style="${hasArticles ? 'cursor:pointer;' : ''}">
                        <div class="tier-label">TIER ${tier}</div>
                        <div class="tier-value">${count.toLocaleString('id-ID')}</div>
                        <div class="tier-percent">${percent.toFixed(1)}%</div>
                        ${hasArticles ? '<div style="font-size:0.65rem;color:#6366f1;margin-top:4px;">Klik untuk detail</div>' : ''}
                    </div>
                `;
            });
            html += '</div>';

            // Add total
            html += `
                <div style="margin-top:20px;padding:15px;background:#f8fafc;border-radius:10px;text-align:center;">
                    <div style="font-size:0.75rem;color:#9ca3af;font-weight:600;">TOTAL STOCK</div>
                    <div style="font-size:1.5rem;font-weight:700;color:#1f2937;">${total.toLocaleString('id-ID')} pairs</div>
                </div>
            `;

            document.getElementById('tierBreakdown').innerHTML = html;
        }

        function showTierArticles(tier) {
            const articles = filteredTierArticles[tier] || [];
            if (articles.length === 0) {
                alert('Tidak ada artikel untuk Tier ' + tier);
                return;
            }

            // Sort by store, then by nama, then by size
            const sorted = [...articles].sort((a, b) => {
                if (a.store !== b.store) return a.store.localeCompare(b.store);
                if (a.nama !== b.nama) return a.nama.localeCompare(b.nama);
                return (a.size || '').localeCompare(b.size || '');
            });

            const totalStock = articles.reduce((a,b) => a + b.stock, 0);
            const uniqueStores = [...new Set(articles.map(a => a.store))].length;

            let html = `
                <div style="margin-bottom:15px;padding:10px;background:#f0f9ff;border-radius:8px;">
                    <strong>Tier ${tier}</strong> - ${sorted.length} items di ${uniqueStores} store, Total: ${totalStock.toLocaleString('id-ID')} pairs
                </div>
                <div style="max-height:400px;overflow-y:auto;">
                    <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                        <thead>
                            <tr style="background:#f8fafc;position:sticky;top:0;">
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;">Store</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;">SKU</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;">Nama Artikel</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;">Size</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">Qty</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            sorted.forEach((item, idx) => {
                html += `
                    <tr style="background:${idx % 2 === 0 ? '#fff' : '#f9fafb'};">
                        <td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;font-weight:500;">${item.store}</td>
                        <td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;font-family:monospace;font-size:0.8rem;">${item.sku}</td>
                        <td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;">${item.nama}</td>
                        <td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:center;">${item.size}</td>
                        <td style="padding:8px 10px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:600;">${item.stock.toLocaleString('id-ID')}</td>
                    </tr>
                `;
            });

            html += '</tbody></table></div>';

            document.getElementById('tierModalTitle').textContent = '📦 Detail Artikel Tier ' + tier;
            document.getElementById('tierModalBody').innerHTML = html;
            document.getElementById('tierModal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeTierModal(event) {
            if (event && event.target !== event.currentTarget) return;
            document.getElementById('tierModal').classList.remove('active');
            document.body.style.overflow = 'auto';
        }

        // Helper function to get assortment count for a size
        function getAssortmentForSize(sku, assortmentStr) {
            if (!assortmentStr || assortmentStr === '-') return '-';

            // Extract size suffix from SKU (e.g., Z22 from Z2LS01Z22)
            const sizeMatch = sku.match(/Z(\d+)$/i);
            if (!sizeMatch) return '-';

            const sizeNum = parseInt(sizeMatch[1]);
            const parts = assortmentStr.split('-').map(p => parseInt(p));

            if (parts.length === 3) {
                // 3-part assortment: Z21/Z22=first, Z23/Z24=second, Z25/Z26=third
                if (sizeNum <= 22) return parts[0] || '-';
                if (sizeNum <= 24) return parts[1] || '-';
                return parts[2] || '-';
            } else if (parts.length === 5) {
                // 5-part assortment: Z21=first, Z22=second, Z23=third, Z24=fourth, Z25=fifth
                const idx = sizeNum - 21;
                return (idx >= 0 && idx < parts.length) ? parts[idx] : '-';
            } else if (parts.length === 4) {
                // 4-part assortment: Z21=first, Z22=second, Z23=third, Z24=fourth
                const idx = sizeNum - 21;
                return (idx >= 0 && idx < parts.length) ? parts[idx] : '-';
            }
            return '-';
        }

        // SKU Detail Modal Functions
        function showSkuDetail(kodeKecil, dataType) {
            var entityData = allData[currentEntity] || {};
            var data = dataType === 'warehouse' ? (entityData.warehouse || []) : (entityData.retail || []);

            // Get location filter based on type
            let locationFilter = '';
            let locationLabel = '';
            if (dataType === 'warehouse') {
                locationFilter = document.getElementById('whFilterWarehouse').value;
                locationLabel = 'Warehouse';
            } else {
                locationFilter = document.getElementById('tableFilterStore').value;
                locationLabel = 'Store';
            }

            // Find all unique SKUs with this kode_kecil
            const skuMap = {};
            data.forEach(item => {
                if ((item.kode_kecil || '').toUpperCase() === kodeKecil.toUpperCase()) {
                    const sku = item.sku;
                    if (!skuMap[sku]) {
                        let qty = item.total;
                        if (locationFilter && item.store_stock && item.store_stock[locationFilter] !== undefined) {
                            qty = item.store_stock[locationFilter];
                        }
                        skuMap[sku] = {
                            sku: sku,
                            name: item.name || '-',
                            qty: qty
                        };
                    }
                }
            });

            // Convert to array and sort by SKU (alphabetically)
            const skuItems = Object.values(skuMap).sort((a, b) => a.sku.localeCompare(b.sku));

            if (!skuItems.length) {
                alert('Data tidak ditemukan');
                return;
            }

            // Get assortment from assortmentMap
            const assortment = assortmentMap[kodeKecil.toUpperCase()] || '-';

            // Build modal content
            let html = `<div style="margin-bottom: 15px; padding: 10px; background: #f0f9ff; border-radius: 8px;">
                <strong>Kode Kecil:</strong> ${kodeKecil} |
                <strong>Assortment:</strong> ${assortment} |
                <strong>Total SKU:</strong> ${skuItems.length}
                ${locationFilter ? ' | <strong>' + locationLabel + ':</strong> ' + locationFilter : ''}
            </div>`;

            html += `<div style="max-height: 400px; overflow-y: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                    <thead style="position: sticky; top: 0; background: #1e3a5f; color: white;">
                        <tr>
                            <th style="padding: 10px; text-align: left;">SKU</th>
                            <th style="padding: 10px; text-align: left;">Nama Barang</th>
                            <th style="padding: 10px; text-align: center;">Asst</th>
                            <th style="padding: 10px; text-align: right;">Qty</th>
                        </tr>
                    </thead>
                    <tbody>`;

            let totalQty = 0;
            skuItems.forEach((item, idx) => {
                totalQty += item.qty;
                const bgColor = idx % 2 === 0 ? '#ffffff' : '#f8fafc';
                const qtyColor = item.qty < 0 ? 'color: #dc2626;' : '';
                const asstCount = getAssortmentForSize(item.sku, assortment);
                html += `<tr style="background: ${bgColor}; border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 8px 10px; font-weight: 500;">${item.sku}</td>
                    <td style="padding: 8px 10px;">${item.name}</td>
                    <td style="padding: 8px 10px; text-align: center; font-weight: 600; color: #6366f1;">${asstCount}</td>
                    <td style="padding: 8px 10px; text-align: right; font-weight: 600; ${qtyColor}">${item.qty.toLocaleString('id-ID')}</td>
                </tr>`;
            });

            const totalColor = totalQty < 0 ? 'color: #fca5a5;' : '';
            html += `</tbody>
                    <tfoot style="background: #1e3a5f; color: white; font-weight: bold;">
                        <tr>
                            <td colspan="2" style="padding: 10px;">Total</td>
                            <td style="padding: 10px;"></td>
                            <td style="padding: 10px; text-align: right; ${totalColor}">${totalQty.toLocaleString('id-ID')}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>`;

            document.getElementById('skuModalTitle').textContent = '📋 Detail SKU: ' + kodeKecil;
            document.getElementById('skuModalBody').innerHTML = html;
            document.getElementById('skuModal').classList.add('active');
            document.body.style.overflow = 'hidden';
        }

        function closeSkuModal(event) {
            if (event && event.target !== event.currentTarget) return;
            document.getElementById('skuModal').classList.remove('active');
            document.body.style.overflow = 'auto';
        }

        // Close tier modal with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeTierModal();
                closeSkuModal();
            }
        });

        // ==================== STOCK CONTROL FUNCTIONS ====================
        let scItems = [];
        let scFilteredItems = [];
        let scCurrentPage = 1;
        const scItemsPerPage = 50;

        function buildSkuItems() {
            const skuMap = {};
            const retailData = allData.DDD?.retail || [];
            const whData = allData.DDD?.warehouse || [];

            // Process retail data
            retailData.forEach(item => {
                const sku = item.sku;
                if (!sku) return;
                if (!skuMap[sku]) {
                    skuMap[sku] = {
                        sku: sku,
                        kodeKecil: item.kode_kecil,
                        name: item.name,
                        size: item.size || '',
                        series: item.series,
                        gender: item.gender,
                        tier: item.tier,
                        WHS: 0, WHB: 0, WHJ: 0,
                        stokToko: 0,
                        stokTokoBali: 0,
                        stokTokoJakarta: 0,
                        stokTokoJatim: 0,
                        stokTokoBatam: 0,
                        stokTokoSulawesi: 0,
                        stokTokoSumatera: 0,
                        globalStock: 0,
                        whTotal: 0
                    };
                }
                // Sum retail stock by area
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([store, stock]) => {
                        const area = getAreaFromStore(store);
                        const s = store.toLowerCase();
                        skuMap[sku].stokToko += stock;
                        if (area === 'Bali') skuMap[sku].stokTokoBali += stock;
                        else if (area === 'Jakarta') skuMap[sku].stokTokoJakarta += stock;
                        else if (area === 'Jawa Timur') skuMap[sku].stokTokoJatim += stock;
                        else {
                            if (s.includes('batam')) skuMap[sku].stokTokoBatam += stock;
                            else if (s.includes('manado')) skuMap[sku].stokTokoSulawesi += stock;
                            else if (s.includes('ska')) skuMap[sku].stokTokoSumatera += stock;
                        }
                    });
                }
            });

            // Process warehouse data
            whData.forEach(item => {
                const sku = item.sku;
                if (!sku) return;
                if (!skuMap[sku]) {
                    skuMap[sku] = {
                        sku: sku,
                        kodeKecil: item.kode_kecil,
                        name: item.name,
                        size: item.size || '',
                        series: item.series,
                        gender: item.gender,
                        tier: item.tier,
                        WHS: 0, WHB: 0, WHJ: 0,
                        stokToko: 0,
                        stokTokoBali: 0,
                        stokTokoJakarta: 0,
                        stokTokoJatim: 0,
                        stokTokoBatam: 0,
                        stokTokoSulawesi: 0,
                        stokTokoSumatera: 0,
                        globalStock: 0,
                        whTotal: 0
                    };
                }
                // Sum warehouse stock
                if (item.store_stock) {
                    Object.entries(item.store_stock).forEach(([wh, stock]) => {
                        const w = wh.toLowerCase();
                        if (w.includes('pusat')) skuMap[sku].WHS += stock;
                        else if (w.includes('bali') || w.includes('gatsu')) skuMap[sku].WHB += stock;
                        else if (w.includes('jakarta') || w.includes('pluit')) skuMap[sku].WHJ += stock;
                    });
                }
            });

            // Calculate totals
            Object.values(skuMap).forEach(item => {
                item.whTotal = item.WHS + item.WHB + item.WHJ;
                item.globalStock = item.whTotal + item.stokToko;
            });

            return Object.values(skuMap);
        }

        function initStockControl() {
            scItems = buildSkuItems();
            // Populate series filter
            const seriesSet = new Set();
            scItems.forEach(item => { if (item.series) seriesSet.add(item.series); });
            const seriesSelect = document.getElementById('scFilterSeries');
            if (seriesSelect) {
                seriesSelect.innerHTML = '<option value="">Semua</option>';
                [...seriesSet].sort().forEach(s => {
                    seriesSelect.innerHTML += '<option value="' + s + '">' + s + '</option>';
                });
            }
            renderStockControlTable();
        }

        function renderStockControlTable() {
            const area = document.getElementById('scFilterArea')?.value || 'all';
            const gender = document.getElementById('scFilterGender')?.value || '';
            const series = document.getElementById('scFilterSeries')?.value || '';
            const tier = document.getElementById('scFilterTier')?.value || '';
            const twtoFilter = document.getElementById('scFilterTWTO')?.value || '';
            const search = (document.getElementById('scSearch')?.value || '').toLowerCase();

            // Build sales lookup from scItems (article level)
            const salesLookup = {};
            (allData.DDD?.retail || []).forEach(item => {
                if (!item.kode_kecil) return;
                if (!salesLookup[item.kode_kecil]) {
                    salesLookup[item.kode_kecil] = {
                        salesM1: item.sales_m1 || 0,
                        salesM2: item.sales_m2 || 0,
                        salesM3: item.sales_m3 || 0,
                        avgSales: item.avg_sales || 0,
                        salesBali: item.sales_bali || {m1:0,m2:0,m3:0,avg:0},
                        salesJakarta: item.sales_jakarta || {m1:0,m2:0,m3:0,avg:0},
                        salesJatim: item.sales_jatim || {m1:0,m2:0,m3:0,avg:0},
                        salesOther: item.sales_other || {m1:0,m2:0,m3:0,avg:0}
                    };
                }
            });

            // Count SKUs per article for sales distribution
            const skuCountPerArticle = {};
            scItems.forEach(item => {
                skuCountPerArticle[item.kodeKecil] = (skuCountPerArticle[item.kodeKecil] || 0) + 1;
            });

            // Filter items
            scFilteredItems = scItems.filter(item => {
                if (gender && item.gender !== gender) return false;
                if (series && item.series !== series) return false;
                if (tier && String(item.tier) !== tier) return false;
                if (search && !item.sku?.toLowerCase().includes(search) && !item.name?.toLowerCase().includes(search)) return false;

                // Area filter for stock
                if (area !== 'all') {
                    let hasStock = false;
                    if (area === 'BALI') hasStock = (item.WHB + item.stokTokoBali) !== 0;
                    else if (area === 'JAKARTA') hasStock = (item.WHJ + item.stokTokoJakarta) !== 0;
                    else if (area === 'JATIM') hasStock = (item.WHS + item.stokTokoJatim) !== 0;
                    else if (area === 'BATAM') hasStock = item.stokTokoBatam !== 0;
                    else if (area === 'SULAWESI') hasStock = item.stokTokoSulawesi !== 0;
                    else if (area === 'SUMATERA') hasStock = item.stokTokoSumatera !== 0;
                    if (!hasStock) return false;
                }

                // TW+TO filter
                if (twtoFilter) {
                    const sales = salesLookup[item.kodeKecil] || {};
                    const skuCount = skuCountPerArticle[item.kodeKecil] || 1;
                    const avgSales = (sales.avgSales || 0) / skuCount;
                    const twto = avgSales > 0 ? (item.globalStock / avgSales) : 999;
                    if (twtoFilter === 'critical' && twto >= 2) return false;
                    if (twtoFilter === 'low' && (twto < 2 || twto >= 4)) return false;
                    if (twtoFilter === 'normal' && (twto < 4 || twto >= 8)) return false;
                    if (twtoFilter === 'high' && twto < 8) return false;
                }
                return true;
            });

            // Pagination
            const totalPages = Math.ceil(scFilteredItems.length / scItemsPerPage);
            if (scCurrentPage > totalPages) scCurrentPage = 1;
            const start = (scCurrentPage - 1) * scItemsPerPage;
            const pageData = scFilteredItems.slice(start, start + scItemsPerPage);

            // Render table
            const tbody = document.getElementById('scTableBody');
            if (!tbody) return;

            tbody.innerHTML = pageData.map(item => {
                const sales = salesLookup[item.kodeKecil] || {};
                const skuCount = skuCountPerArticle[item.kodeKecil] || 1;
                let m1, m2, m3, avgSales, whStock, tokoStock, globalStock;

                if (area === 'all') {
                    m1 = (sales.salesM1 || 0) / skuCount;
                    m2 = (sales.salesM2 || 0) / skuCount;
                    m3 = (sales.salesM3 || 0) / skuCount;
                    avgSales = (sales.avgSales || 0) / skuCount;
                    whStock = item.whTotal;
                    tokoStock = item.stokToko;
                    globalStock = item.globalStock;
                } else if (area === 'BALI') {
                    m1 = (sales.salesBali?.m1 || 0) / skuCount;
                    m2 = (sales.salesBali?.m2 || 0) / skuCount;
                    m3 = (sales.salesBali?.m3 || 0) / skuCount;
                    avgSales = (sales.salesBali?.avg || 0) / skuCount;
                    whStock = item.WHB || 0;
                    tokoStock = item.stokTokoBali || 0;
                    globalStock = whStock + tokoStock;
                } else if (area === 'JAKARTA') {
                    m1 = (sales.salesJakarta?.m1 || 0) / skuCount;
                    m2 = (sales.salesJakarta?.m2 || 0) / skuCount;
                    m3 = (sales.salesJakarta?.m3 || 0) / skuCount;
                    avgSales = (sales.salesJakarta?.avg || 0) / skuCount;
                    whStock = item.WHJ || 0;
                    tokoStock = item.stokTokoJakarta || 0;
                    globalStock = whStock + tokoStock;
                } else if (area === 'JATIM') {
                    m1 = (sales.salesJatim?.m1 || 0) / skuCount;
                    m2 = (sales.salesJatim?.m2 || 0) / skuCount;
                    m3 = (sales.salesJatim?.m3 || 0) / skuCount;
                    avgSales = (sales.salesJatim?.avg || 0) / skuCount;
                    whStock = item.WHS || 0;
                    tokoStock = item.stokTokoJatim || 0;
                    globalStock = whStock + tokoStock;
                } else if (area === 'BATAM') {
                    m1 = (sales.salesOther?.m1 || 0) / skuCount / 3;
                    m2 = (sales.salesOther?.m2 || 0) / skuCount / 3;
                    m3 = (sales.salesOther?.m3 || 0) / skuCount / 3;
                    avgSales = (sales.salesOther?.avg || 0) / skuCount / 3;
                    whStock = 0;
                    tokoStock = item.stokTokoBatam || 0;
                    globalStock = tokoStock;
                } else if (area === 'SULAWESI') {
                    m1 = (sales.salesOther?.m1 || 0) / skuCount / 3;
                    m2 = (sales.salesOther?.m2 || 0) / skuCount / 3;
                    m3 = (sales.salesOther?.m3 || 0) / skuCount / 3;
                    avgSales = (sales.salesOther?.avg || 0) / skuCount / 3;
                    whStock = 0;
                    tokoStock = item.stokTokoSulawesi || 0;
                    globalStock = tokoStock;
                } else if (area === 'SUMATERA') {
                    m1 = (sales.salesOther?.m1 || 0) / skuCount / 3;
                    m2 = (sales.salesOther?.m2 || 0) / skuCount / 3;
                    m3 = (sales.salesOther?.m3 || 0) / skuCount / 3;
                    avgSales = (sales.salesOther?.avg || 0) / skuCount / 3;
                    whStock = 0;
                    tokoStock = item.stokTokoSumatera || 0;
                    globalStock = tokoStock;
                }

                const tw = avgSales > 0 ? (whStock / avgSales).toFixed(1) : 0;
                const to = avgSales > 0 ? (tokoStock / avgSales).toFixed(1) : 0;
                const twVal = parseFloat(tw) || 0;
                const toVal = parseFloat(to) || 0;
                const twtoVal = twVal + toVal;
                const twto = twtoVal.toFixed(1);

                let twColor = '#6b7280', twBg = 'transparent';
                let toColor = '#6b7280', toBg = 'transparent';
                let twtoColor = '#6b7280', twtoBg = 'transparent';
                if (avgSales > 0) {
                    if (twVal < 1) { twColor = '#ef4444'; twBg = '#fef2f2'; }
                    else if (twVal < 2) { twColor = '#f59e0b'; twBg = '#fffbeb'; }
                    else if (twVal < 4) { twColor = '#10b981'; twBg = '#f0fdf4'; }
                    else { twColor = '#3b82f6'; twBg = '#eff6ff'; }

                    if (toVal < 1) { toColor = '#ef4444'; toBg = '#fef2f2'; }
                    else if (toVal < 2) { toColor = '#f59e0b'; toBg = '#fffbeb'; }
                    else if (toVal < 4) { toColor = '#10b981'; toBg = '#f0fdf4'; }
                    else { toColor = '#3b82f6'; toBg = '#eff6ff'; }

                    if (twtoVal < 2) { twtoColor = '#ef4444'; twtoBg = '#fef2f2'; }
                    else if (twtoVal < 4) { twtoColor = '#f59e0b'; twtoBg = '#fffbeb'; }
                    else if (twtoVal < 8) { twtoColor = '#10b981'; twtoBg = '#f0fdf4'; }
                    else { twtoColor = '#3b82f6'; twtoBg = '#eff6ff'; }
                }

                let whPusat = '-', whBali = '-', whJkt = '-';
                if (area === 'all') {
                    whPusat = item.WHS.toLocaleString();
                    whBali = item.WHB.toLocaleString();
                    whJkt = item.WHJ.toLocaleString();
                } else if (area === 'BALI') {
                    whBali = item.WHB.toLocaleString();
                } else if (area === 'JAKARTA') {
                    whJkt = item.WHJ.toLocaleString();
                } else if (area === 'JATIM') {
                    whPusat = item.WHS.toLocaleString();
                }

                return '<tr style="border-bottom:1px solid #f3f4f6;color:#1f2937;">' +
                    '<td style="padding:8px;font-family:monospace;font-weight:600;color:#1f2937;">' + item.sku + '</td>' +
                    '<td style="padding:8px;text-align:center;font-weight:500;color:#6366f1;">' + (item.size||'-') + '</td>' +
                    '<td style="padding:8px;font-size:0.75rem;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#4b5563;" title="' + (item.name||'') + '">' + (item.name||'-') + '</td>' +
                    '<td style="padding:8px;text-align:center;font-size:0.75rem;color:#6b7280;">' + (item.series||'-') + '</td>' +
                    '<td style="padding:8px;text-align:center;font-size:0.75rem;color:#6b7280;">' + (item.gender||'-') + '</td>' +
                    '<td style="padding:8px;text-align:center;color:#6b7280;">' + (item.tier||'-') + '</td>' +
                    '<td style="padding:8px;text-align:right;color:#374151;">' + m1.toFixed(1) + '</td>' +
                    '<td style="padding:8px;text-align:right;color:#374151;">' + m2.toFixed(1) + '</td>' +
                    '<td style="padding:8px;text-align:right;color:#374151;">' + m3.toFixed(1) + '</td>' +
                    '<td style="padding:8px;text-align:right;background:#fef3c7;font-weight:600;color:#92400e;">' + avgSales.toFixed(1) + '</td>' +
                    '<td style="padding:8px;text-align:right;color:#374151;">' + whPusat + '</td>' +
                    '<td style="padding:8px;text-align:right;color:#374151;">' + whBali + '</td>' +
                    '<td style="padding:8px;text-align:right;color:#374151;">' + whJkt + '</td>' +
                    '<td style="padding:8px;text-align:right;background:#dbeafe;font-weight:600;color:#1e3a8a;">' + whStock.toLocaleString() + '</td>' +
                    '<td style="padding:8px;text-align:right;background:#dcfce7;font-weight:600;color:#166534;">' + tokoStock.toLocaleString() + '</td>' +
                    '<td style="padding:8px;text-align:right;background:#f3e8ff;font-weight:600;color:#7c3aed;">' + globalStock.toLocaleString() + '</td>' +
                    '<td style="padding:8px;text-align:center;font-weight:600;background:' + twBg + ';color:' + twColor + ';">' + tw + '</td>' +
                    '<td style="padding:8px;text-align:center;font-weight:600;background:' + toBg + ';color:' + toColor + ';">' + to + '</td>' +
                    '<td style="padding:8px;text-align:center;font-weight:700;background:' + twtoBg + ';color:' + twtoColor + ';">' + twto + '</td>' +
                '</tr>';
            }).join('');

            // Page info
            document.getElementById('scPageInfo').textContent =
                'Showing ' + (start + 1) + '-' + Math.min(start + scItemsPerPage, scFilteredItems.length) +
                ' of ' + scFilteredItems.length + ' SKUs';

            // Pagination
            renderScPagination(totalPages);
        }

        function renderScPagination(totalPages) {
            const container = document.getElementById('scPagination');
            if (!container) return;
            let html = '';
            if (totalPages <= 1) { container.innerHTML = ''; return; }

            html += '<button onclick="scGoToPage(1)" style="padding:5px 10px;border:1px solid #d1d5db;background:white;border-radius:4px;cursor:pointer;"' + (scCurrentPage === 1 ? ' disabled' : '') + '>&laquo;</button>';
            html += '<button onclick="scGoToPage(' + (scCurrentPage - 1) + ')" style="padding:5px 10px;border:1px solid #d1d5db;background:white;border-radius:4px;cursor:pointer;"' + (scCurrentPage === 1 ? ' disabled' : '') + '>&lsaquo;</button>';

            let startPage = Math.max(1, scCurrentPage - 2);
            let endPage = Math.min(totalPages, startPage + 4);
            if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

            for (let i = startPage; i <= endPage; i++) {
                html += '<button onclick="scGoToPage(' + i + ')" style="padding:5px 10px;border:1px solid ' + (i === scCurrentPage ? '#10b981' : '#d1d5db') + ';background:' + (i === scCurrentPage ? '#10b981' : 'white') + ';color:' + (i === scCurrentPage ? 'white' : '#374151') + ';border-radius:4px;cursor:pointer;">' + i + '</button>';
            }

            html += '<button onclick="scGoToPage(' + (scCurrentPage + 1) + ')" style="padding:5px 10px;border:1px solid #d1d5db;background:white;border-radius:4px;cursor:pointer;"' + (scCurrentPage === totalPages ? ' disabled' : '') + '>&rsaquo;</button>';
            html += '<button onclick="scGoToPage(' + totalPages + ')" style="padding:5px 10px;border:1px solid #d1d5db;background:white;border-radius:4px;cursor:pointer;"' + (scCurrentPage === totalPages ? ' disabled' : '') + '>&raquo;</button>';

            container.innerHTML = html;
        }

        function scGoToPage(page) {
            scCurrentPage = page;
            renderStockControlTable();
        }

        function exportStockControl() {
            alert('Export feature coming soon!');
        }
    </script>
</body>
</html>'''
    return html

def main():
    print("=" * 60)
    print("  INVENTORY DASHBOARD GENERATOR v3.0")
    print("=" * 60)
    print()

    script_dir = Path(__file__).parent

    # Load Master Data dari Google Sheets
    print("📋 Loading Master dari Google Sheets...")
    load_master_data()      # Master Data (gid=0) - mapping SKU ke info
    load_master_produk()    # Master Produk (gid=813944059) - Tier
    load_master_store()     # Master Store/Warehouse (gid=1803569317) - Area mapping
    load_max_stock()        # Max Stock (gid=382740121) - Max stock per store/WH
    load_master_assortment()  # Master Assortment (gid=1063661008) - Assortment per kode kecil
    print()

    all_data = {}
    all_stores = {}

    for entity, files in FILES_CONFIG.items():
        print(f"\n📁 {entity}:")
        all_data[entity] = {}
        all_stores[entity] = {}

        for data_type, filename in files.items():
            if filename:
                filepath = script_dir / filename
                items, stores = read_csv_detailed(str(filepath), entity, data_type)
                all_data[entity][data_type] = items
                all_stores[entity][data_type] = stores
            else:
                all_data[entity][data_type] = []
                all_stores[entity][data_type] = []

    print("\n" + "=" * 60)
    print("  Generating Dashboard...")
    print("=" * 60)

    html_content = generate_html(all_data, all_stores)

    output_path = script_dir / 'dashboard_inventory.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ Dashboard berhasil dibuat!")
    print(f"   File: {output_path}")
    print()

    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    for entity, data in all_data.items():
        wh_count = len(data.get('warehouse', []))
        rt_count = len(data.get('retail', []))
        wh_stores = len(all_stores[entity].get('warehouse', []))
        rt_stores = len(all_stores[entity].get('retail', []))
        print(f"  {entity}: WH={wh_count} SKU ({wh_stores} loc) | Retail={rt_count} SKU ({rt_stores} stores)")
    print()

if __name__ == '__main__':
    main()
