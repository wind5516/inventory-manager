// 进销存管理逻辑
const API = "";
let tab = "overview";
let cache = { products: [], stores: [] };

async function api(path, method = "GET", body = null) {
  const headers = { "Content-Type": "application/json" };
  const res = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.message || "请求失败");
  return data;
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast"; el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2200);
}

async function loadCache() {
  try {
    cache.products = (await api("/api/products")).items;
    cache.stores = (await api("/api/stores")).items;
  } catch (e) { toast(e.message); }
}

async function render() {
  await loadCache();
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  const main = document.getElementById("main");
  if (tab === "overview") await renderOverview(main);
  else if (tab === "products") await renderProducts(main);
  else if (tab === "stores") await renderStores(main);
  else if (tab === "movements") await renderMovements(main);
  else if (tab === "alerts") await renderAlerts(main);
  else await renderReports(main);
  refreshBadge();
}

async function refreshBadge() {
  try {
    const a = await api("/api/alerts");
    document.getElementById("alertBadge").textContent = a.items.length;
  } catch (e) {}
}

// ---------- 总览 ----------
async function renderOverview(main) {
  const s = await api("/api/stats");
  const storeOpts = `<option value="">全部店铺</option>` + cache.stores.map(x => `<option value="${x.id}">${x.name}</option>`).join("");
  main.innerHTML = `
    <div class="stats">
      <div class="stat"><div class="num">${s.products}</div><div class="label">商品 SKU</div></div>
      <div class="stat"><div class="num">${s.stores}</div><div class="label">店铺数</div></div>
      <div class="stat"><div class="num">${s.total_qty}</div><div class="label">库存总件数</div></div>
      <div class="stat"><div class="num">¥${s.capital.toFixed(2)}</div><div class="label">库存占用资金</div></div>
      <div class="stat"><div class="num" style="color:${s.low_stock ? "#ef4444" : "#16a34a"}">${s.low_stock}</div><div class="label">低库存预警</div></div>
    </div>
    <div class="toolbar">
      <select id="ovStore" onchange="renderOverviewGrid()">${storeOpts}</select>
      <input type="text" id="ovQ" placeholder="搜索 SKU / 名称…">
      <label style="font-size:13px;color:#6b7280"><input type="checkbox" id="ovLow" onchange="renderOverviewGrid()"> 仅看低库存</label>
      <button class="btn" onclick="ovSearch()">查询</button>
      <button class="btn green" onclick="openMove()">＋ 入库/出库/盘点</button>
      <button class="btn ghost" onclick="openSync()">⇄ 店铺同步</button>
    </div>
    <div id="ovGrid"></div>`;
  await renderOverviewGrid();
}

async function renderOverviewGrid() {
  const storeId = document.getElementById("ovStore").value;
  const q = document.getElementById("ovQ").value.trim();
  const low = document.getElementById("ovLow").checked ? 1 : 0;
  const data = await api(`/api/stock?store_id=${storeId}&q=${encodeURIComponent(q)}&low=${low}`);
  const grid = document.getElementById("ovGrid");
  if (!data.items.length) { grid.innerHTML = `<div class="empty">暂无库存数据</div>`; return; }
  grid.innerHTML = `<table><tr><th>SKU</th><th>商品</th><th>规格</th><th>店铺</th><th>库存</th><th>成本价</th><th>占用资金</th><th>状态</th><th>操作</th></tr>` +
    data.items.map(r => `<tr>
      <td>${r.sku}</td><td>${r.name}</td><td>${r.spec}</td>
      <td>${r.store_name}</td>
      <td><b style="color:${r.low ? "#ef4444" : "#222"}">${r.quantity}</b></td>
      <td>¥${r.cost_price.toFixed(2)}</td><td>¥${r.stock_value.toFixed(2)}</td>
      <td>${r.low ? `<span class="tag off">低库存</span>` : `<span class="tag on">正常</span>`}</td>
      <td style="white-space:nowrap">
        <button class="btn ghost" onclick="openMove(${r.product_id},${r.store_id},'in')">入库</button>
        <button class="btn gray" onclick="openMove(${r.product_id},${r.store_id},'out')">出库</button>
        <button class="btn" onclick="openMove(${r.product_id},${r.store_id},'check')">盘点</button>
      </td></tr>`).join("") + `</table>`;
}

function ovSearch() { renderOverviewGrid(); }

function openMove(productId = 0, storeId = 0, type = "in") {
  const prodOpts = `<option value="">选择商品</option>` + cache.products.map(p => `<option value="${p.id}" ${p.id === productId ? "selected" : ""}>${p.sku} ${p.name}</option>`).join("");
  const storeOpts = `<option value="">选择店铺</option>` + cache.stores.map(s => `<option value="${s.id}" ${s.id === storeId ? "selected" : ""}>${s.name}</option>`).join("");
  document.getElementById("modal").innerHTML = `
  <div class="modal-mask" onclick="if(event.target===this)closeM()">
    <div class="modal">
      <h3>${type === "in" ? "入库" : type === "out" ? "出库" : "盘点"}</h3>
      <div class="field"><label>商品</label><select id="mProd" style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:8px">${prodOpts}</select></div>
      <div class="field"><label>店铺</label><select id="mStore" style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:8px">${storeOpts}</select></div>
      ${type === "check" ? `<div class="field"><label>实际盘点数量</label><input id="mActual" type="number" min="0"></div>`
        : `<div class="field"><label>数量</label><input id="mQty" type="number" min="1"></div>`}
      <div class="field"><label>备注</label><input id="mRemark" placeholder="可选"></div>
      <div class="actions">
        <button class="btn gray" onclick="closeM()">取消</button>
        <button class="btn" onclick="submitMove('${type}')">确认${type === "in" ? "入库" : type === "out" ? "出库" : "盘点"}</button>
      </div>
    </div>
  </div>`;
}

async function submitMove(type) {
  const pid = +document.getElementById("mProd").value;
  const sid = +document.getElementById("mStore").value;
  if (!pid || !sid) { toast("请选择商品和店铺"); return; }
  const body = { product_id: pid, store_id: sid, type, remark: document.getElementById("mRemark").value.trim() };
  if (type === "check") body.actual_qty = +document.getElementById("mActual").value;
  else body.quantity = +document.getElementById("mQty").value;
  try {
    const r = await api("/api/movements", "POST", body);
    toast(`${type === "in" ? "入库" : type === "out" ? "出库" : "盘点"}成功：库存 ${r.before} → ${r.after}`);
    closeM(); render();
  } catch (e) { toast(e.message); }
}

function openSync() {
  const opts = cache.stores.map(s => `<option value="${s.id}">${s.name}</option>`).join("");
  document.getElementById("modal").innerHTML = `
  <div class="modal-mask" onclick="if(event.target===this)closeM()">
    <div class="modal">
      <h3>店铺库存同步</h3>
      <div class="field"><label>源店铺（以它为准）</label><select id="sSrc" style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:8px">${opts}</select></div>
      <div class="field"><label>目标店铺（将被覆盖）</label><select id="sDst" style="width:100%;padding:8px;border:1px solid #d1d5db;border-radius:8px">${opts}</select></div>
      <div style="font-size:12px;color:#6b7280">将源店铺全部商品的库存数量同步到目标店铺，并记录同步流水。</div>
      <div class="actions"><button class="btn gray" onclick="closeM()">取消</button>
        <button class="btn" onclick="submitSync()">开始同步</button></div>
    </div>
  </div>`;
}

async function submitSync() {
  const src = +document.getElementById("sSrc").value;
  const dst = +document.getElementById("sDst").value;
  if (!src || !dst) { toast("请选择店铺"); return; }
  try {
    const r = await api("/api/sync", "POST", { source_store_id: src, target_store_id: dst });
    toast(`同步完成，更新 ${r.synced} 个 SKU`); closeM(); render();
  } catch (e) { toast(e.message); }
}

// ---------- 商品 ----------
async function renderProducts(main) {
  const data = await api("/api/products");
  main.innerHTML = `
    <div class="toolbar">
      <input type="text" id="pQ" placeholder="搜索 SKU / 名称…">
      <button class="btn" onclick="pSearch()">查询</button>
      <button class="btn green" onclick="openProduct()">＋ 新增商品</button>
      <label class="btn gray" style="cursor:pointer">📥 Excel 导入<input type="file" id="pFile" accept=".xlsx,.xls" style="display:none" onchange="importExcel(this)"></label>
      <a class="btn ghost" href="/api/export/inventory.xlsx" style="text-decoration:none">📤 导出库存 Excel</a>
    </div>
    <table><tr><th>SKU</th><th>名称</th><th>规格</th><th>单位</th><th>成本价</th><th>售价</th><th>预警阈值</th><th>操作</th></tr>
    ${data.items.map(p => `<tr>
      <td>${p.sku}</td><td>${p.name}</td><td>${p.spec}</td><td>${p.unit}</td>
      <td>¥${p.cost_price.toFixed(2)}</td><td>¥${p.sale_price.toFixed(2)}</td><td>${p.low_threshold}</td>
      <td style="white-space:nowrap">
        <button class="btn ghost" onclick='openProduct(${JSON.stringify(p).replace(/'/g, "&#39;")})'>编辑</button>
        <button class="btn red" onclick="delProduct(${p.id})">删除</button></td></tr>`).join("") || '<tr><td colspan="8" style="text-align:center;color:#9ca3af">暂无商品</td></tr>'}
    </table>`;
}

async function pSearch() {
  const q = document.getElementById("pQ").value.trim();
  const data = await api(`/api/products?q=${encodeURIComponent(q)}`);
  document.querySelector("#main table").innerHTML = data.items.map(p => `<tr><td>${p.sku}</td><td>${p.name}</td><td>${p.spec}</td><td>${p.unit}</td><td>¥${p.cost_price.toFixed(2)}</td><td>¥${p.sale_price.toFixed(2)}</td><td>${p.low_threshold}</td><td><button class="btn ghost" onclick='openProduct(${JSON.stringify(p).replace(/'/g, "&#39;")})'>编辑</button></td></tr>`).join("");
}

function openProduct(p) {
  const isEdit = !!p;
  document.getElementById("modal").innerHTML = `
  <div class="modal-mask" onclick="if(event.target===this)closeM()">
    <div class="modal">
      <h3>${isEdit ? "编辑商品" : "新增商品"}</h3>
      <div class="field"><label>SKU（唯一）</label><input id="fSku" value="${isEdit ? p.sku : ""}" ${isEdit ? "disabled" : ""}></div>
      <div class="field"><label>名称</label><input id="fName" value="${isEdit ? p.name : ""}"></div>
      <div class="field"><label>规格</label><input id="fSpec" value="${isEdit ? p.spec : ""}"></div>
      <div class="field"><label>单位</label><input id="fUnit" value="${isEdit ? p.unit : "件"}"></div>
      <div class="field"><label>成本价</label><input id="fCost" type="number" step="0.01" value="${isEdit ? p.cost_price : 0}"></div>
      <div class="field"><label>售价</label><input id="fSale" type="number" step="0.01" value="${isEdit ? p.sale_price : 0}"></div>
      <div class="field"><label>低库存预警阈值</label><input id="fThr" type="number" value="${isEdit ? p.low_threshold : 10}"></div>
      <div class="actions"><button class="btn gray" onclick="closeM()">取消</button>
        <button class="btn" onclick="saveProduct(${isEdit ? p.id : "null"})">保存</button></div>
    </div>
  </div>`;
}

async function saveProduct(id) {
  const body = {
    sku: document.getElementById("fSku").value.trim(),
    name: document.getElementById("fName").value.trim(),
    spec: document.getElementById("fSpec").value.trim(),
    unit: document.getElementById("fUnit").value.trim() || "件",
    cost_price: +document.getElementById("fCost").value,
    sale_price: +document.getElementById("fSale").value,
    low_threshold: +document.getElementById("fThr").value,
  };
  if (!body.sku || !body.name) { toast("SKU 和名称必填"); return; }
  try {
    if (id) await api(`/api/products/${id}`, "PUT", body);
    else await api("/api/products", "POST", body);
    closeM(); toast("保存成功"); render();
  } catch (e) { toast(e.message); }
}

async function delProduct(id) {
  if (!confirm("确认删除该商品？")) return;
  try { await api(`/api/products/${id}`, "DELETE"); toast("已删除"); render(); } catch (e) { toast(e.message); }
}

async function importExcel(input) {
  const file = input.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    const res = await fetch("/api/import/products", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "导入失败");
    toast(`导入成功 ${data.imported} 条${data.skipped.length ? `，跳过重复 ${data.skipped.length} 条` : ""}`);
    input.value = ""; render();
  } catch (e) { toast(e.message); }
}

// ---------- 店铺 ----------
async function renderStores(main) {
  const data = await api("/api/stores");
  main.innerHTML = `
    <div class="toolbar"><button class="btn green" onclick="openStore()">＋ 新增店铺</button></div>
    <table><tr><th>ID</th><th>店铺</th><th>平台</th><th>备注</th><th>在售 SKU</th><th>库存资金</th><th>操作</th></tr>
    ${data.items.map(s => `<tr><td>${s.id}</td><td>${s.name}</td><td>${s.platform}</td><td>${s.remark}</td>
      <td>${s.sku_count}</td><td>¥${s.stock_value.toFixed(2)}</td>
      <td><button class="btn red" onclick="delStore(${s.id})">删除</button></td></tr>`).join("")}
    </table>`;
}

function openStore() {
  document.getElementById("modal").innerHTML = `
  <div class="modal-mask" onclick="if(event.target===this)closeM()">
    <div class="modal"><h3>新增店铺</h3>
      <div class="field"><label>店铺名称</label><input id="sName"></div>
      <div class="field"><label>平台</label><input id="sPlat" placeholder="淘宝 / 拼多多 / 抖音"></div>
      <div class="field"><label>备注</label><input id="sRemark"></div>
      <div class="actions"><button class="btn gray" onclick="closeM()">取消</button>
        <button class="btn" onclick="saveStore()">保存</button></div>
    </div>
  </div>`;
}

async function saveStore() {
  const name = document.getElementById("sName").value.trim();
  if (!name) { toast("店铺名必填"); return; }
  try {
    await api("/api/stores", "POST", { name, platform: document.getElementById("sPlat").value.trim(), remark: document.getElementById("sRemark").value.trim() });
    closeM(); toast("店铺已新增"); render();
  } catch (e) { toast(e.message); }
}

async function delStore(id) {
  if (!confirm("删除店铺会同时删除其库存记录，确认？")) return;
  try { await api(`/api/stores/${id}`, "DELETE"); toast("已删除"); render(); } catch (e) { toast(e.message); }
}

// ---------- 流水 ----------
async function renderMovements(main) {
  const data = await api("/api/movements?limit=200");
  const TYPE = { in: ["入库", "green"], out: ["出库", "red"], check: ["盘点", ""], sync: ["同步", ""] };
  main.innerHTML = `<h2 style="margin-bottom:14px">出入库流水（最近 200 条）</h2>
    <table><tr><th>时间</th><th>类型</th><th>SKU</th><th>商品</th><th>店铺</th><th>变动</th><th>变动后库存</th><th>备注</th></tr>
    ${data.items.map(m => `<tr>
      <td style="font-size:12px">${m.created_at}</td>
      <td><span class="tag ${(TYPE[m.type]||["", ""])[1] || "on"}">${(TYPE[m.type]||[m.type])[0]}</span></td>
      <td>${m.sku}</td><td>${m.product_name}</td><td>${m.store_name}</td>
      <td style="color:${m.change_qty >= 0 ? "#16a34a" : "#ef4444"};font-weight:600">${m.change_qty >= 0 ? "+" : ""}${m.change_qty}</td>
      <td>${m.after_qty}</td><td style="font-size:12px;color:#6b7280">${m.remark}</td></tr>`).join("") || '<tr><td colspan="8" style="text-align:center;color:#9ca3af">暂无流水</td></tr>'}
    </table>`;
}

// ---------- 预警 ----------
async function renderAlerts(main) {
  const data = await api("/api/alerts");
  main.innerHTML = `<h2 style="margin-bottom:14px">低库存预警</h2>
    ${data.items.length ? `<table><tr><th>SKU</th><th>商品</th><th>规格</th><th>店铺</th><th>当前库存</th><th>预警阈值</th><th>缺口</th></tr>` +
      data.items.map(a => `<tr><td>${a.sku}</td><td>${a.name}</td><td>${a.spec}</td><td>${a.store_name}</td>
        <td><b style="color:#ef4444">${a.quantity}</b></td><td>${a.low_threshold}</td>
        <td style="color:#ef4444">缺 ${Math.max(0, a.low_threshold - a.quantity)}</td></tr>`).join("") + `</table>`
      : `<div class="empty">🎉 所有店铺库存充足，暂无预警</div>`}`;
}

// ---------- 报表 ----------
async function renderReports(main) {
  const inv = await api("/api/report/inventory");
  const profit = await api("/api/report/profit");
  main.innerHTML = `
    <h2 style="margin-bottom:8px">库存汇总报表</h2>
    <table style="margin-bottom:20px"><tr><th>SKU</th><th>商品</th><th>单位</th><th>成本价</th><th>售价</th><th>总库存</th><th>覆盖店铺</th><th>库存资金</th><th>货值(售价)</th></tr>
    ${inv.items.map(r => `<tr><td>${r.sku}</td><td>${r.name}</td><td>${r.unit}</td>
      <td>¥${r.cost_price.toFixed(2)}</td><td>¥${r.sale_price.toFixed(2)}</td>
      <td><b>${r.total_qty}</b></td><td>${r.in_stores}/${r.store_count}</td>
      <td>¥${r.stock_value.toFixed(2)}</td><td>¥${r.sale_value.toFixed(2)}</td></tr>`).join("")}
    </table>
    <h2 style="margin-bottom:8px">毛利与库存周转</h2>
    <div class="panel" style="margin-bottom:12px">累计毛利（按出库量估算）：<b style="color:#16a34a;font-size:20px">¥${profit.total_profit.toFixed(2)}</b></div>
    <table><tr><th>SKU</th><th>商品</th><th>单位毛利</th><th>累计出库</th><th>毛利</th><th>当前库存</th><th>周转率(出库/库存)</th></tr>
    ${profit.items.map(r => `<tr><td>${r.sku}</td><td>${r.name}</td>
      <td>¥${r.unit_profit.toFixed(2)}</td><td>${r.out_qty}</td>
      <td style="color:#16a34a">¥${r.profit.toFixed(2)}</td><td>${r.current_qty}</td><td>${r.turnover}</td></tr>`).join("")}
    </table>`;
}

// ---------- 工具 ----------
function closeM() { document.getElementById("modal").innerHTML = ""; }

document.querySelectorAll(".nav-btn").forEach(b => b.onclick = () => { tab = b.dataset.tab; render(); });
render();
