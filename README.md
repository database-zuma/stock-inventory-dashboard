# Stock Inventory Dashboard

Dashboard untuk monitoring stock Retail dan Warehouse ZUMA.

## Live Dashboard

**[Buka Dashboard](https://database-zuma.github.io/stock-inventory-dashboard/dashboard_inventory.html)**

## Fitur

### 1. Stock Inventory
- **Multi-Store Support**: DDD, LJBB, MBB, UBB
- **Stock Monitoring**: Warehouse dan Retail
- **Tier Analysis**: Breakdown per tier (1, 2, 3, 4, 5)
- **Filter & Search**: Filter by area, store, tier, artikel

### 2. Max Stock Analysis
- **Fill Rate**: Analisis persentase stock vs max stock
- **Overstock Detection**: Identifikasi item yang melebihi kapasitas
- **Area-based View**: Breakdown per area (Bali, Jakarta, Jawa Timur)

### 3. Control Stock - Turnover Analysis
- **Summary Cards**: WH Pusat (Jatim), WH Bali, WH Jakarta, Total Stok Toko
- **Sales Data**: NOV, DES, JAN (3 bulan terakhir dari salesss.csv)
- **TW (Turnover Weeks)**: WH Stock / Avg Sales
- **TO (Turnover)**: Store Stock / Avg Sales
- **Filters**: Area, Gender, Tier, Search, TW Status, TO Status
- **Data Source**: WH dari DDD + LJBB, Retail dari DDD

## Struktur File

```
├── dashboard_inventory.html   # Dashboard utama (buka di browser)
├── generate_dashboard.py      # Script generate dashboard
├── Stock WH DDD.csv           # Data stock warehouse DDD
├── Stock WH LJBB.csv          # Data stock warehouse LJBB
├── Stock WH MBB.csv           # Data stock warehouse MBB
├── Stock WH UBB.csv           # Data stock warehouse UBB
├── Stok Retail DDD.csv        # Data stock retail
├── salesss.csv                # Data sales (untuk Stock Control)
└── README.md                  # Dokumentasi
```

## Cara Update Dashboard

### 1. Update Data CSV
Letakkan file CSV terbaru di folder ini:
- `Stock WH DDD.csv`, `Stock WH LJBB.csv`, `Stock WH MBB.csv`, `Stock WH UBB.csv`
- `Stok Retail DDD.csv`
- `salesss.csv` (untuk Stock Control - Turnover Analysis)

### 2. Generate Dashboard
```bash
python generate_dashboard.py
```

### 3. Push ke GitHub
```bash
git add -A
git commit -m "Update data [tanggal]"
git push origin main
```

Dashboard akan otomatis terupdate di GitHub Pages dalam beberapa menit.

## Data Source

- Stock Warehouse: Export dari sistem inventory
- Stock Retail: Export dari POS/sistem retail
- Sales Data: Export dari sistem penjualan (salesss.csv)
- Master Produk: Google Sheets (auto-fetch saat generate)
- Master Store: Google Sheets (auto-fetch saat generate)
- Max Stock: Google Sheets (auto-fetch saat generate)

## Tech Stack

- Python 3 (generate dashboard)
- HTML/CSS/JavaScript (dashboard frontend)
- GitHub Pages (hosting)
