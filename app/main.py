from fastapi import FastAPI
from app.scraper.workflow import start_scheduler

app = FastAPI(
    title="web-scraper-cirion API",
    description="Backend para el Web Scraper de componentes IT de Cirion Technologies",
    version="1.0.0"
)

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
