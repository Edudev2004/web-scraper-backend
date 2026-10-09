from abc import ABC, abstractmethod
import aiohttp
from typing import Dict, Any, List

class BaseScraperStrategy(ABC):
    """
    Clase base abstracta (Patrón Estrategia) para todos los scrapers de proveedores.
    Obliga a que cualquier proveedor nuevo que agreguemos siga estas mismas reglas.
    """
    def __init__(self):
        # Headers comunes para simular un navegador real y evitar bloqueos básicos
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8"
        }

    async def fetch_html(self, url: str) -> str:
        """Obtiene el HTML crudo de una página de forma asíncrona y eficiente."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status() # Lanza error si la página da 404 o 500
                return await response.text()

    @abstractmethod
    async def search_offers(self, query: str) -> List[Dict[str, Any]]:
        """
        Cada proveedor hijo (ej. ScraperAmazon) DEBE implementar este método con su propia lógica (BeautifulSoup).
        Recibe un término de búsqueda (ej. "Cisco C9200") y debe devolver una lista con las mejores ofertas:
        [
            {
                "name": str,
                "url": str,
                "price_original": float,
                "currency_code": str,
                "stock_status": str,
                "rating": float
            }
        ]
        """
        pass
