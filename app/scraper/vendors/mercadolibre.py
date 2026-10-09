import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from app.scraper.base_strategy import BaseScraperStrategy

class MercadoLibreScraper(BaseScraperStrategy):
    """
    Estrategia de Búsqueda Inteligente para MercadoLibre.
    """
    async def search_offers(self, query: str, model_number: str = None, part_number: str = None, product_name: str = None) -> List[Dict[str, Any]]:
        # 1. Transformar término de búsqueda para Mercado Libre incluyendo modelo y part_number
        query_parts = [product_name or query]
        if model_number and model_number.strip():
            query_parts.append(model_number.strip())
        if part_number and part_number.strip() and part_number.lower() not in (model_number or '').lower():
            query_parts.append(part_number.strip())
            
        search_term = " ".join(query_parts).strip()
        formatted_query = search_term.replace(" ", "-").lower()
        
        # Filtro de condición NUEVO en Mercado Libre Perú: _ITEM*CONDITION_2230284
        search_url = f"https://listado.mercadolibre.com.pe/{formatted_query}_ITEM*CONDITION_2230284"
        
        html = await self.fetch_html(search_url)
        soup = BeautifulSoup(html, "html.parser")
        
        results = []
        # Seleccionamos todas las tarjetas de producto en la cuadrícula (clásica o nueva estructura poly-card)
        items = soup.select(".ui-search-layout__item") or soup.select(".poly-card") or soup.select(".poly-component__content")
        
        for item in items:
            try:
                # Nombre y Link
                title_tag = item.select_one(".ui-search-item__title") or item.select_one(".poly-component__title") or item.select_one("h2")
                link_tag = item.select_one(".ui-search-link") or item.select_one("a.poly-component__title") or item.select_one("h2 a") or item.select_one("a")
                if not title_tag or not link_tag:
                    continue
                    
                name = title_tag.text.strip()
                raw_href = link_tag.get("href", "")
                if not raw_href:
                    continue
                    
                # Limpiar la URL directa del artículo eliminando parámetros de tracking
                clean_url = raw_href.split("?")[0].split("#")[0] if raw_href.startswith("http") else f"https://listado.mercadolibre.com.pe{raw_href}"
                
                # Descartar si el texto de la tarjeta dice reacondicionado o usado
                item_text = item.text.lower()
                if any(w in item_text for w in ["reacondicionado", "usado", "refurbished", "segunda mano", "open box"]):
                    continue
                    
                # VALIDACIÓN ESTRICTA:
                # 1. Producto Nuevo
                # 2. Coincidencia con Part Number (si se especificó)
                # 3. Coincidencia con Modelo (si se especificó)
                # 4. Coincidencia con tipo de producto (no accesorios)
                if not self.is_valid_match(name, product_name or query, model_number=model_number, part_number=part_number):
                    continue
                
                # Moneda y Precio
                curr_tag = item.select_one(".andes-money-amount__currency-symbol")
                curr_symbol = curr_tag.text.strip() if curr_tag else "S/"
                currency_code = "USD" if ("US$" in curr_symbol or "U$S" in curr_symbol or "$" in curr_symbol) else "PEN"

                price_tag = item.select_one(".andes-money-amount__fraction") or item.select_one(".poly-price__current .andes-money-amount__fraction")
                if not price_tag:
                    continue
                    
                price_text = price_tag.text.replace(".", "").replace(",", "").strip()
                price = float(price_text)
                if price <= 0:
                    continue
                
                # Reseñas (Reviews)
                reviews_tag = item.select_one(".ui-search-reviews__rating-number") or item.select_one(".poly-reviews__rating")
                rating = float(reviews_tag.text) if reviews_tag else 0.0
                
                results.append({
                    "name": name,
                    "url": clean_url,
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
            
        results.sort(key=lambda x: (x["price_original"], -x["rating"]))
        
        # Filtro: Descartar basura (precios absurdamente bajos)
        if len(results) > 2:
            avg_price = sum(r["price_original"] for r in results) / len(results)
            results = [r for r in results if r["price_original"] >= avg_price * 0.2]
            
        return results[:5]
