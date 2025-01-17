from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import google_oauth_router

app = FastAPI()

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(google_oauth_router.router, prefix="/auth", tags=["Google OAuth"])
