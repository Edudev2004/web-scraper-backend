import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiolimiter import AsyncLimiter
from sqlalchemy import func
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

async def scrape_search_task(product_id: int, product_name: str, model_number: str, part_number: str, active_vendors_set: set):
    """
    Busca un producto en los proveedores activos con validación estricta de modelo, part number y condición nuevo,
    crea o actualiza el VendorCatalog y guarda los logs con su URL directa y precio real.
    """
    async with global_rate_limiter:
        try:
            query_parts = [product_name]
            if model_number and model_number.strip():
                query_parts.append(model_number.strip())
            if part_number and part_number.strip() and part_number.lower() not in (model_number or '').lower():
                query_parts.append(part_number.strip())
                
            search_term = " ".join(query_parts).strip()
            logger.info(f"[Busqueda] Buscando ofertas para Producto ID {product_id}: '{search_term}' (Modelo: {model_number or 'N/A'}, P/N: {part_number or 'N/A'})")
            
            # Filtrar solo estrategias activas
            results_to_save = {}
            for v_name, strategy in scraper_engine._strategies.items():
                if v_name not in active_vendors_set:
                    logger.info(f"[Pausado] Saltando '{v_name}' (desactivado por el usuario en BD).")
                    continue
                try:
                    top_offers = await strategy.search_offers(
                        query=search_term, 
                        model_number=model_number, 
                        part_number=part_number,
                        product_name=product_name
                    )
                    if top_offers:
                        results_to_save[v_name] = top_offers
                    else:
                        logger.info(f"[Sin Coincidencias] {v_name}: No se encontraron productos nuevos que coincidan estrictamente con el modelo '{model_number}' o P/N '{part_number}'.")
                except Exception as e:
                    logger.error(f"[Error] Fallo busqueda en {v_name}: {str(e)}")
            
            if not results_to_save:
                logger.info(f"[Info] No se guardaron ofertas para '{search_term}' porque no hubo coincidencias válidas.")
                return

            async with async_session() as session:
                logs_creados = 0
                for vendor_name, offers in results_to_save.items():
                    vendor = await get_or_create_vendor(session, vendor_name)
                    catalog = await get_or_create_catalog(session, product_id, vendor.vendor_id)
                    
                    for offer in offers:
                        status_enum = StockStatus.IN_STOCK if offer.get("stock_status") == "IN_STOCK" else StockStatus.UNKNOWN
                        direct_url = offer.get("url")
                        
                        if direct_url:
                            catalog.product_url = direct_url
                            catalog.last_scraped_at = func.now()
                        
                        price_orig = float(offer.get("price_original", 0))
                        currency_code = offer.get("currency_code", "USD")
                        
                        # Conversión básica USD si viene en Soles PEN
                        if currency_code == "PEN":
                            price_usd = round(price_orig / 3.75, 2)
                            curr_id = 2
                        else:
                            price_usd = round(price_orig, 2)
                            curr_id = 1
                        
                        new_log = ScrapingLog(
                            catalog_id=catalog.catalog_id,
                            price_original=price_orig,
                            currency_id=curr_id,
                            exchange_rate_id=1,
                            price_usd=price_usd,
                            stock_status=status_enum,
                            raw_data={
                                "url": direct_url,
                                "name": offer.get("name"),
                                "rating": offer.get("rating")
                            }
                        )
                        session.add(new_log)
                        logs_creados += 1
                        
                await session.commit()
                logger.info(f"[Exito] Se guardaron {logs_creados} ofertas legítimas para '{search_term}'")
                
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

        # Obtener plataformas activas en BD
        active_vendors_res = await session.execute(select(Vendor).where(Vendor.is_active == True))
        active_vendors_set = {v.vendor_name for v in active_vendors_res.scalars().all()}
        
        logger.info(f"[Info] Se buscaran ofertas para {len(products)} productos en plataformas activas: {active_vendors_set}")
        
        tasks = [
            scrape_search_task(
                product_id=p.product_id,
                product_name=p.product_name,
                model_number=p.model_number,
                part_number=p.part_number,
                active_vendors_set=active_vendors_set
            ) 
            for p in products
        ]
        await asyncio.gather(*tasks)
        logger.info("[Fin] Ciclo del Cazador de Ofertas Finalizado.")

scheduler = AsyncIOScheduler()

def start_scheduler():
    scheduler.add_job(run_automated_scraping_cycle, 'interval', hours=12, id='main_scraping_job')
    scheduler.start()
    logger.info("[Scheduler] Iniciado. Ejecutando workflow cada 12 horas.")
