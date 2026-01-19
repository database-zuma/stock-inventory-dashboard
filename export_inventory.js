// Export Inventory Data untuk Claude.ai Web
const fs = require('fs');
const path = require('path');

// Load data from dashboard HTML
const htmlPath = path.join(__dirname, 'dashboard_inventory.html');
const html = fs.readFileSync(htmlPath, 'utf8');

const allDataMatch = html.match(/const allData = (\{[\s\S]*?\});[\s\n]*const allStores/);
if (!allDataMatch) {
    console.error('Could not find allData');
    process.exit(1);
}

const allData = JSON.parse(allDataMatch[1]);

// Create summary data (smaller file)
const summary = {
    generated: new Date().toISOString(),
    stats: {
        totalSku: 0,
        totalRetailStock: 0,
        totalWarehouseStock: 0
    },
    byGender: {},
    byArea: {},
    skuList: []
};

// Process DDD entity (main)
const ddd = allData.DDD;

if (ddd.retail) {
    for (const item of ddd.retail) {
        summary.stats.totalSku++;
        summary.stats.totalRetailStock += item.total || 0;

        // Gender
        const gender = item.gender || 'OTHER';
        summary.byGender[gender] = (summary.byGender[gender] || 0) + (item.total || 0);

        // Collect SKU with store breakdown
        const storeBreakdown = {};
        if (item.store_stock) {
            for (const [store, qty] of Object.entries(item.store_stock)) {
                if (qty > 0) {
                    // Determine area
                    const storeLower = store.toLowerCase();
                    let area = 'Other';
                    if (storeLower.includes('bali') || storeLower.includes('gatsu') || storeLower.includes('dalung') ||
                        storeLower.includes('singaraja') || storeLower.includes('tabanan') || storeLower.includes('gianyar') ||
                        storeLower.includes('klungkung') || storeLower.includes('jembrana') || storeLower.includes('kapal') ||
                        storeLower.includes('seririt') || storeLower.includes('bangli') || storeLower.includes('peliatan') ||
                        storeLower.includes('kesiman') || storeLower.includes('panjer') || storeLower.includes('pemogan') ||
                        storeLower.includes('penatih') || storeLower.includes('peguyangan') || storeLower.includes('monang') ||
                        storeLower.includes('kedonganan') || storeLower.includes('uluwatu') || storeLower.includes('bajra') ||
                        storeLower.includes('karangasem') || storeLower.includes('level 21') || storeLower.includes('lippo bali') ||
                        storeLower.includes('living world') || storeLower.includes('galeria') || storeLower.includes('icon')) {
                        area = 'Bali';
                    } else if (storeLower.includes('pluit') || storeLower.includes('puri') || storeLower.includes('moi') ||
                               storeLower.includes('bintaro')) {
                        area = 'Jakarta';
                    } else if (storeLower.includes('galaxy') || storeLower.includes('tunjungan') || storeLower.includes('ptc') ||
                               storeLower.includes('royal') || storeLower.includes('matos') || storeLower.includes('cito') ||
                               storeLower.includes('olympic') || storeLower.includes('sidoarjo') || storeLower.includes('gresik') ||
                               storeLower.includes('mojokerto') || storeLower.includes('batu')) {
                        area = 'Jawa Timur';
                    } else if (storeLower.includes('lombok') || storeLower.includes('mataram') || storeLower.includes('epicentrum')) {
                        area = 'Lombok';
                    } else if (storeLower.includes('manado')) {
                        area = 'Sulawesi';
                    } else if (storeLower.includes('batam') || storeLower.includes('nagoya')) {
                        area = 'Batam';
                    } else if (storeLower.includes('ska') || storeLower.includes('sumatera')) {
                        area = 'Sumatera';
                    }

                    summary.byArea[area] = (summary.byArea[area] || 0) + qty;
                    storeBreakdown[store] = qty;
                }
            }
        }

        summary.skuList.push({
            sku: item.sku,
            kode: item.kode_kecil,
            name: item.name,
            gender: item.gender,
            series: item.series,
            size: item.size,
            tier: item.tier,
            total: item.total,
            stores: storeBreakdown
        });
    }
}

// Warehouse stock
if (ddd.warehouse) {
    for (const item of ddd.warehouse) {
        summary.stats.totalWarehouseStock += item.total || 0;
    }
}

// Sort SKU by total stock descending
summary.skuList.sort((a, b) => b.total - a.total);

// Write full data
fs.writeFileSync(
    path.join(__dirname, 'inventory_data.json'),
    JSON.stringify(summary, null, 2)
);

console.log('Exported to inventory_data.json');
console.log('Total SKU:', summary.stats.totalSku);
console.log('File size:', (JSON.stringify(summary).length / 1024 / 1024).toFixed(2), 'MB');

// Also create a smaller summary without individual SKU details
const smallSummary = {
    generated: summary.generated,
    stats: summary.stats,
    byGender: summary.byGender,
    byArea: summary.byArea,
    topSku: summary.skuList.slice(0, 100) // Top 100 only
};

fs.writeFileSync(
    path.join(__dirname, 'inventory_summary.json'),
    JSON.stringify(smallSummary, null, 2)
);

console.log('\nAlso exported inventory_summary.json (smaller, top 100 SKU only)');
