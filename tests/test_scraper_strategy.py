import pytest
from app.scraper.base_strategy import BaseScraperStrategy

class TestScraperStrategyValidation:
    """
    Pruebas unitarias para las reglas de validacion y filtrado estricto
    definidas en BaseScraperStrategy.is_valid_match().
    """

    def test_should_accept_valid_new_product_matching_model_and_pn(self):
        title = "Switch Cisco Catalyst C9200L-48P-4X-E 48 Puertos PoE+ Nuevo Original"
        product_name = "Switch Cisco Catalyst 48 Puertos PoE"
        model_number = "C9200L-48P-4X-E"
        part_number = "C9200L-48P-4X-E"

        result = BaseScraperStrategy.is_valid_match(
            title=title,
            product_name=product_name,
            model_number=model_number,
            part_number=part_number
        )
        assert result is True

    @pytest.mark.parametrize("negative_keyword", [
        "usado",
        "reacondicionado",
        "refurbished",
        "renewed",
        "open box",
        "segunda mano",
        "pre-owned",
        "remanufacturado"
    ])
    def test_should_reject_used_or_refurbished_products(self, negative_keyword):
        title = f"Switch Cisco Catalyst C9200L-48P-4X-E ({negative_keyword})"
        result = BaseScraperStrategy.is_valid_match(
            title=title,
            product_name="Switch Cisco",
            model_number="C9200L-48P-4X-E",
            part_number="C9200L-48P-4X-E"
        )
        assert result is False

    @pytest.mark.parametrize("accessory_keyword", [
        "cable de alimentacion",
        "power cord",
        "fuente de poder",
        "cooling fan ventilador",
        "rack mount bracket soporte",
        "rail kit de montaje",
        "reemplazo replacement"
    ])
    def test_should_reject_accessories_when_searching_main_equipment(self, accessory_keyword):
        title = f"Cisco {accessory_keyword} para Catalyst C9200L-48P-4X-E"
        result = BaseScraperStrategy.is_valid_match(
            title=title,
            product_name="Switch Cisco Catalyst",
            model_number="C9200L-48P-4X-E",
            part_number="C9200L-48P-4X-E"
        )
        assert result is False

    def test_should_reject_different_part_number(self):
        title = "Switch Cisco Catalyst C9200L-24T-4G-E 24 Puertos Nuevo"
        result = BaseScraperStrategy.is_valid_match(
            title=title,
            product_name="Switch Cisco Catalyst",
            model_number="C9200L-48P-4X-E",
            part_number="C9200L-48P-4X-E"
        )
        assert result is False

    def test_should_accept_mikrotik_router_match(self):
        title = "Router MikroTik hEX RB750Gr3 Gigabit 5 Puertos RouterOS L4 Nuevo"
        product_name = "Router Mikrotik hEX"
        model_number = "RB750Gr3"
        part_number = "RB750Gr3"

        result = BaseScraperStrategy.is_valid_match(
            title=title,
            product_name=product_name,
            model_number=model_number,
            part_number=part_number
        )
        assert result is True

    def test_should_return_false_for_empty_title(self):
        assert BaseScraperStrategy.is_valid_match("", "Switch Cisco") is False
        assert BaseScraperStrategy.is_valid_match(None, "Switch Cisco") is False
