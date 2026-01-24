#!/usr/bin/env python3
"""
Generate Dashboard HTML yang fetch data dari Supabase
Menggantikan embedded data dengan API calls

Run: python generate_dashboard_supabase.py
Output: dashboard_inventory.html (versi Supabase)
"""

import os
import base64
from pathlib import Path

# Supabase Config (akan di-embed di JavaScript)
SUPABASE_URL = "https://voypxpibaujymwmhavjl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZveXB4cGliYXVqeW13bWhhdmpsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkxMTk1MDgsImV4cCI6MjA4NDY5NTUwOH0.g9MZabcH10dPsknEv1KbGpGDS071SlsPqpFRt_jXQxQ"

# Load logos as base64
def load_logo_base64(filename):
    """Load image file and convert to base64 data URI"""
    try:
        filepath = Path(__file__).parent / filename
        if filepath.exists():
            with open(filepath, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
                return f"data:image/png;base64,{data}"
    except Exception as e:
        print(f"Warning: Could not load logo {filename}: {e}")
    return ""

# Load all logos
LOGO_ZUMA = load_logo_base64("ZUMA_FINAL LOGO_UPDATED-07.png")
LOGO_DDD = load_logo_base64("b.png")
LOGO_LJBB = load_logo_base64("ljbb.png")
LOGO_MBB = load_logo_base64("mbb.png")
LOGO_UBB = load_logo_base64("a.png")

# Generate HTML
def generate_html():
    """Generate complete dashboard HTML with Supabase integration"""

    html = f'''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoring Stock Retail & Warehouse - Zuma Indonesia</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #6366f1; --primary-light: #818cf8; --secondary: #ec4899;
            --success: #10b981; --warning: #f59e0b; --danger: #ef4444; --info: #06b6d4;
            --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --card-bg: rgba(255, 255, 255, 0.98); --shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Poppins', sans-serif;
            background: #ffffff;
            min-height: 100vh; color: #1f2937;
        }}
        .header {{
            background: linear-gradient(135deg, #1f2937 0%, #111827 50%, #0f172a 100%); padding: 20px 40px; color: white;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3); position: sticky; top: 0; z-index: 100;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .header h1 {{ font-size: 1.6rem; font-weight: 700; }}
        .header p {{ opacity: 0.9; font-size: 0.85rem; }}
        .header .date {{ font-size: 0.8rem; opacity: 0.85; text-align: right; }}
        .container {{ max-width: 1700px; margin: 0 auto; padding: 25px; }}

        /* Loading Overlay */
        .loading-overlay {{
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); z-index: 9999;
            display: flex; align-items: center; justify-content: center;
            flex-direction: column;
        }}
        .loading-spinner {{
            width: 60px; height: 60px;
            border: 6px solid #f3f3f3;
            border-top: 6px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .loading-text {{
            margin-top: 20px; font-size: 1.2rem; color: white;
            font-weight: 600;
        }}
        .loading-detail {{
            margin-top: 10px; font-size: 0.9rem; color: #ddd;
        }}

        /* Entity Pills */
        .entity-section {{
            display: flex; gap: 15px; align-items: center;
            flex-wrap: wrap; margin-bottom: 20px;
        }}
        .entity-pills {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .entity-pill {{
            padding: 10px 20px; border-radius: 25px; font-size: 0.85rem;
            font-weight: 600; cursor: pointer; transition: all 0.3s ease;
            border: 2px solid transparent; display: flex; align-items: center; gap: 8px;
        }}
        .entity-pill.ddd {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: 2px solid #b91c1c; }}
        .entity-pill.ljbb {{ background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; border: 2px solid #1d4ed8; }}
        .entity-pill.mbb {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; border: 2px solid #6d28d9; }}
        .entity-pill.ubb {{ background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: 2px solid #b45309; }}
        .entity-pill.active {{ transform: scale(1.08); box-shadow: 0 6px 20px rgba(0,0,0,0.4); }}
        .entity-pill .logo {{ width: 20px; height: 20px; object-fit: contain; }}
        .entity-pill .count {{
            background: rgba(255,255,255,0.5); padding: 2px 8px;
            border-radius: 10px; font-size: 0.75rem;
        }}
    </style>
</head>
<body>
    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="loading-spinner"></div>
        <div class="loading-text">Memuat Data...</div>
        <div class="loading-detail" id="loadingDetail">Menghubungkan ke database...</div>
    </div>

    <!-- Header -->
    <div class="header">
        <div>
            <h1>📊 Monitoring Stock Retail & Warehouse</h1>
            <p>ZUMA Indonesia - Real-time Dashboard</p>
        </div>
        <div class="date" id="currentDate"></div>
    </div>

    <div class="container">
        <div class="entity-section">
            <div class="entity-pills" id="entityPills">
                <!-- Will be populated by JavaScript -->
            </div>
        </div>

        <div id="dashboardContent">
            <p style="text-align:center; padding: 40px; color: #9ca3af;">
                Loading dashboard...
            </p>
        </div>
    </div>

    <script>
        // Supabase Configuration
        const SUPABASE_URL = '{SUPABASE_URL}';
        const SUPABASE_KEY = '{SUPABASE_KEY}';

        // Logos (base64 encoded)
        const LOGOS = {{
            zuma: '{LOGO_ZUMA}',
            ddd: '{LOGO_DDD}',
            ljbb: '{LOGO_LJBB}',
            mbb: '{LOGO_MBB}',
            ubb: '{LOGO_UBB}'
        }};

        // Global data store
        let allData = null;
        let salesSummary = null;
        let salesDetail = null;

        // Helper: Fetch from Supabase
        async function fetchFromSupabase(table, params = {{}}) {{
            try {{
                const queryString = new URLSearchParams(params).toString();
                const url = `${{SUPABASE_URL}}/rest/v1/${{table}}${{queryString ? '?' + queryString : ''}}`;

                const response = await fetch(url, {{
                    headers: {{
                        'apikey': SUPABASE_KEY,
                        'Authorization': `Bearer ${{SUPABASE_KEY}}`
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

        // Update loading status
        function updateLoadingStatus(message) {{
            const detail = document.getElementById('loadingDetail');
            if (detail) detail.textContent = message;
        }}

        // Hide loading overlay
        function hideLoading() {{
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) {{
                overlay.style.opacity = '0';
                setTimeout(() => overlay.style.display = 'none', 300);
            }}
        }}

        // Load all data from Supabase
        async function loadAllData() {{
            try {{
                updateLoadingStatus('Memuat data inventory...');
                const inventoryData = await fetchFromSupabase('inventory');
                console.log(`✅ Loaded ${{inventoryData.length}} inventory items`);

                updateLoadingStatus('Memuat data sales summary...');
                salesSummary = await fetchFromSupabase('sales_summary');
                console.log(`✅ Loaded ${{salesSummary.length}} sales summary records`);

                updateLoadingStatus('Memuat data sales detail...');
                salesDetail = await fetchFromSupabase('sales_detail', {{
                    limit: 10000,
                    order: 'tanggal.desc'
                }});
                console.log(`✅ Loaded ${{salesDetail.length}} sales transactions`);

                // Transform inventory data to match old format
                updateLoadingStatus('Memproses data...');
                allData = transformInventoryData(inventoryData);

                updateLoadingStatus('Menampilkan dashboard...');
                renderDashboard();

                hideLoading();
            }} catch (error) {{
                console.error('Error loading data:', error);
                updateLoadingStatus('❌ Gagal memuat data. Silakan refresh halaman.');
            }}
        }}

        // Transform Supabase data to match old dashboard format
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

                // Parse store_stock JSON string
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

        // Render dashboard (placeholder - will be expanded)
        function renderDashboard() {{
            // Set current date
            const dateEl = document.getElementById('currentDate');
            if (dateEl) {{
                const now = new Date();
                dateEl.textContent = now.toLocaleDateString('id-ID', {{
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                }});
            }}

            // Render entity pills
            renderEntityPills();

            // Render dashboard content
            const content = document.getElementById('dashboardContent');
            content.innerHTML = `
                <div style="text-align: center; padding: 60px 20px;">
                    <h2 style="color: #1f2937; margin-bottom: 20px;">✅ Dashboard Connected to Supabase!</h2>
                    <p style="color: #6b7280; font-size: 1.1rem; margin-bottom: 30px;">
                        Data berhasil dimuat dari database cloud. Dashboard lengkap sedang dalam proses finalisasi.
                    </p>
                    <div style="background: #f0fdf4; border: 2px solid #10b981; border-radius: 12px; padding: 20px; max-width: 600px; margin: 0 auto;">
                        <h3 style="color: #059669; margin-bottom: 15px;">📊 Data Summary:</h3>
                        <div style="text-align: left; color: #047857;">
                            <p><strong>Inventory Items:</strong> ${{Object.values(allData).reduce((sum, entity) => sum + entity.warehouse.length + entity.retail.length, 0).toLocaleString()}} items</p>
                            <p><strong>Sales Summary:</strong> ${{salesSummary.length.toLocaleString()}} SKUs</p>
                            <p><strong>Sales Transactions:</strong> ${{salesDetail.length.toLocaleString()}} transactions</p>
                            <p style="margin-top: 15px; font-size: 0.9rem;">
                                <strong>File Size:</strong> HTML ~50KB (vs 24MB sebelumnya) ✨
                            </p>
                        </div>
                    </div>
                </div>
            `;
        }}

        // Render entity pills
        function renderEntityPills() {{
            const pillsContainer = document.getElementById('entityPills');
            if (!pillsContainer || !allData) return;

            const entities = ['DDD', 'LJBB', 'MBB', 'UBB'];
            const entityClasses = {{
                'DDD': 'ddd',
                'LJBB': 'ljbb',
                'MBB': 'mbb',
                'UBB': 'ubb'
            }};

            const logoMap = {{
                'DDD': LOGOS.ddd,
                'LJBB': LOGOS.ljbb,
                'MBB': LOGOS.mbb,
                'UBB': LOGOS.ubb
            }};

            pillsContainer.innerHTML = entities.map(entity => {{
                const data = allData[entity] || {{ warehouse: [], retail: [] }};
                const count = data.warehouse.length + data.retail.length;
                const logo = logoMap[entity];

                return `
                    <div class="entity-pill ${{entityClasses[entity]}} active">
                        ${{logo ? `<img src="${{logo}}" class="logo" alt="${{entity}}">` : ''}}
                        <span>${{entity}}</span>
                        <span class="count">${{count}}</span>
                    </div>
                `;
            }}).join('');
        }}

        // Initialize dashboard on page load
        document.addEventListener('DOMContentLoaded', () => {{
            console.log('🚀 Starting Supabase Dashboard...');
            loadAllData();
        }});
    </script>
</body>
</html>
'''

    return html

def main():
    print("="*60)
    print("Generating Supabase Dashboard...")
    print("="*60)

    html_content = generate_html()

    output_file = os.path.join(os.path.dirname(__file__), 'dashboard_inventory.html')

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    file_size = os.path.getsize(output_file)
    print(f"✅ Dashboard generated: {output_file}")
    print(f"📊 File size: {file_size / 1024:.1f} KB (vs 24MB before!)")
    print("="*60)
    print("\nNext steps:")
    print("1. Open dashboard_inventory.html in browser")
    print("2. Check if data loads from Supabase")
    print("3. If successful, full dashboard features will be added")
    print()

if __name__ == '__main__':
    main()
