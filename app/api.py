"""进销存业务路由"""
import io
import os

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from . import db
from .schemas import MovementIn, ProductIn, ProductUpdate, StoreIn, SyncIn

router = APIRouter(prefix="/api", tags=["进销存"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")


def _record(conn, product_id, store_id, mtype, change_qty, before_qty, after_qty, remark):
    conn.execute(
        "INSERT INTO movements(product_id, store_id, type, change_qty, before_qty, after_qty, remark) VALUES(?,?,?,?,?,?,?)",
        (product_id, store_id, mtype, change_qty, before_qty, after_qty, remark),
    )


# ---------- 总览 ----------
@router.get("/stats", summary="总览统计")
def stats():
    with db.get_conn() as conn:
        products = conn.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]
        stores = conn.execute("SELECT COUNT(*) c FROM stores").fetchone()["c"]
        total_qty = conn.execute("SELECT COALESCE(SUM(quantity),0) v FROM stock").fetchone()["v"]
        capital = conn.execute(
            """SELECT COALESCE(SUM(s.quantity*p.cost_price),0) v FROM stock s
               JOIN products p ON p.id=s.product_id""").fetchone()["v"]
        low = conn.execute(
            """SELECT COUNT(*) c FROM stock s JOIN products p ON p.id=s.product_id
               WHERE s.quantity <= p.low_threshold""").fetchone()["c"]
        skus = conn.execute("SELECT COUNT(*) c FROM stock WHERE quantity>0").fetchone()["c"]
    return {
        "products": products, "stores": stores, "total_qty": total_qty,
        "capital": round(capital, 2), "low_stock": low, "in_stock_skus": skus,
    }


# ---------- 商品 ----------
@router.get("/products", summary="商品列表")
def list_products(q: str | None = None):
    with db.get_conn() as conn:
        if q:
            rows = conn.execute(
                "SELECT * FROM products WHERE sku LIKE ? OR name LIKE ? ORDER BY id",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    return {"items": [db.row_to_dict(r) for r in rows]}


@router.post("/products", summary="新增商品")
def create_product(body: ProductIn):
    with db.get_conn() as conn:
        if conn.execute("SELECT id FROM products WHERE sku=?", (body.sku.strip(),)).fetchone():
            raise HTTPException(400, f"SKU {body.sku} 已存在")
        cur = conn.execute(
            "INSERT INTO products(sku, name, spec, unit, cost_price, sale_price, low_threshold) VALUES(?,?,?,?,?,?,?)",
            (body.sku.strip(), body.name, body.spec, body.unit, body.cost_price, body.sale_price, body.low_threshold),
        )
        pid = cur.lastrowid
        for s in conn.execute("SELECT id FROM stores").fetchall():
            conn.execute("INSERT INTO stock(product_id, store_id, quantity) VALUES(?,?,0)", (pid, s["id"]))
    return {"ok": True, "id": pid}


@router.put("/products/{product_id}", summary="更新商品")
def update_product(product_id: int, body: ProductUpdate):
    fields, params = [], []
    for key in ("name", "spec", "unit", "cost_price", "sale_price", "low_threshold"):
        val = getattr(body, key)
        if val is not None:
            fields.append(f"{key}=?")
            params.append(val)
    if not fields:
        raise HTTPException(400, "没有需要更新的字段")
    params.append(product_id)
    with db.get_conn() as conn:
        if not conn.execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone():
            raise HTTPException(404, "商品不存在")
        conn.execute(f"UPDATE products SET {', '.join(fields)} WHERE id=?", params)
    return {"ok": True}


@router.delete("/products/{product_id}", summary="删除商品")
def delete_product(product_id: int):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    return {"ok": True}


# ---------- 店铺 ----------
@router.get("/stores", summary="店铺列表")
def list_stores():
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM stores ORDER BY id").fetchall()
        data = [db.row_to_dict(r) for r in rows]
        for d in data:
            d["stock_value"] = conn.execute(
                "SELECT COALESCE(SUM(s.quantity*p.cost_price),0) v FROM stock s JOIN products p ON p.id=s.product_id WHERE s.store_id=?",
                (d["id"],),
            ).fetchone()["v"]
            d["sku_count"] = conn.execute("SELECT COUNT(*) c FROM stock WHERE store_id=? AND quantity>0", (d["id"],)).fetchone()["c"]
    return {"items": data}


@router.post("/stores", summary="新增店铺")
def create_store(body: StoreIn):
    with db.get_conn() as conn:
        if conn.execute("SELECT id FROM stores WHERE name=?", (body.name.strip(),)).fetchone():
            raise HTTPException(400, "店铺名已存在")
        cur = conn.execute("INSERT INTO stores(name, platform, remark) VALUES(?,?,?)", (body.name.strip(), body.platform, body.remark))
        sid = cur.lastrowid
        for p in conn.execute("SELECT id FROM products").fetchall():
            conn.execute("INSERT INTO stock(product_id, store_id, quantity) VALUES(?,?,0)", (p["id"], sid))
    return {"ok": True, "id": sid}


@router.delete("/stores/{store_id}", summary="删除店铺")
def delete_store(store_id: int):
    with db.get_conn() as conn:
        conn.execute("DELETE FROM stores WHERE id=?", (store_id,))
    return {"ok": True}


# ---------- 库存 ----------
@router.get("/stock", summary="库存总览")
def list_stock(store_id: int | None = None, q: str | None = None, low: int = 0):
    where, params = [], []
    if store_id:
        where.append("s.store_id=?")
        params.append(store_id)
    if q:
        where.append("(p.sku LIKE ? OR p.name LIKE ?)")
        params += [f"%{q}%", f"%{q}%"]
    if low:
        where.append("s.quantity <= p.low_threshold")
    cond = (" WHERE " + " AND ".join(where)) if where else ""
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT s.id, s.product_id, s.store_id, s.quantity,
                       p.sku, p.name, p.spec, p.unit, p.cost_price, p.sale_price, p.low_threshold,
                       st.name AS store_name, st.platform
                FROM stock s
                JOIN products p ON p.id=s.product_id
                JOIN stores st ON st.id=s.store_id
                {cond} ORDER BY p.id, s.store_id""",
            params,
        ).fetchall()
        items = [db.row_to_dict(r) for r in rows]
        for it in items:
            it["low"] = it["quantity"] <= it["low_threshold"]
            it["stock_value"] = round(it["quantity"] * it["cost_price"], 2)
    return {"items": items}


# ---------- 出入库 / 盘点 / 同步 ----------
@router.post("/movements", summary="入库/出库/盘点")
def create_movement(body: MovementIn):
    with db.get_conn() as conn:
        prod = conn.execute("SELECT * FROM products WHERE id=?", (body.product_id,)).fetchone()
        store = conn.execute("SELECT * FROM stores WHERE id=?", (body.store_id,)).fetchone()
        if prod is None or store is None:
            raise HTTPException(404, "商品或店铺不存在")
        row = conn.execute("SELECT quantity FROM stock WHERE product_id=? AND store_id=?", (body.product_id, body.store_id)).fetchone()
        before = row["quantity"] if row else 0
        if body.type == "in":
            change = body.quantity
            remark = body.remark or "入库"
        elif body.type == "out":
            change = -body.quantity
            if before + change < 0:
                raise HTTPException(400, f"出库失败：当前库存 {before}，不足 {body.quantity}")
            remark = body.remark or "出库"
        else:  # check 盘点
            actual = body.actual_qty
            if actual is None:
                raise HTTPException(400, "盘点需提供 actual_qty")
            change = actual - before
            remark = body.remark or f"盘点修正（账面 {before} → 实际 {actual}）"
        after = before + change
        if row:
            conn.execute("UPDATE stock SET quantity=? WHERE product_id=? AND store_id=?", (after, body.product_id, body.store_id))
        else:
            conn.execute("INSERT INTO stock(product_id, store_id, quantity) VALUES(?,?,?)", (body.product_id, body.store_id, after))
        _record(conn, body.product_id, body.store_id, body.type, change, before, after, remark)
    return {"ok": True, "before": before, "change": change, "after": after}


@router.post("/sync", summary="店铺库存同步（源覆盖目标）")
def sync_stores(body: SyncIn):
    if body.source_store_id == body.target_store_id:
        raise HTTPException(400, "源店铺与目标店铺不能相同")
    with db.get_conn() as conn:
        if not (conn.execute("SELECT id FROM stores WHERE id=?", (body.source_store_id,)).fetchone()
                and conn.execute("SELECT id FROM stores WHERE id=?", (body.target_store_id,)).fetchone()):
            raise HTTPException(404, "店铺不存在")
        rows = conn.execute("SELECT product_id, quantity FROM stock WHERE store_id=?", (body.source_store_id,)).fetchall()
        count = 0
        for r in rows:
            target = conn.execute("SELECT quantity FROM stock WHERE product_id=? AND store_id=?", (r["product_id"], body.target_store_id)).fetchone()
            before = target["quantity"] if target else 0
            change = r["quantity"] - before
            if change == 0:
                continue
            if target:
                conn.execute("UPDATE stock SET quantity=? WHERE product_id=? AND store_id=?", (r["quantity"], r["product_id"], body.target_store_id))
            else:
                conn.execute("INSERT INTO stock(product_id, store_id, quantity) VALUES(?,?,?)", (r["product_id"], body.target_store_id, r["quantity"]))
            _record(conn, r["product_id"], body.target_store_id, "sync", change, before, r["quantity"], "店铺同步")
            count += 1
    return {"ok": True, "synced": count}


# ---------- 流水 ----------
@router.get("/movements", summary="出入库流水")
def list_movements(product_id: int | None = None, store_id: int | None = None, limit: int = Query(default=100, le=500)):
    where, params = [], []
    if product_id:
        where.append("m.product_id=?"); params.append(product_id)
    if store_id:
        where.append("m.store_id=?"); params.append(store_id)
    cond = (" WHERE " + " AND ".join(where)) if where else ""
    with db.get_conn() as conn:
        rows = conn.execute(
            f"""SELECT m.*, p.sku, p.name AS product_name, st.name AS store_name
                FROM movements m
                JOIN products p ON p.id=m.product_id
                JOIN stores st ON st.id=m.store_id
                {cond} ORDER BY m.id DESC LIMIT ?""",
            params + [limit],
        ).fetchall()
    return {"items": [db.row_to_dict(r) for r in rows]}


# ---------- 低库存预警 ----------
@router.get("/alerts", summary="低库存预警")
def alerts():
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT s.*, p.sku, p.name, p.spec, p.low_threshold, st.name AS store_name
               FROM stock s JOIN products p ON p.id=s.product_id JOIN stores st ON st.id=s.store_id
               WHERE s.quantity <= p.low_threshold ORDER BY (p.low_threshold - s.quantity) DESC""",
        ).fetchall()
    return {"items": [db.row_to_dict(r) for r in rows]}


# ---------- 报表 ----------
@router.get("/report/inventory", summary="库存汇总报表")
def report_inventory():
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT p.id, p.sku, p.name, p.spec, p.unit, p.cost_price, p.sale_price,
                      COALESCE(SUM(s.quantity),0) AS total_qty,
                      COUNT(CASE WHEN s.quantity>0 THEN 1 END) AS in_stores,
                      (SELECT COUNT(*) FROM stores) AS store_count
               FROM products p LEFT JOIN stock s ON s.product_id=p.id
               GROUP BY p.id ORDER BY p.id""",
        ).fetchall()
        items = [db.row_to_dict(r) for r in rows]
        for it in items:
            it["stock_value"] = round(it["total_qty"] * it["cost_price"], 2)
            it["sale_value"] = round(it["total_qty"] * it["sale_price"], 2)
            it["per_store_avg"] = round(it["total_qty"] / it["store_count"], 1) if it["store_count"] else 0
    return {"items": items}


@router.get("/report/profit", summary="毛利与周转报表")
def report_profit():
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT p.id, p.sku, p.name, p.cost_price, p.sale_price,
                      COALESCE(SUM(CASE WHEN m.type='out' THEN -m.change_qty ELSE 0 END),0) AS out_qty,
                      COALESCE(SUM(CASE WHEN m.type='in' THEN m.change_qty ELSE 0 END),0) AS in_qty,
                      COALESCE(SUM(s.quantity),0) AS current_qty
               FROM products p
               LEFT JOIN movements m ON m.product_id=p.id
               LEFT JOIN stock s ON s.product_id=p.id
               GROUP BY p.id ORDER BY p.id""",
        ).fetchall()
        items = [db.row_to_dict(r) for r in rows]
        for it in items:
            unit_profit = it["sale_price"] - it["cost_price"]
            it["unit_profit"] = round(unit_profit, 2)
            it["profit"] = round(it["out_qty"] * unit_profit, 2)
            it["turnover"] = round(it["out_qty"] / it["current_qty"], 2) if it["current_qty"] else 0
        total_profit = round(sum(i["profit"] for i in items), 2)
    return {"items": items, "total_profit": total_profit}


# ---------- Excel 导入导出 ----------
@router.get("/export/inventory.xlsx", summary="导出库存汇总 Excel")
def export_inventory():
    with db.get_conn() as conn:
        rows = conn.execute(
            """SELECT p.sku AS SKU, p.name AS 商品名称, p.spec AS 规格, p.unit AS 单位,
                      p.cost_price AS 成本价, p.sale_price AS 售价, p.low_threshold AS 预警阈值,
                      s.store_id, st.name AS 店铺, s.quantity AS 库存
               FROM stock s JOIN products p ON p.id=s.product_id JOIN stores st ON st.id=s.store_id
               ORDER BY p.id, s.store_id""",
        ).fetchall()
        data = [dict(r) for r in rows]
    df = pd.DataFrame(data)
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, "库存汇总.xlsx")
    df.to_excel(path, index=False, sheet_name="库存汇总")
    return FileResponse(path, filename="库存汇总.xlsx")


@router.post("/import/products", summary="Excel 批量导入商品")
async def import_products(file: UploadFile):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "仅支持 .xlsx / .xls 文件")
    content = await file.read()
    df = pd.read_excel(io.BytesIO(content))
    required = {"sku", "name"}
    if not required.issubset(df.columns):
        raise HTTPException(400, f"Excel 至少需要列：{required}（当前列：{list(df.columns)}）")
    imported, skipped = 0, []
    with db.get_conn() as conn:
        for _, row in df.iterrows():
            sku = str(row.get("sku", "")).strip()
            name = str(row.get("name", "")).strip()
            if not sku or not name:
                continue
            if conn.execute("SELECT id FROM products WHERE sku=?", (sku,)).fetchone():
                skipped.append(sku)
                continue
            cur = conn.execute(
                "INSERT INTO products(sku, name, spec, unit, cost_price, sale_price, low_threshold) VALUES(?,?,?,?,?,?,?)",
                (sku, name, str(row.get("spec", "") or ""), str(row.get("unit", "件") or "件"),
                 float(row.get("cost_price", 0) or 0), float(row.get("sale_price", 0) or 0),
                 int(row.get("low_threshold", 10) or 10)),
            )
            pid = cur.lastrowid
            for s in conn.execute("SELECT id FROM stores").fetchall():
                conn.execute("INSERT INTO stock(product_id, store_id, quantity) VALUES(?,?,0)", (pid, s["id"]))
            imported += 1
    return {"ok": True, "imported": imported, "skipped": skipped}
