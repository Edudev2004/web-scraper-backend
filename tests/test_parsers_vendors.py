import pytest
from unittest.mock import AsyncMock, patch
from app.scraper.vendors.mercadolibre import MercadoLibreScraper
from app.scraper.vendors.amazon import AmazonScraper

# HTML simulado de una tarjeta de MercadoLibre Peru
MOCK_MELI_HTML = """
<div class="ui-search-layout__item">
    <div class="ui-search-result__content-wrapper">
        <a class="ui-search-link" href="https://articulo.mercadolibre.com.pe/MPE-12345678-switch-cisco-c9200l-48p-4x-e?searchVariation=1#position=1">
            <h2 class="ui-search-item__title">Switch Cisco Catalyst C9200L-48P-4X-E 48P PoE+ Nuevo</h2>
        </a>
        <div class="ui-search-price">
            <span class="andes-money-amount__currency-symbol">S/</span>
            <span class="andes-money-amount__fraction">12,500</span>
        </div>
    </div>
</div>
<div class="ui-search-layout__item">
    <div class="ui-search-result__content-wrapper">
        <a class="ui-search-link" href="https://articulo.mercadolibre.com.pe/MPE-99999999-cable-cisco?tracking=abc">
            <h2 class="ui-search-item__title">Cable de consola para Switch Cisco C9200L</h2>
        </a>
        <div class="ui-search-price">
            <span class="andes-money-amount__currency-symbol">S/</span>
            <span class="andes-money-amount__fraction">45</span>
        </div>
    </div>
</div>
"""

# HTML simulado de una tarjeta de Amazon US
MOCK_AMAZON_HTML = """
<div data-component-type="s-search-result">
    <h2>
        <a class="a-link-normal" href="/dp/B08XYZ1234/ref=sr_1_1">
            Switch Cisco Catalyst C9200L-48P-4X-E 48-Port PoE+ Network Switch
        </a>
    </h2>
    <div class="a-price">
        <span class="a-offscreen">$2,850.00</span>
    </div>
</div>
<div data-component-type="s-search-result">
    <h2>
        <a class="a-link-normal" href="/dp/B00RENEWED1/ref=sr_1_2">
            Switch Cisco Catalyst C9200L-48P-4X-E (Renewed)
        </a>
    </h2>
    <div class="a-price">
        <span class="a-offscreen">$1,200.00</span>
    </div>
</div>
"""

@pytest.mark.asyncio
class TestVendorScrapers:
    """
    Pruebas unitarias para parsers de MercadoLibre y Amazon
    utilizando Mocks para simular respuestas HTML sin conexiones de red.
    """

    async def test_mercadolibre_parser_extracts_clean_offers(self):
        scraper = MercadoLibreScraper()
        
        # Simulamos fetch_html con AsyncMock (equivalente a Mockito when().thenReturn())
        with patch.object(scraper, 'fetch_html', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = MOCK_MELI_HTML

            offers = await scraper.search_offers(
                query="Switch Cisco",
                model_number="C9200L-48P-4X-E",
                part_number="C9200L-48P-4X-E",
                product_name="Switch Cisco Catalyst 48 Puertos PoE"
            )

            # Debe haber filtrado el cable accesorio y mantenido solo el switch
            assert len(offers) == 1
            offer = offers[0]
            assert "Switch Cisco Catalyst C9200L-48P-4X-E" in offer["name"]
            assert offer["price_original"] == 12500.0
            assert offer["currency_code"] == "PEN"
            assert "searchVariation" not in offer["url"] # URL limpia sin params

    async def test_amazon_parser_extracts_clean_offers_and_discards_renewed(self):
        scraper = AmazonScraper()

        with patch.object(scraper, 'fetch_html', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = MOCK_AMAZON_HTML

            offers = await scraper.search_offers(
                query="Switch Cisco",
                model_number="C9200L-48P-4X-E",
                part_number="C9200L-48P-4X-E",
                product_name="Switch Cisco Catalyst 48 Puertos PoE"
            )

            # Debe haber filtrado el producto Renewed y mantenido solo el nuevo
            assert len(offers) == 1
            offer = offers[0]
            assert "Switch Cisco Catalyst C9200L-48P-4X-E" in offer["name"]
            assert offer["price_original"] == 2850.0
            assert offer["currency_code"] == "USD"
            assert offer["url"] == "https://www.amazon.com/dp/B08XYZ1234"
