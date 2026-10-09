import logging
from typing import Dict
from .base_strategy import BaseScraperStrategy
from .vendors.mercadolibre import MercadoLibreScraper
from .vendors.amazon import AmazonScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScraperEngine:
    """
    Motor principal (Orquestador). Aplica Factory Pattern para decidir
    qué estrategia (archivo) usar según la URL del proveedor que estemos consultando.
    """
    def __init__(self):
        # Aquí registramos los proveedores disponibles.
        self._strategies: Dict[str, BaseScraperStrategy] = {
            "MercadoLibre": MercadoLibreScraper(),
            "Amazon": AmazonScraper()
        }

    async def search_all_vendors(self, query: str) -> Dict[str, list]:
        """Método principal que envía la búsqueda a todos los proveedores y agrupa los resultados."""
        logger.info(f"[ScraperEngine] Iniciando Cazador de Ofertas para: '{query}'")
        
        all_results = {}
        
        for vendor_name, strategy in self._strategies.items():
            try:
                # Cada estrategia devuelve su Top 5
                top_offers = await strategy.search_offers(query)
                all_results[vendor_name] = top_offers
                logger.info(f"[Exito] {vendor_name}: Encontro {len(top_offers)} ofertas validas.")
            except Exception as e:
                logger.error(f"[Error] Fallo la busqueda en {vendor_name}: {str(e)}")
                all_results[vendor_name] = []
                
        return all_results

# Instancia global (Singleton) del motor
scraper_engine = ScraperEngine()
