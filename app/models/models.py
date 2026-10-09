import enum
from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, ForeignKey, DateTime, Enum, SmallInteger, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base

class StockStatus(enum.Enum):
    IN_STOCK = 'IN_STOCK'
    OUT_OF_STOCK = 'OUT_OF_STOCK'
    LIMITED = 'LIMITED'
    UNKNOWN = 'UNKNOWN'

class Currency(Base):
    __tablename__ = 'currencies'
    currency_id = Column(SmallInteger, primary_key=True, index=True)
    currency_code = Column(String(3), nullable=False, unique=True)
    currency_name = Column(String(50), nullable=False)
    symbol = Column(String(5), nullable=False)

class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'
    exchange_rate_id = Column(BigInteger, primary_key=True)
    currency_id = Column(SmallInteger, ForeignKey('currencies.currency_id'), nullable=False)
    rate_to_usd = Column(Numeric(18, 6), nullable=False)
    rate_date = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(100))

class ProductCategory(Base):
    __tablename__ = 'product_categories'
    category_id = Column(SmallInteger, primary_key=True)
    category_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    parent_category_id = Column(SmallInteger, ForeignKey('product_categories.category_id'))

class Brand(Base):
    __tablename__ = 'brands'
    brand_id = Column(SmallInteger, primary_key=True)
    brand_name = Column(String(100), nullable=False, unique=True)
    website = Column(String(512))

class Product(Base):
    __tablename__ = 'products'
    product_id = Column(Integer, primary_key=True)
    product_name = Column(String(255), nullable=False)
    brand_id = Column(SmallInteger, ForeignKey('brands.brand_id'), nullable=False)
    category_id = Column(SmallInteger, ForeignKey('product_categories.category_id'), nullable=False)
    model_number = Column(String(100))
    part_number = Column(String(100))
    description = Column(Text)
    specifications = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    brand = relationship("Brand", lazy="joined")
    category = relationship("ProductCategory", lazy="joined")

class Vendor(Base):
    __tablename__ = 'vendors'
    vendor_id = Column(Integer, primary_key=True)
    vendor_name = Column(String(255), nullable=False)
    country_code = Column(String(2), nullable=False)
    website = Column(String(512))
    contact_email = Column(String(255))
    default_currency_id = Column(SmallInteger, ForeignKey('currencies.currency_id'), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    currency = relationship("Currency", lazy="joined")

class VendorCatalog(Base):
    __tablename__ = 'vendor_catalog'
    catalog_id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.product_id'), nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendors.vendor_id'), nullable=False)
    vendor_sku = Column(String(150), nullable=False)
    product_url = Column(String(2048), nullable=False)
    currency_id = Column(SmallInteger, ForeignKey('currencies.currency_id'), nullable=False)
    scraping_enabled = Column(Boolean, nullable=False, default=True)
    scraping_frequency = Column(Integer, nullable=False, default=60)
    last_scraped_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ScrapingLog(Base):
    __tablename__ = 'scraping_logs'
    log_id = Column(BigInteger, primary_key=True)
    catalog_id = Column(Integer, ForeignKey('vendor_catalog.catalog_id'), nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    price_original = Column(Numeric(18, 4), nullable=False)
    currency_id = Column(SmallInteger, ForeignKey('currencies.currency_id'), nullable=False)
    exchange_rate_id = Column(BigInteger, ForeignKey('exchange_rates.exchange_rate_id'), nullable=False)
    price_usd = Column(Numeric(18, 4), nullable=False)
    stock_status = Column(Enum(StockStatus, name="stock_status_t", create_type=False), nullable=False, default=StockStatus.UNKNOWN)
    stock_quantity = Column(Integer)
    http_status_code = Column(SmallInteger)
    scraping_ms = Column(Integer)
    error_message = Column(Text)
    raw_data = Column(JSONB)
