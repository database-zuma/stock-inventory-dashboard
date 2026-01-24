#!/usr/bin/env python3
"""
Create proper updateEntityCounts function that actually updates UI
"""

# Read index.html
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace updateEntityCounts function
old_function = '''        function updateEntityCounts() {
            // Entity counts removed from UI - function kept for compatibility
        }'''

new_function = '''        function updateEntityCounts() {
            // Update entity pill counts based on allData
            if (!allData) {
                console.log('⚠️  allData not loaded yet');
                return;
            }

            console.log('🔄 Updating entity counts in UI...');

            // Count items for each entity
            const entities = ['DDD', 'LJBB', 'MBB', 'UBB'];

            entities.forEach(entity => {
                const entityData = allData[entity];
                if (!entityData) {
                    console.log(`  ${entity}: not found in allData`);
                    return;
                }

                const warehouseCount = entityData.warehouse ? entityData.warehouse.length : 0;
                const retailCount = entityData.retail ? entityData.retail.length : 0;
                const totalCount = warehouseCount + retailCount;

                console.log(`  ${entity}: ${totalCount} items`);

                // Find entity pill and update count
                const pill = document.querySelector(`.entity-pill[data-entity="${entity}"]`);
                if (pill) {
                    // Find or create count element
                    let countElem = pill.querySelector('.count');
                    if (!countElem) {
                        countElem = document.createElement('span');
                        countElem.className = 'count';
                        pill.appendChild(countElem);
                    }

                    // Update count text
                    countElem.textContent = `${totalCount} items`;

                    console.log(`    Updated ${entity} pill to ${totalCount} items`);
                }
            });

            console.log('✅ Entity counts updated');
        }'''

content = content.replace(old_function, new_function)

# Write back
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Created proper updateEntityCounts function!")
print("📝 Changes:")
print("  - Updates entity pill counts from allData")
print("  - Counts warehouse + retail items per entity")
print("  - Updates .count element in each pill")
print("  - Adds console logging for debugging")
