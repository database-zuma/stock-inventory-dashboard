import json
import re

# Read files
html_path = 'dashboard_inventory.html'
stock_control_path = 'stock_control_v2.json'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

with open(stock_control_path, 'r', encoding='utf-8') as f:
    stock_control = json.load(f)

# Get month names
month_names = stock_control['salesPeriod']['monthNames']
wh = stock_control['warehouseSummary']

# New Stock Control View HTML
new_stock_control_view = '''        <!-- ==================== STOCK CONTROL VIEW ==================== -->
        <div class="view-container" id="stockcontrolView">
            <h2 style="margin-bottom:20px;color:#1f2937;">📊 Stock Control - Turnover Analysis</h2>
            <p style="color:#6b7280;margin-bottom:20px;">Data sales: ''' + ', '.join(month_names) + ''' (3 bulan terakhir)</p>

            <!-- Warehouse Stock Summary Cards -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:25px;">
                <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:16px;padding:20px;">
                    <h4 style="color:#b45309;margin-bottom:8px;">📦 WH Pusat (Jatim)</h4>
                    <div style="font-size:1.6rem;font-weight:700;color:#92400e;">''' + f'{wh["WHS"]:,}'.replace(',', '.') + '''</div>
                </div>
                <div style="background:linear-gradient(135deg,#dbeafe,#bfdbfe);border-radius:16px;padding:20px;">
                    <h4 style="color:#1d4ed8;margin-bottom:8px;">📦 WH Bali</h4>
                    <div style="font-size:1.6rem;font-weight:700;color:#1e40af;">''' + f'{wh["WHB"]:,}'.replace(',', '.') + '''</div>
                </div>
                <div style="background:linear-gradient(135deg,#dcfce7,#bbf7d0);border-radius:16px;padding:20px;">
                    <h4 style="color:#15803d;margin-bottom:8px;">📦 WH Jakarta</h4>
                    <div style="font-size:1.6rem;font-weight:700;color:#166534;">''' + f'{wh["WHJ"]:,}'.replace(',', '.') + '''</div>
                </div>
                <div style="background:linear-gradient(135deg,#f3e8ff,#e9d5ff);border-radius:16px;padding:20px;">
                    <h4 style="color:#7c3aed;margin-bottom:8px;">🏪 Total Stok Toko</h4>
                    <div style="font-size:1.6rem;font-weight:700;color:#6d28d9;">''' + f'{stock_control["totalStokToko"]:,}'.replace(',', '.') + '''</div>
                </div>
            </div>

            <!-- Filter Section -->
            <div style="display:flex;gap:15px;margin-bottom:20px;flex-wrap:wrap;">
                <div>
                    <label style="font-weight:600;margin-right:8px;">Gender:</label>
                    <select id="scGenderFilter" onchange="filterStockControlV2()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
                        <option value="all">Semua</option>
                        <option value="MEN">MEN</option>
                        <option value="LADIES">LADIES</option>
                        <option value="BOYS">BOYS</option>
                        <option value="GIRLS">GIRLS</option>
                        <option value="BABY">BABY</option>
                        <option value="JUNIOR">JUNIOR</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight:600;margin-right:8px;">Tier:</label>
                    <select id="scTierFilter" onchange="filterStockControlV2()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
                        <option value="all">Semua</option>
                        <option value="1">Tier 1</option>
                        <option value="2">Tier 2</option>
                        <option value="3">Tier 3</option>
                        <option value="4">Tier 4</option>
                        <option value="5">Tier 5</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight:600;margin-right:8px;">Search:</label>
                    <input type="text" id="scSearchInput" onkeyup="filterStockControlV2()" placeholder="Cari kode/artikel..." style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;width:200px;">
                </div>
                <div>
                    <label style="font-weight:600;margin-right:8px;">TO Status:</label>
                    <select id="scToFilter" onchange="filterStockControlV2()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
                        <option value="all">Semua</option>
                        <option value="critical">🔴 Critical (TO < 1)</option>
                        <option value="warning">🟡 Warning (TO 1-2)</option>
                        <option value="ok">🟢 OK (TO 2-4)</option>
                        <option value="overstock">🔵 Overstock (TO > 4)</option>
                    </select>
                </div>
            </div>

            <!-- Stock Control Table -->
            <div style="background:white;border-radius:16px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <div style="overflow-x:auto;">
                    <table id="stockControlTable" style="width:100%;border-collapse:collapse;font-size:0.8rem;">
                        <thead>
                            <tr style="background:#f8fafc;">
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;position:sticky;left:0;background:#f8fafc;">Kode</th>
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;">Article</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;">Series</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;">Gender</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;">Tier</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">''' + month_names[0][:3] + '''</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">''' + month_names[1][:3] + '''</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">''' + month_names[2][:3] + '''</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;background:#fef3c7;">Avg</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">WH Pusat</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">WH Bali</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">WH Jkt</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;background:#e0f2fe;">WH Total</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;">Stok Toko</th>
                                <th style="padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;background:#f3e8ff;">Global</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;">TW</th>
                                <th style="padding:10px;text-align:center;border-bottom:2px solid #e5e7eb;background:#fef2f2;">TO</th>
                            </tr>
                        </thead>
                        <tbody id="stockControlBody">
                        </tbody>
                    </table>
                </div>
                <div id="stockControlPagination" style="margin-top:15px;text-align:center;"></div>
            </div>

            <!-- Legend -->
            <div style="margin-top:15px;padding:15px;background:#f8fafc;border-radius:12px;font-size:0.85rem;">
                <strong>Keterangan TO (Turnover Overall):</strong>
                <span style="margin-left:15px;color:#ef4444;">🔴 Critical (< 1 bulan)</span>
                <span style="margin-left:15px;color:#f59e0b;">🟡 Warning (1-2 bulan)</span>
                <span style="margin-left:15px;color:#10b981;">🟢 OK (2-4 bulan)</span>
                <span style="margin-left:15px;color:#3b82f6;">🔵 Overstock (> 4 bulan)</span>
                <br><br>
                <strong>TW</strong> = WH Total / Avg Sales (berapa bulan stock WH bertahan)<br>
                <strong>TO</strong> = Global Stock / Avg Sales (berapa bulan total stock bertahan)
            </div>
        </div> <!-- End stockcontrolView -->'''

# Find and replace the stock control view
pattern = r'<!-- ==================== STOCK CONTROL VIEW ====================.*?<!-- End stockcontrolView -->'
html = re.sub(pattern, new_stock_control_view, html, flags=re.DOTALL)

# Update the JavaScript data and functions
# Remove old stockControlData
html = re.sub(r'const stockControlData = \{[^;]+\};', '', html)

# Remove old stock control functions
old_funcs = [
    'function filterStockControl',
    'function renderStoreControl',
    'function renderCriticalSku'
]

# Add new JavaScript
new_js = '''
        // ============ STOCK CONTROL V2 DATA ============
        const stockControlDataV2 = ''' + json.dumps(stock_control, ensure_ascii=False) + ''';

        let scCurrentPage = 1;
        const scPageSize = 50;

        // ============ STOCK CONTROL V2 FUNCTIONS ============
        function filterStockControlV2() {
            scCurrentPage = 1;
            renderStockControlV2();
        }

        function renderStockControlV2() {
            const tbody = document.getElementById('stockControlBody');
            if (!tbody) return;

            const genderFilter = document.getElementById('scGenderFilter')?.value || 'all';
            const tierFilter = document.getElementById('scTierFilter')?.value || 'all';
            const searchFilter = (document.getElementById('scSearchInput')?.value || '').toLowerCase();
            const toFilter = document.getElementById('scToFilter')?.value || 'all';

            let items = stockControlDataV2.items || [];

            // Apply filters
            items = items.filter(item => {
                if (genderFilter !== 'all' && item.gender !== genderFilter) return false;
                if (tierFilter !== 'all' && item.tier !== tierFilter) return false;
                if (searchFilter && !item.kodeKecil.toLowerCase().includes(searchFilter) &&
                    !(item.article || '').toLowerCase().includes(searchFilter)) return false;

                if (toFilter !== 'all') {
                    const to = item.to || 0;
                    if (toFilter === 'critical' && to >= 1) return false;
                    if (toFilter === 'warning' && (to < 1 || to >= 2)) return false;
                    if (toFilter === 'ok' && (to < 2 || to >= 4)) return false;
                    if (toFilter === 'overstock' && to < 4) return false;
                }

                return true;
            });

            // Pagination
            const totalPages = Math.ceil(items.length / scPageSize);
            const startIdx = (scCurrentPage - 1) * scPageSize;
            const pageItems = items.slice(startIdx, startIdx + scPageSize);

            // Render table
            tbody.innerHTML = pageItems.map(item => {
                const to = item.to || 0;
                let toColor = '#6b7280';
                let toBg = 'transparent';
                if (item.avgSales > 0) {
                    if (to < 1) { toColor = '#ef4444'; toBg = '#fef2f2'; }
                    else if (to < 2) { toColor = '#f59e0b'; toBg = '#fffbeb'; }
                    else if (to < 4) { toColor = '#10b981'; toBg = '#f0fdf4'; }
                    else { toColor = '#3b82f6'; toBg = '#eff6ff'; }
                }

                return `<tr style="border-bottom:1px solid #f3f4f6;">
                    <td style="padding:8px;font-family:monospace;font-weight:600;position:sticky;left:0;background:white;">${item.kodeKecil}</td>
                    <td style="padding:8px;font-size:0.75rem;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${item.article || ''}">${item.article || '-'}</td>
                    <td style="padding:8px;text-align:center;font-size:0.75rem;">${item.series || '-'}</td>
                    <td style="padding:8px;text-align:center;font-size:0.75rem;">${item.gender || '-'}</td>
                    <td style="padding:8px;text-align:center;">${item.tier || '-'}</td>
                    <td style="padding:8px;text-align:right;">${item.salesM1.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;">${item.salesM2.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;">${item.salesM3.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;background:#fef3c7;font-weight:600;">${item.avgSales.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;">${item.WHS.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;">${item.WHB.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;">${item.WHJ.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;background:#e0f2fe;font-weight:600;">${item.whTotal.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;">${item.stokToko.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;background:#f3e8ff;font-weight:600;">${item.globalStock.toLocaleString()}</td>
                    <td style="padding:8px;text-align:center;">${item.tw || '-'}</td>
                    <td style="padding:8px;text-align:center;background:${toBg};color:${toColor};font-weight:700;">${to || '-'}</td>
                </tr>`;
            }).join('');

            // Render pagination
            const pagination = document.getElementById('stockControlPagination');
            if (pagination) {
                pagination.innerHTML = `
                    <span style="margin-right:15px;">Showing ${startIdx + 1}-${Math.min(startIdx + scPageSize, items.length)} of ${items.length}</span>
                    <button onclick="scChangePage(-1)" ${scCurrentPage === 1 ? 'disabled' : ''} style="padding:5px 15px;margin-right:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;">← Prev</button>
                    <span>Page ${scCurrentPage} of ${totalPages}</span>
                    <button onclick="scChangePage(1)" ${scCurrentPage === totalPages ? 'disabled' : ''} style="padding:5px 15px;margin-left:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;">Next →</button>
                `;
            }
        }

        function scChangePage(delta) {
            scCurrentPage += delta;
            renderStockControlV2();
        }

'''

# Insert before INITIALIZATION
insert_marker = '        // ============ INITIALIZATION ============'
if insert_marker in html:
    html = html.replace(insert_marker, new_js + '\n' + insert_marker)

# Update switchView to use new function
old_switch_handler = """            // Initialize stock control when switching to that view
            if (view === 'stockcontrol') {
                setTimeout(filterStockControl, 100);
            }"""

new_switch_handler = """            // Initialize stock control when switching to that view
            if (view === 'stockcontrol') {
                setTimeout(filterStockControlV2, 100);
            }"""

html = html.replace(old_switch_handler, new_switch_handler)

# Also check for the other version
old_switch2 = "if (view === 'stockcontrol') {"
if old_switch2 in html and 'filterStockControlV2' not in html.split(old_switch2)[1][:100]:
    html = html.replace(
        "if (view === 'stockcontrol') {\n                filterStockControl();",
        "if (view === 'stockcontrol') {\n                filterStockControlV2();"
    )

# Write back
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print('Stock Control V2 updated successfully!')
print(f'Total items: {len(stock_control["items"])}')
print(f'Months: {", ".join(month_names)}')
