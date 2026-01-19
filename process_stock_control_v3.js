// Process Stock Control V3 - With Area Filter
const fs = require('fs');
const path = require('path');

// ============ STORE TO AREA MAPPING ============
const storeAreaMap = {
    // BALI & LOMBOK
    'zuma dalung': 'BALI',
    'zuma kedonganan': 'BALI',
    'zuma kesiman': 'BALI',
    'zuma panjer': 'BALI',
    'zuma penatih': 'BALI',
    'zuma bajra': 'BALI',
    'zuma bangli': 'BALI',
    'zuma batubulan': 'BALI',
    'zuma gianyar': 'BALI',
    'zuma jembrana': 'BALI',
    'zuma kapal': 'BALI',
    'zuma karangasem': 'BALI',
    'zuma klungkung': 'BALI',
    'zuma lebah peliatan': 'BALI',
    'zuma level 21': 'BALI',
    'zuma lippo bali': 'BALI',
    'zuma mall bali galeria': 'BALI',
    'zuma mall bali icon': 'BALI',
    'zuma mataram lombok': 'BALI',
    'zuma monang maning': 'BALI',
    'zuma monkey forest ubud': 'BALI',
    'zuma peguyangan': 'BALI',
    'zuma peliatan': 'BALI',
    'zuma pemogan': 'BALI',
    'zuma seririt': 'BALI',
    'zuma singaraja': 'BALI',
    'zuma tabanan': 'BALI',
    'zuma tanah lot': 'BALI',
    'zuma uluwatu': 'BALI',

    // JAKARTA
    'zuma epicentrum': 'JAKARTA',
    'zuma bintaro xchange': 'JAKARTA',
    'zuma lippo mall puri': 'JAKARTA',
    'zuma living world': 'JAKARTA',
    'zuma moi': 'JAKARTA',
    'zuma pluit village': 'JAKARTA',

    // JATIM (Jawa Timur)
    'zuma city of tomorrow mall': 'JATIM',
    'zuma galaxy mall': 'JATIM',
    'zuma lippo sidoarjo': 'JATIM',
    'zuma ptc': 'JATIM',
    'zuma royal plaza': 'JATIM',
    'zuma tunjungan plaza': 'JATIM',
    'zuma sunrise mall': 'JATIM',
    'zuma mall olympic garden': 'JATIM',
    'zuma lippo batu': 'JATIM',
    'zuma matos': 'JATIM',
    'zuma icon mall gresik': 'JATIM',

    // OTHER
    'zuma mega mall manado': 'OTHER',
    'zuma nagoya hill batam': 'OTHER',
    'zuma ska mall': 'OTHER'
};

function getStoreArea(storeName) {
    const normalized = storeName.toLowerCase().trim();
    for (const [key, area] of Object.entries(storeAreaMap)) {
        if (normalized.includes(key) || key.includes(normalized)) {
            return area;
        }
    }
    return 'OTHER';
}

// ============ LOAD SALES DATA ============
const csvPath = path.join(__dirname, 'order-detail-ab0b5e97289247159e6fbd29ccf90d5b.csv');
const csvContent = fs.readFileSync(csvPath, 'utf8');

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

function getKodeKecil(sku) {
    return sku.replace(/Z\d+$/, '');
}

// ============ AGGREGATE SALES BY KODE KECIL, MONTH, AND AREA ============
const salesByKode = {};

productSales.forEach(row => {
    const date = row['Tanggal Pesanan']?.substring(0, 10);
    const sku = row.Sku?.trim();
    const qty = parseInt(row.Jumlah) || 0;
    const store = row.Toko || '';
    if (!date || !sku || qty <= 0) return;

    const kodeKecil = getKodeKecil(sku);
    const month = date.substring(0, 7);
    const area = getStoreArea(store);

    if (!salesByKode[kodeKecil]) {
        salesByKode[kodeKecil] = {
            kodeKecil,
            months: {},
            byArea: { BALI: {}, JAKARTA: {}, JATIM: {}, OTHER: {} },
            totalSales: 0
        };
    }

    // Total sales
    if (!salesByKode[kodeKecil].months[month]) {
        salesByKode[kodeKecil].months[month] = 0;
    }
    salesByKode[kodeKecil].months[month] += qty;
    salesByKode[kodeKecil].totalSales += qty;

    // Sales by area
    if (!salesByKode[kodeKecil].byArea[area][month]) {
        salesByKode[kodeKecil].byArea[area][month] = 0;
    }
    salesByKode[kodeKecil].byArea[area][month] += qty;
});

console.log(`\nUnique KODE KECIL: ${Object.keys(salesByKode).length}`);

// ============ AGGREGATE INVENTORY BY KODE KECIL AND AREA ============
const inventoryByKode = {};

// Store area mapping for inventory
const storeInventoryAreaMap = {};

// Process ALL entities (DDD, LJBB, UBB, MBB)
const entities = ['DDD', 'LJBB', 'UBB', 'MBB'];

entities.forEach(entity => {
    // Process retail data
    const retailData = inventoryData[entity]?.retail || [];
    retailData.forEach(item => {
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
                stokTokoByArea: { BALI: 0, JAKARTA: 0, JATIM: 0, OTHER: 0 },
                WHB: 0,
                WHJ: 0,
                WHS: 0
            };
        }

        // Update article info if empty
        if (!inventoryByKode[kodeKecil].article && item.name) {
            inventoryByKode[kodeKecil].article = item.name?.replace(/,\s*\d+\/?\d*$/, '').replace(/,\s*(SIZE\s*)?\d+$/, '').trim() || '';
        }
        if (!inventoryByKode[kodeKecil].gender && item.gender) {
            inventoryByKode[kodeKecil].gender = item.gender;
        }
        if (!inventoryByKode[kodeKecil].series && item.series) {
            inventoryByKode[kodeKecil].series = item.series;
        }
        if (!inventoryByKode[kodeKecil].tier && item.tier) {
            inventoryByKode[kodeKecil].tier = item.tier;
        }

        // Sum store stock by area
        if (item.store_stock) {
            Object.entries(item.store_stock).forEach(([store, qty]) => {
                if (qty > 0 && !store.toLowerCase().includes('warehouse')) {
                    inventoryByKode[kodeKecil].stokToko += qty;
                    const area = getStoreArea(store);
                    inventoryByKode[kodeKecil].stokTokoByArea[area] += qty;
                }
            });
        }
    });

    // Process warehouse data
    const warehouseData = inventoryData[entity]?.warehouse || [];
    warehouseData.forEach(item => {
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
                stokTokoByArea: { BALI: 0, JAKARTA: 0, JATIM: 0, OTHER: 0 },
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

    console.log(`Processed entity: ${entity} - Retail: ${retailData.length}, Warehouse: ${warehouseData.length}`);
});

// ============ GET MONTHS ============
const allMonths = new Set();
Object.values(salesByKode).forEach(s => {
    Object.keys(s.months).forEach(m => allMonths.add(m));
});
const sortedMonths = Array.from(allMonths).sort();
console.log(`Sales months: ${sortedMonths.join(', ')}`);

const last3Months = sortedMonths.slice(-3);
console.log(`Using last 3 months: ${last3Months.join(', ')}`);

// ============ BUILD STOCK CONTROL LIST ============
const stockControlList = [];
const allKodes = new Set([...Object.keys(salesByKode), ...Object.keys(inventoryByKode)]);

allKodes.forEach(kodeKecil => {
    const sales = salesByKode[kodeKecil] || {
        months: {},
        byArea: { BALI: {}, JAKARTA: {}, JATIM: {}, OTHER: {} },
        totalSales: 0
    };
    const inventory = inventoryByKode[kodeKecil] || {
        article: '', gender: '', series: '', tier: '',
        stokToko: 0,
        stokTokoByArea: { BALI: 0, JAKARTA: 0, JATIM: 0, OTHER: 0 },
        WHB: 0, WHJ: 0, WHS: 0
    };

    // Total sales per month
    const salesM1 = sales.months[last3Months[0]] || 0;
    const salesM2 = sales.months[last3Months[1]] || 0;
    const salesM3 = sales.months[last3Months[2]] || 0;
    const avgSales = Math.round((salesM1 + salesM2 + salesM3) / 3);

    // Sales per area per month
    const salesByArea = {};
    ['BALI', 'JAKARTA', 'JATIM', 'OTHER'].forEach(area => {
        const areaData = sales.byArea[area] || {};
        const m1 = areaData[last3Months[0]] || 0;
        const m2 = areaData[last3Months[1]] || 0;
        const m3 = areaData[last3Months[2]] || 0;
        salesByArea[area] = {
            m1, m2, m3,
            avg: Math.round((m1 + m2 + m3) / 3)
        };
    });

    // Stock
    const whTotal = inventory.WHB + inventory.WHJ + inventory.WHS;
    const globalStock = inventory.stokToko + whTotal;

    // Turnover
    const tw = avgSales > 0 ? (whTotal / avgSales).toFixed(1) : 0;
    const to = avgSales > 0 ? (globalStock / avgSales).toFixed(1) : 0;

    stockControlList.push({
        kodeKecil,
        article: inventory.article,
        series: inventory.series,
        gender: inventory.gender,
        tier: inventory.tier,
        // Total sales
        salesM1, salesM2, salesM3, avgSales,
        // Sales by area
        salesBali: salesByArea.BALI,
        salesJakarta: salesByArea.JAKARTA,
        salesJatim: salesByArea.JATIM,
        salesOther: salesByArea.OTHER,
        // Warehouse stock
        WHS: inventory.WHS,
        WHB: inventory.WHB,
        WHJ: inventory.WHJ,
        whTotal,
        // Store stock
        stokToko: inventory.stokToko,
        stokTokoBali: inventory.stokTokoByArea.BALI,
        stokTokoJakarta: inventory.stokTokoByArea.JAKARTA,
        stokTokoJatim: inventory.stokTokoByArea.JATIM,
        stokTokoOther: inventory.stokTokoByArea.OTHER,
        // Global
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
    stokTokoSummary: {
        BALI: stockControlList.reduce((sum, i) => sum + i.stokTokoBali, 0),
        JAKARTA: stockControlList.reduce((sum, i) => sum + i.stokTokoJakarta, 0),
        JATIM: stockControlList.reduce((sum, i) => sum + i.stokTokoJatim, 0),
        OTHER: stockControlList.reduce((sum, i) => sum + i.stokTokoOther, 0),
        TOTAL: stockControlList.reduce((sum, i) => sum + i.stokToko, 0)
    },
    totalGlobalStock: stockControlList.reduce((sum, i) => sum + i.globalStock, 0),
    items: stockControlList
};

fs.writeFileSync(
    path.join(__dirname, 'stock_control_v3.json'),
    JSON.stringify(output, null, 2)
);

// Print summary
console.log('\n=== SUMMARY ===');
console.log(`Total items: ${stockControlList.length}`);
console.log(`\nWarehouse Stock:`);
console.log(`  WH Pusat (Jatim): ${output.warehouseSummary.WHS.toLocaleString()}`);
console.log(`  WH Bali: ${output.warehouseSummary.WHB.toLocaleString()}`);
console.log(`  WH Jakarta: ${output.warehouseSummary.WHJ.toLocaleString()}`);
console.log(`\nStore Stock by Area:`);
console.log(`  Bali & Lombok: ${output.stokTokoSummary.BALI.toLocaleString()}`);
console.log(`  Jakarta: ${output.stokTokoSummary.JAKARTA.toLocaleString()}`);
console.log(`  Jawa Timur: ${output.stokTokoSummary.JATIM.toLocaleString()}`);
console.log(`  Other: ${output.stokTokoSummary.OTHER.toLocaleString()}`);
console.log(`  Total: ${output.stokTokoSummary.TOTAL.toLocaleString()}`);

console.log(`\nSaved to stock_control_v3.json`);
