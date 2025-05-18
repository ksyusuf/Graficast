from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException
from core.exceptions import (
    validation_exception_handler,
    http_exception_handler,
    method_not_allowed_exception_handler
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from api.routes import shares, health, templates

app = FastAPI(
    title="Graficast API",
    description="Graficast API Documentation",
    version="1.0.0"
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler'ları
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(StarletteHTTPException, method_not_allowed_exception_handler)

# Rotaları ekle
app.include_router(health.router)
app.include_router(templates.router)
app.include_router(shares.router)
