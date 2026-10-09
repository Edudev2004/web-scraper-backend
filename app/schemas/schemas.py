from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProductCreate(BaseModel):
    product_name: str
    brand_id: int
    category_id: int
    model_number: Optional[str] = None
    part_number: Optional[str] = None

class BrandResponse(BaseModel):
    brand_id: int
    brand_name: str
    
    class Config:
        orm_mode = True

class CategoryResponse(BaseModel):
    category_id: int
    category_name: str
    
    class Config:
        orm_mode = True

class ProductResponse(BaseModel):
    product_id: int
    product_name: str
    brand: Optional[BrandResponse] = None
    category: Optional[CategoryResponse] = None
    model_number: Optional[str] = None
    part_number: Optional[str] = None
    
    class Config:
        orm_mode = True

class DealResponse(BaseModel):
    log_id: int
    scraped_at: datetime
    price_usd: float
    stock_status: str
    
    class Config:
        orm_mode = True
