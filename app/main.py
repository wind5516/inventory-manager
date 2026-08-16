"""多店铺进销存 FastAPI 入口"""
import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .api import router
from .seed import seed_if_empty

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(
    title="多店铺进销存管理工具 API",
    description="多平台店铺统一库存管理：出入库/盘点/库存同步/低库存预警/报表/Excel 导入导出",
    version="1.0.0",
)

db.init_db()
seed_if_empty()

app.include_router(router)


@app.get("/", include_in_schema=False)
def index():
    return RedirectResponse("/static/index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health", tags=["系统"])
def health():
    return {"status": "ok", "service": "inventory-manager"}
