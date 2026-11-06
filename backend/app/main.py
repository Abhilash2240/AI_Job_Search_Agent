import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import database
from embeddings.model_loader import get_model

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database tables
    await database.init()
    # Pre-warm SBERT model
    try:
        model = get_model()
        logger.info(f"Loaded SBERT model – dimension: {model.get_sentence_embedding_dimension()}")
    except Exception as e:
        logger.warning(f"SBERT model loading deferred or not found: {e}")
    yield
    # Shutdown: Clean up connections
    await database.close()

app = FastAPI(
    title="AI Job Search Agent API",
    version="0.1.0",
    description="FastAPI backend for the AI Job Search Agent, providing resume parsing, role recommendation, job discovery and matching services.",
    lifespan=lifespan
)

# CORS – allow frontend on any origin during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api import (
    resume,
    profile,
    sources,
    companies,
    discovery,
    jobs,
    matching,
    saved_jobs,
    applications,
    pipeline,
    preferences,
    dashboard,
)

app.include_router(resume.router)
app.include_router(profile.router)
app.include_router(sources.router)
app.include_router(companies.router)
app.include_router(discovery.router)
app.include_router(jobs.router)
app.include_router(matching.router)
app.include_router(saved_jobs.router)
app.include_router(applications.router)
app.include_router(pipeline.router)
app.include_router(preferences.router)
app.include_router(dashboard.router)

# Health check endpoints
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "AI Job Search Agent API",
        "version": "1.0.0",
        "database": "connected",
    }
