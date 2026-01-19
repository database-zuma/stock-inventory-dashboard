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

# Create the complete Stock Control section (HTML + JavaScript)
stock_control_html = '''        <!-- ==================== STOCK CONTROL VIEW ==================== -->
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
                    <select id="scGenderFilter" onchange="renderStockControlTable()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
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
                    <select id="scTierFilter" onchange="renderStockControlTable()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
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
                    <input type="text" id="scSearchInput" onkeyup="renderStockControlTable()" placeholder="Cari kode/artikel..." style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;width:200px;">
                </div>
                <div>
                    <label style="font-weight:600;margin-right:8px;">TO Status:</label>
                    <select id="scToFilter" onchange="renderStockControlTable()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
                        <option value="all">Semua</option>
                        <option value="critical">Critical (TO &lt; 1)</option>
                        <option value="warning">Warning (TO 1-2)</option>
                        <option value="ok">OK (TO 2-4)</option>
                        <option value="overstock">Overstock (TO &gt; 4)</option>
                    </select>
                </div>
            </div>

            <!-- Stock Control Table -->
            <div style="background:white;border-radius:16px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <div style="overflow-x:auto;">
                    <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
                        <thead>
                            <tr style="background:#f8fafc;">
                                <th style="padding:10px;text-align:left;border-bottom:2px solid #e5e7eb;">Kode</th>
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
                        <tbody id="scTableBody">
                        </tbody>
                    </table>
                </div>
                <div id="scPagination" style="margin-top:15px;text-align:center;"></div>
            </div>

            <!-- Legend -->
            <div style="margin-top:15px;padding:15px;background:#f8fafc;border-radius:12px;font-size:0.85rem;">
                <strong>Keterangan TO (Turnover Overall):</strong>
                <span style="margin-left:15px;color:#ef4444;">● Critical (&lt; 1 bulan)</span>
                <span style="margin-left:15px;color:#f59e0b;">● Warning (1-2 bulan)</span>
                <span style="margin-left:15px;color:#10b981;">● OK (2-4 bulan)</span>
                <span style="margin-left:15px;color:#3b82f6;">● Overstock (&gt; 4 bulan)</span>
                <br><br>
                <strong>TW</strong> = WH Total / Avg Sales (berapa bulan stock WH bertahan)<br>
                <strong>TO</strong> = Global Stock / Avg Sales (berapa bulan total stock bertahan)
            </div>
        </div> <!-- End stockcontrolView -->'''

# JavaScript for Stock Control
stock_control_js = '''
        // ============ STOCK CONTROL V2 ============
        const scItems = ''' + json.dumps(stock_control['items'], ensure_ascii=False) + ''';
        let scPage = 1;
        const scPerPage = 50;

        function renderStockControlTable() {
            const tbody = document.getElementById('scTableBody');
            if (!tbody) return;

            const gender = document.getElementById('scGenderFilter')?.value || 'all';
            const tier = document.getElementById('scTierFilter')?.value || 'all';
            const search = (document.getElementById('scSearchInput')?.value || '').toLowerCase();
            const toStatus = document.getElementById('scToFilter')?.value || 'all';

            let filtered = scItems.filter(item => {
                if (gender !== 'all' && item.gender !== gender) return false;
                if (tier !== 'all' && item.tier !== tier) return false;
                if (search && !item.kodeKecil.toLowerCase().includes(search) &&
                    !(item.article || '').toLowerCase().includes(search)) return false;
                if (toStatus !== 'all') {
                    const to = item.to || 0;
                    if (toStatus === 'critical' && to >= 1) return false;
                    if (toStatus === 'warning' && (to < 1 || to >= 2)) return false;
                    if (toStatus === 'ok' && (to < 2 || to >= 4)) return false;
                    if (toStatus === 'overstock' && to < 4) return false;
                }
                return true;
            });

            const totalPages = Math.ceil(filtered.length / scPerPage);
            if (scPage > totalPages) scPage = 1;
            const start = (scPage - 1) * scPerPage;
            const pageData = filtered.slice(start, start + scPerPage);

            tbody.innerHTML = pageData.map(item => {
                const to = item.to || 0;
                let toColor = '#6b7280', toBg = 'transparent';
                if (item.avgSales > 0) {
                    if (to < 1) { toColor = '#ef4444'; toBg = '#fef2f2'; }
                    else if (to < 2) { toColor = '#f59e0b'; toBg = '#fffbeb'; }
                    else if (to < 4) { toColor = '#10b981'; toBg = '#f0fdf4'; }
                    else { toColor = '#3b82f6'; toBg = '#eff6ff'; }
                }
                return `<tr style="border-bottom:1px solid #f3f4f6;">
                    <td style="padding:8px;font-family:monospace;font-weight:600;">${item.kodeKecil}</td>
                    <td style="padding:8px;font-size:0.75rem;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${item.article||''}">${item.article||'-'}</td>
                    <td style="padding:8px;text-align:center;font-size:0.75rem;">${item.series||'-'}</td>
                    <td style="padding:8px;text-align:center;font-size:0.75rem;">${item.gender||'-'}</td>
                    <td style="padding:8px;text-align:center;">${item.tier||'-'}</td>
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
                    <td style="padding:8px;text-align:center;">${item.tw||'-'}</td>
                    <td style="padding:8px;text-align:center;background:${toBg};color:${toColor};font-weight:700;">${to||'-'}</td>
                </tr>`;
            }).join('');

            document.getElementById('scPagination').innerHTML = `
                <span style="margin-right:15px;">Showing ${start+1}-${Math.min(start+scPerPage,filtered.length)} of ${filtered.length}</span>
                <button onclick="scPage--;renderStockControlTable()" ${scPage===1?'disabled':''} style="padding:5px 15px;margin-right:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;">Prev</button>
                <span>Page ${scPage} of ${totalPages||1}</span>
                <button onclick="scPage++;renderStockControlTable()" ${scPage>=totalPages?'disabled':''} style="padding:5px 15px;margin-left:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;">Next</button>
            `;
        }

'''

# Find and replace stock control view
old_view_pattern = r'<!-- ==================== STOCK CONTROL VIEW ====================.*?<!-- End stockcontrolView -->'
if re.search(old_view_pattern, html, re.DOTALL):
    html = re.sub(old_view_pattern, stock_control_html, html, flags=re.DOTALL)
    print('Stock Control View replaced')
else:
    # Insert after brokensize view
    insert_after = '</div> <!-- End brokensizeView -->'
    if insert_after in html:
        html = html.replace(insert_after, insert_after + '\n\n' + stock_control_html)
        print('Stock Control View inserted')

# Remove old stock control JS
html = re.sub(r'// ============ STOCK CONTROL DATA ============.*?// ============ STOCK CONTROL FUNCTIONS ============.*?function filterStockControl\(\).*?\n        \}', '', html, flags=re.DOTALL)
html = re.sub(r'// ============ STOCK CONTROL V2 ============.*?function renderStockControlTable\(\).*?\n        \}', '', html, flags=re.DOTALL)

# Add new JS before INITIALIZATION
init_marker = '        // ============ INITIALIZATION ============'
if init_marker in html:
    html = html.replace(init_marker, stock_control_js + '\n' + init_marker)
    print('Stock Control JS added')

# Update switchView to call renderStockControlTable
if "view === 'stockcontrol'" in html:
    # Remove old handlers
    html = re.sub(r"if \(view === 'stockcontrol'\) \{\s*setTimeout\([^)]+\);\s*\}", "", html)
    html = re.sub(r"if \(view === 'stockcontrol'\) \{\s*filterStockControl[^}]+\}", "", html)

# Add new handler in switchView
old_switch = "currentView = view;"
new_switch = """currentView = view;
            if (view === 'stockcontrol') { renderStockControlTable(); }"""
if 'renderStockControlTable' not in html.split(old_switch)[1][:200]:
    html = html.replace(old_switch, new_switch, 1)
    print('switchView updated')

# Write
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\\nDone! {len(stock_control["items"])} items')
