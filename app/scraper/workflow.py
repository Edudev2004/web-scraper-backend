import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiolimiter import AsyncLimiter
from sqlalchemy.future import select
from app.db.database import async_session
from app.models.models import Product, ScrapingLog, Vendor, VendorCatalog, StockStatus
from app.scraper.engine import scraper_engine

logger = logging.getLogger(__name__)

# Creamos un Rate Limiter: Máximo 1 petición cada 2 segundos por defecto
global_rate_limiter = AsyncLimiter(max_rate=1, time_period=2.0)

async def get_or_create_vendor(session, vendor_name: str) -> Vendor:
    result = await session.execute(select(Vendor).where(Vendor.vendor_name == vendor_name))
    vendor = result.scalars().first()
    if not vendor:
        vendor = Vendor(vendor_name=vendor_name, country_code='US', default_currency_id=1)
        session.add(vendor)
        await session.flush()
    return vendor

async def get_or_create_catalog(session, product_id: int, vendor_id: int) -> VendorCatalog:
    result = await session.execute(select(VendorCatalog).where(
        VendorCatalog.product_id == product_id,
        VendorCatalog.vendor_id == vendor_id
    ))
    catalog = result.scalars().first()
    if not catalog:
        catalog = VendorCatalog(
            product_id=product_id, 
            vendor_id=vendor_id, 
            vendor_sku=f"SKU-AUTO-{product_id}-{vendor_id}",
            product_url=f"https://{vendor_id}.com/search?q={product_id}",
            currency_id=1
        )
        session.add(catalog)
        await session.flush()
    return catalog

async def scrape_search_task(product_id: int, search_term: str):
    """
    Busca un producto en todos los proveedores, crea dinámicamente
    el Vendor y el VendorCatalog si no existen, y guarda los logs.
    """
    async with global_rate_limiter:
        try:
            logger.info(f"[Busqueda] Ofertas para el Producto ID {product_id} - '{search_term}'")
            all_vendors_results = await scraper_engine.search_all_vendors(search_term)
            
            async with async_session() as session:
                logs_creados = 0
                for vendor_name, offers in all_vendors_results.items():
                    vendor = await get_or_create_vendor(session, vendor_name)
                    catalog = await get_or_create_catalog(session, product_id, vendor.vendor_id)
                    
                    for offer in offers:
                        status_enum = StockStatus.IN_STOCK if offer.get("stock_status") == "IN_STOCK" else StockStatus.UNKNOWN
                        
                        new_log = ScrapingLog(
                            catalog_id=catalog.catalog_id,
                            price_original=offer.get("price_original", 0),
                            currency_id=1,
                            exchange_rate_id=1,
                            price_usd=offer.get("price_original", 0),
                            stock_status=status_enum,
                        )
                        session.add(new_log)
                        logs_creados += 1
                        
                await session.commit()
                logger.info(f"[Exito] Se guardaron {logs_creados} ofertas para '{search_term}'")
                
        except Exception as e:
            logger.error(f"[Error] Buscando el producto {product_id}: {str(e)}")


async def run_automated_scraping_cycle():
    """Workflow Principal (Cazador de Ofertas)"""
    logger.info("[Inicio] Ciclo Automatizado del Cazador de Ofertas...")
    
    async with async_session() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        
        if not products:
            logger.warning("No hay productos/terminos en la base de datos para buscar.")
            return

        logger.info(f"[Info] Se buscaran ofertas para {len(products)} productos.")
        
        tasks = [scrape_search_task(p.product_id, p.product_name) for p in products]
        await asyncio.gather(*tasks)
        logger.info("[Fin] Ciclo del Cazador de Ofertas Finalizado.")

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(run_automated_scraping_cycle, 'interval', hours=12, id='main_scraping_job')
    scheduler.start()
    logger.info("[Scheduler] Iniciado. Ejecutando workflow cada 12 horas.")
