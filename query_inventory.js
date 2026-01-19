// Query Inventory ZUMA - Claude Code Tool
// Usage: node query_inventory.js <command> [args]

const fs = require('fs');
const path = require('path');

// Load data from dashboard HTML
function loadData() {
    const htmlPath = path.join(__dirname, 'dashboard_inventory.html');
    const html = fs.readFileSync(htmlPath, 'utf8');

    // Extract allData JSON
    const allDataMatch = html.match(/const allData = (\{[\s\S]*?\});[\s\n]*const allStores/);
    const allStoresMatch = html.match(/const allStores = (\{[\s\S]*?\});[\s\n]*const storeAreaMap/);
    const maxStockMatch = html.match(/const maxStockMap = (\{[\s\S]*?\});[\s\n]/);

    if (!allDataMatch) {
        console.error('Could not find allData in HTML');
        process.exit(1);
    }

    return {
        allData: JSON.parse(allDataMatch[1]),
        allStores: allStoresMatch ? JSON.parse(allStoresMatch[1]) : {},
        maxStockMap: maxStockMatch ? JSON.parse(maxStockMatch[1]) : {}
    };
}

// Search SKU across all stores
function searchSku(sku, data) {
    const results = [];
    const searchTerm = sku.toLowerCase();

    for (const [entity, entityData] of Object.entries(data.allData)) {
        // Search in retail
        if (entityData.retail) {
            for (const item of entityData.retail) {
                if (item.sku.toLowerCase().includes(searchTerm) ||
                    item.kode_kecil?.toLowerCase().includes(searchTerm)) {
                    const stores = [];
                    if (item.store_stock) {
                        for (const [store, qty] of Object.entries(item.store_stock)) {
                            if (qty > 0) {
                                stores.push({ store, qty });
                            }
                        }
                    }
                    if (stores.length > 0) {
                        results.push({
                            entity,
                            type: 'retail',
                            sku: item.sku,
                            name: item.name,
                            gender: item.gender,
                            series: item.series,
                            size: item.size,
                            tier: item.tier,
                            total: item.total,
                            stores: stores.sort((a, b) => b.qty - a.qty)
                        });
                    }
                }
            }
        }

        // Search in warehouse
        if (entityData.warehouse) {
            for (const item of entityData.warehouse) {
                if (item.sku.toLowerCase().includes(searchTerm) ||
                    item.kode_kecil?.toLowerCase().includes(searchTerm)) {
                    const stores = [];
                    if (item.store_stock) {
                        for (const [store, qty] of Object.entries(item.store_stock)) {
                            if (qty > 0) {
                                stores.push({ store, qty });
                            }
                        }
                    }
                    if (stores.length > 0) {
                        results.push({
                            entity,
                            type: 'warehouse',
                            sku: item.sku,
                            name: item.name,
                            gender: item.gender,
                            series: item.series,
                            size: item.size,
                            tier: item.tier,
                            total: item.total,
                            stores: stores.sort((a, b) => b.qty - a.qty)
                        });
                    }
                }
            }
        }
    }

    return results;
}

// Get stock by area
function getStockByArea(area, type, data) {
    const results = [];
    const searchArea = area.toLowerCase();

    for (const [entity, entityData] of Object.entries(data.allData)) {
        const items = type === 'warehouse' ? entityData.warehouse : entityData.retail;
        if (!items) continue;

        for (const item of items) {
            if (item.store_stock) {
                for (const [store, qty] of Object.entries(item.store_stock)) {
                    const storeLower = store.toLowerCase();
                    let storeArea = '';

                    // Determine area
                    if (storeLower.includes('bali') || storeLower.includes('gatsu')) storeArea = 'bali';
                    else if (storeLower.includes('pluit') || storeLower.includes('puri') || storeLower.includes('moi')) storeArea = 'jakarta';
                    else if (storeLower.includes('pusat') || storeLower.includes('surabaya') || storeLower.includes('sidoarjo') || storeLower.includes('gresik') || storeLower.includes('mojokerto')) storeArea = 'jawa timur';

                    if (storeArea === searchArea && qty > 0) {
                        results.push({
                            entity,
                            sku: item.sku,
                            name: item.name,
                            store,
                            qty
                        });
                    }
                }
            }
        }
    }

    return results;
}

// Get store summary
function getStoreSummary(storeName, data) {
    const results = {
        store: storeName,
        totalSku: 0,
        totalStock: 0,
        items: []
    };
    const searchStore = storeName.toLowerCase();

    for (const [entity, entityData] of Object.entries(data.allData)) {
        const allItems = [...(entityData.retail || []), ...(entityData.warehouse || [])];

        for (const item of allItems) {
            if (item.store_stock) {
                for (const [store, qty] of Object.entries(item.store_stock)) {
                    if (store.toLowerCase().includes(searchStore) && qty !== 0) {
                        results.totalSku++;
                        results.totalStock += qty;
                        results.items.push({
                            sku: item.sku,
                            name: item.name,
                            size: item.size,
                            qty
                        });
                    }
                }
            }
        }
    }

    results.items.sort((a, b) => b.qty - a.qty);
    return results;
}

// Get overall stats
function getStats(data) {
    const stats = {
        totalSku: 0,
        totalStock: 0,
        byEntity: {},
        byGender: {},
        lowStock: 0,
        outOfStock: 0,
        highStock: 0
    };

    for (const [entity, entityData] of Object.entries(data.allData)) {
        stats.byEntity[entity] = { retail: 0, warehouse: 0 };

        if (entityData.retail) {
            for (const item of entityData.retail) {
                stats.totalSku++;
                stats.totalStock += item.total || 0;
                stats.byEntity[entity].retail += item.total || 0;

                // Gender stats
                const gender = item.gender || 'OTHER';
                stats.byGender[gender] = (stats.byGender[gender] || 0) + (item.total || 0);

                // Stock status
                if (item.total === 0) stats.outOfStock++;
                else if (item.total < 10) stats.lowStock++;
                else if (item.total > 100) stats.highStock++;
            }
        }

        if (entityData.warehouse) {
            for (const item of entityData.warehouse) {
                stats.byEntity[entity].warehouse += item.total || 0;
            }
        }
    }

    return stats;
}

// Main
const command = process.argv[2];
const args = process.argv.slice(3);

try {
    const data = loadData();

    switch (command) {
        case 'search':
        case 'sku':
            if (!args[0]) {
                console.log('Usage: node query_inventory.js search <sku>');
                process.exit(1);
            }
            const skuResults = searchSku(args[0], data);
            console.log(JSON.stringify(skuResults, null, 2));
            break;

        case 'store':
            if (!args[0]) {
                console.log('Usage: node query_inventory.js store <store_name>');
                process.exit(1);
            }
            const storeResults = getStoreSummary(args.join(' '), data);
            console.log(JSON.stringify(storeResults, null, 2));
            break;

        case 'area':
            if (!args[0]) {
                console.log('Usage: node query_inventory.js area <area_name> [retail|warehouse]');
                process.exit(1);
            }
            const areaResults = getStockByArea(args[0], args[1] || 'retail', data);
            console.log(JSON.stringify(areaResults.slice(0, 50), null, 2));
            break;

        case 'stats':
            const stats = getStats(data);
            console.log(JSON.stringify(stats, null, 2));
            break;

        default:
            console.log(`
ZUMA Inventory Query Tool
=========================
Commands:
  search <sku>     - Search SKU across all stores (e.g., search z2mf01z24)
  store <name>     - Get store stock summary (e.g., store singaraja)
  area <name>      - Get stock by area (e.g., area bali)
  stats            - Get overall statistics

Examples:
  node query_inventory.js search z2mf01z24
  node query_inventory.js store "zuma singaraja"
  node query_inventory.js area "jawa timur"
  node query_inventory.js stats
            `);
    }
} catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
}
