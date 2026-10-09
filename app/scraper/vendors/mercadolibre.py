import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.scraper.base_strategy import BaseScraperStrategy

class MercadoLibreScraper(BaseScraperStrategy):
    """
    Estrategia de Búsqueda Inteligente para MercadoLibre.
    """
    async def search_offers(self, query: str) -> List[Dict[str, Any]]:
        # 1. Transformar el término de búsqueda a la URL de Mercado Libre
        # Ejemplo: "Cisco C9200" -> "https://listado.mercadolibre.com.pe/cisco-c9200"
        formatted_query = query.replace(" ", "-").lower()
        search_url = f"https://listado.mercadolibre.com.pe/{formatted_query}"
        
        html = await self.fetch_html(search_url)
        soup = BeautifulSoup(html, "html.parser")
        
        results = []
        # Seleccionamos todas las tarjetas de producto en la cuadrícula
        items = soup.select(".ui-search-layout__item")
        
        for item in items:
            try:
                # Nombre y Link
                title_tag = item.select_one(".ui-search-item__title")
                link_tag = item.select_one(".ui-search-link")
                if not title_tag or not link_tag:
                    continue
                    
                name = title_tag.text.strip()
                item_url = link_tag.get("href")
                
                # Precio
                price_tag = item.select_one(".andes-money-amount__fraction")
                if not price_tag:
                    continue
                    
                price_text = price_tag.text.replace(".", "").replace(",", "")
                price = float(price_text)
                
                # Reseñas (Reviews) para calificar la calidad de la oferta
                reviews_tag = item.select_one(".ui-search-reviews__rating-number")
                rating = float(reviews_tag.text) if reviews_tag else 0.0
                
                results.append({
                    "name": name,
                    "url": item_url,
                    "price_original": price,
                    "currency_code": "PEN", # ML Perú por defecto
                    "stock_status": "IN_STOCK",
                    "rating": rating
                })
            except Exception:
                continue # Ignoramos tarjetas defectuosas
                
        # --- ANÁLISIS Y FILTRADO INTELIGENTE ---
        # Si no hay resultados, salimos
        if not results:
            return []
            
        # Algoritmo simple: Ordenamos por las que tienen mayor rating y menor precio.
        # En el mundo real se aplica una fórmula de "Score" (ej. rating * 100 - precio).
        # Por ahora, ordenaremos simplemente por precio de menor a mayor
        results.sort(key=lambda x: (x["price_original"], -x["rating"]))
        
        # Filtro: Descartar basura (precios absurdamente bajos que suelen ser accesorios en lugar del equipo)
        # Ejemplo: Promedio de precios, si cuesta menos del 10% del promedio, es un accesorio.
        if len(results) > 2:
            avg_price = sum(r["price_original"] for r in results) / len(results)
            results = [r for r in results if r["price_original"] >= avg_price * 0.2]
            
        # Devolvemos solo el "Top 5" de las mejores ofertas reales encontradas
        top_offers = results[:5]
        
        return top_offers
