// Calculate Days of Stock (DOS) - Combine Inventory + Sales Data
const fs = require('fs');
const path = require('path');

// Load sales summary
const salesPath = path.join(__dirname, 'sales_summary.json');
const salesData = JSON.parse(fs.readFileSync(salesPath, 'utf8'));

// Load inventory from dashboard HTML
const htmlPath = path.join(__dirname, 'dashboard_inventory.html');
const html = fs.readFileSync(htmlPath, 'utf8');

// Extract allData JSON
const allDataMatch = html.match(/const allData = (\{[\s\S]*?\});[\s\n]*const allStores/);
if (!allDataMatch) {
    console.error('Could not find allData in HTML');
    process.exit(1);
}
const inventoryData = JSON.parse(allDataMatch[1]);

// Build sales lookup (by SKU + Store)
const salesLookup = {};
salesData.salesBySkuStore.forEach(item => {
    const key = `${item.sku.toLowerCase()}|${item.store.toLowerCase()}`;
    salesLookup[key] = item;
});

// Build sales by store lookup
const storeSalesLookup = {};
salesData.salesByStore.forEach(item => {
    storeSalesLookup[item.store.toLowerCase()] = item;
});

// Store warehouse mapping
const storeWarehouseMap = {
    // Bali -> WHB
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
    // Lombok -> WHB
    'zuma epicentrum lombok': 'WHB', 'zuma epicentrum': 'WHB',
    'zuma mataram lombok': 'WHB', 'zuma mataram': 'WHB',
    // Jakarta -> WHJ
    'zuma bintaro xchange': 'WHJ', 'zuma lippo mall puri': 'WHJ',
    'zuma moi': 'WHJ', 'zuma pluit village': 'WHJ', 'zuma pluit village mall': 'WHJ',
    // Jawa Timur -> WHS
    'zuma city of tomorrow': 'WHS', 'zuma city of tomorrow mall': 'WHS',
    'zuma galaxy mall': 'WHS', 'zuma icon mall gresik': 'WHS',
    'zuma lippo batu': 'WHS', 'zuma lippo sidoarjo': 'WHS',
    'zuma matos': 'WHS', 'zuma mall olympic garden': 'WHS',
    'zuma ptc': 'WHS', 'zuma royal plaza': 'WHS',
    'zuma sunrise mojokerto': 'WHS', 'zuma sunrise mall mojokerto': 'WHS',
    'zuma tunjungan plaza 3': 'WHS', 'zuma tunjungan plaza': 'WHS'
};

function getWarehouse(storeName) {
    const normalized = storeName.toLowerCase().trim();
    if (storeWarehouseMap[normalized]) return storeWarehouseMap[normalized];
    for (const [key, wh] of Object.entries(storeWarehouseMap)) {
        if (normalized.includes(key) || key.includes(normalized)) return wh;
    }
    return null;
}

function getArea(storeName) {
    const s = storeName.toLowerCase();
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
    if (s.includes('lombok') || s.includes('mataram') || s.includes('epicentrum')) return 'Lombok';
    if (s.includes('pluit') || s.includes('puri') || s.includes('moi') || s.includes('bintaro')) return 'Jakarta';
    if (s.includes('galaxy') || s.includes('tunjungan') || s.includes('ptc') ||
        s.includes('royal') || s.includes('matos') || s.includes('cito') ||
        s.includes('city of tomorrow') || s.includes('olympic') || s.includes('sidoarjo') ||
        s.includes('gresik') || s.includes('mojokerto') || s.includes('batu')) {
        return 'Jawa Timur';
    }
    if (s.includes('manado')) return 'Sulawesi';
    if (s.includes('batam') || s.includes('nagoya')) return 'Batam';
    if (s.includes('ska') || s.includes('sumatera')) return 'Sumatera';
    return 'Other';
}

// Calculate DOS for each store
const storeStockControl = {};
const skuStockControl = [];

// Process DDD retail data (main entity)
const dddRetail = inventoryData.DDD?.retail || [];

dddRetail.forEach(item => {
    if (!item.store_stock) return;

    Object.entries(item.store_stock).forEach(([store, currentStock]) => {
        if (currentStock <= 0) return;

        const storeLower = store.toLowerCase();
        const salesKey = `${item.sku.toLowerCase()}|${storeLower}`;
        const sales = salesLookup[salesKey];

        const dailyRate = sales ? sales.dailyRate : 0;
        const dos = dailyRate > 0 ? Math.round(currentStock / dailyRate) : 999; // 999 = no sales
        const warehouse = getWarehouse(store);
        const area = getArea(store);

        // Add to SKU stock control
        skuStockControl.push({
            sku: item.sku,
            name: item.name,
            gender: item.gender,
            series: item.series,
            tier: item.tier,
            store,
            area,
            warehouse,
            currentStock,
            dailyRate: dailyRate.toFixed(2),
            monthlyRate: (dailyRate * 30).toFixed(1),
            dos,
            status: dos < 14 ? 'CRITICAL' : dos < 30 ? 'WARNING' : dos < 60 ? 'OK' : 'OVERSTOCK'
        });

        // Aggregate by store
        if (!storeStockControl[store]) {
            storeStockControl[store] = {
                store,
                area,
                warehouse,
                totalStock: 0,
                totalSku: 0,
                totalDailyRate: 0,
                critical: 0,
                warning: 0,
                ok: 0,
                overstock: 0
            };
        }
        storeStockControl[store].totalStock += currentStock;
        storeStockControl[store].totalSku++;
        storeStockControl[store].totalDailyRate += dailyRate;

        if (dos < 14) storeStockControl[store].critical++;
        else if (dos < 30) storeStockControl[store].warning++;
        else if (dos < 60) storeStockControl[store].ok++;
        else storeStockControl[store].overstock++;
    });
});

// Calculate store-level DOS
Object.values(storeStockControl).forEach(store => {
    store.avgDos = store.totalDailyRate > 0
        ? Math.round(store.totalStock / store.totalDailyRate)
        : 999;
});

// Output
const stockControlData = {
    generated: new Date().toISOString(),
    salesPeriod: salesData.dateRange,
    storeControl: Object.values(storeStockControl).sort((a, b) => a.avgDos - b.avgDos),
    skuControl: skuStockControl.sort((a, b) => a.dos - b.dos)
};

fs.writeFileSync(
    path.join(__dirname, 'stock_control.json'),
    JSON.stringify(stockControlData, null, 2)
);

console.log('=== STORE STOCK CONTROL (by DOS) ===\n');
console.log('Store                          | Area       | WH  | Stock  | Daily | DOS | Status');
console.log('-'.repeat(90));

stockControlData.storeControl.slice(0, 20).forEach(s => {
    const status = s.avgDos < 14 ? '🔴 CRITICAL' :
                   s.avgDos < 30 ? '🟡 WARNING' :
                   s.avgDos < 60 ? '🟢 OK' : '🔵 OVERSTOCK';
    console.log(
        `${s.store.padEnd(30)} | ${s.area.padEnd(10)} | ${(s.warehouse || '-').padEnd(3)} | ${String(s.totalStock).padStart(6)} | ${s.totalDailyRate.toFixed(1).padStart(5)} | ${String(s.avgDos).padStart(3)} | ${status}`
    );
});

console.log('\n=== CRITICAL SKU (DOS < 14 days) ===');
const criticalSku = skuStockControl.filter(s => s.dos < 14 && s.warehouse).slice(0, 20);
criticalSku.forEach(s => {
    console.log(`${s.sku} @ ${s.store}: ${s.currentStock} pcs, ${s.dailyRate}/day = ${s.dos} days → Restock from ${s.warehouse}`);
});

console.log('\nSaved to stock_control.json');
