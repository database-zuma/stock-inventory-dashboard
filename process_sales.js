// Process Sales Data for Stock Control
const fs = require('fs');
const path = require('path');

// Store to Warehouse mapping
const storeWarehouseMap = {
    // Bali -> Warehouse Bali
    'zuma bajra': 'WHB', 'zuma bangli': 'WHB', 'zuma batubulan': 'WHB',
    'zuma dalung': 'WHB', 'zuma gianyar': 'WHB', 'zuma jembrana': 'WHB',
    'zuma kapal': 'WHB', 'zuma karangasem': 'WHB', 'zuma kedonganan': 'WHB',
    'zuma kesiman': 'WHB', 'zuma klungkung': 'WHB', 'zuma level 21': 'WHB',
    'zuma lippo bali': 'WHB', 'zuma living world': 'WHB', 'zuma mall bali galeria': 'WHB',
    'zuma mall bali icon': 'WHB', 'zuma monang maning': 'WHB', 'zuma panjer': 'WHB',
    'zuma peguyangan': 'WHB', 'zuma peliatan': 'WHB', 'zuma lebah peliatan': 'WHB',
    'zuma pemogan': 'WHB', 'zuma penatih': 'WHB', 'zuma seririt': 'WHB',
    'zuma singaraja': 'WHB', 'zuma tabanan': 'WHB', 'zuma tanah lot': 'WHB',
    'zuma uluwatu': 'WHB',

    // Lombok -> Warehouse Bali
    'zuma epicentrum lombok': 'WHB', 'zuma epicentrum': 'WHB',
    'zuma mataram lombok': 'WHB', 'zuma mataram': 'WHB',

    // Jakarta -> Warehouse Jakarta (Pluit)
    'zuma bintaro xchange': 'WHJ', 'zuma bintaro': 'WHJ',
    'zuma lippo mall puri': 'WHJ', 'zuma lippo puri': 'WHJ',
    'zuma moi': 'WHJ', 'zuma pluit village': 'WHJ', 'zuma pluit village mall': 'WHJ',

    // Jawa Timur -> Warehouse Pusat (Jatim)
    'zuma city of tomorrow': 'WHS', 'zuma city of tomorrow mall': 'WHS', 'zuma cito': 'WHS',
    'zuma galaxy mall': 'WHS', 'zuma icon mall gresik': 'WHS',
    'zuma lippo batu': 'WHS', 'zuma lippo sidoarjo': 'WHS',
    'zuma matos': 'WHS', 'zuma mall olympic garden': 'WHS', 'zuma mog': 'WHS',
    'zuma ptc': 'WHS', 'zuma royal plaza': 'WHS',
    'zuma sunrise mojokerto': 'WHS', 'zuma sunrise mall mojokerto': 'WHS',
    'zuma tunjungan plaza 3': 'WHS', 'zuma tp3': 'WHS'

    // Others (Batam, Sulawesi, Sumatera) -> No warehouse
};

// Get warehouse for store
function getWarehouse(storeName) {
    const normalized = storeName.toLowerCase().trim();

    // Direct match
    if (storeWarehouseMap[normalized]) {
        return storeWarehouseMap[normalized];
    }

    // Partial match
    for (const [key, wh] of Object.entries(storeWarehouseMap)) {
        if (normalized.includes(key) || key.includes(normalized)) {
            return wh;
        }
    }

    return null; // No warehouse
}

// Get area from store name
function getArea(storeName) {
    const s = storeName.toLowerCase();

    // Bali stores
    if (s.includes('bajra') || s.includes('bangli') || s.includes('batubulan') ||
        s.includes('dalung') || s.includes('gianyar') || s.includes('jembrana') ||
        s.includes('kapal') || s.includes('karangasem') || s.includes('kedonganan') ||
        s.includes('kesiman') || s.includes('klungkung') || s.includes('level 21') ||
        s.includes('lippo bali') || s.includes('living world') || s.includes('galeria') ||
        s.includes('bali icon') || s.includes('monang') || s.includes('panjer') ||
        s.includes('peguyangan') || s.includes('peliatan') || s.includes('pemogan') ||
        s.includes('penatih') || s.includes('seririt') || s.includes('singaraja') ||
        s.includes('tabanan') || s.includes('tanah lot') || s.includes('uluwatu')) {
        return 'Bali';
    }

    // Lombok
    if (s.includes('lombok') || s.includes('mataram') || s.includes('epicentrum')) {
        return 'Lombok';
    }

    // Jakarta
    if (s.includes('pluit') || s.includes('puri') || s.includes('moi') || s.includes('bintaro')) {
        return 'Jakarta';
    }

    // Jawa Timur
    if (s.includes('galaxy') || s.includes('tunjungan') || s.includes('ptc') ||
        s.includes('royal') || s.includes('matos') || s.includes('cito') ||
        s.includes('city of tomorrow') || s.includes('olympic') || s.includes('sidoarjo') ||
        s.includes('gresik') || s.includes('mojokerto') || s.includes('batu')) {
        return 'Jawa Timur';
    }

    // Sulawesi
    if (s.includes('manado')) return 'Sulawesi';

    // Batam
    if (s.includes('batam') || s.includes('nagoya')) return 'Batam';

    // Sumatera
    if (s.includes('ska') || s.includes('sumatera')) return 'Sumatera';

    return 'Other';
}

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
        headers.forEach((h, idx) => {
            row[h.trim()] = values[idx] || '';
        });
        data.push(row);
    }

    return data;
}

// Main processing
const csvPath = path.join(__dirname, 'order-detail-8ca1621ed66942478178a6086c848029.csv');
const content = fs.readFileSync(csvPath, 'utf8');
const salesData = parseCSV(content);

console.log(`Total sales records: ${salesData.length}`);

// Filter out non-product items (SHOPBAG, PAPERBAG, INBOX, etc.)
const productSales = salesData.filter(row => {
    const sku = (row.Sku || '').toUpperCase();
    return sku &&
           !sku.includes('SHOPBAG') &&
           !sku.includes('PAPERBAG') &&
           !sku.includes('INBOX') &&
           !sku.includes('BOX');
});

console.log(`Product sales (excluding bags/boxes): ${productSales.length}`);

// Calculate sales by SKU and Store
const salesBySkuStore = {};
const salesByStore = {};
const dateRange = { min: null, max: null };

productSales.forEach(row => {
    const date = row['Tanggal Pesanan']?.substring(0, 10);
    const store = row.Toko?.trim();
    const sku = row.Sku?.trim();
    const qty = parseInt(row.Jumlah) || 0;
    const productName = row.Produk?.trim();

    if (!date || !store || !sku || qty <= 0) return;

    // Track date range
    if (!dateRange.min || date < dateRange.min) dateRange.min = date;
    if (!dateRange.max || date > dateRange.max) dateRange.max = date;

    // Sales by SKU + Store
    const key = `${sku}|${store}`;
    if (!salesBySkuStore[key]) {
        salesBySkuStore[key] = {
            sku,
            store,
            productName,
            area: getArea(store),
            warehouse: getWarehouse(store),
            totalQty: 0,
            transactions: 0
        };
    }
    salesBySkuStore[key].totalQty += qty;
    salesBySkuStore[key].transactions++;

    // Sales by Store
    if (!salesByStore[store]) {
        salesByStore[store] = {
            store,
            area: getArea(store),
            warehouse: getWarehouse(store),
            totalQty: 0,
            totalSku: new Set(),
            transactions: 0
        };
    }
    salesByStore[store].totalQty += qty;
    salesByStore[store].totalSku.add(sku);
    salesByStore[store].transactions++;
});

// Calculate days in date range
const startDate = new Date(dateRange.min);
const endDate = new Date(dateRange.max);
const days = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;

console.log(`\nDate range: ${dateRange.min} to ${dateRange.max} (${days} days)`);

// Add daily rate calculations
Object.values(salesBySkuStore).forEach(item => {
    item.dailyRate = item.totalQty / days;
    item.monthlyRate = item.dailyRate * 30;
});

Object.values(salesByStore).forEach(item => {
    item.totalSku = item.totalSku.size;
    item.dailyRate = item.totalQty / days;
});

// Output results
const salesSummary = {
    generated: new Date().toISOString(),
    dateRange: {
        start: dateRange.min,
        end: dateRange.max,
        days
    },
    totalTransactions: productSales.length,
    salesBySkuStore: Object.values(salesBySkuStore),
    salesByStore: Object.values(salesByStore)
};

// Write to JSON
fs.writeFileSync(
    path.join(__dirname, 'sales_summary.json'),
    JSON.stringify(salesSummary, null, 2)
);

console.log('\n=== TOP 10 STORES BY SALES ===');
const topStores = Object.values(salesByStore)
    .sort((a, b) => b.totalQty - a.totalQty)
    .slice(0, 10);
topStores.forEach((s, i) => {
    console.log(`${i + 1}. ${s.store} (${s.area}) - ${s.totalQty} pcs (${s.dailyRate.toFixed(1)}/day) → ${s.warehouse || 'No WH'}`);
});

console.log('\n=== TOP 10 SKU BY SALES ===');
const skuSales = {};
Object.values(salesBySkuStore).forEach(item => {
    if (!skuSales[item.sku]) {
        skuSales[item.sku] = { sku: item.sku, name: item.productName, totalQty: 0 };
    }
    skuSales[item.sku].totalQty += item.totalQty;
});
const topSku = Object.values(skuSales).sort((a, b) => b.totalQty - a.totalQty).slice(0, 10);
topSku.forEach((s, i) => {
    console.log(`${i + 1}. ${s.sku} - ${s.totalQty} pcs`);
});

console.log('\nSaved to sales_summary.json');
