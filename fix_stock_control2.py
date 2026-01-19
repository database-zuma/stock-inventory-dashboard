import json

# Read files
html_path = 'dashboard_inventory.html'
stock_control_path = 'stock_control_v2.json'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

with open(stock_control_path, 'r', encoding='utf-8') as f:
    stock_control = json.load(f)

# JavaScript for Stock Control - to be added before </script>
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

            const pag = document.getElementById('scPagination');
            if (pag) {
                pag.innerHTML = `
                    <span style="margin-right:15px;">Showing ${start+1}-${Math.min(start+scPerPage,filtered.length)} of ${filtered.length}</span>
                    <button onclick="scPage--;renderStockControlTable()" ${scPage===1?'disabled':''} style="padding:5px 15px;margin-right:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;">Prev</button>
                    <span>Page ${scPage} of ${totalPages||1}</span>
                    <button onclick="scPage++;renderStockControlTable()" ${scPage>=totalPages?'disabled':''} style="padding:5px 15px;margin-left:5px;border-radius:5px;border:1px solid #e5e7eb;cursor:pointer;">Next</button>
                `;
            }
        }

'''

# Check if scItems already exists
if 'const scItems' in html:
    print('scItems already exists, skipping')
else:
    # Insert before </script>
    script_end = html.rfind('    </script>')
    if script_end > 0:
        html = html[:script_end] + stock_control_js + html[script_end:]
        print('Stock Control JS added before </script>')
    else:
        print('ERROR: Could not find </script>')

# Write
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Done! {len(stock_control["items"])} items')
