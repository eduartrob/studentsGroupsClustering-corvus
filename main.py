from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.routers.teams import router as teams_router
from src.rabbitmq import start_rabbitmq_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
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