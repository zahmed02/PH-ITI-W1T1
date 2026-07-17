from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routes import router
from backend.chat_router import router as chat_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Medical Appointment System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include both routers under /api prefix
app.include_router(router, prefix="/api")
app.include_router(chat_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Medical Appointment System API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)