# Zuma Stock & Inventory Dashboard — Agent Skill Document

> This file ensures any Claude agent session can quickly understand the full architecture,
> diagnose common failures, and fix issues without lengthy debugging.

## Architecture Overview

```
Browser (GitHub Pages)
  └─ dashboard_inventory.html (~9,870 lines, single-file HTML+CSS+JS)
       └─ fetchAPI() calls
            └─ Cloudflare Tunnel (trycloudflare.com — EPHEMERAL URL)
                 └─ cloudflared on VPS (systemd: cloudflared-zuma.service)
                      └─ nginx on VPS (localhost:8443)
                           └─ gunicorn (unix socket: /run/zuma-api/gunicorn.sock)
                                └─ Python FastAPI app (/opt/zuma-api/main.py)
                                     └─ PostgreSQL (openclaw_ops database)
```

### Key Constants in dashboard_inventory.html

| Variable | Line | Current Value |
|----------|------|---------------|
| `API_BASE` | ~1953 | `https://roommate-stage-apartment-popular.trycloudflare.com` |
| `API_BASE_LOCAL` | ~1954 | same as API_BASE |
| `API_KEY` | ~1955 | `97d25067-a2ca-44ba-ac5b-61539b627271` |

### VPS Access

- **SSH**: `ssh vps-db` (76.76.21.21, root)
- **Dashboard URL**: `https://database-zuma.github.io/stock-inventory-dashboard/dashboard_inventory.html`

---

## API Endpoints

| Endpoint | Method | Cache TTL | Notes |
|----------|--------|-----------|-------|
| `/api/stock` | GET | — | ~2s response |
| `/api/stores` | GET | — | ~0.4s |
| `/api/store-areas` | GET | — | ~0.4s |
| `/api/max-stock` | GET | — | ~0.4s |
| `/api/sales/aggregate` | GET | 300s | Main sales summary |
| `/api/targets` | GET | — | ~0.4s |
| `/api/assortment` | GET | — | ~0.4s |
| `/api/sales/detail?from=...&to=...` | GET | varies | Per-month detail, ~2-5s each |
| `/api/sales/detail?channel=online&from=...&to=...` | GET | — | Online channel filter |
| `/api/sales/online-area?from=...&to=...` | GET | — | Online area breakdown |
| `/api/sales/consignment?from=...&to=...` | GET | — | Consignment data |
| `/api/refund` | GET | — | ❌ NOT BUILT (returns 404) |

---

## VPS Services

| Service | Systemd Unit | Config Location |
|---------|-------------|-----------------|
| Cloudflared tunnel | `cloudflared-zuma.service` | `/etc/systemd/system/cloudflared-zuma.service` |
| FastAPI app | `zuma-api.service` | `/opt/zuma-api/main.py` |
| Nginx | `nginx.service` | `/etc/nginx/sites-available/zuma-api` |
| Gunicorn | (via zuma-api.service) | `/opt/zuma-api/gunicorn.conf.py` |

### Service Commands (on VPS)

```bash
# Check all services
systemctl status cloudflared-zuma zuma-api nginx

# Restart API
systemctl restart zuma-api

# Restart tunnel (WARNING: changes the tunnel URL!)
systemctl restart cloudflared-zuma

# Get current tunnel URL
journalctl -u cloudflared-zuma --no-pager -n 20 | grep "trycloudflare.com"
# or
cat /var/log/zuma-api/cloudflare-tunnel.log | grep "trycloudflare.com" | tail -1
```

---

## Data Loading Flow (Frontend)

The dashboard loads data in **two phases**:

### Phase 1 — Parallel bulk load (`loadDashboardData()` ~line 2105)
```
Promise.all([
  /api/stock, /api/stores, /api/store-areas, /api/max-stock,
  /api/sales/aggregate, /api/targets, /api/assortment
])
```
All 7 endpoints must succeed. Failure of ANY → "Gagal memuat data: Failed to fetch".

### Phase 2 — Sequential per-month detail
```
for each month (Jan, Feb, Mar 2026):
  /api/sales/detail?from=YYYY-MM-01&to=YYYY-MM-DD
```
Loads ~83,000 records total. These feed the 4 sales channel tabs.

### Sales Rendering Chain
```
loadDashboardData() → stores data in global variables
  → renderSalesDashboard() (~line 5464)
    → switchSalesChannel() (~line 8113)
      → renderSalesChannel() (~lines 7526-7645)
        → renders Retail / Online / Consignment / Wholesale tabs
```

**CRITICAL**: If `renderSalesDashboard()` throws an uncaught error, ALL 4 sales tabs will show 0 rows even though data is loaded. Always use null checks before `.textContent` or `.innerHTML` assignments.

---

## Troubleshooting Decision Tree

### Symptom: "Gagal memuat data: Failed to fetch"

```
1. Is the tunnel URL still valid?
   └─ SSH to VPS: journalctl -u cloudflared-zuma -n 20 | grep trycloudflare
   └─ Compare with API_BASE in dashboard_inventory.html (~line 1953)
   └─ If different → update API_BASE, commit & push
   
2. Is cloudflared running?
   └─ SSH to VPS: systemctl status cloudflared-zuma
   └─ If dead → systemctl restart cloudflared-zuma
   └─ WARNING: restart generates new URL, must update dashboard
   
3. Is the API service running?
   └─ SSH to VPS: systemctl status zuma-api
   └─ If dead → systemctl restart zuma-api
   
4. Is nginx running?
   └─ SSH to VPS: systemctl status nginx
   └─ If dead → systemctl restart nginx

5. Test from VPS directly:
   └─ curl -H "X-API-Key: 97d25067-a2ca-44ba-ac5b-61539b627271" http://localhost:8443/api/stores
   └─ If works → tunnel issue. If fails → API/nginx issue.

6. Test through tunnel:
   └─ curl -H "X-API-Key: 97d25067-a2ca-44ba-ac5b-61539b627271" https://<tunnel-url>/api/stores
   └─ If fails with timeout → check nginx port 8443 config
```

### Symptom: Sales tables show 0 rows / empty data

```
1. Check browser console for JS errors
   └─ TypeError / null reference → fix the JS crash, add null checks
   └─ CRITICAL: A single uncaught error in renderSalesDashboard() kills ALL tabs
   
2. Check if data actually loaded
   └─ Browser console: typeof salesDetailData, salesDetailData.length
   └─ If undefined or 0 → API issue (see "Failed to fetch" tree above)
   └─ If >0 → rendering bug in JS

3. Common JS crash pattern:
   └─ document.getElementById('someId').textContent = value
   └─ If element doesn't exist → TypeError crashes the entire render function
   └─ FIX: const el = document.getElementById('someId'); if (el) el.textContent = value;
```

### Symptom: API timeout (30s+ then HTTP 000)

```
1. Check for database locks
   └─ SSH to VPS, then:
   └─ psql -U zuma_api -d openclaw_ops
   └─ SELECT pid, state, query, age(clock_timestamp(), query_start) as duration
      FROM pg_stat_activity
      WHERE state != 'idle' AND query_start < now() - interval '30 seconds'
      ORDER BY duration DESC;
   
2. If long-running queries found:
   └─ SELECT pg_cancel_backend(<pid>);  -- graceful cancel
   └─ SELECT pg_terminate_backend(<pid>);  -- force kill
   
3. Common culprit: DELETE on raw.accurate_sales_ddd table
   └─ Locks the table → blocks core.sales_with_product view queries
   └─ These views are used by /api/sales/aggregate
```

---

## Known Gotchas

1. **Tunnel URL is EPHEMERAL** — `trycloudflare.com` URLs change whenever cloudflared restarts (VPS reboot, service restart). After any VPS restart, check and update `API_BASE` in the dashboard.

2. **CORS is locked down** — nginx only allows `Access-Control-Allow-Origin: https://database-zuma.github.io`. Testing from other origins will fail.

3. **Port 8443 is firewalled** — Cannot connect directly to VPS:8443 from internet. Only cloudflared (running on localhost) can access it.

4. **Single-file architecture** — The entire dashboard is one HTML file (~9,870 lines). Be extremely careful with edits. Always:
   - Test JS syntax with `new Function()` before committing
   - Check div nesting (don't break HTML structure)
   - Verify in browser before pushing

5. **No `/api/refund` endpoint** — Console shows 404 errors for this. Not a bug — the feature hasn't been built yet.

6. **Database lock cascading** — A long-running query on `raw.accurate_sales_ddd` can lock the entire sales view chain, causing API timeouts that look like tunnel failures.

---

## Safe Edit Rules (User's Explicit Constraints)

- ⚠️ "km atiati kalau melakukan perubahan" — BE CAREFUL with changes
- ⚠️ "jangan sampai ilang lagi datanya atau kosong" — Don't make data disappear
- ⚠️ "ngapain ke vercel itu" — DO NOT deploy to Vercel
- ⚠️ "sesuai perintah jangan blank ya" — Don't break the dashboard
- ⚠️ Always test in browser before pushing
- ⚠️ Always validate JS syntax before committing
- ⚠️ Always check div nesting before committing
- ⚠️ Use "Consignment" not "Konsinyasi"
- ⚠️ Fix ONE thing at a time

---

## Key Line Number Reference

| What | Approx Line | Notes |
|------|-------------|-------|
| API_BASE declaration | ~1953 | Tunnel URL goes here |
| API_KEY declaration | ~1955 | Auth key |
| fetchAPI() function | ~1957-1963 | No timeout set |
| loadDashboardData() | ~2105-2179 | Phase 1 + Phase 2 data loading |
| Sidebar navigation | ~563-566 | Retail → Online → Consignment → Wholesale |
| renderSalesDashboard() | ~5464-5489 | Entry point for sales rendering |
| switchSalesChannel() | ~8113 | Tab switching logic |
| renderSalesChannel() | ~7526-7645 | Per-channel rendering |

> **NOTE**: Line numbers shift as the file is edited. Use function name search instead of absolute line numbers.

---

## Git Workflow

```bash
# Local repo
cd /Users/database-zuma/stock-inventory-dashboard

# After making changes
git add dashboard_inventory.html
git commit -m "fix: descriptive message"
git push origin main

# Dashboard auto-deploys via GitHub Pages
# URL: https://database-zuma.github.io/stock-inventory-dashboard/dashboard_inventory.html
```

---

## Previous Bugs Fixed (Don't Re-introduce)

| Bug | Root Cause | Fix | Commit |
|-----|-----------|-----|--------|
| "Failed to fetch" | Wrong tunnel URL in API_BASE | Updated to current `trycloudflare.com` URL | `4d060da` |
| Sales tables showing 0 rows | `document.getElementById('salesPeriodRange').textContent` crashes (element doesn't exist) | Added null check | `2ce6a28` |
| API timeout on /api/sales/aggregate | Stuck DELETE query locking database tables | Killed stuck PID via `pg_terminate_backend()` | (runtime fix) |
