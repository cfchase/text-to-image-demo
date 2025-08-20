from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import logging
from app.api.router import router as api_router
from app.config import settings
from app.services.mcp_service import mcp_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting application in {settings.environment} mode")
    logger.info(f"LiteLLM integration: {'Enabled' if settings.api_key else 'Disabled'}")
    
    if settings.api_key:
        logger.info(f"LLM model: {settings.model} (via LiteLLM)")
    
    # Initialize MCP service
    logger.info("Initializing MCP service...")
    await mcp_service.initialize()
    
    if mcp_service.is_available:
        logger.info(f"MCP service initialized with {len(mcp_service.get_tools())} tools")
    else:
        logger.info("MCP service initialized with no tools available")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP service...")
    await mcp_service.shutdown()


app = FastAPI(
    title="React FastAPI Template API",
    description="A template API built with FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "React FastAPI Template API"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)