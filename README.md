# 多店铺进销存管理工具

面向多平台电商卖家（淘宝 / 拼多多 / 抖音小店）的统一库存管理工具。
解决「各平台库存各管各的、容易超卖、对不上账」的痛点：库存总览、出入库、盘点、**店铺库存一键同步**、低库存预警、毛利与周转报表、**Excel 批量导入导出**。

## 功能

- 🏬 多店铺：新增/删除店铺，每个店铺独立库存
- 📦 商品：SKU 主数据（成本价/售价/预警阈值），Excel 批量导入
- ➕ 入库 / ➖ 出库 / 📋 盘点：自动校验库存、记录完整流水（变动前后数量）
- ⇄ 店铺同步：一键把源店铺全部库存覆盖到目标店铺（防止超卖）
- 🚨 低库存预警：库存 ≤ 阈值自动标红、预警列表
- 📊 报表：库存汇总（占用资金）、毛利估算、库存周转率
- 📤📥 Excel：库存汇总导出 .xlsx（pandas 生成）、商品模板导入

## 快速开始

```bash
pip install -r requirements.txt
python run.py            # 默认 127.0.0.1:8001
```

| 入口 | 地址 |
|---|---|
| 使用界面 | http://127.0.0.1:8001/static/index.html |
| 接口文档 | http://127.0.0.1:8001/docs |

首次启动自动写入演示数据：3 个店铺、10 个商品、20 条初始库存流水。

## 目录结构

```
inventory-manager/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── db.py            # SQLite 连接与建表
│   ├── schemas.py       # 请求模型
│   ├── api.py           # 全部业务路由
│   └── seed.py          # 演示数据
├── static/              # 单页前端（原生 HTML/JS）
├── data/                # SQLite 数据文件（自动生成）
├── exports/             # 导出的 Excel（自动生成）
├── run.py
└── requirements.txt
```

## 核心 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/stock | 库存总览（store_id / q / low 筛选） |
| POST | /api/movements | 入库 / 出库 / 盘点 |
| POST | /api/sync | 店铺库存同步（源覆盖目标） |
| GET | /api/alerts | 低库存预警 |
| GET | /api/report/inventory | 库存汇总报表 |
| GET | /api/report/profit | 毛利与周转报表 |
| GET | /api/export/inventory.xlsx | 导出库存 Excel |
| POST | /api/import/products | 导入商品 Excel |

## 说明

- 本地工具，无需登录与数据库安装；如需多人使用可自行加认证并部署。
- 库存变动均为流水式记录（before → after），可追溯每一次操作。
