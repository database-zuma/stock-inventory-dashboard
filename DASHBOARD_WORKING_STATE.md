# 🛡️ Dashboard Working State — DO NOT REGRESS

> **Last updated:** 7 Maret 2026
> **File:** `dashboard_inventory.html` (~9187 lines)
> **Live:** https://database-zuma.github.io/stock-inventory-dashboard/dashboard_inventory.html

---

## ✅ Semua Tab/View yang SUDAH JALAN

### Sales > Retail Tabs
| Tab | Status | Catatan |
|-----|--------|---------|
| 📊 Performance | ✅ | Score cards, ARP chart, target achievement, store breakdown |
| 🩴 Produk | ✅ | Top 20 produk, tier performance, gender/weekly chart |
| 👥 SPG | ✅ | Leaderboard, area metrics chart (ATV/ATU/ARP per area) |
| 💳 Transaksi | ✅ | Full table: TANGGAL, TOKO, SPG, ORDER, SKU, QTY, PRICE, TOTAL HARGA |
| 🔄 Refund | ✅ | Scorecards, refund by toko, refund by area, donut chart, top artikel, top SPG, detail transaksi |
| 🔍 Cari SKU | ✅ | Search by SKU code OR article name, summary cards, per-SKU breakdown with store-level detail |

### Other Views
| View | Status | Catatan |
|------|--------|---------|
| 📦 Consignment | ✅ | Filters (Tahun/Bulan/Area/Partner/Toko/Cari SKU), metrics, sales per area, partner table, bar charts, top 20, trend bulanan |
| 🏭 Wholesale | ✅ | Basic view (no metric cards/filters — removed per user request) |
| 🌐 Online | ✅ | Basic view (no metric cards/filters — removed per user request) |
| 📊 Stock Inventory | ✅ | DDD/LJBB/MBB/UBB tabs with warehouse/retail toggle |

---

## 🔧 Critical Technical Details — JANGAN DIUBAH

### 1. HTML Nesting Structure (PALING PENTING)
```
salesRetailTabWrapper (line ~1193)
├── Tab buttons div (line ~1194)
├── salesTabPerformance
├── salesTabTrend (hidden, merged into Performance)
├── salesTabProduct
├── salesTabSpg          ← HARUS DITUTUP </div> SEBELUM tab berikutnya!
├── salesTabTransaction  ← HARUS jadi SIBLING, bukan child dari salesTabSpg
├── salesTabSkusearch    ← HARUS jadi SIBLING
├── salesTabRefund       ← HARUS jadi SIBLING
└── </div> closes salesRetailTabWrapper

consignmentView (line ~1522) ← TERPISAH dari retail
```

**⚠️ BUG YANG PERNAH TERJADI:** `salesTabSpg` tidak ditutup → Transaction/Refund/CariSKU jadi CHILD dari SPG → ketika SPG hidden, semua ikut hidden → tab-tab itu kosong.

**FIX (commit 2406ab6):** Tambah `</div>` penutup setelah content SPG tab, SEBELUM `salesTabTransaction` dimulai.

### 2. SKU Search — articleNameMap Priority
```javascript
// Line ~8231 di searchSKUSales()
// ✅ BENAR — cek articleNameMap DULU:
const name = (articleNameMap[article] || item.product_name || '').toUpperCase();

// ❌ SALAH — jangan balik urutannya:
// const name = (item.product_name || articleNameMap[article] || '').toUpperCase();
```

**Kenapa:** `item.product_name` berisi SKU code (e.g., `M1CAV201Z42`) yang SELALU truthy, jadi `articleNameMap` tidak pernah dicek. User search "CLASSIC" return 0 results karena SKU code tidak mengandung "CLASSIC", tapi `articleNameMap` punya nama lengkap seperti "MEN CLASSIC 1, JET BLACK".

### 3. Consignment — Terpisah dari Retail
- Consignment punya layout sendiri, BUKAN copy retail
- Metric cards & global filter HANYA untuk retail
- Consignment punya filter sendiri: Tahun, Bulan, Area, Partner, Toko, Cari SKU (urutan ini!)
- Table header warna sama dengan retail: `#002A3A`
- 9 partner, masing-masing warna unik di bar chart

### 4. API Tunnels
```javascript
// Tunnel LAMA — retail data (stock, sales aggregate, detail, targets, assortment)
API_BASE = 'https://gadgets-explains-municipality-spa.trycloudflare.com'

// Tunnel BARU — refunds + consignment
API_BASE_LOCAL = 'https://lions-outline-furnished-officially.trycloudflare.com'
```
**⚠️ JANGAN KILL cloudflared processes tanpa konfirmasi!**

### 5. Data Quirks
- `salesDetailData` = 82,937 rows (retail transactions)
- `articleNameMap` = 3,369 entries (article code → article name)
- ~32% rows punya `total = 0` — ini masalah di database (`mart.mv_accurate_summary`), bukan bug dashboard
- `product_name` di salesDetailData = SKU code, BUKAN nama artikel

---

## 🚫 Hal yang SUDAH DIHAPUS (Jangan Tambah Balik)

- ❌ Metric cards & filter section di Consignment/Wholesale/Online
- ❌ Bali United dari daftar area/partner
- ❌ Kolom "Trx" dari tabel consignment
- ❌ Header banner di Refund tab
- ❌ "Sales per Partner" (diganti "Sales per Area" + bar chart)
- ❌ Non-sandal products dari view default

---

## 📋 User Preferences (Jangan Override)

- Retail metric card font size — JANGAN UBAH
- Consignment layout — JANGAN samakan dengan retail
- Omosando — TETAP di filter walaupun 0 sales
- Pepito — sudah di-merge jadi 1 entry
- Bar chart consignment — warna BEDA dari retail
- "Total Sales Rp X" — pakai `white-space: nowrap` (Rp gabung dengan angka)
- Filter consignment urutan: Tahun → Bulan → Area → Partner → Toko → Cari SKU
- Area chart: warna Bali ≠ Jatim

---

## 📝 Commits Reference

| Commit | Fix |
|--------|-----|
| `cecb60e` | SKU search articleNameMap priority |
| `2406ab6` | Close salesTabSpg div — HTML nesting fix |
| `9d6f8af` | SPG area metrics chart getAreaFromStore |
| `f6d7d02` | SPG area metrics, consig filter reorder, nowrap values |
| `3e85c30` | Refund bar, header, unique colors, total toko, bigger filters |

---

**⚡ RULE: Sebelum push perubahan apapun, WAJIB cek:**
1. Semua 6 retail tabs masih bisa diklik dan menampilkan data
2. Consignment view masih load data dari API
3. Cari SKU search "CLASSIC" masih return ~470 SKU
4. HTML nesting masih benar (Transaction/Refund/CariSKU = siblings, bukan children)
