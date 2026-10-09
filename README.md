# web-scraper-cirion - Backend

Este es el backend del sistema de monitoreo inteligente de adquisiciones de hardware IT para Cirion Technologies. El sistema actúa como un **Cazador de Ofertas Autónomo**, rastreando plataformas B2B y de retail en busca de los mejores precios para componentes informáticos, normalizando sus valores y proveyendo un historial de precios consolidado.

## 🚀 Tecnologías Principales
*   **FastAPI**: Framework web moderno, rápido y asíncrono.
*   **SQLAlchemy + asyncpg**: ORM y driver asíncrono para bases de datos relacionales.
*   **PostgreSQL**: Base de datos robusta, estandarizada en 3FN (Tercera Forma Normal).
*   **APScheduler**: Motor de cron interno para la automatización del workflow.
*   **aiohttp + BeautifulSoup4**: Extracción rápida e inteligente de código HTML.
*   **aiolimiter**: Control estricto de Rate Limiting para evitar bloqueos por parte de los proveedores.

## 🏗 Arquitectura del Software
El sistema implementa **Clean Architecture (Multicapa)** combinada con el **Patrón Factory y Strategy**.
1.  **Workflow Autónomo:** A través de un Scheduler configurado internamente, el sistema se despierta, lee los productos a monitorear y despacha la búsqueda de manera paralela.
2.  **Scraper Engine:** Orquesta múltiples "estrategias" (una para cada tienda: Amazon, MercadoLibre, etc.).
3.  **Filtrado Inteligente:** Los scrapers no devuelven toda la basura de la página. Tienen un algoritmo para calificar el "rating", limpiar accesorios (por margen de precio) y devolver únicamente el Top 5 de las ofertas más relevantes de cada proveedor.

## ⚙️ Estructura de Directorios (Resumen)
*   `app/api/`: Rutas HTTP para conectar con el Frontend o Sistemas de Terceros.
*   `app/db/`: Configuración del engine asíncrono de Postgres.
*   `app/models/`: Modelos ORM exactos según el esquema 3FN.
*   `app/scraper/`: El corazón del scraper.
    *   `engine.py`: El orquestador que envía la orden de búsqueda global.
    *   `workflow.py`: El cron job (Scheduler) con Rate Limiting.
    *   `vendors/`: Los extractores puros (Amazon, MercadoLibre, etc.).

## 🛠 Cómo Ejecutar Localmente

1.  **Levantar Base de Datos en Docker** (Usa el puerto 5433 para evitar colisiones):
    ```bash
    docker-compose up -d
    ```

2.  **Activar el Entorno Virtual:**
    ```bash
    .\venv\Scripts\activate
    ```

3.  **Iniciar el Servidor (API y Workflow):**
    ```bash
    uvicorn app.main:app --reload
    ```
    
*(El servidor de desarrollo correrá en http://127.0.0.1:8000)*
