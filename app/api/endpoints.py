from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.database import get_db
from app.models.models import Product, ScrapingLog
from app.schemas.schemas import ProductCreate, ProductResponse, DealResponse
from app.scraper.workflow import run_automated_scraping_cycle

router = APIRouter()

@router.post("/scrape/run", summary="Ejecutar el bot scraper de forma manual")
async def trigger_scraper(background_tasks: BackgroundTasks):
    """
    Inicia inmediatamente el ciclo de búsqueda de ofertas en segundo plano.
    No bloquea la petición HTTP, retornando un mensaje de confirmación al instante.
    """
    background_tasks.add_task(run_automated_scraping_cycle)
    return {"message": "El Cazador de Ofertas ha sido enviado a buscar en segundo plano. Los resultados aparecerán en la base de datos pronto."}

@router.post("/products", response_model=ProductResponse, summary="Registrar nuevo término de búsqueda")
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db)):
    """
    Agrega un nuevo producto (Término de búsqueda) a la base de datos.
    Nota: Se asume que brand_id y category_id existen en la BD.
    """
    try:
        new_product = Product(
            product_name=product.product_name,
            brand_id=product.brand_id,
            category_id=product.category_id,
            model_number=product.model_number,
            part_number=product.part_number
        )
        
        db.add(new_product)
        await db.commit()
        await db.refresh(new_product)
        
        return new_product
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando producto: {str(e)}. Verifica que brand_id y category_id existan.")

@router.get("/products", response_model=List[ProductResponse], summary="Listar productos bajo monitoreo")
async def get_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product))
    products = result.scalars().all()
    return products

@router.get("/deals", summary="Obtener las mejores ofertas capturadas")
async def get_best_deals(db: AsyncSession = Depends(get_db)):
    # Limitando a los ultimos 50 logs por ahora
    query = select(ScrapingLog).order_by(ScrapingLog.scraped_at.desc()).limit(50)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    deals = []
    for log in logs:
        deals.append({
            "log_id": log.log_id,
            "scraped_at": log.scraped_at,
            "price_usd": float(log.price_usd),
            "stock_status": log.stock_status.value
        })
        
    return deals
