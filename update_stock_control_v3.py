import json
import re

# Read files
html_path = 'dashboard_inventory.html'
stock_control_path = 'stock_control_v3.json'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

with open(stock_control_path, 'r', encoding='utf-8') as f:
    stock_control = json.load(f)

# Get data
month_names = stock_control['salesPeriod']['monthNames']
wh = stock_control['warehouseSummary']
stokToko = stock_control['stokTokoSummary']

# New filter HTML - add Area filter
area_filter_html = '''<div>
                    <label style="font-weight:600;margin-right:8px;color:#1f2937;">Area:</label>
                    <select id="scAreaFilter" onchange="scPage=1;renderStockControlTable()" style="padding:8px 16px;border-radius:8px;border:1px solid #e5e7eb;">
                        <option value="all">Semua Area</option>
                        <option value="BALI">Bali & Lombok</option>
                        <option value="JAKARTA">Jakarta</option>
                        <option value="JATIM">Jawa Timur</option>
                        <option value="OTHER">Lainnya</option>
                    </select>
                </div>
                <div>
                    <label style="font-weight:600;margin-right:8px;color:#1f2937;">Gender:</label>'''

# Replace Gender filter to add Area filter before it
html = html.replace(
    '''<div>
                    <label style="font-weight:600;margin-right:8px;color:#1f2937;">Gender:</label>''',
    area_filter_html
)
print('Area filter added')

# Update scItems with new data
old_scitems_pattern = r'const scItems = \[.*?\];'
new_scitems = 'const scItems = ' + json.dumps(stock_control['items'], ensure_ascii=False) + ';'

if re.search(old_scitems_pattern, html, re.DOTALL):
    html = re.sub(old_scitems_pattern, new_scitems, html, flags=re.DOTALL)
    print('scItems updated with v3 data')
else:
    print('ERROR: scItems not found')

# New renderStockControlTable function with area logic
new_render_function = '''function renderStockControlTable() {
            const tbody = document.getElementById('scTableBody');
            if (!tbody) return;

            const area = document.getElementById('scAreaFilter')?.value || 'all';
            const gender = document.getElementById('scGenderFilter')?.value || 'all';
            const tier = document.getElementById('scTierFilter')?.value || 'all';
            const search = (document.getElementById('scSearchInput')?.value || '').toLowerCase();
            const twStatus = document.getElementById('scTwFilter')?.value || 'all';
            const toStatus = document.getElementById('scToFilter')?.value || 'all';

            let filtered = scItems.filter(item => {
                if (gender !== 'all' && item.gender !== gender) return false;
                if (tier !== 'all' && item.tier !== tier) return false;
                if (search && !item.kodeKecil.toLowerCase().includes(search) &&
                    !(item.article || '').toLowerCase().includes(search)) return false;

                // Get data based on area
                let avgSales, whStock, tokoStock, globalStock;
                if (area === 'all') {
                    avgSales = item.avgSales;
                    whStock = item.whTotal;
                    tokoStock = item.stokToko;
                    globalStock = item.globalStock;
                } else if (area === 'BALI') {
                    avgSales = item.salesBali?.avg || 0;
                    whStock = item.WHB || 0;
                    tokoStock = item.stokTokoBali || 0;
                    globalStock = whStock + tokoStock;
                } else if (area === 'JAKARTA') {
                    avgSales = item.salesJakarta?.avg || 0;
                    whStock = item.WHJ || 0;
                    tokoStock = item.stokTokoJakarta || 0;
                    globalStock = whStock + tokoStock;
                } else if (area === 'JATIM') {
                    avgSales = item.salesJatim?.avg || 0;
                    whStock = item.WHS || 0;
                    tokoStock = item.stokTokoJatim || 0;
                    globalStock = whStock + tokoStock;
                } else {
                    avgSales = item.salesOther?.avg || 0;
                    whStock = 0;
                    tokoStock = item.stokTokoOther || 0;
                    globalStock = tokoStock;
                }

                const tw = avgSales > 0 ? whStock / avgSales : 0;
                const to = avgSales > 0 ? globalStock / avgSales : 0;

                if (twStatus !== 'all') {
                    if (twStatus === 'critical' && tw >= 1) return false;
                    if (twStatus === 'warning' && (tw < 1 || tw >= 2)) return false;
                    if (twStatus === 'ok' && (tw < 2 || tw >= 4)) return false;
                    if (twStatus === 'overstock' && tw < 4) return false;
                }
                if (toStatus !== 'all') {
                    if (toStatus === 'critical' && to >= 1) return false;
                    if (toStatus === 'warning' && (to < 1 || to >= 2)) return false;
                    if (toStatus === 'ok' && (to < 2 || to >= 4)) return false;
                    if (toStatus === 'overstock' && to < 4) return false;
                }
                return true;
            });

            // Sort by avgSales based on area
            filtered.sort((a, b) => {
                let avgA, avgB;
                if (area === 'all') {
                    avgA = a.avgSales; avgB = b.avgSales;
                } else if (area === 'BALI') {
                    avgA = a.salesBali?.avg || 0; avgB = b.salesBali?.avg || 0;
                } else if (area === 'JAKARTA') {
                    avgA = a.salesJakarta?.avg || 0; avgB = b.salesJakarta?.avg || 0;
                } else if (area === 'JATIM') {
                    avgA = a.salesJatim?.avg || 0; avgB = b.salesJatim?.avg || 0;
                } else {
                    avgA = a.salesOther?.avg || 0; avgB = b.salesOther?.avg || 0;
                }
                return avgB - avgA;
            });

            const totalPages = Math.ceil(filtered.length / scPerPage);
            if (scPage > totalPages) scPage = 1;
            const start = (scPage - 1) * scPerPage;
            const pageData = filtered.slice(start, start + scPerPage);

            tbody.innerHTML = pageData.map(item => {
                // Get data based on area
                let m1, m2, m3, avgSales, whStock, tokoStock, globalStock;
                if (area === 'all') {
                    m1 = item.salesM1; m2 = item.salesM2; m3 = item.salesM3;
                    avgSales = item.avgSales;
                    whStock = item.whTotal;
                    tokoStock = item.stokToko;
                    globalStock = item.globalStock;
                } else if (area === 'BALI') {
                    m1 = item.salesBali?.m1 || 0; m2 = item.salesBali?.m2 || 0; m3 = item.salesBali?.m3 || 0;
                    avgSales = item.salesBali?.avg || 0;
                    whStock = item.WHB || 0;
                    tokoStock = item.stokTokoBali || 0;
                    globalStock = whStock + tokoStock;
                } else if (area === 'JAKARTA') {
                    m1 = item.salesJakarta?.m1 || 0; m2 = item.salesJakarta?.m2 || 0; m3 = item.salesJakarta?.m3 || 0;
                    avgSales = item.salesJakarta?.avg || 0;
                    whStock = item.WHJ || 0;
                    tokoStock = item.stokTokoJakarta || 0;
                    globalStock = whStock + tokoStock;
                } else if (area === 'JATIM') {
                    m1 = item.salesJatim?.m1 || 0; m2 = item.salesJatim?.m2 || 0; m3 = item.salesJatim?.m3 || 0;
                    avgSales = item.salesJatim?.avg || 0;
                    whStock = item.WHS || 0;
                    tokoStock = item.stokTokoJatim || 0;
                    globalStock = whStock + tokoStock;
                } else {
                    m1 = item.salesOther?.m1 || 0; m2 = item.salesOther?.m2 || 0; m3 = item.salesOther?.m3 || 0;
                    avgSales = item.salesOther?.avg || 0;
                    whStock = 0;
                    tokoStock = item.stokTokoOther || 0;
                    globalStock = tokoStock;
                }

                const tw = avgSales > 0 ? (whStock / avgSales).toFixed(1) : 0;
                const to = avgSales > 0 ? (globalStock / avgSales).toFixed(1) : 0;
                const twVal = parseFloat(tw) || 0;
                const toVal = parseFloat(to) || 0;

                let twColor = '#6b7280', twBg = 'transparent';
                let toColor = '#6b7280', toBg = 'transparent';
                if (avgSales > 0) {
                    if (twVal < 1) { twColor = '#ef4444'; twBg = '#fef2f2'; }
                    else if (twVal < 2) { twColor = '#f59e0b'; twBg = '#fffbeb'; }
                    else if (twVal < 4) { twColor = '#10b981'; twBg = '#f0fdf4'; }
                    else { twColor = '#3b82f6'; twBg = '#eff6ff'; }

                    if (toVal < 1) { toColor = '#ef4444'; toBg = '#fef2f2'; }
                    else if (toVal < 2) { toColor = '#f59e0b'; toBg = '#fffbeb'; }
                    else if (toVal < 4) { toColor = '#10b981'; toBg = '#f0fdf4'; }
                    else { toColor = '#3b82f6'; toBg = '#eff6ff'; }
                }

                // Show WH columns based on area
                let whPusat = '-', whBali = '-', whJkt = '-';
                if (area === 'all') {
                    whPusat = item.WHS.toLocaleString();
                    whBali = item.WHB.toLocaleString();
                    whJkt = item.WHJ.toLocaleString();
                } else if (area === 'BALI') {
                    whBali = item.WHB.toLocaleString();
                } else if (area === 'JAKARTA') {
                    whJkt = item.WHJ.toLocaleString();
                } else if (area === 'JATIM') {
                    whPusat = item.WHS.toLocaleString();
                }

                return `<tr style="border-bottom:1px solid #f3f4f6;color:#1f2937;">
                    <td style="padding:8px;font-family:monospace;font-weight:600;color:#1f2937;">${item.kodeKecil}</td>
                    <td style="padding:8px;font-size:0.75rem;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#4b5563;" title="${item.article||''}">${item.article||'-'}</td>
                    <td style="padding:8px;text-align:center;font-size:0.75rem;color:#6b7280;">${item.series||'-'}</td>
                    <td style="padding:8px;text-align:center;font-size:0.75rem;color:#6b7280;">${item.gender||'-'}</td>
                    <td style="padding:8px;text-align:center;color:#6b7280;">${item.tier||'-'}</td>
                    <td style="padding:8px;text-align:right;color:#374151;">${m1.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;color:#374151;">${m2.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;color:#374151;">${m3.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;background:#fef3c7;font-weight:600;color:#92400e;">${avgSales.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;color:#374151;">${whPusat}</td>
                    <td style="padding:8px;text-align:right;color:#374151;">${whBali}</td>
                    <td style="padding:8px;text-align:right;color:#374151;">${whJkt}</td>
                    <td style="padding:8px;text-align:right;background:#dbeafe;font-weight:600;color:#1e3a8a;">${whStock.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;background:#dcfce7;font-weight:600;color:#166534;">${tokoStock.toLocaleString()}</td>
                    <td style="padding:8px;text-align:right;background:#f3e8ff;font-weight:600;color:#6d28d9;">${globalStock.toLocaleString()}</td>
                    <td style="padding:8px;text-align:center;background:${twBg};color:${twColor};font-weight:700;">${tw||'-'}</td>
                    <td style="padding:8px;text-align:center;background:${toBg};color:${toColor};font-weight:700;">${to||'-'}</td>
                </tr>`;
            }).join('');

            const pag = document.getElementById('scPagination');
            if (pag) {
                pag.innerHTML = `
                    <span style="margin-right:15px;color:#6b7280;">Showing ${start+1}-${Math.min(start+scPerPage,filtered.length)} of ${filtered.length}</span>
                    <button onclick="scPage--;renderStockControlTable()" ${scPage===1?'disabled':''} style="padding:5px 15px;margin-right:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;color:#374151;background:#fff;">Prev</button>
                    <span style="color:#374151;">Page ${scPage} of ${totalPages||1}</span>
                    <button onclick="scPage++;renderStockControlTable()" ${scPage>=totalPages?'disabled':''} style="padding:5px 15px;margin-left:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;color:#374151;background:#fff;">Next</button>
                `;
            }
        }'''

# Replace old render function
old_render_pattern = r'function renderStockControlTable\(\) \{[\s\S]*?const pag = document\.getElementById\(\'scPagination\'\);[\s\S]*?\}\s*\}'
if re.search(old_render_pattern, html):
    html = re.sub(old_render_pattern, new_render_function, html)
    print('renderStockControlTable updated with area logic')
else:
    print('ERROR: renderStockControlTable not found')

# Write
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\nDone! {len(stock_control["items"])} items with area data')
