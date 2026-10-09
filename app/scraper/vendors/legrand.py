import logging
from typing import List, Dict, Any
from app.scraper.base_strategy import BaseScraperStrategy

logger = logging.getLogger(__name__)

class LegrandScraper(BaseScraperStrategy):
    """
    Estrategia de Búsqueda para Legrand Perú (Catálogo B2B / Distribución).
    Nota: Legrand opera como fabricante mayorista en Perú. Su catálogo oficial
    requiere consulta técnica o vinculación con distribuidores autorizados.
    """
    async def search_offers(self, query: str, model_number: str = None, part_number: str = None, product_name: str = None) -> List[Dict[str, Any]]:
        search_target = part_number or model_number or query
        logger.info(f"[Legrand Perú] Consultando catálogo para '{search_target}'...")
        
        # En la web oficial legrand.com.pe los precios no son públicos de venta directa.
        # Se estructura la llamada para cuando se enlace el portal con credenciales o API B2B.
        try:
            # Por ahora retorna lista vacía de forma segura hasta recibir credenciales de portal B2B
            return []
        except Exception as e:
            logger.error(f"[Legrand Perú] Error en búsqueda: {str(e)}")
            return []

    def parse_product_page(self, html: str) -> Dict[str, Any]:
        return {
            "price": 0.0,
            "currency": "PEN",
            "stock_status": "UNKNOWN"
        }
