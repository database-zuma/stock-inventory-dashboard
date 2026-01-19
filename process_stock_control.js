// Process Stock Control - Format sesuai template
const fs = require('fs');
const path = require('path');

// ============ LOAD SALES DATA ============
const csvPath = path.join(__dirname, 'order-detail-ab0b5e97289247159e6fbd29ccf90d5b.csv');
const csvContent = fs.readFileSync(csvPath, 'utf8');

// Parse CSV
function parseCSV(content) {
    const lines = content.split('\n');
    const headers = lines[0].split(';');
    const data = [];
    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;
        const values = line.split(';');
        const row = {};
        headers.forEach((h, idx) => row[h.trim()] = values[idx] || '');
        data.push(row);
    }
    return data;
}

const salesData = parseCSV(csvContent);
console.log(`Loaded ${salesData.length} sales records`);

// Filter product sales (exclude bags, boxes)
const productSales = salesData.filter(row => {
    const sku = (row.Sku || '').toUpperCase();
    return sku && !sku.includes('SHOPBAG') && !sku.includes('PAPERBAG') &&
           !sku.includes('INBOX') && !sku.includes('BOX');
});
console.log(`Product sales: ${productSales.length}`);

// ============ LOAD INVENTORY DATA ============
const htmlPath = path.join(__dirname, 'dashboard_inventory.html');
const html = fs.readFileSync(htmlPath, 'utf8');

const allDataMatch = html.match(/const allData = (\{[\s\S]*?\});[\s\n]*const allStores/);
if (!allDataMatch) {
    console.error('Could not find allData');
    process.exit(1);
}
const inventoryData = JSON.parse(allDataMatch[1]);

// ============ WAREHOUSE MAPPING ============
const warehouseNameMap = {
    'warehouse bali gatsu - box': 'WHB',
    'warehouse bali gatsu - protol': 'WHB',
    'warehouse bali gatsu': 'WHB',
    'warehouse pluit': 'WHJ',
    'warehouse pusat': 'WHS',
    'warehouse pusat protol': 'WHS'
};

function getWarehouseCode(whName) {
    const normalized = whName.toLowerCase().trim();
    for (const [key, code] of Object.entries(warehouseNameMap)) {
        if (normalized.includes(key)) return code;
    }
    return null;
}

// Extract KODE KECIL from SKU (remove size suffix)
function getKodeKecil(sku) {
    // M1SPV201Z40 -> M1SPV201
    // L1CAV201Z39 -> L1CAV201
    return sku.replace(/Z\d+$/, '');
}

// ============ AGGREGATE SALES BY KODE KECIL AND MONTH ============
const salesByKode = {};

productSales.forEach(row => {
    const date = row['Tanggal Pesanan']?.substring(0, 10);
    const sku = row.Sku?.trim();
    const qty = parseInt(row.Jumlah) || 0;
    if (!date || !sku || qty <= 0) return;

    const kodeKecil = getKodeKecil(sku);
    const month = date.substring(0, 7); // YYYY-MM

    if (!salesByKode[kodeKecil]) {
        salesByKode[kodeKecil] = {
            kodeKecil,
            months: {},
            totalSales: 0
        };
    }

    if (!salesByKode[kodeKecil].months[month]) {
        salesByKode[kodeKecil].months[month] = 0;
    }
    salesByKode[kodeKecil].months[month] += qty;
    salesByKode[kodeKecil].totalSales += qty;
});

console.log(`\nUnique KODE KECIL: ${Object.keys(salesByKode).length}`);

// ============ AGGREGATE INVENTORY BY KODE KECIL ============
const inventoryByKode = {};

// Process retail data
const dddRetail = inventoryData.DDD?.retail || [];
dddRetail.forEach(item => {
    const kodeKecil = item.kode_kecil || getKodeKecil(item.sku);

    if (!inventoryByKode[kodeKecil]) {
        inventoryByKode[kodeKecil] = {
            kodeKecil,
            article: item.name?.replace(/,\s*\d+\/?\d*$/, '').replace(/,\s*(SIZE\s*)?\d+$/, '').trim() || '',
            gender: item.gender || '',
            series: item.series || '',
            tier: item.tier || '',
            category: item.category || '',
            stokToko: 0,
            WHB: 0,
            WHJ: 0,
            WHS: 0
        };
    }

    // Sum store stock
    if (item.store_stock) {
        Object.entries(item.store_stock).forEach(([store, qty]) => {
            if (qty > 0 && !store.toLowerCase().includes('warehouse')) {
                inventoryByKode[kodeKecil].stokToko += qty;
            }
        });
    }

    inventoryByKode[kodeKecil].total = (inventoryByKode[kodeKecil].total || 0) + (item.total || 0);
});

// Process warehouse data
const dddWarehouse = inventoryData.DDD?.warehouse || [];
dddWarehouse.forEach(item => {
    const kodeKecil = item.kode_kecil || getKodeKecil(item.sku);

    if (!inventoryByKode[kodeKecil]) {
        inventoryByKode[kodeKecil] = {
            kodeKecil,
            article: item.name?.replace(/,\s*\d+\/?\d*$/, '').replace(/,\s*(SIZE\s*)?\d+$/, '').trim() || '',
            gender: item.gender || '',
            series: item.series || '',
            tier: item.tier || '',
            category: item.category || '',
            stokToko: 0,
            WHB: 0,
            WHJ: 0,
            WHS: 0
        };
    }

    // Sum warehouse stock
    if (item.store_stock) {
        Object.entries(item.store_stock).forEach(([wh, qty]) => {
            if (qty > 0) {
                const whCode = getWarehouseCode(wh);
                if (whCode && inventoryByKode[kodeKecil][whCode] !== undefined) {
                    inventoryByKode[kodeKecil][whCode] += qty;
                }
            }
        });
    }
});

// ============ MERGE SALES + INVENTORY ============
const stockControlList = [];

// Get all unique months from sales
const allMonths = new Set();
Object.values(salesByKode).forEach(s => {
    Object.keys(s.months).forEach(m => allMonths.add(m));
});
const sortedMonths = Array.from(allMonths).sort();
console.log(`Sales months: ${sortedMonths.join(', ')}`);

// Use last 3 months
const last3Months = sortedMonths.slice(-3);
console.log(`Using last 3 months: ${last3Months.join(', ')}`);

// Combine all kode kecil
const allKodes = new Set([...Object.keys(salesByKode), ...Object.keys(inventoryByKode)]);

allKodes.forEach(kodeKecil => {
    const sales = salesByKode[kodeKecil] || { months: {}, totalSales: 0 };
    const inventory = inventoryByKode[kodeKecil] || {
        article: '', gender: '', series: '', tier: '',
        stokToko: 0, WHB: 0, WHJ: 0, WHS: 0
    };

    // Sales per month
    const salesM1 = sales.months[last3Months[0]] || 0;
    const salesM2 = sales.months[last3Months[1]] || 0;
    const salesM3 = sales.months[last3Months[2]] || 0;
    const avgSales = Math.round((salesM1 + salesM2 + salesM3) / 3);

    // Stock
    const whTotal = inventory.WHB + inventory.WHJ + inventory.WHS;
    const globalStock = inventory.stokToko + whTotal;

    // Turnover calculations
    // TW = WH Total / Avg Sales (bulan)
    // TO = Global Stock / Avg Sales (bulan)
    const tw = avgSales > 0 ? (whTotal / avgSales).toFixed(1) : '-';
    const to = avgSales > 0 ? (globalStock / avgSales).toFixed(1) : '-';

    stockControlList.push({
        kodeKecil,
        article: inventory.article,
        series: inventory.series,
        gender: inventory.gender,
        tier: inventory.tier,
        salesM1,
        salesM2,
        salesM3,
        avgSales,
        WHS: inventory.WHS,
        WHB: inventory.WHB,
        WHJ: inventory.WHJ,
        whTotal,
        stokToko: inventory.stokToko,
        globalStock,
        tw: parseFloat(tw) || 0,
        to: parseFloat(to) || 0
    });
});

// Sort by avgSales descending
stockControlList.sort((a, b) => b.avgSales - a.avgSales);

// ============ OUTPUT ============
const output = {
    generated: new Date().toISOString(),
    salesPeriod: {
        months: last3Months,
        monthNames: last3Months.map(m => {
            const [year, month] = m.split('-');
            const monthNames = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                               'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'];
            return monthNames[parseInt(month)];
        })
    },
    warehouseSummary: {
        WHB: stockControlList.reduce((sum, i) => sum + i.WHB, 0),
        WHJ: stockControlList.reduce((sum, i) => sum + i.WHJ, 0),
        WHS: stockControlList.reduce((sum, i) => sum + i.WHS, 0)
    },
    totalStokToko: stockControlList.reduce((sum, i) => sum + i.stokToko, 0),
    totalGlobalStock: stockControlList.reduce((sum, i) => sum + i.globalStock, 0),
    items: stockControlList
};

fs.writeFileSync(
    path.join(__dirname, 'stock_control_v2.json'),
    JSON.stringify(output, null, 2)
);

// Print top 20
console.log('\n=== TOP 20 BY AVERAGE SALES ===');
console.log('KODE KECIL      | Article                              | Gender  | Avg  | WH Tot | Toko  | Global | TO');
console.log('-'.repeat(110));
stockControlList.slice(0, 20).forEach(item => {
    console.log(
        `${item.kodeKecil.padEnd(15)} | ${(item.article || '-').substring(0, 36).padEnd(36)} | ${(item.gender || '-').padEnd(7)} | ${String(item.avgSales).padStart(4)} | ${String(item.whTotal).padStart(6)} | ${String(item.stokToko).padStart(5)} | ${String(item.globalStock).padStart(6)} | ${String(item.to).padStart(4)}`
    );
});

console.log(`\nTotal items: ${stockControlList.length}`);
console.log(`Saved to stock_control_v2.json`);
