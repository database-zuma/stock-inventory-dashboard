import json

# Read files
html_path = 'dashboard_inventory.html'
stock_control_path = 'stock_control.json'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

with open(stock_control_path, 'r', encoding='utf-8') as f:
    stock_control = json.load(f)

# Check if already added
if 'stockcontrolView' in html:
    print('Stock Control View already exists!')
else:
    # Add Stock Control View after brokensize view
    old_marker = '        </div> <!-- End brokensizeView -->'

    stock_control_view = '''        </div> <!-- End brokensizeView -->

        <!-- ==================== STOCK CONTROL VIEW ==================== -->
        <div class="view-container" id="stockcontrolView">
            <h2 style="margin-bottom:20px;color:#1f2937;">📊 Stock Control - Turnover Analysis</h2>
            <p style="color:#6b7280;margin-bottom:20px;">Data berdasarkan sales ''' + stock_control['salesPeriod']['start'] + ' s/d ' + stock_control['salesPeriod']['end'] + ' (' + str(stock_control['salesPeriod']['days']) + ''' hari)</p>

            <!-- Warehouse Filter -->
            <div style="margin-bottom:20px;">
                <label style="font-weight:600;margin-right:10px;">Filter Warehouse:</label>
                <select id="stockControlWhFilter" onchange="filterStockControl()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
                    <option value="all">Semua</option>
                    <option value="WHB">WHB - Warehouse Bali</option>
                    <option value="WHJ">WHJ - Warehouse Jakarta</option>
                    <option value="WHS">WHS - Warehouse Pusat (Jatim)</option>
                    <option value="none">Tanpa Warehouse</option>
                </select>
            </div>

            <!-- Store Stock Control Table -->
            <div style="background:white;border-radius:16px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin-bottom:20px;">
                <h3 style="margin-bottom:15px;color:#1f2937;">🏪 Store Turnover Analysis</h3>
                <p style="font-size:0.85rem;color:#6b7280;margin-bottom:15px;">
                    <span style="color:#ef4444;">● CRITICAL</span> (DOS &lt; 14 hari) |
                    <span style="color:#f59e0b;">● WARNING</span> (14-30 hari) |
                    <span style="color:#10b981;">● OK</span> (30-60 hari) |
                    <span style="color:#3b82f6;">● OVERSTOCK</span> (&gt; 60 hari)
                </p>
                <div style="overflow-x:auto;">
                    <table id="storeControlTable" style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                        <thead>
                            <tr style="background:#f8fafc;">
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">Store</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Area</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">WH</th>
                                <th style="padding:12px;text-align:right;border-bottom:2px solid #e5e7eb;">Stock</th>
                                <th style="padding:12px;text-align:right;border-bottom:2px solid #e5e7eb;">Sales/Day</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">DOS</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Status</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Critical</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Warning</th>
                            </tr>
                        </thead>
                        <tbody id="storeControlBody">
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Critical SKU Table -->
            <div style="background:white;border-radius:16px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <h3 style="margin-bottom:15px;color:#1f2937;">🚨 Critical SKU - Perlu Restock (DOS &lt; 14 hari)</h3>
                <div style="overflow-x:auto;max-height:500px;overflow-y:auto;">
                    <table id="criticalSkuTable" style="width:100%;border-collapse:collapse;font-size:0.85rem;">
                        <thead style="position:sticky;top:0;background:#f8fafc;">
                            <tr>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">SKU</th>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">Product</th>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">Store</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Stock</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Sales/Day</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">DOS</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Restock From</th>
                            </tr>
                        </thead>
                        <tbody id="criticalSkuBody">
                        </tbody>
                    </table>
                </div>
            </div>
        </div> <!-- End stockcontrolView -->'''

    html = html.replace(old_marker, stock_control_view)
    print('Stock Control View added!')

# Add the JavaScript data and functions
stock_control_js = '''
        // ============ STOCK CONTROL DATA ============
        const stockControlData = ''' + json.dumps(stock_control, ensure_ascii=False) + ''';

        // ============ STOCK CONTROL FUNCTIONS ============
        function filterStockControl() {
            const whFilter = document.getElementById('stockControlWhFilter').value;
            renderStoreControl(whFilter);
            renderCriticalSku(whFilter);
        }

        function renderStoreControl(whFilter = 'all') {
            const tbody = document.getElementById('storeControlBody');
            if (!tbody) return;

            let stores = stockControlData.storeControl || [];

            if (whFilter === 'none') {
                stores = stores.filter(s => !s.warehouse);
            } else if (whFilter !== 'all') {
                stores = stores.filter(s => s.warehouse === whFilter);
            }

            tbody.innerHTML = stores.map(s => {
                const statusColor = s.avgDos < 14 ? '#ef4444' :
                                   s.avgDos < 30 ? '#f59e0b' :
                                   s.avgDos < 60 ? '#10b981' : '#3b82f6';
                const statusText = s.avgDos < 14 ? 'CRITICAL' :
                                  s.avgDos < 30 ? 'WARNING' :
                                  s.avgDos < 60 ? 'OK' : 'OVERSTOCK';
                const statusBg = s.avgDos < 14 ? '#fef2f2' :
                                s.avgDos < 30 ? '#fffbeb' :
                                s.avgDos < 60 ? '#f0fdf4' : '#eff6ff';

                return `<tr style="border-bottom:1px solid #f3f4f6;">
                    <td style="padding:10px;font-weight:500;">${s.store}</td>
                    <td style="padding:10px;text-align:center;">${s.area}</td>
                    <td style="padding:10px;text-align:center;font-weight:600;">${s.warehouse || '-'}</td>
                    <td style="padding:10px;text-align:right;">${s.totalStock.toLocaleString()}</td>
                    <td style="padding:10px;text-align:right;">${s.totalDailyRate.toFixed(1)}</td>
                    <td style="padding:10px;text-align:center;font-weight:700;color:${statusColor};">${s.avgDos}</td>
                    <td style="padding:10px;text-align:center;">
                        <span style="background:${statusBg};color:${statusColor};padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:600;">
                            ${statusText}
                        </span>
                    </td>
                    <td style="padding:10px;text-align:center;color:#ef4444;font-weight:600;">${s.critical > 0 ? s.critical : '-'}</td>
                    <td style="padding:10px;text-align:center;color:#f59e0b;font-weight:600;">${s.warning > 0 ? s.warning : '-'}</td>
                </tr>`;
            }).join('');
        }

        function renderCriticalSku(whFilter = 'all') {
            const tbody = document.getElementById('criticalSkuBody');
            if (!tbody) return;

            let skus = (stockControlData.skuControl || []).filter(s => s.dos < 14 && s.warehouse);

            if (whFilter === 'none') {
                skus = [];
            } else if (whFilter !== 'all') {
                skus = skus.filter(s => s.warehouse === whFilter);
            }

            // Limit to 100
            skus = skus.slice(0, 100);

            tbody.innerHTML = skus.map(s => {
                return `<tr style="border-bottom:1px solid #f3f4f6;">
                    <td style="padding:10px;font-family:monospace;font-weight:500;">${s.sku}</td>
                    <td style="padding:10px;font-size:0.8rem;">${s.name || '-'}</td>
                    <td style="padding:10px;">${s.store}</td>
                    <td style="padding:10px;text-align:center;font-weight:600;">${s.currentStock}</td>
                    <td style="padding:10px;text-align:center;">${s.dailyRate}</td>
                    <td style="padding:10px;text-align:center;color:#ef4444;font-weight:700;">${s.dos}</td>
                    <td style="padding:10px;text-align:center;">
                        <span style="background:#dbeafe;color:#1d4ed8;padding:4px 12px;border-radius:20px;font-size:0.75rem;font-weight:600;">
                            ${s.warehouse}
                        </span>
                    </td>
                </tr>`;
            }).join('');

            if (skus.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="padding:20px;text-align:center;color:#9ca3af;">Tidak ada SKU critical untuk filter ini</td></tr>';
            }
        }

'''

# Check if JS already added
if 'stockControlData' not in html:
    # Find position to insert - before INITIALIZATION section
    insert_marker = '        // ============ INITIALIZATION ============'
    if insert_marker in html:
        html = html.replace(insert_marker, stock_control_js + '\n' + insert_marker)
        print('Stock Control JavaScript added!')
    else:
        print('Warning: Could not find INITIALIZATION marker')
else:
    print('Stock Control JavaScript already exists!')

# Update switchView function to handle stockcontrol
if "view === 'stockcontrol'" not in html or 'filterStockControl' not in html:
    # Find switchView function and add stockcontrol handling
    old_switch = "currentView = view;"
    new_switch = """currentView = view;

            // Initialize stock control when switching to that view
            if (view === 'stockcontrol') {
                setTimeout(filterStockControl, 100);
            }"""

    if old_switch in html and "setTimeout(filterStockControl" not in html:
        html = html.replace(old_switch, new_switch, 1)  # Only replace first occurrence
        print('SwitchView updated for stockcontrol!')

# Write back
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print('\nDone! Stock Control feature complete.')
