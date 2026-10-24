import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db

@pytest.fixture
def client():
    """
    Cliente de pruebas de FastAPI (equivalente a MockMvc en Spring Boot).
    Parchea el scheduler para evitar inicios de tareas de fondo en tests.
    """
    with patch("app.main.start_scheduler"):
        with TestClient(app) as test_client:
            yield test_client

class TestApiEndpoints:
    """
    Pruebas de integracion/endpoints HTTP para la API de FastAPI.
    """

    def test_root_endpoint_returns_welcome_message(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "correctamente" in data["message"]

    def test_trigger_scraper_returns_background_confirmation(self, client):
        with patch("app.api.endpoints.run_automated_scraping_cycle") as mock_cycle:
            response = client.post("/api/scrape/run")
            assert response.status_code == 200
            data = response.json()
            assert "Cazador de Ofertas" in data["message"]

    def test_get_products_with_mocked_db(self, client):
        # Simulamos la sesion de BD inyectada (equivalente a mockear el EntityManager / Repository)
        mock_session = AsyncMock()
        mock_result = MagicMock()
        
        # Simular dos productos de prueba
        mock_prod_1 = MagicMock()
        mock_prod_1.product_id = 1
        mock_prod_1.product_name = "Switch Cisco Catalyst"
        mock_prod_1.brand_id = 1
        mock_prod_1.category_id = 1
        mock_prod_1.model_number = "C9200L-48P-4X-E"
        mock_prod_1.part_number = "C9200L-48P-4X-E"
        mock_prod_1.description = "Switch 48P"
        mock_prod_1.created_at = "2026-10-24T00:00:00"
        mock_prod_1.brand = None
        mock_prod_1.category = None

        mock_result.scalars.return_value.all.return_value = [mock_prod_1]
        mock_session.execute.return_value = mock_result

        async def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = client.get("/api/products")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["product_id"] == 1
            assert data[0]["model_number"] == "C9200L-48P-4X-E"
        finally:
            app.dependency_overrides.clear()
