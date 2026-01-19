import json
import re

# Read files
html_path = 'dashboard_inventory.html'
stock_control_path = 'stock_control.json'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

with open(stock_control_path, 'r', encoding='utf-8') as f:
    stock_control = json.load(f)

# 1. Update the stockcontrolView HTML to include warehouse summary
old_view_start = '''        <!-- ==================== STOCK CONTROL VIEW ==================== -->
        <div class="view-container" id="stockcontrolView">
            <h2 style="margin-bottom:20px;color:#1f2937;">📊 Stock Control - Turnover Analysis</h2>'''

wh = stock_control['warehouseStock']
new_view_start = '''        <!-- ==================== STOCK CONTROL VIEW ==================== -->
        <div class="view-container" id="stockcontrolView">
            <h2 style="margin-bottom:20px;color:#1f2937;">📊 Stock Control - Turnover Analysis</h2>

            <!-- Warehouse Stock Summary Cards -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px;margin-bottom:25px;">
                <div style="background:linear-gradient(135deg,#dbeafe,#bfdbfe);border-radius:16px;padding:20px;">
                    <h4 style="color:#1d4ed8;margin-bottom:8px;">📦 WHB - Warehouse Bali</h4>
                    <div style="font-size:1.8rem;font-weight:700;color:#1e40af;">''' + f'{wh["WHB"]["totalStock"]:,}'.replace(',', '.') + '''</div>
                    <div style="font-size:0.85rem;color:#3b82f6;">''' + f'{wh["WHB"]["totalSku"]:,}'.replace(',', '.') + ''' SKU</div>
                    <div style="font-size:0.75rem;color:#6b7280;margin-top:5px;">Bali & Lombok</div>
                </div>
                <div style="background:linear-gradient(135deg,#dcfce7,#bbf7d0);border-radius:16px;padding:20px;">
                    <h4 style="color:#15803d;margin-bottom:8px;">📦 WHJ - Warehouse Jakarta</h4>
                    <div style="font-size:1.8rem;font-weight:700;color:#166534;">''' + f'{wh["WHJ"]["totalStock"]:,}'.replace(',', '.') + '''</div>
                    <div style="font-size:0.85rem;color:#22c55e;">''' + f'{wh["WHJ"]["totalSku"]:,}'.replace(',', '.') + ''' SKU</div>
                    <div style="font-size:0.75rem;color:#6b7280;margin-top:5px;">Jakarta</div>
                </div>
                <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:16px;padding:20px;">
                    <h4 style="color:#b45309;margin-bottom:8px;">📦 WHS - Warehouse Pusat</h4>
                    <div style="font-size:1.8rem;font-weight:700;color:#92400e;">''' + f'{wh["WHS"]["totalStock"]:,}'.replace(',', '.') + '''</div>
                    <div style="font-size:0.85rem;color:#f59e0b;">''' + f'{wh["WHS"]["totalSku"]:,}'.replace(',', '.') + ''' SKU</div>
                    <div style="font-size:0.75rem;color:#6b7280;margin-top:5px;">Jawa Timur</div>
                </div>
            </div>'''

html = html.replace(old_view_start, new_view_start)

# 2. Update Critical SKU table header to include WH Stock column
old_critical_header = '''                            <tr>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">SKU</th>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">Product</th>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">Store</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Stock</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Sales/Day</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">DOS</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Restock From</th>
                            </tr>'''

new_critical_header = '''                            <tr>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">SKU</th>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">Product</th>
                                <th style="padding:12px;text-align:left;border-bottom:2px solid #e5e7eb;">Store</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Stock</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Sales/Day</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">DOS</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Restock From</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">WH Stock</th>
                                <th style="padding:12px;text-align:center;border-bottom:2px solid #e5e7eb;">Status</th>
                            </tr>'''

html = html.replace(old_critical_header, new_critical_header)

# 3. Update the JavaScript stockControlData and renderCriticalSku function
# First, update the data
old_data_pattern = r'const stockControlData = \{[^;]+\};'
new_data = 'const stockControlData = ' + json.dumps(stock_control, ensure_ascii=False) + ';'
html = re.sub(old_data_pattern, new_data, html, count=1)

# 4. Update renderCriticalSku function to show warehouse stock
old_render_critical = '''        function renderCriticalSku(whFilter = 'all') {
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
        }'''

new_render_critical = '''        function renderCriticalSku(whFilter = 'all') {
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
                const whStock = s.warehouseStock || 0;
                const available = whStock > 0;
                const statusBg = available ? '#dcfce7' : '#fef2f2';
                const statusColor = available ? '#15803d' : '#dc2626';
                const statusText = available ? '✅ Available' : '❌ Kosong';

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
                    <td style="padding:10px;text-align:center;font-weight:600;">${whStock > 0 ? whStock.toLocaleString() : '-'}</td>
                    <td style="padding:10px;text-align:center;">
                        <span style="background:${statusBg};color:${statusColor};padding:4px 8px;border-radius:12px;font-size:0.7rem;font-weight:600;">
                            ${statusText}
                        </span>
                    </td>
                </tr>`;
            }).join('');

            if (skus.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" style="padding:20px;text-align:center;color:#9ca3af;">Tidak ada SKU critical untuk filter ini</td></tr>';
            }
        }'''

html = html.replace(old_render_critical, new_render_critical)

# Write back
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print('Stock Control updated with warehouse stock data!')
print(f'- WHB: {wh["WHB"]["totalStock"]:,} pcs')
print(f'- WHJ: {wh["WHJ"]["totalStock"]:,} pcs')
print(f'- WHS: {wh["WHS"]["totalStock"]:,} pcs')
