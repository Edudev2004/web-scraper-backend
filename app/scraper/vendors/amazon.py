import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.scraper.base_strategy import BaseScraperStrategy

class AmazonScraper(BaseScraperStrategy):
    """
    Estrategia de Búsqueda Inteligente para Amazon.
    """
    def __init__(self):
        super().__init__()
        self.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })

    async def search_offers(self, query: str, model_number: str = None, part_number: str = None, product_name: str = None) -> List[Dict[str, Any]]:
        # 1. Transformar término de búsqueda para Amazon incluyendo modelo y part_number si existen
        query_parts = [product_name or query]
        if model_number and model_number.strip():
            query_parts.append(model_number.strip())
        if part_number and part_number.strip() and part_number.lower() not in (model_number or '').lower():
            query_parts.append(part_number.strip())
            
        search_term = " ".join(query_parts).strip()
        formatted_query = urllib.parse.quote_plus(search_term)
        
        # Filtro de condición NUEVO en Amazon: &rh=p_n_condition-type%3A2224371011
        search_url = f"https://www.amazon.com/s?k={formatted_query}&rh=p_n_condition-type%3A2224371011"
        
        html = await self.fetch_html(search_url)
        soup = BeautifulSoup(html, "html.parser")
        
        results = []
        # Seleccionar tarjetas de productos en la búsqueda
        items = soup.select('div[data-component-type="s-search-result"]')
        
        for item in items:
            try:
                # Extraer título real del producto (evitando solo el brand)
                title = ""
                for h2 in item.select("h2"):
                    t = h2.text.strip()
                    if len(t) > len(title):
                        title = t
                
                # Extraer ASIN y enlace directo al producto (/dp/ASIN)
                asin = None
                for a in item.select('a[href*="/dp/"]'):
                    href = a.get("href", "")
                    m = re.search(r'/dp/([A-Z0-9]{10})', href)
                    if m:
                        asin = m.group(1)
                        # Si no teníamos título largo, el texto del enlace puede tenerlo
                        t_a = a.text.strip()
                        if len(t_a) > len(title) and not t_a.startswith("("):
                            title = t_a
                        break
                        
                if not asin or not title:
                    continue
                    
                direct_url = f"https://www.amazon.com/dp/{asin}"
                
                # VALIDACIÓN ESTRICTA:
                # 1. Producto Nuevo (sin reacondicionados/usados)
                # 2. Coincidencia con Part Number (si se especificó)
                # 3. Coincidencia con Modelo (si se especificó)
                # 4. Coincidencia con tipo de producto (no accesorios)
                if not self.is_valid_match(title, product_name or query, model_number=model_number, part_number=part_number):
                    continue
                
                # Extraer Precio
                price_tag = item.select_one(".a-price .a-offscreen") or item.select_one(".a-price-whole")
                if not price_tag:
                    # Si la tarjeta de búsqueda no tiene precio directo (ej. "Ver opciones de compra"),
                    # consultamos directamente la página del producto directo (/dp/ASIN)
                    try:
                        detail_html = await self.fetch_html(direct_url)
                        detail_soup = BeautifulSoup(detail_html, "html.parser")
                        price_tag = (
                            detail_soup.select_one(".a-price .a-offscreen") 
                            or detail_soup.select_one("#priceblock_ourprice") 
                            or detail_soup.select_one(".a-price")
                        )
                    except Exception:
                        pass

                if not price_tag:
                    continue
                    
                # Moneda y Precio
                raw_price_str = price_tag.text
                currency_code = "PEN" if ("PEN" in raw_price_str or "S/" in raw_price_str) else "USD"
                clean_num_str = raw_price_str.replace(',', '').replace('$', '').replace('PEN', '').replace('S/', '').strip()
                match = re.search(r'(\d+\.?\d*)', clean_num_str)
                if not match:
                    continue
                price = float(match.group(1))
                if price <= 0:
                    continue
                
                # Reseñas
                rating_tag = item.select_one(".a-icon-star-small .a-icon-alt") or item.select_one(".a-icon-alt")
                rating = 0.0
                if rating_tag:
                    rating_match = re.search(r'([\d.]+)', rating_tag.text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        
                results.append({
                    "name": title,
                    "url": direct_url,
                    "price_original": price,
                    "currency_code": currency_code,
                    "stock_status": "IN_STOCK",
                    "rating": rating
                })
            except Exception:
                continue
                
        # Si no hay coincidencias estrictas con el producto y modelo nuevo, NO DEVOLVER BASURA NI FALLBACKS
        if not results:
            return []
            
        # Ordenamos por precio
        results.sort(key=lambda x: (x["price_original"], -x["rating"]))
        
        # Filtro Anti-Basura (descartar precios anómalamente bajos)
        if len(results) > 2:
            avg_price = sum(r["price_original"] for r in results) / len(results)
            results = [r for r in results if r["price_original"] >= avg_price * 0.2]
            
        return results[:5]
