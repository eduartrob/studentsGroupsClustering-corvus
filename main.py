from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.teams import router as teams_router
from services.rabbitmq_service import start_rabbitmq_consumer

from core.database import engine, Base
import models.models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    rabbitmq_conn = await start_rabbitmq_consumer()
    yield
    # Shutdown
    if rabbitmq_conn:
        await rabbitmq_conn.close()

app = FastAPI(title="Student Clustering API (Full Stack Teams)", lifespan=lifespan)
app.include_router(teams_router)

@app.get("/")
def root():
    return {"status": "✅ Clustering Service Running", "docs": "http://localhost:8000/docs"}