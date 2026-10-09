from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProductCreate(BaseModel):
    product_name: str
    brand_id: int
    category_id: int
    model_number: Optional[str] = None
    part_number: Optional[str] = None
    description: Optional[str] = None

class BrandCreate(BaseModel):
    brand_name: str

class BrandResponse(BaseModel):
    brand_id: int
    brand_name: str
    
    class Config:
        orm_mode = True

class CategoryCreate(BaseModel):
    category_name: str

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
    description: Optional[str] = None
    
    class Config:
        orm_mode = True

class DealResponse(BaseModel):
    log_id: int
    scraped_at: datetime
    price_original: float
    currency_code: str = "USD"
    currency_symbol: str = "$"
    price_usd: float
    stock_status: str
    product_name: str
    vendor_name: str
    product_url: str
    offer_title: Optional[str] = None
    
    class Config:
        orm_mode = True

class CurrencyResponse(BaseModel):
    currency_id: int
    currency_code: str
    currency_name: str
    symbol: str

    class Config:
        orm_mode = True

class VendorCreate(BaseModel):
    vendor_name: str
    country_code: str = "US"
    website: Optional[str] = None
    contact_email: Optional[str] = None
    default_currency_id: int = 1
    is_active: bool = True

class VendorUpdate(BaseModel):
    vendor_name: Optional[str] = None
    country_code: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    default_currency_id: Optional[int] = None
    is_active: Optional[bool] = None

class VendorResponse(BaseModel):
    vendor_id: int
    vendor_name: str
    country_code: str
    website: Optional[str] = None
    contact_email: Optional[str] = None
    default_currency_id: int
    is_active: bool
    created_at: datetime
    currency: Optional[CurrencyResponse] = None
    total_catalogs: int = 0
    has_driver: bool = True

    class Config:
        orm_mode = True
