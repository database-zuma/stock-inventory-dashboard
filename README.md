# Stock Inventory Dashboard

Dashboard untuk monitoring stock Retail dan Warehouse ZUMA.

## Live Dashboard

**[Buka Dashboard](https://database-id.github.io/stock-inventory-dashboard/dashboard_inventory.html)**

## Fitur

- **Multi-Store Support**: DDD, LJBB, MBB, UBB
- **Stock Monitoring**: Warehouse dan Retail
- **Tier Analysis**: Breakdown per tier (A, B, C, D, E)
- **DOS (Days of Stock)**: Analisis stock control
- **Max Stock Analysis**: Identifikasi overstock
- **Filter & Search**: Filter by area, store, tier, artikel

## Struktur File

```
├── dashboard_inventory.html   # Dashboard utama (buka di browser)
├── generate_dashboard.py      # Script generate dashboard
├── Stock WH *.csv             # Data stock warehouse per store
├── Stok Retail *.csv          # Data stock retail
├── stock_control_v*.json      # Data DOS & stock control
└── inventory_summary.json     # Summary data
```

## Cara Update Dashboard

### 1. Update Data CSV
Letakkan file CSV terbaru di folder ini:
- `Stock WH DDD.csv`, `Stock WH LJBB.csv`, `Stock WH MBB.csv`, `Stock WH UBB.csv`
- `Stok Retail DDD.csv`

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
- Master Produk: Google Sheets (auto-fetch saat generate)

## Tech Stack

- Python 3 (generate dashboard)
- HTML/CSS/JavaScript (dashboard frontend)
- GitHub Pages (hosting)
