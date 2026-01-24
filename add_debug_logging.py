#!/usr/bin/env python3
"""
Add debug logging to see what's happening with data transformation
"""

# Read index.html
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find transformInventoryData function and add logging after it
old_transform_end = '''                transformed[entity][type].push({
                    sku: item.sku,
                    kode_kecil: item.kode_kecil,
                    name: item.name,
                    size: item.size,
                    category: item.category,
                    gender: item.gender,
                    series: item.series,
                    tipe: item.tipe,
                    tier: item.tier,
                    color: item.color,
                    total: item.total,
                    store_stock: storeStock,
                    entity: entity,
                    type: type
                });
            });

            return transformed;
        }'''

new_transform_end = '''                transformed[entity][type].push({
                    sku: item.sku,
                    kode_kecil: item.kode_kecil,
                    name: item.name,
                    size: item.size,
                    category: item.category,
                    gender: item.gender,
                    series: item.series,
                    tipe: item.tipe,
                    tier: item.tier,
                    color: item.color,
                    total: item.total,
                    store_stock: storeStock,
                    entity: entity,
                    type: type
                });
            });

            // Debug logging
            console.log('🔍 Transformed data structure:', Object.keys(transformed));
            for (const entity in transformed) {
                const warehouseCount = transformed[entity].warehouse ? transformed[entity].warehouse.length : 0;
                const retailCount = transformed[entity].retail ? transformed[entity].retail.length : 0;
                console.log(`  ${entity}: ${warehouseCount} warehouse + ${retailCount} retail = ${warehouseCount + retailCount} total`);
            }

            return transformed;
        }'''

content = content.replace(old_transform_end, new_transform_end)

# Also add logging after allData assignment
old_alldata = '''                // Transform to dashboard format
                allData = transformInventoryData(inventoryData);'''

new_alldata = '''                // Transform to dashboard format
                allData = transformInventoryData(inventoryData);
                console.log('🎯 allData assigned:', allData ? 'YES' : 'NO', allData ? Object.keys(allData) : 'NULL');'''

content = content.replace(old_alldata, new_alldata)

# Write back
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Added debug logging!")
print("📝 Changes:")
print("  - Added logging after data transformation")
print("  - Shows entity counts (warehouse + retail)")
print("  - Shows allData assignment status")
