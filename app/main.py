from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.scraper.workflow import start_scheduler
from app.api.endpoints import router as api_router

app = FastAPI(
    title="web-scraper-cirion API",
    description="Backend para el Web Scraper de componentes IT de Cirion Technologies",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conectando las rutas creadas
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    start_scheduler()
    print("\n" + "="*50)
    print("SERVIDOR WEB SCRAPER INICIADO")
    print("="*50)
    print("API Principal: http://127.0.0.1:8000")
    print("Documentacion Swagger: http://127.0.0.1:8000/docs")
    print("="*50 + "\n")

@app.get("/")
async def root():
    return {"message": "¡API funcionando correctamente! Lista para conectar el scraper."}
