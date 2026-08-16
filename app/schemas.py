"""请求模型"""
from typing import Optional

from pydantic import BaseModel, Field


class ProductIn(BaseModel):
    sku: str
    name: str
    spec: str = ""
    unit: str = "件"
    cost_price: float = Field(default=0, ge=0)
    sale_price: float = Field(default=0, ge=0)
    low_threshold: int = Field(default=10, ge=0)


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = Field(default=None, ge=0)
    sale_price: Optional[float] = Field(default=None, ge=0)
    low_threshold: Optional[int] = Field(default=None, ge=0)


class StoreIn(BaseModel):
    name: str
    platform: str = ""
    remark: str = ""


class MovementIn(BaseModel):
    product_id: int
    store_id: int
    type: str = Field(pattern="^(in|out|check)$")
    quantity: int = Field(default=0, ge=0)      # in/out 使用
    actual_qty: Optional[int] = Field(default=None, ge=0)  # check 使用
    remark: str = ""


class SyncIn(BaseModel):
    source_store_id: int
    target_store_id: int
