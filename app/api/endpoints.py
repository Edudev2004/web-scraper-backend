from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models.models import Product, ScrapingLog, Brand, ProductCategory, Vendor, Currency, VendorCatalog
from app.schemas.schemas import (
    ProductCreate, 
    ProductResponse, 
    DealResponse, 
    BrandCreate, 
    BrandResponse, 
    CategoryCreate, 
    CategoryResponse,
    CurrencyResponse,
    VendorCreate,
    VendorUpdate,
    VendorResponse
)
from app.scraper.workflow import run_automated_scraping_cycle

router = APIRouter()

@router.post("/scrape/run", summary="Ejecutar el bot scraper de forma manual")
async def trigger_scraper(background_tasks: BackgroundTasks):
    """
    Inicia inmediatamente el ciclo de búsqueda de ofertas en segundo plano.
    No bloquea la petición HTTP, retornando un mensaje de confirmación al instante.
    """
    background_tasks.add_task(run_automated_scraping_cycle)
    return {"message": "El Cazador de Ofertas ha sido enviado a buscar en segundo plano. Los resultados aparecerán en la base de datos pronto."}

@router.post("/products", response_model=ProductResponse, summary="Registrar nuevo término de búsqueda")
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    """
    Agrega un nuevo producto (Término de búsqueda) a la base de datos.
    Nota: Se asume que brand_id y category_id existen en la BD.
    """
    try:
        new_product = Product(
            product_name=product.product_name,
            brand_id=product.brand_id,
            category_id=product.category_id,
            model_number=product.model_number,
            part_number=product.part_number,
            description=product.description
        )
        
        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)
        
        return new_product
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando producto: {str(e)}. Verifica que brand_id y category_id existan.")

@router.get("/products", response_model=List[ProductResponse], summary="Listar productos bajo monitoreo")
async def get_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product))
    products = result.scalars().all()
    return products

@router.delete("/products/{product_id}", summary="Eliminar un término de búsqueda")
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.product_id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    await db.delete(product)
    await db.commit()
    return {"message": "Producto eliminado exitosamente"}

@router.put("/products/{product_id}", response_model=ProductResponse, summary="Actualizar un producto existente")
async def update_product(product_id: int, product_data: ProductCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.product_id == product_id))
    product = result.scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    product.product_name = product_data.product_name
    product.brand_id = product_data.brand_id
    product.category_id = product_data.category_id
    product.model_number = product_data.model_number
    product.part_number = product_data.part_number
    product.description = product_data.description
    
    await db.commit()
    await db.refresh(product)
    return product

@router.get("/deals", response_model=List[DealResponse], summary="Obtener las mejores ofertas capturadas")
async def get_best_deals(db: AsyncSession = Depends(get_db)):
    query = (
        select(
            ScrapingLog.log_id,
            ScrapingLog.scraped_at,
            ScrapingLog.price_original,
            ScrapingLog.price_usd,
            ScrapingLog.stock_status,
            ScrapingLog.raw_data,
            Product.product_name,
            Vendor.vendor_name,
            VendorCatalog.product_url,
            Currency.currency_code,
            Currency.symbol.label("currency_symbol")
        )
        .join(VendorCatalog, ScrapingLog.catalog_id == VendorCatalog.catalog_id)
        .join(Product, VendorCatalog.product_id == Product.product_id)
        .join(Vendor, VendorCatalog.vendor_id == Vendor.vendor_id)
        .outerjoin(Currency, ScrapingLog.currency_id == Currency.currency_id)
        .order_by(ScrapingLog.scraped_at.desc())
        .limit(50)
    )
    result = await db.execute(query)
    rows = result.all()
    
    deals = []
    for r in rows:
        url = (r.raw_data or {}).get("url") if isinstance(r.raw_data, dict) else r.product_url
        offer_title = (r.raw_data or {}).get("name") if isinstance(r.raw_data, dict) else None
        deals.append({
            "log_id": r.log_id,
            "scraped_at": r.scraped_at,
            "price_original": float(r.price_original),
            "currency_code": r.currency_code or "USD",
            "currency_symbol": r.currency_symbol or "$",
            "price_usd": float(r.price_usd),
            "stock_status": r.stock_status.value if hasattr(r.stock_status, 'value') else str(r.stock_status),
            "product_name": r.product_name,
            "vendor_name": r.vendor_name,
            "product_url": url,
            "offer_title": offer_title
        })
        
    return deals


@router.get("/brands", response_model=List[BrandResponse], summary="Obtener todas las marcas")
async def get_brands(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand))
    return result.scalars().all()

@router.post("/brands", response_model=BrandResponse, summary="Crear una nueva marca")
async def create_brand(brand: BrandCreate, db: AsyncSession = Depends(get_db)):
    new_brand = Brand(brand_name=brand.brand_name)
    db.add(new_brand)
    await db.commit()
    await db.refresh(new_brand)
    return new_brand

@router.delete("/brands/{brand_id}", summary="Eliminar una marca")
async def delete_brand(brand_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand).where(Brand.brand_id == brand_id))
    brand = result.scalars().first()
    if not brand:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    
    try:
        await db.delete(brand)
        await db.commit()
        return {"message": "Marca eliminada exitosamente"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="No se puede eliminar esta marca porque está asignada a uno o más objetivos.")

@router.get("/categories", response_model=List[CategoryResponse], summary="Obtener todas las categorias")
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductCategory))
    return result.scalars().all()

@router.post("/categories", response_model=CategoryResponse, summary="Crear una nueva categoria")
async def create_category(cat: CategoryCreate, db: AsyncSession = Depends(get_db)):
    new_cat = ProductCategory(category_name=cat.category_name)
    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)
    return new_cat

@router.delete("/categories/{category_id}", summary="Eliminar una categoria")
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProductCategory).where(ProductCategory.category_id == category_id))
    category = result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    try:
        await db.delete(category)
        await db.commit()
        return {"message": "Categoría eliminada exitosamente"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="No se puede eliminar esta categoría porque está asignada a uno o más objetivos.")

# ==========================================
# ENDPOINTS DE MONEDAS (CURRENCIES)
# ==========================================

@router.get("/currencies", response_model=List[CurrencyResponse], summary="Obtener catálogo de monedas")
async def get_currencies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Currency).order_by(Currency.currency_id))
    return result.scalars().all()

# ==========================================
# ENDPOINTS DE PROVEEDORES (VENDORS)
# ==========================================

@router.get("/vendors", response_model=List[VendorResponse], summary="Obtener todos los proveedores")
async def get_vendors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).order_by(Vendor.vendor_id))
    vendors = result.scalars().all()
    
    # Contar registros de catálogos vinculados a cada proveedor
    counts_res = await db.execute(
        select(VendorCatalog.vendor_id, func.count(VendorCatalog.catalog_id))
        .group_by(VendorCatalog.vendor_id)
    )
    catalog_counts = dict(counts_res.all())
    
    # Estrategias reales implementadas en el motor
    from app.scraper.engine import scraper_engine
    def normalize_name(s: str) -> str:
        return s.lower().replace(" ", "").replace("ú", "u").replace("é", "e").replace("á", "a").replace("í", "i").replace("ó", "o")
    available_drivers = [normalize_name(k) for k in scraper_engine._strategies.keys()]
    
    response = []
    for v in vendors:
        v_dict = {
            "vendor_id": v.vendor_id,
            "vendor_name": v.vendor_name,
            "country_code": v.country_code,
            "website": v.website,
            "contact_email": v.contact_email,
            "default_currency_id": v.default_currency_id,
            "is_active": v.is_active,
            "created_at": v.created_at,
            "currency": v.currency,
            "total_catalogs": catalog_counts.get(v.vendor_id, 0),
            "has_driver": normalize_name(v.vendor_name) in available_drivers
        }
        response.append(v_dict)
    return response

@router.post("/vendors", response_model=VendorResponse, summary="Registrar nuevo proveedor")
async def create_vendor(vendor_in: VendorCreate, db: AsyncSession = Depends(get_db)):
    # Validar que no exista un proveedor con el mismo nombre
    existing = await db.execute(select(Vendor).where(Vendor.vendor_name == vendor_in.vendor_name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail=f"Ya existe un proveedor registrado con el nombre '{vendor_in.vendor_name}'")
    
    new_vendor = Vendor(
        vendor_name=vendor_in.vendor_name,
        country_code=vendor_in.country_code.upper(),
        website=vendor_in.website,
        contact_email=vendor_in.contact_email,
        default_currency_id=vendor_in.default_currency_id,
        is_active=vendor_in.is_active
    )
    db.add(new_vendor)
    await db.commit()
    await db.refresh(new_vendor)
    return new_vendor

@router.put("/vendors/{vendor_id}", response_model=VendorResponse, summary="Actualizar información de proveedor")
async def update_vendor(vendor_id: int, vendor_data: VendorUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).where(Vendor.vendor_id == vendor_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    if vendor_data.vendor_name is not None:
        vendor.vendor_name = vendor_data.vendor_name
    if vendor_data.country_code is not None:
        vendor.country_code = vendor_data.country_code.upper()
    if vendor_data.website is not None:
        vendor.website = vendor_data.website
    if vendor_data.contact_email is not None:
        vendor.contact_email = vendor_data.contact_email
    if vendor_data.default_currency_id is not None:
        vendor.default_currency_id = vendor_data.default_currency_id
    if vendor_data.is_active is not None:
        vendor.is_active = vendor_data.is_active
        
    await db.commit()
    await db.refresh(vendor)
    return vendor

@router.patch("/vendors/{vendor_id}/status", response_model=VendorResponse, summary="Alternar estado activo/inactivo de proveedor")
async def toggle_vendor_status(vendor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).where(Vendor.vendor_id == vendor_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    vendor.is_active = not vendor.is_active
    await db.commit()
    await db.refresh(vendor)
    return vendor

@router.delete("/vendors/{vendor_id}", summary="Eliminar o dar de baja a un proveedor")
async def delete_vendor(vendor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).where(Vendor.vendor_id == vendor_id))
    vendor = result.scalars().first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
    try:
        await db.delete(vendor)
        await db.commit()
        return {"message": "Proveedor eliminado exitosamente"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400, 
            detail="No se puede eliminar este proveedor porque tiene catálogos o registros de scraping históricos vinculados. Puedes desactivarlo en su lugar."
        )
