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

    async def search_offers(self, query: str) -> List[Dict[str, Any]]:
        # 1. Transformar término de búsqueda para Amazon
        formatted_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.amazon.com/s?k={formatted_query}"
        
        html = await self.fetch_html(search_url)
        soup = BeautifulSoup(html, "html.parser")
        
        results = []
        # Seleccionar tarjetas de productos en la búsqueda
        items = soup.select('div[data-component-type="s-search-result"]')
        
        for item in items:
            try:
                # Nombre y Link
                title_tag = item.select_one("h2 a span")
                link_tag = item.select_one("h2 a")
                
                if not title_tag or not link_tag:
                    continue
                    
                name = title_tag.text.strip()
                item_url = "https://www.amazon.com" + link_tag.get("href")
                
                # Precio
                price_whole = item.select_one(".a-price-whole")
                price_fraction = item.select_one(".a-price-fraction")
                
                if not price_whole:
                    continue
                    
                price_text = price_whole.text.replace(",", "").replace(".", "") + "." + (price_fraction.text if price_fraction else "00")
                price = float(price_text)
                
                # Reseñas
                rating_tag = item.select_one(".a-icon-star-small .a-icon-alt")
                rating = 0.0
                if rating_tag:
                    # Ej: "4.5 out of 5 stars" -> 4.5
                    rating_match = re.search(r'([\d.]+)', rating_tag.text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                        
                results.append({
                    "name": name,
                    "url": item_url,
                    "price_original": price,
                    "currency_code": "USD",
                    "stock_status": "IN_STOCK",
                    "rating": rating
                })
            except Exception:
                continue
                
        # --- ANÁLISIS Y FILTRADO INTELIGENTE ---
        if not results:
            return []
            
        # Ordenamos combinando precio y rating
        results.sort(key=lambda x: (x["price_original"], -x["rating"]))
        
        # Filtro Anti-Basura
        if len(results) > 2:
            avg_price = sum(r["price_original"] for r in results) / len(results)
            results = [r for r in results if r["price_original"] >= avg_price * 0.2]
            
        return results[:5]
