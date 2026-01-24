#!/usr/bin/env python3
"""
Fix timing issue: loadAllData should wait for authentication
"""

# Read index.html
with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace initDashboard function
old_init = '''        // Initialize dashboard on page load
        async function initDashboard() {
            // Check authentication first
            const isAuth = await checkAuth();
            if (!isAuth) return;

            // Load data
            const loaded = await loadAllData();
            if (!loaded) return;

            // Initialize dashboard (call existing init functions)
            if (typeof updateEntityCounts === 'function') {
                updateEntityCounts();
            }
            if (typeof selectEntity === 'function') {
                selectEntity('DDD');
            }
            if (typeof switchTab === 'function') {
                switchTab('inventory');
            }
        }'''

new_init = '''        // Initialize dashboard on page load
        async function initDashboard() {
            try {
                // Check authentication first and WAIT for session
                console.log('🔐 Checking authentication...');
                const isAuth = await checkAuth();
                if (!isAuth) {
                    console.log('❌ Not authenticated, redirecting to login');
                    return;
                }

                console.log('✅ Authentication successful');

                // Small delay to ensure session is fully loaded
                await new Promise(resolve => setTimeout(resolve, 500));

                // Load data
                console.log('📊 Loading data from Supabase...');
                const loaded = await loadAllData();
                if (!loaded) {
                    console.log('❌ Failed to load data');
                    return;
                }

                console.log('✅ Data loaded successfully');

                // Initialize dashboard (call existing init functions)
                if (typeof updateEntityCounts === 'function') {
                    updateEntityCounts();
                }
                if (typeof selectEntity === 'function') {
                    selectEntity('DDD');
                }
                if (typeof switchTab === 'function') {
                    switchTab('inventory');
                }

                console.log('✅ Dashboard initialized');
            } catch (error) {
                console.error('❌ Error initializing dashboard:', error);
                alert('Gagal memuat dashboard. Silakan refresh halaman.');
            }
        }'''

content = content.replace(old_init, new_init)

# Write back
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed timing issue!")
print("📝 Changes:")
print("  - Added console logging for debugging")
print("  - Added 500ms delay after auth to ensure session ready")
print("  - Added error handling with try-catch")
print("  - Added user-friendly error message")
