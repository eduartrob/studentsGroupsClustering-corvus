from fastapi import FastAPI
from src.routers.teams import router as teams_router

app = FastAPI(title="Student Clustering API (Full Stack Teams)")
app.include_router(teams_router)

@app.get("/")
def root():
    return {"status": "✅ Clustering Service Running", "docs": "http://localhost:8000/docs"}