import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiolimiter import AsyncLimiter
from sqlalchemy.future import select
from app.db.database import async_session
from app.models.models import Product, ScrapingLog
from app.scraper.engine import scraper_engine

logger = logging.getLogger(__name__)

# Creamos un Rate Limiter: Máximo 1 petición cada 2 segundos por defecto
# Esto evita que nos bloqueen la IP (HTTP 429 Too Many Requests)
global_rate_limiter = AsyncLimiter(max_rate=1, time_period=2.0)

async def scrape_search_task(product_id: int, search_term: str):
    """
    Realiza la búsqueda de un producto en TODOS los proveedores disponibles,
    respeta el Rate Limit, y guarda el Top 5 de cada uno en la BD.
    """
    async with global_rate_limiter: # Espera su turno si hay muchas peticiones
        try:
            logger.info(f"[Busqueda] Ofertas para el Producto ID {product_id} - '{search_term}'")
            
            # Llama al orquestador para buscar en Amazon, ML, etc.
            all_vendors_results = await scraper_engine.search_all_vendors(search_term)
            
            # Guardamos todos los resultados en la BD
            async with async_session() as session:
                logs_creados = 0
                for vendor_name, offers in all_vendors_results.items():
                    for offer in offers:
                        new_log = ScrapingLog(
                            product_id=product_id,
                            price_original=offer["price_original"],
                            currency_code=offer["currency_code"],
                            price_usd=offer["price_original"], # TODO: Aplicar tipo de cambio real
                            stock_status=offer["stock_status"],
                        )
                        session.add(new_log)
                        logs_creados += 1
                        
                await session.commit()
                logger.info(f"[Exito] Se guardaron {logs_creados} ofertas encontradas para '{search_term}'")
                
        except Exception as e:
            logger.error(f"[Error] Buscando el producto {product_id}: {str(e)}")


async def run_automated_scraping_cycle():
    """
    Workflow Principal (Cazador de Ofertas).
    """
    logger.info("[Inicio] Ciclo Automatizado del Cazador de Ofertas...")
    
    async with async_session() as session:
        result = await session.execute(select(Product))
        products = result.scalars().all()
        
        if not products:
            logger.warning("No hay productos/terminos en la base de datos para buscar.")
            return

        logger.info(f"[Info] Se buscaran ofertas para {len(products)} productos.")
        
        # Encolamos las búsquedas
        tasks = [
            scrape_search_task(p.id, p.name) # Usamos el nombre del producto como término de búsqueda
            for p in products
        ]
        
        await asyncio.gather(*tasks)
        logger.info("[Fin] Ciclo del Cazador de Ofertas Finalizado.")

# Instancia global del Scheduler
scheduler = AsyncIOScheduler()

def start_scheduler():
    """Inicia el cron configurable"""
    # Aquí podríamos leer la frecuencia de la BD tal como en JungleClick.
    # Por ahora lo configuramos cada 12 horas como ejemplo
    scheduler.add_job(run_automated_scraping_cycle, 'interval', hours=12, id='main_scraping_job')
    scheduler.start()
    logger.info("[Scheduler] Iniciado. Ejecutando workflow cada 12 horas.")
