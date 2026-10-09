from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, ForeignKey, DateTime, Enum, func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum

class StockStatus(enum.Enum):
    IN_STOCK = "IN_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PRE_ORDER = "PRE_ORDER"
    UNKNOWN = "UNKNOWN"

class Vendor(Base):
    __tablename__ = "vendors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    domain_url = Column(String(255), nullable=False)
    api_endpoint = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relaciones
    products = relationship("Product", back_populates="vendor")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    parent_category_id = Column(Integer, ForeignKey("categories.id"))
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relación jerárquica (self-referencing)
    subcategories = relationship("Category", back_populates="parent_category")
    parent_category = relationship("Category", back_populates="subcategories", remote_side=[id])
    
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    vendor_product_code = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    specifications_json = Column(Text) # Puedes usar JSONB si usas Postgres específico
    url_link = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relaciones
    vendor = relationship("Vendor", back_populates="products")
    category = relationship("Category", back_populates="products")
    logs = relationship("ScrapingLog", back_populates="product")

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    currency_code = Column(String(3), nullable=False) # ej: USD, EUR, PEN
    rate_to_usd = Column(Numeric(12, 6), nullable=False)
    effective_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class ScrapingLog(Base):
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price_original = Column(Numeric(12, 2), nullable=False)
    currency_code = Column(String(3), nullable=False) # Referencia al código
    price_usd = Column(Numeric(12, 2), nullable=False) # Valor calculado en USD al instante del scrapeo
    stock_status = Column(Enum(StockStatus), nullable=False)
    extracted_at = Column(DateTime, server_default=func.now())
    is_acknowledged = Column(Boolean, default=False)
    
    # Relaciones
    product = relationship("Product", back_populates="logs")
