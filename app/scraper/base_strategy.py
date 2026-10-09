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
        """
        Obtiene el HTML crudo de una página de forma asíncrona.
        Utiliza el binario curl del sistema para emitir la huella TLS de navegador
        y evitar bloqueos 503 de WAF (Cloudflare/Amazon), con fallback a aiohttp.
        """
        import shutil
        import asyncio
        curl_path = shutil.which("curl.exe") or shutil.which("curl") or "C:\\Windows\\System32\\curl.exe"
        if curl_path:
            # Para Mercado Libre, usar User-Agent indexador para evitar el bloqueo WAF suspicious-traffic-frontend
            if "mercadolibre" in url.lower():
                ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
            else:
                ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                
            args = [
                curl_path,
                "-s",
                "-L",
                "--compressed",
                "-A", ua,
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "-H", "Accept-Language: es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7",
                url
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                text = stdout.decode("utf-8", errors="ignore")
                if len(text) > 1000 and "suspicious-traffic-frontend" not in text:
                    return text
            except Exception:
                pass

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                return await response.text()

    @staticmethod
    def is_valid_match(title: str, product_name: str, model_number: str = None, part_number: str = None) -> bool:
        """
        Filtro estricto de coincidencia:
        1. Solo productos NUEVOS (descarta usados, refurbished, reacondicionados).
        2. Coincidencia estricta con el Part Number si existe (ej. C9200L-48P-4X-E).
        3. Coincidencia estricta con el Modelo si existe (ej. C9200-48P o RB750Gr3).
        4. Coincidencia con la especificacion/marca del producto.
        5. Descarta accesorios si se busca un equipo principal.
        """
        import re
        if not title:
            return False

        title_lower = title.lower()
        title_clean = re.sub(r'[^a-z0-9]', '', title_lower)
        
        # 1. Filtro Condicion: DEBE SER NUEVO, NUNCA USADO NI REACONDICIONADO
        negative_conditions = [
            "renewed", "refurbished", "pre-owned", "used", 
            "reacondicionado", "segunda mano", "usado", "open box", "remanufacturado"
        ]
        if any(neg in title_lower for neg in negative_conditions):
            return False

        # 2. Filtro de Part Number Estricto (si se especifica)
        if part_number and part_number.strip():
            pn_str = part_number.strip().lower()
            pn_clean = re.sub(r'[^a-z0-9]', '', pn_str)
            pn_tokens = [tok for tok in re.split(r'[-_\s/]+', pn_str) if len(tok) >= 2]
            
            exact_pn_match = pn_clean in title_clean
            tokens_pn_match = all(tok in title_lower or tok in title_clean for tok in pn_tokens) if pn_tokens else False
            
            if not (exact_pn_match or tokens_pn_match):
                return False

        # 3. Filtro de Modelo Estricto (si se especifica)
        if model_number and model_number.strip():
            model_str = model_number.strip().lower()
            model_clean = re.sub(r'[^a-z0-9]', '', model_str)
            # Tokens significativos del modelo (ej. 'c9200', '48p')
            model_tokens = [tok for tok in re.split(r'[-_\s/]+', model_str) if len(tok) >= 2]
            
            exact_match = model_clean in title_clean
            tokens_match = all(tok in title_lower or tok in title_clean for tok in model_tokens) if model_tokens else False
            
            if not (exact_match or tokens_match):
                return False

        # 4. Filtro de especificacion del producto (marca / tipo)
        if product_name and product_name.strip():
            name_tokens = [tok.lower() for tok in re.split(r'[-_\s/]+', product_name) if len(tok) >= 3]
            stop_words = {"puertos", "ports", "port", "para", "with", "con", "del", "las", "los", "switch", "router"}
            significant_tokens = [t for t in name_tokens if t not in stop_words]
            if significant_tokens:
                if not any(t in title_lower for t in significant_tokens):
                    return False

        # 5. Filtro de accesorios irrelevantes cuando se busca un equipo principal
        equipment_keywords = ["switch", "router", "firewall", "servidor", "server", "access point"]
        is_equipment_search = any(k in (product_name or '').lower() for k in equipment_keywords)
        if is_equipment_search:
            accessory_keywords = [
                "cable", "power cord", "power supply", "power adapter", 
                "fuente", "alimentaci", "cargador", "charger",
                "ventilador", "cooling fan", "fan", "rack mount", "funda", 
                "soporte", "bracket", "rail kit", "reemplazo", "replacement"
            ]
            # Si el titulo contiene palabras de accesorio pero el usuario busca el equipo principal
            if any(acc in title_lower for acc in accessory_keywords):
                if not any(acc in (product_name or '').lower() for acc in accessory_keywords):
                    return False

        return True

    @abstractmethod
    async def search_offers(self, query: str, model_number: str = None, part_number: str = None, product_name: str = None) -> List[Dict[str, Any]]:
        """
        Cada proveedor hijo (ej. ScraperAmazon, MercadoLibre) DEBE implementar este metodo.
        Recibe query, model_number, part_number y product_name, y devuelve una lista con las ofertas reales encontradas.
        Si no hay coincidencias estrictas, DEBE retornar una lista vacia [].
        """
        pass

