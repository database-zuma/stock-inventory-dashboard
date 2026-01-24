#!/usr/bin/env python3
"""
Generate Complete ZUMA Dashboard dengan Supabase + Authentication
Mengambil struktur dari dashboard lama, tapi data dari Supabase
"""

import os
import base64
from pathlib import Path

# Supabase Config
SUPABASE_URL = "https://voypxpibaujymwmhavjl.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZveXB4cGliYXVqeW13bWhhdmpsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxMTk1MDgsImV4cCI6MjA4NDY5NTUwOH0.g9MZabcH10dPsknEv1KbGpGDS071SlsPqpFRt_jXQxQ"

def load_logo_base64(filename):
    """Load image and convert to base64"""
    try:
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            with open(filepath, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{data}"
    except:
        pass
    return ""

# Load logos
LOGO_ZUMA = load_logo_base64("ZUMA_FINAL LOGO_UPDATED-07.png")
LOGO_DDD = load_logo_base64("b.png")
LOGO_LJBB = load_logo_base64("ljbb.png")
LOGO_MBB = load_logo_base64("mbb.png")
LOGO_UBB = load_logo_base64("a.png")

def extract_dashboard_template():
    """Extract HTML/CSS/JS structure from original dashboard"""

    backup_file = Path(__file__).parent / "dashboard_inventory_backup.html"

    if not backup_file.exists():
        print("Error: dashboard_inventory_backup.html not found!")
        return None

    print("📂 Reading original dashboard...")

    # Read line by line to find where embedded data starts
    with open(backup_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    # Find where const allData starts (around line 1378)
    data_start_idx = None
    for i, line in enumerate(lines):
        if 'const allData = {' in line or 'const allData={' in line:
            data_start_idx = i
            print(f"  ✅ Found embedded data at line {i+1}")
            break

    if data_start_idx is None:
        print("  ⚠️  Could not find embedded data, using full file")
        # Extract HTML/CSS part (before </script>)
        template_lines = []
        for line in lines:
            template_lines.append(line)
            if '</body>' in line or '</html>' in line:
                break
        return ''.join(template_lines[:1377])  # Up to script tag

    # Extract everything BEFORE embedded data
    template_before = ''.join(lines[:data_start_idx])

    # Find where embedded data ENDS and functions start
    # Look for common function patterns
    func_start_idx = None
    for i in range(data_start_idx + 1, min(data_start_idx + 100, len(lines))):
        line = lines[i].strip()
        if line.startswith('function ') or line.startswith('// Dashboard'):
            func_start_idx = i
            print(f"  ✅ Found functions start at line {i+1}")
            break

    if func_start_idx is None:
        # If can't find, assume data is small and functions start soon
        func_start_idx = data_start_idx + 20

    # Extract everything AFTER embedded data (functions till end)
    template_after = ''.join(lines[func_start_idx:])

    return (template_before, template_after)

def generate_complete_dashboard():
    """Generate complete dashboard HTML"""

    print("\n" + "="*60)
    print("🚀 GENERATING COMPLETE ZUMA DASHBOARD")
    print("="*60)

    # Extract template
    result = extract_dashboard_template()
    if result is None:
        print("❌ Failed to extract template")
        return False

    template_before, template_after = result

    print("\n📝 Building new dashboard with Supabase...")

    # Build complete HTML
    html = template_before

    # Add Supabase configuration and data loading
    html += f'''
        // ========================================
        // SUPABASE CONFIGURATION & AUTHENTICATION
        // ========================================

        const SUPABASE_URL = '{SUPABASE_URL}';
        const SUPABASE_ANON_KEY = '{SUPABASE_ANON_KEY}';

        // Logos (base64)
        const LOGOS = {{
            zuma: '{LOGO_ZUMA}',
            ddd: '{LOGO_DDD}',
            ljbb: '{LOGO_LJBB}',
            mbb: '{LOGO_MBB}',
            ubb: '{LOGO_UBB}'
        }};

        // Initialize Supabase client
        const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

        // Check authentication
        let currentUser = null;

        async function checkAuth() {{
            const {{ data: {{ session }} }} = await supabase.auth.getSession();
            if (!session) {{
                // Not logged in, redirect to login
                window.location.href = 'login.html';
                return false;
            }}
            currentUser = session.user;
            return true;
        }}

        // Logout function
        async function logout() {{
            await supabase.auth.signOut();
            window.location.href = 'login.html';
        }}

        // Fetch data from Supabase
        async function fetchFromSupabase(table, params = {{}}) {{
            try {{
                const queryString = new URLSearchParams(params).toString();
                const url = `${{SUPABASE_URL}}/rest/v1/${{table}}${{queryString ? '?' + queryString : ''}}`;

                const response = await fetch(url, {{
                    headers: {{
                        'apikey': SUPABASE_ANON_KEY,
                        'Authorization': `Bearer ${{SUPABASE_ANON_KEY}}`
                    }}
                }});

                if (!response.ok) {{
                    throw new Error(`HTTP error! status: ${{response.status}}`);
                }}

                return await response.json();
            }} catch (error) {{
                console.error(`Error fetching from ${{table}}:`, error);
                throw error;
            }}
        }}

        // Transform Supabase inventory data to dashboard format
        function transformInventoryData(inventoryData) {{
            const transformed = {{}};

            inventoryData.forEach(item => {{
                const entity = item.entity;
                const type = item.type;

                if (!transformed[entity]) {{
                    transformed[entity] = {{
                        warehouse: [],
                        retail: []
                    }};
                }}

                // Parse store_stock JSON
                let storeStock = {{}};
                try {{
                    storeStock = typeof item.store_stock === 'string'
                        ? JSON.parse(item.store_stock)
                        : item.store_stock || {{}};
                }} catch (e) {{
                    console.error('Error parsing store_stock:', e);
                }}

                transformed[entity][type].push({{
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
                }});
            }});

            return transformed;
        }}

        // Load all data from Supabase
        let allData = null;
        let salesSummaryData = null;
        let salesDetailData = null;

        async function loadAllData() {{
            try {{
                console.log('Loading data from Supabase...');

                // Show loading overlay
                showLoadingOverlay('Memuat data dari database...');

                // Fetch inventory data
                updateLoadingStatus('Memuat data inventory...');
                const inventoryData = await fetchFromSupabase('inventory');
                console.log(`✅ Loaded ${{inventoryData.length}} inventory items`);

                // Transform to dashboard format
                allData = transformInventoryData(inventoryData);

                // Fetch sales summary
                updateLoadingStatus('Memuat data sales summary...');
                salesSummaryData = await fetchFromSupabase('sales_summary');
                console.log(`✅ Loaded ${{salesSummaryData.length}} sales summary records`);

                // Fetch sales detail
                updateLoadingStatus('Memuat data sales detail...');
                salesDetailData = await fetchFromSupabase('sales_detail', {{
                    limit: 10000,
                    order: 'tanggal.desc'
                }});
                console.log(`✅ Loaded ${{salesDetailData.length}} sales transactions`);

                // Hide loading
                hideLoadingOverlay();

                console.log('✅ All data loaded successfully');
                return true;
            }} catch (error) {{
                console.error('Error loading data:', error);
                alert('Gagal memuat data dari database. Silakan refresh halaman.');
                return false;
            }}
        }}

        // Loading overlay functions
        function showLoadingOverlay(message) {{
            let overlay = document.getElementById('loadingOverlay');
            if (!overlay) {{
                overlay = document.createElement('div');
                overlay.id = 'loadingOverlay';
                overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:99999;display:flex;flex-direction:column;align-items:center;justify-content:center;';
                overlay.innerHTML = `
                    <div style="width:60px;height:60px;border:6px solid #f3f3f3;border-top:6px solid #667eea;border-radius:50%;animation:spin 1s linear infinite;"></div>
                    <div id="loadingText" style="color:white;margin-top:20px;font-size:1.2rem;font-weight:600;"></div>
                    <style>@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}</style>
                `;
                document.body.appendChild(overlay);
            }}
            overlay.style.display = 'flex';
            updateLoadingStatus(message);
        }}

        function updateLoadingStatus(message) {{
            const loadingText = document.getElementById('loadingText');
            if (loadingText) loadingText.textContent = message;
        }}

        function hideLoadingOverlay() {{
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {{
                overlay.style.opacity = '0';
                setTimeout(() => overlay.style.display = 'none', 300);
            }}
        }}

        // Initialize dashboard on page load
        async function initDashboard() {{
            // Check authentication first
            const isAuth = await checkAuth();
            if (!isAuth) return;

            // Load data
            const loaded = await loadAllData();
            if (!loaded) return;

            // Initialize dashboard (call existing init functions)
            if (typeof updateEntityCounts === 'function') {{
                updateEntityCounts();
            }}
            if (typeof selectEntity === 'function') {{
                selectEntity('DDD');
            }}
            if (typeof switchTab === 'function') {{
                switchTab('inventory');
            }}
        }}

        // Run when page loads
        document.addEventListener('DOMContentLoaded', initDashboard);

        // Add logout button to header
        document.addEventListener('DOMContentLoaded', () => {{
            setTimeout(() => {{
                const header = document.querySelector('.header');
                if (header && currentUser) {{
                    const logoutBtn = document.createElement('button');
                    logoutBtn.textContent = '🚪 Logout';
                    logoutBtn.style.cssText = 'padding:8px 16px;background:#ef4444;color:white;border:none;border-radius:8px;cursor:pointer;font-weight:600;';
                    logoutBtn.onclick = logout;
                    header.appendChild(logoutBtn);
                }}
            }}, 1000);
        }});

'''

    # Add the rest of the JavaScript functions from original dashboard
    html += template_after

    # Save to index.html
    output_file = Path(__file__).parent / "index.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    file_size = os.path.getsize(output_file)

    print(f"\n✅ Dashboard generated: {output_file}")
    print(f"📊 File size: {file_size / 1024:.1f} KB (vs 24MB before!)")
    print("\n" + "="*60)
    print("✅ COMPLETE! Dashboard siap digunakan!")
    print("="*60)
    print("\nNext steps:")
    print("1. Open login.html in browser")
    print("2. Login with your Supabase user credentials")
    print("3. Dashboard akan otomatis load data dari Supabase")
    print("\nUntuk deploy ke Vercel:")
    print("- Baca README_DEPLOYMENT.md untuk instruksi lengkap")
    print()

    return True

if __name__ == '__main__':
    try:
        generate_complete_dashboard()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
