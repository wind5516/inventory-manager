"""演示数据：店铺 / 商品 / 初始库存 / 示例流水"""
from . import db

STORES = [
    ("淘宝旗舰店", "淘宝", "主力店铺"),
    ("拼多多专卖店", "拼多多", "走量店铺"),
    ("抖音小店", "抖音", "直播带货"),
]

PRODUCTS = [
    ("T0001", "基础纯棉白T", "L/白色", "件", 25.0, 59.0, 20),
    ("T0002", "潮流印花T恤", "XL/黑色", "件", 38.0, 89.0, 15),
    ("H0001", "加绒连帽卫衣", "L/灰色", "件", 62.0, 139.0, 10),
    ("H0002", "美式复古圆领卫衣", "M/藏青", "件", 55.0, 129.0, 8),
    ("J0001", "飞行员夹克", "L/军绿", "件", 95.0, 219.0, 5),
    ("F0001", "中长款风衣", "M/卡其", "件", 110.0, 259.0, 5),
    ("K0001", "宽松直筒休闲裤", "32/黑色", "条", 45.0, 109.0, 12),
    ("K0002", "束脚运动裤", "L/深灰", "条", 48.0, 119.0, 10),
    ("A0001", "棒球帽", "均码/黑", "顶", 15.0, 49.0, 30),
    ("A0002", "纯色帆布腰带", "均码/棕", "条", 10.0, 39.0, 25),
]

INIT_STOCK = [  # (sku, store_index, qty)
    ("T0001", 0, 120), ("T0001", 1, 80), ("T0001", 2, 40),
    ("T0002", 0, 60), ("T0002", 1, 90),
    ("H0001", 0, 30), ("H0001", 2, 15),
    ("H0002", 1, 25), ("H0002", 2, 6),
    ("J0001", 0, 12), ("F0001", 0, 8), ("F0001", 1, 4),
    ("K0001", 0, 50), ("K0001", 2, 22),
    ("K0002", 0, 35), ("K0002", 1, 18),
    ("A0001", 0, 150), ("A0001", 2, 80),
    ("A0002", 0, 120), ("A0002", 1, 60),
]


def seed_if_empty() -> None:
    with db.get_conn() as conn:
        if conn.execute("SELECT COUNT(*) c FROM products").fetchone()["c"]:
            return
        for i, (name, platform, remark) in enumerate(STORES):
            conn.execute("INSERT INTO stores(name, platform, remark) VALUES(?,?,?)", (name, platform, remark))
        for sku, name, spec, unit, cost, sale, threshold in PRODUCTS:
            conn.execute(
                "INSERT INTO products(sku, name, spec, unit, cost_price, sale_price, low_threshold) VALUES(?,?,?,?,?,?,?)",
                (sku, name, spec, unit, cost, sale, threshold),
            )
        for sku, store_idx, qty in INIT_STOCK:
            pid = conn.execute("SELECT id FROM products WHERE sku=?", (sku,)).fetchone()["id"]
            conn.execute("INSERT INTO stock(product_id, store_id, quantity) VALUES(?,?,?)", (pid, store_idx + 1, qty))
            conn.execute(
                "INSERT INTO movements(product_id, store_id, type, change_qty, before_qty, after_qty, remark) VALUES(?,?,?,?,?,?,'初始库存')",
                (pid, store_idx + 1, "in", qty, 0, qty),
            )
    print("[seed] 进销存演示数据已写入：3 个店铺 / 10 个商品")
